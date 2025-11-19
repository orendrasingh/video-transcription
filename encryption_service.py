import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

class EncryptionService:
    """Handle encryption and decryption of sensitive data"""
    
    def __init__(self):
        encryption_key = os.getenv('ENCRYPTION_KEY')
        if not encryption_key:
            raise ValueError("ENCRYPTION_KEY not found in environment variables")
        self.cipher = Fernet(encryption_key.encode())
    
    def encrypt(self, data: str) -> str:
        """Encrypt a string and return base64 encoded encrypted data"""
        if not data:
            return data
        encrypted = self.cipher.encrypt(data.encode())
        return encrypted.decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt base64 encoded encrypted data and return original string"""
        if not encrypted_data:
            return encrypted_data
        decrypted = self.cipher.decrypt(encrypted_data.encode())
        return decrypted.decode()
