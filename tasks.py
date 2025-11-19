"""Background tasks for video transcription"""
from celery import Task, Celery
from app_factory import create_app
from models import db, Transcription
from transcription_service import TranscriptionService
from encryption_service import EncryptionService
import os
import sys
import traceback
from datetime import datetime

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Create Flask app instance
flask_app = create_app()

# Create Celery instance
celery = Celery(
    'tasks',
    broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://localhost:6379/0')
)

# Configure Celery
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_send_sent_event=True,
    worker_send_task_events=True,
    result_expires=3600,
    task_time_limit=3600,
    task_soft_time_limit=3300,
)

class TranscriptionTask(Task):
    """Base task with progress tracking"""
    
    def update_progress(self, transcription_id, status, progress, message):
        """Update task progress in database and emit socket event"""
        try:
            with flask_app.app_context():
                transcription = Transcription.query.get(transcription_id)
                if transcription:
                    transcription.status = status
                    db.session.commit()
                    
                    # Try to emit socket event (may fail if socketio not available in worker)
                    try:
                        from flask_socketio import SocketIO
                        socketio = SocketIO(message_queue=os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
                        socketio.emit('status_update', {
                            'id': transcription_id,
                            'status': status,
                            'progress': progress,
                            'message': message
                        })
                    except Exception as socket_error:
                        # Socket emit failed, but DB update succeeded
                        pass
        except Exception as e:
            print(f"Error updating progress: {e}")

@celery.task(bind=True, base=TranscriptionTask)
def process_transcription(self, transcription_id, video_path, provider, encrypted_key):
    """
    Background task to process video transcription with progress updates
    
    Args:
        transcription_id: Database ID of transcription record
        video_path: Path to uploaded video file
        provider: 'gemini' or 'openai'
        encrypted_key: Encrypted API key
    """
    audio_path = None
    
    with flask_app.app_context():
        try:
            # Update: Starting
            self.update_progress(transcription_id, 'processing', 10, 'Starting transcription...')
            
            # Decrypt API key
            encryption_service = EncryptionService()
            api_key = encryption_service.decrypt(encrypted_key)
            
            # Initialize service
            service = TranscriptionService()
            
            # Step 1: Extract audio
            self.update_progress(transcription_id, 'processing', 20, 'Extracting audio from video...')
            audio_path = service.extract_audio(video_path)
            
            # Step 2: Check file size and estimate time
            file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
            self.update_progress(
                transcription_id, 
                'processing', 
                30, 
                f'Audio extracted ({file_size_mb:.1f}MB). Starting transcription...'
            )
            
            # Step 3: Transcribe with progress updates
            if provider == 'gemini':
                self.update_progress(transcription_id, 'processing', 40, 'Uploading to Gemini API...')
                transcription_text = service.transcribe_with_progress(
                    audio_path, 
                    provider, 
                    api_key,
                    progress_callback=lambda progress, msg: self.update_progress(
                        transcription_id, 'processing', 40 + int(progress * 0.5), msg
                    )
                )
            else:  # openai
                self.update_progress(transcription_id, 'processing', 40, 'Starting Whisper transcription...')
                transcription_text = service.transcribe_with_progress(
                    audio_path, 
                    provider, 
                    api_key,
                    progress_callback=lambda progress, msg: self.update_progress(
                        transcription_id, 'processing', 40 + int(progress * 0.5), msg
                    )
                )
            
            # Step 4: Save result
            self.update_progress(transcription_id, 'processing', 95, 'Saving transcription...')
            
            transcription = Transcription.query.get(transcription_id)
            if transcription:
                transcription.transcription_text = transcription_text
                transcription.status = 'completed'
                transcription.completed_at = datetime.utcnow()
                db.session.commit()
            
            self.update_progress(transcription_id, 'completed', 100, 'Transcription completed!')
            
            return {
                'status': 'completed',
                'transcription_id': transcription_id,
                'text': transcription_text
            }
            
        except Exception as e:
            error_msg = str(e)
            error_trace = traceback.format_exc()
            print(f"Transcription failed: {error_trace}")
            
            # Update database with error
            try:
                transcription = Transcription.query.get(transcription_id)
                if transcription:
                    transcription.status = 'failed'
                    transcription.transcription_text = f"Error: {error_msg}"
                    db.session.commit()
                
                self.update_progress(transcription_id, 'failed', 0, f'Transcription failed: {error_msg}')
            except Exception as db_error:
                print(f"Error updating failure status: {db_error}")
            
            return {
                'status': 'failed',
                'transcription_id': transcription_id,
                'error': error_msg
            }
            
        finally:
            # Cleanup temporary files
            try:
                if audio_path and os.path.exists(audio_path):
                    os.remove(audio_path)
                if os.path.exists(video_path):
                    os.remove(video_path)
            except Exception as e:
                print(f"Cleanup error: {e}")
