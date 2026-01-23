# ============================================================================
# SCRIPT 1: config.py - Configuration Management
# ============================================================================

import os
import json
from datetime import timedelta
from pathlib import Path

class Config:
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    SECRET_KEY = os.getenv('SECRET_KEY', 'atharvajagtap0107080133446677cybeydbs')
    DEBUG = os.getenv('DEBUG', 'False') == 'True'
    TESTING = False
    
    BASE_DIR = Path(__file__).parent.absolute()
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    TEMP_FOLDER = os.path.join(BASE_DIR, 'temp')
    MODEL_FOLDER = os.path.join(BASE_DIR, 'models')
    LOG_FOLDER = os.path.join(BASE_DIR, 'logs')
    
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(TEMP_FOLDER, exist_ok=True)
    os.makedirs(MODEL_FOLDER, exist_ok=True)
    os.makedirs(LOG_FOLDER, exist_ok=True)
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = os.getenv('SQLALCHEMY_ECHO', 'False') == 'True'
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'echo_pool': False,
        'max_overflow': 20,
    }
    
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///personality_assessment.db')
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300
    
    JSON_SORT_KEYS = False
    JSONIFY_PRETTYPRINT_REGULAR = os.getenv('FLASK_ENV') != 'production'
    
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    GEMINI_API_TIMEOUT = int(os.getenv('GEMINI_API_TIMEOUT', '30'))
    GEMINI_MAX_RETRIES = int(os.getenv('GEMINI_MAX_RETRIES', '3'))
    GEMINI_RETRY_DELAY = int(os.getenv('GEMINI_RETRY_DELAY', '2'))
    
    VAE_MODEL_PATH = os.path.join(MODEL_FOLDER, 'vae_model.pkl')
    VAE_SCALER_PATH = os.path.join(MODEL_FOLDER, 'vae_scaler.pkl')
    VAE_ENCODER_PATH = os.path.join(MODEL_FOLDER, 'vae_encoder.pkl')
    VAE_DECODER_PATH = os.path.join(MODEL_FOLDER, 'vae_decoder.pkl')
    
    QUESTIONNAIRE_CONFIG = {
        'total_questions': 35,
        'domain_questions': 5,
        'num_domains': 6,
        'validity_questions': [30, 31, 32, 33, 34],
        'min_response': 0,
        'max_response': 10,
        'required_variance': 1.5,
    }
    
    ASSESSMENT_CONFIG = {
        'min_age': 13,
        'max_age': 120,
        'valid_sexes': ['M', 'F', 'O'],
        'response_timeout_seconds': 3600,
        'max_retakes': 5,
    }
    
    API_CONFIG = {
        'max_request_size': 5 * 1024 * 1024,
        'rate_limit_enabled': True,
        'rate_limit_requests': 100,
        'rate_limit_period': 3600,
        'request_timeout': 30,
    }
    
    LOGGING_CONFIG = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            },
            'detailed': {
                'format': '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(funcName)s(): %(message)s'
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'DEBUG',
                'formatter': 'standard',
                'stream': 'ext://sys.stdout',
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': 'detailed',
                'filename': os.path.join(LOG_FOLDER, 'app.log'),
                'maxBytes': 10485760,
                'backupCount': 10,
            },
            'error_file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'ERROR',
                'formatter': 'detailed',
                'filename': os.path.join(LOG_FOLDER, 'error.log'),
                'maxBytes': 10485760,
                'backupCount': 10,
            },
        },
        'root': {
            'level': 'INFO',
            'handlers': ['console', 'file', 'error_file'],
        },
    }
    
    SECURITY_CONFIG = {
        'enable_csrf': True,
        'session_timeout': 1800,
        'password_min_length': 8,
        'max_login_attempts': 5,
        'lockout_duration': 900,
    }
    
    EMAIL_CONFIG = {
        'sender_email': os.getenv('SENDER_EMAIL', 'noreply@personality-assessment.com'),
        'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
        'smtp_port': int(os.getenv('SMTP_PORT', '587')),
        'smtp_username': os.getenv('SMTP_USERNAME', ''),
        'smtp_password': os.getenv('SMTP_PASSWORD', ''),
    }
    
    CORS_CONFIG = {
        'origins': os.getenv('CORS_ORIGINS', 'http://localhost:5000,http://localhost:3000').split(','),
        'methods': ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        'allow_headers': ['Content-Type', 'Authorization'],
    }
    
    BACKUP_CONFIG = {
        'enable_backups': True,
        'backup_frequency': 'daily',
        'backup_retention_days': 30,
        'backup_path': os.path.join(BASE_DIR, 'backups'),
    }
    
    os.makedirs(BACKUP_CONFIG['backup_path'], exist_ok=True)
    
    MONITORING_CONFIG = {
        'enable_monitoring': True,
        'metrics_interval': 60,
        'error_alert_threshold': 5,
        'performance_alert_threshold': 5000,
    }
    
    PAGINATION_CONFIG = {
        'default_page_size': 20,
        'max_page_size': 100,
        'min_page_size': 1,
    }
    
    FEATURES = {
        'enable_email_notifications': False,
        'enable_pdf_export': True,
        'enable_data_analytics': True,
        'enable_user_dashboard': True,
        'enable_admin_panel': True,
        'enable_api_documentation': True,
    }
    
    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False
    SQLALCHEMY_ECHO = True
    CACHE_TYPE = 'simple'
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    SQLALCHEMY_ECHO = False
    CACHE_TYPE = 'redis'
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'
    PREFERRED_URL_SCHEME = 'https'

class TestingConfig(Config):
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    CACHE_TYPE = 'simple'

config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig,
}

def get_config():
    env = os.getenv('FLASK_ENV', 'development')
    return config_by_name.get(env, DevelopmentConfig)
