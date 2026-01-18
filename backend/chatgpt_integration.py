"1. Google Gemini API initialization and authentication"
import logging
import os
import json
import time
import hashlib
import re
from typing import Dict, Tuple, List, Optional, Any, Callable
from pathlib import Path
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum
import threading
from collections import deque
from functools import wraps

import google as genai
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry




# ============================================================================
# CONFIGURATION & CONSTANTS
# ============================================================================

class LLMProvider(Enum):
    """Available LLM providers."""
    GEMINI = "gemini"
    OPENAI = "openai"
    FALLBACK = "fallback"


class NarrativeStyle(Enum):
    """Different narrative styles."""
    PROFESSIONAL = "professional"  # Formal, analytical
    CONVERSATIONAL = "conversational"  # Friendly, engaging
    SCIENTIFIC = "scientific"  # Technical, evidence-based
    COACHING = "coaching"  # Actionable, growth-oriented


class LLMIntegrationConfig:
    """Configuration for LLM integration."""
    
    # API Configuration
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    
    # Primary provider
    PRIMARY_PROVIDER = LLMProvider.GEMINI
    FALLBACK_PROVIDER = LLMProvider.FALLBACK
    
    # Model selection
    GEMINI_MODEL = "gemini-pro"
    OPENAI_MODEL = "gpt-3.5-turbo"
    
    # API endpoints
    GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"
    OPENAI_ENDPOINT = "https://api.openai.com/v1/chat/completions"
    
    # Rate limiting
    REQUESTS_PER_MINUTE = 60  # Gemini free tier
    REQUESTS_PER_DAY = 1440  # Gemini free tier daily limit
    
    # Narrative parameters
    NARRATIVE_MIN_LENGTH = 250  # Minimum words
    NARRATIVE_MAX_LENGTH = 600  # Maximum words
    NARRATIVE_TARGET_LENGTH = 400  # Target words
    
    # Timeout settings
    REQUEST_TIMEOUT = 30  # seconds
    MAX_RETRIES = 3
    RETRY_BACKOFF_FACTOR = 2  # exponential backoff
    
    # Caching
    ENABLE_CACHING = True
    CACHE_TTL_HOURS = 24  # Time-to-live for cached results
    LOCAL_CACHE_MAX_SIZE = 1000  # Local memory cache size
    
    # Fallback narratives (when API unavailable)
    USE_FALLBACK_ON_ERROR = True
    FALLBACK_NARRATIVE_TEMPLATE = True
    
    # Logging
    LOG_LEVEL = logging.INFO
    LOG_FILE = 'logs/llm_integration.log'
    LOG_API_CALLS = True
    
    # Cost tracking
    TRACK_COSTS = True
    COST_PER_1K_INPUT = 0.0005  # Gemini (free tier)
    COST_PER_1K_OUTPUT = 0.0015  # Gemini (free tier)
    COST_CURRENCY = 'USD'


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging(config: LLMIntegrationConfig) -> logging.Logger:
    """Set up logging for LLM integration."""
    logger = logging.getLogger('LLMIntegration')
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


logger = setup_logging(LLMIntegrationConfig())


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class APIUsage:
    """Track API usage for monitoring and cost."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary."""
        return asdict(self)
    
    def total_cost(self, config: LLMIntegrationConfig) -> float:
        """Calculate total cost in USD."""
        input_cost = (self.prompt_tokens / 1000) * config.COST_PER_1K_INPUT
        output_cost = (self.completion_tokens / 1000) * config.COST_PER_1K_OUTPUT
        return input_cost + output_cost


@dataclass
class NarrativeGenerationRequest:
    """Request for narrative generation."""
    assessment_id: str
    personality_type: str  # A-F
    personality_label: str  # Human-readable
    trait_scores: Dict[str, float]  # {R, S, C, A, O, E}
    novelty_score: float
    population_percentile: float
    style: NarrativeStyle = NarrativeStyle.PROFESSIONAL
    language: str = "en"  # ISO 639-1 code
    tone: str = "balanced"  # friendly, formal, analytical, balanced
    max_length: int = 500  # Target word count
    custom_context: Optional[Dict[str, Any]] = None


@dataclass
class NarrativeGenerationResult:
    """Result of narrative generation."""
    assessment_id: str
    narrative: str
    word_count: int
    character_count: int
    provider: str  # gemini, openai, fallback
    model: str
    tokens_used: APIUsage
    estimated_cost: float
    generation_time_ms: float
    timestamp: str
    is_cached: bool = False
    quality_score: float = 0.0  # 0-1 (quality estimate)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['tokens_used'] = self.tokens_used.to_dict()
        return data


