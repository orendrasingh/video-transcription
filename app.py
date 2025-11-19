from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
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
from email_service import EmailService, mail
import threading

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Security Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24))
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///transcriptions.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 524288000))

# Email Configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

# Security Headers
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.socket.io; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' ws: wss:"
    return response

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)
mail.init_app(app)
CORS(app, supports_credentials=True)
socketio = SocketIO(app, cors_allowed_origins="*")

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[f"{os.getenv('RATE_LIMIT_PER_MINUTE', 60)} per minute"],
    storage_uri=os.getenv('REDIS_URL', 'memory://')
)

transcription_service = TranscriptionService()
encryption_service = EncryptionService()
email_service = EmailService()

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
    
    # Save video file
    filename = f"{transcription_id}_{video.filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    video.save(filepath)
    
    # Create transcription record
    transcription = Transcription(
        id=transcription_id,
        user_id=user_id,
        filename=video.filename,
        provider=provider,
        status='processing'
    )
    db.session.add(transcription)
    db.session.commit()
    
    # Start transcription in background thread
    thread = threading.Thread(
        target=process_transcription,
        args=(transcription_id, filepath, provider, api_key)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'transcription_id': transcription_id,
        'message': 'Transcription started'
    })

def process_transcription(transcription_id, filepath, provider, api_key):
    """Process transcription in background"""
    with app.app_context():
        try:
            # Update status
            socketio.emit('status_update', {
                'transcription_id': transcription_id,
                'status': 'processing',
                'message': 'Extracting audio from video...'
            })
            
            # Extract audio
            audio_path = transcription_service.extract_audio(filepath)
            
            socketio.emit('status_update', {
                'transcription_id': transcription_id,
                'status': 'processing',
                'message': 'Transcribing audio...'
            })
            
            # Transcribe
            result = transcription_service.transcribe(audio_path, provider, api_key)
            
            # Update database
            transcription = db.session.get(Transcription, transcription_id)
            transcription.status = 'completed'
            transcription.transcription_text = result
            transcription.completed_at = datetime.now(UTC)
            db.session.commit()
            
            socketio.emit('status_update', {
                'transcription_id': transcription_id,
                'status': 'completed',
                'message': 'Transcription completed!',
                'text': result
            })
            
            # Cleanup
            os.remove(filepath)
            os.remove(audio_path)
            
        except Exception as e:
            # Update status to failed
            transcription = db.session.get(Transcription, transcription_id)
            transcription.status = 'failed'
            transcription.transcription_text = f'Error: {str(e)}'
            transcription.completed_at = datetime.now(UTC)
            db.session.commit()
            
            socketio.emit('status_update', {
                'transcription_id': transcription_id,
                'status': 'failed',
                'message': f'Transcription failed: {str(e)}'
            })

@app.route('/api/transcriptions/<transcription_id>', methods=['GET'])
@login_required
def get_transcription(transcription_id):
    """Get specific transcription details"""
    user_id = session['user_id']
    transcription = db.session.get(Transcription, transcription_id)
    if not transcription or transcription.user_id != user_id:
        return jsonify({'error': 'Transcription not found'}), 404
    
    return jsonify({
        'id': transcription.id,
        'filename': transcription.filename,
        'provider': transcription.provider,
        'status': transcription.status,
        'text': transcription.transcription_text,
        'created_at': transcription.created_at.isoformat(),
        'completed_at': transcription.completed_at.isoformat() if transcription.completed_at else None
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
