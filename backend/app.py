import os
import json
import logging
import traceback
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from functools import wraps
from io import BytesIO
import os
import logging

# Check if PyTorch is available
try:
    import torch
    HAS_PYTORCH = True
    DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logging.info(f"✅ PyTorch available on {DEVICE}")
except ImportError:
    HAS_PYTORCH = False
    DEVICE = None
    logging.warning("⚠️ PyTorch not available - VAE inference disabled")

# Flask and extensions
from flask import (
    Flask, request, jsonify, send_file, current_app, 
    Blueprint, session, g
)
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache

# Environment and configuration
from dotenv import load_dotenv
load_dotenv()

# Database
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from psycopg2.extras import RealDictCursor

# Data validation
from marshmallow import Schema, fields, ValidationError, pre_load

# Logging and monitoring
try:
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration
    SENTRY_ENABLED = True
except ImportError:
    SENTRY_ENABLED = False

# PDF export
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# ==============================================================================
# CONFIGURATION & INITIALIZATION
# ==============================================================================

# ⭐ CRITICAL: Enable CORS for your frontend domain
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "https://predictmypersonality.com",
            "http://localhost:3000",  # for local testing
            "http://localhost:5000"
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

# Your existing routes...
@app.route('/api/demographics', methods=['POST'])
def submit_demographics():
    data = request.json
    
    session_id = str(uuid.uuid4())
    assessment_id = str(uuid.uuid4())
    
    return jsonify({
        'success': True,
        'sessionId': session_id,
        'assessmentId': assessment_id,
        'message': 'Demographics saved'
    }), 201







# Load environment variables
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres.trwmfrwqjycwdafwirlx:Vanshita0108@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AIzaSyDlAoB7soQNbNviMEUfz3Rq2WFBSPZ-XHY')
FLASK_ENV = os.getenv('FLASK_ENV', 'development')
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
DEBUG = FLASK_ENV == 'development'

# Initialize Sentry error tracking
if SENTRY_ENABLED and SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[FlaskIntegration()],
        traces_sample_rate=0.1,
        debug=DEBUG,
        attach_stacktrace=True
    )

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
import uuid
from flask import g
from datetime import datetime

def generate_request_id():
    return str(uuid.uuid4())[:8]

def get_current_timestamp():
    return datetime.utcnow().isoformat() + 'Z'

@app.before_request
def setup_request_context():
    g.request_id = generate_request_id()
    g.start_time = datetime.utcnow()

def api_response(success=True, data=None, error=None, status_code=200):
    return jsonify({
        'success': success,
        'data': data,
        'error': error,
        'request_id': g.get('request_id', 'unknown'),
        'timestamp': get_current_timestamp(),
        'duration_ms': int((datetime.utcnow() - g.start_time).total_seconds() * 1000)
    }), status_code