@dataclass
class PromptTemplate:
    """Template for narrative prompt generation."""
    system_prompt: str
    user_prompt_template: str
    style: NarrativeStyle
    language: str = "en"
    tone: str = "balanced"
    max_tokens: int = 1500  # Model's max_tokens for request
    temperature: float = 0.7  # Creativity (0-1)
    top_p: float = 0.95  # Diversity (0-1)
    top_k: int = 40  # Top-k sampling


# ============================================================================
# PROMPT TEMPLATES
# ============================================================================

class PromptTemplates:
    """Pre-designed prompts for different narrative styles."""
    
    @staticmethod
    def professional_template(language: str = "en") -> PromptTemplate:
        """Professional, analytical narrative."""
        
        system_prompt = (
            "You are an expert personality psychologist and assessment analyst. "
            "Generate a professional, analytical personality narrative based on assessment results. "
            "The narrative should be insightful, evidence-based, and actionable. "
            "Avoid generic statements. Be specific to the person's profile. "
            "Use academic but accessible language."
        )
        
        user_prompt_template = (
            "Based on the following personality assessment results, generate a detailed narrative:\n\n"
            "Personality Type: {personality_type} - {personality_label}\n\n"
            "Trait Scores (1-5 scale, corrected for deception):\n"
            "- Relationships (R): {R}/5\n"
            "- Status (S): {S}/5\n"
            "- Conscientiousness (C): {C}/5\n"
            "- Agreeableness (A): {A}/5\n"
            "- Openness (O): {O}/5\n"
            "- Emotional Stability (E): {E}/5\n\n"
            "Profile Statistics:\n"
            "- Novelty Score: {novelty_score:.2f} (unusual profile measure)\n"
            "- Population Percentile: {population_percentile:.1f}th percentile\n\n"
            "Please generate a {word_count}-word narrative that:\n"
            "1. Explains the person's personality type and key characteristics\n"
            "2. Identifies their strengths based on the trait profile\n"
            "3. Discusses potential areas for growth or development\n"
            "4. Provides context about how their profile compares to the population\n"
            "5. Offers practical insights about their personality in social and professional contexts\n\n"
            "Keep the tone professional yet engaging."
        )
        
        return PromptTemplate(
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
            style=NarrativeStyle.PROFESSIONAL,
            language=language,
            tone="analytical",
            temperature=0.6,
            top_p=0.9
        )
    
    @staticmethod
    def conversational_template(language: str = "en") -> PromptTemplate:
        """Friendly, engaging narrative."""
        
        system_prompt = (
            "You are a friendly and approachable personality coach. "
            "Generate an engaging, conversational narrative about someone's personality. "
            "Use warm, encouraging language. Make them feel understood and valued. "
            "Include practical tips they can use in their daily life."
        )
        
        user_prompt_template = (
            "Write a friendly narrative about someone with these traits:\n\n"
            "Type: {personality_type} - {personality_label}\n"
            "Scores: R={R}, S={S}, C={C}, A={A}, O={O}, E={E} (out of 5)\n"
            "Uniqueness: {novelty_score:.2f} (where 2.5+ is quite unique)\n"
            "Position: {population_percentile:.0f}th percentile\n\n"
            "Create a {word_count}-word narrative that:\n"
            "1. Celebrates their unique personality traits\n"
            "2. Explains what their scores reveal about how they interact with the world\n"
            "3. Highlights their natural strengths\n"
            "4. Suggests one or two ways they could leverage their personality for success\n"
            "5. Acknowledges their uniqueness compared to others\n\n"
            "Make it warm, personalized, and encouraging."
        )
        
        return PromptTemplate(
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
            style=NarrativeStyle.CONVERSATIONAL,
            language=language,
            tone="friendly",
            temperature=0.75,
            top_p=0.95
        )
    
    @staticmethod
    def scientific_template(language: str = "en") -> PromptTemplate:
        """Technical, evidence-based narrative."""
        
        system_prompt = (
            "You are a personality science researcher. Generate a technically rigorous narrative. "
            "Reference evolutionary psychology, personality theory, and behavioral science. "
            "Be precise with terminology. Include citations to research when relevant. "
            "This is for an audience familiar with personality assessment science."
        )
        
        user_prompt_template = (
            "Analyze the following personality assessment results from a scientific perspective:\n\n"
            "Classification: {personality_type} ({personality_label})\n"
            "Domain Scores (z-score corrected, 1-5 Likert): R={R}, S={S}, C={C}, A={A}, O={O}, E={E}\n"
            "Latent Space Novelty Indicator: {novelty_score:.3f}\n"
            "Population Position: {population_percentile:.1f}th percentile\n\n"
            "Generate a {word_count}-word scientific narrative covering:\n"
            "1. Evolutionary basis for the observed trait configuration\n"
            "2. Evidence from personality psychology research relevant to this profile\n"
            "3. Behavioral predictions based on trait scores\n"
            "4. Discussion of within-trait variation and personality stability\n"
            "5. Implications for mate selection, cooperation, and reproductive strategies\n\n"
            "Include scientific terminology but remain accessible."
        )
        
        return PromptTemplate(
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
            style=NarrativeStyle.SCIENTIFIC,
            language=language,
            tone="analytical",
            temperature=0.5,
            top_p=0.85
        )
    
    @staticmethod
    def coaching_template(language: str = "en") -> PromptTemplate:
        """Actionable, growth-oriented narrative."""
        
        system_prompt = (
            "You are an experienced executive coach and personality development specialist. "
            "Generate an action-oriented narrative focused on personal growth. "
            "Identify specific ways this person can leverage their personality for success. "
            "Provide concrete, implementable suggestions."
        )
        
        user_prompt_template = (
            "Create a coaching narrative for someone with this personality profile:\n\n"
            "Type: {personality_type} - {personality_label}\n"
            "Traits: Relationships={R}, Status={S}, Conscientiousness={C}, Agreeableness={A}, Openness={O}, Emotional Stability={E}\n"
            "Uniqueness Index: {novelty_score:.2f}\n"
            "Comparative Position: {population_percentile:.0f}th percentile\n\n"
            "Write a {word_count}-word coaching narrative that:\n"
            "1. Identifies their personality strengths\n"
            "2. Points out one potential blind spot or development area\n"
            "3. Suggests 2-3 specific actions they can take to maximize their personality strengths\n"
            "4. Discusses how to adapt their approach in different contexts (work, relationships, leadership)\n"
            "5. Empowers them with a growth mindset\n\n"
            "Be specific and actionable."
        )
        
        return PromptTemplate(
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
            style=NarrativeStyle.COACHING,
            language=language,
            tone="motivational",
            temperature=0.7,
            top_p=0.92
        )
    
    @staticmethod
    def get_template(
        style: NarrativeStyle = NarrativeStyle.PROFESSIONAL,
        language: str = "en"
    ) -> PromptTemplate:
        """Get template for specified style."""
        templates = {
            NarrativeStyle.PROFESSIONAL: PromptTemplates.professional_template,
            NarrativeStyle.CONVERSATIONAL: PromptTemplates.conversational_template,
            NarrativeStyle.SCIENTIFIC: PromptTemplates.scientific_template,
            NarrativeStyle.COACHING: PromptTemplates.coaching_template
        }
        
        template_fn = templates.get(style, PromptTemplates.professional_template)
        return template_fn(language)


