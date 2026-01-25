# ============================================================================
# EFOPA Configuration Module
# ============================================================================
# Configuration constants and initialization settings for EFOPA enhancement
# ============================================================================

import os
from typing import Dict

# ============================================================================
# QUESTIONNAIRE CONFIGURATION
# ============================================================================

EFOPA_QUESTIONNAIRE_CONFIG = {
    'version': '1.0',
    'name': 'EFOPA Compact Questionnaire',
    'total_items': 35,
    'core_items': 30,
    'validity_items': 5,
    'scale_min': 0,
    'scale_max': 10,
    'scale_labels': {
        0: 'Strongly Disagree',
        5: 'Neutral',
        10: 'Strongly Agree'
    }
}

# ============================================================================
# DOMAIN CONFIGURATION
# ============================================================================

EFOPA_DOMAIN_CONFIG = {
    'R': {
        'name': 'Relationships',
        'category': 'Romantic/Sexual',
        'construct': 'Mating strategy, commitment authenticity, temptation',
        'items': ['R1', 'R2', 'R3', 'R4', 'R5'],
        'weight': 0.88,  # Highest deception pressure
        'fitness_domain': True,
    },
    'S': {
        'name': 'Status',
        'category': 'Confidence',
        'construct': 'Self-assessment, status signaling, financial disclosure',
        'items': ['S6', 'S7', 'S8', 'S9', 'S10'],
        'weight': 0.82,
        'fitness_domain': True,
    },
    'C': {
        'name': 'Conscientiousness',
        'category': 'Reliability',
        'construct': 'Follow-through, internal motivation, parenting dedication',
        'items': ['C11', 'C12', 'C13', 'C14', 'C15'],
        'weight': 0.68,
        'fitness_domain': False,
    },
    'A': {
        'name': 'Agreeableness',
        'category': 'Helping',
        'construct': 'Public vs. private altruism, moral consistency, coalition loyalty',
        'items': ['A16', 'A17', 'A18', 'A19', 'A20'],
        'weight': 0.62,
        'fitness_domain': False,
    },
    'O': {
        'name': 'Openness',
        'category': 'Knowledge',
        'construct': 'Expertise admission, intellectual humility, creativity attribution',
        'items': ['O21', 'O22', 'O23', 'O24', 'O25'],
        'weight': 0.58,
        'fitness_domain': False,
    },
    'E': {
        'name': 'Emotional Stability',
        'category': 'Emotions',
        'construct': 'Composure, self-regulation, vulnerability concealment, resilience',
        'items': ['E26', 'E27', 'E28', 'E29', 'E30'],
        'weight': 0.75,
        'fitness_domain': True,
    },
}

# ============================================================================
# VALIDITY ITEMS CONFIGURATION
# ============================================================================

EFOPA_VALIDITY_ITEMS = {
    'V31': {
        'text': 'Admits mistakes easily',
        'check_type': 'consistency',
        'paired_with': 'A',
        'threshold': 3.0,
    },
    'V32': {
        'text': 'Genuinely humble',
        'check_type': 'authenticity',
        'paired_with': 'O',
        'threshold': 3.0,
    },
    'V33': {
        'text': 'Consistent across contexts',
        'check_type': 'stability',
        'paired_with': 'C',
        'threshold': 3.0,
    },
    'V34': {
        'text': 'Understands own motivations',
        'check_type': 'self_awareness',
        'paired_with': 'E',
        'threshold': 7.0,  # Inverted threshold (high score is problematic)
    },
    'V35': {
        'text': 'Remembers acting selfishly',
        'check_type': 'value_behavior_gap',
        'paired_with': 'A',
        'threshold': 7.0,  # Inverted threshold
    },
}

# ============================================================================
# LAMBDA CALCULATION CONFIGURATION
# ============================================================================

EFOPA_LAMBDA_CONFIG = {
    'contradiction_weight': 0.10,
    'extreme_consistency_weight': 0.05,
    'response_variability_weight': 0.03,
    'max_lambda': 1.0,
    'deception_thresholds': {
        'low': (0.0, 0.35),
        'moderate': (0.35, 0.65),
        'high': (0.65, 1.0),
    }
}

# ============================================================================
# DOMAIN COST CONFIGURATION
# ============================================================================

EFOPA_DOMAIN_COST_CONFIG = {
    'R': {
        'honesty_cost': 0.35,  # Cost of being honest about mating/temptation
        'fitness_impact': 'reproductive',
        'magnitude': 'high',
    },
    'S': {
        'honesty_cost': 0.32,
        'fitness_impact': 'status_and_resources',
        'magnitude': 'high',
    },
    'C': {
        'honesty_cost': 0.22,
        'fitness_impact': 'partnership_value',
        'magnitude': 'moderate',
    },
    'A': {
        'honesty_cost': 0.18,
        'fitness_impact': 'coalition_access',
        'magnitude': 'moderate',
    },
    'O': {
        'honesty_cost': 0.15,
        'fitness_impact': 'mate_selection',
        'magnitude': 'moderate_low',
    },
    'E': {
        'honesty_cost': 0.28,
        'fitness_impact': 'status_and_partnership',
        'magnitude': 'high',
    },
}

# ============================================================================
# ELEPHANT MODULE CONFIGURATION
# ============================================================================

