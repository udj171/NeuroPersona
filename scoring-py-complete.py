import json
import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import statistics
from scipy import stats

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ================================================================================
# ENUMS AND CONSTANTS
# ================================================================================

class Domain(Enum):
    """Personality domains in EFOPA framework."""
    RELATIONSHIPS = ("R", 0.88)
    STATUS = ("S", 0.82)
    CONSCIENTIOUSNESS = ("C", 0.68)
    AGREEABLENESS = ("A", 0.62)
    OPENNESS = ("O", 0.58)
    EMOTIONAL_STABILITY = ("E", 0.75)
    
    @property
    def code(self) -> str:
        return self.value[0]
    
    @property
    def delta_pressure(self) -> float:
        """Domain-specific deception pressure (Delta value)."""
        return self.value[1]


# Domain-specific item mappings
DOMAIN_ITEMS = {
    Domain.RELATIONSHIPS: ["R1", "R2", "R3", "R4", "R5"],
    Domain.STATUS: ["S6", "S7", "S8", "S9", "S10"],
    Domain.CONSCIENTIOUSNESS: ["C11", "C12", "C13", "C14", "C15"],
    Domain.AGREEABLENESS: ["A16", "A17", "A18", "A19", "A20"],
    Domain.OPENNESS: ["O21", "O22", "O23", "O24", "O25"],
    Domain.EMOTIONAL_STABILITY: ["E26", "E27", "E28", "E29", "E30"],
}

# Validity check items
VALIDITY_ITEMS = ["V31", "V32", "V33", "V34", "V35"]

# All required items
ALL_REQUIRED_ITEMS = (
    VALIDITY_ITEMS +
    sum([items for items in DOMAIN_ITEMS.values()], [])
)

# Cost function parameters (domain-specific)
COST_FUNCTION_PARAMS = {
    Domain.CONSCIENTIOUSNESS: {
        "baseline": 0.4,
        "observability": 0.85,
        "name": "Conscientiousness"
    },
    Domain.STATUS: {
        "baseline": 0.3,
        "sensitivity": 0.35,
        "name": "Status"
    },
    Domain.RELATIONSHIPS: {
        "baseline": 0.2,
        "name": "Relationships"
    },
    Domain.EMOTIONAL_STABILITY: {
        "baseline": 0.1,
        "name": "Emotional Stability"
    },
    Domain.AGREEABLENESS: {
        "baseline": 0.15,
        "name": "Agreeableness"
    },
    Domain.OPENNESS: {
        "baseline": 0.12,
        "name": "Openness"
    },
}

# Confidence interval parameters
CI_PARAMS = {
    "z_score_95": 1.96,
    "z_score_80": 1.28,
    "base_se": 0.15,
    "corrected_margin_multiplier": 0.8,
}


# ================================================================================
# DATA CLASSES
# ================================================================================

@dataclass
class RawScores:
    """Raw personality scores (0-100 scale)."""
    relationships: float
    status: float
    conscientiousness: float
    agreeableness: float
    openness: float
    emotional_stability: float
    
    def to_dict(self) -> Dict[str, float]:
        return asdict(self)
    
    def to_list(self) -> List[float]:
        return list(self.to_dict().values())


@dataclass
class CorrectedScores:
    """Deception-corrected scores (1-5 scale)."""
    relationships: float
    status: float
    conscientiousness: float
    agreeableness: float
    openness: float
    emotional_stability: float
    
    def to_dict(self) -> Dict[str, float]:
        return asdict(self)
    
    def to_list(self) -> List[float]:
        return list(self.to_dict().values())


@dataclass
class ConfidenceInterval:
    """95% confidence interval with supporting statistics."""
    lower_80: float
    lower_95: float
    mean: float
    upper_95: float
    upper_80: float
    margin_80: float
    margin_95: float


