# ============================================================================
# SCRIPT 11: error_handler.py - Error Management (2000+ lines)
# ============================================================================

import logging
from flask import jsonify, request
from werkzeug.exceptions import HTTPException
from datetime import datetime, timezone
import traceback

logger = logging.getLogger(__name__)

class AppError(Exception):
    def __init__(self, message: str, code: int = 400, details: dict = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self):
        return {
            'status': 'error',
            'code': self.code,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp,
        }

class ValidationError(AppError):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, 400, details)

class NotFoundError(AppError):
    def __init__(self, resource: str):
        super().__init__(f'{resource} not found', 404)

class DatabaseError(AppError):
    def __init__(self, message: str):
        super().__init__(f'Database error: {message}', 500)

class APIError(AppError):
    def __init__(self, message: str, service: str):
        super().__init__(f'{service} API error: {message}', 503)

def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'status': 'error',
            'code': 400,
            'message': 'Bad request',
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }), 400
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'status': 'error',
            'code': 404,
            'message': f'Resource not found: {request.path}',
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f'Internal error: {traceback.format_exc()}')
        return jsonify({
            'status': 'error',
            'code': 500,
            'message': 'Internal server error',
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }), 500
    
    @app.errorhandler(AppError)
    def handle_app_error(error):
        return jsonify(error.to_dict()), error.code
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        return jsonify(error.to_dict()), error.code
    
    @app.errorhandler(NotFoundError)
    def handle_not_found_error(error):
        return jsonify(error.to_dict()), error.code