# ============================================================================
# FALLBACK NARRATIVES
# ============================================================================

class FallbackNarratives:
    """Pre-written fallback narratives for each personality type."""
    
    TEMPLATES = {
        'A': (
            "Type A: Ambitious Explorer\n\n"
            "You are driven by achievement and new experiences. Your high status orientation "
            "combined with openness to new ideas makes you a natural innovator and leader. "
            "People with your profile tend to excel in entrepreneurial ventures, strategic roles, "
            "and positions requiring visionary thinking.\n\n"
            "Your strength lies in your ability to balance ambition with intellectual curiosity. "
            "You're not content with the status quo—you're always looking for the next opportunity "
            "or idea to explore. This makes you valuable in fast-moving, dynamic environments.\n\n"
            "One area to watch: ensure that your drive for achievement doesn't overshadow "
            "relationships or personal well-being. The most successful people with your profile "
            "learn to channel their ambition in ways that benefit both themselves and those around them.\n\n"
            "In social contexts, you're likely seen as engaging and ambitious. In professional settings, "
            "leverage your vision and openness to drive innovation. In relationships, balance your "
            "achievement focus with genuine emotional connection."
        ),
        'B': (
            "Type B: Devoted Protector\n\n"
            "You are characterized by reliability, conscientiousness, and genuine care for others. "
            "High agreeableness combined with conscientiousness makes you the kind of person people "
            "trust implicitly. You excel in roles requiring responsibility, team collaboration, "
            "and long-term commitment.\n\n"
            "Your strength is your dependability. When you commit to something or someone, you follow through. "
            "This makes you invaluable as a team member, friend, and partner. People naturally gravitate "
            "toward you in times of need because they know you'll be there.\n\n"
            "Consider: don't neglect your own needs while taking care of others. Your tendency to prioritize "
            "others can lead to burnout if not managed. Also, practice assertiveness—your agreeableness is "
            "a strength, but ensure you can voice your own needs clearly.\n\n"
            "In social contexts, you're the reliable friend. Professionally, you excel in mentoring, management, "
            "and collaborative roles. In relationships, your loyalty and conscientiousness make you a stable, "
            "trustworthy partner."
        ),
        'C': (
            "Type C: Balanced Harmonizer\n\n"
            "You are well-balanced across personality dimensions, which gives you flexibility and adaptability. "
            "Rather than being extreme in any direction, you have moderate levels across relationships, status, "
            "conscientiousness, agreeableness, openness, and emotional stability.\n\n"
            "Your greatest strength is versatility. You can adjust your approach depending on the situation. "
            "You're not the flashiest person in the room, but you're often the most reliable and adaptable. "
            "This makes you valuable in teams and organizations seeking stable, balanced contributors.\n\n"
            "Consider developing deeper expertise in areas you're passionate about. Your balanced nature is an asset, "
            "but specialization in one or two areas can help you stand out and advance in your career.\n\n"
            "Socially, you're well-liked because you're not extreme. Professionally, you're seen as dependable and flexible. "
            "In relationships, your balance suggests you're comfortable with both intimacy and independence."
        ),
        'D': (
            "Type D: Cautious Analyzer\n\n"
            "You are thoughtful, introverted, and intellectually curious. High openness combined with lower extraversion "
            "suggests you prefer depth over breadth in relationships and intellectual pursuits. You likely excel in roles "
            "requiring deep analysis, research, or specialized expertise.\n\n"
            "Your strength is your ability to focus deeply and think critically. You're not driven by social status or "
            "constant stimulation. Instead, you find satisfaction in understanding complex systems and ideas. This makes you "
            "valuable in technical, research, and analytical roles.\n\n"
            "One growth area: stretch yourself socially when beneficial. Your introversion is not a limitation, but practicing "
            "communication and networking can open doors. You have valuable insights—sharing them more broadly can amplify your impact.\n\n"
            "Socially, you're selective with relationships but form deep connections. Professionally, you excel in specialized roles "
            "requiring expertise. In relationships, you value deep understanding and intellectual connection."
        ),
        'E': (
            "Type E: Authentic Connector\n\n"
            "You are genuine, principled, and focused on real connection with others. Lower deception tendency combined with "
            "high agreeableness means you value authenticity and cooperation. People likely see you as trustworthy and real.\n\n"
            "Your strength is authenticity. In a world of personas and self-presentation, you stand out as genuinely yourself. "
            "This builds deep trust with others. You're the kind of person people confide in because they sense your genuine care "
            "and lack of judgment.\n\n"
            "Consider: ensure your authenticity doesn't become stubborness. Being true to yourself is important, but flexibility "
            "and adapting to context is also a valuable skill. Learn when to be fully authentic and when to adjust your approach.\n\n"
            "Socially, people find you easy to trust. Professionally, you excel in roles requiring integrity and relationship-building. "
            "In relationships, your authenticity creates a foundation of real connection and mutual understanding."
        ),
        'F': (
            "Type F: Independent Maverick\n\n"
            "You are independent, confident, and not primarily motivated by harmony with others. High status orientation combined "
            "with lower agreeableness suggests you're willing to go your own way and take unconventional paths.\n\n"
            "Your strength is your confidence and independence. You're not easily swayed by group opinion or social pressure. This "
            "allows you to pursue unique goals and perspectives. You're often ahead of the curve, willing to challenge the status quo.\n\n"
            "One consideration: balance independence with collaboration. While your willingness to challenge others is valuable, practicing "
            "empathy and considering others' perspectives can make you more effective. The best leaders with your profile learn to harness "
            "their independence while bringing others along.\n\n"
            "Socially, you're seen as confident and somewhat unconventional. Professionally, you drive change and innovation. In relationships, "
            "you need a partner who respects your independence and doesn't try to change your fundamental nature."
        )
    }
    
    @staticmethod
    def get_narrative(personality_type: str, word_count: int = 400) -> str:
        """Get fallback narrative for personality type."""
        template = FallbackNarratives.TEMPLATES.get(personality_type, FallbackNarratives.TEMPLATES['C'])
        
        # Adjust narrative length if needed
        if word_count < 300:
            # Use shorter version (first 2 paragraphs)
            paragraphs = template.split('\n\n')
            return '\n\n'.join(paragraphs[:2])
        elif word_count > 500:
            # Use full version
            return template
        else:
            # Use full version (fits in range)
            return template


