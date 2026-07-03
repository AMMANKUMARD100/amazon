import os

class Config:
    """Base configurations for CampusMate AI."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev_secret_key_change_in_production_123456')
    
    # Database
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DATABASE_PATH = os.environ.get('DATABASE_PATH', os.path.join(BASE_DIR, 'database', 'campusmate.db'))
    
    # Session Settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False  # Set to True in production (HTTPS)
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Rate Limiting
    RATELIMIT_DEFAULT = "100 per minute"
    RATELIMIT_AUTH = "10 per minute"
