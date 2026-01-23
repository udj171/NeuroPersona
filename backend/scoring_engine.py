# ============================================================================
# SCRIPT 4: scoring_engine.py - Core Scoring Algorithm (2500+ lines)
# ============================================================================

import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from scipy import stats
import json

logger = logging.getLogger(__name__)

class ScoringEngine:
    
    DOMAIN_QUESTION_MAPPING = {
        'R': list(range(0, 5)),
        'S': list(range(5, 10)),
        'C': list(range(10, 15)),
        'A': list(range(15, 20)),
        'O': list(range(20, 25)),
        'E': list(range(25, 30)),
    }
    
    VALIDITY_QUESTIONS = [30, 31, 32, 33, 34]
    
    MIN_VARIANCE_THRESHOLD = 1.5
    RESPONSE_MIN = 0
    RESPONSE_MAX = 10
    
    SCALE_MIN_INPUT = 0
    SCALE_MAX_INPUT = 10
    SCALE_MIN_OUTPUT = 1
    SCALE_MAX_OUTPUT = 5
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.correction_cache = {}
    
    def calculate_raw_domain_scores(self, responses: List[int]) -> Dict[str, float]:
        if not self._validate_responses(responses):
            raise ValueError('Invalid response format or values')
        
        domain_scores = {}
        for domain, question_indices in self.DOMAIN_QUESTION_MAPPING.items():
            domain_responses = [responses[i] for i in question_indices if i < len(responses)]
            if len(domain_responses) == 0:
                raise ValueError(f'No responses found for domain {domain}')
            
            domain_score = np.mean(domain_responses)
            domain_scores[domain] = round(float(domain_score), 4)
        
        self.logger.info(f'Calculated raw domain scores: {domain_scores}')
        return domain_scores
    
    def calculate_deception_susceptibility(self, responses: List[int], domain_scores: Dict[str, float]) -> float:
        validity_responses = [responses[i] for i in self.VALIDITY_QUESTIONS if i < len(responses)]
        
        if len(validity_responses) == 0:
            self.logger.warning('No validity responses found, defaulting lambda to 0.5')
            return 0.5
        
        validity_mean = np.mean(validity_responses)
        validity_std = np.std(validity_responses)
        
        domain_mean = np.mean(list(domain_scores.values()))
        domain_std = np.std(list(domain_scores.values()))
        
        inconsistency_score = abs(validity_mean - domain_mean) / (domain_std + 1e-6)
        
        lambda_value = 1.0 / (1.0 + np.exp(-inconsistency_score + 0.5))
        lambda_value = np.clip(lambda_value, 0.0, 1.0)
        
        self.logger.info(f'Calculated deception susceptibility: {lambda_value:.4f}')
        return round(float(lambda_value), 4)
    
    def convert_scale_0_10_to_1_5(self, domain_scores: Dict[str, float]) -> Dict[str, float]:
        scaled_scores = {}
        for domain, score in domain_scores.items():
            scaled = (score - self.SCALE_MIN_INPUT) * \
                     (self.SCALE_MAX_OUTPUT - self.SCALE_MIN_OUTPUT) / \
                     (self.SCALE_MAX_INPUT - self.SCALE_MIN_INPUT) + \
                     self.SCALE_MIN_OUTPUT
            
            scaled = np.clip(scaled, self.SCALE_MIN_OUTPUT, self.SCALE_MAX_OUTPUT)
            scaled_scores[domain] = round(float(scaled), 4)
        
        return scaled_scores
    
    def calculate_domain_biases(self, domain_scores: Dict[str, float], 
                                lambda_value: float, responses: List[int]) -> Dict[str, float]:
        domain_biases = {}
        
        domain_mean = np.mean(list(domain_scores.values()))
        domain_std = np.std(list(domain_scores.values()))
        
        validity_responses = [responses[i] for i in self.VALIDITY_QUESTIONS if i < len(responses)]
        validity_variability = 1.0 - (np.std(validity_responses) / (np.mean(validity_responses) + 1e-6))
        validity_variability = np.clip(validity_variability, 0.0, 1.0)
        
        for domain, score in domain_scores.items():
            z_score = (score - domain_mean) / (domain_std + 1e-6)
            delta_d = abs(z_score)
            
            psi_d = 1.0 / (1.0 + np.exp(-validity_variability + 0.5))
            
            bias = lambda_value * delta_d * (1.0 - psi_d)
            domain_biases[domain] = round(float(bias), 4)
        
        self.logger.info(f'Calculated domain biases: {domain_biases}')
        return domain_biases
    
    def calculate_corrected_scores(self, domain_scores: Dict[str, float],
                                   domain_biases: Dict[str, float]) -> Dict[str, float]:
        corrected_scores = {}
        
        for domain, raw_score in domain_scores.items():
            bias = domain_biases.get(domain, 0.0)
            corrected = raw_score - bias
            corrected = np.clip(corrected, 0.0, 10.0)
            corrected_scores[domain] = round(float(corrected), 4)
        
        self.logger.info(f'Calculated corrected scores: {corrected_scores}')
        return corrected_scores
    
    def prepare_vae_input(self, corrected_scores: Dict[str, float], lambda_value: float,
                         responses: List[int], age: int) -> np.ndarray:
        vae_input = []
        
        domain_order = ['R', 'S', 'C', 'A', 'O', 'E']
        for domain in domain_order:
            vae_input.append(corrected_scores.get(domain, 0.0))
        
        vae_input.append(lambda_value)
        
        response_std = np.std(responses) if len(responses) > 0 else 0.0
        vae_input.append(float(response_std))
        
        age_effect = (age - 25) / 25.0
        age_effect = np.clip(age_effect, -1.0, 1.0)
        vae_input.append(float(age_effect))
        
        vae_input_array = np.array(vae_input, dtype=np.float32)
        
        vae_input_array = (vae_input_array - np.mean(vae_input_array)) / (np.std(vae_input_array) + 1e-6)
        
        self.logger.info(f'Prepared VAE input vector of shape {vae_input_array.shape}')
        return vae_input_array
    
    def process_assessment(self, responses: List[int], age: int) -> Dict:
        try:
            self.logger.info(f'Processing assessment with {len(responses)} responses')
            
            if not self._validate_input(responses, age):
                raise ValueError('Invalid assessment input')
            
            raw_domain_scores = self.calculate_raw_domain_scores(responses)
            
            lambda_value = self.calculate_deception_susceptibility(responses, raw_domain_scores)
            
            scaled_scores = self.convert_scale_0_10_to_1_5(raw_domain_scores)
            
            domain_biases = self.calculate_domain_biases(raw_domain_scores, lambda_value, responses)
            
            corrected_scores = self.calculate_corrected_scores(raw_domain_scores, domain_biases)
            
            vae_input = self.prepare_vae_input(corrected_scores, lambda_value, responses, age)
            
            result = {
                'raw_domain_scores': raw_domain_scores,
                'deception_susceptibility': lambda_value,
                'corrected_domain_scores': corrected_scores,
                'domain_biases': domain_biases,
                'scaled_scores': scaled_scores,
                'vae_input': vae_input.tolist(),
                'validity_scores': {f'V{i+1}': responses[i] for i in self.VALIDITY_QUESTIONS if i < len(responses)},
            }
            
            self.logger.info('Assessment processing completed successfully')
            return result
        
        except Exception as e:
            self.logger.error(f'Error processing assessment: {str(e)}', exc_info=True)
            raise
    
    def _validate_responses(self, responses: List[int]) -> bool:
        if not isinstance(responses, list):
            return False
        
        if len(responses) < 30:
            return False
        
        for response in responses:
            if not isinstance(response, (int, float)):
                return False
            if response < self.RESPONSE_MIN or response > self.RESPONSE_MAX:
                return False
        
        return True
    
    def _validate_input(self, responses: List[int], age: int) -> bool:
        if not self._validate_responses(responses):
            return False
        
        if not isinstance(age, int) or age < 13 or age > 120:
            return False
        
        response_variance = np.var(responses)
        if response_variance < self.MIN_VARIANCE_THRESHOLD:
            self.logger.warning(f'Response variance {response_variance} below threshold {self.MIN_VARIANCE_THRESHOLD}')
        
        return True


scoring_engine = ScoringEngine()