app.config['SECRET_KEY'] = SECRET_KEY
app.config['JSON_SORT_KEYS'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = DEBUG

# Enable CORS
CORS(app, resources={
    r"/api/*": {
        "origins": ["*"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Caching
cache = Cache(app, config={
    'CACHE_TYPE': 'simple',
    'CACHE_DEFAULT_TIMEOUT': 300
})

# ==============================================================================
# DATABASE CONNECTION POOL
# ==============================================================================

class DatabasePool:
    """PostgreSQL connection pool manager."""
    
    def __init__(self, database_url: str, min_connections: int = 1, max_connections: int = 20):
        """Initialize connection pool."""
        self.pool = SimpleConnectionPool(min_connections, max_connections, database_url)
        logger.info(f"Database pool initialized: {min_connections}-{max_connections} connections")
    
    def get_connection(self):
        """Get connection from pool."""
        try:
            conn = self.pool.getconn()
            conn.autocommit = False
            return conn
        except Exception as e:
            logger.error(f"Failed to get database connection: {e}")
            raise
    
    def put_connection(self, conn):
        """Return connection to pool."""
        try:
            self.pool.putconn(conn)
        except Exception as e:
            logger.error(f"Failed to return connection to pool: {e}")
    
    def close_all(self):
        """Close all connections in pool."""
        self.pool.closeall()


# Initialize database pool
try:
    db_pool = DatabasePool(DATABASE_URL, min_connections=2, max_connections=20)
    logger.info("Database pool created successfully")
except Exception as e:
    logger.error(f"Failed to initialize database pool: {e}")
    raise

# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================

def get_db_connection():
    """Get database connection from pool."""
    if 'db' not in g:
        g.db = db_pool.get_connection()
    return g.db


def close_db_connection(e=None):
    """Close database connection."""
    db = g.pop('db', None)
    if db is not None:
        db_pool.put_connection(db)


app.teardown_appcontext(close_db_connection)


def generate_session_id() -> str:
    """Generate unique session ID."""
    return str(uuid.uuid4())


def generate_assessment_id() -> str:
    """Generate unique assessment ID."""
    return str(uuid.uuid4())


def hash_password(password: str) -> str:
    """Hash password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def get_current_timestamp() -> str:
    """Get current ISO format timestamp."""
    return datetime.utcnow().isoformat() + 'Z'


def safe_json_dumps(obj: Any) -> str:
    """Safely convert object to JSON string."""
    try:
        return json.dumps(obj, default=str)
    except Exception as e:
        logger.error(f"JSON serialization error: {e}")
        return "{}"


def extract_pagination_params() -> Tuple[int, int]:
    """Extract pagination parameters from request."""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        # Validate ranges
        page = max(1, min(page, 10000))
        limit = max(1, min(limit, 100))
        return page, limit
    except (ValueError, TypeError):
        return 1, 10


def log_request_info():
    """Log incoming request information."""
    logger.info(f"{request.method} {request.path} | "
                f"IP: {request.remote_addr} | "
                f"User-Agent: {request.headers.get('User-Agent', 'Unknown')}")


def log_response_info(response_data: Dict, status_code: int):
    """Log outgoing response information."""
    logger.info(f"Response: {status_code} | "
                f"Body size: {len(safe_json_dumps(response_data))} bytes")


# ==============================================================================
# DATA VALIDATION SCHEMAS
# ==============================================================================

class DemographicsSchema(Schema):
    """Validate demographic data."""
    
    age = fields.Int(required=True, validate=lambda x: 18 <= x <= 120)
    sex = fields.Str(required=True, validate=lambda x: x in ['M', 'F', 'NB', 'Other', 'Prefer not to answer'])
    country = fields.Str(required=True, validate=lambda x: len(x) >= 2)
    
    @pre_load
    def process_data(self, data, **kwargs):
        """Pre-process input data."""
        if isinstance(data, str):
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return data
        return data


class QuestionnaireResponseSchema(Schema):
    """Validate questionnaire responses."""
    
    session_id = fields.Str(required=True)
    responses = fields.Dict(required=True)
    completion_time = fields.Int(required=False)
    
    @pre_load
    def validate_responses(self, data, **kwargs):
        """Validate all 35 responses are provided."""
        responses = data.get('responses', {})
        
        # Check all 35 items present
        required_items = [f'{domain}{i}' for domain in ['R', 'S', 'C', 'A', 'O', 'E', 'V']
                         for i in range(1, 6)]
        
        for item in required_items:
            if item not in responses:
                raise ValidationError(f"Missing response for item {item}")
            
            try:
                value = int(responses[item])
                if not (0 <= value <= 10):
                    raise ValidationError(f"Response for {item} must be between 0 and 10")
            except (ValueError, TypeError):
                raise ValidationError(f"Invalid response value for {item}")
        
        return data


class ScoringResultsSchema(Schema):
    """Validate scoring results."""
    
    assessment_id = fields.Str(required=True)
    raw_scores = fields.Dict(required=True)
    corrected_scores = fields.Dict(required=True)
    validity_score = fields.Float(required=True)
    confidence_intervals = fields.Dict(required=True)


# ==============================================================================
# ERROR HANDLERS & MIDDLEWARE
# ==============================================================================

@app.before_request
def before_request():
    """Pre-request processing."""
    g.request_id = generate_session_id()
    g.start_time = datetime.utcnow()
    log_request_info()


@app.after_request
def after_request(response):
    """Post-request processing."""
    # Add security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net"
    response.headers['Request-ID'] = g.request_id
    
    # Log response
    try:
        response_data = json.loads(response.get_data(as_text=True))
    except:
        response_data = {}
    log_response_info(response_data, response.status_code)
    
    return response


@app.errorhandler(400)
def bad_request(error):
    """Handle 400 Bad Request."""
    logger.warning(f"Bad request: {error}")
    return jsonify({
        'success': False,
        'error': 'Bad request',
        'message': str(error),
        'request_id': g.get('request_id', 'unknown')
    }), 400


@app.errorhandler(401)
def unauthorized(error):
    """Handle 401 Unauthorized."""
    logger.warning(f"Unauthorized request: {error}")
    return jsonify({
        'success': False,
        'error': 'Unauthorized',
        'message': 'Authentication required',
        'request_id': g.get('request_id', 'unknown')
    }), 401


@app.errorhandler(403)
def forbidden(error):
    """Handle 403 Forbidden."""
    logger.warning(f"Forbidden request: {error}")
    return jsonify({
        'success': False,
        'error': 'Forbidden',
        'message': 'Access denied',
        'request_id': g.get('request_id', 'unknown')
    }), 403


@app.errorhandler(404)
def not_found(error):
    """Handle 404 Not Found."""
    logger.info(f"Resource not found: {request.path}")
    return jsonify({
        'success': False,
        'error': 'Not found',
        'message': f"Endpoint {request.path} not found",
        'request_id': g.get('request_id', 'unknown')
    }), 404


@app.errorhandler(429)
def rate_limit_handler(e):
    """Handle 429 Too Many Requests."""
    logger.warning(f"Rate limit exceeded: {request.remote_addr}")
    return jsonify({
        'success': False,
        'error': 'Rate limit exceeded',
        'message': 'Too many requests. Please try again later.',
        'request_id': g.get('request_id', 'unknown')
    }), 429


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 Internal Server Error."""
    logger.error(f"Internal server error: {error}", exc_info=True)
    
    # Send to Sentry if enabled
    if SENTRY_ENABLED:
        sentry_sdk.capture_exception(error)
    
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'message': 'An unexpected error occurred',
        'request_id': g.get('request_id', 'unknown')
    }), 500


# ==============================================================================
# AUTHENTICATION & AUTHORIZATION
# ==============================================================================

def require_auth(f):
    """Decorator to require authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing authorization header'}), 401
        
        token = auth_header.split(' ')[1]
        
        # Validate token (simple implementation)
        if not token or len(token) < 10:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401
        
        g.user_id = token  # In production, decode JWT
        return f(*args, **kwargs)
    
    return decorated_function


def require_session(f):
    """Decorator to require valid session ID."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_id = request.args.get('session_id') or request.json.get('session_id')
        
        if not session_id:
            return jsonify({'success': False, 'error': 'Missing session ID'}), 400
        
        # Validate session exists in database
        try:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute(
                "SELECT * FROM assessments WHERE session_id = %s",
                (session_id,)
            )
            assessment = cursor.fetchone()
            cursor.close()
            
            if not assessment:
                return jsonify({'success': False, 'error': 'Invalid session'}), 401
            
            g.session_id = session_id
            g.assessment = assessment
        except Exception as e:
            logger.error(f"Session validation error: {e}")
            return jsonify({'success': False, 'error': 'Session validation failed'}), 500
        
        return f(*args, **kwargs)
    
    return decorated_function


# ==============================================================================
# HEALTH CHECK ENDPOINT
# ==============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring."""
    try:
        # Test database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        
        return jsonify({
            'success': True,
            'status': 'healthy',
            'timestamp': get_current_timestamp(),
            'environment': FLASK_ENV,
            'database': 'connected',
            'request_id': g.get('request_id', 'unknown')
        }), 200
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': get_current_timestamp()
        }), 503


# ==============================================================================
# ASSESSMENT ENDPOINTS
# ==============================================================================

@app.route('/api/demographics', methods=['POST'])
@limiter.limit("10 per minute")
def submit_demographics():
    """
    Submit demographic information and create assessment session.
    
    Request body:
    {
        "age": 25,
        "sex": "M",
        "country": "United States"
    }
    
    Returns:
    {
        "success": true,
        "session_id": "uuid",
        "csrf_token": "token",
        "message": "Demographics stored successfully"
    }
    """
    try:
        # Parse and validate input
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
        
        # Validate schema
        schema = DemographicsSchema()
        try:
            validated_data = schema.load(data)
        except ValidationError as e:
            return jsonify({
                'success': False,
                'error': 'Validation error',
                'details': e.messages
            }), 400
        
        # Generate IDs
        session_id = generate_session_id()
        csrf_token = generate_session_id()[:32]
        
        # Store in database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """
                INSERT INTO assessments (session_id, age, sex, country, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING session_id
                """,
                (session_id, validated_data['age'], validated_data['sex'], 
                 validated_data['country'], 'started', get_current_timestamp())
            )
            
            conn.commit()
            result = cursor.fetchone()
            cursor.close()
            
            logger.info(f"Demographics submitted: session_id={session_id}")
            
            return jsonify({
                'success': True,
                'session_id': session_id,
                'csrf_token': csrf_token,
                'message': 'Demographics stored successfully',
                'request_id': g.get('request_id', 'unknown')
            }), 200
        
        except Exception as e:
            conn.rollback()
            cursor.close()
            logger.error(f"Database insert error: {e}")
            raise
    
    except Exception as e:
        logger.error(f"Error in submit_demographics: {e}", exc_info=True)
        if SENTRY_ENABLED:
            sentry_sdk.capture_exception(e)
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e) if DEBUG else 'An error occurred'
        }), 500


@app.route('/api/submit-responses', methods=['POST'])
@limiter.limit("10 per minute")
@require_session
def submit_questionnaire_responses():
    """
    Submit questionnaire responses (35 items) and trigger scoring pipeline.
    
    Request body:
    {
        "session_id": "uuid",
        "responses": {
            "R1": 8,
            "R2": 7,
            ...
            "V35": 5
        },
        "completion_time": 480
    }
    
    Returns:
    {
        "success": true,
        "assessment_id": "uuid",
        "status": "processing",
        "message": "Responses submitted successfully"
    }
    """
    try:
        data = request.get_json()
        
        # Validate schema
        schema = QuestionnaireResponseSchema()
        try:
            validated_data = schema.load(data)
        except ValidationError as e:
            return jsonify({
                'success': False,
                'error': 'Validation error',
                'details': e.messages
            }), 400
        
        session_id = g.session_id
        assessment_id = generate_assessment_id()
        
        # Store responses in database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Store assessment
            cursor.execute(
                """
                INSERT INTO assessments (
                    assessment_id, session_id, responses, completion_time, 
                    status, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (assessment_id, session_id, safe_json_dumps(validated_data['responses']),
                 validated_data.get('completion_time', 0), 'processing', get_current_timestamp())
            )
            
            # Store individual responses
            for item_id, score in validated_data['responses'].items():
                cursor.execute(
                    """
                    INSERT INTO responses (assessment_id, item_id, score, created_at)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (assessment_id, item_id, score, get_current_timestamp())
                )
            
            conn.commit()
            cursor.close()
            
            logger.info(f"Questionnaire responses submitted: assessment_id={assessment_id}")
            
            return jsonify({
                'success': True,
                'assessment_id': assessment_id,
                'status': 'processing',
                'message': 'Responses submitted successfully. Processing assessment...',
                'request_id': g.get('request_id', 'unknown')
            }), 202
        
        except Exception as e:
            conn.rollback()
            cursor.close()
            logger.error(f"Database error in submit_questionnaire_responses: {e}")
            raise
    
    except Exception as e:
        logger.error(f"Error in submit_questionnaire_responses: {e}", exc_info=True)
        if SENTRY_ENABLED:
            sentry_sdk.capture_exception(e)
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@app.route('/api/calculate-scores', methods=['POST'])
@limiter.limit("20 per minute")
def calculate_scores():
    """
    Calculate personality scores using 7-step pipeline.
    
    Request body:
    {
        "assessment_id": "uuid"
    }
    
    Returns:
    {
        "success": true,
        "raw_scores": {...},
        "corrected_scores": {...},
        "validity_score": 0.85,
        "confidence_intervals": {...},
        "deception_parameters": {...}
    }
    """
    try:
        data = request.get_json()
        assessment_id = data.get('assessment_id')
        
        if not assessment_id:
            return jsonify({'success': False, 'error': 'Missing assessment_id'}), 400
        
        # Retrieve responses from database
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute(
                "SELECT item_id, score FROM responses WHERE assessment_id = %s",
                (assessment_id,)
            )
            response_records = cursor.fetchall()
            
            if not response_records:
                cursor.close()
                return jsonify({'success': False, 'error': 'Assessment not found'}), 404
            
            # Convert to dictionary
            responses = {r['item_id']: r['score'] for r in response_records}
            
            # Step 1: Calculate raw domain scores
            raw_scores = calculate_raw_scores(responses)
            
            # Step 2: Assess response validity
            validity_score = assess_response_validity(responses)
            
            # Step 3: Calculate deception susceptibility
            lambda_param = calculate_deception_susceptibility(responses, raw_scores)
            
            # Step 4: Calculate domain-specific deception pressure
            delta_values = get_delta_values()
            
            # Step 5: Apply deception correction
            corrected_scores = apply_deception_correction(raw_scores, lambda_param, delta_values)
            
            # Step 6: Prepare VAE input
            vae_input = prepare_vae_input(corrected_scores, lambda_param, validity_score)
            
            # Step 7: Calculate confidence intervals
            confidence_intervals = calculate_confidence_intervals(raw_scores, corrected_scores, validity_score)
            
            # Store results
            cursor.execute(
                """
                INSERT INTO scoring_results (
                    assessment_id, raw_scores, corrected_scores, validity_score,
                    deception_lambda, delta_values, confidence_intervals, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (assessment_id, safe_json_dumps(raw_scores), safe_json_dumps(corrected_scores),
                 validity_score, lambda_param, safe_json_dumps(delta_values),
                 safe_json_dumps(confidence_intervals), get_current_timestamp())
            )
            
            # Store VAE input for next step
            cursor.execute(
                """
                INSERT INTO vae_inputs (assessment_id, input_vector, created_at)
                VALUES (%s, %s, %s)
                """,
                (assessment_id, safe_json_dumps(vae_input), get_current_timestamp())
            )
            
            conn.commit()
            cursor.close()
            
            logger.info(f"Scores calculated: assessment_id={assessment_id}, validity={validity_score:.2f}")
            
            return jsonify({
                'success': True,
                'assessment_id': assessment_id,
                'raw_scores': raw_scores,
                'corrected_scores': corrected_scores,
                'validity_score': validity_score,
                'confidence_intervals': confidence_intervals,
                'deception_parameters': {
                    'lambda': lambda_param,
                    'delta_values': delta_values
                },
                'request_id': g.get('request_id', 'unknown')
            }), 200
        
        except Exception as e:
            conn.rollback()
            cursor.close()
            logger.error(f"Error in calculate_scores: {e}")
            raise
    
    except Exception as e:
        logger.error(f"Error in calculate_scores: {e}", exc_info=True)
        if SENTRY_ENABLED:
            sentry_sdk.capture_exception(e)
        return jsonify({
            'success': False,
            'error': 'Scoring calculation failed'
        }), 500


@app.route('/api/run-vae', methods=['POST'])
@limiter.limit("20 per minute")
def run_vae_inference():
    """
    Run VAE inference for personality classification.
    
    Request body:
    {
        "assessment_id": "uuid"
    }
    
    Returns:
    {
        "success": true,
        "primary_type": "Ambitious Explorer",
        "confidence": 0.68,
        "anomaly_score": 0.23,
        "personality_blend": {...}
    }
    """
    try:
        data = request.get_json()
        assessment_id = data.get('assessment_id')
        
        if not assessment_id:
            return jsonify({'success': False, 'error': 'Missing assessment_id'}), 400
        
        # Retrieve VAE input from database
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute(
                "SELECT input_vector FROM vae_inputs WHERE assessment_id = %s",
                (assessment_id,)
            )
            vae_record = cursor.fetchone()
            
            if not vae_record:
                cursor.close()
                return jsonify({'success': False, 'error': 'VAE input not found'}), 404
            
            vae_input = json.loads(vae_record['input_vector'])
            
            # Run VAE inference
            classification = run_vae_classification(vae_input)
            
            # Store VAE results
            cursor.execute(
                """
                INSERT INTO vae_outputs (
                    assessment_id, latent_vector, anomaly_score,
                    primary_type, primary_confidence, type_blend, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (assessment_id, safe_json_dumps(classification['latent_vector']),
                 classification['anomaly_score'], classification['primary_type'],
                 classification['primary_confidence'], safe_json_dumps(classification['type_blend']),
                 get_current_timestamp())
            )
            
            conn.commit()
            cursor.close()
            
            logger.info(f"VAE inference complete: assessment_id={assessment_id}, "
                       f"type={classification['primary_type']}")
            
            return jsonify({
                'success': True,
                'assessment_id': assessment_id,
                'primary_type': classification['primary_type'],
                'primary_confidence': classification['primary_confidence'],
                'secondary_type': classification.get('secondary_type', ''),
                'secondary_confidence': classification.get('secondary_confidence', 0),
                'anomaly_score': classification['anomaly_score'],
                'is_anomalous': classification['anomaly_score'] > 0.7,
                'personality_blend': classification['type_blend'],
                'descriptors': classification.get('descriptors', []),
                'request_id': g.get('request_id', 'unknown')
            }), 200
        
        except Exception as e:
            conn.rollback()
            cursor.close()
            logger.error(f"Error in run_vae_inference: {e}")
            raise
    
    except Exception as e:
        logger.error(f"Error in run_vae_inference: {e}", exc_info=True)
        if SENTRY_ENABLED:
            sentry_sdk.capture_exception(e)
        return jsonify({
            'success': False,
            'error': 'VAE inference failed'
        }), 500


@app.route('/api/generate-narrative', methods=['POST'])
@limiter.limit("20 per minute")
def generate_narrative():
    """
    Generate AI-powered personality narrative.
    
    Request body:
    {
        "assessment_id": "uuid"
    }
    
    Returns:
    {
        "success": true,
        "narrative": "Your personality narrative...",
        "word_count": 437,
        "api_used": "gemini-pro",
        "tokens_used": 150
    }
    """
    try:
        data = request.get_json()
        assessment_id = data.get('assessment_id')
        
        if not assessment_id:
            return jsonify({'success': False, 'error': 'Missing assessment_id'}), 400
        
        # Retrieve assessment data
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Get scoring results
            cursor.execute(
                "SELECT * FROM scoring_results WHERE assessment_id = %s",
                (assessment_id,)
            )
            scoring_results = cursor.fetchone()
            
            # Get VAE classification
            cursor.execute(
                "SELECT * FROM vae_outputs WHERE assessment_id = %s",
                (assessment_id,)
            )
            vae_results = cursor.fetchone()
            
            if not scoring_results or not vae_results:
                cursor.close()
                return jsonify({'success': False, 'error': 'Assessment data not found'}), 404
            
            # Build context for narrative generation
            narrative_context = {
                'personality_type': vae_results['primary_type'],
                'confidence': vae_results['primary_confidence'],
                'raw_scores': json.loads(scoring_results['raw_scores']),
                'corrected_scores': json.loads(scoring_results['corrected_scores']),
                'anomaly_score': vae_results['anomaly_score'],
                'type_blend': json.loads(vae_results['type_blend'])
            }
            
            # Generate narrative
            narrative_data = generate_personality_narrative(narrative_context)
            
            # Store narrative
            cursor.execute(
                """
                INSERT INTO narratives (
                    assessment_id, narrative_text, word_count,
                    api_used, tokens_used, quality_score, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (assessment_id, narrative_data['narrative'], narrative_data['word_count'],
                 narrative_data['api_used'], narrative_data.get('tokens_used', 0),
                 narrative_data.get('quality_score', 0.8), get_current_timestamp())
            )
            
            # Mark assessment as complete
            cursor.execute(
                """
                UPDATE assessments SET status = %s, completed_at = %s
                WHERE assessment_id = %s
                """,
                ('completed', get_current_timestamp(), assessment_id)
            )
            
            conn.commit()
            cursor.close()
            
            logger.info(f"Narrative generated: assessment_id={assessment_id}")
            
            return jsonify({
                'success': True,
                'assessment_id': assessment_id,
                'narrative': narrative_data['narrative'],
                'word_count': narrative_data['word_count'],
                'api_used': narrative_data['api_used'],
                'tokens_used': narrative_data.get('tokens_used', 0),
                'quality_score': narrative_data.get('quality_score', 0.8),
                'request_id': g.get('request_id', 'unknown')
            }), 200
        
        except Exception as e:
            conn.rollback()
            cursor.close()
            logger.error(f"Error in generate_narrative: {e}")
            raise
    
    except Exception as e:
        logger.error(f"Error in generate_narrative: {e}", exc_info=True)
        if SENTRY_ENABLED:
            sentry_sdk.capture_exception(e)
        return jsonify({
            'success': False,
            'error': 'Narrative generation failed'
        }), 500


@app.route('/api/results/<assessment_id>', methods=['GET'])
@limiter.limit("30 per minute")
def get_results(assessment_id):
    """
    Retrieve complete assessment results.
    
    URL params:
    - assessment_id: UUID of assessment
    
    Returns:
    {
        "success": true,
        "assessment": {...},
        "demographics": {...},
        "raw_scores": {...},
        "corrected_scores": {...},
        "personality_type": "...",
        "narrative": "...",
        "confidence_intervals": {...}
    }
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Get assessment
            cursor.execute(
                "SELECT * FROM assessments WHERE assessment_id = %s",
                (assessment_id,)
            )
            assessment = cursor.fetchone()
            
            if not assessment:
                cursor.close()
                return jsonify({'success': False, 'error': 'Assessment not found'}), 404
            
            # Get scoring results
            cursor.execute(
                "SELECT * FROM scoring_results WHERE assessment_id = %s",
                (assessment_id,)
            )
            scoring = cursor.fetchone()
            
            # Get VAE results
            cursor.execute(
                "SELECT * FROM vae_outputs WHERE assessment_id = %s",
                (assessment_id,)
            )
            vae = cursor.fetchone()
            
            # Get narrative
            cursor.execute(
                "SELECT * FROM narratives WHERE assessment_id = %s",
                (assessment_id,)
            )
            narrative = cursor.fetchone()
            
            cursor.close()
            
            # Build response
            result = {
                'success': True,
                'assessment_id': assessment_id,
                'status': assessment['status'],
                'demographics': {
                    'age': assessment['age'],
                    'sex': assessment['sex'],
                    'country': assessment['country']
                },
                'created_at': assessment['created_at']
            }
            
            if scoring:
                result['raw_scores'] = json.loads(scoring['raw_scores'])
                result['corrected_scores'] = json.loads(scoring['corrected_scores'])
                result['validity_score'] = scoring['validity_score']
                result['confidence_intervals'] = json.loads(scoring['confidence_intervals'])
                result['deception_lambda'] = scoring['deception_lambda']
            
            if vae:
                result['personality_type'] = vae['primary_type']
                result['confidence'] = vae['primary_confidence']
                result['anomaly_score'] = vae['anomaly_score']
                result['type_blend'] = json.loads(vae['type_blend'])
            
            if narrative:
                result['narrative'] = narrative['narrative_text']
                result['narrative_metadata'] = {
                    'word_count': narrative['word_count'],
                    'api_used': narrative['api_used'],
                    'generated_at': narrative['created_at']
                }
            
            return jsonify(result), 200
        
        except Exception as e:
            cursor.close()
            logger.error(f"Error in get_results: {e}")
            raise
    
    except Exception as e:
        logger.error(f"Error in get_results: {e}", exc_info=True)
        if SENTRY_ENABLED:
            sentry_sdk.capture_exception(e)
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve results'
        }), 500


@app.route('/api/export-pdf/<assessment_id>', methods=['GET'])
@limiter.limit("10 per minute")
def export_pdf(assessment_id):
    """
    Export assessment results as PDF.
    
    Returns: PDF file
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Retrieve all assessment data
            cursor.execute(
                "SELECT * FROM assessments WHERE assessment_id = %s",
                (assessment_id,)
            )
            assessment = cursor.fetchone()
            
            if not assessment:
                cursor.close()
                return jsonify({'success': False, 'error': 'Assessment not found'}), 404
            
            # Get other data
            cursor.execute("SELECT * FROM scoring_results WHERE assessment_id = %s", (assessment_id,))
            scoring = cursor.fetchone()
            
            cursor.execute("SELECT * FROM vae_outputs WHERE assessment_id = %s", (assessment_id,))
            vae = cursor.fetchone()
            
            cursor.execute("SELECT * FROM narratives WHERE assessment_id = %s", (assessment_id,))
            narrative = cursor.fetchone()
            
            cursor.close()
            
            # Generate PDF
            pdf_buffer = BytesIO()
            pdf = SimpleDocTemplate(pdf_buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
            
            # Build PDF content
            elements = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#2C5282'),
                spaceAfter=30,
                alignment=1
            )
            elements.append(Paragraph("EFOPA Personality Assessment Results", title_style))
            elements.append(Spacer(1, 12))
            
            # Demographics
            demo_data = [
                ['Age', str(assessment['age'])],
                ['Sex', assessment['sex']],
                ['Country', assessment['country']],
                ['Assessment Date', assessment['created_at']]
            ]
            demo_table = Table(demo_data, colWidths=[2*inch, 4*inch])
            demo_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E2E8F0')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey)
            ]))
            elements.append(demo_table)
            elements.append(Spacer(1, 20))
            
            # Personality Type
            elements.append(Paragraph("Personality Profile", styles['Heading2']))
            if vae:
                elements.append(Paragraph(
                    f"<b>Personality Type:</b> {vae['primary_type']}<br/>"
                    f"<b>Confidence:</b> {vae['primary_confidence']:.0%}",
                    styles['Normal']
                ))
                elements.append(Spacer(1, 12))
            
            # Domain Scores
            elements.append(Paragraph("Domain Scores", styles['Heading2']))
            if scoring:
                raw = json.loads(scoring['raw_scores'])
                corrected = json.loads(scoring['corrected_scores'])
                
                score_data = [['Domain', 'Raw Score', 'Corrected Score']]
                for domain in ['R', 'S', 'C', 'A', 'O', 'E']:
                    score_data.append([
                        domain,
                        f"{raw.get(domain, 0):.1f}",
                        f"{corrected.get(domain, 0):.1f}"
                    ])
                
                score_table = Table(score_data, colWidths=[2*inch, 2*inch, 2*inch])
                score_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667EEA')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey)
                ]))
                elements.append(score_table)
                elements.append(Spacer(1, 20))
            
            # Narrative
            if narrative:
                elements.append(Paragraph("Personality Narrative", styles['Heading2']))
                elements.append(Paragraph(narrative['narrative_text'], styles['Normal']))
            
            # Footer
            elements.append(Spacer(1, 20))
            elements.append(Paragraph(
                f"<i>Generated on {get_current_timestamp()} | Assessment ID: {assessment_id}</i>",
                styles['Normal']
            ))
            
            # Build PDF
            pdf.build(elements)
            pdf_buffer.seek(0)
            
            logger.info(f"PDF exported: assessment_id={assessment_id}")
            
            return send_file(
                pdf_buffer,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f'efopa-results-{assessment_id[:8]}.pdf'
            )
        
        except Exception as e:
            cursor.close()
            logger.error(f"PDF generation error: {e}")
            raise
    
    except Exception as e:
        logger.error(f"Error in export_pdf: {e}", exc_info=True)
        if SENTRY_ENABLED:
            sentry_sdk.capture_exception(e)
        return jsonify({
            'success': False,
            'error': 'PDF export failed'
        }), 500


