"""
LightGBM model for stock price prediction
"""

import numpy as np
import lightgbm as lgb
from .base_model import BaseModel


class LightGBMModel(BaseModel):
    """
    LightGBM Gradient Boosting model

    Strengths:
    - Fast training and inference
    - Handles non-linear relationships
    - Feature importance
    - Robust to outliers
    """

    def __init__(self, params: dict = None):
        super().__init__(model_name='LightGBM')

        # Default parameters
        self.params = params or {
            'objective': 'regression',
            'metric': 'mae',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'max_depth': -1,
            'min_data_in_leaf': 20,
            'verbose': -1,
            'seed': 42
        }

    def fit(self, X: np.ndarray, y: np.ndarray, num_boost_round: int = 500) -> 'LightGBMModel':
        """
        Train LightGBM model

        Args:
            X: Features
            y: Targets
            num_boost_round: Number of boosting iterations

        Returns:
            self
        """
        # Create dataset
        train_data = lgb.Dataset(X, label=y)

        # Train model
        self.model = lgb.train(
            self.params,
            train_data,
            num_boost_round=num_boost_round,
            valid_sets=[train_data],
            valid_names=['train'],
            callbacks=[
                lgb.early_stopping(stopping_rounds=50),
                lgb.log_evaluation(period=0)  # Suppress training logs
            ]
        )

        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predict using LightGBM

        Args:
            X: Features

        Returns:
            Predictions
        """
        if not self.is_fitted:
            raise ValueError("Model is not fitted yet. Call fit() first.")

        predictions = self.model.predict(X, num_iteration=self.model.best_iteration)
        return predictions

    def get_feature_importance(self) -> dict:
        """
        Get feature importance scores

        Returns:
            Dictionary of {feature_name: importance}
        """
        if not self.is_fitted:
            raise ValueError("Model is not fitted yet.")

        importance = self.model.feature_importance(importance_type='gain')
        return {
            f'feature_{i}': imp
            for i, imp in enumerate(importance)
        }
