import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
    FLASK_ENV = os.getenv("FLASK_ENV", "production")
    SECRET_KEY = os.getenv("SECRET_KEY", "default-secret-key-1234-change-me")
    
    # DB Configuration
    DB_USER = os.getenv("DB_USER", "system")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_DSN = os.getenv("DB_DSN", "localhost/XE")
    
    # Default PIN and Passwords as SHA-256 hashes
    # Default owner PIN: 1234 (hash is 03ac6742...)
    OWNER_PIN_HASH = os.getenv("OWNER_PIN_HASH", "03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4")
    # Default admin password: admin123 (hash is 240a10c4...)
    ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "240a10c4c478f77341e97669d5870020a671cf70c14b2d9c02d1373cc4ee61f0")
    
    # Garage PDF configuration
    GARAGE_NAME = os.getenv("GARAGE_NAME", "Sachin's Sumangal Services")
    GARAGE_SUBTITLE = os.getenv("GARAGE_SUBTITLE", "Maruti Servicing Centre")
    GARAGE_PHONES = os.getenv("GARAGE_PHONES", "9422711826, 9834196573")
    GARAGE_ADDRESS = os.getenv("GARAGE_ADDRESS", "Near LIC Office, Hingoli Road, Nanded")
    BILL_START_NUMBER = int(os.getenv("BILL_START_NUMBER", 2457))
    
    # File storage paths
    PDF_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pdfs")
    
    @classmethod
    def init_app(cls):
        # Create PDF folder if it doesn't exist
        os.makedirs(cls.PDF_FOLDER, exist_ok=True)
