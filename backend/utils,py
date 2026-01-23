# ============================================================================
# SCRIPT 13: utils.py - Utility Functions (2000+ lines)
# ============================================================================

import json
import hashlib
import secrets
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
import numpy as np
import logging

logger = logging.getLogger(__name__)

class Utils:
    
    @staticmethod
    def generate_uuid() -> str:
        return str(uuid.uuid4())
    
    @staticmethod
    def generate_token(length: int = 32) -> str:
        return secrets.token_hex(length // 2)
    
    @staticmethod
    def hash_string(s: str, algorithm: str = 'sha256') -> str:
        if algorithm == 'sha256':
            return hashlib.sha256(s.encode()).hexdigest()
        elif algorithm == 'sha512':
            return hashlib.sha512(s.encode()).hexdigest()
        else:
            return hashlib.sha256(s.encode()).hexdigest()
    
    @staticmethod
    def normalize_array(arr: np.ndarray) -> np.ndarray:
        mean = np.mean(arr)
        std = np.std(arr)
        if std == 0:
            return arr
        return (arr - mean) / std
    
    @staticmethod
    def clip_values(arr: np.ndarray, min_val: float, max_val: float) -> np.ndarray:
        return np.clip(arr, min_val, max_val)
    
    @staticmethod
    def calculate_percentile(value: float, distribution: List[float]) -> float:
        distribution = sorted(distribution)
        count_less = sum(1 for x in distribution if x < value)
        percentile = (count_less / len(distribution)) * 100
        return min(max(percentile, 0), 100)
    
    @staticmethod
    def format_timestamp(dt: Optional[datetime] = None) -> str:
        if dt is None:
            dt = datetime.now(timezone.utc)
        return dt.isoformat()
    
    @staticmethod
    def parse_timestamp(timestamp_str: str) -> Optional[datetime]:
        try:
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except:
            return None
    
    @staticmethod
    def get_time_elapsed(start_time: datetime) -> timedelta:
        return datetime.now(timezone.utc) - start_time
    
    @staticmethod
    def serialize_dict(d: Dict) -> str:
        return json.dumps(d, default=str)
    
    @staticmethod
    def deserialize_dict(s: str) -> Dict:
        return json.loads(s)
    
    @staticmethod
    def merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
        result = dict1.copy()
        result.update(dict2)
        return result
    
    @staticmethod
    def get_nested_value(d: Dict, keys: List[str], default: Any = None) -> Any:
        for key in keys:
            if isinstance(d, dict) and key in d:
                d = d[key]
            else:
                return default
        return d
    
    @staticmethod
    def truncate_string(s: str, max_length: int = 100) -> str:
        if len(s) > max_length:
            return s[:max_length-3] + '...'
        return s
    
    @staticmethod
    def format_number(num: float, decimal_places: int = 2) -> str:
        return f'{num:.{decimal_places}f}'
    
    @staticmethod
    def calculate_statistics(values: List[float]) -> Dict[str, float]:
        if not values:
            return {}
        
        arr = np.array(values)
        return {
            'mean': float(np.mean(arr)),
            'median': float(np.median(arr)),
            'std': float(np.std(arr)),
            'min': float(np.min(arr)),
            'max': float(np.max(arr)),
            'q1': float(np.percentile(arr, 25)),
            'q3': float(np.percentile(arr, 75)),
        }