# ==============================================================================
# SCORING PIPELINE FUNCTIONS
# ==============================================================================

def calculate_raw_scores(responses: Dict[str, int]) -> Dict[str, float]:
    """Calculate raw domain scores (average of 5 items per domain, 0-100 scale)."""
    domains = {
        'R': ['R1', 'R2', 'R3', 'R4', 'R5'],
        'S': ['S6', 'S7', 'S8', 'S9', 'S10'],
        'C': ['C11', 'C12', 'C13', 'C14', 'C15'],
        'A': ['A16', 'A17', 'A18', 'A19', 'A20'],
        'O': ['O21', 'O22', 'O23', 'O24', 'O25'],
        'E': ['E26', 'E27', 'E28', 'E29', 'E30']
    }
    
    raw_scores = {}
    for domain, items in domains.items():
        values = [responses.get(item, 5) for item in items]
        average = sum(values) / len(values)
        raw_scores[domain] = round(average * 10, 2)  # Scale to 0-100
    
    return raw_scores


def assess_response_validity(responses: Dict[str, int]) -> float:
    """
    Assess validity of responses using consistency checks.
    Returns validity score 0-1, where 1 = highly valid.
    """
    # Check for response variance
    all_values = list(responses.values())
    if len(set(all_values)) < 3:
        return 0.40  # Low variance = suspicious
    
    # Check for extreme consistency
    valid_items = [v for k, v in responses.items() if not k.startswith('V')]
    validity_items = [v for k, v in responses.items() if k.startswith('V')]
    
    # Calculate entropy (randomness)
    from collections import Counter
    counter = Counter(all_values)
    entropy = sum(-(count/len(all_values)) * (count/len(all_values)) 
                 for count in counter.values())
    
    # Normalize entropy to 0-1 scale
    max_entropy = 2.3  # log2(10) for uniform distribution across 0-10
    normalized_entropy = min(entropy / max_entropy, 1.0)
    
    return round(normalized_entropy, 2)


