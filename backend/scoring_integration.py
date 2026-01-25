# ============================================================================
# Scoring Integration Module - EFOPA Enhancement Integration
# ============================================================================
# This module integrates the EFOPA enhancement engine with the existing
# scoring pipeline while maintaining backward compatibility
# ============================================================================

import numpy as np
from typing import Dict, List, Tuple
import logging
from efopa_enhancement_module import efopa_engine

logger = logging.getLogger(__name__)

class EnhancedScoringIntegration:
    """
    Integration layer between the existing ScoringEngine and EFOPA enhancement modules.
    Maintains backward compatibility while adding advanced features.
    """
    
    def __init__(self, scoring_engine):
        """
        Initialize integration with existing scoring engine.
        
        Args:
            scoring_engine: The existing ScoringEngine instance
        """
        self.scoring_engine = scoring_engine
        self.efopa_engine = efopa_engine
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def process_with_efopa_enhancement(self, responses: List[int], age: int) -> Dict:
        """
        Process assessment with EFOPA enhancement layers.
        Returns comprehensive results including all advanced metrics.
        """
        try:
            # Step 1: Use existing scoring engine for base calculation
            self.logger.info("Step 1: Computing base scores using ScoringEngine")
            base_result = self.scoring_engine.process_assessment(responses, age)
            
            # Step 2: Apply EFOPA enhancement pipeline
            self.logger.info("Step 2: Applying EFOPA enhancement pipeline")
            efopa_result = self.efopa_engine.process_efopa_complete(
                responses, age, base_result['raw_domain_scores']
            )
            
            # Step 3: Integrate results
            self.logger.info("Step 3: Integrating base and EFOPA results")
            integrated_result = self._integrate_results(base_result, efopa_result)
            
            # Step 4: Calculate metadata and summaries
            self.logger.info("Step 4: Computing metadata and summaries")
            integrated_result['metadata'] = self._calculate_metadata(integrated_result)
            
            self.logger.info("EFOPA enhancement processing completed successfully")
            return integrated_result
        
        except Exception as e:
            self.logger.error(f"Error in EFOPA enhancement processing: {str(e)}", exc_info=True)
            raise
    
    def _integrate_results(self, base_result: Dict, efopa_result: Dict) -> Dict:
        """
        Integrate base scoring results with EFOPA enhancement results.
        """
        integrated = {
            # Original base results (for backward compatibility)
            'base_scoring': {
                'raw_domain_scores': base_result['raw_domain_scores'],
                'deception_susceptibility': base_result['deception_susceptibility'],
                'corrected_domain_scores': base_result['corrected_domain_scores'],
                'domain_biases': base_result['domain_biases'],
                'scaled_scores': base_result['scaled_scores'],
            },
            # EFOPA Enhancement Results
            'efopa_enhancement': {
                'lambda_analysis': efopa_result['lambda_analysis'],
                'domain_costs': efopa_result['domain_costs'],
                'elephant_module': efopa_result['elephant_module'],
                'validity_metrics': efopa_result['validity_metrics'],
                'authenticity_metrics': efopa_result['authenticity_metrics'],
            },
            # VAE Input (from base result)
            'vae_input': base_result['vae_input'],
            'validity_scores': base_result.get('validity_scores', {}),
        }
        
        return integrated
    
    def _calculate_metadata(self, integrated_result: Dict) -> Dict:
        """
        Calculate comprehensive metadata and summaries.
        """
        lambda_analysis = integrated_result['efopa_enhancement']['lambda_analysis']
        validity_metrics = integrated_result['efopa_enhancement']['validity_metrics']
        authenticity = integrated_result['efopa_enhancement']['authenticity_metrics']
        elephant = integrated_result['efopa_enhancement']['elephant_module']
        
        # Quality indicators
        assessment_quality = {
            'lambda_score': lambda_analysis['lambda_score'],
            'deception_level': lambda_analysis['deception_level'],
            'validity_quality': validity_metrics.get('quality_level', 'unknown'),
            'authenticity_score': authenticity['authenticity_index'],
            'average_credibility': elephant['avg_weighted_credibility'],
        }
        
        # Risk flags
        risk_flags = []
        
        if lambda_analysis['lambda_score'] > 0.65:
            risk_flags.append('high_deception_susceptibility')
        
        if lambda_analysis['contradiction_count'] >= 3:
            risk_flags.append('multiple_contradictions_detected')
        
        if validity_metrics.get('quality_level') in ['low', 'very_low']:
            risk_flags.append('low_response_validity')
        
        if authenticity['authenticity_index'] < 0.5:
            risk_flags.append('low_authenticity_score')
        
        # Recommendations
        recommendations = self._generate_recommendations(
            assessment_quality, risk_flags, integrated_result
        )
        
        return {
            'assessment_quality': assessment_quality,
            'risk_flags': risk_flags,
            'recommendations': recommendations,
            'processing_timestamp': np.datetime64('now'),
        }
    
    def _generate_recommendations(self, quality: Dict, risk_flags: List[str], 
                                 result: Dict) -> List[str]:
        """
        Generate recommendations based on assessment quality and risk flags.
        """
        recommendations = []
        
        if 'high_deception_susceptibility' in risk_flags:
            recommendations.append(
                'High deception susceptibility detected. Consider follow-up questions in identified domains.'
            )
        
        if 'multiple_contradictions_detected' in risk_flags:
            contradictions = result['efopa_enhancement']['lambda_analysis']['contradictions_detected']
            domains = set(c.get('domain') for c in contradictions if 'domain' in c)
            recommendations.append(
                f"Internal contradictions detected in domains: {', '.join(domains)}. "
                "Recommend domain-specific clarification."
            )
        
        if 'low_response_validity' in risk_flags:
            recommendations.append(
                'Low response validity detected. Assessment may need re-administration with clearer instructions.'
            )
        
        if 'low_authenticity_score' in risk_flags:
            recommendations.append(
                'Assessment shows low authenticity indicators. Results should be interpreted cautiously.'
            )
        
        if quality['average_credibility'] < 0.6:
            recommendations.append(
                'Weighted credibility score is below acceptable threshold. Consider manual review.'
            )
        
        if not recommendations:
            recommendations.append('Assessment quality is acceptable. Results are reliable for interpretation.')
        
        return recommendations
    
    def calculate_comparative_scores(self, responses: List[int], age: int) -> Dict:
        """
        Calculate comparative analysis between base scores and EFOPA-corrected scores.
        """
        base_result = self.scoring_engine.process_assessment(responses, age)
        efopa_result = self.efopa_engine.process_efopa_complete(
            responses, age, base_result['raw_domain_scores']
        )
        
        raw_scores = base_result['raw_domain_scores']
        elephant_credibility = efopa_result['elephant_module']['weighted_credibility_scores']
        
        comparative = {}
        for domain in raw_scores:
            raw = raw_scores[domain]
            credibility = elephant_credibility.get(domain, 0.5)
            
            # Credibility-weighted score (accounts for implicit bias)
            credibility_weighted = raw * credibility
            
            comparative[domain] = {
                'raw_score': round(float(raw), 4),
                'weighted_credibility': round(float(credibility), 4),
                'credibility_weighted_score': round(float(credibility_weighted), 4),
                'adjustment_magnitude': round(float(abs(raw - credibility_weighted)), 4),
            }
        
        return {'comparative_analysis': comparative}
    
    def get_domain_insights(self, integrated_result: Dict, domain: str) -> Dict:
        """
        Get detailed insights for a specific domain.
        """
        if domain not in ['R', 'S', 'C', 'A', 'O', 'E']:
            raise ValueError(f"Invalid domain: {domain}")
        
        base = integrated_result['base_scoring']
        efopa = integrated_result['efopa_enhancement']
        
        raw_score = base['raw_domain_scores'].get(domain, 0)
        corrected_score = base['corrected_domain_scores'].get(domain, 0)
        bias = base['domain_biases'].get(domain, 0)
        
        domain_cost = None
        for d_cost in efopa['domain_costs']['domain_costs'].values():
            if d_cost['domain'] == domain:
                domain_cost = d_cost
                break
        
        elephant_info = efopa['elephant_module']['elephant_analysis'].get(domain, {})
        
        return {
            'domain': domain,
            'domain_name': self.efopa_engine.DOMAIN_MAPPINGS[domain]['name'],
            'scoring': {
                'raw_score': round(float(raw_score), 4),
                'bias_applied': round(float(bias), 4),
                'corrected_score': round(float(corrected_score), 4),
            },
            'cost_analysis': domain_cost,
            'elephant_analysis': elephant_info,
            'interpretation': self._generate_domain_interpretation(domain, raw_score, bias),
        }
    
    def _generate_domain_interpretation(self, domain: str, score: float, bias: float) -> str:
        """
        Generate human-readable interpretation for a domain score.
        """
        score_level = 'low' if score < 4 else 'moderate' if score < 6 else 'high'
        bias_direction = 'inflated' if bias > 0.2 else 'deflated' if bias < -0.2 else 'minimal'
        
        domain_names = {
            'R': 'Relationships',
            'S': 'Status',
            'C': 'Conscientiousness',
            'A': 'Agreeableness',
            'O': 'Openness',
            'E': 'Emotional Stability',
        }
        
        return (
            f"{domain_names[domain]}: {score_level.capitalize()} (score {score:.1f}). "
            f"Potential {bias_direction} bias detected ({bias:.2f}). "
            f"Corrected score: {score - bias:.1f}."
        )


# ============================================================================
# Helper Functions for Integration
# ============================================================================

def create_enhanced_scoring_integration(scoring_engine):
    """
    Factory function to create enhanced scoring integration.
    """
    return EnhancedScoringIntegration(scoring_engine)
