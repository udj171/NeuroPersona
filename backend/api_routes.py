# ============================================================================
# SCRIPT 7: api_routes.py - REST API Endpoints (3000+ lines)
# ============================================================================

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import desc
import logging
from datetime import datetime, timezone
import uuid
from models import db, User, Assessment, Result, VAEOutput, PersonalityClassification, GeminiInterpretation
from scoring_engine import ScoringEngine
from vae_inference import VAEInference
from gemini_client import GeminiClient
from utils import utils

api_bp = Blueprint('api', __name__)
logger = logging.getLogger(__name__)

@api_bp.before_request
def log_request():
    logger.info(f'{request.method} {request.path} from {request.remote_addr}')

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
        logger.error(f'Health check failed: {str(e)}')
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }), 503

@api_bp.route('/start-assessment', methods=['POST'])
def start_assessment():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Request body must be JSON',
            }), 400
        
        age = data.get('age')
        sex = data.get('sex')
        
        if not age or not sex:
            return jsonify({
                'status': 'error',
                'message': 'Missing required fields: age, sex',
            }), 400
        
        if not isinstance(age, int) or age < 13 or age > 120:
            return jsonify({
                'status': 'error',
                'message': 'Age must be between 13 and 120',
            }), 400
        
        if sex not in ['M', 'F', 'O']:
            return jsonify({
                'status': 'error',
                'message': 'Sex must be M, F, or O',
            }), 400
        
        user = User(age=age, sex=sex)
        db.session.add(user)
        db.session.commit()
        
        assessment = Assessment(
            user_id=user.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
        )
        db.session.add(assessment)
        db.session.commit()
        
        logger.info(f'Started assessment {assessment.id} for user {user.id}')
        
        return jsonify({
            'status': 'success',
            'user_id': user.id,
            'assessment_id': assessment.id,
            'external_id': str(assessment.external_id),
        }), 201
    
    except Exception as e:
        logger.error(f'Error in start_assessment: {str(e)}', exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'error': str(e) if current_app.debug else None,
        }), 500

@api_bp.route('/submit-assessment', methods=['POST'])
def submit_assessment():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Request body must be JSON',
            }), 400
        
        assessment_id = data.get('assessment_id')
        responses = data.get('responses')
        
        if not assessment_id or not responses:
            return jsonify({
                'status': 'error',
                'message': 'Missing required fields: assessment_id, responses',
            }), 400
        
        if len(responses) < 30:
            return jsonify({
                'status': 'error',
                'message': 'Must provide at least 30 responses',
            }), 400
        
        for i, response in enumerate(responses[:35]):
            if not isinstance(response, (int, float)) or response < 0 or response > 10:
                return jsonify({
                    'status': 'error',
                    'message': f'Response {i} must be a number between 0 and 10',
                }), 400
        
        assessment = Assessment.query.get(assessment_id)
        if not assessment:
            return jsonify({
                'status': 'error',
                'message': 'Assessment not found',
            }), 404
        
        assessment.responses_json = responses[:35]
        assessment.completed_at = datetime.now(timezone.utc)
        db.session.commit()
        
        try:
            result_data = scoring_engine.process_assessment(responses, assessment.user.age)
            
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
            
            logger.info(f'Successfully processed assessment {assessment.id}')
            
            return jsonify({
                'status': 'success',
                'assessment_id': assessment.id,
                'message': 'Assessment submitted and processed',
            }), 202
        
        except Exception as e:
            logger.error(f'Error processing assessment data: {str(e)}', exc_info=True)
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': 'Error processing assessment',
                'error': str(e) if current_app.debug else None,
            }), 500
    
    except Exception as e:
        logger.error(f'Error in submit_assessment: {str(e)}', exc_info=True)
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
        logger.error(f'Error in get_results: {str(e)}', exc_info=True)
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
        logger.error(f'Error in list_assessments: {str(e)}', exc_info=True)
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
        logger.error(f'Error in get_user_assessments: {str(e)}', exc_info=True)
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
        logger.error(f'Error in get_statistics: {str(e)}', exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
        }), 500
