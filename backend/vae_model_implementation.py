"vae model pipeline"

import os
import sys
import json
import logging
import warnings
import pickle
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Union
from pathlib import Path
from dataclasses import dataclass, asdict
import numpy as np

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset
import matplotlib.pyplot as plt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('vae_model.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Suppress warnings
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)


# Use for diagnostics:
@app.route('/api/model-stats', methods=['GET'])
def get_model_stats():
    stats = vae_model.get_latent_statistics(...)
    return api_response(data=stats)












# ============================================================================
# DATA CLASSES & CONFIGURATION
# ============================================================================

@dataclass
class VAEConfig:
    """VAE model configuration"""
    # Architecture
    input_dim: int = 9  # 6 traits + Λ + σ + demo_effect
    latent_dim: int = 16  # Latent space dimension
    encoder_hidden_dims: List[int] = None  # [64, 32]
    decoder_hidden_dims: List[int] = None  # [32, 64]

    # Domain-specific configuration
    num_domains: int = 6  # R, S, C, A, O, E
    domain_dim: int = 2  # 2D latent per domain
    elephant_dim: int = 2  # Elephant module latent
    press_dim: int = 2  # Press secretary module latent

    # Training hyperparameters
    learning_rate: float = 1e-3
    batch_size: int = 32
    num_epochs: int = 100
    beta_max: float = 1.0  # KL annealing
    beta_anneal_steps: int = 50
    lambda_elephant: float = 0.5
    lambda_press: float = 0.5
    free_bits: float = 0.25  # Nats per dimension

    # Inference configuration
    novelty_threshold: float = 2.5  # Anomaly detection threshold
    temperature: float = 0.7  # Softmax temperature for classification

    # Device configuration
    device: str = 'cuda' if torch.cuda.is_available() else 'cpu'

    # Paths
    model_save_path: str = './models/vae_model.pt'
    checkpoint_dir: str = './checkpoints/'

    def __post_init__(self):
        """Post-initialization setup"""
        if self.encoder_hidden_dims is None:
            self.encoder_hidden_dims = [64, 32]
        if self.decoder_hidden_dims is None:
            self.decoder_hidden_dims = [32, 64]

        # Create checkpoint directory if it doesn't exist
        os.makedirs(self.checkpoint_dir, exist_ok=True)


@dataclass
class VAEOutput:
    """VAE inference output"""
    personality_type: str  # A, B, C, D, E, F
    confidence: float  # 0-1 confidence score
    novelty_score: float  # Novelty/anomaly score
    is_anomalous: bool  # Anomaly flag
    latent_vector: np.ndarray  # 16D latent representation
    reconstruction_error: float  # MSE reconstruction loss
    domain_scores: Dict[str, float]  # Per-domain scores
    elephant_latent: np.ndarray  # Overall deception module
    press_latent: np.ndarray  # Narrative coherence module
    timestamp: str  # Inference timestamp
    model_version: str  # Model version


@dataclass
class PersonalityType:
    """Personality type classification"""
    type_code: str  # A, B, C, D, E, F
    name: str
    description: str
    latent_center: np.ndarray  # Prototypical latent vector
    confidence_threshold: float  # Min confidence for this type


# ============================================================================
# VAE ARCHITECTURE
# ============================================================================

