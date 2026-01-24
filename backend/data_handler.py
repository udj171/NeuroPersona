# ============================================================================
# SCRIPT 8: data_handler.py - Database Operations & Persistence (2500+ lines)
# ============================================================================

import logging
from typing import Dict, List, Optional, Tuple, Any
import json
from datetime import datetime, timezone
from sqlalchemy import and_, or_, func, desc
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import numpy as np
from models import (
    db, User, Assessment, Result, VAEOutput,
    PersonalityClassification, GeminiInterpretation, AuditLog,
)


logger = logging.getLogger(__name__)

class DataHandler:
    
    def __init__(self, db_instance):
        self.db = db_instance
        self.logger = logging.getLogger(self.__class__.__name__)
        self.cache = {}
    
    def create_user(self, age: int, sex: str) -> Optional[int]:
        try:
            user = User(age=age, sex=sex)
            self.db.session.add(user)
            self.db.session.commit()
            self.logger.info(f'Created user {user.id} with age {age}, sex {sex}')
            return user.id
        except IntegrityError as e:
            self.db.session.rollback()
            self.logger.error(f'Integrity error creating user: {str(e)}')
            return None
        except SQLAlchemyError as e:
            self.db.session.rollback()
            self.logger.error(f'Database error creating user: {str(e)}')
            return None
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        try:
            user = User.query.get(user_id)
            if user:
                return user.to_dict()
            return None
        except SQLAlchemyError as e:
            self.logger.error(f'Error retrieving user {user_id}: {str(e)}')
            return None
    
    def create_assessment(self, user_id: int, ip_address: str = '', user_agent: str = '') -> Optional[int]:
        try:
            assessment = Assessment(
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            self.db.session.add(assessment)
            self.db.session.commit()
            self.logger.info(f'Created assessment {assessment.id} for user {user_id}')
            return assessment.id
        except SQLAlchemyError as e:
            self.db.session.rollback()
            self.logger.error(f'Error creating assessment: {str(e)}')
            return None
    
    def update_assessment_responses(self, assessment_id: int, responses: List[int]) -> bool:
        try:
            assessment = Assessment.query.get(assessment_id)
            if not assessment:
                self.logger.warning(f'Assessment {assessment_id} not found')
                return False
            
            assessment.responses_json = responses
            assessment.completed_at = datetime.now(timezone.utc)
            self.db.session.commit()
            self.logger.info(f'Updated responses for assessment {assessment_id}')
            return True
        except SQLAlchemyError as e:
            self.db.session.rollback()
            self.logger.error(f'Error updating assessment responses: {str(e)}')
            return False
    
    def save_scoring_results(self, assessment_id: int, scoring_data: Dict) -> bool:
        try:
            result = Result(
                assessment_id=assessment_id,
                raw_domain_scores=scoring_data.get('raw_domain_scores'),
                deception_susceptibility=scoring_data.get('deception_susceptibility'),
                corrected_domain_scores=scoring_data.get('corrected_domain_scores'),
                domain_biases=scoring_data.get('domain_biases'),
                validity_scores=scoring_data.get('validity_scores'),
                vae_input_vector=scoring_data.get('vae_input_vector'),
            )
            self.db.session.add(result)
            self.db.session.commit()
            self.logger.info(f'Saved scoring results for assessment {assessment_id}')
            return True
        except IntegrityError:
            self.db.session.rollback()
            self.logger.warning(f'Results already exist for assessment {assessment_id}')
            return False
        except SQLAlchemyError as e:
            self.db.session.rollback()
            self.logger.error(f'Error saving scoring results: {str(e)}')
            return False
    
    def save_vae_outputs(self, assessment_id: int, vae_data: Dict) -> bool:
        try:
            vae_output = VAEOutput(
                assessment_id=assessment_id,
                latent_representation=vae_data.get('latent_representation'),
                reconstruction_error=vae_data.get('reconstruction_error'),
                latent_distance_from_mean=vae_data.get('latent_distance_from_mean'),
                local_density=vae_data.get('local_density'),
                novelty_score=vae_data.get('novelty_score'),
            )
            self.db.session.add(vae_output)
            self.db.session.commit()
            self.logger.info(f'Saved VAE outputs for assessment {assessment_id}')
            return True
        except IntegrityError:
            self.db.session.rollback()
            self.logger.warning(f'VAE outputs already exist for assessment {assessment_id}')
            return False
        except SQLAlchemyError as e:
            self.db.session.rollback()
            self.logger.error(f'Error saving VAE outputs: {str(e)}')
            return False
    
    def save_personality_classification(self, assessment_id: int, classification_data: Dict) -> bool:
        try:
            classification = PersonalityClassification(
                assessment_id=assessment_id,
                personality_type=classification_data.get('personality_type'),
                confidence_score=classification_data.get('confidence_score'),
                personality_details=classification_data.get('personality_details'),
                type_description=classification_data.get('type_description'),
                key_traits=classification_data.get('key_traits'),
            )
            self.db.session.add(classification)
            self.db.session.commit()
            self.logger.info(f'Saved personality classification for assessment {assessment_id}')
            return True
        except IntegrityError:
            self.db.session.rollback()
            self.logger.warning(f'Classification already exists for assessment {assessment_id}')
            return False
        except SQLAlchemyError as e:
            self.db.session.rollback()
            self.logger.error(f'Error saving classification: {str(e)}')
            return False
    
    def save_gemini_interpretation(self, assessment_id: int, interpretation_data: Dict) -> bool:
        try:
            interpretation = GeminiInterpretation(
                assessment_id=assessment_id,
                prompt_text=interpretation_data.get('prompt_text', ''),
                interpretation_text=interpretation_data.get('interpretation_text'),
                tokens_used=interpretation_data.get('tokens_used'),
                response_time_ms=interpretation_data.get('response_time_ms'),
                api_status=interpretation_data.get('api_status', 'success'),
            )
            self.db.session.add(interpretation)
            self.db.session.commit()
            self.logger.info(f'Saved Gemini interpretation for assessment {assessment_id}')
            return True
        except IntegrityError:
            self.db.session.rollback()
            self.logger.warning(f'Interpretation already exists for assessment {assessment_id}')
            return False
        except SQLAlchemyError as e:
            self.db.session.rollback()
            self.logger.error(f'Error saving interpretation: {str(e)}')
            return False
    
    def get_assessment_with_results(self, assessment_id: int) -> Optional[Dict]:
        try:
            assessment = Assessment.query.get(assessment_id)
            if not assessment:
                return None
            
            result_dict = assessment.to_dict(include_responses=False)
            
            if assessment.results:
                result_dict['results'] = assessment.results.to_dict()
            
            if assessment.vae_outputs:
                result_dict['vae'] = assessment.vae_outputs.to_dict()
            
            if assessment.personality_classifications:
                result_dict['personality'] = assessment.personality_classifications.to_dict()
            
            if assessment.gemini_interpretations:
                result_dict['interpretation'] = assessment.gemini_interpretations.to_dict()
            
            return result_dict
        except SQLAlchemyError as e:
            self.logger.error(f'Error retrieving assessment with results: {str(e)}')
            return None
    
    def get_user_assessments(self, user_id: int, limit: int = 50) -> List[Dict]:
        try:
            assessments = Assessment.query.filter_by(user_id=user_id)\
                .order_by(desc(Assessment.created_at))\
                .limit(limit)\
                .all()
            return [a.to_dict() for a in assessments]
        except SQLAlchemyError as e:
            self.logger.error(f'Error retrieving user assessments: {str(e)}')
            return []
    
    def get_personality_distribution(self) -> Dict[str, int]:
        try:
            distribution = self.db.session.query(
                PersonalityClassification.personality_type,
                func.count(PersonalityClassification.id)
            ).group_by(PersonalityClassification.personality_type).all()
            
            return {ptype: count for ptype, count in distribution}
        except SQLAlchemyError as e:
            self.logger.error(f'Error retrieving personality distribution: {str(e)}')
            return {}
    
    def get_statistics(self) -> Dict[str, Any]:
        try:
            total_users = User.query.count()
            total_assessments = Assessment.query.count()
            completed = Assessment.query.filter_by(is_valid=True).count()
            avg_deception = self.db.session.query(func.avg(Result.deception_susceptibility)).scalar()
            
            return {
                'total_users': total_users,
                'total_assessments': total_assessments,
                'completed_assessments': completed,
                'completion_rate': completed / total_assessments if total_assessments > 0 else 0,
                'average_deception_susceptibility': float(avg_deception) if avg_deception else None,
                'personality_distribution': self.get_personality_distribution(),
            }
        except SQLAlchemyError as e:
            self.logger.error(f'Error retrieving statistics: {str(e)}')
            return {}
    
    def get_training_data_export(self, limit: Optional[int] = None) -> List[Dict]:
        try:
            query = self.db.session.query(Assessment, Result, PersonalityClassification, VAEOutput)\
                .join(Result, Assessment.id == Result.assessment_id)\
                .join(PersonalityClassification, Assessment.id == PersonalityClassification.assessment_id)\
                .join(VAEOutput, Assessment.id == VAEOutput.assessment_id)\
                .filter(Assessment.is_valid == True)
            
            if limit:
                query = query.limit(limit)
            
            results = query.all()
            
            export_data = []
            for assessment, result, personality, vae in results:
                export_data.append({
                    'assessment_id': assessment.id,
                    'age': assessment.user.age,
                    'sex': assessment.user.sex,
                    'responses': assessment.responses_json,
                    'raw_domain_scores': result.raw_domain_scores,
                    'corrected_domain_scores': result.corrected_domain_scores,
                    'deception_susceptibility': result.deception_susceptibility,
                    'personality_type': personality.personality_type,
                    'confidence': personality.confidence_score,
                    'novelty_score': vae.novelty_score,
                })
            
            self.logger.info(f'Exported {len(export_data)} training records')
            return export_data
        except SQLAlchemyError as e:
            self.logger.error(f'Error exporting training data: {str(e)}')
            return []
    
    def log_audit_action(self, action: str, resource_type: str, resource_id: int = None,
                        user_id: int = None, details: Dict = None, ip_address: str = None) -> bool:
        try:
            audit_log = AuditLog(
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                user_id=user_id,
                details=details,
                ip_address=ip_address,
            )
            self.db.session.add(audit_log)
            self.db.session.commit()
            return True
        except SQLAlchemyError as e:
            self.db.session.rollback()
            self.logger.error(f'Error logging audit action: {str(e)}')
            return False
    
    def cleanup_old_data(self, days_old: int = 90) -> int:
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
            
            old_assessments = Assessment.query.filter(Assessment.created_at < cutoff_date).all()
            count = len(old_assessments)
            
            for assessment in old_assessments:
                self.db.session.delete(assessment)
            
            self.db.session.commit()
            self.logger.info(f'Deleted {count} old assessments')
            return count
        except SQLAlchemyError as e:
            self.db.session.rollback()
            self.logger.error(f'Error cleaning up old data: {str(e)}')
            return 0
    
    def health_check(self) -> bool:
        try:
            self.db.session.execute('SELECT 1')
            return True
        except SQLAlchemyError:
            return False