def calculate_deception_susceptibility(responses: Dict[str, int], raw_scores: Dict[str, float]) -> float:
    """
    Estimate individual deception susceptibility (Lambda parameter).
    Range: 0.3 to 2.0, where 1.0 is baseline.
    """
    # Check for contradictions in responses
    contradiction_count = 0
    
    # Example: High Status claims but low Conscientiousness
    if raw_scores.get('S', 0) > 75 and raw_scores.get('C', 0) < 40:
        contradiction_count += 1
    
    # High Agreeableness but low Emotional Stability
    if raw_scores.get('A', 0) > 75 and raw_scores.get('E', 0) < 35:
        contradiction_count += 1
    
    # Validity check
    validity = assess_response_validity(responses)
    
    # Calculate Lambda
    lambda_base = 1.0
    lambda_contradictions = 0.15 * contradiction_count
    lambda_validity = 0.3 * (1.0 - validity)
    
    lambda_param = lambda_base + lambda_contradictions + lambda_validity
    
    # Clamp to valid range
    return round(max(0.3, min(lambda_param, 2.0)), 2)


def get_delta_values() -> Dict[str, float]:
    """Get domain-specific deception pressure values."""
    return {
        'R': 0.88,  # Highest - mating context
        'S': 0.82,  # Very High - status is valuable
        'E': 0.75,  # High - emotional suppression
        'C': 0.68,  # Moderate - reliability valued
        'A': 0.62,  # Moderate - social harmony
        'O': 0.58   # Moderate-Low - openness less pressured
    }


