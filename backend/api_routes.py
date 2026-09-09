# ============================================================================
# SCRIPT 7: api_routes.py - REST API Endpoints
# ============================================================================

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import desc, func
import logging
import time
import traceback
from datetime import datetime, timezone

from models import (db, User, Assessment, Result, ModelOutput,
                    PersonalityClassification, Interpretation)
from ocean_items import (ALL_ITEM_IDS, N_ITEMS, SCALE_MAX, SCALE_MIN,
                         TRAIT_ORDER, TRAITS, to_frontend_payload)

api_bp = Blueprint('api', __name__)
logger = logging.getLogger(__name__)

scoring_engine = None
model_engine = None
narrative_generator = None


def set_engines(scoring, model, narrative):
    """Set engine references from app.py"""
    global scoring_engine, model_engine, narrative_generator
    scoring_engine = scoring
    model_engine = model
    narrative_generator = narrative
    logger.info('[API_ROUTES] Engines configured:')
    logger.info(f"  - ScoringEngine: {'Ready' if scoring else 'None'}")
    logger.info(f"  - ModelInferenceEngine: {'Ready' if model else 'None'}"
                + (f" (trained={model.is_trained})" if model else ''))
    logger.info(f"  - NarrativeGenerator: {'Ready' if narrative else 'None'}"
                + (f" (backend={narrative.active_backend})" if narrative else ''))


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


@api_bp.route('/questionnaire', methods=['GET'])
def get_questionnaire():
    """The item bank the questionnaire page renders.

    Served from the same module the scorer reads, so the wording, the item
    ids and the answer scale cannot drift apart between the two.
    """
    try:
        return jsonify({'status': 'success', **to_frontend_payload()}), 200
    except Exception as e:
        logger.error(f'[QUESTIONNAIRE] Error: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': 'Could not load the questionnaire',
            'code': 'QUESTIONNAIRE_UNAVAILABLE'
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
    """Score one completed questionnaire and store every intermediate result."""
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

        if not assessment_id or responses is None:
            return jsonify({
                'status': 'error',
                'message': 'Missing required fields: assessment_id, responses',
                'code': 'MISSING_FIELDS'
            }), 400

        if not isinstance(responses, dict):
            return jsonify({
                'status': 'error',
                'message': 'Responses must be an object keyed by item id',
                'code': 'INVALID_RESPONSES_FORMAT'
            }), 400

        clean, error = _validate_responses(responses)
        if error:
            return jsonify(error), 400

        assessment = Assessment.query.get(assessment_id)
        if not assessment:
            return jsonify({
                'status': 'error',
                'message': 'Assessment not found',
                'code': 'ASSESSMENT_NOT_FOUND'
            }), 404

        assessment.responses_json = clean
        assessment.completed_at = datetime.now(timezone.utc)
        db.session.commit()
        logger.info(f'[SUBMIT_ASSESSMENT] Assessment {assessment_id} responses saved')

        if not scoring_engine:
            logger.error('[SUBMIT_ASSESSMENT] Scoring engine not initialized')
            return jsonify({
                'status': 'error',
                'message': 'Scoring engine not available',
                'code': 'ENGINE_NOT_READY'
            }), 503

        try:
            scored = scoring_engine.process_assessment(clean, assessment.user.age)

            db.session.add(Result(
                assessment_id=assessment.id,
                raw_trait_scores=scored['raw_trait_scores'],
                corrected_trait_scores=scored['corrected_trait_scores'],
                trait_biases=scored['trait_biases'],
                lambda_score=scored['lambda'],
                lambda_band=scored['lambda_band'],
                lambda_analysis=scored['lambda_analysis'],
                validity_responses=scored['validity_responses'],
                model_input_vector=scored['model_input'],
            ))
            db.session.commit()
            logger.info(f'[SUBMIT_ASSESSMENT] Scoring completed for {assessment_id}')

            # Model inference. An untrained engine still answers, and says so.
            inference = model_engine.process(
                scored['model_input'], scored['raw_trait_scores'])

            db.session.add(ModelOutput(
                assessment_id=assessment.id,
                weights_loaded=inference['weights_loaded'],
                model_version=inference['model_version'],
                latent_representation=inference['latent'],
                reconstruction_error=inference['reconstruction_error'],
                latent_distance_from_mean=inference['latent_distance_from_mean'],
                novelty_score=inference['novelty_score'],
                percentiles=inference['percentiles'],
            ))
            db.session.add(PersonalityClassification(
                assessment_id=assessment.id,
                type_index=inference['type_index'],
                type_name=inference['type_name'],
                confidence_score=inference['confidence'],
                runner_up_name=inference['runner_up_name'],
                type_traits=inference['type_traits'],
                type_probabilities=inference['type_probabilities'],
            ))
            db.session.commit()
            logger.info(f'[SUBMIT_ASSESSMENT] Inference completed for {assessment_id} '
                        f"(trained={inference['weights_loaded']})")

            if narrative_generator:
                started = time.perf_counter()
                written = narrative_generator.generate({
                    'type_name': inference['type_name'],
                    'confidence': inference['confidence'],
                    'weights_loaded': inference['weights_loaded'],
                    'percentiles': inference['percentiles'],
                    'lambda': scored['lambda'],
                    'lambda_band': scored['lambda_band'],
                    'raw_trait_scores': scored['raw_trait_scores'],
                    'corrected_trait_scores': scored['corrected_trait_scores'],
                })
                db.session.add(Interpretation(
                    assessment_id=assessment.id,
                    interpretation_text=written['interpretation'],
                    backend=written['backend'],
                    model_name=written['model'],
                    generation_time_ms=int((time.perf_counter() - started) * 1000),
                ))
                db.session.commit()
                logger.info(f"[SUBMIT_ASSESSMENT] Interpretation written for {assessment_id} "
                            f"({written['backend']})")

            return jsonify({
                'status': 'success',
                'assessment_id': assessment.id,
                'message': 'Assessment submitted and processed',
            }), 202

        except Exception as e:
            logger.error(f'[SUBMIT_ASSESSMENT] Error processing assessment: {str(e)}')
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
        except Exception:
            pass
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR',
            'error': str(e) if current_app.debug else None,
        }), 500


