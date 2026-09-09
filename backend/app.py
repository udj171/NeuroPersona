"""
Flask Application - Personality Assessment Backend (API Only)
FIXED: Auto-detect old INTEGER id schema and reset to STRING(36) UUID
"""

import os
import logging
import traceback
from datetime import datetime, timezone

from flask import Flask, jsonify, request
from flask_cors import CORS
from sqlalchemy import text
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
# CREATE APP FIRST
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

# ============================================================================
# IMPORT MODELS (MUST BE AFTER app IS CREATED)
# ============================================================================

from models import db, User, Assessment

# Initialize database with app
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
model_engine = None
narrative_generator = None

def initialize_engines():
    """Build the three engines at startup. Each one is independent: a failure
    leaves that engine as None and the app still serves."""
    global scoring_engine, model_engine, narrative_generator

    try:
        logger.info("[ENGINES] Initializing scoring engine...")
        from scoring_engine import ScoringEngine
        scoring_engine = ScoringEngine()
        logger.info("[ENGINES] ✓ Scoring engine initialized")
    except Exception as e:
        logger.error(f"[ENGINES] ✗ Failed to initialize scoring engine: {str(e)}")
        scoring_engine = None

    try:
        logger.info("[ENGINES] Initializing model inference engine...")
        from model_inference import ModelInferenceEngine
        model_engine = ModelInferenceEngine()
        if model_engine.is_trained:
            logger.info("[ENGINES] ✓ Model engine initialized with trained weights")
        else:
            logger.warning("[ENGINES] ⚠ Model engine initialized WITHOUT weights. "
                           "Results will be scored but no type will be claimed. "
                           "See training/ to produce model_weights/ocean_vae.npz")
    except Exception as e:
        logger.error(f"[ENGINES] ✗ Failed to initialize model engine: {str(e)}")
        model_engine = None

    try:
        logger.info("[ENGINES] Initializing narrative generator...")
        from narrative import NarrativeGenerator
        narrative_generator = NarrativeGenerator()
        logger.info(f"[ENGINES] ✓ Narrative generator initialized "
                    f"(backend: {narrative_generator.active_backend})")
    except Exception as e:
        logger.error(f"[ENGINES] ✗ Failed to initialize narrative generator: {str(e)}")
        narrative_generator = None

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
# DATABASE INITIALIZATION & CONNECTION VERIFICATION
# ============================================================================

def verify_database_connection():
    """Verify database connection is working"""
    try:
        logger.info("[DB] Verifying database connection...")
        db_url = app.config['SQLALCHEMY_DATABASE_URI']
        if 'postgresql' in db_url:
            logger.info(f"[DB] Using PostgreSQL (Render)")
        elif 'sqlite' in db_url:
            logger.info(f"[DB] Using SQLite (local/fallback)")
        else:
            logger.info(f"[DB] Using: {db_url[:50]}...")
        
        # Try to execute a simple query
        with app.app_context():
            result = db.session.execute(text('SELECT 1'))
            logger.info("[DB] ✓ Database connection verified")
            return True
    except Exception as e:
        logger.error(f"[DB] ✗ Database connection failed: {str(e)}")
        logger.error(f"[DB] Traceback: {traceback.format_exc()}")
        return False