def apply_deception_correction(raw_scores: Dict[str, float], 
                              lambda_param: float, 
                              delta_values: Dict[str, float]) -> Dict[str, float]:
    """Apply deception correction: Corrected = Raw / (1 + Lambda * Delta)."""
    corrected_scores = {}
    
    for domain, raw_score in raw_scores.items():
        delta = delta_values.get(domain, 0.70)
        denominator = 1.0 + (lambda_param * delta)
        
        if denominator > 0:
            corrected = raw_score / denominator
        else:
            corrected = raw_score
        
        # Scale corrected scores to 0-5 range (1-5 for interpretation)
        corrected_scaled = 1 + (corrected / 100.0) * 4  # 1-5 scale
        corrected_scores[domain] = round(corrected_scaled, 2)
    
    return corrected_scores


def prepare_vae_input(corrected_scores: Dict[str, float], 
                     lambda_param: float, 
                     validity_score: float) -> List[float]:
    """Prepare 9D vector for VAE inference."""
    # 6 corrected traits (normalized 0-1)
    traits = [
        corrected_scores.get('R', 0) / 5.0,
        corrected_scores.get('S', 0) / 5.0,
        corrected_scores.get('C', 0) / 5.0,
        corrected_scores.get('A', 0) / 5.0,
        corrected_scores.get('O', 0) / 5.0,
        corrected_scores.get('E', 0) / 5.0,
    ]
    
    # Add additional inputs
    vae_input = traits + [validity_score, lambda_param / 2.0, 0.5]  # Last is personality diversity
    
    return vae_input


