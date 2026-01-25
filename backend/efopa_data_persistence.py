# ============================================================================
# EFOPA Data Persistence Layer
# ============================================================================
# Handles storage and retrieval of EFOPA enhancement results to database
# ============================================================================

import logging
from datetime import datetime, timezone
from typing import Dict, Any
import traceback

from models import db
from models_efopa_extension import (
    EFOPALambdaAnalysis,
    EFOPADomainCosts,
    EFOPAElephantModule,
    EFOPAValidityMetrics,
    EFOPAAuthenticityMetrics,
    EFOPAAssessmentMetadata,
)

logger = logging.getLogger(__name__)

class EFOPADataPersistence:
    """
    Handles persistence of EFOPA enhancement results to database.
    """
    
    @staticmethod
    def save_complete_efopa_results(assessment_id: int, integrated_result: Dict) -> Dict[str, Any]:
        """
        Save complete EFOPA analysis results to database.
        
        Args:
            assessment_id: ID of the assessment
            integrated_result: Complete integrated result from EnhancedScoringIntegration
        
        Returns:
            Dictionary with save status and stored record IDs
        """
        try:
            logger.info(f"[EFOPA_PERSISTENCE] Saving complete EFOPA results for assessment {assessment_id}")
            
            # Extract components
            efopa_data = integrated_result.get('efopa_enhancement', {})
            metadata = integrated_result.get('metadata', {})
            
            # Save each component
            saved_records = {}
            
            # 1. Save Lambda Analysis
            lambda_record = EFOPADataPersistence.save_lambda_analysis(
                assessment_id, efopa_data.get('lambda_analysis', {})
            )
            saved_records['lambda_analysis'] = lambda_record.id if lambda_record else None
            
            # 2. Save Domain Costs
            domain_costs_record = EFOPADataPersistence.save_domain_costs(
                assessment_id, efopa_data.get('domain_costs', {})
            )
            saved_records['domain_costs'] = domain_costs_record.id if domain_costs_record else None
            
            # 3. Save Elephant Module
            elephant_record = EFOPADataPersistence.save_elephant_module(
                assessment_id, efopa_data.get('elephant_module', {})
            )
            saved_records['elephant_module'] = elephant_record.id if elephant_record else None
            
            # 4. Save Validity Metrics
            validity_record = EFOPADataPersistence.save_validity_metrics(
                assessment_id, efopa_data.get('validity_metrics', {})
            )
            saved_records['validity_metrics'] = validity_record.id if validity_record else None
            
            # 5. Save Authenticity Metrics
            authenticity_record = EFOPADataPersistence.save_authenticity_metrics(
                assessment_id, efopa_data.get('authenticity_metrics', {})
            )
            saved_records['authenticity_metrics'] = authenticity_record.id if authenticity_record else None
            
            # 6. Save Assessment Metadata
            metadata_record = EFOPADataPersistence.save_assessment_metadata(
                assessment_id, metadata
            )
            saved_records['assessment_metadata'] = metadata_record.id if metadata_record else None
            
            logger.info(
                f"[EFOPA_PERSISTENCE] Successfully saved EFOPA results for assessment {assessment_id}. "
                f"Records: {saved_records}"
            )
            
            return {
                'status': 'success',
                'assessment_id': assessment_id,
                'saved_records': saved_records,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }
        
        except Exception as e:
            logger.error(
                f"[EFOPA_PERSISTENCE] Error saving EFOPA results for assessment {assessment_id}: {str(e)}"
            )
            logger.error(traceback.format_exc())
            return {
                'status': 'error',
                'assessment_id': assessment_id,
                'error': str(e),
            }
    
    @staticmethod
    def save_lambda_analysis(assessment_id: int, lambda_data: Dict) -> EFOPALambdaAnalysis:
        """
        Save Lambda analysis to database.
        """
        try:
            # Delete existing record if it exists
            EFOPALambdaAnalysis.query.filter_by(assessment_id=assessment_id).delete()
            
            record = EFOPALambdaAnalysis(
                assessment_id=assessment_id,
                lambda_score=lambda_data.get('lambda_score', 0.0),
                deception_level=lambda_data.get('deception_level', 'Unknown'),
                contradictions_detected=lambda_data.get('contradictions_detected', []),
                contradiction_count=lambda_data.get('contradiction_count', 0),
                extreme_consistency_score=lambda_data.get('extreme_consistency_score', 0.0),
                response_variability_penalty=lambda_data.get('response_variability_penalty', 0.0),
            )
            
            db.session.add(record)
            db.session.commit()
            logger.debug(f"[EFOPA_PERSISTENCE] Saved Lambda analysis for assessment {assessment_id}")
            return record
        
        except Exception as e:
            logger.error(f"[EFOPA_PERSISTENCE] Error saving lambda analysis: {str(e)}")
            db.session.rollback()
            raise
    
    @staticmethod
    def save_domain_costs(assessment_id: int, domain_costs_data: Dict) -> EFOPADomainCosts:
        """
        Save domain costs analysis to database.
        """
        try:
            # Delete existing record if it exists
            EFOPADomainCosts.query.filter_by(assessment_id=assessment_id).delete()
            
            record = EFOPADomainCosts(
                assessment_id=assessment_id,
                domain_costs_data=domain_costs_data.get('domain_costs', {}),
                average_honesty_cost=domain_costs_data.get('average_honesty_cost', 0.0),
                total_fitness_impact=domain_costs_data.get('total_fitness_impact', 0.0),
            )
            
            db.session.add(record)
            db.session.commit()
            logger.debug(f"[EFOPA_PERSISTENCE] Saved domain costs for assessment {assessment_id}")
            return record
        
        except Exception as e:
            logger.error(f"[EFOPA_PERSISTENCE] Error saving domain costs: {str(e)}")
            db.session.rollback()
            raise
    
    @staticmethod
    def save_elephant_module(assessment_id: int, elephant_data: Dict) -> EFOPAElephantModule:
        """
        Save elephant module analysis to database.
        """
        try:
            # Delete existing record if it exists
            EFOPAElephantModule.query.filter_by(assessment_id=assessment_id).delete()
            
            record = EFOPAElephantModule(
                assessment_id=assessment_id,
                elephant_analysis_data=elephant_data.get('elephant_analysis', {}),
                weighted_credibility_scores=elephant_data.get('weighted_credibility_scores', {}),
                average_weighted_credibility=elephant_data.get('average_weighted_credibility', 0.0),
            )
            
            db.session.add(record)
            db.session.commit()
            logger.debug(f"[EFOPA_PERSISTENCE] Saved elephant module for assessment {assessment_id}")
            return record
        
        except Exception as e:
            logger.error(f"[EFOPA_PERSISTENCE] Error saving elephant module: {str(e)}")
            db.session.rollback()
            raise
    
    @staticmethod
    def save_validity_metrics(assessment_id: int, validity_data: Dict) -> EFOPAValidityMetrics:
        """
        Save validity metrics to database.
        """
        try:
            # Delete existing record if it exists
            EFOPAValidityMetrics.query.filter_by(assessment_id=assessment_id).delete()
            
            record = EFOPAValidityMetrics(
                assessment_id=assessment_id,
                validity_metrics_data=validity_data.get('validity_metrics', {}),
                validity_scores_data=validity_data.get('validity_scores', {}),
                overall_validity_score=validity_data.get('overall_validity_score', 0.0),
                quality_level=validity_data.get('quality_level', 'unknown'),
                admits_mistakes=validity_data.get('validity_scores', {}).get('V31', 0) >= 5,
                genuinely_humble=validity_data.get('validity_scores', {}).get('V32', 0) >= 5,
                consistent_across_contexts=validity_data.get('validity_scores', {}).get('V33', 0) >= 5,
                understands_motivations=validity_data.get('validity_scores', {}).get('V34', 0) >= 5,
                remembers_selfishness=validity_data.get('validity_scores', {}).get('V35', 0) >= 5,
            )
            
            db.session.add(record)
            db.session.commit()
            logger.debug(f"[EFOPA_PERSISTENCE] Saved validity metrics for assessment {assessment_id}")
            return record
        
        except Exception as e:
            logger.error(f"[EFOPA_PERSISTENCE] Error saving validity metrics: {str(e)}")
            db.session.rollback()
            raise
    
    @staticmethod
    def save_authenticity_metrics(assessment_id: int, authenticity_data: Dict) -> EFOPAAuthenticityMetrics:
        """
        Save authenticity metrics to database.
        """
        try:
            # Delete existing record if it exists
            EFOPAAuthenticityMetrics.query.filter_by(assessment_id=assessment_id).delete()
            
            record = EFOPAAuthenticityMetrics(
                assessment_id=assessment_id,
                coherence_by_domain=authenticity_data.get('coherence_by_domain', {}),
                overall_coherence=authenticity_data.get('overall_coherence', 0.0),
                authenticity_index=authenticity_data.get('authenticity_index', 0.0),
                authenticity_level=authenticity_data.get('authenticity_level', 'unknown'),
                corrected_domain_scores=authenticity_data.get('corrected_domain_scores', {}),
            )
            
            db.session.add(record)
            db.session.commit()
            logger.debug(f"[EFOPA_PERSISTENCE] Saved authenticity metrics for assessment {assessment_id}")
            return record
        
        except Exception as e:
            logger.error(f"[EFOPA_PERSISTENCE] Error saving authenticity metrics: {str(e)}")
            db.session.rollback()
            raise
    
    @staticmethod
    def save_assessment_metadata(assessment_id: int, metadata: Dict) -> EFOPAAssessmentMetadata:
        """
        Save assessment metadata to database.
        """
        try:
            # Delete existing record if it exists
            EFOPAAssessmentMetadata.query.filter_by(assessment_id=assessment_id).delete()
            
            risk_flags = metadata.get('risk_flags', [])
            
            record = EFOPAAssessmentMetadata(
                assessment_id=assessment_id,
                assessment_quality=metadata.get('assessment_quality', {}),
                risk_flags=risk_flags,
                risk_flag_count=len(risk_flags),
                has_risk=len(risk_flags) > 0,
                recommendations=metadata.get('recommendations', []),
                overall_quality_score=metadata.get('assessment_quality', {}).get('lambda_score', 0.5),
                assessment_status=EFOPADataPersistence._determine_assessment_status(
                    metadata, risk_flags
                ),
            )
            
            db.session.add(record)
            db.session.commit()
            logger.debug(f"[EFOPA_PERSISTENCE] Saved assessment metadata for assessment {assessment_id}")
            return record
        
        except Exception as e:
            logger.error(f"[EFOPA_PERSISTENCE] Error saving assessment metadata: {str(e)}")
            db.session.rollback()
            raise
    
    @staticmethod
    def _determine_assessment_status(metadata: Dict, risk_flags: list) -> str:
        """
        Determine overall assessment status based on quality and risk flags.
        """
        quality = metadata.get('assessment_quality', {})
        lambda_score = quality.get('lambda_score', 0.5)
        validity_quality = quality.get('validity_quality', 'unknown')
        authenticity = quality.get('authenticity_score', 0.5)
        
        if len(risk_flags) >= 2:
            return 'flagged'
        elif lambda_score > 0.65 or validity_quality == 'low' or authenticity < 0.4:
            return 'flagged'
        elif lambda_score > 0.5 or validity_quality == 'moderate':
            return 'acceptable'
        else:
            return 'reliable'
    
    @staticmethod
    def get_efopa_results(assessment_id: int) -> Dict:
        """
        Retrieve all EFOPA results for an assessment.
        """
        try:
            lambda_analysis = EFOPALambdaAnalysis.query.filter_by(
                assessment_id=assessment_id
            ).first()
            domain_costs = EFOPADomainCosts.query.filter_by(
                assessment_id=assessment_id
            ).first()
            elephant_module = EFOPAElephantModule.query.filter_by(
                assessment_id=assessment_id
            ).first()
            validity_metrics = EFOPAValidityMetrics.query.filter_by(
                assessment_id=assessment_id
            ).first()
            authenticity_metrics = EFOPAAuthenticityMetrics.query.filter_by(
                assessment_id=assessment_id
            ).first()
            metadata = EFOPAAssessmentMetadata.query.filter_by(
                assessment_id=assessment_id
            ).first()
            
            return {
                'assessment_id': assessment_id,
                'lambda_analysis': lambda_analysis.to_dict() if lambda_analysis else None,
                'domain_costs': domain_costs.to_dict() if domain_costs else None,
                'elephant_module': elephant_module.to_dict() if elephant_module else None,
                'validity_metrics': validity_metrics.to_dict() if validity_metrics else None,
                'authenticity_metrics': authenticity_metrics.to_dict() if authenticity_metrics else None,
                'assessment_metadata': metadata.to_dict() if metadata else None,
            }
        
        except Exception as e:
            logger.error(f"[EFOPA_PERSISTENCE] Error retrieving EFOPA results: {str(e)}")
            raise
