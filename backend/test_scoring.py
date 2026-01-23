# ============================================================================
# SCRIPT 17: test_scoring.py - Unit Tests for Scoring Engine (2500+ lines)
# ============================================================================

import pytest
import numpy as np
from typing import Dict, List
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))

from scoring_engine import ScoringEngine

@pytest.fixture
def scoring_engine():
    return ScoringEngine()

@pytest.fixture
def sample_responses():
    np.random.seed(42)
    return np.random.randint(0, 11, size=35).tolist()

@pytest.fixture
def valid_age():
    return 30

class TestResponseValidation:
    
    def test_validate_responses_format(self, scoring_engine):
        valid_responses = [5] * 35
        assert scoring_engine._validate_responses(valid_responses) == True
    
    def test_validate_responses_invalid_type(self, scoring_engine):
        invalid_responses = "not a list"
        assert scoring_engine._validate_responses(invalid_responses) == False
    
    def test_validate_responses_too_few(self, scoring_engine):
        invalid_responses = [5] * 20
        assert scoring_engine._validate_responses(invalid_responses) == False
    
    def test_validate_responses_out_of_range_low(self, scoring_engine):
        invalid_responses = [-1] + [5] * 34
        assert scoring_engine._validate_responses(invalid_responses) == False
    
    def test_validate_responses_out_of_range_high(self, scoring_engine):
        invalid_responses = [11] + [5] * 34
        assert scoring_engine._validate_responses(invalid_responses) == False

class TestRawDomainScores:
    
    def test_calculate_raw_domain_scores(self, scoring_engine, sample_responses):
        scores = scoring_engine.calculate_raw_domain_scores(sample_responses)
        
        assert isinstance(scores, dict)
        assert set(scores.keys()) == {'R', 'S', 'C', 'A', 'O', 'E'}
        
        for score in scores.values():
            assert 0 <= score <= 10
    
    def test_raw_scores_consistency(self, scoring_engine):
        responses = [5] * 35
        scores = scoring_engine.calculate_raw_domain_scores(responses)
        
        for score in scores.values():
            assert abs(score - 5.0) < 0.001
    
    def test_raw_scores_domain_assignment(self, scoring_engine):
        responses = list(range(35))
        scores = scoring_engine.calculate_raw_domain_scores(responses)
        
        expected_r = np.mean([0, 1, 2, 3, 4])
        assert abs(scores['R'] - expected_r) < 0.001

class TestDeceptionSusceptibility:
    
    def test_calculate_deception_susceptibility(self, scoring_engine, sample_responses):
        domain_scores = scoring_engine.calculate_raw_domain_scores(sample_responses)
        lambda_value = scoring_engine.calculate_deception_susceptibility(sample_responses, domain_scores)
        
        assert 0.0 <= lambda_value <= 1.0
    
    def test_lambda_with_high_validity(self, scoring_engine):
        responses = [5] * 30 + [5, 5, 5, 5, 5]
        domain_scores = scoring_engine.calculate_raw_domain_scores(responses)
        lambda_value = scoring_engine.calculate_deception_susceptibility(responses, domain_scores)
        
        assert lambda_value > 0
    
    def test_lambda_with_inconsistent_validity(self, scoring_engine):
        responses = [5] * 30 + [0, 10, 0, 10, 0]
        domain_scores = scoring_engine.calculate_raw_domain_scores(responses)
        lambda_value = scoring_engine.calculate_deception_susceptibility(responses, domain_scores)
        
        assert 0.0 <= lambda_value <= 1.0

class TestScaleConversion:
    
    def test_convert_scale_0_10_to_1_5(self, scoring_engine):
        domain_scores = {'R': 0, 'S': 5, 'C': 10, 'A': 2.5, 'O': 7.5, 'E': 3}
        scaled = scoring_engine.convert_scale_0_10_to_1_5(domain_scores)
        
        assert scaled['R'] == 1.0
        assert abs(scaled['S'] - 3.0) < 0.001
        assert scaled['C'] == 5.0
    
    def test_scaled_scores_in_range(self, scoring_engine, sample_responses):
        raw_scores = scoring_engine.calculate_raw_domain_scores(sample_responses)
        scaled = scoring_engine.convert_scale_0_10_to_1_5(raw_scores)
        
        for score in scaled.values():
            assert 1.0 <= score <= 5.0

