"""
Prediction Service for Stock Price Forecasting using Ensemble Model

This service provides:
1. Load trained ensemble models
2. Fetch latest stock data from database
3. Generate features
4. Make predictions (3-day or 48-day forecast)
5. Return predictions with confidence intervals
"""

import os
import sys
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pickle

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.prediction.ensemble_stacking import EnsembleStacking
from src.prediction.utils.feature_engineering import create_features


class PredictionService:
    """
    Service for stock price prediction using ensemble model

    Features:
    - Model loading and caching
    - Feature generation from raw data
    - Prediction with confidence intervals
    - Support for 3-day and 48-day forecasts
    """

    def __init__(self, models_dir: str = None):
        """
        Initialize prediction service

        Args:
            models_dir: Directory containing trained models
                       Default: src/prediction/trained_models/
        """
        if models_dir is None:
            models_dir = os.path.join(
                os.path.dirname(__file__),
                'trained_models'
            )

        self.models_dir = models_dir
        self.loaded_models = {}  # Cache for loaded models

        # Ensure models directory exists
        os.makedirs(self.models_dir, exist_ok=True)

    def _get_model_path(self, ticker: str, horizon: str) -> str:
        """Get path to model file"""
        return os.path.join(
            self.models_dir,
            f"{ticker}_{horizon}_ensemble.pkl"
        )

    def load_model(self, ticker: str, horizon: str = "3day") -> EnsembleStacking:
        """
        Load trained ensemble model

        Args:
            ticker: Stock ticker symbol (e.g., 'VCB', 'VHM')
            horizon: Forecast horizon ('3day' or '48day')

        Returns:
            Loaded EnsembleStacking model

        Raises:
            FileNotFoundError: If model file doesn't exist
        """
        # Check cache
        cache_key = f"{ticker}_{horizon}"
        if cache_key in self.loaded_models:
            return self.loaded_models[cache_key]

        # Load from disk
        model_path = self._get_model_path(ticker, horizon)

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model not found: {model_path}\n"
                f"Please train the model first using: "
                f"python scripts/train_ensemble.py --ticker {ticker} --horizon {horizon}"
            )

        print(f"📂 Loading model: {ticker} ({horizon})")
        ensemble = EnsembleStacking.load(model_path)

        # Cache it
        self.loaded_models[cache_key] = ensemble

        return ensemble

    def prepare_features_from_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare features from raw OHLCV data

        Args:
            df: DataFrame with columns ['open', 'high', 'low', 'close', 'volume']
               Index should be datetime

        Returns:
            DataFrame with engineered features
        """
        # Ensure datetime index
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'date' in df.columns or 'time' in df.columns:
                date_col = 'date' if 'date' in df.columns else 'time'
                df[date_col] = pd.to_datetime(df[date_col])
                df = df.set_index(date_col)
            else:
                raise ValueError("DataFrame must have datetime index or 'date'/'time' column")

        # Sort by date
        df = df.sort_index()

        # Create features
        features = create_features(df)

        return features

    def predict(
        self,
        ticker: str,
        data: pd.DataFrame,
        horizon: str = "3day",
        return_confidence: bool = True
    ) -> Dict:
        """
        Make prediction for stock price

        Args:
            ticker: Stock ticker symbol
            data: Historical OHLCV data (minimum 100 rows recommended)
            horizon: Forecast horizon ('3day' or '48day')
            return_confidence: If True, return confidence intervals

        Returns:
            Dictionary with:
            - ticker: Stock symbol
            - horizon: Forecast horizon
            - current_price: Latest closing price
            - predicted_price: Predicted price
            - change_percent: Expected change percentage
            - confidence_lower: Lower bound (95% CI)
            - confidence_upper: Upper bound (95% CI)
            - prediction_date: When prediction was made
            - target_date: Date for predicted price
        """
        # Load model
        ensemble = self.load_model(ticker, horizon)

        # Prepare features
        features = self.prepare_features_from_data(data)

        # Get the last row for prediction (most recent data)
        X_latest = features.iloc[[-1]].drop(columns=['close'], errors='ignore')

        # Make prediction
        predicted_price = ensemble.predict(X_latest)[0]

        # Current price
        current_price = data['close'].iloc[-1]

        # Calculate change
        change_percent = ((predicted_price - current_price) / current_price) * 100

        # Calculate target date
        horizon_days = int(horizon.replace('day', ''))
        last_date = data.index[-1]

        # Add business days (skip weekends)
        target_date = last_date + pd.Timedelta(days=horizon_days)
        while target_date.weekday() >= 5:  # Saturday=5, Sunday=6
            target_date += pd.Timedelta(days=1)

        result = {
            "ticker": ticker,
            "horizon": horizon,
            "current_price": float(current_price),
            "predicted_price": float(predicted_price),
            "change_percent": float(change_percent),
            "prediction_date": datetime.now().isoformat(),
            "target_date": target_date.isoformat(),
        }

        # Add confidence intervals if requested
        if return_confidence:
            # Estimate confidence intervals using ensemble std
            # This is a simplified approach; for better CI, use quantile regression
            predictions_by_model = []
            for model_name, model in ensemble.base_models.items():
                if model.is_fitted:
                    pred = model.predict(X_latest.values)[0]
                    predictions_by_model.append(pred)

            if predictions_by_model:
                std = np.std(predictions_by_model)
                # 95% confidence interval (±1.96 * std)
                result["confidence_lower"] = float(predicted_price - 1.96 * std)
                result["confidence_upper"] = float(predicted_price + 1.96 * std)
            else:
                # Fallback: use 5% of predicted price as uncertainty
                result["confidence_lower"] = float(predicted_price * 0.95)
                result["confidence_upper"] = float(predicted_price * 1.05)

        return result

    def predict_multiple(
        self,
        ticker: str,
        data: pd.DataFrame,
        horizons: List[str] = ["3day", "48day"]
    ) -> Dict[str, Dict]:
        """
        Make predictions for multiple horizons

        Args:
            ticker: Stock ticker symbol
            data: Historical OHLCV data
            horizons: List of forecast horizons

        Returns:
            Dictionary mapping horizon to prediction result
        """
        results = {}

        for horizon in horizons:
            try:
                results[horizon] = self.predict(ticker, data, horizon)
            except Exception as e:
                results[horizon] = {
                    "error": str(e),
                    "ticker": ticker,
                    "horizon": horizon
                }

        return results

    def get_available_models(self) -> List[Dict]:
        """
        List all trained models

        Returns:
            List of dicts with model info (ticker, horizon, file_size, modified_date)
        """
        if not os.path.exists(self.models_dir):
            return []

        models = []

        for filename in os.listdir(self.models_dir):
            if filename.endswith('_ensemble.pkl'):
                # Parse filename: TICKER_HORIZONday_ensemble.pkl
                parts = filename.replace('_ensemble.pkl', '').split('_')
                if len(parts) >= 2:
                    ticker = parts[0]
                    horizon = '_'.join(parts[1:])

                    filepath = os.path.join(self.models_dir, filename)
                    file_size = os.path.getsize(filepath)
                    modified_date = datetime.fromtimestamp(
                        os.path.getmtime(filepath)
                    ).isoformat()

                    models.append({
                        "ticker": ticker,
                        "horizon": horizon,
                        "file_size_mb": round(file_size / (1024 * 1024), 2),
                        "modified_date": modified_date,
                        "file_path": filepath
                    })

        return models


# Global service instance (singleton pattern)
_service_instance = None


def get_prediction_service() -> PredictionService:
    """Get global prediction service instance (singleton)"""
    global _service_instance
    if _service_instance is None:
        _service_instance = PredictionService()
    return _service_instance


# Convenience functions for direct use
def predict_stock_price(
    ticker: str,
    data: pd.DataFrame,
    horizon: str = "3day"
) -> Dict:
    """
    Convenience function to predict stock price

    Args:
        ticker: Stock ticker symbol
        data: Historical OHLCV data
        horizon: Forecast horizon ('3day' or '48day')

    Returns:
        Prediction result dictionary
    """
    service = get_prediction_service()
    return service.predict(ticker, data, horizon)


if __name__ == "__main__":
    # Example usage
    print("🔮 Ensemble Prediction Service")
    print("=" * 50)

    service = PredictionService()

    # List available models
    models = service.get_available_models()
    print(f"\n📋 Available models: {len(models)}")
    for model in models:
        print(f"  - {model['ticker']} ({model['horizon']}): "
              f"{model['file_size_mb']} MB, "
              f"modified: {model['modified_date']}")

    # Example prediction (requires trained model)
    if models:
        ticker = models[0]['ticker']
        horizon = models[0]['horizon']

        print(f"\n🔍 Example prediction for {ticker} ({horizon}):")

        # Load sample data (replace with real data)
        # df = pd.read_sql(f"SELECT * FROM stock_prices WHERE ticker='{ticker}'", conn)

        print("  ⚠️ Note: Need to provide actual OHLCV data to make prediction")
        print(f"  Usage: service.predict('{ticker}', df, '{horizon}')")
    else:
        print("\n⚠️ No trained models found!")
        print("Train a model first: python scripts/train_ensemble.py --ticker VCB --horizon 3day")
