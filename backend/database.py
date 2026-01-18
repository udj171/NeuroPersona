"Purpose:Complete database abstraction layer for personality assessment platform.Handles all CRUD operations, connection pooling, transaction management,data validation, error handling, and compliance with GDPR requirements."

import os
import json
import logging
import time
import threading
from typing import Dict, List, Tuple, Optional, Any, Union
from contextlib import contextmanager
from datetime import datetime, timedelta
from uuid import uuid4, UUID
import hashlib
import hmac
from functools import wraps
from dataclasses import dataclass, asdict
from enum import Enum

# Database drivers
import psycopg2
import psycopg2.pool
import psycopg2.extras
from psycopg2 import sql

# Data processing
import numpy as np
from scipy.spatial.distance import mahalanobis
import redis

# Configuration
from dotenv import load_dotenv

load_dotenv()



# ============================================================================
# CONFIGURATION AND LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/database.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': int(os.environ.get('DB_PORT', 5432)),
    'database': os.environ.get('DB_NAME', 'efopa_db'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD', ''),
}

POOL_CONFIG = {
    'minconn': 5,
    'maxconn': 50,
    'timeout': 30,
    'idle_in_transaction_session_timeout': 60000,  # 60 seconds
    'statement_timeout': 30000,  # 30 seconds per query
}

CACHE_CONFIG = {
    'enabled': os.environ.get('CACHE_ENABLED', 'true').lower() == 'true',
    'ttl': int(os.environ.get('CACHE_TTL', 3600)),  # 1 hour default
    'redis_url': os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
}

# ============================================================================
# DATA MODELS AND ENUMS
# ============================================================================

class AssessmentStatus(Enum):
    """Assessment lifecycle states."""
    STARTED = 'started'
    IN_PROGRESS = 'in_progress'
    SUBMITTED = 'submitted'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'


class UserStatus(Enum):
    """User account states."""
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    DELETED = 'deleted'
    SUSPENDED = 'suspended'


@dataclass
class User:
    """User profile model."""
    user_id: str
    email: str
    country: str
    age: int
    sex: str  # M, F, NB, Prefer not to say
    created_at: str
    updated_at: str
    assessment_count: int = 0
    status: str = 'active'
    consent_given: bool = True


@dataclass
class Assessment:
    """Assessment session model."""
    assessment_id: str
    user_id: str
    session_id: str
    status: str
    responses_count: int
    progress_percentage: int
    created_at: str
    completed_at: Optional[str] = None
    time_seconds: Optional[int] = None
    validity_score: Optional[float] = None
    error_message: Optional[str] = None


@dataclass
class Response:
    """Individual questionnaire response."""
    response_id: str
    assessment_id: str
    item_id: int
    domain: str
    score: int
    response_time_ms: int
    timestamp: str


@dataclass
class ScoringResult:
    """Scoring pipeline results."""
    scoring_id: str
    assessment_id: str
    validity_score: float
    response_entropy: float
    raw_scores: Dict[str, float]
    corrected_scores: Dict[str, float]
    confidence_intervals: Dict[str, Dict[str, float]]
    percentiles: Dict[str, int]
    deception_lambda: float
    deception_delta: Dict[str, float]
    created_at: str


@dataclass
class MLResult:
    """ML pipeline outputs."""
    ml_id: str
    assessment_id: str
    latent_representation: Tuple[float, float, float]
    anomaly_score: float
    is_anomalous: bool
    reconstruction_error: float
    primary_type: str
    primary_confidence: float
    secondary_type: Optional[str] = None
    secondary_confidence: Optional[float] = None
    type_blend: Optional[Dict[str, float]] = None
    descriptors: Optional[List[str]] = None
    created_at: Optional[str] = None


@dataclass
class Narrative:
    """AI-generated narrative."""
    narrative_id: str
    assessment_id: str
    narrative_text: str
    word_count: int
    generation_time_ms: float
    provider: str  # gemini, openai, claude, fallback
    quality_score: float
    is_cached: bool
    created_at: str


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class DatabaseError(Exception):
    """Base database exception."""
    pass


class ConnectionPoolError(DatabaseError):
    """Connection pool or connectivity issue."""
    pass


class QueryExecutionError(DatabaseError):
    """SQL execution error."""
    pass


class ValidationError(DatabaseError):
    """Data validation failed."""
    pass


class NotFoundError(DatabaseError):
    """Record not found."""
    pass


class DuplicateError(DatabaseError):
    """Unique constraint violation."""
    pass


class TransactionError(DatabaseError):
    """Transaction commit/rollback failed."""
    pass


class GDPRError(DatabaseError):
    """Privacy-related operation failed."""
    pass


# ============================================================================
# CONNECTION MANAGEMENT
# ============================================================================

class ConnectionPool:
    """
    Thread-safe connection pool wrapper around psycopg2.
    
    Handles:
    - Connection lifecycle (acquire, release, validate)
    - Automatic reconnection on failure
    - Connection timeouts
    - Resource cleanup
    """
    
    def __init__(self, dsn: str, **pool_kwargs):
        """
        Initialize connection pool.
        
        Args:
            dsn: PostgreSQL connection string
            **pool_kwargs: Pool configuration (minconn, maxconn, timeout, etc.)
        """
        self.dsn = dsn
        self.pool = None
        self._lock = threading.Lock()
        self._pool_kwargs = pool_kwargs
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize the connection pool."""
        try:
            self.pool = psycopg2.pool.SimpleConnectionPool(
                self._pool_kwargs.get('minconn', 5),
                self._pool_kwargs.get('maxconn', 50),
                self.dsn,
                cursor_factory=psycopg2.extras.RealDictCursor,
                options="-c statement_timeout=30000"
            )
            logger.info("Connection pool initialized successfully")
        except psycopg2.Error as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            raise ConnectionPoolError(f"Connection pool initialization failed: {e}")
    
    def get_connection(self):
        """
        Get connection from pool.
        
        Returns:
            psycopg2 connection object
            
        Raises:
            ConnectionPoolError: If connection cannot be acquired
        """
        if self.pool is None:
            raise ConnectionPoolError("Connection pool not initialized")
        
        try:
            return self.pool.getconn()
        except psycopg2.pool.PoolError as e:
            logger.error(f"Connection pool exhausted: {e}")
            raise ConnectionPoolError(f"Connection pool exhausted: {e}")
    
    def put_connection(self, conn):
        """
        Return connection to pool.
        
        Args:
            conn: Connection to return
        """
        if self.pool is not None and conn is not None:
            try:
                self.pool.putconn(conn)
            except Exception as e:
                logger.warning(f"Error returning connection to pool: {e}")
    
    def close_all(self):
        """Close all connections in pool."""
        if self.pool:
            try:
                self.pool.closeall()
                logger.info("Connection pool closed")
            except Exception as e:
                logger.error(f"Error closing connection pool: {e}")
    
    def validate_connection(self, conn) -> bool:
        """
        Validate connection is still alive.
        
        Args:
            conn: Connection to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            return True
        except Exception:
            return False