class DomainSpecificEncoder(nn.Module):
    """
    Domain-specific encoder network
    Input: 6D (domain responses) + 1D (consistency signals)
    Output: μ, σ (2D latent space)
    """

    def __init__(self, input_dim: int = 6, latent_dim: int = 2,
                 hidden_dims: List[int] = None):
        super(DomainSpecificEncoder, self).__init__()

        if hidden_dims is None:
            hidden_dims = [64, 32]

        self.input_dim = input_dim
        self.latent_dim = latent_dim

        # Encoder layers
        layers = []
        prev_dim = input_dim

        for hidden_dim in hidden_dims:
            layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.BatchNorm1d(hidden_dim),
                nn.ReLU()
            ])
            prev_dim = hidden_dim

        self.encoder = nn.Sequential(*layers)

        # Latent distribution parameters
        self.mu_layer = nn.Linear(prev_dim, latent_dim)
        self.logvar_layer = nn.Linear(prev_dim, latent_dim)

        # Initialize weights
        self._init_weights()

    def _init_weights(self):
        """Xavier/Kaiming initialization"""
        for layer in self.modules():
            if isinstance(layer, nn.Linear):
                nn.init.xavier_uniform_(layer.weight)
                if layer.bias is not None:
                    nn.init.zeros_(layer.bias)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass
        Args:
            x: (batch_size, input_dim) input tensor
        Returns:
            mu, logvar: (batch_size, latent_dim) distribution parameters
        """
        h = self.encoder(x)
        mu = self.mu_layer(h)
        logvar = self.logvar_layer(h)

        return mu, logvar


class DomainSpecificDecoder(nn.Module):
    """
    Domain-specific decoder network
    Input: 2D (domain latent) + 2D (elephant) + 2D (press) = 6D
    Output: 5D (reconstructed domain responses)
    """

    def __init__(self, latent_dim: int = 6, output_dim: int = 5,
                 hidden_dims: List[int] = None):
        super(DomainSpecificDecoder, self).__init__()

        if hidden_dims is None:
            hidden_dims = [32, 16]

        self.latent_dim = latent_dim
        self.output_dim = output_dim

        # Decoder layers
        layers = []
        prev_dim = latent_dim

        for hidden_dim in hidden_dims:
            layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.ReLU()
            ])
            prev_dim = hidden_dim

        self.decoder = nn.Sequential(*layers)

        # Output layer (5 domain responses)
        self.output_layer = nn.Linear(prev_dim, output_dim)

        # Initialize weights
        self._init_weights()

    def _init_weights(self):
        """Xavier/Kaiming initialization"""
        for layer in self.modules():
            if isinstance(layer, nn.Linear):
                nn.init.xavier_uniform_(layer.weight)
                if layer.bias is not None:
                    nn.init.zeros_(layer.bias)

    def forward(self, z_domain: torch.Tensor, z_elephant: torch.Tensor,
                z_press: torch.Tensor) -> torch.Tensor:
        """
        Forward pass with modular deception integration
        Args:
            z_domain: (batch_size, 2) domain latent
            z_elephant: (batch_size, 2) elephant module latent
            z_press: (batch_size, 2) press secretary module latent
        Returns:
            reconstructed: (batch_size, 5) reconstructed responses
        """
        # Concatenate all latent representations
        z_combined = torch.cat([z_domain, z_elephant, z_press], dim=1)

        # Decode
        h = self.decoder(z_combined)
        reconstructed = torch.sigmoid(self.output_layer(h)) * 5  # Scale to 0-5

        return reconstructed


class ElephantModule(nn.Module):
    """
    Elephant Module: Overall deception propensity
    Captures cross-domain consistent deception patterns
    Input: concatenated consistency signals from all domains
    Output: 2D latent (overall deception + audience sensitivity)
    """

    def __init__(self, input_dim: int = 6, latent_dim: int = 2):
        super(ElephantModule, self).__init__()

        self.input_dim = input_dim
        self.latent_dim = latent_dim

        # Consistency analyzer
        self.consistency_network = nn.Sequential(
            nn.Linear(input_dim, 32),
            nn.ReLU(),
            nn.BatchNorm1d(32),
            nn.Linear(32, 16),
            nn.ReLU()
        )

        # Latent distribution
        self.mu_layer = nn.Linear(16, latent_dim)
        self.logvar_layer = nn.Linear(16, latent_dim)

        self._init_weights()

    def _init_weights(self):
        for layer in self.modules():
            if isinstance(layer, nn.Linear):
                nn.init.xavier_uniform_(layer.weight)
                if layer.bias is not None:
                    nn.init.zeros_(layer.bias)

    def forward(self, consistency_signals: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            consistency_signals: (batch_size, 6) cross-domain consistency
        Returns:
            mu, logvar: (batch_size, latent_dim)
        """
        h = self.consistency_network(consistency_signals)
        mu = self.mu_layer(h)
        logvar = self.logvar_layer(h)

        return mu, logvar