EFOPA_ELEPHANT_CONFIG = {
    'implicit_bias_factors': {
        'R': 0.92,  # Strongest implicit bias in relationships
        'S': 0.88,  # Strong implicit bias in status
        'C': 0.75,  # Moderate implicit bias
        'A': 0.70,  # Moderate implicit bias
        'O': 0.65,  # Moderate-low implicit bias
        'E': 0.82,  # Strong implicit bias in emotional stability
    },
    'credibility_weight_scaling': 1.0,
    'min_credibility': 0.1,
    'max_credibility': 1.0,
}

# ============================================================================
# VALIDITY METRICS CONFIGURATION
# ============================================================================

EFOPA_VALIDITY_CONFIG = {
    'quality_thresholds': {
        'high': (0.75, 1.0),
        'moderate': (0.55, 0.75),
        'low': (0.35, 0.55),
        'very_low': (0.0, 0.35),
    },
    'validity_score_weights': {
        'V31': 0.20,  # Admits mistakes
        'V32': 0.20,  # Genuinely humble
        'V33': 0.20,  # Consistent
        'V34': 0.20,  # Self-aware
        'V35': 0.20,  # Remembers selfishness
    }
}

# ============================================================================
# AUTHENTICITY METRICS CONFIGURATION
# ============================================================================

EFOPA_AUTHENTICITY_CONFIG = {
    'authenticity_thresholds': {
        'high': (0.70, 1.0),
        'moderate': (0.45, 0.70),
        'low': (0.0, 0.45),
    },
    'coherence_weights': {
        'within_domain': 0.40,
        'cross_domain': 0.35,
        'temporal': 0.25,
    }
}

# ============================================================================
# VAE INPUT CONFIGURATION
# ============================================================================

EFOPA_VAE_CONFIG = {
    'dimensions': 9,
    'input_features': ['R', 'S', 'C', 'A', 'O', 'E', 'lambda', 'sigma_contextual', 'demo_effect'],
    'scale_input': '1-5',  # Input to VAE should be 1-5 scale
    'standardization': 'z-score',
    'latent_dimension': 8,
}

# ============================================================================
# ASSESSMENT METADATA CONFIGURATION
# ============================================================================

EFOPA_METADATA_CONFIG = {
    'assessment_status_levels': {
        'reliable': 'High confidence in results',
        'acceptable': 'Moderate confidence in results',
        'flagged': 'Low confidence - manual review recommended',
        'failed': 'Assessment failed quality checks',
    },
    'risk_flag_definitions': {
        'high_deception_susceptibility': 'Lambda score > 0.65',
        'multiple_contradictions': 'Contradiction count >= 3',
        'low_response_validity': 'Quality level in [low, very_low]',
        'low_authenticity_score': 'Authenticity index < 0.5',
    }
}

# ============================================================================
# SCALE CONVERSION CONFIGURATION
# ============================================================================

EFOPA_SCALE_CONVERSION = {
    'user_scale': (0, 10),
    'vae_scale': (1, 5),
    'conversion_formula': 'vae_score = 1 + (user_score / 10) * 4',
}

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

EFOPA_LOGGING_CONFIG = {
    'log_level': os.environ.get('EFOPA_LOG_LEVEL', 'INFO'),
    'include_debug_info': os.environ.get('EFOPA_DEBUG', 'False').lower() == 'true',
}

# ============================================================================
# FEATURE FLAGS
# ============================================================================

EFOPA_FEATURE_FLAGS = {
    'enable_lambda_analysis': True,
    'enable_domain_costs': True,
    'enable_elephant_module': True,
    'enable_validity_metrics': True,
    'enable_authenticity_metrics': True,
    'enable_metadata_generation': True,
    'enable_recommendations': True,
}

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

EFOPA_DB_CONFIG = {
    'create_tables_on_init': True,
    'migrate_on_init': False,
    'auto_backup': True,
}

def get_efopa_config() -> Dict:
    """
    Get complete EFOPA configuration.
    """
    return {
        'questionnaire': EFOPA_QUESTIONNAIRE_CONFIG,
        'domains': EFOPA_DOMAIN_CONFIG,
        'validity_items': EFOPA_VALIDITY_ITEMS,
        'lambda': EFOPA_LAMBDA_CONFIG,
        'domain_costs': EFOPA_DOMAIN_COST_CONFIG,
        'elephant': EFOPA_ELEPHANT_CONFIG,
        'validity': EFOPA_VALIDITY_CONFIG,
        'authenticity': EFOPA_AUTHENTICITY_CONFIG,
        'vae': EFOPA_VAE_CONFIG,
        'metadata': EFOPA_METADATA_CONFIG,
        'scale_conversion': EFOPA_SCALE_CONVERSION,
        'logging': EFOPA_LOGGING_CONFIG,
        'feature_flags': EFOPA_FEATURE_FLAGS,
        'database': EFOPA_DB_CONFIG,
    }

def validate_efopa_configuration() -> bool:
    """
    Validate EFOPA configuration consistency.
    """
    config = get_efopa_config()
    
    # Validate domain configuration
    assert len(config['domains']) == 6, "Must have exactly 6 domains"
    
    # Validate validity items
    assert len(config['validity_items']) == 5, "Must have exactly 5 validity items"
    
    # Validate weights sum
    validity_weights = config['validity'].get('validity_score_weights', {})
    assert abs(sum(validity_weights.values()) - 1.0) < 0.01, "Validity weights must sum to 1.0"
    
    return True
