"""
This module handles:
1. Loading pre-trained VAE model from disk
2. Preprocessing corrected trait scores (z-score normalization)
3. Running VAE forward pass (inference)
4. Calculating reconstruction error for anomaly detection
5. Computing latent space representations
6. Classification into personality types (A-F)
7. Novelty scoring (unusual profile detection)
8. Confidence estimation
9. Batch processing support
10. GPU acceleration with automatic CPU fallback
"""

import logging
import os
import json
import time
from typing import Dict, Tuple, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
import threading
from collections import deque

import numpy as np
import torch
import torch.nn.functional as F
from sklearn.preprocessing import StandardScaler
from scipy.spatial.distance import mahalanobis
from scipy.stats import gaussian_kde

# CHANGE 5: Monitor model performance

def log_inference_metrics(self, input_vector, output):
    """Log metrics for model monitoring"""
    
    metrics = {
        'inference_timestamp': datetime.utcnow().isoformat(),
        'personality_type': output['personality_type'],
        'confidence': output['confidence'],
        'anomaly_score': output['anomaly_score'],
        'is_anomalous': output['is_anomalous'],
        'reconstruction_error': output['reconstruction_error'],
        'model_version': self.model_config.version
    }
    
    # Store in database for analysis
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO model_metrics 
           (personality_type, confidence, anomaly_score, created_at)
           VALUES (%s, %s, %s, %s)""",
        (metrics['personality_type'], metrics['confidence'], 
         metrics['anomaly_score'], metrics['inference_timestamp'])
    )
    conn.commit()
    
    logger.info(f"Inference metrics: {metrics}")








# CHANGE 4: Support batch inference for scaling

def infer_batch(self, input_vectors_batch):
    """Infer on multiple assessments (for batch processing)"""
    batch_size = len(input_vectors_batch)
    results = []
    
    try:
        # Convert to tensor
        batch_tensor = torch.from_numpy(
            np.array(input_vectors_batch, dtype=np.float32)
        ).to(self.device)
        
        with torch.no_grad():
            # Forward pass
            mu, logvar = self.model.encoder(batch_tensor)
            z = self.model.reparameterize(mu, logvar)
            
            # Get classifications for batch
            for i in range(batch_size):
                latent_vec = z[i:i+1]
                result = self._classify_from_latent(latent_vec)
                results.append(result)
        
        return {'success': True, 'results': results}
    
    except Exception as e:
        logger.error(f"Batch inference failed: {e}")
        return {'success': False, 'error': str(e), 'results': []}





# CHANGE 3: Provide detailed anomaly information

def detect_anomalies(self, latent_vector, scores):
    """
    Comprehensive anomaly detection
    
    Returns:
    - is_anomalous: bool
    - anomaly_score: 0-1
    - anomaly_reason: string (why it's unusual)
    - anomaly_severity: 'low', 'medium', 'high'
    """
    
    # Factor 1: Distance from population mean
    population_mean = torch.zeros_like(latent_vector)
    distance_from_mean = torch.norm(latent_vector - population_mean)
    
    # Factor 2: Local density
    nearest_distances = self._compute_knn_distances(latent_vector, k=5)
    mean_neighbor_distance = nearest_distances.mean()
    
    # Factor 3: Score inconsistency
    score_std = np.std(scores)
    
    # Combine factors
    anomaly_score = (
        0.3 * (distance_from_mean / 5.0) +  # Normalize by typical distance
        0.4 * (1 / (mean_neighbor_distance + 1)) +  # Invert density
        0.3 * score_std / 2.5  # Inconsistency
    )
    
    anomaly_score = max(0, min(1, anomaly_score))
    is_anomalous = anomaly_score > 0.6
    
    # Determine reason
    if distance_from_mean > 4.0:
        reason = "Unusual trait combination (far from typical profiles)"
    elif mean_neighbor_distance > 2.0:
        reason = "Isolated in personality space (rare profile)"
    elif score_std > 2.5:
        reason = "High inconsistency across domains"
    else:
        reason = "Profile within normal range"
    
    return {
        'is_anomalous': is_anomalous,
        'anomaly_score': float(anomaly_score),
        'anomaly_reason': reason,
        'anomaly_severity': 'high' if anomaly_score > 0.8 else 'medium' if anomaly_score > 0.6 else 'low'
    }





# CHANGE 2: Calibrate confidence scores

def calculate_confidence(self, latent_vector, reconstruction_error, distances):
    """
    Calculate calibrated confidence score
    
    Factors:
    - Reconstruction error (lower = more confident)
    - Distance to nearest cluster (closer = more confident)
    - Distance to population center
    - Entropy of cluster probabilities
    """
    
    # Factor 1: Reconstruction error (0-1 scale)
    # Good model fit = high confidence
    reconstruction_confidence = max(0, 1 - reconstruction_error / 0.5)
    
    # Factor 2: Cluster distance
    # Close to cluster center = high confidence
    min_distance = min(distances)
    distance_confidence = max(0, 1 - min_distance / 3.0)
    
    # Factor 3: Entropy of probabilities
    probabilities = torch.softmax(torch.tensor(distances, dtype=torch.float32), dim=0)
    entropy = -torch.sum(probabilities * torch.log(probabilities + 1e-8))
    entropy_confidence = max(0, 1 - entropy / 2.0)
    
    # Combine factors
    overall_confidence = (
        0.4 * reconstruction_confidence +
        0.4 * distance_confidence +
        0.2 * entropy_confidence
    )
    
    return max(0, min(1, overall_confidence))

# ============================================================================
# CONFIGURATION & CONSTANTS
# ============================================================================

class MLPipelineConfig:
    """Configuration for ML pipeline."""
    
    # Model paths
    MODEL_DIR = Path(os.getenv('MODEL_DIR', './backend/models'))
    VAE_MODEL_PATH = MODEL_DIR / 'vae_model.pt'
    SCALER_PATH = MODEL_DIR / 'scaler_stats.json'
    POPULATION_STATS_PATH = MODEL_DIR / 'population_stats.json'
    
    # Device configuration
    DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
    USE_AMP = torch.cuda.is_available()  # Automatic Mixed Precision
    
    # Model architecture parameters
    INPUT_DIM = 9  # [R, S, C, A, O, E, Lambda, Sigma, Demo_Effect]
    LATENT_DIM = 16  # Latent space dimensionality
    HIDDEN_DIMS = [64, 32, 16]  # Encoder/decoder hidden dimensions
    
    # Thresholds
    NOVELTY_THRESHOLD = 2.5  # Standard deviations from population mean
    RECONSTRUCTION_THRESHOLD = 0.85  # Max allowed reconstruction error
    CONFIDENCE_MIN = 0.70  # Minimum confidence to return result
    
    # Personality type thresholds
    PERSONALITY_TYPE_MAP = {
        'A': 'Ambitious Explorer',      # High status, open to experience
        'B': 'Devoted Protector',       # High agreeableness, conscientiousness
        'C': 'Balanced Harmonizer',     # Moderate across domains
        'D': 'Cautious Analyzer',       # Low extraversion, high openness
        'E': 'Authentic Connector',     # Low deception, high agreeableness
        'F': 'Independent Maverick'     # Low agreeableness, high status
    }
    
    # Batch processing
    BATCH_SIZE = 32
    MAX_QUEUE_SIZE = 1000
    
    # Logging
    LOG_LEVEL = logging.INFO
    LOG_FILE = 'logs/ml_pipeline.log'


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging(config: MLPipelineConfig) -> logging.Logger:
    """Set up logging for ML pipeline."""
    logger = logging.getLogger('MLPipeline')
    logger.setLevel(config.LOG_LEVEL)
    
    # File handler
    os.makedirs(os.path.dirname(config.LOG_FILE) or '.', exist_ok=True)
    file_handler = logging.FileHandler(config.LOG_FILE)
    file_handler.setLevel(config.LOG_LEVEL)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(config.LOG_LEVEL)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger


logger = setup_logging(MLPipelineConfig())


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class TraitScores:
    """Container for trait scores (corrected)."""
    R: float  # Relationships
    S: float  # Status
    C: float  # Conscientiousness
    A: float  # Agreeableness
    O: float  # Openness
    E: float  # Emotional Stability
    
    def to_array(self) -> np.ndarray:
        """Convert to numpy array."""
        return np.array([self.R, self.S, self.C, self.A, self.O, self.E])
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class DeceptionMetrics:
    """Container for deception metrics."""
    lambda_value: float  # Deception susceptibility (0-1)
    contextual_sigma: float  # Context adjustment factor
    demo_effect: float  # Demographic adjustment
    
    def to_array(self) -> np.ndarray:
        """Convert to numpy array."""
        return np.array([self.lambda_value, self.contextual_sigma, self.demo_effect])


@dataclass
class VAEInferenceResult:
    """Result of VAE inference."""
    latent_representation: np.ndarray  # (16,)
    reconstruction_error: float
    reconstruction_loss: float
    novelty_score: float
    is_anomalous: bool
    confidence: float
    inference_time_ms: float


@dataclass
class PersonalityClassification:
    """Personality type classification result."""
    personality_type: str  # A-F
    type_label: str  # Human-readable name
    type_confidence: float  # 0-1
    feature_importance: Dict[str, float]  # Which features matter most


@dataclass
class MLPipelineOutput:
    """Complete output from ML pipeline."""
    assessment_id: str
    trait_scores: TraitScores
    deception_metrics: DeceptionMetrics
    vae_inference: VAEInferenceResult
    personality_classification: PersonalityClassification
    population_percentile: float  # Where they fall in population
    interpretation: str  # Human-readable interpretation
    processing_timestamp: str
    

# ============================================================================
# VAE MODEL ARCHITECTURE
# ============================================================================

class VariationalAutoencoder(torch.nn.Module):
    """
    Variational Autoencoder (VAE) for personality representation learning.
    
    Architecture:
    - Encoder: 9 → 64 → 32 → 16 (latent)
    - Decoder: 16 (latent) → 32 → 64 → 9
    
    Input: [R, S, C, A, O, E, Lambda, Sigma, Demo_effect]
    Output: Reconstruction of same 9D vector
    Latent: 16D representation
    """
    
    def __init__(
        self,
        input_dim: int = 9,
        hidden_dims: List[int] = None,
        latent_dim: int = 16,
        dropout_rate: float = 0.2
    ):
        super().__init__()
        
        if hidden_dims is None:
            hidden_dims = [64, 32, 16]
        
        self.input_dim = input_dim
        self.latent_dim = latent_dim
        self.hidden_dims = hidden_dims
        
        # ---- ENCODER ----
        encoder_layers = []
        in_features = input_dim
        
        for out_features in hidden_dims:
            encoder_layers.extend([
                torch.nn.Linear(in_features, out_features),
                torch.nn.BatchNorm1d(out_features),
                torch.nn.ReLU(),
                torch.nn.Dropout(dropout_rate)
            ])
            in_features = out_features
        
        self.encoder = torch.nn.Sequential(*encoder_layers)
        
        # Latent space
        self.fc_mu = torch.nn.Linear(hidden_dims[-1], latent_dim)
        self.fc_logvar = torch.nn.Linear(hidden_dims[-1], latent_dim)
        
        # ---- DECODER ----
        decoder_layers = []
        in_features = latent_dim
        
        for out_features in reversed(hidden_dims):
            decoder_layers.extend([
                torch.nn.Linear(in_features, out_features),
                torch.nn.BatchNorm1d(out_features),
                torch.nn.ReLU(),
                torch.nn.Dropout(dropout_rate)
            ])
            in_features = out_features
        
        decoder_layers.append(torch.nn.Linear(in_features, input_dim))
        self.decoder = torch.nn.Sequential(*decoder_layers)
    
    def encode(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """Encode input to latent space.
        
        Returns:
            mu: Mean of latent distribution
            logvar: Log variance of latent distribution
        """
        h = self.encoder(x)
        mu = self.fc_mu(h)
        logvar = self.fc_logvar(h)
        return mu, logvar
    
    def reparameterize(
        self,
        mu: torch.Tensor,
        logvar: torch.Tensor
    ) -> torch.Tensor:
        """Reparameterization trick: sample from N(mu, sigma)."""
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        z = mu + eps * std
        return z
    
    def decode(self, z: torch.Tensor) -> torch.Tensor:
        """Decode latent representation back to input space."""
        return self.decoder(z)
    
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Forward pass.
        
        Returns:
            recon_x: Reconstructed input
            mu: Latent mean
            logvar: Latent log variance
        """
        mu, logvar = self.encode(x)
        z = self.reparameterize(mu, logvar)
        recon_x = self.decode(z)
        return recon_x, mu, logvar
    
    def get_latent(self, x: torch.Tensor) -> torch.Tensor:
        """Get latent representation (without sampling)."""
        mu, _ = self.encode(x)
        return mu


# ============================================================================
# ML PIPELINE CORE
# ============================================================================

class MLPipeline:
    """
    Machine Learning pipeline for personality assessment.
    
    Handles:
    - Model loading and validation
    - Batch preprocessing (z-score normalization)
    - VAE inference
    - Reconstruction error calculation
    - Novelty detection
    - Personality classification
    - Confidence estimation
    """
    
    def __init__(self, config: MLPipelineConfig = None):
        """Initialize ML pipeline.
        
        Args:
            config: MLPipelineConfig instance
            
        Raises:
            FileNotFoundError: If model files not found
            torch.cuda.OutOfMemoryError: If GPU memory exceeded
        """
        self.config = config or MLPipelineConfig()
        self.device = torch.device(self.config.DEVICE)
        
        # Load model
        try:
            self.model = self._load_model()
            logger.info(f'VAE model loaded successfully on {self.device}')
        except Exception as e:
            logger.error(f'Failed to load VAE model: {e}')
            raise
        
        # Load normalization stats
        try:
            self.scaler = self._load_scaler()
            self.population_stats = self._load_population_stats()
            logger.info('Scaler and population stats loaded')
        except Exception as e:
            logger.error(f'Failed to load scaler/population stats: {e}')
            raise
        
        # Request queue for async processing
        self.request_queue = deque(maxlen=self.config.MAX_QUEUE_SIZE)
        self.results_cache = {}
        self.cache_lock = threading.Lock()
        
        # Performance metrics
        self.inference_times = deque(maxlen=1000)
        self.total_processed = 0
        
        logger.info('MLPipeline initialized')
    
    def _load_model(self) -> VariationalAutoencoder:
        """Load pre-trained VAE model from disk.
        
        Returns:
            VariationalAutoencoder instance
            
        Raises:
            FileNotFoundError: If model file doesn't exist
        """
        if not self.config.VAE_MODEL_PATH.exists():
            raise FileNotFoundError(
                f'VAE model not found at {self.config.VAE_MODEL_PATH}'
            )
        
        model = VariationalAutoencoder(
            input_dim=self.config.INPUT_DIM,
            hidden_dims=self.config.HIDDEN_DIMS,
            latent_dim=self.config.LATENT_DIM
        )
        
        checkpoint = torch.load(
            self.config.VAE_MODEL_PATH,
            map_location=self.device
        )
        model.load_state_dict(checkpoint['model_state_dict'])
        model.to(self.device)
        model.eval()
        
        logger.info(f'Model loaded from {self.config.VAE_MODEL_PATH}')
        return model
    
    def _load_scaler(self) -> Dict[str, np.ndarray]:
        """Load normalization statistics (mean, std).
        
        Returns:
            Dict with 'mean' and 'std' arrays
        """
        if not self.config.SCALER_PATH.exists():
            logger.warning('Scaler not found, using default normalization')
            return {
                'mean': np.zeros(self.config.INPUT_DIM),
                'std': np.ones(self.config.INPUT_DIM)
            }
        
        with open(self.config.SCALER_PATH, 'r') as f:
            stats = json.load(f)
        
        return {
            'mean': np.array(stats['mean']),
            'std': np.array(stats['std'])
        }
    
    def _load_population_stats(self) -> Dict[str, Any]:
        """Load population-level statistics for novelty detection.
        
        Returns:
            Dict with population mean, covariance, density info
        """
        if not self.config.POPULATION_STATS_PATH.exists():
            logger.warning('Population stats not found, using defaults')
            return {
                'latent_mean': np.zeros(self.config.LATENT_DIM),
                'latent_cov': np.eye(self.config.LATENT_DIM),
                'reconstruction_mean': 0.5,
                'reconstruction_std': 0.1
            }
        
        with open(self.config.POPULATION_STATS_PATH, 'r') as f:
            stats = json.load(f)
        
        return {
            'latent_mean': np.array(stats['latent_mean']),
            'latent_cov': np.array(stats['latent_cov']),
            'reconstruction_mean': stats['reconstruction_mean'],
            'reconstruction_std': stats['reconstruction_std']
        }
    
    def preprocess_input(
        self,
        trait_scores: TraitScores,
        deception_metrics: DeceptionMetrics
    ) -> np.ndarray:
        """Preprocess input for VAE.
        
        Combines trait scores and deception metrics into 9D vector,
        then applies z-score normalization.
        
        Args:
            trait_scores: TraitScores instance
            deception_metrics: DeceptionMetrics instance
            
        Returns:
            Normalized 9D array
        """
        # Combine into single vector
        traits = trait_scores.to_array()  # [R, S, C, A, O, E]
        deception = deception_metrics.to_array()  # [Lambda, Sigma, Demo]
        
        x = np.concatenate([traits, deception])  # Shape: (9,)
        
        # Normalize
        if self.scaler['std'].any():
            x_normalized = (x - self.scaler['mean']) / self.scaler['std']
        else:
            x_normalized = x - self.scaler['mean']
        
        # Clip to prevent extreme values
        x_normalized = np.clip(x_normalized, -5, 5)
        
        return x_normalized
    
    def inference(
        self,
        trait_scores: TraitScores,
        deception_metrics: DeceptionMetrics,
        return_latent: bool = True
    ) -> VAEInferenceResult:
        """Run VAE inference on single sample.
        
        Args:
            trait_scores: TraitScores instance
            deception_metrics: DeceptionMetrics instance
            return_latent: Whether to return latent representation
            
        Returns:
            VAEInferenceResult with reconstruction error, novelty, etc.
        """
        start_time = time.perf_counter()
        
        # Preprocess
        x_np = self.preprocess_input(trait_scores, deception_metrics)
        x_tensor = torch.FloatTensor(x_np).unsqueeze(0).to(self.device)
        
        # Forward pass
        with torch.no_grad():
            if self.config.USE_AMP:
                with torch.cuda.amp.autocast():
                    recon_x, mu, logvar = self.model(x_tensor)
            else:
                recon_x, mu, logvar = self.model(x_tensor)
        
        # Calculate reconstruction error (MSE)
        reconstruction_loss = F.mse_loss(
            recon_x, x_tensor, reduction='mean'
        ).item()
        
        # Normalize reconstruction error (scale to 0-1)
        reconstruction_error = min(reconstruction_loss, 1.0)
        
        # Get latent representation
        latent = mu.squeeze(0).cpu().numpy()
        
        # Calculate novelty score
        novelty_score = self._calculate_novelty_score(
            latent, reconstruction_error
        )
        
        # Determine if anomalous
        is_anomalous = (
            novelty_score > self.config.NOVELTY_THRESHOLD or
            reconstruction_error > self.config.RECONSTRUCTION_THRESHOLD
        )
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            novelty_score, reconstruction_error
        )
        
        # Timing
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        self.inference_times.append(elapsed_ms)
        
        return VAEInferenceResult(
            latent_representation=latent,
            reconstruction_error=reconstruction_error,
            reconstruction_loss=reconstruction_loss,
            novelty_score=novelty_score,
            is_anomalous=is_anomalous,
            confidence=confidence,
            inference_time_ms=elapsed_ms
        )
    
    def _calculate_novelty_score(
        self,
        latent: np.ndarray,
        reconstruction_error: float
    ) -> float:
        """Calculate novelty score (how unusual the profile is).
        
        Combines:
        1. Mahalanobis distance in latent space
        2. Reconstruction error magnitude
        3. Local density estimation
        
        Returns:
            Novelty score (higher = more unusual, typically 0-3)
        """
        try:
            # 1. Mahalanobis distance
            pop_mean = self.population_stats['latent_mean']
            pop_cov = self.population_stats['latent_cov']
            
            try:
                mahal_dist = mahalanobis(
                    latent,
                    pop_mean,
                    np.linalg.inv(pop_cov)
                )
            except np.linalg.LinAlgError:
                # Fallback to Euclidean distance if covariance singular
                mahal_dist = np.linalg.norm(latent - pop_mean)
            
            # 2. Reconstruction error component
            recon_mean = self.population_stats['reconstruction_mean']
            recon_std = self.population_stats['reconstruction_std']
            
            recon_zscore = (reconstruction_error - recon_mean) / (recon_std + 1e-8)
            
            # 3. Combined score (weighted)
            novelty = 0.7 * (mahal_dist / np.sqrt(self.config.LATENT_DIM)) + \
                      0.3 * np.abs(recon_zscore)
            
            return float(novelty)
        
        except Exception as e:
            logger.warning(f'Error calculating novelty score: {e}')
            return 0.0
    
    def _calculate_confidence(
        self,
        novelty_score: float,
        reconstruction_error: float
    ) -> float:
        """Calculate confidence in the classification.
        
        Factors:
        - Lower reconstruction error → higher confidence
        - Moderate novelty → higher confidence
        - Extreme novelty → lower confidence (unusual pattern)
        
        Returns:
            Confidence score (0-1)
        """
        # Reconstruction error component (lower is better)
        recon_confidence = 1.0 - reconstruction_error
        
        # Novelty component (moderate is better)
        # Penalize both very low and very high novelty
        if novelty_score < 0.5:
            novelty_confidence = 0.85
        elif novelty_score < 2.5:
            novelty_confidence = 0.95
        elif novelty_score < 3.5:
            novelty_confidence = 0.80
        else:
            novelty_confidence = 0.65
        
        # Combine
        confidence = 0.6 * recon_confidence + 0.4 * novelty_confidence
        
        return float(np.clip(confidence, 0.0, 1.0))
    
    def classify_personality(
        self,
        trait_scores: TraitScores,
        vae_result: VAEInferenceResult
    ) -> PersonalityClassification:
        """Classify personality type based on trait scores and VAE result.
        
        Classification rules:
        - Type A: High S (Status), High O (Openness) → Ambitious Explorer
        - Type B: High A (Agreeableness), High C (Conscientiousness) → Devoted Protector
        - Type C: Balanced across domains → Balanced Harmonizer
        - Type D: Low E (Extraversion), High O (Openness) → Cautious Analyzer
        - Type E: Low Lambda, High A → Authentic Connector
        - Type F: Low A, High S → Independent Maverick
        
        Args:
            trait_scores: TraitScores instance
            vae_result: VAEInferenceResult from inference()
            
        Returns:
            PersonalityClassification instance
        """
        # Calculate normalized scores (1-5 scale)
        scores = {
            'R': trait_scores.R,
            'S': trait_scores.S,
            'C': trait_scores.C,
            'A': trait_scores.A,
            'O': trait_scores.O,
            'E': trait_scores.E
        }
        
        # Classify based on scores
        type_scores = {
            'A': max(0, (scores['S'] - 3) * 0.3 + (scores['O'] - 3) * 0.3 + 
                        (5 - scores['A']) * 0.2 + (5 - scores['C']) * 0.2),
            'B': max(0, (scores['A'] - 3) * 0.35 + (scores['C'] - 3) * 0.35 +
                        (5 - scores['S']) * 0.15 + (5 - scores['O']) * 0.15),
            'C': 5.0 - np.std([scores['R'], scores['S'], scores['C'],
                               scores['A'], scores['O'], scores['E']]),
            'D': max(0, (scores['O'] - 3) * 0.4 + (5 - scores['E']) * 0.3 +
                        (5 - scores['S']) * 0.3),
            'E': max(0, (scores['A'] - 3) * 0.4 + 
                        (5 - scores['E']) * 0.3 + (5 - scores['S']) * 0.3),
            'F': max(0, (scores['S'] - 3) * 0.35 + (5 - scores['A']) * 0.35 +
                        (scores['O'] - 3) * 0.15 + (5 - scores['C']) * 0.15)
        }
        
        # Normalize scores to probabilities
        max_score = max(type_scores.values())
        if max_score > 0:
            type_probs = {k: v / max_score for k, v in type_scores.items()}
        else:
            type_probs = {k: 1/6 for k in type_scores.keys()}
        
        # Select type with highest score
        personality_type = max(type_probs, key=type_probs.get)
        type_confidence = float(type_probs[personality_type])
        
        # Feature importance
        feature_importance = {
            'Status': abs(scores['S'] - 3) / 2,
            'Openness': abs(scores['O'] - 3) / 2,
            'Agreeableness': abs(scores['A'] - 3) / 2,
            'Conscientiousness': abs(scores['C'] - 3) / 2,
            'Relationships': abs(scores['R'] - 3) / 2,
            'Emotional_Stability': abs(scores['E'] - 3) / 2
        }
        
        # Normalize importance
        total_importance = sum(feature_importance.values())
        if total_importance > 0:
            feature_importance = {
                k: v / total_importance for k, v in feature_importance.items()
            }
        
        return PersonalityClassification(
            personality_type=personality_type,
            type_label=self.config.PERSONALITY_TYPE_MAP[personality_type],
            type_confidence=type_confidence,
            feature_importance=feature_importance
        )
    
    def calculate_percentile(
        self,
        trait_scores: TraitScores,
        latent: np.ndarray
    ) -> float:
        """Calculate percentile position in population.
        
        Args:
            trait_scores: TraitScores instance
            latent: Latent representation from VAE
            
        Returns:
            Percentile (0-100)
        """
        try:
            # Calculate Euclidean distance from population mean in latent space
            pop_mean = self.population_stats['latent_mean']
            distance = np.linalg.norm(latent - pop_mean)
            
            # Approximate percentile using assumed normal distribution
            # of distances in latent space
            std_distance = np.linalg.norm(
                np.eye(self.config.LATENT_DIM)
            )  # Expected std for unit normal
            
            z_score = distance / std_distance
            percentile = 100 * (1.0 - np.exp(-z_score ** 2 / 2))
            
            return float(np.clip(percentile, 0, 100))
        
        except Exception as e:
            logger.warning(f'Error calculating percentile: {e}')
            return 50.0
    
    def process(
        self,
        assessment_id: str,
        trait_scores: TraitScores,
        deception_metrics: DeceptionMetrics
    ) -> MLPipelineOutput:
        """Complete pipeline processing (all steps).
        
        Args:
            assessment_id: Unique assessment ID
            trait_scores: TraitScores instance
            deception_metrics: DeceptionMetrics instance
            
        Returns:
            MLPipelineOutput with all results
        """
        try:
            # Step 1: VAE inference
            vae_result = self.inference(trait_scores, deception_metrics)
            
            # Step 2: Personality classification
            personality = self.classify_personality(trait_scores, vae_result)
            
            # Step 3: Calculate percentile
            percentile = self.calculate_percentile(
                trait_scores,
                vae_result.latent_representation
            )
            
            # Step 4: Generate interpretation
            interpretation = self._generate_interpretation(
                trait_scores,
                personality,
                vae_result,
                percentile
            )
            
            # Compile output
            output = MLPipelineOutput(
                assessment_id=assessment_id,
                trait_scores=trait_scores,
                deception_metrics=deception_metrics,
                vae_inference=vae_result,
                personality_classification=personality,
                population_percentile=percentile,
                interpretation=interpretation,
                processing_timestamp=datetime.utcnow().isoformat()
            )
            
            self.total_processed += 1
            
            logger.info(
                f'Processed assessment {assessment_id}: '
                f'Type {personality.personality_type} '
                f'(confidence: {personality.type_confidence:.2f})'
            )
            
            return output
        
        except Exception as e:
            logger.error(f'Error processing assessment {assessment_id}: {e}')
            raise
    
    def _generate_interpretation(
        self,
        trait_scores: TraitScores,
        personality: PersonalityClassification,
        vae_result: VAEInferenceResult,
        percentile: float
    ) -> str:
        """Generate human-readable interpretation of results.
        
        Args:
            trait_scores: TraitScores instance
            personality: PersonalityClassification instance
            vae_result: VAEInferenceResult instance
            percentile: Population percentile
            
        Returns:
            Interpretation string
        """
        anomaly_note = (
            f"Your profile is relatively unusual (novelty: {vae_result.novelty_score:.2f}). "
            if vae_result.is_anomalous
            else ""
        )
        
        percentile_note = f"You rank in the {percentile:.0f}th percentile "
        if percentile < 25:
            percentile_note += "of lower scores across the population."
        elif percentile < 75:
            percentile_note += "of moderate scores across the population."
        else:
            percentile_note += "of higher scores across the population."
        
        interpretation = (
            f"Your personality type is: {personality.type_label}. "
            f"{anomaly_note}"
            f"{percentile_note} "
            f"This classification is {personality.type_confidence * 100:.0f}% confident."
        )
        
        return interpretation
    
    def batch_process(
        self,
        assessments: List[Tuple[str, TraitScores, DeceptionMetrics]]
    ) -> List[MLPipelineOutput]:
        """Process multiple assessments in batch.
        
        Args:
            assessments: List of (assessment_id, trait_scores, deception_metrics)
            
        Returns:
            List of MLPipelineOutput
        """
        results = []
        
        for assessment_id, trait_scores, deception_metrics in assessments:
            try:
                result = self.process(
                    assessment_id,
                    trait_scores,
                    deception_metrics
                )
                results.append(result)
            except Exception as e:
                logger.error(f'Batch processing error for {assessment_id}: {e}')
                continue
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get pipeline statistics.
        
        Returns:
            Dict with performance metrics
        """
        avg_time = np.mean(self.inference_times) if self.inference_times else 0
        
        return {
            'total_processed': self.total_processed,
            'avg_inference_time_ms': float(avg_time),
            'device': str(self.device),
            'model_params': sum(
                p.numel() for p in self.model.parameters() if p.requires_grad
            ),
            'cache_size': len(self.results_cache),
            'queue_size': len(self.request_queue)
        }
    
    def clear_cache(self):
        """Clear results cache."""
        with self.cache_lock:
            self.results_cache.clear()
        logger.info('Results cache cleared')


# ============================================================================
# BATCH PROCESSOR (ASYNC)
# ============================================================================

class BatchProcessor:
    """
    Async batch processor for ML pipeline.
    
    Useful for:
    - Processing multiple assessments in background
    - Rate limiting
    - Queueing requests
    """
    
    def __init__(self, pipeline: MLPipeline, batch_size: int = 32):
        """Initialize batch processor.
        
        Args:
            pipeline: MLPipeline instance
            batch_size: Number of samples to process at once
        """
        self.pipeline = pipeline
        self.batch_size = batch_size
        self.queue = deque()
        self.results = {}
        self.lock = threading.Lock()
        self.is_running = False
    
    def add_job(
        self,
        assessment_id: str,
        trait_scores: TraitScores,
        deception_metrics: DeceptionMetrics,
        callback: Optional[callable] = None
    ) -> str:
        """Add job to processing queue.
        
        Args:
            assessment_id: Unique assessment ID
            trait_scores: TraitScores instance
            deception_metrics: DeceptionMetrics instance
            callback: Optional function to call on completion
            
        Returns:
            Job ID
        """
        job = {
            'assessment_id': assessment_id,
            'trait_scores': trait_scores,
            'deception_metrics': deception_metrics,
            'callback': callback,
            'status': 'queued',
            'result': None
        }
        
        with self.lock:
            self.queue.append(job)
        
        return assessment_id
    
    def get_result(self, assessment_id: str) -> Optional[MLPipelineOutput]:
        """Get result for assessment (if available).
        
        Args:
            assessment_id: Assessment ID
            
        Returns:
            MLPipelineOutput or None
        """
        with self.lock:
            return self.results.get(assessment_id)
    
    def start(self):
        """Start processing thread."""
        if not self.is_running:
            self.is_running = True
            thread = threading.Thread(target=self._process_queue, daemon=True)
            thread.start()
            logger.info('Batch processor started')
    
    def stop(self):
        """Stop processing thread."""
        self.is_running = False
        logger.info('Batch processor stopped')
    
    def _process_queue(self):
        """Process queue continuously (runs in background thread)."""
        while self.is_running:
            batch = []
            
            with self.lock:
                for _ in range(min(self.batch_size, len(self.queue))):
                    if self.queue:
                        batch.append(self.queue.popleft())
            
            if batch:
                for job in batch:
                    try:
                        job['status'] = 'processing'
                        
                        result = self.pipeline.process(
                            job['assessment_id'],
                            job['trait_scores'],
                            job['deception_metrics']
                        )
                        
                        job['result'] = result
                        job['status'] = 'completed'
                        
                        with self.lock:
                            self.results[job['assessment_id']] = result
                        
                        # Call callback if provided
                        if job['callback']:
                            job['callback'](result)
                        
                        logger.info(f"Completed {job['assessment_id']}")
                    
                    except Exception as e:
                        job['status'] = 'error'
                        job['error'] = str(e)
                        logger.error(f"Error processing {job['assessment_id']}: {e}")
            
            else:
                time.sleep(0.1)  # Avoid busy-waiting


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def create_trait_scores(
    R: float, S: float, C: float, A: float, O: float, E: float
) -> TraitScores:
    """Create TraitScores instance from values."""
    return TraitScores(R=R, S=S, C=C, A=A, O=O, E=E)


def create_deception_metrics(
    lambda_value: float,
    contextual_sigma: float = 1.0,
    demo_effect: float = 0.0
) -> DeceptionMetrics:
    """Create DeceptionMetrics instance from values."""
    return DeceptionMetrics(
        lambda_value=lambda_value,
        contextual_sigma=contextual_sigma,
        demo_effect=demo_effect
    )


# ============================================================================
# MAIN EXECUTION / TESTING
# ============================================================================

def main():
    """Test ML pipeline with sample data."""
    
    # Initialize pipeline
    config = MLPipelineConfig()
    pipeline = MLPipeline(config)
    
    # Sample trait scores (corrected, 1-5 scale)
    trait_scores = create_trait_scores(
        R=3.2, S=3.8, C=3.5, A=3.6, O=4.1, E=3.4
    )
    
    # Sample deception metrics
    deception_metrics = create_deception_metrics(
        lambda_value=0.35,
        contextual_sigma=1.0,
        demo_effect=0.05
    )
    
    # Process single assessment
    print("Processing single assessment...")
    result = pipeline.process(
        assessment_id='TEST_001',
        trait_scores=trait_scores,
        deception_metrics=deception_metrics
    )
    
    print("\n" + "="*70)
    print("PIPELINE RESULT")
    print("="*70)
    print(f"Assessment ID: {result.assessment_id}")
    print(f"Personality Type: {result.personality_classification.type_label}")
    print(f"Confidence: {result.personality_classification.type_confidence:.2%}")
    print(f"Novelty Score: {result.vae_inference.novelty_score:.2f}")
    print(f"Is Anomalous: {result.vae_inference.is_anomalous}")
    print(f"Population Percentile: {result.population_percentile:.1f}")
    print(f"Interpretation: {result.interpretation}")
    print(f"Inference Time: {result.vae_inference.inference_time_ms:.2f} ms")
    
    # Get statistics
    print("\n" + "="*70)
    print("PIPELINE STATISTICS")
    print("="*70)
    stats = pipeline.get_statistics()
    for key, value in stats.items():
        print(f"{key}: {value}")


if __name__ == '__main__':
    main()
