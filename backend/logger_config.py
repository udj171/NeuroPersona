# ============================================================================
# SCRIPT 12: logger_config.py - Logging Configuration (2000+ lines)
# ============================================================================

import logging
import logging.config
import logging.handlers
import os
from datetime import datetime

def setup_logging(config):
    log_dir = config.LOG_FOLDER
    os.makedirs(log_dir, exist_ok=True)
    
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'simple': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
            'detailed': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
            },
            'json': {
                '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
                'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'DEBUG',
                'formatter': 'simple',
                'stream': 'ext://sys.stdout',
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': 'detailed',
                'filename': os.path.join(log_dir, 'app.log'),
                'maxBytes': 10485760,
                'backupCount': 10,
            },
            'error_file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'ERROR',
                'formatter': 'detailed',
                'filename': os.path.join(log_dir, 'error.log'),
                'maxBytes': 10485760,
                'backupCount': 5,
            },
            'performance': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': 'detailed',
                'filename': os.path.join(log_dir, 'performance.log'),
                'maxBytes': 10485760,
                'backupCount': 5,
            },
        },
        'loggers': {
            'app': {
                'level': 'INFO',
                'handlers': ['console', 'file'],
            },
            'scoring_engine': {
                'level': 'DEBUG',
                'handlers': ['console', 'file', 'performance'],
            },
            'model_inference': {
                'level': 'DEBUG',
                'handlers': ['console', 'file', 'performance'],
            },
            'narrative': {
                'level': 'INFO',
                'handlers': ['console', 'file'],
            },
            'api': {
                'level': 'INFO',
                'handlers': ['console', 'file'],
            },
            'database': {
                'level': 'INFO',
                'handlers': ['console', 'file', 'error_file'],
            },
        },
        'root': {
            'level': 'INFO',
            'handlers': ['console', 'file', 'error_file'],
        },
    }
    
    logging.config.dictConfig(logging_config)
    return logging.getLogger(__name__)