# ============================================================================
# CACHING LAYER
# ============================================================================

class CacheManager:
    """
    Dual-layer caching system (in-memory + Redis).
    
    Provides:
    - In-memory cache with TTL
    - Optional Redis backend for distributed caching
    - Automatic cache invalidation
    - Cache statistics
    """
    
    def __init__(self, enabled: bool = True, ttl: int = 3600, redis_url: str = None):
        """
        Initialize cache manager.
        
        Args:
            enabled: Enable caching
            ttl: Cache TTL in seconds
            redis_url: Redis connection URL (optional)
        """
        self.enabled = enabled
        self.ttl = ttl
        self.local_cache = {}
        self.cache_timestamps = {}
        self.redis_client = None
        self.stats = {'hits': 0, 'misses': 0, 'sets': 0}
        self._lock = threading.Lock()
        
        if enabled and redis_url:
            try:
                self.redis_client = redis.from_url(redis_url)
                self.redis_client.ping()
                logger.info("Redis cache initialized")
            except Exception as e:
                logger.warning(f"Redis connection failed, using local cache only: {e}")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        if not self.enabled:
            return None
        
        # Check in-memory cache first
        with self._lock:
            if key in self.local_cache:
                timestamp = self.cache_timestamps.get(key)
                if timestamp and datetime.now() - timestamp < timedelta(seconds=self.ttl):
                    self.stats['hits'] += 1
                    return self.local_cache[key]
                else:
                    # Expired
                    del self.local_cache[key]
                    del self.cache_timestamps[key]
        
        # Check Redis
        if self.redis_client:
            try:
                value = self.redis_client.get(key)
                if value:
                    self.stats['hits'] += 1
                    return json.loads(value)
            except Exception as e:
                logger.warning(f"Redis get error: {e}")
        
        self.stats['misses'] += 1
        return None
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """
        Set cache value.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional custom TTL
            
        Returns:
            True if successful
        """
        if not self.enabled:
            return False
        
        ttl = ttl or self.ttl
        
        try:
            with self._lock:
                self.local_cache[key] = value
                self.cache_timestamps[key] = datetime.now()
            self.stats['sets'] += 1
            
            # Set in Redis if available
            if self.redis_client:
                try:
                    self.redis_client.setex(
                        key,
                        ttl,
                        json.dumps(value)
                    )
                except Exception as e:
                    logger.warning(f"Redis set error: {e}")
            
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete cache entry."""
        try:
            with self._lock:
                self.local_cache.pop(key, None)
                self.cache_timestamps.pop(key, None)
            
            if self.redis_client:
                self.redis_client.delete(key)
            
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    def clear(self):
        """Clear all cache."""
        try:
            with self._lock:
                self.local_cache.clear()
                self.cache_timestamps.clear()
            
            if self.redis_client:
                self.redis_client.flushdb()
            
            logger.info("Cache cleared")
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        total = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total * 100) if total > 0 else 0
        return {
            **self.stats,
            'total': total,
            'hit_rate_percent': round(hit_rate, 2)
        }


# ============================================================================
# MAIN DATABASE MANAGER
# ============================================================================

class DatabaseManager:
    """
    Central database management class.
    
    Handles:
    - Connection pooling and lifecycle
    - Transaction management
    - Retry logic and error handling
    - Query execution and monitoring
    - Batch operations
    - Caching
    """
    
    def __init__(
        self,
        database_url: str = None,
        pool_size: int = 10,
        max_connections: int = 50,
        timeout: int = 30,
        retry_attempts: int = 3,
        enable_cache: bool = True,
        cache_ttl: int = 3600
    ):
        """
        Initialize database manager.
        
        Args:
            database_url: PostgreSQL connection string
            pool_size: Initial pool size
            max_connections: Maximum pool size
            timeout: Connection timeout (seconds)
            retry_attempts: Max retries for transient failures
            enable_cache: Enable caching layer
            cache_ttl: Cache TTL (seconds)
        """
        self.database_url = database_url or self._build_dsn()
        self.retry_attempts = retry_attempts
        self.slow_query_threshold = 100  # ms
        self.query_stats = {
            'total_queries': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'total_time_ms': 0,
            'slow_queries': 0,
        }
        self._query_lock = threading.Lock()
        
        # Initialize connection pool
        self.conn_pool = ConnectionPool(
            self.database_url,
            minconn=pool_size,
            maxconn=max_connections,
            timeout=timeout
        )
        
        # Initialize cache
        self.cache = CacheManager(
            enabled=enable_cache,
            ttl=cache_ttl,
            redis_url=CACHE_CONFIG.get('redis_url')
        )
        
        logger.info(f"DatabaseManager initialized for {DB_CONFIG['database']}")
    
    @staticmethod
    def _build_dsn() -> str:
        """Build PostgreSQL connection string."""
        return (
            f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@"
            f"{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
        )
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for getting database connection.
        
        Yields:
            psycopg2 connection object
            
        Handles:
        - Connection acquisition from pool
        - Automatic commit/rollback
        - Connection return to pool
        """
        conn = None
        try:
            conn = self.conn_pool.get_connection()
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Connection error: {e}")
            raise
        finally:
            if conn:
                self.conn_pool.put_connection(conn)
    
    def execute_query(
        self,
        query: str,
        params: tuple = None,
        fetch: str = 'one',
        retry: bool = True,
        cache_key: str = None,
        cache_ttl: int = None
    ) -> Any:
        """
        Execute SQL query with retry logic and caching.
        
        Args:
            query: SQL query string
            params: Query parameters (for prepared statements)
            fetch: 'one', 'all', or None (for INSERT/UPDATE/DELETE)
            retry: Enable automatic retry on failure
            cache_key: Optional cache key for GET queries
            cache_ttl: Optional cache TTL override
            
        Returns:
            Query result (row, rows, or None)
            
        Raises:
            QueryExecutionError: If query fails after retries
        """
        # Check cache first
        if cache_key and fetch == 'one':
            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit for key: {cache_key}")
                return cached
        
        start_time = time.time()
        last_error = None
        
        for attempt in range(self.retry_attempts if retry else 1):
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    
                    # Get results based on fetch type
                    if fetch == 'one':
                        result = cursor.fetchone()
                    elif fetch == 'all':
                        result = cursor.fetchall()
                    else:
                        result = None
                    
                    cursor.close()
                    
                    # Cache result if applicable
                    if cache_key and result and fetch == 'one':
                        self.cache.set(cache_key, result, cache_ttl)
                    
                    # Track query statistics
                    self._track_query_success(time.time() - start_time)
                    
                    return result
            
            except psycopg2.errors.InsufficientPrivilege as e:
                logger.error(f"Permission denied: {e}")
                raise QueryExecutionError(f"Permission denied: {e}")
            
            except psycopg2.errors.UniqueViolation as e:
                logger.error(f"Unique constraint violation: {e}")
                raise DuplicateError(f"Duplicate record: {e}")
            
            except psycopg2.IntegrityError as e:
                logger.error(f"Integrity error: {e}")
                raise ValidationError(f"Data integrity error: {e}")
            
            except (psycopg2.OperationalError, psycopg2.DatabaseError) as e:
                last_error = e
                if attempt < self.retry_attempts - 1:
                    wait_time = (2 ** attempt)
                    logger.warning(
                        f"Query failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}"
                    )
                    time.sleep(wait_time)
                else:
                    self._track_query_failure(time.time() - start_time)
                    logger.error(f"Query failed after {self.retry_attempts} attempts: {e}")
            
            except Exception as e:
                self._track_query_failure(time.time() - start_time)
                logger.error(f"Unexpected query error: {e}")
                raise QueryExecutionError(f"Query execution failed: {e}")
        
        raise QueryExecutionError(f"Query failed after retries: {last_error}")
    
    def execute_batch(
        self,
        query: str,
        params_list: List[tuple],
        batch_size: int = 1000
    ) -> Tuple[int, int, List[str]]:
        """
        Execute multiple INSERT/UPDATE/DELETE operations efficiently.
        
        Args:
            query: SQL query string (with %s placeholders)
            params_list: List of parameter tuples
            batch_size: Number of rows per batch
            
        Returns:
            (success_count, error_count, error_details)
        """
        success_count = 0
        error_count = 0
        error_details = []
        
        logger.info(f"Starting batch operation with {len(params_list)} rows")
        
        # Process in batches
        for i in range(0, len(params_list), batch_size):
            batch = params_list[i:i + batch_size]
            
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.executemany(query, batch)
                    batch_success = cursor.rowcount
                    success_count += batch_success
                    logger.debug(f"Batch {i // batch_size + 1}: {batch_success} rows inserted")
                    cursor.close()
            
            except Exception as e:
                error_count += len(batch)
                error_msg = f"Batch {i // batch_size + 1} failed: {str(e)}"
                error_details.append(error_msg)
                logger.error(error_msg)
        
        logger.info(
            f"Batch operation complete: {success_count} successful, "
            f"{error_count} failed"
        )
        
        return success_count, error_count, error_details
    
    def get_transaction(self):
        """
        Create explicit transaction context.
        
        Yields:
            Transaction object with commit/rollback methods
        """
        return self.get_connection()
    
    def _track_query_success(self, execution_time_ms: float):
        """Track successful query statistics."""
        with self._query_lock:
            self.query_stats['total_queries'] += 1
            self.query_stats['successful_queries'] += 1
            self.query_stats['total_time_ms'] += execution_time_ms
            
            if execution_time_ms > self.slow_query_threshold:
                self.query_stats['slow_queries'] += 1
                logger.warning(f"Slow query detected: {execution_time_ms:.0f}ms")
    
    def _track_query_failure(self, execution_time_ms: float):
        """Track failed query statistics."""
        with self._query_lock:
            self.query_stats['total_queries'] += 1
            self.query_stats['failed_queries'] += 1
            self.query_stats['total_time_ms'] += execution_time_ms
    
    def get_query_stats(self) -> Dict[str, Any]:
        """Get query execution statistics."""
        with self._query_lock:
            stats = self.query_stats.copy()
        
        total = stats['total_queries']
        avg_time = (stats['total_time_ms'] / total) if total > 0 else 0
        success_rate = (stats['successful_queries'] / total * 100) if total > 0 else 0
        
        return {
            **stats,
            'average_time_ms': round(avg_time, 2),
            'success_rate_percent': round(success_rate, 2),
            'cache_stats': self.cache.get_stats()
        }
    
    def close(self):
        """Close database connections."""
        self.conn_pool.close_all()
        logger.info("Database manager closed")