def check_and_migrate_schema():
    """Check if database schema needs to be recreated for UUID migration"""
    with app.app_context():
        try:
            logger.info("[SCHEMA] Checking database schema...")
            # Check if users table exists and inspect its structure
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'users' not in tables:
                logger.info("[SCHEMA] No users table found, creating fresh schema...")
                db.create_all()
                logger.info("[SCHEMA] ✓ Fresh schema created")
                return True
            
            # Check if id column is String type (new schema)
            columns = inspector.get_columns('users')
            id_column = next((c for c in columns if c['name'] == 'id'), None)
            
            if id_column:
                col_type = str(id_column['type'])
                logger.info(f"[SCHEMA] Users.id column type: {col_type}")
                
                # If it's INTEGER, GUID, SERIAL, or CHAR type from old schema, reset
                if any(x in col_type for x in ['INTEGER', 'SERIAL', 'GUID']) or (col_type == 'CHAR' and 'VARCHAR' not in col_type):
                    logger.warning(f"[SCHEMA] Detected old schema with {col_type} id column. Resetting to String(36) UUID schema...")
                    try:
                        logger.info("[SCHEMA] Dropping all tables...")
                        db.drop_all()
                        logger.info("[SCHEMA] ✓ All tables dropped")
                        
                        logger.info("[SCHEMA] Creating new tables with String(36) UUID schema...")
                        db.create_all()
                        logger.info("[SCHEMA] ✓ New schema created")
                        
                        # Verify
                        new_inspector = db.inspect(db.engine)
                        new_columns = new_inspector.get_columns('users')
                        new_id_col = next((c for c in new_columns if c['name'] == 'id'), None)
                        logger.info(f"[SCHEMA] ✓ Migration complete. New id column type: {new_id_col['type']}")
                        return True
                    except Exception as e:
                        logger.error(f"[SCHEMA] ✗ Error during schema migration: {str(e)}")
                        logger.error(traceback.format_exc())
                        return False
                elif 'VARCHAR' in col_type or 'CHAR' in col_type:
                    logger.info("[SCHEMA] ✓ Schema is up-to-date (VARCHAR/STRING type)")
                    return True
                else:
                    logger.info(f"[SCHEMA] ✓ Schema appears correct (type: {col_type})")
                    return True
            else:
                logger.warning("[SCHEMA] Could not determine id column type, attempting fresh create...")
                db.drop_all()
                db.create_all()
                return True
                
        except Exception as e:
            logger.error(f"[SCHEMA] ✗ Error checking schema: {str(e)}")
            logger.error(traceback.format_exc())
            # Attempt recovery by recreating
            try:
                logger.info("[SCHEMA] Attempting schema recovery...")
                db.drop_all()
                db.create_all()
                logger.info("[SCHEMA] ✓ Schema recovered")
                return True
            except Exception as recovery_error:
                logger.error(f"[SCHEMA] ✗ Schema recovery failed: {str(recovery_error)}")
                return False

# ============================================================================
# CATCH-ALL FOR NON-API ROUTES
# ============================================================================

@app.route('/')
@app.route('/<path:path>')
def frontend_redirect(path=None):
    """Redirect all non-API requests to frontend info"""
    return jsonify({
        'error': 'Frontend not served from backend',
        'message': 'Visit: https://www.predictmypersonality.com',
        'api_endpoints': [
            'GET /api/health',
            'GET /api/questionnaire',
            'POST /api/start-assessment',
            'POST /api/submit-assessment',
            'GET /api/results/<assessment_id>'
        ]
    }), 404

# ============================================================================
# STARTUP SEQUENCE
# ============================================================================

with app.app_context():
    try:
        logger.info("[STARTUP] ========================================")
        logger.info("[STARTUP] NEUROPERSONA BACKEND INITIALIZATION")
        logger.info("[STARTUP] ========================================")
        
        logger.info(f"[STARTUP] Database: {app.config['SQLALCHEMY_DATABASE_URI'][:60]}...")
        
        # Verify database connection first
        db_ok = verify_database_connection()
        if not db_ok:
            logger.error("[STARTUP] ✗ Database connection failed, but continuing...")
        else:
            logger.info("[STARTUP] ✓ Database connection verified")
        
        # Check and migrate schema if needed
        schema_ok = check_and_migrate_schema()
        if not schema_ok:
            logger.error("[STARTUP] ✗ Schema check/migration failed, but continuing...")
        else:
            logger.info("[STARTUP] ✓ Schema check passed")
        
    except Exception as e:
        logger.error(f"[STARTUP] ✗ Error during startup: {str(e)}")
        logger.error(traceback.format_exc())

# Initialize engines after app context
with app.app_context():
    initialize_engines()
    set_engines(scoring_engine, model_engine, narrative_generator)
    logger.info("[ENGINES] ✓ All engines passed to API routes")

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
logger.info(f"     - Model Engine: {'✓ Ready' if model_engine else '✗ Failed'}"
            + (f" (trained: {model_engine.is_trained})" if model_engine else ''))
logger.info(f"     - Narrative: {'✓ Ready' if narrative_generator else '✗ Failed'}"
            + (f" (backend: {narrative_generator.active_backend})" if narrative_generator else ''))
logger.info("[APP] ✓ API endpoints ready:")
logger.info("     - GET /api/health")
logger.info("     - GET /api/questionnaire")
logger.info("     - POST /api/start-assessment")
logger.info("     - POST /api/submit-assessment")
logger.info("     - GET /api/results/<assessment_id>")
logger.info("[APP] ✓ Ready to accept requests")

# ============================================================================
# RUN APP
# ============================================================================

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('FLASK_ENV') == 'development'
    )
