"""
ARIMAX Stock Price Predictor
ARIMA with eXogenous variables (Volume, RSI, MACD, etc.)
Cải thiện độ chính xác bằng cách thêm technical indicators
"""

import pandas as pd
import numpy as np
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import adfuller
import warnings
import logging

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class ARIMAXPredictor:
    """Dự đoán giá cổ phiếu bằng ARIMAX với technical indicators"""

    @staticmethod
    def prepare_exogenous_features(df):
        """
        Chuẩn bị exogenous features từ DataFrame

        Args:
            df: DataFrame với columns: close, volume, rsi, macd, ma5, ma20

        Returns:
            DataFrame: Features đã chuẩn bị
        """
        features = pd.DataFrame()

        # Volume (normalized)
        if 'volume' in df.columns:
            # Normalize volume by rolling mean
            volume_ma = df['volume'].rolling(window=5, min_periods=1).mean()
            features['volume_norm'] = df['volume'] / volume_ma
            features['volume_norm'].fillna(1.0, inplace=True)

        # RSI (already 0-100)
        if 'rsi' in df.columns:
            features['rsi'] = df['rsi'].fillna(50.0)  # Neutral value

        # MACD
        if 'macd_main' in df.columns:
            features['macd'] = df['macd_main'].fillna(0.0)

        # MA crossover signal
        if 'ma5' in df.columns and 'ma20' in df.columns:
            # 1 if MA5 > MA20 (bullish), -1 if MA5 < MA20 (bearish)
            features['ma_signal'] = np.where(
                df['ma5'] > df['ma20'], 1, -1
            )

        # Price momentum (% change)
        if 'close' in df.columns:
            features['momentum'] = df['close'].pct_change(5).fillna(0) * 100

        # Ensure no NaN values
        features.fillna(method='ffill', inplace=True)
        features.fillna(0, inplace=True)

        logger.info(f"📊 Prepared {len(features.columns)} exogenous features: {list(features.columns)}")
        return features

    @staticmethod
    def auto_select_order(prices, exog, max_p=3, max_q=2):
        """
        Tự động chọn best ARIMAX parameters

        Args:
            prices: Mảng giá
            exog: Exogenous features DataFrame
            max_p: Max AR order
            max_q: Max MA order

        Returns:
            tuple: (p, d, q) tối ưu
        """
        best_aic = float('inf')
        best_order = None

        d = 1  # Usually 1 for stock prices

        for p in range(0, max_p + 1):
            for q in range(0, max_q + 1):
                try:
                    model = SARIMAX(
                        prices,
                        exog=exog,
                        order=(p, d, q),
                        enforce_stationarity=False,
                        enforce_invertibility=False
                    )
                    model_fit = model.fit(disp=False, maxiter=100)

                    if model_fit.aic < best_aic:
                        best_aic = model_fit.aic
                        best_order = (p, d, q)

                except Exception as e:
                    continue

        if best_order is None:
            best_order = (1, 1, 1)  # Default
            logger.warning(f"⚠️ Could not auto-select, using default ARIMAX{best_order}")
        else:
            logger.info(f"✅ Best ARIMAX order: {best_order} (AIC={best_aic:.2f})")

        return best_order

    @staticmethod
    def predict_3day_arimax(df, auto_order=True):
        """
        Dự đoán 3 ngày bằng ARIMAX với exogenous variables

        Args:
            df: DataFrame phải có columns: close, volume, rsi, macd_main, ma5, ma20
            auto_order: Tự động chọn parameters

        Returns:
            dict: {
                'predictions': [day1, day2, day3],
                'order': (p, d, q),
                'features_used': [list of features]
            }
        """
        try:
            # Validate input
            required_cols = ['close']
            if not all(col in df.columns for col in required_cols):
                logger.error(f"❌ Missing required columns: {required_cols}")
                return None

            if len(df) < 30:
                logger.warning(f"⚠️ Not enough data (have {len(df)}, need >= 30)")
                return None

            # Prepare data
            df_recent = df.tail(60).copy()
            prices = df_recent['close'].values

            # Prepare exogenous features
            exog_features = ARIMAXPredictor.prepare_exogenous_features(df_recent)

            if exog_features.empty or len(exog_features.columns) == 0:
                logger.warning("⚠️ No exogenous features available, falling back to ARIMA")
                from src.predictions_arima.arima_predict import ARIMAPredictor
                return {
                    'predictions': ARIMAPredictor.predict_3day_arima(df),
                    'order': None,
                    'features_used': [],
                    'model': 'ARIMA_FALLBACK'
                }

            logger.info(f"📊 Training ARIMAX with {len(prices)} prices + {len(exog_features.columns)} features")

            # Auto-select order
            if auto_order:
                order = ARIMAXPredictor.auto_select_order(prices, exog_features)
            else:
                order = (1, 1, 1)

            # Fit ARIMAX model
            model = SARIMAX(
                prices,
                exog=exog_features,
                order=order,
                enforce_stationarity=False,
                enforce_invertibility=False
            )
            model_fit = model.fit(disp=False, maxiter=200)

            # Forecast 3 days
            # Need to provide future exog values (use last values as proxy)
            last_exog = exog_features.iloc[-1:].values
            future_exog = np.repeat(last_exog, 3, axis=0)

            forecast = model_fit.forecast(steps=3, exog=future_exog)
            predictions = [round(float(p), 2) for p in forecast]

            logger.info(f"✅ ARIMAX{order} predictions: {predictions}")

            # Validate predictions
            last_price = float(prices[-1])
            for i, pred in enumerate(predictions):
                if pred < 0 or abs(pred - last_price) / last_price > 0.5:
                    logger.warning(f"⚠️ Suspicious prediction adjusted: {pred}")
                    predictions[i] = last_price * (1.05 if pred > last_price else 0.95)

            return {
                'predictions': predictions,
                'order': order,
                'features_used': list(exog_features.columns),
                'model': 'ARIMAX'
            }

        except Exception as e:
            logger.error(f"❌ Error in ARIMAX prediction: {e}", exc_info=True)
            return None

    @staticmethod
    def predict_with_confidence(df, confidence=0.95):
        """
        Dự đoán với confidence interval

        Args:
            df: DataFrame với features
            confidence: Mức độ tin cậy

        Returns:
            dict: Predictions với confidence intervals
        """
        try:
            df_recent = df.tail(60).copy()
            prices = df_recent['close'].values
            exog_features = ARIMAXPredictor.prepare_exogenous_features(df_recent)

            if exog_features.empty:
                logger.warning("⚠️ No features, falling back to ARIMA")
                return None

            # Auto-select order
            order = ARIMAXPredictor.auto_select_order(prices, exog_features)

            # Fit model
            model = SARIMAX(
                prices,
                exog=exog_features,
                order=order,
                enforce_stationarity=False,
                enforce_invertibility=False
            )
            model_fit = model.fit(disp=False, maxiter=200)

            # Forecast with confidence interval
            last_exog = exog_features.iloc[-1:].values
            future_exog = np.repeat(last_exog, 3, axis=0)

            forecast_result = model_fit.get_forecast(steps=3, exog=future_exog)
            predictions = forecast_result.predicted_mean
            conf_int = forecast_result.conf_int(alpha=1-confidence)

            result = {
                'predictions': [round(float(p), 2) for p in predictions],
                'lower_bound': [round(float(p), 2) for p in conf_int.iloc[:, 0]],
                'upper_bound': [round(float(p), 2) for p in conf_int.iloc[:, 1]],
                'order': order,
                'features_used': list(exog_features.columns),
                'confidence': confidence,
                'model': 'ARIMAX'
            }

            logger.info(f"✅ ARIMAX{order} with {confidence*100}% confidence interval")
            return result

        except Exception as e:
            logger.error(f"❌ Error in confidence prediction: {e}")
            return None

    @staticmethod
    def compare_with_without_exog(df):
        """
        So sánh ARIMAX (with exog) vs ARIMA (without exog)

        Args:
            df: DataFrame

        Returns:
            dict: Comparison results
        """
        try:
            # ARIMA (no exog)
            from src.predictions_arima.arima_predict import ARIMAPredictor
            arima_pred = ARIMAPredictor.predict_3day_arima(df)

            # ARIMAX (with exog)
            arimax_result = ARIMAXPredictor.predict_3day_arimax(df)

            if arima_pred and arimax_result:
                arimax_pred = arimax_result['predictions']

                comparison = {
                    'arima': arima_pred,
                    'arimax': arimax_pred,
                    'difference': [
                        round(arimax_pred[i] - arima_pred[i], 2)
                        for i in range(3)
                    ],
                    'improvement': [
                        round((arimax_pred[i] - arima_pred[i]) / arima_pred[i] * 100, 2)
                        for i in range(3)
                    ],
                    'features_used': arimax_result['features_used']
                }

                logger.info("📊 ARIMAX vs ARIMA comparison:")
                logger.info(f"   ARIMA:  {arima_pred}")
                logger.info(f"   ARIMAX: {arimax_pred}")
                logger.info(f"   Diff:   {comparison['difference']}")

                return comparison
            else:
                return None

        except Exception as e:
            logger.error(f"❌ Error in comparison: {e}")
            return None

    @staticmethod
    def batch_predict(tickers_data: dict):
        """
        Dự đoán nhiều tickers cùng lúc

        Args:
            tickers_data: Dict {ticker: dataframe}

        Returns:
            dict: {ticker: predictions}
        """
        results = {}

        for ticker, df in tickers_data.items():
            logger.info(f"🔄 Processing {ticker}...")
            result = ARIMAXPredictor.predict_3day_arimax(df)

            if result:
                results[ticker] = result
            else:
                logger.warning(f"⚠️ Failed to predict {ticker}")

        logger.info(f"✅ Batch prediction completed: {len(results)}/{len(tickers_data)} successful")
        return results
