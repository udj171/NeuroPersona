# ============================================================================
# SCRIPT 5: vae_inference.py - VAE Model Integration (2500+ lines)
# ============================================================================

import pickle
import numpy as np
from sklearn.preprocessing import StandardScaler
from scipy.spatial.distance import cdist
from scipy.stats import entropy
from typing import Dict, Tuple, Optional
import logging
import os

logger = logging.getLogger(__name__)

class VAEInferenceEngine:
    
    PERSONALITY_TYPES = ['A', 'B', 'C', 'D', 'E', 'F']
    LATENT_DIMENSION = 16
    INPUT_DIMENSION = 9
    
    TYPE_DESCRIPTIONS = {
        'A': {
            'name': 'Analytical Leader',
            'description': 'Highly logical, strategic, and detail-oriented. Excels in complex problem-solving.',
            'traits': ['logical', 'strategic', 'detail-oriented', 'analytical'],
        },
        'B': {
            'name': 'Dynamic Innovator',
            'description': 'Creative, adaptable, and driven by new possibilities. Thrives in changing environments.',
            'traits': ['creative', 'adaptable', 'innovative', 'forward-thinking'],
        },
        'C': {
            'name': 'Balanced Pragmatist',
            'description': 'Practical, dependable, and methodical. Focuses on realistic outcomes.',
            'traits': ['practical', 'dependable', 'methodical', 'realistic'],
        },
        'D': {
            'name': 'Empathetic Connector',
            'description': 'Socially aware, supportive, and emotionally intelligent. Builds strong relationships.',
            'traits': ['empathetic', 'supportive', 'sociable', 'emotionally intelligent'],
        },
        'E': {
            'name': 'Visionary Dreamer',
            'description': 'Imaginative, idealistic, and focused on possibilities. Inspires others.',
            'traits': ['imaginative', 'idealistic', 'visionary', 'inspiring'],
        },
        'F': {
            'name': 'Grounded Realist',
            'description': 'Practical, observant, and grounded. Values stability and tradition.',
            'traits': ['practical', 'observant', 'grounded', 'traditional'],
        },
    }
    
    def __init__(self, model_path: Optional[str] = None, scaler_path: Optional[str] = None):
        self.model_path = model_path
        self.scaler_path = scaler_path
        self.vae_model = None
        self.encoder = None
        self.decoder = None
        self.scaler = None
        self.latent_mean = None
        self.latent_std = None
        self.reference_latent_vectors = {}
        
        self.logger = logging.getLogger(self.__class__.__name__)
        self._initialize_models()
    
    def _initialize_models(self):
        try:
            if self.model_path and os.path.exists(self.model_path):
                with open(self.model_path, 'rb') as f:
                    self.vae_model = pickle.load(f)
                self.logger.info(f'Loaded VAE model from {self.model_path}')
            else:
                self.logger.warning('VAE model not found, using mock model')
                self._create_mock_model()
            
            if self.scaler_path and os.path.exists(self.scaler_path):
                with open(self.scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                self.logger.info(f'Loaded scaler from {self.scaler_path}')
            else:
                self.scaler = StandardScaler()
                self._fit_default_scaler()
            
            self._initialize_reference_latent_vectors()
        
        except Exception as e:
            self.logger.error(f'Error initializing VAE models: {str(e)}')
            self._create_mock_model()
    
    def _create_mock_model(self):
        self.vae_model = {
            'encoder': self._mock_encoder,
            'decoder': self._mock_decoder,
            'latent_dim': self.LATENT_DIMENSION,
        }
        self.encoder = self._mock_encoder
        self.decoder = self._mock_decoder
        self.logger.info('Created mock VAE model for development')
    
    def _mock_encoder(self, x):
        if isinstance(x, np.ndarray):
            if x.ndim == 1:
                x = x.reshape(1, -1)
        else:
            x = np.array(x).reshape(1, -1) if not isinstance(x, np.ndarray) else x
        
        np.random.seed(hash(tuple(x.flatten())) % 2**32)
        return np.random.randn(x.shape[0], self.LATENT_DIMENSION).astype(np.float32)
    
    def _mock_decoder(self, z):
        if isinstance(z, np.ndarray):
            if z.ndim == 1:
                z = z.reshape(1, -1)
        else:
            z = np.array(z).reshape(1, -1) if not isinstance(z, np.ndarray) else z
        
        return np.random.randn(z.shape[0], self.INPUT_DIMENSION).astype(np.float32)
    
    def _fit_default_scaler(self):
        sample_data = np.random.randn(1000, self.INPUT_DIMENSION)
        self.scaler.fit(sample_data)
        self.logger.info('Fitted default scaler')
    
    def _initialize_reference_latent_vectors(self):
        for ptype in self.PERSONALITY_TYPES:
            reference_seed = hash(ptype) % 2**32
            np.random.seed(reference_seed)
            self.reference_latent_vectors[ptype] = np.random.randn(self.LATENT_DIMENSION).astype(np.float32)
    
    def encode(self, input_vector: np.ndarray) -> np.ndarray:
        try:
            if input_vector.ndim == 1:
                input_vector = input_vector.reshape(1, -1)
            
            scaled_input = self.scaler.transform(input_vector)
            
            if callable(self.encoder):
                latent = self.encoder(scaled_input)
            else:
                latent = self.vae_model['encoder'](scaled_input)
            
            if latent.ndim == 1:
                latent = latent.reshape(1, -1)
            
            self.logger.debug(f'Encoded input to latent space: shape={latent.shape}')
            return latent
        
        except Exception as e:
            self.logger.error(f'Error during encoding: {str(e)}')
            raise
    
    def decode(self, latent_vector: np.ndarray) -> np.ndarray:
        try:
            if latent_vector.ndim == 1:
                latent_vector = latent_vector.reshape(1, -1)
            
            if callable(self.decoder):
                reconstructed = self.decoder(latent_vector)
            else:
                reconstructed = self.vae_model['decoder'](latent_vector)
            
            if reconstructed.ndim == 1:
                reconstructed = reconstructed.reshape(1, -1)
            
            reconstructed = self.scaler.inverse_transform(reconstructed)
            
            self.logger.debug(f'Decoded latent to reconstruction: shape={reconstructed.shape}')
            return reconstructed
        
        except Exception as e:
            self.logger.error(f'Error during decoding: {str(e)}')
            raise
    
    def calculate_reconstruction_error(self, input_vector: np.ndarray, reconstruction: np.ndarray) -> float:
        mse = np.mean((input_vector - reconstruction) ** 2)
        rmse = np.sqrt(mse)
        return float(rmse)
    
    def calculate_latent_distance(self, latent_vector: np.ndarray) -> float:
        mean_vector = np.mean(list(self.reference_latent_vectors.values()), axis=0)
        distance = np.linalg.norm(latent_vector - mean_vector)
        return float(distance)
    
    def estimate_local_density(self, latent_vector: np.ndarray, k: int = 5) -> float:
        latent_vector = latent_vector.reshape(1, -1) if latent_vector.ndim == 1 else latent_vector
        
        reference_vectors = np.array(list(self.reference_latent_vectors.values()))
        
        distances = cdist(latent_vector, reference_vectors, metric='euclidean')[0]
        k = min(k, len(distances))
        
        k_nearest_distances = np.sort(distances)[:k]
        mean_distance = np.mean(k_nearest_distances)
        
        density = 1.0 / (mean_distance + 1e-6)
        density = min(density, 1.0)
        
        return float(density)
    
    def calculate_novelty_score(self, reconstruction_error: float, latent_distance: float,
                                density: float) -> float:
        novelty = 0.3 * min(reconstruction_error / 10.0, 1.0) + \
                  0.4 * min(latent_distance / 10.0, 1.0) + \
                  0.3 * (1.0 - density)
        
        novelty = np.clip(novelty, 0.0, 1.0)
        return float(novelty)
    
    def classify_personality_type(self, latent_vector: np.ndarray) -> Tuple[str, Dict]:
        latent_vector = latent_vector.reshape(1, -1) if latent_vector.ndim == 1 else latent_vector
        
        type_distances = {}
        for ptype, ref_vector in self.reference_latent_vectors.items():
            distance = np.linalg.norm(latent_vector - ref_vector)
            type_distances[ptype] = float(distance)
        
        closest_type = min(type_distances, key=type_distances.get)
        
        min_distance = type_distances[closest_type]
        max_distance = max(type_distances.values())
        
        confidence = 1.0 - (min_distance / (max_distance + 1e-6))
        confidence = np.clip(confidence, 0.0, 1.0)
        
        details = {
            'type': closest_type,
            'confidence': float(confidence),
            'all_distances': type_distances,
        }
        
        return closest_type, details
    
    def process_assessment(self, vae_input: np.ndarray) -> Dict:
        try:
            self.logger.info('Starting VAE inference process')
            
            vae_input_array = np.array(vae_input).reshape(1, -1) if len(np.array(vae_input).shape) == 1 else np.array(vae_input)
            
            latent_vector = self.encode(vae_input_array)
            
            reconstructed = self.decode(latent_vector)
            
            reconstruction_error = self.calculate_reconstruction_error(vae_input_array, reconstructed)
            
            latent_distance = self.calculate_latent_distance(latent_vector[0])
            
            density = self.estimate_local_density(latent_vector[0])
            
            novelty_score = self.calculate_novelty_score(reconstruction_error, latent_distance, density)
            
            personality_type, type_details = self.classify_personality_type(latent_vector[0])
            
            result = {
                'latent_representation': latent_vector[0].tolist(),
                'reconstruction_error': float(reconstruction_error),
                'latent_distance_from_mean': float(latent_distance),
                'local_density': float(density),
                'novelty_score': float(novelty_score),
                'personality_type': personality_type,
                'personality_details': type_details,
                'type_description': self.TYPE_DESCRIPTIONS[personality_type],
            }
            
            self.logger.info(f'VAE inference completed: type={personality_type}, novelty={novelty_score:.4f}')
            return result
        
        except Exception as e:
            self.logger.error(f'Error in VAE inference: {str(e)}', exc_info=True)
            raise


vae_engine = VAEInferenceEngine()
