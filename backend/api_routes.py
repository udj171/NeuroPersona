# ============================================================================
# SCRIPT 7: api_routes.py - REST API Endpoints
# ============================================================================

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import desc, func
import logging
from datetime import datetime, timezone
import uuid
import traceback
from models import db, User, Assessment, Result, VAEOutput, PersonalityClassification, GeminiInterpretation


# These will be injected by app.py
api_bp = Blueprint('api', __name__)
logger = logging.getLogger(__name__)

scoring_engine = None
vae_engine = None
gemini_client = None

def set_engines(scoring, vae, gemini):
    """Set engine references from app.py"""
    global scoring_engine, vae_engine, gemini_client
    scoring_engine = scoring
    vae_engine = vae
    gemini_client = gemini
    logger.info("[API_ROUTES] Engines configured:")
    logger.info(f"  - ScoringEngine: {'Ready' if scoring else 'None'}")
    logger.info(f"  - VAEInferenceEngine: {'Ready' if vae else 'None'}")
    logger.info(f"  - GeminiClient: {'Ready' if gemini else 'None'}")


@api_bp.before_request
def log_request():
    logger.info(f'{request.method} {request.path} from {request.remote_addr}')


@api_bp.route('/health', methods=['GET', 'HEAD'])
def health_check():
    """
    SIMPLIFIED HEALTH CHECK
    Returns 200 immediately without database queries.
    Frontend wake-up call can use this to detect when backend is responsive.
    """
    try:
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'service': 'personality-assessment-api',
            'version': '1.0.0',
        }), 200
    except Exception as e:
        logger.error(f'[HEALTH] Unexpected error: {str(e)}')
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }), 500


