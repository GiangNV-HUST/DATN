"""
XGBoost model for stock price prediction
"""

import numpy as np
import xgboost as xgb
from .base_model import BaseModel


class XGBoostModel(BaseModel):
    """
    XGBoost Gradient Boosting model

    Strengths:
    - Powerful gradient boosting
    - Handles complex patterns
    - Regularization built-in
    - Parallel processing
    """

    def __init__(self, params: dict = None):
        super().__init__(model_name='XGBoost')

        # Default parameters
        self.params = params or {
            'objective': 'reg:squarederror',
            'max_depth': 6,
            'learning_rate': 0.05,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'min_child_weight': 3,
            'gamma': 0.1,
            'alpha': 0.1,  # L1 regularization
            'lambda': 1.0,  # L2 regularization
            'seed': 42,
            'verbosity': 0
        }

    def fit(self, X: np.ndarray, y: np.ndarray, num_boost_round: int = 500) -> 'XGBoostModel':
        """
        Train XGBoost model

        Args:
            X: Features
            y: Targets
            num_boost_round: Number of boosting iterations

        Returns:
            self
        """
        # Create DMatrix
        dtrain = xgb.DMatrix(X, label=y)

        # Train model
        self.model = xgb.train(
            self.params,
            dtrain,
            num_boost_round=num_boost_round,
            evals=[(dtrain, 'train')],
            early_stopping_rounds=50,
            verbose_eval=False
        )

        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predict using XGBoost

        Args:
            X: Features

        Returns:
            Predictions
        """
        if not self.is_fitted:
            raise ValueError("Model is not fitted yet. Call fit() first.")

        dtest = xgb.DMatrix(X)
        predictions = self.model.predict(dtest)
        return predictions

    def get_feature_importance(self) -> dict:
        """
        Get feature importance scores

        Returns:
            Dictionary of {feature_name: importance}
        """
        if not self.is_fitted:
            raise ValueError("Model is not fitted yet.")

        importance = self.model.get_score(importance_type='gain')
        return importance