def calculate_confidence_intervals(raw_scores: Dict[str, float],
                                  corrected_scores: Dict[str, float],
                                  validity_score: float) -> Dict[str, Dict[str, float]]:
    """Calculate 80% and 95% confidence intervals."""
    ci = {}
    
    for domain in raw_scores.keys():
        raw = raw_scores[domain]
        corrected = corrected_scores[domain]
        
        # Confidence interval width depends on validity
        ci_width_raw = 5 + (1 - validity_score) * 25
        ci_width_corrected = 0.5 + (1 - validity_score) * 2.5
        
        ci[domain] = {
            'raw_80': {'lower': raw - ci_width_raw/2, 'upper': raw + ci_width_raw/2},
            'raw_95': {'lower': raw - ci_width_raw, 'upper': raw + ci_width_raw},
            'corrected_80': {'lower': corrected - ci_width_corrected/2, 'upper': corrected + ci_width_corrected/2},
            'corrected_95': {'lower': corrected - ci_width_corrected, 'upper': corrected + ci_width_corrected}
        }
    
    return ci


# ==============================================================================
# VAE CLASSIFICATION FUNCTION
# ==============================================================================

def run_vae_classification(vae_input: List[float]) -> Dict[str, Any]:
    """
    Run VAE inference and personality classification.
    Returns classification results.
    """
    # Personality type clusters (6 types)
    personality_types = [
        'Ambitious Explorer',
        'Reliable Provider',
        'Creative Visionary',
        'Natural Leader',
        'Harmonious Supporter',
        'Wise Analyst'
    ]
    
    # Simple classification based on trait scores
    # In production, use actual VAE model
    R, S, C, A, O, E = vae_input[:6]
    
    # Determine primary type based on highest trait
    traits = {'R': R, 'S': S, 'C': C, 'A': A, 'O': O, 'E': E}
    sorted_traits = sorted(traits.items(), key=lambda x: x[1], reverse=True)
    
    # Map traits to personality types
    type_mapping = {
        ('S', 'R'): 'Ambitious Explorer',
        ('S', 'E'): 'Natural Leader',
        ('C', 'A'): 'Reliable Provider',
        ('O', 'R'): 'Creative Visionary',
        ('A', 'C'): 'Harmonious Supporter',
        ('E', 'O'): 'Wise Analyst'
    }
    
    top_traits = tuple(sorted_traits[0][0] for _ in range(1))
    primary_type = type_mapping.get(top_traits, personality_types[0])
    
    # Calculate anomaly score
    anomaly_score = abs(sum(vae_input) - 3.0) / 3.0  # Simplified
    anomaly_score = round(min(anomaly_score, 1.0), 2)
    
    # Type blend probabilities
    type_blend = {ptype: round(max(0, 0.1 + (0.2 * (i == 0) + 0.1 * (i < 3))), 2) 
                 for i, ptype in enumerate(personality_types)}
    type_blend[primary_type] = round(max(type_blend[primary_type], 0.6), 2)
    
    # Normalize probabilities
    total = sum(type_blend.values())
    type_blend = {k: v/total for k, v in type_blend.items()}
    
    return {
        'latent_vector': [round(x, 3) for x in vae_input[:3]],
        'primary_type': primary_type,
        'primary_confidence': round(type_blend[primary_type], 2),
        'secondary_type': personality_types[1],
        'secondary_confidence': round(list(type_blend.values())[1], 2),
        'anomaly_score': anomaly_score,
        'type_blend': type_blend,
        'descriptors': ['Driven', 'Ambitious', 'Curious', 'Reliable', 'Empathetic']
    }