@api_bp.route('/start-assessment', methods=['POST'])
def start_assessment():
    """Start a new assessment session"""
    try:
        # Parse JSON request
        data = request.get_json(force=True, silent=True)
        
        if data is None:
            logger.warning('[START_ASSESSMENT] No JSON body received')
            return jsonify({
                'status': 'error',
                'message': 'Request body must be valid JSON',
                'code': 'INVALID_JSON'
            }), 400
        
        # Extract and validate fields
        age = data.get('age')
        sex = data.get('sex')
        
        logger.info(f'[START_ASSESSMENT] Received: age={age}, sex={sex}')
        
        # Validate age
        if age is None:
            logger.warning('[START_ASSESSMENT] Missing age field')
            return jsonify({
                'status': 'error',
                'message': 'Missing required field: age',
                'code': 'MISSING_AGE'
            }), 400
        
        if not isinstance(age, (int, float)):
            logger.warning(f'[START_ASSESSMENT] Invalid age type: {type(age)}')
            return jsonify({
                'status': 'error',
                'message': 'Age must be a number',
                'code': 'INVALID_AGE_TYPE'
            }), 400
        
        age = int(age)
        if age < 13 or age > 120:
            logger.warning(f'[START_ASSESSMENT] Age out of range: {age}')
            return jsonify({
                'status': 'error',
                'message': 'Age must be between 13 and 120',
                'code': 'AGE_OUT_OF_RANGE'
            }), 400
        
        # Validate sex
        if sex is None:
            logger.warning('[START_ASSESSMENT] Missing sex field')
            return jsonify({
                'status': 'error',
                'message': 'Missing required field: sex',
                'code': 'MISSING_SEX'
            }), 400
        
        if sex not in ['M', 'F', 'O']:
            logger.warning(f'[START_ASSESSMENT] Invalid sex value: {sex}')
            return jsonify({
                'status': 'error',
                'message': 'Sex must be M, F, or O',
                'code': 'INVALID_SEX'
            }), 400
        
        # Create user and assessment in single transaction
        try:
            logger.info(f'[START_ASSESSMENT] Creating user with age={age}, sex={sex}')
            user = User(age=age, sex=sex)
            logger.info(f'[START_ASSESSMENT] User instance created: {user}')
            
            db.session.add(user)
            logger.info(f'[START_ASSESSMENT] User added to session')
            
            db.session.commit()  # ✅ CRITICAL FIX: Commit user to database
            logger.info(f'[START_ASSESSMENT] User committed to database, ID: {user.id}')
            
        except Exception as e:
            logger.error(f'[START_ASSESSMENT] Error creating user: {str(e)}')
            logger.error(f'[START_ASSESSMENT] Full traceback: {traceback.format_exc()}')
            logger.error(f'[START_ASSESSMENT] Exception type: {type(e).__name__}')
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': 'Error creating user record',
                'code': 'USER_CREATE_ERROR',
                'details': str(e) if current_app.debug else None
            }), 500
        
        # Create assessment
        try:
            logger.info(f'[START_ASSESSMENT] Creating assessment for user {user.id}')
            assessment = Assessment(
                user_id=user.id,  # User now exists in database
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', '')[:500],
            )
            logger.info(f'[START_ASSESSMENT] Assessment instance created')
            
            db.session.add(assessment)
            logger.info(f'[START_ASSESSMENT] Assessment added to session')
            
            db.session.commit()
            logger.info(f'[START_ASSESSMENT] Assessment committed to database')
            logger.info(f'[START_ASSESSMENT] Created assessment {assessment.id} (external_id: {assessment.external_id}) for user {user.id}')
            
        except Exception as e:
            logger.error(f'[START_ASSESSMENT] Error creating assessment: {str(e)}')
            logger.error(f'[START_ASSESSMENT] Full traceback: {traceback.format_exc()}')
            logger.error(f'[START_ASSESSMENT] Exception type: {type(e).__name__}')
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': 'Error creating assessment record',
                'code': 'ASSESSMENT_CREATE_ERROR',
                'details': str(e) if current_app.debug else None
            }), 500
        
        # Success response
        logger.info(f'[START_ASSESSMENT] SUCCESS: Returning assessment_id={assessment.id}, external_id={assessment.external_id}')
        return jsonify({
            'status': 'success',
            'user_id': str(user.id),
            'assessment_id': assessment.id,
            'external_id': str(assessment.external_id),
        }), 201
    
    except Exception as e:
        logger.error(f'[START_ASSESSMENT] Unexpected error: {str(e)}')
        logger.error(f'[START_ASSESSMENT] Traceback: {traceback.format_exc()}')
        logger.error(f'[START_ASSESSMENT] Exception type: {type(e).__name__}')
        try:
            db.session.rollback()
        except:
            pass
        
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR',
            'error': str(e) if current_app.debug else None,
        }), 500