# ============================================================================
# USER OPERATIONS
# ============================================================================

class UserOperations:
    """All user-related database operations."""
    
    @staticmethod
    def create_user(
        db: DatabaseManager,
        email: str,
        country: str,
        age: int,
        sex: str,
        consent: bool
    ) -> str:
        """
        Create new user record.
        
        Args:
            email: User email
            country: ISO 3166-1 country code
            age: Age (18-120)
            sex: M, F, NB, or 'Prefer not to say'
            consent: GDPR consent checkbox
            
        Returns:
            user_id (UUID string)
            
        Raises:
            DuplicateError: Email already exists
            ValidationError: Invalid input
        """
        # Validation
        if age < 18 or age > 120:
            raise ValidationError(f"Invalid age: {age}")
        if sex not in ['M', 'F', 'NB', 'Prefer not to say']:
            raise ValidationError(f"Invalid sex: {sex}")
        if not email or '@' not in email:
            raise ValidationError(f"Invalid email: {email}")
        
        user_id = str(uuid4())
        now = datetime.now().isoformat()
        
        query = """
            INSERT INTO users (user_id, email, country, age, sex, created_at, 
                             updated_at, consent_given, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING user_id
        """
        
        try:
            result = db.execute_query(
                query,
                (user_id, email, country, age, sex, now, now, consent, UserStatus.ACTIVE.value),
                fetch='one'
            )
            logger.info(f"Created user: {user_id}")
            return result['user_id'] if result else user_id
        except DuplicateError:
            raise DuplicateError(f"User with email {email} already exists")
    
    @staticmethod
    def get_user(db: DatabaseManager, user_id: str) -> Optional[Dict]:
        """
        Retrieve user profile.
        
        Args:
            user_id: User ID
            
        Returns:
            User dictionary with all fields or None
            
        Raises:
            NotFoundError: User not found
        """
        query = """
            SELECT * FROM users WHERE user_id = %s
        """
        
        result = db.execute_query(
            query,
            (user_id,),
            fetch='one',
            cache_key=f"user:{user_id}"
        )
        
        if not result:
            raise NotFoundError(f"User not found: {user_id}")
        
        return dict(result)
    
    @staticmethod
    def update_user(
        db: DatabaseManager,
        user_id: str,
        **fields
    ) -> Dict:
        """
        Update user fields.
        
        Args:
            user_id: User ID
            **fields: Field names and values to update
            
        Returns:
            Updated user dictionary
        """
        allowed_fields = {'country', 'age', 'status', 'consent_given'}
        fields = {k: v for k, v in fields.items() if k in allowed_fields}
        
        if not fields:
            return UserOperations.get_user(db, user_id)
        
        fields['updated_at'] = datetime.now().isoformat()
        
        set_clause = ', '.join(f"{k} = %s" for k in fields.keys())
        query = f"""
            UPDATE users 
            SET {set_clause}
            WHERE user_id = %s
            RETURNING *
        """
        
        params = tuple(fields.values()) + (user_id,)
        result = db.execute_query(query, params, fetch='one')
        
        # Invalidate cache
        db.cache.delete(f"user:{user_id}")
        
        logger.info(f"Updated user: {user_id}")
        return dict(result)
    
    @staticmethod
    def delete_user(
        db: DatabaseManager,
        user_id: str,
        reason: str = 'User requested deletion'
    ) -> bool:
        """
        Delete user (GDPR right to be forgotten).
        
        Args:
            user_id: User ID
            reason: Reason for deletion
            
        Returns:
            True if successful
        """
        try:
            with db.get_transaction() as conn:
                cursor = conn.cursor()
                
                # Anonymize user data
                now = datetime.now().isoformat()
                cursor.execute("""
                    UPDATE users 
                    SET email = %s, status = %s, updated_at = %s, country = NULL
                    WHERE user_id = %s
                """, (f"deleted_{user_id[:8]}@deleted.local", UserStatus.DELETED.value, now, user_id))
                
                # Delete assessments and responses
                cursor.execute("""
                    DELETE FROM responses 
                    WHERE assessment_id IN (
                        SELECT assessment_id FROM assessments WHERE user_id = %s
                    )
                """, (user_id,))
                
                cursor.execute("""
                    DELETE FROM assessments WHERE user_id = %s
                """, (user_id,))
                
                # Log deletion
                cursor.execute("""
                    INSERT INTO audit_log (table_name, operation, record_id, user_id, 
                                         old_values, reason, timestamp)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, ('users', 'DELETE', user_id, user_id, None, reason, now))
                
                cursor.close()
                conn.commit()
            
            # Clear cache
            db.cache.delete(f"user:{user_id}")
            logger.info(f"Deleted user: {user_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            raise GDPRError(f"Failed to delete user: {e}")
    
    @staticmethod
    def get_user_history(
        db: DatabaseManager,
        user_id: str,
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict]:
        """
        Get user's assessment history.
        
        Args:
            user_id: User ID
            limit: Max results
            offset: Pagination offset
            
        Returns:
            List of assessment summaries
        """
        query = """
            SELECT a.assessment_id, a.created_at, a.completed_at, 
                   a.time_seconds, s.corrected_scores, m.primary_type
            FROM assessments a
            LEFT JOIN scoring_results s ON a.assessment_id = s.assessment_id
            LEFT JOIN ml_results m ON a.assessment_id = m.assessment_id
            WHERE a.user_id = %s
            ORDER BY a.created_at DESC
            LIMIT %s OFFSET %s
        """
        
        results = db.execute_query(
            query,
            (user_id, limit, offset),
            fetch='all',
            cache_key=f"user_history:{user_id}:{limit}:{offset}",
            cache_ttl=300  # 5 minutes
        )
        
        return [dict(r) for r in results] if results else []


# ============================================================================
# ASSESSMENT OPERATIONS
# ============================================================================

class AssessmentOperations:
    """Assessment session management."""
    
    @staticmethod
    def start_assessment(
        db: DatabaseManager,
        user_id: str,
        session_id: str,
        ip_address: str,
        user_agent: str
    ) -> str:
        """
        Create new assessment session.
        
        Args:
            user_id: User ID
            session_id: Session UUID
            ip_address: User IP address
            user_agent: Browser user agent
            
        Returns:
            assessment_id
        """
        assessment_id = str(uuid4())
        now = datetime.now().isoformat()
        
        query = """
            INSERT INTO assessments 
            (assessment_id, user_id, session_id, status, responses_count, 
             progress_percentage, created_at, ip_address, user_agent)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING assessment_id
        """
        
        result = db.execute_query(
            query,
            (assessment_id, user_id, session_id, AssessmentStatus.STARTED.value, 
             0, 0, now, ip_address, user_agent),
            fetch='one'
        )
        
        logger.info(f"Started assessment: {assessment_id}")
        return result['assessment_id'] if result else assessment_id
    
    @staticmethod
    def update_progress(
        db: DatabaseManager,
        assessment_id: str,
        responses_count: int
    ) -> bool:
        """
        Update progress during assessment.
        
        Args:
            assessment_id: Assessment ID
            responses_count: Number of responses so far
            
        Returns:
            True if successful
        """
        progress = min(int(responses_count / 35 * 100), 100)
        
        query = """
            UPDATE assessments 
            SET responses_count = %s, progress_percentage = %s, 
                status = %s
            WHERE assessment_id = %s
        """
        
        db.execute_query(
            query,
            (responses_count, progress, AssessmentStatus.IN_PROGRESS.value, assessment_id),
            fetch=None
        )
        
        return True
    
    @staticmethod
    def complete_assessment(
        db: DatabaseManager,
        assessment_id: str,
        time_seconds: int
    ) -> bool:
        """
        Mark assessment as completed.
        
        Args:
            assessment_id: Assessment ID
            time_seconds: Total completion time
            
        Returns:
            True if successful
        """
        now = datetime.now().isoformat()
        
        query = """
            UPDATE assessments 
            SET status = %s, completed_at = %s, time_seconds = %s
            WHERE assessment_id = %s
        """
        
        db.execute_query(
            query,
            (AssessmentStatus.COMPLETED.value, now, time_seconds, assessment_id),
            fetch=None
        )
        
        # Clear cache
        db.cache.delete(f"assessment:{assessment_id}")
        
        logger.info(f"Completed assessment: {assessment_id}")
        return True
    
    @staticmethod
    def fail_assessment(
        db: DatabaseManager,
        assessment_id: str,
        error_message: str,
        traceback: str = None
    ) -> bool:
        """
        Mark assessment as failed with error details.
        
        Args:
            assessment_id: Assessment ID
            error_message: Error description
            traceback: Full stack trace (optional)
            
        Returns:
            True if successful
        """
        now = datetime.now().isoformat()
        
        query = """
            UPDATE assessments 
            SET status = %s, error_message = %s, error_traceback = %s, 
                completed_at = %s
            WHERE assessment_id = %s
        """
        
        db.execute_query(
            query,
            (AssessmentStatus.FAILED.value, error_message, traceback, now, assessment_id),
            fetch=None
        )
        
        logger.error(f"Failed assessment {assessment_id}: {error_message}")
        return True
    
    @staticmethod
    def get_assessment(db: DatabaseManager, assessment_id: str) -> Optional[Dict]:
        """Retrieve assessment details."""
        query = """
            SELECT * FROM assessments WHERE assessment_id = %s
        """
        
        result = db.execute_query(
            query,
            (assessment_id,),
            fetch='one',
            cache_key=f"assessment:{assessment_id}"
        )
        
        return dict(result) if result else None


# ============================================================================
# RESPONSE OPERATIONS
# ============================================================================

class ResponseOperations:
    """Questionnaire response handling."""
    
    @staticmethod
    def store_responses(
        db: DatabaseManager,
        assessment_id: str,
        responses: Dict[int, int]
    ) -> Tuple[int, int]:
        """
        Store all 35 questionnaire responses efficiently.
        
        Args:
            assessment_id: Assessment ID
            responses: Dict mapping item_id to score (0-10)
            
        Returns:
            (stored_count, error_count)
        """
        # Validate responses
        if len(responses) != 35:
            logger.warning(f"Expected 35 responses, got {len(responses)}")
        
        params_list = []
        now = datetime.now().isoformat()
        
        for item_id, score in responses.items():
            if not isinstance(score, int) or score < 0 or score > 10:
                logger.warning(f"Invalid score for item {item_id}: {score}")
                continue
            
            # Determine domain
            if 1 <= item_id <= 5:
                domain = 'R'
            elif 6 <= item_id <= 10:
                domain = 'S'
            elif 11 <= item_id <= 15:
                domain = 'C'
            elif 16 <= item_id <= 20:
                domain = 'A'
            elif 21 <= item_id <= 25:
                domain = 'O'
            elif 26 <= item_id <= 30:
                domain = 'E'
            elif 31 <= item_id <= 35:
                domain = 'V'  # Validity
            else:
                continue
            
            response_id = str(uuid4())
            params_list.append((
                response_id, assessment_id, item_id, domain, score, 0, now
            ))
        
        query = """
            INSERT INTO responses 
            (response_id, assessment_id, item_id, domain, score, response_time_ms, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        success, errors, _ = db.execute_batch(query, params_list, batch_size=100)
        logger.info(f"Stored {success} responses for assessment {assessment_id}")
        
        return success, errors
    
    @staticmethod
    def get_assessment_responses(
        db: DatabaseManager,
        assessment_id: str
    ) -> Dict[int, int]:
        """
        Retrieve all responses for assessment.
        
        Returns:
            Dict mapping item_id to score
        """
        query = """
            SELECT item_id, score FROM responses 
            WHERE assessment_id = %s
            ORDER BY item_id
        """
        
        results = db.execute_query(
            query,
            (assessment_id,),
            fetch='all',
            cache_key=f"responses:{assessment_id}"
        )
        
        return {r['item_id']: r['score'] for r in results} if results else {}
    
    @staticmethod
    def get_domain_responses(
        db: DatabaseManager,
        assessment_id: str,
        domain: str
    ) -> Dict[int, int]:
        """
        Get responses for specific domain.
        
        Args:
            domain: R, S, C, A, O, E, or V
            
        Returns:
            Dict of item_id -> score for domain
        """
        query = """
            SELECT item_id, score FROM responses 
            WHERE assessment_id = %s AND domain = %s
            ORDER BY item_id
        """
        
        results = db.execute_query(
            query,
            (assessment_id, domain),
            fetch='all'
        )
        
        return {r['item_id']: r['score'] for r in results} if results else {}


# ============================================================================
# SCORING RESULTS OPERATIONS
# ============================================================================

class ScoringOperations:
    """Scoring pipeline result storage."""
    
    @staticmethod
    def store_scoring_results(
        db: DatabaseManager,
        assessment_id: str,
        scoring_dict: Dict
    ) -> str:
        """
        Store complete scoring results.
        
        Args:
            assessment_id: Assessment ID
            scoring_dict: Output from scoring.py containing:
                - raw_scores (dict)
                - corrected_scores (dict)
                - validity_score (float)
                - deception_lambda (float)
                - deception_delta (dict)
                - confidence_intervals (dict)
                - percentiles (dict)
                - processing_time_ms (int)
                
        Returns:
            scoring_id
        """
        scoring_id = str(uuid4())
        now = datetime.now().isoformat()
        
        query = """
            INSERT INTO scoring_results 
            (scoring_id, assessment_id, raw_scores, corrected_scores, 
             validity_score, deception_lambda, deception_delta, 
             confidence_intervals, percentiles, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING scoring_id
        """
        
        result = db.execute_query(
            query,
            (
                scoring_id,
                assessment_id,
                json.dumps(scoring_dict.get('raw_scores', {})),
                json.dumps(scoring_dict.get('corrected_scores', {})),
                scoring_dict.get('validity_score', 0.5),
                scoring_dict.get('deception_lambda', 0.5),
                json.dumps(scoring_dict.get('deception_delta', {})),
                json.dumps(scoring_dict.get('confidence_intervals', {})),
                json.dumps(scoring_dict.get('percentiles', {})),
                now
            ),
            fetch='one'
        )
        
        logger.info(f"Stored scoring results: {scoring_id}")
        return result['scoring_id'] if result else scoring_id
    
    @staticmethod
    def get_scoring_results(
        db: DatabaseManager,
        assessment_id: str
    ) -> Optional[Dict]:
        """
        Retrieve complete scoring results.
        
        Returns:
            Complete scoring dictionary
        """
        query = """
            SELECT * FROM scoring_results WHERE assessment_id = %s
        """
        
        result = db.execute_query(
            query,
            (assessment_id,),
            fetch='one',
            cache_key=f"scoring:{assessment_id}"
        )
        
        if not result:
            return None
        
        result_dict = dict(result)
        
        # Parse JSON fields
        result_dict['raw_scores'] = json.loads(result_dict.get('raw_scores', '{}'))
        result_dict['corrected_scores'] = json.loads(result_dict.get('corrected_scores', '{}'))
        result_dict['confidence_intervals'] = json.loads(result_dict.get('confidence_intervals', '{}'))
        result_dict['percentiles'] = json.loads(result_dict.get('percentiles', '{}'))
        result_dict['deception_delta'] = json.loads(result_dict.get('deception_delta', '{}'))
        
        return result_dict


# ============================================================================
# ML RESULTS OPERATIONS
# ============================================================================

class MLOperations:
    """VAE inference and classification storage."""
    
    @staticmethod
    def store_ml_results(
        db: DatabaseManager,
        assessment_id: str,
        ml_output: Dict
    ) -> str:
        """
        Store ML pipeline results.
        
        Args:
            assessment_id: Assessment ID
            ml_output: Output from ml_pipeline.py containing:
                - latent_representation (3D vector)
                - anomaly_score (float)
                - is_anomalous (bool)
                - primary_type (str)
                - primary_confidence (float)
                - secondary_type (str, optional)
                - secondary_confidence (float, optional)
                - type_blend (dict)
                - descriptors (list)
                - reconstruction_error (float)
                - processing_time_ms (int)
                
        Returns:
            ml_id
        """
        ml_id = str(uuid4())
        now = datetime.now().isoformat()
        
        latent = ml_output.get('latent_representation', (0, 0, 0))
        
        query = """
            INSERT INTO ml_results 
            (ml_id, assessment_id, latent_x, latent_y, latent_z, 
             anomaly_score, is_anomalous, reconstruction_error,
             primary_type, primary_confidence, secondary_type, 
             secondary_confidence, type_blend, descriptors, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING ml_id
        """
        
        result = db.execute_query(
            query,
            (
                ml_id,
                assessment_id,
                latent[0] if len(latent) > 0 else 0,
                latent[1] if len(latent) > 1 else 0,
                latent[2] if len(latent) > 2 else 0,
                ml_output.get('anomaly_score', 0),
                ml_output.get('is_anomalous', False),
                ml_output.get('reconstruction_error', 0),
                ml_output.get('primary_type', 'Unknown'),
                ml_output.get('primary_confidence', 0),
                ml_output.get('secondary_type'),
                ml_output.get('secondary_confidence'),
                json.dumps(ml_output.get('type_blend', {})),
                json.dumps(ml_output.get('descriptors', [])),
                now
            ),
            fetch='one'
        )
        
        logger.info(f"Stored ML results: {ml_id}")
        return result['ml_id'] if result else ml_id
    
    @staticmethod
    def get_ml_results(
        db: DatabaseManager,
        assessment_id: str
    ) -> Optional[Dict]:
        """Retrieve ML pipeline results."""
        query = """
            SELECT * FROM ml_results WHERE assessment_id = %s
        """
        
        result = db.execute_query(
            query,
            (assessment_id,),
            fetch='one',
            cache_key=f"ml:{assessment_id}"
        )
        
        if not result:
            return None
        
        result_dict = dict(result)
        result_dict['latent_representation'] = (
            result_dict.get('latent_x', 0),
            result_dict.get('latent_y', 0),
            result_dict.get('latent_z', 0)
        )
        result_dict['type_blend'] = json.loads(result_dict.get('type_blend', '{}'))
        result_dict['descriptors'] = json.loads(result_dict.get('descriptors', '[]'))
        
        return result_dict


# ============================================================================
# NARRATIVE OPERATIONS
# ============================================================================

class NarrativeOperations:
    """AI narrative storage and caching."""
    
    @staticmethod
    def store_narrative(
        db: DatabaseManager,
        assessment_id: str,
        narrative_dict: Dict
    ) -> str:
        """
        Store generated narrative.
        
        Args:
            assessment_id: Assessment ID
            narrative_dict: Output from chatgpt_integration.py
            
        Returns:
            narrative_id
        """
        narrative_id = str(uuid4())
        now = datetime.now().isoformat()
        
        query = """
            INSERT INTO narratives 
            (narrative_id, assessment_id, narrative_text, word_count,
             generation_time_ms, provider, quality_score, is_cached, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING narrative_id
        """
        
        result = db.execute_query(
            query,
            (
                narrative_id,
                assessment_id,
                narrative_dict.get('narrative_text', ''),
                narrative_dict.get('word_count', 0),
                narrative_dict.get('generation_time_ms', 0),
                narrative_dict.get('provider', 'unknown'),
                narrative_dict.get('quality_score', 0.5),
                narrative_dict.get('is_cached', False),
                now
            ),
            fetch='one'
        )
        
        logger.info(f"Stored narrative: {narrative_id}")
        return result['narrative_id'] if result else narrative_id
    
    @staticmethod
    def get_narrative(
        db: DatabaseManager,
        assessment_id: str,
        use_cache: bool = True
    ) -> Optional[Dict]:
        """Retrieve narrative with optional caching."""
        query = """
            SELECT * FROM narratives WHERE assessment_id = %s
        """
        
        result = db.execute_query(
            query,
            (assessment_id,),
            fetch='one',
            cache_key=f"narrative:{assessment_id}" if use_cache else None
        )
        
        return dict(result) if result else None


# ============================================================================
# ANALYTICS OPERATIONS
# ============================================================================

class AnalyticsOperations:
    """Event tracking and analytics."""
    
    @staticmethod
    def track_event(
        db: DatabaseManager,
        event_type: str,
        event_name: str,
        user_id: str = None,
        assessment_id: str = None,
        properties: Dict = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> bool:
        """
        Record analytics event.
        
        Args:
            event_type: Type of event
            event_name: Human-readable name
            user_id: Optional user ID
            assessment_id: Optional assessment ID
            properties: Custom event properties
            ip_address: User IP
            user_agent: User agent string
            
        Returns:
            True if successful
        """
        event_id = str(uuid4())
        now = datetime.now().isoformat()
        
        query = """
            INSERT INTO analytics_events 
            (event_id, event_type, event_name, user_id, assessment_id, 
             properties, ip_address, user_agent, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        try:
            db.execute_query(
                query,
                (
                    event_id, event_type, event_name, user_id, assessment_id,
                    json.dumps(properties or {}), ip_address, user_agent, now
                ),
                fetch=None
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to track event: {e}")
            return False
    
    @staticmethod
    def get_conversion_metrics(
        db: DatabaseManager,
        period: str = 'week'
    ) -> Dict:
        """Calculate conversion funnel metrics."""
        if period == 'week':
            days = 7
        elif period == 'month':
            days = 30
        else:  # day
            days = 1
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Get metrics
        query = """
            SELECT 
                COUNT(DISTINCT CASE WHEN event_type = 'page_view' THEN event_id END) as page_views,
                COUNT(DISTINCT CASE WHEN event_type = 'assessment_started' THEN assessment_id END) as started,
                COUNT(DISTINCT CASE WHEN event_type = 'assessment_completed' THEN assessment_id END) as completed
            FROM analytics_events
            WHERE timestamp >= %s
        """
        
        result = db.execute_query(query, (cutoff_date,), fetch='one')
        
        if not result:
            return {}
        
        result_dict = dict(result)
        page_views = result_dict.get('page_views', 0) or 0
        started = result_dict.get('started', 0) or 0
        completed = result_dict.get('completed', 0) or 0
        
        return {
            'page_views': page_views,
            'assessments_started': started,
            'assessments_completed': completed,
            'completion_rate': (completed / started * 100) if started > 0 else 0,
            'conversion_rate': (completed / page_views * 100) if page_views > 0 else 0,
        }


# ============================================================================
# HEALTH CHECK AND UTILITIES
# ============================================================================

class HealthCheck:
    """Database health check utilities."""
    
    @staticmethod
    def check_connection(db: DatabaseManager) -> Dict:
        """Check database connection."""
        try:
            result = db.execute_query("SELECT 1", fetch='one')
            return {
                'status': 'healthy',
                'connected': result is not None,
                'message': 'Database connection successful'
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'unhealthy',
                'connected': False,
                'message': str(e)
            }
    
    @staticmethod
    def get_database_stats(db: DatabaseManager) -> Dict:
        """Get database statistics."""
        stats = {
            'query_stats': db.get_query_stats(),
            'cache_stats': db.cache.get_stats(),
        }
        
        # Table row counts
        try:
            for table in ['users', 'assessments', 'responses', 'scoring_results', 
                         'ml_results', 'narratives', 'analytics_events']:
                result = db.execute_query(f"SELECT COUNT(*) as count FROM {table}", fetch='one')
                stats[f'{table}_count'] = dict(result).get('count', 0) if result else 0
        except Exception as e:
            logger.warning(f"Could not fetch table counts: {e}")
        
        return stats


# ============================================================================
# CLEANUP AND MAINTENANCE
# ============================================================================

class MaintenanceOperations:
    """Database maintenance and cleanup."""
    
    @staticmethod
    def cleanup_old_sessions(
        db: DatabaseManager,
        days: int = 30
    ) -> int:
        """
        Delete sessions older than N days.
        
        Args:
            days: Delete sessions older than this many days
            
        Returns:
            Number of rows deleted
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        query = """
            DELETE FROM assessments 
            WHERE created_at < %s AND status IN (%s, %s)
            RETURNING assessment_id
        """
        
        results = db.execute_query(
            query,
            (cutoff_date, AssessmentStatus.FAILED.value, AssessmentStatus.COMPLETED.value),
            fetch='all'
        )
        
        deleted_count = len(results) if results else 0
        logger.info(f"Deleted {deleted_count} old sessions (older than {days} days)")
        
        return deleted_count
    
    @staticmethod
    def vacuum_database(db: DatabaseManager) -> bool:
        """
        Vacuum database to reclaim space.
        
        Returns:
            True if successful
        """
        try:
            with db.get_connection() as conn:
                # Vacuum must be in autocommit mode
                conn.autocommit = True
                cursor = conn.cursor()
                cursor.execute("VACUUM ANALYZE")
                cursor.close()
            
            logger.info("Database vacuumed successfully")
            return True
        except Exception as e:
            logger.error(f"Vacuum failed: {e}")
            return False


# ============================================================================
# SCHEMA INITIALIZATION
# ============================================================================

SCHEMA_SQL = """
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    country VARCHAR(2),
    age INTEGER,
    sex VARCHAR(20),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    assessment_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active',
    consent_given BOOLEAN DEFAULT true,
    INDEX idx_user_email (email),
    INDEX idx_user_status (status)
);

-- Assessments table
CREATE TABLE IF NOT EXISTS assessments (
    assessment_id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    session_id UUID UNIQUE NOT NULL,
    status VARCHAR(20) NOT NULL,
    responses_count INTEGER DEFAULT 0,
    progress_percentage INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    time_seconds INTEGER,
    validity_score FLOAT,
    error_message TEXT,
    error_traceback TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    INDEX idx_assessment_user (user_id),
    INDEX idx_assessment_status (status),
    INDEX idx_assessment_created (created_at DESC)
);

-- Responses table
CREATE TABLE IF NOT EXISTS responses (
    response_id UUID PRIMARY KEY,
    assessment_id UUID NOT NULL,
    item_id INTEGER NOT NULL,
    domain VARCHAR(1),
    score INTEGER,
    response_time_ms INTEGER,
    timestamp TIMESTAMP NOT NULL,
    FOREIGN KEY (assessment_id) REFERENCES assessments(assessment_id),
    UNIQUE (assessment_id, item_id),
    INDEX idx_response_assessment (assessment_id),
    INDEX idx_response_domain (domain)
);

-- Scoring results table
CREATE TABLE IF NOT EXISTS scoring_results (
    scoring_id UUID PRIMARY KEY,
    assessment_id UUID UNIQUE NOT NULL,
    raw_scores JSONB,
    corrected_scores JSONB,
    validity_score FLOAT,
    deception_lambda FLOAT,
    deception_delta JSONB,
    confidence_intervals JSONB,
    percentiles JSONB,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (assessment_id) REFERENCES assessments(assessment_id),
    INDEX idx_scoring_assessment (assessment_id)
);

-- ML results table
CREATE TABLE IF NOT EXISTS ml_results (
    ml_id UUID PRIMARY KEY,
    assessment_id UUID UNIQUE NOT NULL,
    latent_x FLOAT,
    latent_y FLOAT,
    latent_z FLOAT,
    anomaly_score FLOAT,
    is_anomalous BOOLEAN,
    reconstruction_error FLOAT,
    primary_type VARCHAR(50),
    primary_confidence FLOAT,
    secondary_type VARCHAR(50),
    secondary_confidence FLOAT,
    type_blend JSONB,
    descriptors JSONB,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (assessment_id) REFERENCES assessments(assessment_id),
    INDEX idx_ml_assessment (assessment_id),
    INDEX idx_ml_type (primary_type)
);

-- Narratives table
CREATE TABLE IF NOT EXISTS narratives (
    narrative_id UUID PRIMARY KEY,
    assessment_id UUID UNIQUE NOT NULL,
    narrative_text TEXT,
    word_count INTEGER,
    generation_time_ms FLOAT,
    provider VARCHAR(50),
    quality_score FLOAT,
    is_cached BOOLEAN,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (assessment_id) REFERENCES assessments(assessment_id),
    INDEX idx_narrative_assessment (assessment_id)
);

-- Analytics events table
CREATE TABLE IF NOT EXISTS analytics_events (
    event_id UUID PRIMARY KEY,
    event_type VARCHAR(50),
    event_name VARCHAR(100),
    user_id UUID,
    assessment_id UUID,
    properties JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    timestamp TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (assessment_id) REFERENCES assessments(assessment_id),
    INDEX idx_event_type (event_type),
    INDEX idx_event_timestamp (timestamp DESC)
);

-- Audit log table
CREATE TABLE IF NOT EXISTS audit_log (
    audit_id UUID PRIMARY KEY,
    table_name VARCHAR(50),
    operation VARCHAR(10),
    record_id VARCHAR(255),
    user_id UUID,
    old_values JSONB,
    new_values JSONB,
    reason TEXT,
    timestamp TIMESTAMP NOT NULL,
    INDEX idx_audit_table (table_name),
    INDEX idx_audit_record (record_id),
    INDEX idx_audit_timestamp (timestamp DESC)
);
"""


def initialize_database(db: DatabaseManager, schema_sql: str = SCHEMA_SQL):
    """
    Initialize PostgreSQL database with full schema.
    
    Args:
        db: DatabaseManager instance
        schema_sql: SQL schema definition
    """
    try:
        statements = schema_sql.split(';')
        for statement in statements:
            if statement.strip():
                db.execute_query(statement, fetch=None)
        logger.info("Database schema initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database schema: {e}")
        raise


# ============================================================================
# MODULE INITIALIZATION
# ============================================================================

def create_database_manager(
    database_url: str = None,
    **kwargs
) -> DatabaseManager:
    """
    Create and initialize a DatabaseManager instance.
    
    Args:
        database_url: Optional PostgreSQL connection string
        **kwargs: Additional arguments for DatabaseManager
        
    Returns:
        Initialized DatabaseManager instance
    """
    db = DatabaseManager(database_url=database_url, **kwargs)
    return db


if __name__ == '__main__':
    # Example usage
    db = create_database_manager()
    
    # Check health
    health = HealthCheck.check_connection(db)
    print(f"Database Health: {health}")
    
    # Initialize schema
    try:
        initialize_database(db)
        print("Database schema initialized")
    except Exception as e:
        print(f"Schema initialization error: {e}")
    
    # Get statistics
    stats = HealthCheck.get_database_stats(db)
    print(f"Database Stats: {stats}")
    
    db.close()
