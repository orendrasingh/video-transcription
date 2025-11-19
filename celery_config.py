"""Celery configuration for background tasks"""
from celery import Celery
from kombu import Queue
import os

def make_celery(app):
    """Create Celery instance integrated with Flask"""
    celery = Celery(
        app.import_name,
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
        result_expires=3600,  # Results expire after 1 hour
        task_time_limit=3600,  # 1 hour max per task
        task_soft_time_limit=3300,  # Soft limit at 55 minutes
    )
    
    class ContextTask(celery.Task):
        """Make celery tasks work with Flask app context"""
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery
