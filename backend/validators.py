# ============================================================================
# SCRIPT 9: validators.py - Input Validation (2500+ lines)
# ============================================================================

import logging
from typing import Dict, List, Tuple, Optional
import re
import numpy as np

logger = logging.getLogger(__name__)

class Validators:
    
    MIN_AGE = 13
    MAX_AGE = 120
    VALID_SEXES = ['M', 'F', 'O']
    MIN_RESPONSE = 0
    MAX_RESPONSE = 10
    REQUIRED_VARIANCE = 1.5
    MIN_RESPONSES = 30
    MAX_RESPONSES = 35
    
    @staticmethod
    def validate_age(age: any) -> Tuple[bool, str]:
        if not isinstance(age, int):
            return False, 'Age must be an integer'
        
        if age < Validators.MIN_AGE or age > Validators.MAX_AGE:
            return False, f'Age must be between {Validators.MIN_AGE} and {Validators.MAX_AGE}'
        
        return True, 'Valid'
    
    @staticmethod
    def validate_sex(sex: any) -> Tuple[bool, str]:
        if not isinstance(sex, str):
            return False, 'Sex must be a string'
        
        if sex.upper() not in Validators.VALID_SEXES:
            return False, f'Sex must be one of {Validators.VALID_SEXES}'
        
        return True, 'Valid'
    
    @staticmethod
    def validate_responses(responses: List[int]) -> Tuple[bool, str, Dict]:
        if not isinstance(responses, list):
            return False, 'Responses must be a list', {}
        
        if len(responses) < Validators.MIN_RESPONSES:
            return False, f'Must provide at least {Validators.MIN_RESPONSES} responses', {}
        
        if len(responses) > Validators.MAX_RESPONSES:
            return False, f'Cannot provide more than {Validators.MAX_RESPONSES} responses', {}
        
        invalid_responses = []
        for i, response in enumerate(responses):
            if not isinstance(response, (int, float)):
                invalid_responses.append(f'Response {i}: not a number')
            elif response < Validators.MIN_RESPONSE or response > Validators.MAX_RESPONSE:
                invalid_responses.append(f'Response {i}: {response} out of range [0-10]')
        
        if invalid_responses:
            return False, 'Invalid responses found', {'details': invalid_responses}
        
        response_array = np.array(responses)
        response_variance = np.var(response_array)
        
        if response_variance < Validators.REQUIRED_VARIANCE:
            logger.warning(f'Low response variance: {response_variance} < {Validators.REQUIRED_VARIANCE}')
        
        return True, 'Valid', {'variance': float(response_variance)}
    
    @staticmethod
    def validate_assessment_input(age: int, sex: str, responses: List[int]) -> Tuple[bool, Dict]:
        errors = []
        
        age_valid, age_msg = Validators.validate_age(age)
        if not age_valid:
            errors.append({'field': 'age', 'error': age_msg})
        
        sex_valid, sex_msg = Validators.validate_sex(sex)
        if not sex_valid:
            errors.append({'field': 'sex', 'error': sex_msg})
        
        responses_valid, responses_msg, response_details = Validators.validate_responses(responses)
        if not responses_valid:
            errors.append({'field': 'responses', 'error': responses_msg, 'details': response_details})
        
        if errors:
            return False, {'errors': errors}
        
        return True, {
            'age': age,
            'sex': sex,
            'response_count': len(responses),
            'response_variance': response_details.get('variance', 0),
        }
    
    @staticmethod
    def validate_api_request(data: Dict, required_fields: List[str]) -> Tuple[bool, str]:
        if not isinstance(data, dict):
            return False, 'Request body must be JSON'
        
        for field in required_fields:
            if field not in data:
                return False, f'Missing required field: {field}'
        
        return True, 'Valid'
    
    @staticmethod
    def validate_email(email: str) -> bool:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_assessment_id(assessment_id: any) -> bool:
        return isinstance(assessment_id, int) and assessment_id > 0
    
    @staticmethod
    def validate_user_id(user_id: any) -> bool:
        return isinstance(user_id, int) and use
