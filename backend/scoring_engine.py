# ============================================================================
# SCRIPT 4: scoring_engine.py - OCEAN Scoring and the Self-Flattery Correction
# ============================================================================
# Two layers live here and are deliberately kept apart:
#
#   1. Standard IPIP-50 scoring. Reverse-key, average per trait, report on a
#      0-100 scale position. Nothing opinionated happens here.
#   2. This project's correction. Estimate lambda from the five cross-checks
#      and the internal consistency of the answers, then shift each trait by a
#      per-trait bias. This is the project's thesis, not settled psychometrics,
#      so both the raw and the corrected scores are always returned.
#
# The model input vector is the 50 RAW item responses in ITEM_ORDER. It is not
# corrected, because the trained weights only ever saw raw responses and
# feeding them something else would break train/serve parity.
# ============================================================================

import logging
from typing import Dict, List, Optional

import numpy as np

from ocean_items import (
    ITEM_ORDER,
    SCALE_MAX,
    SCALE_MIN,
    TRAIT_ITEM_IDS,
    TRAIT_ORDER,
    VALIDITY_ORDER,
    keyed_value,
)

logger = logging.getLogger(__name__)


class ScoringEngine:
    """Turns 55 raw answers into trait scores, a lambda, and a model input."""

    # How strongly each trait pulls a respondent toward a flattering answer,
    # and in which direction. Agreeableness and conscientiousness are the most
    # desirability-loaded of the five; neuroticism is the one people play down
    # rather than up, so its correction runs the other way.
    DESIRABILITY_WEIGHT = {'O': 0.55, 'C': 0.85, 'E': 0.45, 'A': 0.90, 'N': 0.70}
    DESIRABILITY_DIRECTION = {'O': 1.0, 'C': 1.0, 'E': 1.0, 'A': 1.0, 'N': -1.0}

    # Largest shift the correction may apply to a trait, in 0-100 points.
    MAX_CORRECTION = 18.0

    # A profile flatter than this across the five traits is suspiciously even.
    MIN_TRAIT_SPREAD = 6.0

    LAMBDA_BANDS = ((0.35, 'light'), (0.65, 'moderate'))

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    # ------------------------------------------------------------------
    # Standard scoring
    # ------------------------------------------------------------------

    def trait_scores(self, responses: Dict[str, int]) -> Dict[str, float]:
        """Mean each trait's ten keyed items and report a 0-100 scale position."""
        scores = {}
        span = SCALE_MAX - SCALE_MIN
        for trait in TRAIT_ORDER:
            keyed = [keyed_value(item_id, responses[item_id])
                     for item_id in TRAIT_ITEM_IDS[trait]]
            mean = float(np.mean(keyed))
            scores[trait] = round((mean - SCALE_MIN) / span * 100.0, 2)
        self.logger.info(f'[SCORING] Trait scores: {scores}')
        return scores

    def model_input(self, responses: Dict[str, int]) -> List[float]:
        """The 50 raw responses in the exact order the weights were trained on."""
        return [float(responses[item_id]) for item_id in ITEM_ORDER]

    # ------------------------------------------------------------------
    # The correction
    # ------------------------------------------------------------------

    def calculate_lambda(self, responses: Dict[str, int],
                         scores: Dict[str, float]) -> Dict:
        """Estimate how much this set of answers was shaded, from 0 to 1."""
        claim, candour = self._claim_and_candour(responses)

        # A respondent claiming every virtue while conceding no opacity at all
        # is the pattern the cross-checks exist to catch.
        claim_gap = float(np.clip(claim - candour, 0.0, 1.0))

        contradictions = self._detect_contradictions(responses, scores)
        contradiction_load = min(len(contradictions) / 4.0, 1.0)

        style = self._response_style(responses)

        raw_lambda = (0.50 * claim_gap
                      + 0.30 * contradiction_load
                      + 0.20 * style['penalty'])
        value = float(np.clip(raw_lambda, 0.0, 1.0))

        analysis = {
            'lambda': round(value, 4),
            'band': self._band(value),
            'claim_score': round(claim, 4),
            'candour_score': round(candour, 4),
            'claim_gap': round(claim_gap, 4),
            'contradictions': contradictions,
            'contradiction_count': len(contradictions),
            'response_style': style,
        }
        self.logger.info(f"[SCORING] Lambda {value:.4f} ({analysis['band']}), "
                         f'{len(contradictions)} contradictions')
        return analysis

    def _claim_and_candour(self, responses: Dict[str, int]) -> tuple:
        """V1-V3 are claims about oneself; V4-V5 are concessions."""
        span = SCALE_MAX - SCALE_MIN
        claims = [responses[i] for i in ('V1', 'V2', 'V3')]
        concessions = [responses[i] for i in ('V4', 'V5')]
        claim = (float(np.mean(claims)) - SCALE_MIN) / span
        candour = (float(np.mean(concessions)) - SCALE_MIN) / span
        return claim, candour

    def _detect_contradictions(self, responses: Dict[str, int],
                               scores: Dict[str, float]) -> List[Dict]:
        """Pairs that are each defensible alone but rarely true together."""
        found = []

        def add(kind, trait, item, severity):
            found.append({
                'type': kind,
                'trait': trait,
                'trait_score': scores.get(trait),
                'item': item,
                'item_response': responses[item],
                'severity': severity,
            })

        # Warm toward everyone, yet cannot recall a single selfish act.
        if scores['A'] >= 70.0 and responses['V5'] <= 2:
            add('agreeableness_without_selfishness', 'A', 'V5', 'high')

        # Exacting and dutiful, yet finds admitting a mistake hard.
        if scores['C'] >= 70.0 and responses['V1'] <= 2:
            add('conscientiousness_without_admission', 'C', 'V1', 'high')

        # Reports unusual calm and complete insight into their own motives.
        if scores['N'] <= 30.0 and responses['V4'] <= 2:
            add('stability_without_opacity', 'N', 'V4', 'medium')

        # Open and reflective, yet identical in every social context.
        if scores['O'] >= 70.0 and responses['V3'] >= 5:
            add('openness_without_context_shift', 'O', 'V3', 'medium')

        return found

    def _response_style(self, responses: Dict[str, int]) -> Dict:
        """Flag straight-lining and all-or-nothing answering."""
        values = np.array([responses[i] for i in ITEM_ORDER], dtype=float)
        std = float(np.std(values))
        extreme = float(np.mean((values == SCALE_MIN) | (values == SCALE_MAX)))
        midpoint = float(np.mean(values == (SCALE_MIN + SCALE_MAX) / 2))

        penalty = 0.0
        if std < 0.60:            # barely moved the dial across 50 items
            penalty += 0.50
        if extreme > 0.70:        # almost everything at one end or the other
            penalty += 0.30
        if midpoint > 0.60:       # parked on neutral
            penalty += 0.20

        return {
            'std_deviation': round(std, 4),
            'extreme_fraction': round(extreme, 4),
            'midpoint_fraction': round(midpoint, 4),
            'penalty': round(float(np.clip(penalty, 0.0, 1.0)), 4),
        }

    def corrected_scores(self, scores: Dict[str, float],
                         lambda_value: float) -> tuple:
        """Shift each trait against the direction people shade it."""
        values = np.array([scores[t] for t in TRAIT_ORDER], dtype=float)
        mean = float(np.mean(values))
        spread = max(float(np.std(values)), self.MIN_TRAIT_SPREAD)

        corrected, biases = {}, {}
        for trait in TRAIT_ORDER:
            # How far this trait stands out from the rest of the profile.
            z = abs(scores[trait] - mean) / spread
            magnitude = (lambda_value
                         * min(z, 2.0)
                         * self.DESIRABILITY_WEIGHT[trait]
                         * self.MAX_CORRECTION / 2.0)
            signed = self.DESIRABILITY_DIRECTION[trait] * magnitude
            biases[trait] = round(float(signed), 2)
            corrected[trait] = round(float(np.clip(scores[trait] - signed, 0.0, 100.0)), 2)

        self.logger.info(f'[SCORING] Corrected scores: {corrected}')
        return corrected, biases

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------

    def process_assessment(self, responses: Dict[str, int],
                           age: Optional[int] = None) -> Dict:
        """Run the whole scoring layer over one validated response set."""
        raw = self.trait_scores(responses)
        lambda_analysis = self.calculate_lambda(responses, raw)
        corrected, biases = self.corrected_scores(raw, lambda_analysis['lambda'])

        return {
            'raw_trait_scores': raw,
            'corrected_trait_scores': corrected,
            'trait_biases': biases,
            'lambda': lambda_analysis['lambda'],
            'lambda_band': lambda_analysis['band'],
            'lambda_analysis': lambda_analysis,
            'validity_responses': {i: responses[i] for i in VALIDITY_ORDER},
            'model_input': self.model_input(responses),
            'age': age,
        }

    def _band(self, value: float) -> str:
        for threshold, name in self.LAMBDA_BANDS:
            if value < threshold:
                return name
        return 'substantial'


scoring_engine = ScoringEngine()
