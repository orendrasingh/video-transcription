from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, UTC
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    """Store user accounts"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100))
    is_verified = db.Column(db.Boolean, default=False)
    verification_otp = db.Column(db.String(10))
    otp_created_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    
    # Relationships
    api_keys = db.relationship('APIKey', backref='user', lazy=True, cascade='all, delete-orphan')
    transcriptions = db.relationship('Transcription', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.email}>'

class APIKey(db.Model):
    """Store encrypted API keys for different providers"""
    __tablename__ = 'api_keys'
    __table_args__ = (db.UniqueConstraint('user_id', 'provider', name='unique_user_provider'),)
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    provider = db.Column(db.String(50), nullable=False)  # 'gemini' or 'openai'
    key_value = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    
    def __repr__(self):
        return f'<APIKey {self.provider}>'

class Transcription(db.Model):
    """Store transcription history"""
    __tablename__ = 'transcriptions'
    
    id = db.Column(db.String(100), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filename = db.Column(db.String(500), nullable=False)
    provider = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), default='pending')  # pending, processing, completed, failed
    transcription_text = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    completed_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<Transcription {self.id} - {self.filename}>'
