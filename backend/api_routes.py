# ============================================================================
# SCRIPT 7: api_routes.py - REST API Endpoints (FIXED - Better Error Handling)
# ============================================================================

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import desc, func
from sqlalchemy.exc import SQLAlchemyError
import logging
from datetime import datetime, timezone
import uuid
from models import db, User, Assessment, Result, VAEOutput, PersonalityClassification, GeminiInterpretation
from scoring_engine import ScoringEngine
from vae_inference import VAEInferenceEngine
from gemini_client import GeminiClient


# These will be injected by app.py
api_bp = Blueprint('api', __name__)
logger = logging.getLogger(__name__)

scoring_engine = None
vae_engine = None
gemini_client = None

def init_engines(scoring, vae, gemini):
    """Initialize engine references from app.py"""
    global scoring_engine, vae_engine, gemini_client
    scoring_engine = scoring
    vae_engine = vae
    gemini_client = gemini
    logger.info('[ENGINES] ✓ All engines initialized successfully')


@api_bp.before_request
def log_request():
    logger.info(f'[REQUEST] {request.method} {request.path} from {request.remote_addr}')

@api_bp.route('/health', methods=['GET'])
def health_check():
    try:
        db.session.execute('SELECT 1')
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'service': 'personality-assessment-api',
            'version': '1.0.0',
        }), 200
    except Exception as e:
        logger.error(f'[HEALTH] Health check failed: {str(e)}')
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }), 503

@api_bp.route('/start-assessment', methods=['POST'])
def start_assessment():
    """Start a new assessment - FIX: Enhanced error handling"""
    logger.info('[START_ASSESSMENT] Request received')
    
    try:
        # Step 1: Validate request body
        logger.debug('[START_ASSESSMENT] Step 1: Validating request body')
        data = request.get_json()
        
        if not data:
            logger.warning('[START_ASSESSMENT] No JSON body provided')
            return jsonify({
                'status': 'error',
                'message': 'Request body must be JSON',
            }), 400
        
        # Step 2: Extract and validate fields
        logger.debug('[START_ASSESSMENT] Step 2: Extracting fields')
        age = data.get('age')
        sex = data.get('sex')
        
        if not age or not sex:
            logger.warning(f'[START_ASSESSMENT] Missing fields - age: {age}, sex: {sex}')
            return jsonify({
                'status': 'error',
                'message': 'Missing required fields: age, sex',
            }), 400
        
        # Step 3: Validate age
        logger.debug(f'[START_ASSESSMENT] Step 3: Validating age={age}')
        if not isinstance(age, int) or age < 13 or age > 120:
            logger.warning(f'[START_ASSESSMENT] Invalid age: {age}')
            return jsonify({
                'status': 'error',
                'message': 'Age must be between 13 and 120',
            }), 400
        
        # Step 4: Validate sex
        logger.debug(f'[START_ASSESSMENT] Step 4: Validating sex={sex}')
        if sex not in ['M', 'F', 'O']:
            logger.warning(f'[START_ASSESSMENT] Invalid sex: {sex}')
            return jsonify({
                'status': 'error',
                'message': 'Sex must be M, F, or O',
            }), 400
        
        # Step 5: Create User in database
        logger.debug('[START_ASSESSMENT] Step 5: Creating User in database')
        try:
            user = User(age=age, sex=sex)
            db.session.add(user)
            db.session.flush()  # Flush to get the ID without committing
            user_id = user.id
            logger.info(f'[START_ASSESSMENT] User created: user_id={user_id}')
        except SQLAlchemyError as e:
            logger.error(f'[START_ASSESSMENT] Database error creating user: {str(e)}')
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': 'Database error creating user',
                'detail': str(e) if current_app.debug else None,
            }), 500
        
        # Step 6: Create Assessment in database
        logger.debug(f'[START_ASSESSMENT] Step 6: Creating Assessment for user_id={user_id}')
        try:
            assessment = Assessment(
                user_id=user_id,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', ''),
            )
            db.session.add(assessment)
            db.session.flush()
            assessment_id = assessment.id
            logger.info(f'[START_ASSESSMENT] Assessment created: assessment_id={assessment_id}')
        except SQLAlchemyError as e:
            logger.error(f'[START_ASSESSMENT] Database error creating assessment: {str(e)}')
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': 'Database error creating assessment',
                'detail': str(e) if current_app.debug else None,
            }), 500
        
        # Step 7: Commit transaction
        logger.debug('[START_ASSESSMENT] Step 7: Committing transaction')
        try:
            db.session.commit()
            logger.info(f'[START_ASSESSMENT] Transaction committed successfully')
        except SQLAlchemyError as e:
            logger.error(f'[START_ASSESSMENT] Database error during commit: {str(e)}')
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': 'Database error during commit',
                'detail': str(e) if current_app.debug else None,
            }), 500
        
        # Step 8: Return success response
        logger.debug('[START_ASSESSMENT] Step 8: Returning success response')
        response = {
            'status': 'success',
            'user_id': user_id,
            'assessment_id': assessment_id,
            'external_id': str(assessment.external_id),
        }
        logger.info(f'[START_ASSESSMENT] ✓ Complete: {response}')
        return jsonify(response), 201
    
    except Exception as e:
        logger.error(f'[START_ASSESSMENT] ✗ Unexpected error: {str(e)}', exc_info=True)
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'error': str(e) if current_app.debug else None,
        }), 500