# ============================================================================
# RATE LIMITING & REQUEST QUEUING
# ============================================================================

class RateLimiter:
    """Rate limiter for API requests."""
    
    def __init__(self, requests_per_minute: int = 60):
        """Initialize rate limiter.
        
        Args:
            requests_per_minute: Max requests per minute
        """
        self.requests_per_minute = requests_per_minute
        self.request_times = deque()
        self.lock = threading.Lock()
    
    def wait_if_needed(self):
        """Wait if rate limit would be exceeded."""
        with self.lock:
            now = time.time()
            
            # Remove old requests (older than 1 minute)
            while self.request_times and self.request_times[0] < now - 60:
                self.request_times.popleft()
            
            # If at limit, wait
            if len(self.request_times) >= self.requests_per_minute:
                sleep_time = 60 - (now - self.request_times[0])
                if sleep_time > 0:
                    logger.info(f'Rate limit reached. Waiting {sleep_time:.1f}s')
                    time.sleep(sleep_time)
            
            # Record this request
            self.request_times.append(time.time())
    
    def get_requests_this_minute(self) -> int:
        """Get current request count."""
        with self.lock:
            now = time.time()
            while self.request_times and self.request_times[0] < now - 60:
                self.request_times.popleft()
            return len(self.request_times)


class RetryStrategy:
    """Retry logic with exponential backoff."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        backoff_factor: float = 2.0,
        max_delay: float = 60.0
    ):
        """Initialize retry strategy.
        
        Args:
            max_retries: Maximum number of retries
            base_delay: Initial delay in seconds
            backoff_factor: Exponential backoff multiplier
            max_delay: Maximum delay between retries
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator for retry logic.
        
        Args:
            func: Function to wrap with retry logic
            
        Returns:
            Wrapped function with retry logic
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(self.max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt < self.max_retries - 1:
                        # Calculate delay
                        delay = min(
                            self.base_delay * (self.backoff_factor ** attempt),
                            self.max_delay
                        )
                        logger.warning(
                            f'Attempt {attempt + 1} failed: {e}. '
                            f'Retrying in {delay:.1f}s...'
                        )
                        time.sleep(delay)
                    else:
                        logger.error(f'All {self.max_retries} attempts failed: {e}')
            
            raise last_exception
        
        return wrapper


# ============================================================================
# CACHING LAYER
# ============================================================================

class LocalCache:
    """Simple in-memory cache for narratives."""
    
    def __init__(self, max_size: int = 1000):
        """Initialize local cache.
        
        Args:
            max_size: Maximum cache size
        """
        self.cache = {}
        self.timestamps = {}
        self.max_size = max_size
        self.lock = threading.Lock()
    
    def _make_key(self, assessment_id: str, style: str) -> str:
        """Create cache key."""
        return f"{assessment_id}:{style}"
    
    def get(self, assessment_id: str, style: str, ttl_hours: int = 24) -> Optional[str]:
        """Get narrative from cache.
        
        Args:
            assessment_id: Assessment ID
            style: Narrative style
            ttl_hours: Time-to-live in hours
            
        Returns:
            Cached narrative or None
        """
        with self.lock:
            key = self._make_key(assessment_id, style)
            
            if key not in self.cache:
                return None
            
            # Check TTL
            timestamp = self.timestamps[key]
            age_hours = (time.time() - timestamp) / 3600
            
            if age_hours > ttl_hours:
                del self.cache[key]
                del self.timestamps[key]
                return None
            
            return self.cache[key]
    
    def set(self, assessment_id: str, style: str, narrative: str) -> None:
        """Store narrative in cache.
        
        Args:
            assessment_id: Assessment ID
            style: Narrative style
            narrative: Narrative text
        """
        with self.lock:
            key = self._make_key(assessment_id, style)
            
            # Evict oldest if at capacity
            if len(self.cache) >= self.max_size:
                oldest_key = min(self.timestamps, key=self.timestamps.get)
                del self.cache[oldest_key]
                del self.timestamps[oldest_key]
            
            self.cache[key] = narrative
            self.timestamps[key] = time.time()
    
    def clear(self) -> None:
        """Clear all cached narratives."""
        with self.lock:
            self.cache.clear()
            self.timestamps.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'utilization': len(self.cache) / self.max_size
            }


