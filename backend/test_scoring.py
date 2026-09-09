# ============================================================================
# test_scoring.py - Unit tests for the OCEAN scoring engine
# ============================================================================

import numpy as np
import pytest

from ocean_items import (ALL_ITEM_IDS, ITEM_ORDER, N_ITEMS, N_SCORED,
                         REVERSED_IDS, SCALE_MAX, SCALE_MIN, TRAIT_ITEM_IDS,
                         TRAIT_ORDER, keyed_value, reverse_score,
                         to_frontend_payload)
from scoring_engine import ScoringEngine


@pytest.fixture
def engine():
    return ScoringEngine()


def answers(value=3, **overrides):
    """A complete response set, uniform by default."""
    responses = {item_id: value for item_id in ALL_ITEM_IDS}
    responses.update(overrides)
    return responses


# ---------------------------------------------------------------- item bank

class TestItemBank:
    def test_counts(self):
        assert N_SCORED == 50
        assert N_ITEMS == 55
        assert len(set(ALL_ITEM_IDS)) == 55

    def test_ten_items_per_trait(self):
        for trait in TRAIT_ORDER:
            assert len(TRAIT_ITEM_IDS[trait]) == 10

    def test_reverse_score_is_symmetric(self):
        assert reverse_score(1) == 5
        assert reverse_score(5) == 1
        assert reverse_score(3) == 3

    def test_keyed_value_flips_only_reversed_items(self):
        forward = next(i for i in ITEM_ORDER if i not in REVERSED_IDS)
        backward = next(iter(REVERSED_IDS))
        assert keyed_value(forward, 5) == 5
        assert keyed_value(backward, 5) == 1

    def test_frontend_payload_matches_bank(self):
        payload = to_frontend_payload()
        assert payload['counts']['total'] == N_ITEMS
        assert len(payload['items']) == N_ITEMS
        assert payload['scale']['min'] == SCALE_MIN
        assert payload['scale']['max'] == SCALE_MAX


# ------------------------------------------------------------ trait scoring

class TestTraitScores:
    def test_midpoint_answers_give_midpoint_scores(self, engine):
        scores = engine.trait_scores(answers(3))
        for trait in TRAIT_ORDER:
            assert scores[trait] == pytest.approx(50.0)

    def test_score_bounds(self, engine):
        for value in (SCALE_MIN, SCALE_MAX):
            scores = engine.trait_scores(answers(value))
            for trait in TRAIT_ORDER:
                assert 0.0 <= scores[trait] <= 100.0

    def test_reverse_keying_cancels_on_uniform_answers(self, engine):
        # Every trait mixes forward and reverse items, so a uniform sheet must
        # land at the midpoint rather than at an extreme.
        assert engine.trait_scores(answers(5))['E'] == pytest.approx(50.0)

    def test_all_forward_items_high_raises_the_trait(self, engine):
        responses = answers(3)
        for item_id in TRAIT_ITEM_IDS['O']:
            responses[item_id] = 1 if item_id in REVERSED_IDS else 5
        assert engine.trait_scores(responses)['O'] == pytest.approx(100.0)


# ------------------------------------------------------------------- lambda

class TestLambda:
    def test_candid_answers_score_low(self, engine):
        # Moderate claims, real concessions, varied answers.
        rng = np.random.default_rng(7)
        responses = {i: int(rng.integers(2, 5)) for i in ITEM_ORDER}
        responses.update({'V1': 3, 'V2': 3, 'V3': 3, 'V4': 4, 'V5': 4})
        analysis = engine.calculate_lambda(responses, engine.trait_scores(responses))
        assert analysis['lambda'] < 0.35
        assert analysis['band'] == 'light'

    def test_flattering_answers_score_high(self, engine):
        # Every virtue claimed, nothing conceded.
        rng = np.random.default_rng(11)
        responses = {i: int(rng.integers(2, 5)) for i in ITEM_ORDER}
        for item_id in TRAIT_ITEM_IDS['A']:
            responses[item_id] = 1 if item_id in REVERSED_IDS else 5
        responses.update({'V1': 5, 'V2': 5, 'V3': 5, 'V4': 1, 'V5': 1})
        analysis = engine.calculate_lambda(responses, engine.trait_scores(responses))
        assert analysis['lambda'] > 0.5
        assert analysis['contradiction_count'] >= 1

    def test_straight_lining_is_penalised(self, engine):
        responses = answers(4)
        analysis = engine.calculate_lambda(responses, engine.trait_scores(responses))
        assert analysis['response_style']['penalty'] > 0

    def test_lambda_stays_in_range(self, engine):
        rng = np.random.default_rng(3)
        for _ in range(25):
            responses = {i: int(rng.integers(SCALE_MIN, SCALE_MAX + 1)) for i in ALL_ITEM_IDS}
            value = engine.calculate_lambda(responses, engine.trait_scores(responses))['lambda']
            assert 0.0 <= value <= 1.0


# --------------------------------------------------------------- correction

class TestCorrection:
    def test_zero_lambda_leaves_scores_alone(self, engine):
        raw = engine.trait_scores(answers(4))
        corrected, biases = engine.corrected_scores(raw, 0.0)
        assert corrected == pytest.approx(raw)
        assert all(b == 0 for b in biases.values())

    def test_neuroticism_moves_the_other_way(self, engine):
        raw = {'O': 80.0, 'C': 80.0, 'E': 50.0, 'A': 80.0, 'N': 20.0}
        _, biases = engine.corrected_scores(raw, 0.8)
        assert biases['A'] > 0     # inflated virtues come down
        assert biases['N'] < 0     # played-down neuroticism goes up

    def test_corrected_scores_stay_in_range(self, engine):
        rng = np.random.default_rng(5)
        for _ in range(25):
            raw = {t: float(rng.uniform(0, 100)) for t in TRAIT_ORDER}
            corrected, _ = engine.corrected_scores(raw, float(rng.uniform(0, 1)))
            assert all(0.0 <= v <= 100.0 for v in corrected.values())


# ----------------------------------------------------------------- pipeline

class TestPipeline:
    def test_output_shape(self, engine):
        out = engine.process_assessment(answers(3), age=30)
        for key in ('raw_trait_scores', 'corrected_trait_scores', 'trait_biases',
                    'lambda', 'lambda_band', 'lambda_analysis',
                    'validity_responses', 'model_input'):
            assert key in out
        assert len(out['model_input']) == N_SCORED
        assert len(out['validity_responses']) == 5

    def test_model_input_follows_item_order(self, engine):
        responses = answers(3, EXT1=5, OPN10=1)
        out = engine.process_assessment(responses, age=30)
        assert out['model_input'][ITEM_ORDER.index('EXT1')] == 5.0
        assert out['model_input'][ITEM_ORDER.index('OPN10')] == 1.0

    def test_model_input_is_raw_not_keyed(self, engine):
        # Parity with training matters more than tidiness: the weights only
        # ever saw raw responses, reverse items included.
        reversed_id = next(i for i in ITEM_ORDER if i in REVERSED_IDS)
        out = engine.process_assessment(answers(3, **{reversed_id: 5}), age=30)
        assert out['model_input'][ITEM_ORDER.index(reversed_id)] == 5.0

    def test_deterministic(self, engine):
        responses = answers(3, EXT1=5, AGR4=2, V4=1)
        assert engine.process_assessment(responses, 30) == engine.process_assessment(responses, 30)

    def test_json_serialisable(self, engine):
        import json
        json.dumps(engine.process_assessment(answers(4, V1=5, V5=1), age=44))