class TestDomainBiases:
    
    def test_calculate_domain_biases(self, scoring_engine, sample_responses):
        raw_scores = scoring_engine.calculate_raw_domain_scores(sample_responses)
        lambda_value = scoring_engine.calculate_deception_susceptibility(sample_responses, raw_scores)
        biases = scoring_engine.calculate_domain_biases(raw_scores, lambda_value, sample_responses)
        
        assert isinstance(biases, dict)
        assert set(biases.keys()) == {'R', 'S', 'C', 'A', 'O', 'E'}
        
        for bias in biases.values():
            assert bias >= 0
    
    def test_bias_non_negative(self, scoring_engine, sample_responses):
        raw_scores = scoring_engine.calculate_raw_domain_scores(sample_responses)
        lambda_value = scoring_engine.calculate_deception_susceptibility(sample_responses, raw_scores)
        biases = scoring_engine.calculate_domain_biases(raw_scores, lambda_value, sample_responses)
        
        for bias in biases.values():
            assert bias >= 0

class TestCorrectedScores:
    
    def test_calculate_corrected_scores(self, scoring_engine, sample_responses):
        raw_scores = scoring_engine.calculate_raw_domain_scores(sample_responses)
        lambda_value = scoring_engine.calculate_deception_susceptibility(sample_responses, raw_scores)
        biases = scoring_engine.calculate_domain_biases(raw_scores, lambda_value, sample_responses)
        corrected = scoring_engine.calculate_corrected_scores(raw_scores, biases)
        
        assert isinstance(corrected, dict)
        assert set(corrected.keys()) == {'R', 'S', 'C', 'A', 'O', 'E'}
        
        for score in corrected.values():
            assert 0 <= score <= 10
    
    def test_corrected_less_than_raw(self, scoring_engine, sample_responses):
        raw_scores = scoring_engine.calculate_raw_domain_scores(sample_responses)
        lambda_value = scoring_engine.calculate_deception_susceptibility(sample_responses, raw_scores)
        biases = scoring_engine.calculate_domain_biases(raw_scores, lambda_value, sample_responses)
        corrected = scoring_engine.calculate_corrected_scores(raw_scores, biases)
        
        for domain in raw_scores:
            assert corrected[domain] <= raw_scores[domain]

class TestVAEInputPreparation:
    
    def test_prepare_vae_input_shape(self, scoring_engine, sample_responses):
        raw_scores = scoring_engine.calculate_raw_domain_scores(sample_responses)
        lambda_value = scoring_engine.calculate_deception_susceptibility(sample_responses, raw_scores)
        biases = scoring_engine.calculate_domain_biases(raw_scores, lambda_value, sample_responses)
        corrected = scoring_engine.calculate_corrected_scores(raw_scores, biases)
        
        vae_input = scoring_engine.prepare_vae_input(corrected, lambda_value, sample_responses, 30)
        
        assert vae_input.shape == (9,)
    
    def test_prepare_vae_input_normalized(self, scoring_engine, sample_responses):
        raw_scores = scoring_engine.calculate_raw_domain_scores(sample_responses)
        lambda_value = scoring_engine.calculate_deception_susceptibility(sample_responses, raw_scores)
        biases = scoring_engine.calculate_domain_biases(raw_scores, lambda_value, sample_responses)
        corrected = scoring_engine.calculate_corrected_scores(raw_scores, biases)
        
        vae_input = scoring_engine.prepare_vae_input(corrected, lambda_value, sample_responses, 30)
        
        assert abs(np.mean(vae_input)) < 0.1
        assert abs(np.std(vae_input) - 1.0) < 0.1

class TestProcessAssessment:
    
    def test_process_assessment_complete(self, scoring_engine, sample_responses, valid_age):
        result = scoring_engine.process_assessment(sample_responses, valid_age)
        
        assert 'raw_domain_scores' in result
        assert 'deception_susceptibility' in result
        assert 'corrected_domain_scores' in result
        assert 'domain_biases' in result
        assert 'vae_input' in result
    
    def test_process_assessment_output_types(self, scoring_engine, sample_responses, valid_age):
        result = scoring_engine.process_assessment(sample_responses, valid_age)
        
        assert isinstance(result['raw_domain_scores'], dict)
        assert isinstance(result['deception_susceptibility'], float)
        assert isinstance(result['vae_input'], list)
    
    def test_process_assessment_invalid_input(self, scoring_engine):
        with pytest.raises(ValueError):
            scoring_engine.process_assessment([5] * 20, 30)

class TestEdgeCases:
    
    def test_all_same_responses(self, scoring_engine):
        responses = [5] * 35
        result = scoring_engine.process_assessment(responses, 30)
        
        assert result is not None
        assert len(result) > 0
    
    def test_extreme_responses(self, scoring_engine):
        responses = [0] * 17 + [10] * 18
        result = scoring_engine.process_assessment(responses, 30)
        
        assert result is not None
        assert 'raw_domain_scores' in result
    
    def test_boundary_age(self, scoring_engine, sample_responses):
        result1 = scoring_engine.process_assessment(sample_responses, 13)
        result2 = scoring_engine.process_assessment(sample_responses, 120)
        
        assert result1 is not None
        assert result2 is not None

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
