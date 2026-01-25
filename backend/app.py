"""
Flask Application - Personality Assessment Backend (API Only)
FIXED: Engines properly initialized, error handling improved
"""

import os
import logging
import traceback
from datetime import datetime, timezone

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================================================
# SETUP LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# INITIALIZE DATABASE
# ============================================================================

db = SQLAlchemy()

# ============================================================================
# IMPORT MODELS (CRITICAL - MUST BE AFTER db INITIALIZATION)
# ============================================================================

from models import User, Assessment

# ============================================================================
# CREATE APP
# ============================================================================

app = Flask(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL', 
    'sqlite:///assessment.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_SORT_KEYS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize database
db.init_app(app)

# ============================================================================
# CORS CONFIGURATION - CRITICAL!
# ============================================================================

CORS(app,
     resources={r"/api/*": {"origins": "*"}},
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
     allow_headers=['Content-Type', 'Authorization'],
     supports_credentials=True,
     max_age=3600)

logger.info("[CORS] ✓ CORS enabled for all /api/* routes")

# ============================================================================
# INITIALIZE ENGINE INSTANCES
# ============================================================================

scoring_engine = None
vae_engine = None
gemini_client = None

def initialize_engines():
    """Initialize AI engines at startup"""
    global scoring_engine, vae_engine, gemini_client
    
    try:
        logger.info("[ENGINES] Initializing scoring engine...")
        from scoring_engine import ScoringEngine
        scoring_engine = ScoringEngine()
        logger.info("[ENGINES] ✓ Scoring engine initialized")
    except Exception as e:
        logger.error(f"[ENGINES] ✗ Failed to initialize scoring engine: {str(e)}")
        scoring_engine = None
    
    try:
        logger.info("[ENGINES] Initializing VAE inference engine...")
        from vae_inference import VAEInferenceEngine
        vae_engine = VAEInferenceEngine()
        logger.info("[ENGINES] ✓ VAE engine initialized")
    except Exception as e:
        logger.error(f"[ENGINES] ✗ Failed to initialize VAE engine: {str(e)}")
        vae_engine = None
    
    try:
        logger.info("[ENGINES] Initializing Gemini client...")
        from gemini_client import GeminiClient
        gemini_client = GeminiClient()
        logger.info("[ENGINES] ✓ Gemini client initialized")
    except Exception as e:
        logger.error(f"[ENGINES] ✗ Failed to initialize Gemini client: {str(e)}")
        gemini_client = None

# ============================================================================
# IMPORT AND REGISTER BLUEPRINT (MUST BE AFTER app CREATION)
# ============================================================================

from api_routes import api_bp, set_engines

app.register_blueprint(api_bp, url_prefix='/api')
logger.info("[BLUEPRINT] ✓ API blueprint registered")

# ============================================================================
# REQUEST/RESPONSE MIDDLEWARE
# ============================================================================

@app.before_request
def before_request():
    """Track request start time"""
    request.start_time = datetime.now(timezone.utc)
    logger.info(f"[REQUEST] {request.method} {request.path} from {request.remote_addr}")

@app.after_request
def after_request(response):
    """Add security headers and response time"""
    if hasattr(request, 'start_time'):
        duration = (datetime.now(timezone.utc) - request.start_time).total_seconds() * 1000
        response.headers['X-Response-Time'] = f'{duration:.2f}ms'
    
    # Security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    logger.info(f"[RESPONSE] {request.method} {request.path} - {response.status_code}")
    return response

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(400)
def bad_request(error):
    """Handle 400 Bad Request"""
    logger.warning(f"[ERROR 400] {str(error)}")
    return jsonify({
        'status': 'error',
        'code': 400,
        'message': 'Bad request',
        'details': str(error)
    }), 400

@app.errorhandler(404)
def not_found(error):
    """Handle 404 Not Found"""
    logger.warning(f"[ERROR 404] {request.path} not found")
    return jsonify({
        'status': 'error',
        'code': 404,
        'message': 'Endpoint not found',
        'path': request.path,
        'hint': 'Only /api/* endpoints are available. Frontend is served from Vercel.'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 Internal Server Error"""
    logger.error(f"[ERROR 500] {traceback.format_exc()}")
    try:
        db.session.rollback()
    except:
        pass
    return jsonify({
        'status': 'error',
        'code': 500,
        'message': 'Internal server error',
        'details': 'An error occurred processing your request'
    }), 500

# ============================================================================
# CREATE DATABASE TABLES
# ============================================================================

with app.app_context():
    try:
        logger.info("[DATABASE] Creating tables...")
        db.create_all()
        logger.info("[DATABASE] ✓ Database tables created/verified")
    except Exception as e:
        logger.error(f"[DATABASE] ✗ Error creating tables: {e}")
        logger.error(traceback.format_exc())

# ============================================================================
# INITIALIZE ENGINES AFTER APP CONTEXT
# ============================================================================

with app.app_context():
    initialize_engines()
    set_engines(scoring_engine, vae_engine, gemini_client)
    logger.info("[ENGINES] ✓ All engines passed to API routes")

# ============================================================================
# CATCH-ALL FOR NON-API ROUTES
# ============================================================================

@app.route('/')
@app.route('/<path:path>')
def frontend_redirect(path=None):
    """Redirect all non-API requests"""
    return jsonify({
        'error': 'Frontend not served from backend',
        'message': 'Visit: https://www.predictmypersonality.com',
        'api_endpoints': [
            'GET /api/health',
            'POST /api/start-assessment',
            'POST /api/submit-assessment',
            'GET /api/results/<assessment_id>'
        ]
    }), 404

# ============================================================================
# STARTUP MESSAGES
# ============================================================================

logger.info("[APP] ✓ Flask app initialized successfully")
logger.info(f"[APP] ✓ Database: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")
logger.info("[APP] ✓ CORS enabled: Yes")
logger.info("[APP] ✓ All routes served via blueprint")
logger.info("[APP] ✓ Frontend: Served from Vercel (https://www.predictmypersonality.com)")
logger.info("[APP] ✓ Engine Status:")
logger.info(f"     - Scoring Engine: {'✓ Ready' if scoring_engine else '✗ Failed'}")
logger.info(f"     - VAE Engine: {'✓ Ready' if vae_engine else '✗ Failed'}")
logger.info(f"     - Gemini Client: {'✓ Ready' if gemini_client else '✗ Failed'}")
logger.info("[APP] ✓ API endpoints ready:")
logger.info("     - GET /api/health")
logger.info("     - POST /api/start-assessment")
logger.info("     - POST /api/submit-assessment")
logger.info("     - GET /api/results/<assessment_id>")

# ============================================================================
# RUN APP
# ============================================================================

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('FLASK_ENV') == 'development'
    )