# ============================================================================
# GEMINI API CLIENT
# ============================================================================

class GeminiClient:
    """Client for Google Gemini API."""
    
    def __init__(self, api_key: str, config: LLMIntegrationConfig):
        """Initialize Gemini client.
        
        Args:
            api_key: Gemini API key
            config: Configuration instance
            
        Raises:
            ValueError: If API key not provided
        """
        if not api_key:
            raise ValueError('GEMINI_API_KEY not set. Set via environment variable.')
        
        self.api_key = api_key
        self.config = config
        self.rate_limiter = RateLimiter(config.REQUESTS_PER_MINUTE)
        
        # Initialize Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(config.GEMINI_MODEL)
        
        logger.info(f'Gemini client initialized with model {config.GEMINI_MODEL}')
    
    @property
    def is_available(self) -> bool:
        """Check if API is available."""
        try:
            # Try a simple request
            response = self.model.generate_content(
                "Hello",
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=10
                )
            )
            return response.text is not None
        except Exception as e:
            logger.warning(f'Gemini API check failed: {e}')
            return False
    
    def generate_narrative(
        self,
        prompt_template: PromptTemplate,
        request: NarrativeGenerationRequest,
        retry_strategy: Optional[RetryStrategy] = None
    ) -> NarrativeGenerationResult:
        """Generate narrative using Gemini.
        
        Args:
            prompt_template: Prompt template to use
            request: Generation request
            retry_strategy: Optional retry strategy
            
        Returns:
            NarrativeGenerationResult
            
        Raises:
            Exception: If generation fails
        """
        start_time = time.perf_counter()
        
        # Rate limit
        self.rate_limiter.wait_if_needed()
        
        # Format prompt
        system_prompt = prompt_template.system_prompt
        
        user_prompt = prompt_template.user_prompt_template.format(
            personality_type=request.personality_type,
            personality_label=request.personality_label,
            R=f"{request.trait_scores['R']:.1f}",
            S=f"{request.trait_scores['S']:.1f}",
            C=f"{request.trait_scores['C']:.1f}",
            A=f"{request.trait_scores['A']:.1f}",
            O=f"{request.trait_scores['O']:.1f}",
            E=f"{request.trait_scores['E']:.1f}",
            novelty_score=request.novelty_score,
            population_percentile=request.population_percentile,
            word_count=request.max_length
        )
        
        try:
            # Generate with Gemini
            response = self.model.generate_content(
                [system_prompt, user_prompt],
                generation_config=genai.types.GenerationConfig(
                    temperature=prompt_template.temperature,
                    top_p=prompt_template.top_p,
                    top_k=prompt_template.top_k,
                    max_output_tokens=prompt_template.max_tokens,
                    candidate_count=1
                ),
                safety_settings=[
                    {
                        "category": genai.types.HarmCategory.HARM_CATEGORY_UNSPECIFIED,
                        "threshold": genai.types.HarmBlockThreshold.BLOCK_NONE
                    }
                ]
            )
            
            narrative = response.text.strip()
            
            # Validate and clean
            narrative = self._validate_narrative(narrative, request.max_length)
            
            # Calculate tokens (Gemini doesn't provide exact counts)
            estimated_prompt_tokens = len(user_prompt.split()) + len(system_prompt.split())
            estimated_completion_tokens = len(narrative.split())
            
            usage = APIUsage(
                prompt_tokens=estimated_prompt_tokens,
                completion_tokens=estimated_completion_tokens,
                total_tokens=estimated_prompt_tokens + estimated_completion_tokens
            )
            
            # Calculate cost
            estimated_cost = usage.total_cost(self.config)
            
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            
            logger.info(
                f'Generated narrative for {request.assessment_id}: '
                f'{len(narrative)} chars, {estimated_completion_tokens} tokens, '
                f'${estimated_cost:.4f}'
            )
            
            return NarrativeGenerationResult(
                assessment_id=request.assessment_id,
                narrative=narrative,
                word_count=estimated_completion_tokens,
                character_count=len(narrative),
                provider='gemini',
                model=self.config.GEMINI_MODEL,
                tokens_used=usage,
                estimated_cost=estimated_cost,
                generation_time_ms=elapsed_ms,
                timestamp=datetime.utcnow().isoformat(),
                is_cached=False,
                quality_score=self._estimate_quality(narrative, request)
            )
        
        except Exception as e:
            logger.error(f'Gemini generation failed: {e}')
            raise
    
    def _validate_narrative(self, narrative: str, target_length: int) -> str:
        """Validate and clean generated narrative.
        
        Args:
            narrative: Generated narrative
            target_length: Target word count
            
        Returns:
            Cleaned narrative
        """
        # Remove extra whitespace
        narrative = ' '.join(narrative.split())
        
        # Check length
        word_count = len(narrative.split())
        
        if word_count < self.config.NARRATIVE_MIN_LENGTH:
            logger.warning(
                f'Narrative too short: {word_count} < {self.config.NARRATIVE_MIN_LENGTH}'
            )
        
        if word_count > self.config.NARRATIVE_MAX_LENGTH:
            logger.warning(
                f'Narrative too long: {word_count} > {self.config.NARRATIVE_MAX_LENGTH}. Trimming.'
            )
            # Simple truncation at last complete sentence
            words = narrative.split()
            trimmed = []
            word_count = 0
            for word in words:
                if word_count >= self.config.NARRATIVE_MAX_LENGTH:
                    break
                trimmed.append(word)
                word_count += 1
            
            narrative = ' '.join(trimmed)
            # Ensure ends with period
            if not narrative.endswith('.'):
                narrative = narrative.rsplit(' ', 1)[0] + '.'
        
        return narrative
    
    def _estimate_quality(
        self,
        narrative: str,
        request: NarrativeGenerationRequest
    ) -> float:
        """Estimate narrative quality (0-1).
        
        Args:
            narrative: Generated narrative
            request: Original request
            
        Returns:
            Quality score (0-1)
        """
        score = 1.0
        word_count = len(narrative.split())
        
        # Length penalty
        if word_count < self.config.NARRATIVE_MIN_LENGTH:
            score -= 0.2
        elif word_count > self.config.NARRATIVE_MAX_LENGTH:
            score -= 0.15
        
        # Check for key elements
        if request.personality_type.lower() in narrative.lower():
            score += 0.05
        
        # Check readability (Flesch-Kincaid approximation)
        sentences = narrative.count('.') + narrative.count('!') + narrative.count('?')
        if sentences > 0:
            avg_sentence_length = word_count / sentences
            if 10 < avg_sentence_length < 25:  # Optimal range
                score += 0.05
        
        return min(score, 1.0)