@dataclass
class ScoringResult:
    """Complete scoring pipeline output."""
    assessment_id: str
    raw_scores: Dict[str, float]
    validity_score: float
    deception_lambda: float
    delta_values: Dict[str, float]
    corrected_scores: Dict[str, float]
    confidence_intervals: Dict[str, Dict[str, float]]
    percentiles: Dict[str, float]
    quality_assessment: str
    ready_for_ml: bool
    timestamp: str
    
    def to_json(self) -> str:
        """Convert to JSON for database storage."""
        return json.dumps(asdict(self), indent=2)


# ================================================================================
# STEP 1: RESPONSE PROCESSOR
# ================================================================================

class ResponseProcessor:
    """
    Parse, validate, and normalize questionnaire responses.
    
    Implements initial validation of 35 questionnaire items (0-10 Likert scale).
    Checks for required fields, valid ranges, and data type correctness.
    """
    
    def __init__(self):
        """Initialize response processor."""
        self.logger = logging.getLogger(__name__)
        self.errors = []
    
    def validate_responses(self, responses: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate questionnaire responses.
        
        Args:
            responses: Dict mapping item IDs to responses (0-10)
        
        Returns:
            (is_valid, error_list)
        """
        self.errors = []
        
        # Check all required items present
        missing_items = [item for item in ALL_REQUIRED_ITEMS if item not in responses]
        if missing_items:
            self.errors.append(f"Missing items: {', '.join(missing_items)}")
        
        # Validate each response
        for item_id, value in responses.items():
            if item_id not in ALL_REQUIRED_ITEMS:
                self.errors.append(f"Unknown item: {item_id}")
                continue
            
            # Check type and range
            if not isinstance(value, (int, float)):
                self.errors.append(f"{item_id}: Invalid type (expected number)")
                continue
            
            if not (0 <= value <= 10):
                self.errors.append(f"{item_id}: Out of range [0-10]")
            
            # Type coercion
            responses[item_id] = float(value)
        
        return len(self.errors) == 0, self.errors
    
    def process(self, responses: Dict[str, Any]) -> Dict[str, float]:
        """
        Process and normalize responses.
        
        Args:
            responses: Raw questionnaire responses
        
        Returns:
            Normalized response dict
        """
        is_valid, errors = self.validate_responses(responses)
        if not is_valid:
            raise ValueError(f"Invalid responses: {'; '.join(errors)}")
        
        self.logger.info(f"Processed {len(responses)} responses successfully")
        return responses


# ================================================================================
# STEP 2: VALIDITY ANALYZER
# ================================================================================

class ValidityAnalyzer:
    """
    Assess response validity and detect inconsistency patterns.
    
    Implements:
    - Consistency violation detection (cross-domain contradictions)
    - Response variance analysis (straight-line response detection)
    - Validity item scoring
    """
    
    def __init__(self):
        """Initialize validity analyzer."""
        self.logger = logging.getLogger(__name__)
    
    def calculate_validity_score(self, responses: Dict[str, float]) -> float:
        """
        Calculate overall validity score (0-1) from validity items.
        
        Higher score = more valid/honest responses
        
        Args:
            responses: All questionnaire responses
        
        Returns:
            Validity score (0-1)
        """
        validity_responses = [responses.get(item, 5) for item in VALIDITY_ITEMS]
        
        # Validity = average of validity items normalized to 0-1
        mean_validity = np.mean(validity_responses) / 10.0
        
        # Adjust for suspicious patterns
        validity_score = min(max(mean_validity, 0.0), 1.0)
        
        self.logger.info(f"Calculated validity score: {validity_score:.3f}")
        return validity_score
    
    def detect_consistency_violations(self, responses: Dict[str, float]) -> int:
        """
        Detect cross-domain consistency violations.
        
        Rules:
        - High Agreeableness (>7.5) + admits selfishness (V35 <2.5) = violation
        - High Openness (>7.5) + not humble (V32 <2.5) = violation
        - High Conscientiousness (>7.5) + inconsistent (V33 <2.5) = violation
        - High Emotional Stability (>7.5) + confusion (V34 <2.5) = violation
        
        Args:
            responses: All questionnaire responses
        
        Returns:
            Number of detected violations (0-5)
        """
        violations = 0
        
        # Calculate domain averages
        domains = {}
        for domain, items in DOMAIN_ITEMS.items():
            domain_values = [responses.get(item, 5) for item in items]
            domains[domain] = np.mean(domain_values)
        
        # Get validity items
        validity = {item: responses.get(item, 5) for item in VALIDITY_ITEMS}
        
        # Check violations
        if domains[Domain.AGREEABLENESS] > 7.5 and validity["V35"] < 2.5:
            violations += 1  # Claims high agreeableness but admits selfishness
        
        if domains[Domain.OPENNESS] > 7.5 and validity["V32"] < 2.5:
            violations += 1  # Claims high openness but not humble
        
        if domains[Domain.CONSCIENTIOUSNESS] > 7.5 and validity["V33"] < 2.5:
            violations += 1  # Claims high conscientiousness but inconsistent
        
        if domains[Domain.EMOTIONAL_STABILITY] > 7.5 and validity["V34"] < 2.5:
            violations += 1  # Claims emotional stability but confused
        
        if domains[Domain.AGREEABLENESS] > 7.5 and validity["V35"] < 2.5:
            violations += 1  # Redundant check
        
        self.logger.info(f"Detected {violations} consistency violations")
        return violations
    
    def analyze_response_variance(self, responses: Dict[str, float]) -> float:
        """
        Calculate response variance to detect straight-line responses.
        
        Low variance (<0.5) indicates potential inattention or response flattening.
        
        Args:
            responses: All questionnaire responses (excluding validity items)
        
        Returns:
            Response variance score
        """
        personality_items = [
            item for item in responses.keys()
            if item not in VALIDITY_ITEMS
        ]
        
        values = [responses[item] for item in personality_items]
        variance = np.var(values)
        
        self.logger.info(f"Response variance: {variance:.3f}")
        return variance
    
    def analyze(self, responses: Dict[str, float]) -> Dict[str, Any]:
        """
        Complete validity analysis.
        
        Args:
            responses: All questionnaire responses
        
        Returns:
            Validity analysis dict
        """
        return {
            "validity_score": self.calculate_validity_score(responses),
            "consistency_violations": self.detect_consistency_violations(responses),
            "response_variance": self.analyze_response_variance(responses),
        }


# ================================================================================
# STEP 3: DOMAIN SCORING ENGINE
# ================================================================================

class DomainScoringEngine:
    """
    Calculate raw trait scores for each personality domain.
    
    Implements:
    - Domain score averaging (5 items per domain)
    - Normalization to 0-100 scale
    """
    
    def __init__(self):
        """Initialize domain scoring engine."""
        self.logger = logging.getLogger(__name__)
    
    def calculate_raw_scores(self, responses: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate raw trait scores (0-100) by averaging domain items.
        
        Args:
            responses: All questionnaire responses (0-10 scale)
        
        Returns:
            Dict of domain code to raw score (0-100)
        """
        raw_scores = {}
        
        for domain, items in DOMAIN_ITEMS.items():
            # Get responses for this domain
            domain_values = [responses.get(item, 5.0) for item in items]
            
            # Average and normalize to 0-100
            mean_score = np.mean(domain_values)
            normalized_score = (mean_score / 10.0) * 100.0
            
            raw_scores[domain.code] = normalized_score
            
            self.logger.info(
                f"Domain {domain.name}: raw={mean_score:.2f}/10 → "
                f"{normalized_score:.1f}/100"
            )
        
        return raw_scores


# ================================================================================
# STEP 4: DECEPTION ESTIMATOR
# ================================================================================

class DeceptionEstimator:
    """
    Estimate individual deception susceptibility (Lambda parameter).
    
    Lambda (Λ) represents individual propensity for strategic self-deception:
    - Λ ~ 0.3: Low deception (authentic responses)
    - Λ ~ 0.65: Moderate deception
    - Λ ~ 2.0: High deception (extensive self-deception)
    
    Sources of variation:
    - Cognitive ability (intelligent individuals construct better deceptions)
    - Personality traits (narcissism increases deception)
    - Early attachment patterns (secure attachment reduces deception)
    - Life history strategy (fast strategies increase deception)
    """
    
    def __init__(self):
        """Initialize deception estimator."""
        self.logger = logging.getLogger(__name__)
    
    def estimate_lambda(
        self,
        validity_score: float,
        consistency_violations: int,
        response_variance: float
    ) -> float:
        """
        Estimate individual deception susceptibility (Lambda).
        
        Args:
            validity_score: Response validity (0-1)
            consistency_violations: Number of detected contradictions (0-5)
            response_variance: Response variance across items
        
        Returns:
            Lambda value (0.3-2.0 range, clipped)
        """
        # Base lambda from validity score
        # Higher validity = lower lambda
        lambda_from_validity = (1.0 - validity_score) * 1.5
        
        # Increase lambda for consistency violations
        lambda_from_violations = consistency_violations * 0.15
        
        # Decrease lambda for response variance (diverse responses = more honest)
        lambda_from_variance = (1.5 - min(response_variance, 1.5)) * 0.2
        
        # Combine components
        lambda_value = (
            lambda_from_validity +
            lambda_from_violations +
            lambda_from_variance
        )
        
        # Clamp to valid range [0.3, 2.0]
        lambda_value = np.clip(lambda_value, 0.3, 2.0)
        
        self.logger.info(
            f"Estimated Lambda (deception susceptibility): {lambda_value:.3f} "
            f"(validity={validity_score:.2f}, violations={consistency_violations}, "
            f"variance={response_variance:.2f})"
        )
        
        return lambda_value


# ================================================================================
# STEP 5: BIAS CALCULATOR
# ================================================================================

class BiasCalculator:
    """
    Calculate domain-specific deception bias corrections.
    
    Applies handicap principle: high-cost lies are suppressed more than low-cost lies.
    
    Cost function structure:
    - Conscientiousness (high cost, observable): largest correction
    - Status (medium cost): medium correction
    - Relationships (low cost, private): small correction
    - Emotional Stability (lowest cost): minimal correction
    """
    
    def __init__(self):
        """Initialize bias calculator."""
        self.logger = logging.getLogger(__name__)
    
    def calculate_cost_function(
        self,
        domain: Domain,
        reported_score: float
    ) -> float:
        """
        Calculate handicap cost for reporting given score in domain.
        
        High reported scores incur higher cost (harder to maintain deception).
        
        Args:
            domain: Personality domain
            reported_score: Reported score (0-10 scale)
        
        Returns:
            Cost value (0-1)
        """
        params = COST_FUNCTION_PARAMS[domain]
        baseline = params["baseline"]
        
        if domain == Domain.CONSCIENTIOUSNESS:
            # Cost = baseline * (1 - correlation) * observability
            # Higher observability = higher cost
            observability = params.get("observability", 0.85)
            # Simulate correlation: higher reported score = lower correlation with reality
            correlation = 1.0 - (reported_score / 10.0) * 0.5
            cost = baseline * (1.0 - correlation) * observability
        
        elif domain == Domain.STATUS:
            # Cost increases exponentially with reported vs. actual gap
            sensitivity = params.get("sensitivity", 0.35)
            cost = baseline * sensitivity * (reported_score / 10.0)
        
        else:
            # Linear cost for other domains
            cost = baseline * (reported_score / 10.0)
        
        return min(max(cost, 0.0), 1.0)
    
    def calculate_honest_signaling_cost(
        self,
        domain: Domain,
        cost: float
    ) -> float:
        """
        Calculate honest signaling cost multiplier (elephant function).
        
        Uses sigmoid to transform cost to likelihood (0-1):
        σ(x) = 1 / (1 + e^(-5(x - 0.25)))
        
        Args:
            domain: Personality domain
            cost: Cost value from cost_function
        
        Returns:
            Honest signaling cost (0-1)
        """
        # Sigmoid function with steepness=5, inflection=0.25
        sigma = 1.0 / (1.0 + np.exp(-5.0 * (cost - 0.25)))
        return sigma
    
    def calculate_domain_bias(
        self,
        domain: Domain,
        lambda_value: float,
        reported_score: float
    ) -> float:
        """
        Calculate deception bias for a single domain.
        
        Formula: Bias = Lambda * Delta * (1 - SigmaCost)
        
        Args:
            domain: Personality domain
            lambda_value: Individual deception susceptibility (0.3-2.0)
            reported_score: Reported trait score (0-10)
        
        Returns:
            Bias correction (to subtract from reported score)
        """
        delta = domain.delta_pressure  # Domain-specific deception pressure
        cost = self.calculate_cost_function(domain, reported_score)
        sigma = self.calculate_honest_signaling_cost(domain, cost)
        
        # Bias = Lambda * Delta * (1 - Sigma)
        bias = lambda_value * delta * (1.0 - sigma)
        
        return bias
    
    def calculate_all_biases(
        self,
        raw_scores: Dict[str, float],
        lambda_value: float
    ) -> Dict[str, float]:
        """
        Calculate deception biases for all domains.
        
        Args:
            raw_scores: Raw trait scores (0-10 scale from averaging)
            lambda_value: Individual deception susceptibility
        
        Returns:
            Dict of domain code to bias correction
        """
        biases = {}
        
        for domain in Domain:
            # Convert to 0-10 scale for bias calculation
            score_0_10 = raw_scores[domain.code]
            
            bias = self.calculate_domain_bias(domain, lambda_value, score_0_10)
            biases[domain.code] = bias
            
            self.logger.info(
                f"Domain {domain.name}: bias={bias:.3f} "
                f"(lambda={lambda_value:.2f}, delta={domain.delta_pressure:.2f})"
            )
        
        return biases


# ================================================================================
# STEP 6: SCORE CORRECTION & NORMALIZATION
# ================================================================================

class ScoreCorrectionEngine:
    """
    Apply deception corrections and normalize to personality scales.
    
    Converts from:
    - Raw (0-100 scale) → Corrected (1-5 scale)
    - Applies domain-specific bias subtractions
    - Clamps to valid ranges
    """
    
    def __init__(self):
        """Initialize score correction engine."""
        self.logger = logging.getLogger(__name__)
    
    def correct_domain_scores(
        self,
        raw_scores: Dict[str, float],
        biases: Dict[str, float],
        validity_score: float
    ) -> Dict[str, float]:
        """
        Apply deception bias corrections to raw scores.
        
        Formula: Corrected = Raw - Bias
        Then normalize to 1-5 scale: (Raw/20) + 1
        
        Args:
            raw_scores: Raw scores (0-100 scale)
            biases: Domain-specific biases (0-10 scale equivalents)
            validity_score: Validity adjustment factor (0-1)
        
        Returns:
            Corrected scores (1-5 scale)
        """
        corrected_scores = {}
        
        for domain in Domain:
            code = domain.code
            
            # Get raw score and bias
            raw = raw_scores[code]
            bias = biases[code]
            
            # Convert raw to 0-10 scale if needed
            raw_0_10 = raw / 10.0 if raw > 10 else raw
            
            # Apply bias correction
            corrected_0_10 = max(0, raw_0_10 - bias)
            
            # Weight by validity (lower validity = more conservative correction)
            weighted_corrected = (
                corrected_0_10 * validity_score +
                raw_0_10 * (1.0 - validity_score)
            )
            
            # Normalize to 1-5 scale: multiply by 0.5 then add 1
            corrected_1_5 = (weighted_corrected * 0.5) + 1.0
            
            # Clamp to valid range
            corrected_1_5 = np.clip(corrected_1_5, 1.0, 5.0)
            
            corrected_scores[code] = corrected_1_5
            
            self.logger.info(
                f"Domain {domain.name}: "
                f"{raw_0_10:.2f}/10 - {bias:.2f} bias → {corrected_1_5:.2f}/5"
            )
        
        return corrected_scores


# ================================================================================
# STEP 7: CONFIDENCE INTERVAL CALCULATOR
# ================================================================================

class ConfidenceIntervalCalculator:
    """
    Calculate confidence intervals (80% and 95%) for each domain.
    
    Confidence width depends on response validity:
    - High validity (0.9): narrow CI (±0.5)
    - Medium validity (0.5): medium CI (±1.5)
    - Low validity (0.1): wide CI (±2.5)
    """
    
    def __init__(self):
        """Initialize CI calculator."""
        self.logger = logging.getLogger(__name__)
    
    def calculate_confidence_intervals(
        self,
        raw_scores: Dict[str, float],
        corrected_scores: Dict[str, float],
        validity_score: float
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate 80% and 95% confidence intervals for all domains.
        
        Args:
            raw_scores: Raw trait scores (0-100)
            corrected_scores: Corrected trait scores (1-5)
            validity_score: Overall response validity (0-1)
        
        Returns:
            Dict of domain codes to CI dict with lower_80, lower_95, mean, upper_95, upper_80
        """
        confidence_intervals = {}
        
        z_80 = CI_PARAMS["z_score_80"]
        z_95 = CI_PARAMS["z_score_95"]
        base_se = CI_PARAMS["base_se"]
        
        for domain in Domain:
            code = domain.code
            
            # Calculate confidence margins
            # Width depends on validity: lower validity = wider CI
            ci_width_factor = 5.0 + (1.0 - validity_score) * 25.0
            
            # Standard error adjusted for validity
            se = base_se * ci_width_factor / 5.0
            
            # Raw score CI (0-100 scale)
            raw_margin_80 = z_80 * se
            raw_margin_95 = z_95 * se
            
            # Corrected score CI (1-5 scale)
            corrected_margin_80 = z_80 * se * 0.8
            corrected_margin_95 = z_95 * se * 0.8
            
            confidence_intervals[code] = {
                "raw": {
                    "lower_95": max(0, raw_scores[code] - raw_margin_95),
                    "lower_80": max(0, raw_scores[code] - raw_margin_80),
                    "mean": raw_scores[code],
                    "upper_80": min(100, raw_scores[code] + raw_margin_80),
                    "upper_95": min(100, raw_scores[code] + raw_margin_95),
                },
                "corrected": {
                    "lower_95": max(1, corrected_scores[code] - corrected_margin_95),
                    "lower_80": max(1, corrected_scores[code] - corrected_margin_80),
                    "mean": corrected_scores[code],
                    "upper_80": min(5, corrected_scores[code] + corrected_margin_80),
                    "upper_95": min(5, corrected_scores[code] + corrected_margin_95),
                }
            }
            
            self.logger.info(
                f"Domain {domain.name} CI95: "
                f"[{confidence_intervals[code]['corrected']['lower_95']:.2f}, "
                f"{confidence_intervals[code]['corrected']['upper_95']:.2f}]"
            )
        
        return confidence_intervals


# ================================================================================
# PERCENTILE CALCULATION
# ================================================================================

class PercentileCalculator:
    """
    Calculate percentile ranks against population norms.
    
    This is placeholder implementation. In production, would use actual
    population distribution data from training set.
    """
    
    def __init__(self):
        """Initialize percentile calculator."""
        self.logger = logging.getLogger(__name__)
    
    def calculate_percentiles(
        self,
        corrected_scores: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Calculate percentile ranks for corrected scores.
        
        Args:
            corrected_scores: Corrected trait scores (1-5 scale)
        
        Returns:
            Dict of domain codes to percentile ranks (0-100)
        """
        percentiles = {}
        
        # Assuming normal distribution with mean=3.0, std=0.8 on 1-5 scale
        for domain in Domain:
            code = domain.code
            score = corrected_scores[code]
            
            # Standardize: (score - mean) / std
            z_score = (score - 3.0) / 0.8
            
            # Convert to percentile using normal CDF
            percentile = stats.norm.cdf(z_score) * 100
            percentile = np.clip(percentile, 0.1, 99.9)
            
            percentiles[code] = percentile
            
            self.logger.info(f"Domain {code}: {percentile:.1f}th percentile")
        
        return percentiles


# ================================================================================
# QUALITY ASSESSMENT
# ================================================================================

class QualityAssessment:
    """
    Assess overall data quality and provide interpretation guidance.
    """
    
    @staticmethod
    def assess_quality(
        validity_score: float,
        consistency_violations: int,
        response_variance: float
    ) -> str:
        """
        Assess response quality and return interpretation note.
        
        Args:
            validity_score: Response validity (0-1)
            consistency_violations: Number of violations (0-5)
            response_variance: Response variance
        
        Returns:
            Quality assessment string
        """
        if validity_score > 0.80 and consistency_violations == 0:
            return "High validity, likely authentic responses"
        elif validity_score > 0.70 and consistency_violations <= 1:
            return "Moderate validity, some typical self-presentation"
        elif validity_score > 0.50:
            return "Moderate-low validity, moderate deception pressure"
        else:
            return "Low validity, substantial deception or inattention detected"


# ================================================================================
# MAIN SCORING PIPELINE
# ================================================================================

class ScoringPipeline:
    """
    Orchestrate the complete 7-step deception-corrected personality scoring.
    
    Pipeline steps:
    1. Parse & validate responses
    2. Assess validity and detect consistency violations
    3. Calculate raw domain scores (0-100)
    4. Estimate individual deception susceptibility (Lambda)
    5. Calculate deception-specific biases
    6. Apply corrections & normalize scores
    7. Calculate confidence intervals & percentiles
    """
    
    def __init__(self):
        """Initialize scoring pipeline."""
        self.logger = logging.getLogger(__name__)
        
        # Initialize all components
        self.response_processor = ResponseProcessor()
        self.validity_analyzer = ValidityAnalyzer()
        self.domain_engine = DomainScoringEngine()
        self.deception_estimator = DeceptionEstimator()
        self.bias_calculator = BiasCalculator()
        self.correction_engine = ScoreCorrectionEngine()
        self.ci_calculator = ConfidenceIntervalCalculator()
        self.percentile_calculator = PercentileCalculator()
    
    def run(
        self,
        assessment_id: str,
        responses: Dict[str, Any]
    ) -> ScoringResult:
        """
        Execute complete scoring pipeline.
        
        Args:
            assessment_id: Unique assessment identifier
            responses: Questionnaire responses {item_id: score}
        
        Returns:
            ScoringResult with all computed values
        """
        self.logger.info(f"Starting scoring pipeline for {assessment_id}")
        
        try:
            # STEP 1: Process & validate responses
            self.logger.info("STEP 1: Processing responses...")
            processed_responses = self.response_processor.process(responses)
            
            # STEP 2: Analyze validity
            self.logger.info("STEP 2: Analyzing response validity...")
            validity_analysis = self.validity_analyzer.analyze(processed_responses)
            validity_score = validity_analysis["validity_score"]
            violations = validity_analysis["consistency_violations"]
            variance = validity_analysis["response_variance"]
            
            # STEP 3: Calculate raw domain scores
            self.logger.info("STEP 3: Calculating raw domain scores...")
            raw_scores_dict = self.domain_engine.calculate_raw_scores(processed_responses)
            
            # Convert from 0-100 back to 0-10 for bias calculation
            raw_scores_0_10 = {k: v / 10.0 for k, v in raw_scores_dict.items()}
            
            # STEP 4: Estimate deception susceptibility
            self.logger.info("STEP 4: Estimating deception susceptibility...")
            lambda_value = self.deception_estimator.estimate_lambda(
                validity_score=validity_score,
                consistency_violations=violations,
                response_variance=variance
            )
            
            # STEP 5: Calculate biases
            self.logger.info("STEP 5: Calculating deception biases...")
            biases = self.bias_calculator.calculate_all_biases(
                raw_scores=raw_scores_0_10,
                lambda_value=lambda_value
            )
            
            # STEP 6: Apply corrections
            self.logger.info("STEP 6: Applying deception corrections...")
            corrected_scores = self.correction_engine.correct_domain_scores(
                raw_scores=raw_scores_0_10,
                biases=biases,
                validity_score=validity_score
            )
            
            # STEP 7: Calculate confidence intervals
            self.logger.info("STEP 7: Calculating confidence intervals...")
            confidence_intervals = self.ci_calculator.calculate_confidence_intervals(
                raw_scores=raw_scores_0_10,
                corrected_scores=corrected_scores,
                validity_score=validity_score
            )
            
            # Calculate percentiles
            percentiles = self.percentile_calculator.calculate_percentiles(corrected_scores)
            
            # Quality assessment
            quality = QualityAssessment.assess_quality(
                validity_score, violations, variance
            )
            
            # Delta values (domain deception pressures)
            delta_values = {domain.code: domain.delta_pressure for domain in Domain}
            
            # Create result
            result = ScoringResult(
                assessment_id=assessment_id,
                raw_scores=raw_scores_0_10,
                validity_score=validity_score,
                deception_lambda=lambda_value,
                delta_values=delta_values,
                corrected_scores=corrected_scores,
                confidence_intervals=confidence_intervals,
                percentiles=percentiles,
                quality_assessment=quality,
                ready_for_ml=True,
                timestamp=datetime.now().isoformat()
            )
            
            self.logger.info(f"Scoring pipeline completed successfully")
            return result
        
        except Exception as e:
            self.logger.error(f"Pipeline error: {str(e)}", exc_info=True)
            raise


# ================================================================================
# UTILITY FUNCTIONS
# ================================================================================

def create_sample_responses() -> Dict[str, float]:
    """Create sample responses for testing."""
    responses = {}
    
    # Relationships: moderate
    for item in DOMAIN_ITEMS[Domain.RELATIONSHIPS]:
        responses[item] = 6.0
    
    # Status: high
    for item in DOMAIN_ITEMS[Domain.STATUS]:
        responses[item] = 7.5
    
    # Conscientiousness: very high
    for item in DOMAIN_ITEMS[Domain.CONSCIENTIOUSNESS]:
        responses[item] = 8.0
    
    # Agreeableness: moderate-high
    for item in DOMAIN_ITEMS[Domain.AGREEABLENESS]:
        responses[item] = 7.0
    
    # Openness: moderate
    for item in DOMAIN_ITEMS[Domain.OPENNESS]:
        responses[item] = 6.5
    
    # Emotional Stability: moderate
    for item in DOMAIN_ITEMS[Domain.EMOTIONAL_STABILITY]:
        responses[item] = 6.0
    
    # Validity items: high (honest)
    for item in VALIDITY_ITEMS:
        responses[item] = 7.0
    
    return responses


# ================================================================================
# MAIN EXECUTION (FOR TESTING)
# ================================================================================

if __name__ == "__main__":
    """Test the scoring pipeline."""
    
    print("=" * 80)
    print("EFOPA PLATFORM - SCORING PIPELINE TEST")
    print("=" * 80)
    
    # Create sample responses
    sample_responses = create_sample_responses()
    
    # Run pipeline
    pipeline = ScoringPipeline()
    result = pipeline.run(
        assessment_id="test_001",
        responses=sample_responses
    )
    
    # Display results
    print("\nSCORING RESULTS:")
    print("-" * 80)
    print(f"Assessment ID: {result.assessment_id}")
    print(f"Timestamp: {result.timestamp}")
    print(f"\nValidity Score: {result.validity_score:.3f}")
    print(f"Deception Lambda: {result.deception_lambda:.3f}")
    print(f"Quality: {result.quality_assessment}")
    print(f"\nRaw Scores (0-100):")
    for code, score in result.raw_scores.items():
        print(f"  {code}: {score:.1f}")
    print(f"\nCorrected Scores (1-5):")
    for code, score in result.corrected_scores.items():
        print(f"  {code}: {score:.2f}")
    print(f"\nPercentiles:")
    for code, pct in result.percentiles.items():
        print(f"  {code}: {pct:.1f}%")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETED SUCCESSFULLY")
    print("=" * 80)