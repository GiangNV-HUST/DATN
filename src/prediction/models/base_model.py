"""
Base model interface for all prediction models
"""

from abc import ABC, abstractmethod
import numpy as np
import pandas as pd
from typing import Dict, Any
import pickle
from pathlib import Path


class BaseModel(ABC):
    """
    Abstract base class for all prediction models
    """

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model = None
        self.is_fitted = False

    @abstractmethod
    def fit(self, X: np.ndarray, y: np.ndarray) -> 'BaseModel':
        """
        Train the model

        Args:
            X: Features, shape (n_samples, n_features)
            y: Targets, shape (n_samples,)

        Returns:
            self
        """
        pass

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Make predictions

        Args:
            X: Features, shape (n_samples, n_features)

        Returns:
            Predictions, shape (n_samples,)
        """
        pass

    def save(self, filepath: str):
        """Save model to disk"""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'wb') as f:
            pickle.dump(self, f)

        print(f"✓ {self.model_name} saved to {filepath}")

    @staticmethod
    def load(filepath: str) -> 'BaseModel':
        """Load model from disk"""
        with open(filepath, 'rb') as f:
            model = pickle.load(f)

        print(f"✓ Model loaded from {filepath}")
        return model

    def get_params(self) -> Dict[str, Any]:
        """Get model parameters"""
        return {
            'model_name': self.model_name,
            'is_fitted': self.is_fitted
        }

    def __repr__(self):
        return f"{self.__class__.__name__}(name='{self.model_name}', fitted={self.is_fitted})"
