# ============================================================================
# test_model_contract.py - The trainer/server boundary
# ============================================================================
# training/train_vae_ocean.py writes a .npz; backend/model_inference.py reads
# it and multiplies the matrices by hand. Nothing at runtime would notice if
# the two disagreed about layer order, orientation, or item order: the maths
# would still run and the answers would be quietly wrong.
#
# These tests pin that boundary. They do not need torch, because torch's only
# relevant behaviour is nn.Linear storing weight as (out_features, in_features)
# and computing x @ W.T + b, which is reproduced here in numpy.
# ============================================================================

import importlib.util
import json
import os
import sys

import numpy as np
import pytest

from model_inference import ModelInferenceEngine
from ocean_items import ITEM_ORDER, REVERSED_IDS, SCALE_MAX, SCALE_MIN, TRAIT_ORDER

TRAINING_PATH = os.path.join(os.path.dirname(__file__), '..', 'training', 'train_vae_ocean.py')


def load_trainer():
    spec = importlib.util.spec_from_file_location('train_vae_ocean', TRAINING_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules['train_vae_ocean'] = module
    spec.loader.exec_module(module)
    return module


trainer = load_trainer()


# ------------------------------------------------------- the shared item bank

class TestItemBankAgreement:
    """The trainer embeds a copy of the bank so it runs on Kaggle standalone."""

    def test_item_order_matches(self):
        assert trainer.ITEM_ORDER == ITEM_ORDER

    def test_reverse_keys_match(self):
        assert trainer.REVERSED_IDS == REVERSED_IDS

    def test_trait_order_matches(self):
        assert trainer.TRAIT_ORDER == TRAIT_ORDER

    def test_scale_matches(self):
        assert (trainer.SCALE_MIN, trainer.SCALE_MAX) == (SCALE_MIN, SCALE_MAX)

    def test_trait_scores_agree_with_the_backend(self):
        from scoring_engine import ScoringEngine

        rng = np.random.default_rng(0)
        values = rng.integers(1, 6, size=(8, len(ITEM_ORDER))).astype(np.float32)
        from_trainer = trainer.trait_scores(values)

        engine = ScoringEngine()
        for row_index, row in enumerate(values):
            responses = {item: int(v) for item, v in zip(ITEM_ORDER, row)}
            responses.update({f'V{i}': 3 for i in range(1, 6)})
            backend_scores = engine.trait_scores(responses)
            for trait_index, trait in enumerate(TRAIT_ORDER):
                assert from_trainer[row_index, trait_index] == pytest.approx(
                    backend_scores[trait], abs=1e-3)


# --------------------------------------------------------- weight orientation

def torch_linear(x, weight, bias):
    """What nn.Linear computes: weight is (out, in) and y = x @ W.T + b."""
    return x @ weight.T + bias


def build_fake_export(tmp_path, seed=1):
    """A weight file in exactly the layout the trainer writes."""
    rng = np.random.default_rng(seed)
    n_in, h1, h2, latent, k = len(ITEM_ORDER), 128, 64, 16, 6

    # State dict in torch's (out, in) orientation.
    state = {
        'enc1.weight': rng.normal(0, 0.1, (h1, n_in)),
        'enc1.bias': rng.normal(0, 0.1, h1),
        'enc2.weight': rng.normal(0, 0.1, (h2, h1)),
        'enc2.bias': rng.normal(0, 0.1, h2),
        'mu.weight': rng.normal(0, 0.1, (latent, h2)),
        'mu.bias': rng.normal(0, 0.1, latent),
        'dec1.weight': rng.normal(0, 0.1, (h2, latent)),
        'dec1.bias': rng.normal(0, 0.1, h2),
        'dec2.weight': rng.normal(0, 0.1, (n_in, h2)),
        'dec2.bias': rng.normal(0, 0.1, n_in),
    }

    path = os.path.join(tmp_path, 'ocean_vae.npz')
    np.savez_compressed(
        path,
        item_order=np.array(ITEM_ORDER),
        feature_mean=np.full(n_in, 3.0),
        feature_std=np.full(n_in, 1.2),
        enc_w1=state['enc1.weight'].T, enc_b1=state['enc1.bias'],
        enc_w2=state['enc2.weight'].T, enc_b2=state['enc2.bias'],
        enc_mu_w=state['mu.weight'].T, enc_mu_b=state['mu.bias'],
        dec_w1=state['dec1.weight'].T, dec_b1=state['dec1.bias'],
        dec_w2=state['dec2.weight'].T, dec_b2=state['dec2.bias'],
        centroids=rng.normal(0, 1, (k, latent)),
        centroid_traits=rng.uniform(20, 80, (k, 5)),
        type_names=np.array(['The Explorer', 'The Organiser', 'The Connector',
                             'The Observer', 'The Diplomat', 'The Anchor']),
        latent_mean=np.zeros(latent), latent_std=np.ones(latent),
        recon_mean=np.float64(0.8), recon_std=np.float64(0.2),
        trait_quantiles=np.stack([np.linspace(0, 100, 101)] * 5),
        meta_json=json.dumps({'version': 'test', 'n_train': 123456}),
    )
    return path, state


class TestWeightOrientation:
    def test_encoder_matches_the_torch_forward_pass(self, tmp_path):
        path, state = build_fake_export(str(tmp_path))
        engine = ModelInferenceEngine(weights_path=path)
        assert engine.is_trained

        raw = np.random.default_rng(2).integers(1, 6, len(ITEM_ORDER)).astype(float)
        # The engine guards the division, so the reference pass must too.
        x = (raw - 3.0) / (1.2 + 1e-8)

        h = np.tanh(torch_linear(x, state['enc1.weight'], state['enc1.bias']))
        h = np.tanh(torch_linear(h, state['enc2.weight'], state['enc2.bias']))
        expected = torch_linear(h, state['mu.weight'], state['mu.bias'])

        np.testing.assert_allclose(engine.encode(list(raw)), expected, rtol=1e-10)

    def test_decoder_matches_the_torch_forward_pass(self, tmp_path):
        path, state = build_fake_export(str(tmp_path))
        engine = ModelInferenceEngine(weights_path=path)

        latent = np.random.default_rng(3).normal(0, 1, 16)
        h = np.tanh(torch_linear(latent, state['dec1.weight'], state['dec1.bias']))
        expected = torch_linear(h, state['dec2.weight'], state['dec2.bias'])

        np.testing.assert_allclose(engine.decode(latent), expected, rtol=1e-10)

    def test_mismatched_item_order_is_refused(self, tmp_path):
        """A reordered bank must fail loudly, not transpose the inputs silently."""
        path, _ = build_fake_export(str(tmp_path))
        data = dict(np.load(path, allow_pickle=False))
        shuffled = list(ITEM_ORDER)
        shuffled[0], shuffled[1] = shuffled[1], shuffled[0]
        data['item_order'] = np.array(shuffled)
        bad = os.path.join(str(tmp_path), 'bad.npz')
        np.savez_compressed(bad, **data)

        assert ModelInferenceEngine(weights_path=bad).is_trained is False


# ----------------------------------------------------------------- inference

class TestInference:
    def test_trained_result_shape(self, tmp_path):
        path, _ = build_fake_export(str(tmp_path))
        engine = ModelInferenceEngine(weights_path=path)
        raw = list(np.random.default_rng(4).integers(1, 6, len(ITEM_ORDER)).astype(float))
        scores = {t: 50.0 for t in TRAIT_ORDER}

        out = engine.process(raw, scores)
        assert out['weights_loaded'] is True
        assert 0 <= out['type_index'] < 6
        assert 0.0 <= out['confidence'] <= 1.0
        assert 0.0 <= out['novelty_score'] <= 1.0
        assert len(out['latent']) == 16
        assert out['percentiles'] is not None
        assert sum(out['type_probabilities']) == pytest.approx(1.0, abs=1e-3)

    def test_deterministic(self, tmp_path):
        path, _ = build_fake_export(str(tmp_path))
        engine = ModelInferenceEngine(weights_path=path)
        raw = list(np.full(len(ITEM_ORDER), 4.0))
        scores = {t: 60.0 for t in TRAIT_ORDER}
        assert engine.process(raw, scores) == engine.process(raw, scores)

    def test_untrained_is_honest_and_never_random(self):
        engine = ModelInferenceEngine(weights_path='/nonexistent/ocean_vae.npz')
        assert engine.is_trained is False
        scores = {'O': 80.0, 'C': 50.0, 'E': 50.0, 'A': 50.0, 'N': 50.0}
        first = engine.process(list(np.full(len(ITEM_ORDER), 3.0)), scores)
        second = engine.process(list(np.full(len(ITEM_ORDER), 3.0)), scores)
        assert first == second
        assert first['weights_loaded'] is False
        assert first['confidence'] is None
        assert 'notice' in first
        # Openness is the outlier, so it should pick that slot.
        assert first['type_index'] == TRAIT_ORDER.index('O')


# ------------------------------------------------- clustering and naming

class TestClusteringHelpers:
    def test_kmeans_recovers_separated_blobs(self):
        rng = np.random.default_rng(9)
        centres = np.array([[-6.0, -6.0], [6.0, 6.0], [-6.0, 6.0]])
        points = np.vstack([c + rng.normal(0, 0.4, (200, 2)) for c in centres])
        found, labels = trainer.kmeans(points, 3, seed=9)
        assert len(set(labels.tolist())) == 3
        for centre in centres:
            assert np.min(np.linalg.norm(found - centre, axis=1)) < 1.0

    def test_cluster_names_are_unique(self):
        rng = np.random.default_rng(12)
        traits = rng.uniform(20, 80, (6, 5))
        names = trainer.name_clusters(traits)
        assert len(names) == 6
        assert len(set(names)) == 6

    def test_cluster_named_for_its_standout_trait(self):
        # Six clusters, each defined by one trait running high.
        traits = np.full((5, 5), 50.0)
        for i in range(5):
            traits[i, i] = 90.0
        names = trainer.name_clusters(traits)
        for i, trait in enumerate(TRAIT_ORDER):
            assert names[i] == trainer.TRAIT_NAMES[trait][0]
