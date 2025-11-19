import os
import random
import string
from datetime import datetime, timedelta, UTC
from flask_mail import Mail, Message
from models import db

mail = Mail()

class EmailService:
    """Handle email sending and OTP verification"""
    
    @staticmethod
    def generate_otp(length=6):
        """Generate a random OTP"""
        return ''.join(random.choices(string.digits, k=length))
    
    @staticmethod
    def send_verification_email(email, otp):
        """Send verification OTP to email"""
        try:
            msg = Message(
                subject='Verify Your Account - Video Transcription App',
                recipients=[email],
                html=f"""
                <html>
                <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f4f4f4;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                        <h1 style="color: #6366f1; text-align: center;">🎬 Video Transcription App</h1>
                        <h2 style="color: #333;">Email Verification</h2>
                        <p style="color: #666; font-size: 16px;">Thank you for signing up! Please use the following OTP to verify your email address:</p>
                        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
                            <h1 style="color: #6366f1; font-size: 36px; letter-spacing: 8px; margin: 0;">{otp}</h1>
                        </div>
                        <p style="color: #666; font-size: 14px;">This OTP will expire in {os.getenv('OTP_EXPIRY_MINUTES', 10)} minutes.</p>
                        <p style="color: #999; font-size: 12px; margin-top: 30px;">If you didn't request this verification, please ignore this email.</p>
                    </div>
                </body>
                </html>
                """
            )
            mail.send(msg)
            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
    
    @staticmethod
    def verify_otp(stored_otp, stored_time, provided_otp):
        """Verify if OTP is valid and not expired"""
        if not stored_otp or not stored_time:
            return False
        
        # Check if OTP matches
        if stored_otp != provided_otp:
            return False
        
        # Check if OTP is expired
        expiry_minutes = int(os.getenv('OTP_EXPIRY_MINUTES', 10))
        expiry_time = stored_time + timedelta(minutes=expiry_minutes)
        
        # Make stored_time timezone-aware if it's not already
        if stored_time.tzinfo is None:
            stored_time = stored_time.replace(tzinfo=UTC)
            expiry_time = stored_time + timedelta(minutes=expiry_minutes)
        
        if datetime.now(UTC) > expiry_time:
            return False
        
        return True
