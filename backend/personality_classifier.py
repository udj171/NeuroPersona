# ============================================================================
# SCRIPT 10: personality_classifier.py - Type Classification (2500+ lines)
# ============================================================================

import logging
import numpy as np
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

class PersonalityClassifier:
    
    PERSONALITY_TYPES = {
        'A': {
            'name': 'Analytical Leader',
            'description': 'Highly logical and strategic thinker',
            'traits': ['logical', 'strategic', 'analytical'],
            'characteristics': 'Excels in problem-solving and detailed analysis',
        },
        'B': {
            'name': 'Dynamic Innovator',
            'description': 'Creative and adaptable personality',
            'traits': ['creative', 'adaptable', 'innovative'],
            'characteristics': 'Thrives in changing environments',
        },
        'C': {
            'name': 'Balanced Pragmatist',
            'description': 'Practical and methodical approach',
            'traits': ['practical', 'methodical', 'reliable'],
            'characteristics': 'Focuses on realistic outcomes',
        },
        'D': {
            'name': 'Empathetic Connector',
            'description': 'Socially aware and emotionally intelligent',
            'traits': ['empathetic', 'supportive', 'social'],
            'characteristics': 'Builds strong relationships',
        },
        'E': {
            'name': 'Visionary Dreamer',
            'description': 'Imaginative and idealistic personality',
            'traits': ['imaginative', 'visionary', 'idealistic'],
            'characteristics': 'Inspires others through vision',
        },
        'F': {
            'name': 'Grounded Realist',
            'description': 'Practical and observant personality',
            'traits': ['practical', 'observant', 'grounded'],
            'characteristics': 'Values stability and tradition',
        },
    }
    
    DOMAIN_CHARACTERISTICS = {
        'R': 'Resilience - Emotional stability and stress management',
        'S': 'Social Awareness - Understanding social dynamics',
        'C': 'Conscientiousness - Attention to detail and organization',
        'A': 'Adaptability - Flexibility and change management',
        'O': 'Openness - Creativity and intellectual curiosity',
        'E': 'Extroversion - Social engagement and dominance',
    }
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def classify(self, corrected_scores: Dict[str, float], 
                deception_susceptibility: float) -> Tuple[str, Dict]:
        try:
            if not self._validate_scores(corrected_scores):
                self.logger.error('Invalid score format')
                return 'A', self._get_type_details('A')
            
            personality_type = self._determine_type(corrected_scores, deception_susceptibility)
            details = self._get_type_details(personality_type)
            
            self.logger.info(f'Classified personality as type {personality_type}')
            return personality_type, details
        
        except Exception as e:
            self.logger.error(f'Error in classification: {str(e)}')
            return 'A', self._get_type_details('A')
    
    def _validate_scores(self, scores: Dict[str, float]) -> bool:
        required_domains = ['R', 'S', 'C', 'A', 'O', 'E']
        
        if not isinstance(scores, dict):
            return False
        
        if not all(domain in scores for domain in required_domains):
            return False
        
        for score in scores.values():
            if not isinstance(score, (int, float)) or score < 0 or score > 10:
                return False
        
        return True
    
    def _determine_type(self, scores: Dict[str, float], 
                       deception_susceptibility: float) -> str:
        domain_values = [scores.get(d, 0) for d in ['R', 'S', 'C', 'A', 'O', 'E']]
        
        r_score = scores.get('R', 0)
        s_score = scores.get('S', 0)
        c_score = scores.get('C', 0)
        a_score = scores.get('A', 0)
        o_score = scores.get('O', 0)
        e_score = scores.get('E', 0)
        
        mean_score = np.mean(domain_values)
        
        if r_score > mean_score and c_score > mean_score and s_score < mean_score:
            return 'A'
        elif o_score > mean_score and e_score > mean_score and c_score < mean_score:
            return 'B'
        elif c_score > mean_score and r_score > mean_score and o_score < mean_score:
            return 'C'
        elif s_score > mean_score and e_score > mean_score and r_score < mean_score:
            return 'D'
        elif o_score > mean_score and a_score > mean_score:
            return 'E'
        else:
            return 'F'
    
    def _get_type_details(self, personality_type: str) -> Dict:
        if personality_type not in self.PERSONALITY_TYPES:
            personality_type = 'A'
        
        return {
            'type': personality_type,
            'name': self.PERSONALITY_TYPES[personality_type]['name'],
            'description': self.PERSONALITY_TYPES[personality_type]['description'],
            'traits': self.PERSONALITY_TYPES[personality_type]['traits'],
            'characteristics': self.PERSONALITY_TYPES[personality_type]['characteristics'],
        }
    
    def get_domain_interpretation(self, domain: str, score: float) -> str:
        description = self.DOMAIN_CHARACTERISTICS.get(domain, domain)
        
        if score >= 8:
            interpretation = f'Very high {description}'
        elif score >= 6:
            interpretation = f'High {description}'
        elif score >= 4:
            interpretation = f'Moderate {description}'
        elif score >= 2:
            interpretation = f'Low {description}'
        else:
            interpretation = f'Very low {description}'
        
        return interpretation