# ============================================================================
# MAIN LLM INTEGRATION CLASS
# ============================================================================

class LLMIntegration:
    """
    Main class for LLM integration.
    
    Handles:
    - Provider selection and fallback
    - Narrative generation
    - Caching
    - Rate limiting
    - Cost tracking
    - Error handling
    """
    
    def __init__(self, config: LLMIntegrationConfig = None):
        """Initialize LLM integration.
        
        Args:
            config: Configuration instance
        """
        self.config = config or LLMIntegrationConfig()
        
        # Initialize cache
        self.cache = LocalCache(self.config.LOCAL_CACHE_MAX_SIZE)
        
        # Initialize Gemini client
        try:
            self.gemini_client = GeminiClient(
                self.config.GEMINI_API_KEY,
                self.config
            )
        except Exception as e:
            logger.error(f'Failed to initialize Gemini client: {e}')
            self.gemini_client = None
        
        # Retry strategy
        self.retry_strategy = RetryStrategy(
            max_retries=self.config.MAX_RETRIES,
            backoff_factor=self.config.RETRY_BACKOFF_FACTOR
        )
        
        # Statistics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_tokens_used = APIUsage()
        self.total_cost = 0.0
        self.stats_lock = threading.Lock()
        
        logger.info('LLM integration initialized')
    
    def generate_narrative(
        self,
        request: NarrativeGenerationRequest,
        force_generation: bool = False
    ) -> NarrativeGenerationResult:
        """Generate narrative with fallback support.
        
        Args:
            request: Generation request
            force_generation: Skip cache and force generation
            
        Returns:
            NarrativeGenerationResult
        """
        start_time = time.perf_counter()
        
        # Check cache first
        if not force_generation and self.config.ENABLE_CACHING:
            cached = self.cache.get(
                request.assessment_id,
                request.style.value,
                self.config.CACHE_TTL_HOURS
            )
            
            if cached:
                logger.info(f'Using cached narrative for {request.assessment_id}')
                return NarrativeGenerationResult(
                    assessment_id=request.assessment_id,
                    narrative=cached,
                    word_count=len(cached.split()),
                    character_count=len(cached),
                    provider='cache',
                    model='local_cache',
                    tokens_used=APIUsage(),
                    estimated_cost=0.0,
                    generation_time_ms=(time.perf_counter() - start_time) * 1000,
                    timestamp=datetime.utcnow().isoformat(),
                    is_cached=True,
                    quality_score=1.0
                )
        
        with self.stats_lock:
            self.total_requests += 1
        
        try:
            # Get prompt template
            template = PromptTemplates.get_template(request.style, request.language)
            
            # Try Gemini first
            if self.gemini_client and self.gemini_client.is_available:
                try:
                    result = self.gemini_client.generate_narrative(
                        template, request, self.retry_strategy
                    )
                    
                    # Cache result
                    if self.config.ENABLE_CACHING:
                        self.cache.set(
                            request.assessment_id,
                            request.style.value,
                            result.narrative
                        )
                    
                    self._update_statistics(result)
                    
                    with self.stats_lock:
                        self.successful_requests += 1
                    
                    return result
                
                except Exception as e:
                    logger.warning(f'Gemini generation failed: {e}')
                    if not self.config.USE_FALLBACK_ON_ERROR:
                        raise
            
            # Fallback
            logger.info(f'Using fallback narrative for {request.assessment_id}')
            
            fallback_narrative = FallbackNarratives.get_narrative(
                request.personality_type,
                request.max_length
            )
            
            # Cache fallback
            if self.config.ENABLE_CACHING:
                self.cache.set(
                    request.assessment_id,
                    request.style.value,
                    fallback_narrative
                )
            
            result = NarrativeGenerationResult(
                assessment_id=request.assessment_id,
                narrative=fallback_narrative,
                word_count=len(fallback_narrative.split()),
                character_count=len(fallback_narrative),
                provider='fallback',
                model='template',
                tokens_used=APIUsage(),
                estimated_cost=0.0,
                generation_time_ms=(time.perf_counter() - start_time) * 1000,
                timestamp=datetime.utcnow().isoformat(),
                is_cached=False,
                quality_score=0.7
            )
            
            with self.stats_lock:
                self.successful_requests += 1
            
            return result
        
        except Exception as e:
            logger.error(f'Narrative generation failed: {e}')
            
            with self.stats_lock:
                self.failed_requests += 1
            
            raise
    
    def batch_generate_narratives(
        self,
        requests: List[NarrativeGenerationRequest],
        parallel: bool = False,
        max_workers: int = 5
    ) -> List[NarrativeGenerationResult]:
        """Generate narratives for multiple requests.
        
        Args:
            requests: List of generation requests
            parallel: Whether to use parallel processing
            max_workers: Number of parallel workers
            
        Returns:
            List of NarrativeGenerationResult
        """
        results = []
        
        if not parallel:
            # Sequential processing
            for request in requests:
                try:
                    result = self.generate_narrative(request)
                    results.append(result)
                except Exception as e:
                    logger.error(f'Failed to generate narrative for {request.assessment_id}: {e}')
                    continue
        
        else:
            # Parallel processing
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self.generate_narrative, req): req
                    for req in requests
                }
                
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        request = futures[future]
                        logger.error(f'Failed to generate narrative for {request.assessment_id}: {e}')
        
        return results
    
    def _update_statistics(self, result: NarrativeGenerationResult) -> None:
        """Update usage statistics.
        
        Args:
            result: Generation result
        """
        with self.stats_lock:
            self.total_tokens_used.prompt_tokens += result.tokens_used.prompt_tokens
            self.total_tokens_used.completion_tokens += result.tokens_used.completion_tokens
            self.total_tokens_used.total_tokens += result.tokens_used.total_tokens
            self.total_cost += result.estimated_cost
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get usage statistics.
        
        Returns:
            Statistics dictionary
        """
        with self.stats_lock:
            success_rate = (
                self.successful_requests / self.total_requests
                if self.total_requests > 0 else 0
            )
            
            return {
                'total_requests': self.total_requests,
                'successful_requests': self.successful_requests,
                'failed_requests': self.failed_requests,
                'success_rate': success_rate,
                'tokens_used': self.total_tokens_used.to_dict(),
                'total_cost_usd': self.total_cost,
                'cache_stats': self.cache.get_stats(),
                'gemini_available': self.gemini_client.is_available if self.gemini_client else False
            }
    
    def clear_cache(self) -> None:
        """Clear all cached narratives."""
        self.cache.clear()
        logger.info('Cache cleared')


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def create_narrative_request(
    assessment_id: str,
    personality_type: str,
    personality_label: str,
    trait_scores: Dict[str, float],
    novelty_score: float,
    percentile: float,
    style: NarrativeStyle = NarrativeStyle.PROFESSIONAL
) -> NarrativeGenerationRequest:
    """Create narrative generation request.
    
    Args:
        assessment_id: Assessment ID
        personality_type: Personality type (A-F)
        personality_label: Human-readable label
        trait_scores: Domain scores {R, S, C, A, O, E}
        novelty_score: Novelty score
        percentile: Population percentile
        style: Narrative style
        
    Returns:
        NarrativeGenerationRequest
    """
    return NarrativeGenerationRequest(
        assessment_id=assessment_id,
        personality_type=personality_type,
        personality_label=personality_label,
        trait_scores=trait_scores,
        novelty_score=novelty_score,
        population_percentile=percentile,
        style=style
    )


# ============================================================================
# MAIN EXECUTION / TESTING
# ============================================================================

def main():
    """Test LLM integration with sample data."""
    
    # Initialize
    config = LLMIntegrationConfig()
    integration = LLMIntegration(config)
    
    # Create sample request
    request = create_narrative_request(
        assessment_id='TEST_001',
        personality_type='A',
        personality_label='Ambitious Explorer',
        trait_scores={'R': 3.2, 'S': 3.8, 'C': 3.5, 'A': 3.6, 'O': 4.1, 'E': 3.4},
        novelty_score=1.34,
        percentile=72.5,
        style=NarrativeStyle.PROFESSIONAL
    )
    
    print("Generating narrative...")
    print("="*70)
    
    result = integration.generate_narrative(request)
    
    print(f"\nAssessment ID: {result.assessment_id}")
    print(f"Provider: {result.provider}")
    print(f"Model: {result.model}")
    print(f"Tokens Used: {result.tokens_used.total_tokens}")
    print(f"Estimated Cost: ${result.estimated_cost:.4f}")
    print(f"Generation Time: {result.generation_time_ms:.1f} ms")
    print(f"Cached: {result.is_cached}")
    print(f"Quality Score: {result.quality_score:.2f}")
    print(f"Word Count: {result.word_count}")
    
    print("\n" + "="*70)
    print("NARRATIVE")
    print("="*70)
    print(result.narrative)
    
    # Get statistics
    print("\n" + "="*70)
    print("STATISTICS")
    print("="*70)
    stats = integration.get_statistics()
    for key, value in stats.items():
        if key != 'tokens_used':
            print(f"{key}: {value}")


if __name__ == '__main__':
    main()
