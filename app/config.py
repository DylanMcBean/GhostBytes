import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-insecure')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI', 'sqlite:///chat.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Security improvements for session cookies
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True if os.environ.get('FLASK_ENV') == 'production' else False
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = True if os.environ.get('FLASK_ENV') == 'production' else False
    
    # Flask-Login configuration
    REMEMBER_COOKIE_DURATION = 60 * 60 * 24 * 30  # 30 days
    PPERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 30  # 30 days