class PressSecretaryModule(nn.Module):
    """
    Press Secretary Module: Narrative coherence and rationalization
    Captures ability to construct internally-consistent stories
    Input: response patterns across all domains
    Output: 2D latent (rationalization frequency + narrative coherence)
    """

    def __init__(self, input_dim: int = 30, latent_dim: int = 2):
        super(PressSecretaryModule, self).__init__()

        self.input_dim = input_dim
        self.latent_dim = latent_dim

        # Narrative coherence analyzer
        self.coherence_network = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.BatchNorm1d(64),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU()
        )

        # Latent distribution
        self.mu_layer = nn.Linear(16, latent_dim)
        self.logvar_layer = nn.Linear(16, latent_dim)

        self._init_weights()

    def _init_weights(self):
        for layer in self.modules():
            if isinstance(layer, nn.Linear):
                nn.init.xavier_uniform_(layer.weight)
                if layer.bias is not None:
                    nn.init.zeros_(layer.bias)

    def forward(self, responses: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            responses: (batch_size, 30) all responses
        Returns:
            mu, logvar: (batch_size, latent_dim)
        """
        h = self.coherence_network(responses)
        mu = self.mu_layer(h)
        logvar = self.logvar_layer(h)

        return mu, logvar


class VAEModel(nn.Module):
    """
    Complete VAE Model: Variational Autoencoder for Personality Assessment

    Architecture:
    - 6 domain-specific encoders (one per personality domain)
    - 1 elephant module (overall deception)
    - 1 press secretary module (narrative coherence)
    - 6 domain-specific decoders
    - Total latent dimension: 16D (6×2 + 2 + 2)
    """

    def __init__(self, config: VAEConfig = None):
        super(VAEModel, self).__init__()

        self.config = config or VAEConfig()
        self.device = self.config.device

        # Domain names
        self.domain_names = ['R', 'S', 'C', 'A', 'O', 'E']
        self.domain_deltas = {
            'R': 0.88,  # Sexual/Romantic
            'S': 0.82,  # Status/Confidence
            'C': 0.68,  # Conscientiousness
            'A': 0.62,  # Agreeableness
            'O': 0.58,  # Openness
            'E': 0.75  # Emotional Stability
        }

        # Domain-specific encoders
        self.domain_encoders = nn.ModuleDict({
            domain: DomainSpecificEncoder(
                input_dim=6,  # 5 responses + 1 consistency signal
                latent_dim=self.config.domain_dim,
                hidden_dims=self.config.encoder_hidden_dims
            )
            for domain in self.domain_names
        })

        # Meta-modules
        self.elephant_module = ElephantModule(
            input_dim=6,  # Consistency signals from 6 domains
            latent_dim=self.config.elephant_dim
        )

        self.press_module = PressSecretaryModule(
            input_dim=30,  # All 30 responses
            latent_dim=self.config.press_dim
        )

        # Domain-specific decoders
        self.domain_decoders = nn.ModuleDict({
            domain: DomainSpecificDecoder(
                latent_dim=6,  # 2 domain + 2 elephant + 2 press
                output_dim=5,  # 5 responses per domain
                hidden_dims=self.config.decoder_hidden_dims
            )
            for domain in self.domain_names
        })

        self.to(self.device)

    def reparameterize(self, mu: torch.Tensor, logvar: torch.Tensor) -> torch.Tensor:
        """
        Reparameterization trick: z = μ + σ * ε
        Args:
            mu: mean of distribution
            logvar: log variance of distribution
        Returns:
            z: sampled latent variable
        """
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        z = mu + eps * std
        return z

    def encode(self, responses: torch.Tensor, consistency_signals: torch.Tensor
               ) -> Tuple[Dict[str, torch.Tensor], torch.Tensor, torch.Tensor]:
        """
        Encode input to latent space
        Args:
            responses: (batch_size, 30) personality responses
            consistency_signals: (batch_size, 6) cross-domain consistency
        Returns:
            latents: dict of domain latents
            mu_elephant: elephant module mean
            logvar_elephant: elephant module log variance
        """
        latents = {}
        mus = {}
        logvars = {}

        # Encode each domain
        for i, domain in enumerate(self.domain_names):
            domain_responses = responses[:, i * 5:(i + 1) * 5]  # 5 responses per domain
            consistency = consistency_signals[:, i:i + 1]  # 1 consistency signal

            # Concatenate
            x_domain = torch.cat([domain_responses, consistency], dim=1)

            # Encode
            mu, logvar = self.domain_encoders[domain](x_domain)
            mus[domain] = mu
            logvars[domain] = logvar

            # Reparameterize
            z = self.reparameterize(mu, logvar)
            latents[domain] = z

        # Elephant module (consistency across domains)
        mu_elephant, logvar_elephant = self.elephant_module(consistency_signals)
        z_elephant = self.reparameterize(mu_elephant, logvar_elephant)
        latents['elephant'] = z_elephant

        # Press secretary module (narrative coherence)
        mu_press, logvar_press = self.press_module(responses)
        z_press = self.reparameterize(mu_press, logvar_press)
        latents['press'] = z_press

        # Store means and logvars for KL loss
        latents['mus'] = mus
        latents['logvars'] = logvars
        latents['mu_elephant'] = mu_elephant
        latents['logvar_elephant'] = logvar_elephant
        latents['mu_press'] = mu_press
        latents['logvar_press'] = logvar_press

        return latents, mu_elephant, logvar_elephant

    def decode(self, latents: Dict[str, torch.Tensor]) -> torch.Tensor:
        """
        Decode from latent space to responses
        Args:
            latents: dict of domain latents + elephant + press
        Returns:
            reconstructed: (batch_size, 30) reconstructed responses
        """
        reconstructed_domains = []

        z_elephant = latents['elephant']
        z_press = latents['press']

        # Decode each domain
        for domain in self.domain_names:
            z_domain = latents[domain]

            # Domain-specific decoder
            recon = self.domain_decoders[domain](z_domain, z_elephant, z_press)
            reconstructed_domains.append(recon)

        # Concatenate all reconstructed responses
        reconstructed = torch.cat(reconstructed_domains, dim=1)

        return reconstructed

    def forward(self, responses: torch.Tensor,
                consistency_signals: torch.Tensor) -> Tuple[torch.Tensor, Dict]:
        """
        Forward pass through VAE
        Args:
            responses: (batch_size, 30)
            consistency_signals: (batch_size, 6)
        Returns:
            reconstructed: (batch_size, 30)
            latents: dict containing all latent representations
        """
        # Encode
        latents, _, _ = self.encode(responses, consistency_signals)

        # Decode
        reconstructed = self.decode(latents)

        return reconstructed, latents

    def get_latent_vector(self, responses: torch.Tensor,
                          consistency_signals: torch.Tensor) -> np.ndarray:
        """
        Get 16D latent vector for a sample
        Args:
            responses: (30,) or (batch_size, 30)
            consistency_signals: (6,) or (batch_size, 6)
        Returns:
            latent: (16,) or (batch_size, 16) latent vector
        """
        # Ensure batch dimension
        if responses.dim() == 1:
            responses = responses.unsqueeze(0)
            consistency_signals = consistency_signals.unsqueeze(0)

        with torch.no_grad():
            latents, _, _ = self.encode(responses, consistency_signals)

            # Concatenate all latent vectors
            latent_parts = []
            for domain in self.domain_names:
                latent_parts.append(latents[domain])
            latent_parts.append(latents['elephant'])
            latent_parts.append(latents['press'])

            latent_vector = torch.cat(latent_parts, dim=1)

        return latent_vector.cpu().numpy()


# ============================================================================
# INFERENCE ENGINE
# ============================================================================

class VAEInferenceEngine:
    """
    VAE Inference Engine for personality assessment
    Handles model loading, inference, novelty detection, and classification
    """

    def __init__(self, model_path: str, config: VAEConfig = None):
        """
        Initialize inference engine
        Args:
            model_path: path to saved VAE model
            config: VAEConfig instance
        """
        self.config = config or VAEConfig()
        self.device = self.config.device

        # Load model
        self.model = self._load_model(model_path)
        self.model.eval()

        # Personality type prototypes
        self.personality_types = self._initialize_personality_types()

        # Latent space statistics
        self.latent_mean = None
        self.latent_std = None
        self.latent_density_estimator = None

        logger.info("VAE Inference Engine initialized successfully")

    def _load_model(self, model_path: str) -> VAEModel:
        """Load pre-trained VAE model"""
        logger.info(f"Loading VAE model from {model_path}")

        try:
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Model file not found: {model_path}")

            model = VAEModel(self.config)
            checkpoint = torch.load(model_path, map_location=self.device)

            if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
                model.load_state_dict(checkpoint['model_state_dict'])
            else:
                model.load_state_dict(checkpoint)

            logger.info("Model loaded successfully")
            return model

        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise

    def _initialize_personality_types(self) -> Dict[str, PersonalityType]:
        """
        Initialize personality type prototypes
        Based on Enhanced Hidden Motives Framework classification
        """
        types = {
            'A': PersonalityType(
                type_code='A',
                name='Authentic Contributor',
                description='High honesty across domains, low deception propensity, genuine values-aligned behavior',
                latent_center=np.array([-2.0] * 16),  # Exemplary prototype
                confidence_threshold=0.85
            ),
            'B': PersonalityType(
                type_code='B',
                name='Strategic Operator',
                description='Selective deception in high-pressure domains (R, S, E), authentic in others',
                latent_center=np.array([1.5, 1.5] + [-0.5] * 14),  # Selective deception
                confidence_threshold=0.75
            ),
            'C': PersonalityType(
                type_code='C',
                name='Consistent Strategist',
                description='Moderate deception across all domains, coherent false narrative',
                latent_center=np.array([0.5] * 16),  # Balanced deception
                confidence_threshold=0.70
            ),
            'D': PersonalityType(
                type_code='D',
                name='Sophisticated Deceiver',
                description='High deception with internally-consistent narrative, low detection markers',
                latent_center=np.array([2.0] * 12 + [0.5] * 4),  # High sophistication
                confidence_threshold=0.75
            ),
            'E': PersonalityType(
                type_code='E',
                name='Contradictory Performer',
                description='Inconsistent deception patterns, contradictory responses',
                latent_center=np.array([2.0, -2.0] * 8),  # Contradictory
                confidence_threshold=0.60
            ),
            'F': PersonalityType(
                type_code='F',
                name='Anomalous Profile',
                description='Unusual personality pattern, extreme or unusual trait combinations',
                latent_center=np.array([0.0] * 16),  # Neutral center
                confidence_threshold=0.50
            )
        }
        return types

    def infer(self, responses: np.ndarray, demographics: Dict[str, any],
              session_id: str = None) -> VAEOutput:
        """
        Run inference on personality responses

        Args:
            responses: (30,) array of 0-10 scale responses
            demographics: dict with 'age', 'sex', 'country'
            session_id: optional session identifier

        Returns:
            VAEOutput with classification and confidence
        """
        logger.info(f"Running VAE inference (session: {session_id})")

        try:
            # Convert to torch tensor
            responses_tensor = torch.from_numpy(responses).float().unsqueeze(0).to(self.device)

            # Calculate consistency signals (contradiction detection)
            consistency_signals = self._calculate_consistency_signals(responses)
            consistency_tensor = torch.from_numpy(consistency_signals).float().unsqueeze(0).to(self.device)

            # Forward pass through VAE
            with torch.no_grad():
                reconstructed, latents = self.model(responses_tensor, consistency_tensor)

                # Extract latent vector
                latent_vector = self.model.get_latent_vector(
                    responses_tensor, consistency_tensor
                ).squeeze(0)

                # Calculate reconstruction error
                recon_loss = F.mse_loss(reconstructed, responses_tensor)

                # Novelty detection
                novelty_score = self._calculate_novelty_score(latent_vector)
                is_anomalous = novelty_score > self.config.novelty_threshold

                # Personality classification
                personality_type, confidence = self._classify_personality(
                    latent_vector, responses, demographics
                )

                # Extract domain scores
                domain_scores = self._extract_domain_scores(latents)

                # Extract elephant and press modules
                elephant_latent = latents['elephant'].squeeze(0).cpu().numpy()
                press_latent = latents['press'].squeeze(0).cpu().numpy()

            # Create output
            output = VAEOutput(
                personality_type=personality_type,
                confidence=float(confidence),
                novelty_score=float(novelty_score),
                is_anomalous=bool(is_anomalous),
                latent_vector=latent_vector,
                reconstruction_error=float(recon_loss),
                domain_scores=domain_scores,
                elephant_latent=elephant_latent,
                press_latent=press_latent,
                timestamp=datetime.now().isoformat(),
                model_version='1.0'
            )

            logger.info(f"Inference complete: Type={personality_type}, Conf={confidence:.2f}")
            return output

        except Exception as e:
            logger.error(f"Error during inference: {e}")
            raise

    def _calculate_consistency_signals(self, responses: np.ndarray) -> np.ndarray:
        """
        Calculate cross-domain consistency signals
        Used to detect contradictory response patterns

        Args:
            responses: (30,) array

        Returns:
            consistency_signals: (6,) array (one per domain)
        """
        # Domain item ranges
        domain_ranges = {
            'R': (0, 5),  # R1-R5
            'S': (5, 10),  # S6-S10
            'C': (10, 15),  # C11-C15
            'A': (15, 20),  # A16-A20
            'O': (20, 25),  # O21-O25
            'E': (25, 30)  # E26-E30
        }

        consistency = np.zeros(6)

        # High A (altruistic) but low on validity items
        if np.mean(responses[15:20]) > 7.5 and responses[29] < 3:  # High A, low V35
            consistency[3] += 1.0  # Contradiction in agreeableness

        # High O (open-minded) but low on admitting limitations
        if np.mean(responses[20:25]) > 7.5 and responses[28] < 3:  # High O, low V34
            consistency[4] += 1.0

        # High E (emotionally stable) but admits to emotional struggles
        if np.mean(responses[25:30]) > 7.5 and responses[27] < 3:  # High E, low V33
            consistency[5] += 1.0

        # High C (conscientious) but low perceived reliability
        if np.mean(responses[10:15]) > 7.5 and responses[31] < 3 if len(responses) > 31 else False:
            consistency[2] += 1.0

        # Normalize: 0-1 scale (0 = consistent, 1 = highly contradictory)
        return consistency / 2.0

    def _calculate_novelty_score(self, latent_vector: np.ndarray) -> float:
        """
        Calculate novelty/anomaly score
        Combines reconstruction error and latent space distance

        Args:
            latent_vector: (16,) latent representation

        Returns:
            novelty_score: float (higher = more anomalous)
        """
        # Initialize if needed
        if self.latent_mean is None:
            # Use simple default (would be fitted on population in production)
            self.latent_mean = np.zeros(16)
            self.latent_std = np.ones(16)

        # Mahalanobis distance in latent space
        normalized = (latent_vector - self.latent_mean) / (self.latent_std + 1e-6)
        mahal_distance = np.sqrt(np.sum(normalized ** 2))

        # Scale: expect ~95% of samples within 3 std deviations
        novelty = max(0.0, (mahal_distance - 2.0) / 2.0)

        return float(novelty)

    def _classify_personality(self, latent_vector: np.ndarray,
                              responses: np.ndarray,
                              demographics: Dict) -> Tuple[str, float]:
        """
        Classify personality type using latent vector

        Args:
            latent_vector: (16,) latent representation
            responses: (30,) raw responses
            demographics: demographic info

        Returns:
            type_code: str (A-F)
            confidence: float (0-1)
        """
        # Calculate distances to each personality type prototype
        distances = {}
        for type_code, ptype in self.personality_types.items():
            # Euclidean distance to prototype
            dist = np.linalg.norm(latent_vector - ptype.latent_center)
            distances[type_code] = dist

        # Find closest type
        closest_type = min(distances, key=distances.get)

        # Calculate confidence
        dists = np.array(list(distances.values()))
        closest_dist = distances[closest_type]

        # Softmax over distances (lower distance = higher confidence)
        confidences = np.exp(-dists / self.config.temperature)
        confidences /= confidences.sum()
        confidence = float(confidences[list(distances.keys()).index(closest_type)])

        return closest_type, confidence

    def _extract_domain_scores(self, latents: Dict[str, torch.Tensor]) -> Dict[str, float]:
        """Extract domain-specific scores from latent representations"""
        domain_scores = {}

        for domain in self.model.domain_names:
            if domain in latents:
                # L2 norm of domain latent (0-1 scale roughly)
                latent = latents[domain].detach().cpu().numpy()[0]
                score = float(np.linalg.norm(latent) / 2.0)
                domain_scores[domain] = min(1.0, score)

        return domain_scores


# ============================================================================
# MODEL TRAINING (Optional - for retraining)
# ============================================================================

class VAETrainer:
    """
    VAE Trainer for model fitting (optional, used for retraining on new data)
    """

    def __init__(self, model: VAEModel, config: VAEConfig = None):
        self.model = model
        self.config = config or VAEConfig()
        self.device = self.config.device

        # Optimizer
        self.optimizer = torch.optim.Adam(
            self.model.parameters(),
            lr=self.config.learning_rate
        )

        # Tracking
        self.train_losses = []
        self.val_losses = []
        self.best_val_loss = float('inf')

    def vae_loss(self, batch: Tuple[torch.Tensor, torch.Tensor],
                 beta: float = 1.0) -> Tuple[torch.Tensor, Dict]:
        """
        Complete VAE loss function
        L = L_recon + β*L_KL + λ_e*L_elephant + λ_p*L_press
        """
        responses, consistency_signals = batch

        # Forward pass
        reconstructed, latents = self.model(responses, consistency_signals)

        # 1. Reconstruction loss (MSE)
        recon_loss = F.mse_loss(reconstructed, responses, reduction='mean')

        # 2. KL divergence losses
        kl_losses = {}
        total_kl = 0.0

        for domain in self.model.domain_names:
            mu = latents['mus'][domain]
            logvar = latents['logvars'][domain]

            # Standard normal prior KL
            kl = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp(), dim=1)
            kl = kl.mean()

            # Free bits constraint
            free_bits_nats = self.config.free_bits * self.model.config.domain_dim
            kl = torch.clamp(kl, min=free_bits_nats)

            kl_losses[domain] = kl
            total_kl += kl

        # Elephant module KL
        mu_e = latents['mu_elephant']
        logvar_e = latents['logvar_elephant']
        kl_e = -0.5 * torch.sum(1 + logvar_e - mu_e.pow(2) - logvar_e.exp(), dim=1)
        kl_e = kl_e.mean()
        kl_e = torch.clamp(kl_e, min=self.config.free_bits * self.model.config.elephant_dim)
        total_kl += kl_e

        # Press secretary module KL
        mu_p = latents['mu_press']
        logvar_p = latents['logvar_press']
        kl_p = -0.5 * torch.sum(1 + logvar_p - mu_p.pow(2) - logvar_p.exp(), dim=1)
        kl_p = kl_p.mean()
        kl_p = torch.clamp(kl_p, min=self.config.free_bits * self.model.config.press_dim)
        total_kl += kl_p

        # Total loss
        total_loss = recon_loss + beta * total_kl

        return total_loss, {
            'recon': recon_loss.item(),
            'kl_total': total_kl.item(),
            'kl_elephant': kl_e.item(),
            'kl_press': kl_p.item()
        }

    def train_epoch(self, train_loader: DataLoader, beta: float = 1.0) -> float:
        """Train for one epoch"""
        self.model.train()
        total_loss = 0.0

        for batch_idx, batch in enumerate(train_loader):
            self.optimizer.zero_grad()

            loss, losses_dict = self.vae_loss(batch, beta=beta)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
            self.optimizer.step()

            total_loss += loss.item()

            if (batch_idx + 1) % 10 == 0:
                logger.info(f"Batch {batch_idx + 1}: Loss={loss.item():.4f}")

        avg_loss = total_loss / len(train_loader)
        return avg_loss

    def train(self, train_loader: DataLoader, val_loader: DataLoader = None):
        """Train VAE model"""
        logger.info("Starting VAE training")

        for epoch in range(self.config.num_epochs):
            # Annealing schedule for β
            beta = min(
                self.config.beta_max,
                (epoch + 1) / self.config.beta_anneal_steps
            )

            # Train epoch
            train_loss = self.train_epoch(train_loader, beta=beta)
            self.train_losses.append(train_loss)

            # Validation
            if val_loader:
                val_loss = self.validate(val_loader, beta=beta)
                self.val_losses.append(val_loss)

                if val_loss < self.best_val_loss:
                    self.best_val_loss = val_loss
                    self._save_checkpoint(epoch, is_best=True)

            if (epoch + 1) % 10 == 0:
                logger.info(
                    f"Epoch {epoch + 1}: Train Loss={train_loss:.4f}, Val Loss={val_loss:.4f if val_loader else 'N/A'}")

    def validate(self, val_loader: DataLoader, beta: float = 1.0) -> float:
        """Validate model"""
        self.model.eval()
        total_loss = 0.0

        with torch.no_grad():
            for batch in val_loader:
                loss, _ = self.vae_loss(batch, beta=beta)
                total_loss += loss.item()

        avg_loss = total_loss / len(val_loader)
        return avg_loss

    def _save_checkpoint(self, epoch: int, is_best: bool = False):
        """Save model checkpoint"""
        checkpoint = {
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'train_losses': self.train_losses,
            'val_losses': self.val_losses,
        }

        path = os.path.join(
            self.config.checkpoint_dir,
            f"vae_checkpoint_epoch_{epoch}.pt"
        )

        torch.save(checkpoint, path)

        if is_best:
            best_path = os.path.join(self.config.checkpoint_dir, "vae_best.pt")
            torch.save(checkpoint, best_path)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def save_model(model: VAEModel, path: str, metadata: Dict = None):
    """Save VAE model with metadata"""
    checkpoint = {
        'model_state_dict': model.state_dict(),
        'config': asdict(model.config),
        'metadata': metadata or {},
        'timestamp': datetime.now().isoformat()
    }

    os.makedirs(os.path.dirname(path), exist_ok=True)
    torch.save(checkpoint, path)
    logger.info(f"Model saved to {path}")


def load_model(path: str) -> VAEModel:
    """Load VAE model from checkpoint"""
    checkpoint = torch.load(path, map_location='cpu')

    config = VAEConfig(**checkpoint['config'])
    model = VAEModel(config)
    model.load_state_dict(checkpoint['model_state_dict'])

    logger.info(f"Model loaded from {path}")
    return model


def create_sample_batch(batch_size: int = 32) -> Tuple[np.ndarray, np.ndarray]:
    """Create sample batch for testing"""
    # Random responses (0-10 scale)
    responses = np.random.rand(batch_size, 30) * 10

    # Random consistency signals (0-1 scale)
    consistency = np.random.rand(batch_size, 6)

    return responses, consistency


# ============================================================================
# MAIN EXECUTION & EXAMPLES
# ============================================================================

def main():
    """
    Main execution function demonstrating VAE model usage
    """

    logger.info("=" * 80)
    logger.info("EFOPA VAE Model - Demonstration")
    logger.info("=" * 80)

    # Initialize configuration
    config = VAEConfig()
    logger.info(f"Configuration: {asdict(config)}")

    # Step 1: Initialize model
    logger.info("\n[Step 1] Initializing VAE Model")
    model = VAEModel(config)
    logger.info(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")

    # Step 2: Create sample data (for demonstration)
    logger.info("\n[Step 2] Creating sample batch")
    responses, consistency = create_sample_batch(batch_size=4)

    # Convert to tensors
    responses_tensor = torch.from_numpy(responses).float().to(config.device)
    consistency_tensor = torch.from_numpy(consistency).float().to(config.device)

    logger.info(f"Input shapes: responses={responses_tensor.shape}, consistency={consistency_tensor.shape}")

    # Step 3: Forward pass
    logger.info("\n[Step 3] Running forward pass")
    with torch.no_grad():
        reconstructed, latents = model(responses_tensor, consistency_tensor)
        logger.info(f"Reconstructed shape: {reconstructed.shape}")
        logger.info(f"Reconstruction error: {F.mse_loss(reconstructed, responses_tensor).item():.4f}")

    # Step 4: Inference engine
    logger.info("\n[Step 4] Initializing inference engine")

    # Create a dummy model file for testing
    os.makedirs('./models', exist_ok=True)
    save_model(model, './models/vae_model_demo.pt')

    engine = VAEInferenceEngine('./models/vae_model_demo.pt', config)

    # Step 5: Run inference
    logger.info("\n[Step 5] Running inference")
    sample_responses = (np.random.rand(30) * 10).astype(np.float32)
    demographics = {'age': 28, 'sex': 'Male', 'country': 'US'}

    output = engine.infer(sample_responses, demographics, session_id='demo_session_001')

    logger.info(f"\nInference Results:")
    logger.info(f"  Personality Type: {output.personality_type}")
    logger.info(f"  Confidence: {output.confidence:.2%}")
    logger.info(f"  Novelty Score: {output.novelty_score:.4f}")
    logger.info(f"  Is Anomalous: {output.is_anomalous}")
    logger.info(f"  Reconstruction Error: {output.reconstruction_error:.6f}")
    logger.info(f"  Domain Scores: {output.domain_scores}")

    # Step 6: Batch inference
    logger.info("\n[Step 6] Running batch inference")
    batch_responses = (np.random.rand(10, 30) * 10).astype(np.float32)

    batch_results = []
    for i, resp in enumerate(batch_responses):
        result = engine.infer(resp, demographics, session_id=f'batch_{i:03d}')
        batch_results.append(result)
        logger.info(f"  Sample {i}: Type={result.personality_type}, Conf={result.confidence:.2%}")

    logger.info("\n" + "=" * 80)
    logger.info("VAE Model demonstration completed successfully!")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