# ==============================================================================
# NARRATIVE GENERATION FUNCTION
# ==============================================================================

def generate_personality_narrative(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate AI-powered personality narrative using LLM.
    Uses Gemini API or fallback.
    """
    try:
        narrative = generate_gemini_narrative(context)
        return {
            'narrative': narrative['text'],
            'word_count': len(narrative['text'].split()),
            'api_used': 'gemini-pro',
            'tokens_used': narrative.get('tokens', 0),
            'quality_score': 0.9
        }
    except Exception as e:
        logger.warning(f"Gemini API failed: {e}, using fallback")
        return generate_fallback_narrative(context)


def generate_gemini_narrative(context: Dict[str, Any]) -> Dict[str, Any]:
    """Generate narrative using Google Gemini API."""
    try:
        import google.generativeai as genai
        
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set")
        
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-pro')
        
        # Build prompt
        prompt = f"""
        You are an expert psychologist analyzing personality assessment results.
        
        Personality Type: {context.get('personality_type', 'Unknown')}
        Confidence: {context.get('confidence', 0):.0%}
        
        Trait Scores (Corrected):
        - Relationships/Mating: {context.get('corrected_scores', {}).get('R', 0):.1f}
        - Status/Confidence: {context.get('corrected_scores', {}).get('S', 0):.1f}
        - Conscientiousness: {context.get('corrected_scores', {}).get('C', 0):.1f}
        - Agreeableness: {context.get('corrected_scores', {}).get('A', 0):.1f}
        - Openness: {context.get('corrected_scores', {}).get('O', 0):.1f}
        - Emotional Stability: {context.get('corrected_scores', {}).get('E', 0):.1f}
        
        Please write a detailed personality narrative (350-500 words) that:
        1. Addresses the person in second person ("You are...")
        2. Explains key personality traits
        3. Provides actionable life insights
        4. Suggests 2-3 areas for personal growth
        5. Is warm, empowering, and non-judgmental
        
        Write only the narrative, no meta-commentary.
        """
        
        response = model.generate_content(prompt)
        
        narrative_text = response.text
        
        return {
            'text': narrative_text,
            'tokens': len(narrative_text.split()) * 1.3  # Rough estimate
        }
    
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        raise


def generate_fallback_narrative(context: Dict[str, Any]) -> Dict[str, Any]:
    """Generate rule-based personality narrative fallback."""
    ptype = context.get('personality_type', 'Unique Individual')
    
    narrative = f"""
    You are a {ptype}, characterized by a distinctive blend of personality traits that 
    make you uniquely suited for specific life paths and challenges.
    
    Your personality profile reveals strong patterns across multiple dimensions:
    
    Your Relationship Style: You approach romantic and social connections with deliberation 
    and care. Your authenticity in personal relationships is a significant strength, allowing 
    you to build deep, meaningful connections with others.
    
    Your Status and Confidence: You maintain a realistic view of your strengths while 
    remaining open to growth. This balanced perspective helps you navigate competitive 
    situations without overextending or underselling yourself.
    
    Your Conscientiousness: Your follow-through on commitments is notable, making you 
    a reliable presence in both professional and personal contexts. You take your 
    responsibilities seriously and deliver quality work.
    
    Your Agreeableness: You balance cooperation with healthy boundaries. Your ability 
    to work well with others while maintaining your own perspective makes you a valued 
    team member and friend.
    
    Your Openness: You maintain intellectual curiosity while being grounded in practical 
    reality. This combination allows you to learn from diverse experiences without becoming 
    overwhelmed by possibilities.
    
    Your Emotional Stability: You navigate life's challenges with resilience, maintaining 
    perspective even during difficult times. Your emotional awareness is a strength that 
    helps you manage stress effectively.
    
    Areas for Growth: Consider exploring deeper self-reflection in your weaker domains. 
    Seek diverse experiences that challenge your perspectives. Develop patience with areas 
    outside your natural strengths.
    
    Your Path Forward: Leverage your natural strengths while being intentional about 
    developing balance across all personality dimensions. Your authentic self is your greatest asset.
    """
    
    return {
        'narrative': narrative,
        'word_count': len(narrative.split()),
        'api_used': 'fallback',
        'tokens_used': 0,
        'quality_score': 0.7
    }


# ==============================================================================
# ANALYTICS & REPORTING ENDPOINTS
# ==============================================================================

@app.route('/api/history', methods=['GET'])
@limiter.limit("20 per minute")
def get_user_history():
    """
    Retrieve user's assessment history.
    Query params: user_id, limit, offset
    """
    try:
        user_id = request.args.get('user_id')
        page, limit = extract_pagination_params()
        offset = (page - 1) * limit
        
        if not user_id:
            return jsonify({'success': False, 'error': 'Missing user_id'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute(
                """
                SELECT assessment_id, created_at, age, sex, country, status
                FROM assessments
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                (user_id, limit, offset)
            )
            
            assessments = cursor.fetchall()
            
            # Get total count
            cursor.execute("SELECT COUNT(*) as count FROM assessments WHERE user_id = %s", (user_id,))
            total = cursor.fetchone()['count']
            
            cursor.close()
            
            return jsonify({
                'success': True,
                'assessments': assessments,
                'total': total,
                'page': page,
                'limit': limit
            }), 200
        
        except Exception as e:
            cursor.close()
            logger.error(f"Error in get_user_history: {e}")
            raise
    
    except Exception as e:
        logger.error(f"Error in get_user_history: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to retrieve history'}), 500


@app.route('/api/stats', methods=['GET'])
@limiter.limit("10 per minute")
def get_statistics():
    """Get platform statistics."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Total assessments
            cursor.execute("SELECT COUNT(*) as count FROM assessments")
            total_assessments = cursor.fetchone()['count']
            
            # Completed assessments
            cursor.execute("SELECT COUNT(*) as count FROM assessments WHERE status = 'completed'")
            completed = cursor.fetchone()['count']
            
            # Average validity
            cursor.execute("SELECT AVG(validity_score) as avg_validity FROM scoring_results")
            avg_validity = cursor.fetchone()['avg_validity'] or 0
            
            cursor.close()
            
            return jsonify({
                'success': True,
                'total_assessments': total_assessments,
                'completed_assessments': completed,
                'completion_rate': round(completed / max(total_assessments, 1) * 100, 2),
                'average_validity': round(avg_validity, 3),
                'timestamp': get_current_timestamp()
            }), 200
        
        except Exception as e:
            cursor.close()
            logger.error(f"Error in get_statistics: {e}")
            raise
    
    except Exception as e:
        logger.error(f"Error in get_statistics: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to retrieve statistics'}), 500


# ==============================================================================
# INITIALIZATION & STARTUP
# ==============================================================================


def initialize_database():
    """Initialize database schema on first request."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Read and execute schema
        with open('migrations/schema.sql', 'r') as f:
            schema = f.read()
            # Execute schema
            cursor.execute(schema)
        
        conn.commit()
        cursor.close()
        
        logger.info("Database schema initialized")
    
    except FileNotFoundError:
        logger.warning("Schema file not found, skipping initialization")
    except Exception as e:
        logger.warning(f"Database initialization: {e}")


def create_app():
    """Application factory function."""
    logger.info("EFOPA Platform initialized")
    logger.info(f"Environment: {FLASK_ENV}")
    logger.info(f"Debug mode: {DEBUG}")
    return app


# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================

if __name__ == '__main__':
    port = int(os.getenv('PORT', 7860))
    
    logger.info(f"Starting Flask server on port {port}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=DEBUG,
        use_reloader=False,  # Disable in production
        threaded=True
    )
