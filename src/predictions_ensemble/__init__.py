"""
Ensemble Stock Price Prediction
Combines ARIMAX (interpretable, CI) + XGBoost (accurate, CPU-friendly)
Best balance: Speed, Accuracy, Production-ready
"""

from .ensemble_predict import EnsemblePredictor

__all__ = ['EnsemblePredictor']
