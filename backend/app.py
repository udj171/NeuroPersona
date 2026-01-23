# ============================================================================
# SCRIPT 3: app.py - Flask Application Factory
# ============================================================================

from flask import Flask, jsonify, request, render_template, send_from_directory
from flask_cors import CORS
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging.config
from datetime import datetime, timezone
import traceback

cache = Cache()
limiter = Limiter(key_func=get_remote_address)

def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    from config import config_by_name
    config = config_by_name.get(config_name, config_by_name['development'])
    
    app = Flask(__name__)
    app.config.from_object(config)
    
    if isinstance(config.LOGGING_CONFIG, dict):
        logging.config.dictConfig(config.LOGGING_CONFIG)
    logger = logging.getLogger(__name__)
    
    db.init_app(app)
    migrate.init_app(app, db)
    cache.init_app(app)
    limiter.init_app(app)
    
    CORS(app, resources={
        r'/api/*': {
            'origins': config.CORS_CONFIG['origins'],
            'methods': config.CORS_CONFIG['methods'],
            'allow_headers': config.CORS_CONFIG['allow_headers'],
        }
    })
    
    @app.before_request
    def before_request():
        request.start_time = datetime.now(timezone.utc)
    
    @app.after_request
    def after_request(response):
        if hasattr(request, 'start_time'):
            duration = (datetime.now(timezone.utc) - request.start_time).total_seconds() * 1000
            response.headers['X-Response-Time'] = f'{duration:.2f}ms'
        
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        return response
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'status': 'error',
            'code': 400,
            'message': 'Bad request',
            'details': str(error),
        }), 400
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'status': 'error',
            'code': 404,
            'message': 'Resource not found',
        }), 404
    
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({
            'status': 'error',
            'code': 429,
            'message': 'Rate limit exceeded',
            'details': str(e.description),
        }), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f'Internal server error: {traceback.format_exc()}')
        return jsonify({
            'status': 'error',
            'code': 500,
            'message': 'Internal server error',
        }), 500
    
    @app.shell_context_processor
    def make_shell_context():
        return {
            'db': db,
            'User': User,
            'Assessment': Assessment,
            'Result': Result,
            'VAEOutput': VAEOutput,
            'PersonalityClassification': PersonalityClassification,
            'GeminiInterpretation': GeminiInterpretation,
        }
    
    with app.app_context():
        db.create_all()
    
    from blueprints.api import api_bp
    from blueprints.health import health_bp
    from blueprints.admin import admin_bp
    
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(health_bp, url_prefix='/health')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/questionnaire')
    def questionnaire():
        return render_template('questionnaire.html')
    
    @app.route('/results')
    def results():
        return render_template('results.html')
    
    @app.route('/static/<path:filename>')
    def serve_static(filename):
        return send_from_directory('static', filename)
    
    logger.info(f'Flask app created with config: {config_name}')
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
