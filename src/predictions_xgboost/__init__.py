"""
XGBoost-based Stock Price Prediction
CPU-friendly alternative to LSTM with train-on-demand capability
"""

from .xgboost_predict import XGBoostPredictor

__all__ = ['XGBoostPredictor']
