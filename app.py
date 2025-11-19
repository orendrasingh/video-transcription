from flask import render_template, request, jsonify, session
from flask_socketio import emit
import os
from datetime import datetime, UTC
import uuid
from functools import wraps
from dotenv import load_dotenv
import bleach
from email_validator import validate_email, EmailNotValidError
from models import db, APIKey, Transcription, User
from transcription_service import TranscriptionService
from encryption_service import EncryptionService
from email_service import EmailService
from app_factory import app, socketio, limiter

# Load environment variables
load_dotenv()

transcription_service = TranscriptionService()
encryption_service = EncryptionService()
email_service = EmailService()

# Import tasks module
import tasks

# Input sanitization helper
def sanitize_input(text):
    """Sanitize user input to prevent XSS attacks"""
    if not text:
        return text
    return bleach.clean(text, strip=True)

# Email validation helper
def validate_email_address(email):
    """Validate email format"""
    try:
        valid = validate_email(email)
        return valid.email
    except EmailNotValidError:
        return None

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.before_request
def create_tables():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/auth/signup', methods=['POST'])
@limiter.limit("5 per hour")
def signup():
    """Create a new user account and send verification email"""
    data = request.json
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    name = sanitize_input(data.get('name', ''))
    
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
    
    # Validate email format
    validated_email = validate_email_address(email)
    if not validated_email:
        return jsonify({'error': 'Invalid email format'}), 400
    
    # Password strength check
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters long'}), 400
    
    # Check if user already exists
    existing_user = db.session.execute(
        db.select(User).filter_by(email=validated_email)
    ).scalar_one_or_none()
    
    if existing_user:
        return jsonify({'error': 'Email already registered'}), 400
    
    # Generate OTP
    otp = email_service.generate_otp()
    
    # Create new user (not verified yet)
    user = User(
        email=validated_email,
        name=name,
        is_verified=False,
        verification_otp=otp,
        otp_created_at=datetime.now(UTC)
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    
    # Send verification email
    if email_service.send_verification_email(validated_email, otp):
        return jsonify({
            'message': 'Verification email sent. Please check your inbox.',
            'user_id': user.id,
            'requires_verification': True
        })
    else:
        # Rollback user creation if email fails
        db.session.delete(user)
        db.session.commit()
        return jsonify({'error': 'Failed to send verification email. Please try again.'}), 500

@app.route('/api/auth/verify-otp', methods=['POST'])
@limiter.limit("10 per hour")
def verify_otp():
    """Verify OTP and activate user account"""
    data = request.json
    user_id = data.get('user_id')
    otp = data.get('otp', '').strip()
    
    if not user_id or not otp:
        return jsonify({'error': 'User ID and OTP are required'}), 400
    
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if user.is_verified:
        return jsonify({'error': 'Account already verified'}), 400
    
    # Verify OTP
    if email_service.verify_otp(user.verification_otp, user.otp_created_at, otp):
        user.is_verified = True
        user.verification_otp = None
        user.otp_created_at = None
        db.session.commit()
        
        # Log user in
        session['user_id'] = user.id
        session['user_email'] = user.email
        
        return jsonify({
            'message': 'Account verified successfully',
            'user': {'id': user.id, 'email': user.email, 'name': user.name}
        })
    else:
        return jsonify({'error': 'Invalid or expired OTP'}), 400

@app.route('/api/auth/resend-otp', methods=['POST'])
@limiter.limit("3 per hour")
def resend_otp():
    """Resend OTP to user email"""
    data = request.json
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400
    
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if user.is_verified:
        return jsonify({'error': 'Account already verified'}), 400
    
    # Generate new OTP
    otp = email_service.generate_otp()
    user.verification_otp = otp
    user.otp_created_at = datetime.now(UTC)
    db.session.commit()
    
    # Send email
    if email_service.send_verification_email(user.email, otp):
        return jsonify({'message': 'New OTP sent to your email'})
    else:
        return jsonify({'error': 'Failed to send email. Please try again.'}), 500

@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("10 per hour")
def login():
    """Login user"""
    data = request.json
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
    
    # Find user
    user = db.session.execute(
        db.select(User).filter_by(email=email)
    ).scalar_one_or_none()
    
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid email or password'}), 401
    
    # Check if email is verified
    if not user.is_verified:
        return jsonify({
            'error': 'Email not verified',
            'user_id': user.id,
            'requires_verification': True
        }), 403
    
    # Log user in
    session['user_id'] = user.id
    session['user_email'] = user.email
    session.permanent = True
    
    return jsonify({
        'message': 'Login successful',
        'user': {'id': user.id, 'email': user.email, 'name': user.name}
    })

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout user"""
    session.clear()
    return jsonify({'message': 'Logged out successfully'})

@app.route('/api/auth/user', methods=['GET'])
def get_current_user():
    """Get current logged in user"""
    if 'user_id' not in session:
        return jsonify({'user': None})
    
    user = db.session.get(User, session['user_id'])
    if not user:
        session.clear()
        return jsonify({'user': None})
    
    return jsonify({
        'user': {'id': user.id, 'email': user.email, 'name': user.name}
    })

@app.route('/api/keys', methods=['GET', 'POST', 'DELETE'])
@login_required
@login_required
def manage_api_keys():
    """Manage API keys for Gemini and OpenAI"""
    user_id = session['user_id']
    
    if request.method == 'GET':
        keys = db.session.execute(
            db.select(APIKey).filter_by(user_id=user_id)
        ).scalars().all()
        return jsonify([{
            'id': key.id,
            'provider': key.provider,
            'key_preview': key.key_value[:8] + '...' if key.key_value else '',
            'created_at': key.created_at.isoformat()
        } for key in keys])
    
    elif request.method == 'POST':
        data = request.json
        provider = sanitize_input(data.get('provider'))  # 'gemini' or 'openai'
        key_value = data.get('key_value', '').strip()
        
        if not provider or not key_value:
            return jsonify({'error': 'Provider and key_value are required'}), 400
        
        if provider not in ['gemini', 'openai']:
            return jsonify({'error': 'Provider must be gemini or openai'}), 400
        
        # Encrypt the API key before storing
        encrypted_key = encryption_service.encrypt(key_value)
        
        # Check if key already exists for this provider
        existing_key = db.session.execute(
            db.select(APIKey).filter_by(user_id=user_id, provider=provider)
        ).scalar_one_or_none()
        if existing_key:
            existing_key.key_value = encrypted_key
            existing_key.created_at = datetime.now(UTC)
        else:
            existing_key = APIKey(user_id=user_id, provider=provider, key_value=encrypted_key)
            db.session.add(existing_key)
        
        db.session.commit()
        return jsonify({'message': 'API key saved successfully', 'id': existing_key.id})
    
    elif request.method == 'DELETE':
        provider = request.args.get('provider')
        if not provider:
            return jsonify({'error': 'Provider is required'}), 400
        
        key = db.session.execute(
            db.select(APIKey).filter_by(user_id=user_id, provider=provider)
        ).scalar_one_or_none()
        if key:
            db.session.delete(key)
            db.session.commit()
            return jsonify({'message': 'API key deleted successfully'})
        return jsonify({'error': 'API key not found'}), 404

@app.route('/api/transcribe', methods=['POST'])
@login_required
def transcribe():
    """Start video transcription"""
    user_id = session['user_id']
    
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400
    
    video = request.files['video']
    provider = request.form.get('provider', 'gemini')
    
    if video.filename == '':
        return jsonify({'error': 'No video file selected'}), 400
    
    # Check if API key exists
    api_key_record = db.session.execute(
        db.select(APIKey).filter_by(user_id=user_id, provider=provider)
    ).scalar_one_or_none()
    if not api_key_record:
        return jsonify({'error': f'No API key found for {provider}'}), 400
    
    # Decrypt the API key
    api_key = encryption_service.decrypt(api_key_record.key_value)
    
    # Generate unique ID for this transcription
    transcription_id = str(uuid.uuid4())
    
    # Emit upload progress
    socketio.emit('status_update', {
        'id': transcription_id,
        'status': 'uploading',
        'progress': 5,
        'message': 'Uploading video file...'
    })
    
    # Save video file
    filename = f"{transcription_id}_{video.filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    video.save(filepath)
    
    # Emit upload complete
    socketio.emit('status_update', {
        'id': transcription_id,
        'status': 'queued',
        'progress': 10,
        'message': 'Upload complete. Queued for processing...'
    })
    
    # Create transcription record
    transcription = Transcription(
        id=transcription_id,
        user_id=user_id,
        filename=video.filename,
        provider=provider,
        status='queued'
    )
    db.session.add(transcription)
    db.session.commit()
    
    # Queue transcription task with Celery
    # Encrypt API key for task
    encrypted_key = api_key_record.key_value
    
    tasks.process_transcription.apply_async(
        args=[transcription_id, filepath, provider, encrypted_key],
        task_id=transcription_id
    )
    
    return jsonify({
        'transcription_id': transcription_id,
        'message': 'Transcription queued and will start shortly',
        'status': 'queued'
    })

@app.route('/api/transcriptions/<transcription_id>', methods=['GET'])
@login_required
def get_transcription(transcription_id):
    """Get specific transcription details"""
    user_id = session['user_id']
    transcription = db.session.get(Transcription, transcription_id)
    if not transcription or transcription.user_id != user_id:
        return jsonify({'error': 'Transcription not found'}), 404
    
    # Check Celery task status if still processing
    task_info = {}
    if transcription.status in ['queued', 'processing']:
        try:
            task = tasks.celery.AsyncResult(transcription_id)
            task_info = {
                'task_state': task.state,
                'task_info': task.info if task.info else {}
            }
        except Exception as e:
            print(f"Error fetching task status: {e}")
    
    return jsonify({
        'id': transcription.id,
        'filename': transcription.filename,
        'provider': transcription.provider,
        'status': transcription.status,
        'text': transcription.transcription_text,
        'created_at': transcription.created_at.isoformat(),
        'completed_at': transcription.completed_at.isoformat() if transcription.completed_at else None,
        **task_info
    })

@app.route('/api/history', methods=['GET'])
@login_required
def get_history():
    """Get transcription history"""
    user_id = session['user_id']
    transcriptions = db.session.execute(
        db.select(Transcription).filter_by(user_id=user_id).order_by(Transcription.created_at.desc())
    ).scalars().all()
    return jsonify([{
        'id': t.id,
        'filename': t.filename,
        'provider': t.provider,
        'status': t.status,
        'text': t.transcription_text[:200] + '...' if t.transcription_text and len(t.transcription_text) > 200 else t.transcription_text,
        'created_at': t.created_at.isoformat(),
        'completed_at': t.completed_at.isoformat() if t.completed_at else None
    } for t in transcriptions])

@app.route('/api/history/<transcription_id>', methods=['DELETE'])
@login_required
def delete_transcription(transcription_id):
    """Delete a transcription from history"""
    user_id = session['user_id']
    transcription = db.session.get(Transcription, transcription_id)
    if not transcription or transcription.user_id != user_id:
        return jsonify({'error': 'Transcription not found'}), 404
    
    db.session.delete(transcription)
    db.session.commit()
    return jsonify({'message': 'Transcription deleted successfully'})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, host='0.0.0.0', debug=True, port=5001, allow_unsafe_werkzeug=True)