@api_bp.route('/submit-assessment', methods=['POST'])
def submit_assessment():
    """Submit assessment responses"""
    try:
        data = request.get_json(force=True, silent=True)
        
        if data is None:
            return jsonify({
                'status': 'error',
                'message': 'Request body must be JSON',
                'code': 'INVALID_JSON'
            }), 400
        
        assessment_id = data.get('assessment_id')
        responses = data.get('responses')
        
        if not assessment_id or not responses:
            return jsonify({
                'status': 'error',
                'message': 'Missing required fields: assessment_id, responses',
                'code': 'MISSING_FIELDS'
            }), 400
        
        if not isinstance(responses, dict):
            return jsonify({
                'status': 'error',
                'message': 'Responses must be an object/dict',
                'code': 'INVALID_RESPONSES_FORMAT'
            }), 400
        
        if len(responses) < 30:
            return jsonify({
                'status': 'error',
                'message': 'Must provide at least 30 responses',
                'code': 'INSUFFICIENT_RESPONSES'
            }), 400
        
        # Validate response values
        response_list = []
        for key in sorted(responses.keys()):
            val = responses[key]
            if not isinstance(val, (int, float)):
                return jsonify({
                    'status': 'error',
                    'message': f'Response {key} must be a number',
                    'code': 'INVALID_RESPONSE_TYPE'
                }), 400
            
            val = int(val)
            if val < 1 or val > 10:
                return jsonify({
                    'status': 'error',
                    'message': f'Response {key} must be between 1 and 10',
                    'code': 'RESPONSE_OUT_OF_RANGE'
                }), 400
            response_list.append(val)
        
        # Get assessment
        assessment = Assessment.query.get(assessment_id)
        if not assessment:
            return jsonify({
                'status': 'error',
                'message': 'Assessment not found',
                'code': 'ASSESSMENT_NOT_FOUND'
            }), 404
        
        # Save responses
        assessment.responses_json = responses
        assessment.completed_at = datetime.now(timezone.utc)
        db.session.commit()
        
        logger.info(f'[SUBMIT_ASSESSMENT] Assessment {assessment_id} responses saved')
        
        try:
            # Process with scoring engine
            if not scoring_engine:
                logger.error('[SUBMIT_ASSESSMENT] Scoring engine not initialized')
                return jsonify({
                    'status': 'error',
                    'message': 'Scoring engine not available',
                    'code': 'ENGINE_NOT_READY'
                }), 503
            
            result_data = scoring_engine.process_assessment(response_list, assessment.user.age)
            
            result = Result(
                assessment_id=assessment.id,
                raw_domain_scores=result_data['raw_domain_scores'],
                deception_susceptibility=result_data['deception_susceptibility'],
                corrected_domain_scores=result_data['corrected_domain_scores'],
                domain_biases=result_data['domain_biases'],
                validity_scores=result_data.get('validity_scores'),
                vae_input_vector=result_data['vae_input'],
            )
            db.session.add(result)
            db.session.commit()
            
            logger.info(f'[SUBMIT_ASSESSMENT] Scoring completed for assessment {assessment_id}')
            
            # Process with VAE engine
            if vae_engine:
                vae_result = vae_engine.process_assessment(result_data['vae_input'])
                
                vae_output = VAEOutput(
                    assessment_id=assessment.id,
                    latent_representation=vae_result['latent_representation'],
                    reconstruction_error=vae_result['reconstruction_error'],
                    latent_distance_from_mean=vae_result['latent_distance_from_mean'],
                    local_density=vae_result['local_density'],
                    novelty_score=vae_result['novelty_score'],
                )
                db.session.add(vae_output)
                
                personality_classification = PersonalityClassification(
                    assessment_id=assessment.id,
                    personality_type=vae_result['personality_type'],
                    confidence_score=vae_result['personality_details']['confidence'],
                    personality_details=vae_result['personality_details'],
                    type_description=vae_result['type_description']['description'],
                    key_traits=vae_result['type_description']['traits'],
                )
                db.session.add(personality_classification)
                db.session.commit()
                
                logger.info(f'[SUBMIT_ASSESSMENT] VAE processing completed for assessment {assessment_id}')
                
                # Process with Gemini if available
                if gemini_client:
                    assessment_context = {
                        'assessment_id': assessment.id,
                        'personality_type': vae_result['personality_type'],
                        'confidence_score': vae_result['personality_details']['confidence'],
                        'deception_susceptibility': result_data['deception_susceptibility'],
                        'corrected_domain_scores': result_data['corrected_domain_scores'],
                        'novelty_score': vae_result['novelty_score'],
                    }
                    
                    interpretation_result = gemini_client.process_assessment_with_interpretation(assessment_context)
                    
                    gemini_interpretation = GeminiInterpretation(
                        assessment_id=assessment.id,
                        prompt_text='Assessment interpretation request',
                        interpretation_text=interpretation_result['interpretation'],
                        api_status='success' if interpretation_result['api_success'] else 'fallback',
                    )
                    db.session.add(gemini_interpretation)
                    db.session.commit()
                    
                    logger.info(f'[SUBMIT_ASSESSMENT] Gemini interpretation completed for assessment {assessment_id}')
            
            return jsonify({
                'status': 'success',
                'assessment_id': assessment.id,
                'message': 'Assessment submitted and processed',
            }), 202
        
        except Exception as e:
            logger.error(f'[SUBMIT_ASSESSMENT] Error processing assessment data: {str(e)}')
            logger.error(traceback.format_exc())
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': 'Error processing assessment',
                'code': 'PROCESSING_ERROR',
                'error': str(e) if current_app.debug else None,
            }), 500
    
    except Exception as e:
        logger.error(f'[SUBMIT_ASSESSMENT] Unexpected error: {str(e)}')
        logger.error(traceback.format_exc())
        try:
            db.session.rollback()
        except:
            pass
        
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR',
            'error': str(e) if current_app.debug else None,
        }), 500


