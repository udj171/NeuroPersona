# ============================================================================
# EFOPA Enhancement Module - Advanced Personality Assessment Framework
# ============================================================================
# This module implements the Enhanced Hidden Motives Framework for NeuroPersona
# including Lambda (deception susceptibility), cost functions, and authenticity metrics
# ============================================================================

import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from scipy import stats
import json

logger = logging.getLogger(__name__)

class EFOPAEnhancementEngine:
    """
    Advanced EFOPA (Enhanced Framework for Personality Observation & Assessment)
    Enhancement Engine implementing the Enhanced Hidden Motives Framework
    """
    
    # Domain Structure
    DOMAIN_MAPPINGS = {
        'R': {'name': 'Relationships', 'items': list(range(0, 5)), 'deception_weight': 0.88},
        'S': {'name': 'Status', 'items': list(range(5, 10)), 'deception_weight': 0.82},
        'C': {'name': 'Conscientiousness', 'items': list(range(10, 15)), 'deception_weight': 0.68},
        'A': {'name': 'Agreeableness', 'items': list(range(15, 20)), 'deception_weight': 0.62},
        'O': {'name': 'Openness', 'items': list(range(20, 25)), 'deception_weight': 0.58},
        'E': {'name': 'Emotional Stability', 'items': list(range(25, 30)), 'deception_weight': 0.75},
    }
    
    VALIDITY_ITEMS = list(range(30, 35))  # V31-V35 (indices 30-34)
    
    # Contradiction Detection Thresholds
    CONTRADICTION_THRESHOLDS = {
        'high_domain_low_validity': (7.0, 3.0),  # High domain score but low validity
        'high_domain_high_struggle': (7.0, 7.0),  # High domain but admits struggling
        'high_agreement_low_follow_through': (7.0, 3.0),  # High agreeableness but won't admit mistakes
    }
    
    # Cost Function Parameters
    COST_PARAMETERS = {
        'honesty_barrier_r': 2.5,     # Reproductive fitness stakes
        'honesty_barrier_s': 2.2,     # Status/resource stakes
        'honesty_barrier_c': 1.8,     # Partnership value stakes
        'honesty_barrier_a': 1.6,     # Coalition access stakes
        'honesty_barrier_o': 1.4,     # Mate selection stakes
        'honesty_barrier_e': 2.0,     # Status/partnership stakes
    }
    
    # Elephant Module Parameters (Implicit Cognition)
    ELEPHANT_PARAMETERS = {
        'implicit_bias_threshold': 0.65,
        'credibility_weight_high_domain': 0.85,
        'credibility_weight_low_domain': 0.65,
        'implicit_honesty_boost': 0.15,
    }
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.cache = {}
    
    # ========================================================================
    # PHASE 1: ADVANCED LAMBDA CALCULATION
    # ========================================================================
    
    def calculate_lambda_advanced(self, responses: List[int], domain_scores: Dict[str, float]) -> Tuple[float, Dict]:
        """
        Calculate Lambda (deception susceptibility) using advanced contradiction detection.
        Returns (lambda_score, contradiction_analysis)
        """
        contradictions = self._detect_contradictions(responses, domain_scores)
        extreme_consistency = self._detect_extreme_consistency(responses)
        response_variability = self._analyze_response_variability(responses)
        
        # Calculate lambda with weighted contradictions
        lambda_base = 0.10 * len(contradictions['detected']) + 0.05 * extreme_consistency
        lambda_adjusted = lambda_base * (1.0 + response_variability['penalty'])
        lambda_final = np.clip(lambda_adjusted, 0.0, 1.0)
        
        analysis = {
            'lambda_score': round(float(lambda_final), 4),
            'contradictions_detected': contradictions['detected'],
            'contradiction_count': len(contradictions['detected']),
            'extreme_consistency_score': round(float(extreme_consistency), 4),
            'response_variability_penalty': round(float(response_variability['penalty']), 4),
            'deception_level': self._interpret_lambda(lambda_final),
        }
        
        self.logger.info(f"Lambda Calculation: {lambda_final:.4f} ({analysis['deception_level']})")
        return lambda_final, analysis
    
    def _detect_contradictions(self, responses: List[int], domain_scores: Dict[str, float]) -> Dict:
        """
        Detect internal contradictions between domain scores and validity items.
        """
        contradictions = []
        validity_responses = [responses[i] for i in self.VALIDITY_ITEMS if i < len(responses)]
        
        # Contradiction 1: High Agreeableness but won't admit mistakes (V31)
        if domain_scores.get('A', 0) >= 7.0 and validity_responses[0] <= 3.0:
            contradictions.append({
                'type': 'agreeableness_admission_gap',
                'domain': 'A',
                'domain_score': domain_scores['A'],
                'validity_item': 'V31',
                'validity_score': validity_responses[0],
                'severity': 'high',
            })
        
        # Contradiction 2: High Openness but not genuinely humble (V32)
        if domain_scores.get('O', 0) >= 7.0 and validity_responses[1] <= 3.0:
            contradictions.append({
                'type': 'openness_humility_gap',
                'domain': 'O',
                'domain_score': domain_scores['O'],
                'validity_item': 'V32',
                'validity_score': validity_responses[1],
                'severity': 'high',
            })
        
        # Contradiction 3: High Conscientiousness but inconsistent (V33)
        if domain_scores.get('C', 0) >= 7.0 and validity_responses[2] <= 3.0:
            contradictions.append({
                'type': 'conscientiousness_consistency_gap',
                'domain': 'C',
                'domain_score': domain_scores['C'],
                'validity_item': 'V33',
                'validity_score': validity_responses[2],
                'severity': 'medium',
            })
        
        # Contradiction 4: High Emotional Stability but admits internal struggles (V34/V35)
        if domain_scores.get('E', 0) >= 7.0 and (validity_responses[3] >= 7.0 or validity_responses[4] >= 7.0):
            contradictions.append({
                'type': 'emotional_stability_struggle_gap',
                'domain': 'E',
                'domain_score': domain_scores['E'],
                'validity_items': ['V34', 'V35'],
                'validity_scores': [validity_responses[3], validity_responses[4]],
                'severity': 'medium',
            })
        
        # Contradiction 5: High Agreeableness but admits selfishness (V35)
        if domain_scores.get('A', 0) >= 7.0 and validity_responses[4] >= 7.0:
            contradictions.append({
                'type': 'agreeableness_selfishness_gap',
                'domain': 'A',
                'domain_score': domain_scores['A'],
                'validity_item': 'V35',
                'validity_score': validity_responses[4],
                'severity': 'high',
            })
        
        return {'detected': contradictions, 'count': len(contradictions)}
    
    def _detect_extreme_consistency(self, responses: List[int]) -> float:
        """
        Detect unnaturally consistent response patterns (indicator of self-deception).
        """
        validity_responses = [responses[i] for i in self.VALIDITY_ITEMS if i < len(responses)]
        
        # Count responses at extreme ends (0-2 or 8-10)
        extreme_high = sum(1 for v in validity_responses if v >= 8)
        extreme_low = sum(1 for v in validity_responses if v <= 2)
        extreme_total = extreme_high + extreme_low
        
        # Check for unnaturally low variance
        validity_std = np.std(validity_responses)
        variance_penalty = 1.0 if validity_std < 1.0 else 0.0
        
        extreme_consistency = (extreme_total * 0.1) + variance_penalty
        return np.clip(extreme_consistency, 0.0, 1.0)
    
    def _analyze_response_variability(self, responses: List[int]) -> Dict:
        """
        Analyze response variability across all items.
        """
        response_std = np.std(responses)
        response_mean = np.mean(responses)
        
        # Flag suspicious patterns
        penalty = 0.0
        if response_std < 1.5:  # Too consistent
            penalty += 0.15
        if response_mean < 2.0 or response_mean > 8.0:  # Biased toward extreme
            penalty += 0.10
        
        return {
            'std_deviation': round(float(response_std), 4),
            'mean': round(float(response_mean), 4),
            'penalty': round(float(penalty), 4),
        }
    
    def _interpret_lambda(self, lambda_value: float) -> str:
        """
        Interpret lambda deception susceptibility score.
        """
        if lambda_value < 0.35:
            return 'Low'
        elif lambda_value < 0.65:
            return 'Moderate'
        else:
            return 'High'
    
    # ========================================================================
    # PHASE 2: COST FUNCTION ANALYSIS
    # ========================================================================
    
    def calculate_domain_honesty_cost(self, domain: str, domain_score: float) -> Dict:
        """
        Calculate the honesty barrier/cost for a specific domain using evolutionary game theory.
        Higher scores = higher cost to be dishonest (higher honesty)
        """
        if domain not in self.DOMAIN_MAPPINGS:
            raise ValueError(f"Invalid domain: {domain}")
        
        domain_info = self.DOMAIN_MAPPINGS[domain]
        domain_name = domain_info['name']
        deception_weight = domain_info['deception_weight']
        
        # Base honesty cost (inverse of deception weight)
        honesty_barrier = self.COST_PARAMETERS.get(f'honesty_barrier_{domain.lower()}', 2.0)
        
        # Adjust based on domain score
        # Higher domain score = higher cost to be dishonest (honesty demonstrated)
        score_factor = (domain_score / 10.0)  # Normalize 0-10 to 0-1
        
        # Calculate effective honesty cost
        effective_honesty_cost = honesty_barrier * score_factor
        
        # Calculate mating/partnership fitness impact
        fitness_impact = deception_weight * (1.0 - score_factor)
        
        return {
            'domain': domain,
            'domain_name': domain_name,
            'domain_score': round(float(domain_score), 4),
            'honesty_barrier': round(float(honesty_barrier), 4),
            'score_factor': round(float(score_factor), 4),
            'effective_honesty_cost': round(float(effective_honesty_cost), 4),
            'deception_weight': round(float(deception_weight), 4),
            'fitness_impact_if_dishonest': round(float(fitness_impact), 4),
        }
    
    def calculate_all_domain_costs(self, domain_scores: Dict[str, float]) -> Dict:
        """
        Calculate honesty costs for all domains.
        """
        costs = {}
        for domain, score in domain_scores.items():
            costs[domain] = self.calculate_domain_honesty_cost(domain, score)
        
        # Calculate aggregate statistics
        avg_honesty_cost = np.mean([c['effective_honesty_cost'] for c in costs.values()])
        total_fitness_impact = sum(c['fitness_impact_if_dishonest'] for c in costs.values())
        
        return {
            'domain_costs': costs,
            'average_honesty_cost': round(float(avg_honesty_cost), 4),
            'total_fitness_impact': round(float(total_fitness_impact), 4),
            'analysis': 'Lower honesty costs indicate higher deception susceptibility in that domain',
        }
    
    # ========================================================================
    # PHASE 3: ELEPHANT MODULE (Implicit Cognition & Credibility Weighting)
    # ========================================================================
    
    def calculate_elephant_module(self, responses: List[int], domain_scores: Dict[str, float], 
                                  lambda_value: float) -> Dict:
        """
        Elephant module analyzes implicit cognition and credibility weighting.
        Returns implicit bias scores and weighted credibility assessments.
        """
        elephant_analysis = {}
        weighted_credibility = {}
        
        for domain, score in domain_scores.items():
            # Determine if domain score is high or low
            is_high_domain = score >= 7.0
            
            # Get implicit bias
            implicit_bias = self._calculate_implicit_bias(responses, domain, score, lambda_value)
            
            # Determine credibility weight based on domain score level
            credibility_weight = (
                self.ELEPHANT_PARAMETERS['credibility_weight_high_domain']
                if is_high_domain
                else self.ELEPHANT_PARAMETERS['credibility_weight_low_domain']
            )
            
            # Apply implicit bias adjustment
            adjusted_credibility = credibility_weight * (1.0 - implicit_bias['bias_strength'])
            
            # Apply honesty boost if implicit cognition suggests honesty
            if implicit_bias['implicit_honesty_signal']:
                adjusted_credibility += self.ELEPHANT_PARAMETERS['implicit_honesty_boost']
            
            adjusted_credibility = np.clip(adjusted_credibility, 0.0, 1.0)
            
            elephant_analysis[domain] = {
                'domain_score': round(float(score), 4),
                'is_high_domain': is_high_domain,
                'implicit_bias_score': round(float(implicit_bias['bias_strength']), 4),
                'implicit_bias_type': implicit_bias['bias_type'],
                'implicit_honesty_signal': implicit_bias['implicit_honesty_signal'],
                'base_credibility_weight': round(float(credibility_weight), 4),
                'adjusted_credibility_weight': round(float(adjusted_credibility), 4),
            }
            
            weighted_credibility[domain] = round(float(adjusted_credibility), 4)
        
        return {
            'elephant_analysis': elephant_analysis,
            'weighted_credibility_scores': weighted_credibility,
            'avg_weighted_credibility': round(float(np.mean(list(weighted_credibility.values()))), 4),
        }
    
    def _calculate_implicit_bias(self, responses: List[int], domain: str, domain_score: float, 
                                lambda_value: float) -> Dict:
        """
        Calculate implicit bias for a domain based on response patterns.
        """
        domain_indices = self.DOMAIN_MAPPINGS[domain]['items']
        domain_responses = [responses[i] for i in domain_indices if i < len(responses)]
        
        # Analyze response variability within domain
        domain_std = np.std(domain_responses)
        
        # Calculate bias strength
        bias_strength = lambda_value * (1.0 / (1.0 + domain_std))
        
        # Determine bias type
        response_mean = np.mean(domain_responses)
        if response_mean >= 7.0:
            bias_type = 'positivity_bias'  # Tendency to rate self highly
        elif response_mean <= 3.0:
            bias_type = 'negativity_bias'  # Tendency to rate self low
        else:
            bias_type = 'minimal_bias'  # Relatively balanced
        
        # Check for implicit honesty signal (consistent, moderate responses)
        implicit_honesty = domain_std >= 2.0 and 3.0 <= response_mean <= 7.0
        
        return {
            'bias_strength': bias_strength,
            'bias_type': bias_type,
            'implicit_honesty_signal': implicit_honesty,
            'domain_std': round(float(domain_std), 4),
            'response_mean': round(float(response_mean), 4),
        }
    
    # ========================================================================
    # PHASE 4: VALIDITY CHECKING & AUTHENTICITY METRICS
    # ========================================================================
    
    def calculate_validity_metrics(self, responses: List[int]) -> Dict:
        """
        Calculate comprehensive validity metrics for assessment quality.
        """
        validity_responses = [responses[i] for i in self.VALIDITY_ITEMS if i < len(responses)]
        
        if len(validity_responses) < 5:
            self.logger.warning("Insufficient validity items for comprehensive validation")
            return {'status': 'insufficient_data'}
        
        # Validity Metric 1: Admission of Mistakes (V31)
        admits_mistakes = validity_responses[0] >= 5  # Middle or above
        
        # Validity Metric 2: Humility (V32)
        genuinely_humble = validity_responses[1] >= 5
        
        # Validity Metric 3: Consistency (V33)
        consistent_across_contexts = validity_responses[2] >= 5
        
        # Validity Metric 4: Self-Awareness (V34)
        understands_motivations = validity_responses[3] >= 5
        
        # Validity Metric 5: Value-Behavior Gap (V35)
        remembers_selfishness = validity_responses[4] >= 4  # Slightly lower threshold
        
        # Calculate overall validity score
        validity_indicators = [
            admits_mistakes, genuinely_humble, consistent_across_contexts,
            understands_motivations, remembers_selfishness
        ]
        overall_validity = sum(validity_indicators) / len(validity_indicators)
        
        # Quality assessment
        if overall_validity >= 0.8:
            quality_level = 'high'
        elif overall_validity >= 0.6:
            quality_level = 'moderate'
        elif overall_validity >= 0.4:
            quality_level = 'low'
        else:
            quality_level = 'very_low'
        
        return {
            'validity_metrics': {
                'admits_mistakes': admits_mistakes,
                'genuinely_humble': genuinely_humble,
                'consistent_across_contexts': consistent_across_contexts,
                'understands_motivations': understands_motivations,
                'remembers_selfishness': remembers_selfishness,
            },
            'validity_scores': {
                'V31_admission': round(float(validity_responses[0]), 2),
                'V32_humility': round(float(validity_responses[1]), 2),
                'V33_consistency': round(float(validity_responses[2]), 2),
                'V34_awareness': round(float(validity_responses[3]), 2),
                'V35_selfishness': round(float(validity_responses[4]), 2),
            },
            'overall_validity_score': round(float(overall_validity), 4),
            'quality_level': quality_level,
        }
    
    def calculate_authenticity_metrics(self, responses: List[int], domain_scores: Dict[str, float],
                                      lambda_value: float) -> Dict:
        """
        Calculate authenticity/coherence metrics for personality consistency.
        """
        # Coherence Score: How well domain scores align with response patterns
        coherence = self._calculate_coherence_score(responses, domain_scores)
        
        # Honesty Correction: Estimate true scores accounting for deception
        honesty_correction = self._calculate_honesty_correction(domain_scores, lambda_value)
        
        # Authenticity Index: Overall authenticity of assessment
        authenticity_index = (1.0 - lambda_value) * coherence['overall_coherence']
        
        return {
            'coherence': coherence,
            'honesty_correction': honesty_correction,
            'authenticity_index': round(float(authenticity_index), 4),
            'authenticity_level': 'high' if authenticity_index >= 0.7 else 'moderate' if authenticity_index >= 0.5 else 'low',
        }
    
    def _calculate_coherence_score(self, responses: List[int], domain_scores: Dict[str, float]) -> Dict:
        """
        Calculate coherence between individual responses and domain averages.
        """
        coherence_by_domain = {}
        
        for domain, domain_indices in [(d, self.DOMAIN_MAPPINGS[d]['items']) for d in self.DOMAIN_MAPPINGS]:
            domain_responses = [responses[i] for i in domain_indices if i < len(responses)]
            domain_mean = domain_scores.get(domain, 0)
            
            # Calculate deviations
            deviations = [abs(r - domain_mean) for r in domain_responses]
            avg_deviation = np.mean(deviations)
            
            # Coherence: inverse of average deviation (normalized)
            coherence = max(0, 1.0 - (avg_deviation / 10.0))
            coherence_by_domain[domain] = round(float(coherence), 4)
        
        overall_coherence = np.mean(list(coherence_by_domain.values()))
        
        return {
            'coherence_by_domain': coherence_by_domain,
            'overall_coherence': round(float(overall_coherence), 4),
        }
    
    def _calculate_honesty_correction(self, domain_scores: Dict[str, float], lambda_value: float) -> Dict:
        """
        Estimate corrected scores assuming deception based on lambda.
        """
        corrected_scores = {}
        
        for domain, score in domain_scores.items():
            # For high-scoring domains, apply deception correction
            if score >= 6.0:
                # Estimate deception magnitude
                deception_amount = lambda_value * 2.0  # Max 2-point correction
                corrected = max(0, score - deception_amount)
            else:
                corrected = score
            
            corrected_scores[domain] = round(float(corrected), 4)
        
        return {'corrected_domain_scores': corrected_scores}
    
    # ========================================================================
    # INTEGRATED PIPELINE
    # ========================================================================
    
    def process_efopa_complete(self, responses: List[int], age: int, 
                               raw_domain_scores: Dict[str, float]) -> Dict:
        """
        Complete EFOPA processing pipeline.
        Integrates all enhancement modules.
        """
        try:
            # Step 1: Advanced Lambda Calculation
            lambda_value, lambda_analysis = self.calculate_lambda_advanced(responses, raw_domain_scores)
            
            # Step 2: Cost Function Analysis
            domain_costs = self.calculate_all_domain_costs(raw_domain_scores)
            
            # Step 3: Elephant Module (Implicit Cognition)
            elephant_module = self.calculate_elephant_module(responses, raw_domain_scores, lambda_value)
            
            # Step 4: Validity Checking
            validity_metrics = self.calculate_validity_metrics(responses)
            
            # Step 5: Authenticity Metrics
            authenticity_metrics = self.calculate_authenticity_metrics(
                responses, raw_domain_scores, lambda_value
            )
            
            result = {
                'status': 'success',
                'lambda_analysis': lambda_analysis,
                'domain_costs': domain_costs,
                'elephant_module': elephant_module,
                'validity_metrics': validity_metrics,
                'authenticity_metrics': authenticity_metrics,
                'processing_complete': True,
            }
            
            self.logger.info("EFOPA complete processing pipeline executed successfully")
            return result
        
        except Exception as e:
            self.logger.error(f"Error in EFOPA processing pipeline: {str(e)}", exc_info=True)
            raise


# ============================================================================
# Module Initialization
# ============================================================================

efopa_engine = EFOPAEnhancementEngine()