@api_bp.route('/submit-assessment', methods=['POST'])
def submit_assessment():
    """Submit assessment responses - FIX: Enhanced error handling"""
    logger.info('[SUBMIT_ASSESSMENT] Request received')
    
    try:
        # Step 1: Validate request body
        logger.debug('[SUBMIT_ASSESSMENT] Step 1: Validating request body')
        data = request.get_json()
        
        if not data:
            logger.warning('[SUBMIT_ASSESSMENT] No JSON body provided')
            return jsonify({
                'status': 'error',
                'message': 'Request body must be JSON',
            }), 400
        
        # Step 2: Extract fields
        logger.debug('[SUBMIT_ASSESSMENT] Step 2: Extracting fields')
        assessment_id = data.get('assessment_id')
        responses = data.get('responses')
        
        if not assessment_id or not responses:
            logger.warning(f'[SUBMIT_ASSESSMENT] Missing fields - assessment_id: {assessment_id}, responses: {responses}')
            return jsonify({
                'status': 'error',
                'message': 'Missing required fields: assessment_id, responses',
            }), 400
        
        # Step 3: Validate response count
        logger.debug(f'[SUBMIT_ASSESSMENT] Step 3: Validating response count')
        if len(responses) < 30:
            logger.warning(f'[SUBMIT_ASSESSMENT] Insufficient responses: {len(responses)}')
            return jsonify({
                'status': 'error',
                'message': 'Must provide at least 30 responses',
            }), 400
        
        # Step 4: Validate response values
        logger.debug('[SUBMIT_ASSESSMENT] Step 4: Validating response values')
        for i, response in enumerate(responses[:35]):
            if not isinstance(response, (int, float)):
                logger.warning(f'[SUBMIT_ASSESSMENT] Invalid response type at {i}: {type(response)}')
                return jsonify({
                    'status': 'error',
                    'message': f'Response {i} must be a number between 0 and 10',
                }), 400
            if response < 0 or response > 10:
                logger.warning(f'[SUBMIT_ASSESSMENT] Response value out of range at {i}: {response}')
                return jsonify({
                    'status': 'error',
                    'message': f'Response {i} must be a number between 0 and 10',
                }), 400
        
        # Step 5: Find assessment
        logger.debug(f'[SUBMIT_ASSESSMENT] Step 5: Finding assessment {assessment_id}')
        assessment = Assessment.query.get(assessment_id)
        if not assessment:
            logger.warning(f'[SUBMIT_ASSESSMENT] Assessment not found: {assessment_id}')
            return jsonify({
                'status': 'error',
                'message': 'Assessment not found',
            }), 404
        
        # Step 6: Update assessment with responses
        logger.debug('[SUBMIT_ASSESSMENT] Step 6: Updating assessment')
        try:
            assessment.responses_json = responses[:35]
            assessment.completed_at = datetime.now(timezone.utc)
            db.session.commit()
            logger.info(f'[SUBMIT_ASSESSMENT] Assessment updated')
        except SQLAlchemyError as e:
            logger.error(f'[SUBMIT_ASSESSMENT] Database error updating assessment: {str(e)}')
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': 'Database error updating assessment',
                'detail': str(e) if current_app.debug else None,
            }), 500
        
        # Step 7: Process with scoring engine
        logger.debug('[SUBMIT_ASSESSMENT] Step 7: Processing with scoring engine')
        try:
            if scoring_engine is None:
                logger.error('[SUBMIT_ASSESSMENT] Scoring engine not initialized')
                return jsonify({
                    'status': 'error',
                    'message': 'Scoring engine not available',
                }), 500
            
            result_data = scoring_engine.process_assessment(responses, assessment.user.age)
            logger.debug('[SUBMIT_ASSESSMENT] Scoring engine processing complete')
        except Exception as e:
            logger.error(f'[SUBMIT_ASSESSMENT] Error in scoring engine: {str(e)}', exc_info=True)
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': 'Error processing assessment scores',
                'detail': str(e) if current_app.debug else None,
            }), 500
        
        # Step 8: Save result to database
        logger.debug('[SUBMIT_ASSESSMENT] Step 8: Saving result to database')
        try:
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
            db.session.flush()
            logger.info('[SUBMIT_ASSESSMENT] Result saved')
        except SQLAlchemyError as e:
            logger.error(f'[SUBMIT_ASSESSMENT] Database error saving result: {str(e)}')
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': 'Database error saving result',
                'detail': str(e) if current_app.debug else None,
            }), 500
        
        # Step 9: Process with VAE engine
        logger.debug('[SUBMIT_ASSESSMENT] Step 9: Processing with VAE engine')
        try:
            if vae_engine is None:
                logger.error('[SUBMIT_ASSESSMENT] VAE engine not initialized')
                db.session.rollback()
                return jsonify({
                    'status': 'error',
                    'message': 'VAE engine not available',
                }), 500
            
            vae_result = vae_engine.process_assessment(result_data['vae_input'])
            logger.debug('[SUBMIT_ASSESSMENT] VAE processing complete')
        except Exception as e:
            logger.error(f'[SUBMIT_ASSESSMENT] Error in VAE engine: {str(e)}', exc_info=True)
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': 'Error processing VAE analysis',
                'detail': str(e) if current_app.debug else None,
            }), 500
        
        # Step 10: Save VAE output
        logger.debug('[SUBMIT_ASSESSMENT] Step 10: Saving VAE output')
        try:
            vae_output = VAEOutput(
                assessment_id=assessment.id,
                latent_representation=vae_result['latent_representation'],
                reconstruction_error=vae_result['reconstruction_error'],
                latent_distance_from_mean=vae_result['latent_distance_from_mean'],
                local_density=vae_result['local_density'],
                novelty_score=vae_result['novelty_score'],
            )
            db.session.add(vae_output)
            db.session.flush()
            logger.info('[SUBMIT_ASSESSMENT] VAE output saved')
        except Exception as e:
            logger.error(f'[SUBMIT_ASSESSMENT] Error saving VAE output: {str(e)}')
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': 'Error saving VAE output',
                'detail': str(e) if current_app.debug else None,
            }), 500
        
        # Step 11: Save personality classification
        logger.debug('[SUBMIT_ASSESSMENT] Step 11: Saving personality classification')
        try:
            personality_classification = PersonalityClassification(
                assessment_id=assessment.id,
                personality_type=vae_result['personality_type'],
                confidence_score=vae_result['personality_details']['confidence'],
                personality_details=vae_result['personality_details'],
                type_description=vae_result['type_description']['description'],
                key_traits=vae_result['type_description']['traits'],
            )
            db.session.add(personality_classification)
            db.session.flush()
            logger.info('[SUBMIT_ASSESSMENT] Personality classification saved')
        except Exception as e:
            logger.error(f'[SUBMIT_ASSESSMENT] Error saving personality classification: {str(e)}')
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': 'Error saving personality classification',
                'detail': str(e) if current_app.debug else None,
            }), 500
        
        # Step 12: Process Gemini interpretation
        logger.debug('[SUBMIT_ASSESSMENT] Step 12: Processing Gemini interpretation')
        try:
            if gemini_client is None:
                logger.warning('[SUBMIT_ASSESSMENT] Gemini client not available, skipping interpretation')
                interpretation_result = {'interpretation': 'Interpretation unavailable', 'api_success': False}
            else:
                assessment_context = {
                    'assessment_id': assessment.id,
                    'personality_type': vae_result['personality_type'],
                    'confidence_score': vae_result['personality_details']['confidence'],
                    'deception_susceptibility': result_data['deception_susceptibility'],
                    'corrected_domain_scores': result_data['corrected_domain_scores'],
                    'novelty_score': vae_result['novelty_score'],
                }
                interpretation_result = gemini_client.process_assessment_with_interpretation(assessment_context)
                logger.debug('[SUBMIT_ASSESSMENT] Gemini interpretation complete')
        except Exception as e:
            logger.error(f'[SUBMIT_ASSESSMENT] Error in Gemini interpretation: {str(e)}', exc_info=True)
            interpretation_result = {'interpretation': f'Error: {str(e)}', 'api_success': False}
        
        # Step 13: Save Gemini interpretation
        logger.debug('[SUBMIT_ASSESSMENT] Step 13: Saving Gemini interpretation')
        try:
            gemini_interpretation = GeminiInterpretation(
                assessment_id=assessment.id,
                prompt_text='Assessment interpretation request',
                interpretation_text=interpretation_result['interpretation'],
                api_status='success' if interpretation_result['api_success'] else 'fallback',
            )
            db.session.add(gemini_interpretation)
            db.session.flush()
            logger.info('[SUBMIT_ASSESSMENT] Gemini interpretation saved')
        except Exception as e:
            logger.error(f'[SUBMIT_ASSESSMENT] Error saving Gemini interpretation: {str(e)}')
            # Don't rollback here, this is non-critical
        
        # Step 14: Final commit
        logger.debug('[SUBMIT_ASSESSMENT] Step 14: Final commit')
        try:
            db.session.commit()
            logger.info('[SUBMIT_ASSESSMENT] ✓ All data committed successfully')
        except SQLAlchemyError as e:
            logger.error(f'[SUBMIT_ASSESSMENT] Final commit error: {str(e)}')
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': 'Error finalizing assessment',
                'detail': str(e) if current_app.debug else None,
            }), 500
        
        logger.info(f'[SUBMIT_ASSESSMENT] ✓ Complete for assessment {assessment.id}')
        return jsonify({
            'status': 'success',
            'assessment_id': assessment.id,
            'message': 'Assessment submitted and processed',
        }), 202
    
    except Exception as e:
        logger.error(f'[SUBMIT_ASSESSMENT] ✗ Unexpected error: {str(e)}', exc_info=True)
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
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
            }), 404
        
        result = assessment.results
        if not result:
            return jsonify({
                'status': 'error',
                'message': 'Results not yet available',
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
        logger.error(f'[GET_RESULTS] Error: {str(e)}', exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
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
        logger.error(f'[LIST_ASSESSMENTS] Error: {str(e)}', exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
        }), 500

@api_bp.route('/users/<int:user_id>/assessments', methods=['GET'])
def get_user_assessments(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'status': 'error',
                'message': 'User not found',
            }), 404
        
        assessments = Assessment.query.filter_by(user_id=user_id).order_by(desc(Assessment.created_at)).all()
        
        return jsonify({
            'status': 'success',
            'user_id': user_id,
            'assessments': [a.to_dict() for a in assessments],
            'count': len(assessments),
        }), 200
    
    except Exception as e:
        logger.error(f'[GET_USER_ASSESSMENTS] Error: {str(e)}', exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
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
        logger.error(f'[GET_STATISTICS] Error: {str(e)}', exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
        }), 500