@api_bp.route('/results/<int:assessment_id>', methods=['GET'])
def get_results(assessment_id):
    try:
        assessment = Assessment.query.get(assessment_id)
        if not assessment:
            return jsonify({
                'status': 'error',
                'message': 'Assessment not found',
                'code': 'ASSESSMENT_NOT_FOUND'
            }), 404
        
        result = assessment.results
        if not result:
            return jsonify({
                'status': 'error',
                'message': 'Results not yet available',
                'code': 'RESULTS_NOT_AVAILABLE'
            }), 404
        
        vae_output = assessment.vae_outputs
        personality = assessment.personality_classifications
        gemini = assessment.gemini_interpretations
        
        response_data = {
            'status': 'success',
            'assessment_id': assessment.id,
            'user': {
                'age': assessment.user.age,
                'sex': assessment.user.sex,
            },
            'results': result.to_dict(),
            'vae': vae_output.to_dict() if vae_output else None,
            'personality': personality.to_dict() if personality else None,
            'interpretation': gemini.interpretation_text if gemini else None,
        }
        
        return jsonify(response_data), 200
    
    except Exception as e:
        logger.error(f'[GET_RESULTS] Error: {str(e)}')
        logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR',
            'error': str(e) if current_app.debug else None,
        }), 500


@api_bp.route('/assessments', methods=['GET'])
def list_assessments():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        if per_page > 100:
            per_page = 100
        
        paginated = Assessment.query.order_by(desc(Assessment.created_at)).paginate(page=page, per_page=per_page)
        
        assessments = [a.to_dict() for a in paginated.items]
        
        return jsonify({
            'status': 'success',
            'data': assessments,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': paginated.total,
                'pages': paginated.pages,
            },
        }), 200
    
    except Exception as e:
        logger.error(f'[LIST_ASSESSMENTS] Error: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500


@api_bp.route('/users/<user_id>/assessments', methods=['GET'])
def get_user_assessments(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'status': 'error',
                'message': 'User not found',
                'code': 'USER_NOT_FOUND'
            }), 404
        
        assessments = Assessment.query.filter_by(user_id=user_id).order_by(desc(Assessment.created_at)).all()
        
        return jsonify({
            'status': 'success',
            'user_id': str(user_id),
            'assessments': [a.to_dict() for a in assessments],
            'count': len(assessments),
        }), 200
    
    except Exception as e:
        logger.error(f'[GET_USER_ASSESSMENTS] Error: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500


@api_bp.route('/stats', methods=['GET'])
def get_statistics():
    try:
        total_users = User.query.count()
        total_assessments = Assessment.query.count()
        completed_assessments = Assessment.query.filter_by(is_valid=True).count()
        
        personality_distribution = db.session.query(
            PersonalityClassification.personality_type,
            func.count(PersonalityClassification.id)
        ).group_by(PersonalityClassification.personality_type).all()
        
        personality_stats = {
            ptype: count for ptype, count in personality_distribution
        }
        
        avg_deception = db.session.query(func.avg(Result.deception_susceptibility)).scalar()
        
        return jsonify({
            'status': 'success',
            'statistics': {
                'total_users': total_users,
                'total_assessments': total_assessments,
                'completed_assessments': completed_assessments,
                'completion_rate': completed_assessments / total_assessments if total_assessments > 0 else 0,
                'personality_distribution': personality_stats,
                'average_deception_susceptibility': float(avg_deception) if avg_deception else None,
            },
        }), 200
    
    except Exception as e:
        logger.error(f'[GET_STATISTICS] Error: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500
