"""
Prophet model for stock price prediction
"""

import numpy as np
import pandas as pd
from prophet import Prophet
from .base_model import BaseModel


class ProphetModel(BaseModel):
    """
    Facebook Prophet model

    Strengths:
    - Automatic changepoint detection
    - Robust to missing data
    - Handles trend changes well
    - Interpretable components
    """

    def __init__(self, params: dict = None):
        super().__init__(model_name='Prophet')

        # Default parameters
        self.params = params or {
            'changepoint_prior_scale': 0.05,
            'seasonality_prior_scale': 10,
            'daily_seasonality': True,
            'weekly_seasonality': True,
            'yearly_seasonality': False
        }

        self.model = Prophet(**self.params)
        self.feature_names = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> 'ProphetModel':
        """
        Train Prophet model

        Args:
            X: Features (first column should be dates or will use index)
            y: Target values

        Returns:
            self
        """
        # Prepare data for Prophet
        # Prophet requires DataFrame with 'ds' (date) and 'y' (value) columns
        df = pd.DataFrame({
            'ds': pd.date_range(start='2015-01-01', periods=len(y), freq='D'),
            'y': y
        })

        # Add regressors if X has multiple columns
        if X.shape[1] > 0:
            self.feature_names = [f'feature_{i}' for i in range(X.shape[1])]
            for i, name in enumerate(self.feature_names):
                df[name] = X[:, i]
                self.model.add_regressor(name)

        # Fit model
        self.model.fit(df)
        self.is_fitted = True

        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predict using Prophet

        Args:
            X: Features

        Returns:
            Predictions
        """
        if not self.is_fitted:
            raise ValueError("Model is not fitted yet. Call fit() first.")

        # Create future dataframe
        future = pd.DataFrame({
            'ds': pd.date_range(start='2024-01-01', periods=len(X), freq='D')
        })

        # Add regressors
        if self.feature_names:
            for i, name in enumerate(self.feature_names):
                future[name] = X[:, i]

        # Predict
        forecast = self.model.predict(future)
        predictions = forecast['yhat'].values

        return predictions
