# ============================================================================
# SCRIPT 5: model_inference.py - Trained VAE Inference, numpy only
# ============================================================================
# The model is TRAINED in PyTorch on Kaggle (see training/) and SERVED here as
# a handful of numpy matrices. Production therefore needs numpy and nothing
# else, which is what lets the whole backend fit on a free host.
#
# Weight file contract (a single .npz, produced by training/train_vae_ocean.py):
#
#   item_order        (50,)      item ids, in the order the encoder expects
#   feature_mean      (50,)      per-item mean of the training responses
#   feature_std       (50,)      per-item std of the training responses
#   enc_w1 enc_b1                encoder layer 1
#   enc_w2 enc_b2                encoder layer 2
#   enc_mu_w enc_mu_b            latent mean head
#   dec_w1 dec_b1                decoder layer 1
#   dec_w2 dec_b2                decoder output layer
#   centroids         (K, L)     k-means centroids in latent space
#   centroid_traits   (K, 5)     mean O,C,E,A,N score of each cluster, 0-100
#   type_names        (K,)       display name per cluster
#   latent_mean       (L,)       training latent mean
#   latent_std        (L,)       training latent std
#   recon_mean        ()         mean reconstruction error on the training set
#   recon_std         ()         std of reconstruction error on the training set
#   trait_quantiles   (5, 101)   score at each percentile, per trait, for norms
#   meta_json         ()         json string: version, dataset, n_train, date
#
# If the file is absent the engine still answers, deterministically, and every
# response says weights_loaded false. It never fabricates a confident type.
# ============================================================================

import json
import logging
import os
from typing import Dict, List, Optional

import numpy as np

from ocean_items import ITEM_ORDER, TRAIT_ORDER

logger = logging.getLogger(__name__)

DEFAULT_WEIGHTS_PATH = os.path.join(os.path.dirname(__file__), 'model_weights', 'ocean_vae.npz')

# Used only when no trained weights are present, so the six slots still have
# names. Training overwrites these from the data.
FALLBACK_TYPE_NAMES = [
    'The Anchor', 'The Spark', 'The Analyst',
    'The Confidant', 'The Maker', 'The Observer',
]


def _tanh(x: np.ndarray) -> np.ndarray:
    return np.tanh(x)