def _validate_responses(responses):
    """Require every item id exactly once, each an integer on the answer scale."""
    missing = [i for i in ALL_ITEM_IDS if i not in responses]
    if missing:
        return None, {
            'status': 'error',
            'message': f'Missing {len(missing)} of {N_ITEMS} responses',
            'code': 'INCOMPLETE_RESPONSES',
            'missing': missing[:10],
        }

    unknown = [k for k in responses if k not in set(ALL_ITEM_IDS)]
    if unknown:
        return None, {
            'status': 'error',
            'message': 'Unrecognised item ids in responses',
            'code': 'UNKNOWN_ITEM_IDS',
            'unknown': unknown[:10],
        }

    clean = {}
    for item_id in ALL_ITEM_IDS:
        value = responses[item_id]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None, {
                'status': 'error',
                'message': f'Response {item_id} must be a number',
                'code': 'INVALID_RESPONSE_TYPE',
            }
        value = int(value)
        if value < SCALE_MIN or value > SCALE_MAX:
            return None, {
                'status': 'error',
                'message': f'Response {item_id} must be between {SCALE_MIN} and {SCALE_MAX}',
                'code': 'RESPONSE_OUT_OF_RANGE',
            }
        clean[item_id] = value

    return clean, None


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

        model_output = assessment.model_outputs
        personality = assessment.personality_classifications
        interpretation = assessment.interpretations

        return jsonify({
            'status': 'success',
            'assessment_id': assessment.id,
            'user': {'age': assessment.user.age, 'sex': assessment.user.sex},
            'traits': {
                'order': TRAIT_ORDER,
                'names': {k: v['name'] for k, v in TRAITS.items()},
                'blurbs': {k: v['blurb'] for k, v in TRAITS.items()},
            },
            'results': result.to_dict(),
            'model': model_output.to_dict() if model_output else None,
            'personality': personality.to_dict() if personality else None,
            'interpretation': interpretation.interpretation_text if interpretation else None,
            'interpretation_backend': interpretation.backend if interpretation else None,
        }), 200

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
            PersonalityClassification.type_name,
            func.count(PersonalityClassification.id)
        ).group_by(PersonalityClassification.type_name).all()

        personality_stats = {name: count for name, count in personality_distribution}

        avg_lambda = db.session.query(func.avg(Result.lambda_score)).scalar()
        
        return jsonify({
            'status': 'success',
            'statistics': {
                'total_users': total_users,
                'total_assessments': total_assessments,
                'completed_assessments': completed_assessments,
                'completion_rate': completed_assessments / total_assessments if total_assessments > 0 else 0,
                'personality_distribution': personality_stats,
                'average_lambda': float(avg_lambda) if avg_lambda else None,
            },
        }), 200
    
    except Exception as e:
        logger.error(f'[GET_STATISTICS] Error: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500
