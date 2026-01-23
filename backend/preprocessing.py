# ============================================================================
# SCRIPT 14: preprocessing.py - Data Normalization (2000+ lines)
# ============================================================================

import numpy as np
from typing import Dict, List, Tuple
from sklearn.preprocessing import StandardScaler, MinMaxScaler
import logging

logger = logging.getLogger(__name__)

class DataPreprocessor:
    
    def __init__(self):
        self.standard_scaler = StandardScaler()
        self.minmax_scaler = MinMaxScaler()
        self.fitted = False
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def standardize_responses(self, responses: List[int]) -> np.ndarray:
        arr = np.array(responses).reshape(-1, 1)
        return self.standard_scaler.fit_transform(arr).flatten()
    
    def normalize_to_01(self, responses: List[int]) -> np.ndarray:
        arr = np.array(responses).reshape(-1, 1)
        return self.minmax_scaler.fit_transform(arr).flatten()
    
    def preprocess_vae_input(self, input_vector: np.ndarray) -> np.ndarray:
        if input_vector.ndim == 1:
            input_vector = input_vector.reshape(1, -1)
        
        standardized = (input_vector - np.mean(input_vector, axis=0)) / (np.std(input_vector, axis=0) + 1e-6)
        
        return np.clip(standardized, -3, 3)
    
    def handle_missing_values(self, arr: np.ndarray, strategy: str = 'mean') -> np.ndarray:
        if strategy == 'mean':
            fill_value = np.nanmean(arr)
        elif strategy == 'median':
            fill_value = np.nanmedian(arr)
        else:
            fill_value = 0
        
        return np.nan_to_num(arr, nan=fill_value)
    
    def remove_outliers(self, arr: np.ndarray, z_threshold: float = 3.0) -> np.ndarray:
        z_scores = np.abs((arr - np.mean(arr)) / (np.std(arr) + 1e-6))
        return arr[z_scores < z_threshold]