class ModelInferenceEngine:
    """Loads exported VAE weights and scores one profile at a time."""

    def __init__(self, weights_path: Optional[str] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.weights_path = weights_path or os.getenv('MODEL_WEIGHTS_PATH', DEFAULT_WEIGHTS_PATH)
        self.weights: Optional[Dict[str, np.ndarray]] = None
        self.meta: Dict = {}
        self.type_names: List[str] = list(FALLBACK_TYPE_NAMES)
        self._load()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not os.path.exists(self.weights_path):
            self.logger.warning(
                f'[MODEL] No weight file at {self.weights_path}. '
                'Running in untrained mode: profiles are scored, but no type is claimed.'
            )
            return
        try:
            data = np.load(self.weights_path, allow_pickle=False)
            stored_order = [str(x) for x in data['item_order']]
            if stored_order != ITEM_ORDER:
                self.logger.error(
                    '[MODEL] ✗ Weight file item order does not match ocean_items.ITEM_ORDER. '
                    'Refusing to load, because the input columns would be silently transposed.'
                )
                return

            self.weights = {k: data[k] for k in data.files if k != 'meta_json'}
            if 'meta_json' in data.files:
                self.meta = json.loads(str(data['meta_json']))
            if 'type_names' in data.files:
                self.type_names = [str(x) for x in data['type_names']]

            k = self.weights['centroids'].shape[0]
            self.logger.info(
                f'[MODEL] ✓ Loaded weights from {self.weights_path} '
                f"({k} types, latent {self.weights['centroids'].shape[1]}, "
                f"trained on {self.meta.get('n_train', 'unknown')} responses)"
            )
        except Exception as exc:
            self.logger.error(f'[MODEL] ✗ Failed to load weights: {exc}', exc_info=True)
            self.weights = None

    @property
    def is_trained(self) -> bool:
        return self.weights is not None

    # ------------------------------------------------------------------
    # Forward pass
    # ------------------------------------------------------------------

    def encode(self, raw_responses: List[float]) -> np.ndarray:
        w = self.weights
        x = (np.asarray(raw_responses, dtype=np.float64) - w['feature_mean']) / (w['feature_std'] + 1e-8)
        h = _tanh(x @ w['enc_w1'] + w['enc_b1'])
        h = _tanh(h @ w['enc_w2'] + w['enc_b2'])
        return h @ w['enc_mu_w'] + w['enc_mu_b']

    def decode(self, latent: np.ndarray) -> np.ndarray:
        w = self.weights
        h = _tanh(latent @ w['dec_w1'] + w['dec_b1'])
        return h @ w['dec_w2'] + w['dec_b2']

    def percentiles(self, trait_scores: Dict[str, float]) -> Optional[Dict[str, float]]:
        """Where this profile sits in the reference sample, per trait."""
        if not self.is_trained or 'trait_quantiles' not in self.weights:
            return None
        table = self.weights['trait_quantiles']          # (5, 101)
        out = {}
        for idx, trait in enumerate(TRAIT_ORDER):
            rank = int(np.searchsorted(table[idx], trait_scores[trait], side='right'))
            out[trait] = float(np.clip(rank, 0, 100))
        return out

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def process(self, raw_responses: List[float],
                trait_scores: Dict[str, float]) -> Dict:
        if not self.is_trained:
            return self._untrained_result(trait_scores)

        w = self.weights
        latent = self.encode(raw_responses)
        reconstruction = self.decode(latent)

        x = (np.asarray(raw_responses, dtype=np.float64) - w['feature_mean']) / (w['feature_std'] + 1e-8)
        recon_error = float(np.mean((x - reconstruction) ** 2))

        distances = np.linalg.norm(w['centroids'] - latent, axis=1)
        order = np.argsort(distances)
        best, runner_up = int(order[0]), int(order[1])

        # Scale-free softmax over negative distance: temperature is the spread
        # of the distances themselves, so confidence means the same thing
        # whatever the latent space happens to be scaled to.
        temperature = max(float(np.std(distances)), 1e-6)
        weights_ = np.exp(-(distances - distances.min()) / temperature)
        probabilities = weights_ / weights_.sum()
        confidence = float(probabilities[best])

        latent_distance = float(np.linalg.norm(
            (latent - w['latent_mean']) / (w['latent_std'] + 1e-8)))
        novelty = self._novelty(recon_error, latent_distance)

        return {
            'weights_loaded': True,
            'type_index': best,
            'type_name': self.type_names[best],
            'type_traits': {t: round(float(v), 2) for t, v in
                            zip(TRAIT_ORDER, w['centroid_traits'][best])},
            'confidence': round(confidence, 4),
            'runner_up_index': runner_up,
            'runner_up_name': self.type_names[runner_up],
            'type_probabilities': [round(float(p), 4) for p in probabilities],
            'latent': [round(float(v), 5) for v in latent],
            'reconstruction_error': round(recon_error, 6),
            'latent_distance_from_mean': round(latent_distance, 4),
            'novelty_score': round(novelty, 4),
            'percentiles': self.percentiles(trait_scores),
            'model_version': self.meta.get('version', 'unknown'),
        }

    def _novelty(self, recon_error: float, latent_distance: float) -> float:
        """How unusual this profile is, relative to the training sample."""
        w = self.weights
        recon_mean = float(w['recon_mean'])
        recon_std = max(float(w['recon_std']), 1e-8)
        recon_z = (recon_error - recon_mean) / recon_std
        combined = 0.5 * recon_z + 0.5 * (latent_distance - 1.0)
        return float(np.clip(1.0 / (1.0 + np.exp(-combined)), 0.0, 1.0))

    def _untrained_result(self, trait_scores: Dict[str, float]) -> Dict:
        """Deterministic, and honest that no trained model is behind it.

        The type slot is filled by the trait that departs furthest from the
        profile's own mean. That is a description, not a prediction, and the
        confidence is deliberately absent rather than invented.
        """
        values = np.array([trait_scores[t] for t in TRAIT_ORDER])
        dominant = int(np.argmax(np.abs(values - values.mean())))
        return {
            'weights_loaded': False,
            'type_index': dominant,
            'type_name': self.type_names[dominant],
            'type_traits': {t: round(float(v), 2) for t, v in zip(TRAIT_ORDER, values)},
            'confidence': None,
            'runner_up_index': None,
            'runner_up_name': None,
            'type_probabilities': None,
            'latent': None,
            'reconstruction_error': None,
            'latent_distance_from_mean': None,
            'novelty_score': None,
            'percentiles': None,
            'model_version': 'untrained',
            'notice': ('No trained weights are installed, so this type is a plain '
                       'description of which trait stands out, not a model prediction.'),
        }


model_engine = None
