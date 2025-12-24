"""
ARIMA Stock Price Predictor
Cải thiện độ chính xác so với Moving Average
"""

import pandas as pd
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller
import warnings
import logging

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class ARIMAPredictor:
    """Dự đoán giá cổ phiếu bằng ARIMA"""

    @staticmethod
    def check_stationarity(series):
        """
        Kiểm tra tính dừng của chuỗi thời gian

        Args:
            series: pandas Series hoặc numpy array

        Returns:
            bool: True nếu chuỗi dừng (stationary)
        """
        try:
            result = adfuller(series.dropna())
            p_value = result[1]
            is_stationary = p_value <= 0.05

            logger.info(f"📊 Stationarity test: p-value={p_value:.4f}, stationary={is_stationary}")
            return is_stationary
        except Exception as e:
            logger.error(f"Error checking stationarity: {e}")
            return False

    @staticmethod
    def auto_select_order(prices, max_p=5, max_q=2):
        """
        Tự động chọn best ARIMA parameters (p,d,q) dựa trên AIC

        Args:
            prices: Mảng giá cổ phiếu
            max_p: Max AR order
            max_q: Max MA order

        Returns:
            tuple: (p, d, q) tối ưu
        """
        best_aic = float('inf')
        best_order = None

        # d thường là 1 cho stock prices (non-stationary)
        d = 1

        # Grid search
        for p in range(0, max_p + 1):
            for q in range(0, max_q + 1):
                try:
                    model = ARIMA(prices, order=(p, d, q))
                    model_fit = model.fit()

                    if model_fit.aic < best_aic:
                        best_aic = model_fit.aic
                        best_order = (p, d, q)

                except Exception:
                    continue

        if best_order is None:
            # Fallback to default
            best_order = (5, 1, 0)
            logger.warning(f"⚠️ Could not auto-select, using default ARIMA{best_order}")
        else:
            logger.info(f"✅ Best ARIMA order: {best_order} (AIC={best_aic:.2f})")

        return best_order

    @staticmethod
    def predict_3day_arima(df, column="close", auto_order=True):
        """
        Dự đoán 3 ngày bằng ARIMA model

        Args:
            df: DataFrame với column giá (ví dụ: 'close')
            column: Tên column chứa giá (default: 'close')
            auto_order: Tự động chọn best parameters (default: True)

        Returns:
            list: [day1, day2, day3] predictions hoặc None nếu lỗi
        """
        try:
            # Validate input
            if df is None or df.empty:
                logger.warning("⚠️ Empty dataframe")
                return None

            if column not in df.columns:
                logger.error(f"❌ Column '{column}' not found in dataframe")
                return None

            # Lấy giá, ít nhất 30 điểm dữ liệu
            prices = df[column].dropna().values

            if len(prices) < 30:
                logger.warning(f"⚠️ Not enough data for ARIMA (have {len(prices)}, need >= 30)")
                return None

            # Sử dụng 60 ngày gần nhất (hoặc tất cả nếu < 60)
            prices = prices[-min(60, len(prices)):]

            logger.info(f"📊 Training ARIMA with {len(prices)} data points")

            # Auto-select best order hoặc dùng default
            if auto_order:
                order = ARIMAPredictor.auto_select_order(prices)
            else:
                order = (5, 1, 0)  # Default ARIMA(5,1,0)

            # Fit ARIMA model
            model = ARIMA(prices, order=order)
            model_fit = model.fit()

            # Forecast 3 ngày
            forecast = model_fit.forecast(steps=3)
            predictions = [round(float(p), 2) for p in forecast]

            logger.info(f"✅ ARIMA{order} predictions: {predictions}")

            # Validate predictions (không được âm hoặc quá khác biệt)
            last_price = float(prices[-1])
            for i, pred in enumerate(predictions):
                if pred < 0:
                    logger.warning(f"⚠️ Negative prediction adjusted: {pred} -> {last_price}")
                    predictions[i] = last_price
                elif abs(pred - last_price) / last_price > 0.5:  # > 50% change
                    logger.warning(f"⚠️ Extreme prediction adjusted: {pred}")
                    predictions[i] = last_price * (1.1 if pred > last_price else 0.9)

            return predictions

        except Exception as e:
            logger.error(f"❌ Error in ARIMA prediction: {e}", exc_info=True)
            return None

    @staticmethod
    def predict_with_confidence(df, column="close", confidence=0.95):
        """
        Dự đoán 3 ngày kèm confidence interval (khoảng tin cậy)

        Args:
            df: DataFrame với column giá
            column: Tên column chứa giá
            confidence: Mức độ tin cậy (0.95 = 95%)

        Returns:
            dict: {
                'predictions': [day1, day2, day3],
                'lower_bound': [lower1, lower2, lower3],
                'upper_bound': [upper1, upper2, upper3],
                'order': (p, d, q)
            }
        """
        try:
            prices = df[column].dropna().values[-60:]

            if len(prices) < 30:
                logger.warning("⚠️ Not enough data for confidence prediction")
                return None

            # Auto-select order
            order = ARIMAPredictor.auto_select_order(prices)

            # Fit model
            model = ARIMA(prices, order=order)
            model_fit = model.fit()

            # Forecast với confidence interval
            forecast_result = model_fit.get_forecast(steps=3)
            predictions = forecast_result.predicted_mean
            conf_int = forecast_result.conf_int(alpha=1-confidence)

            result = {
                'predictions': [round(float(p), 2) for p in predictions],
                'lower_bound': [round(float(p), 2) for p in conf_int[:, 0]],
                'upper_bound': [round(float(p), 2) for p in conf_int[:, 1]],
                'order': order,
                'confidence': confidence
            }

            logger.info(f"✅ ARIMA{order} with {confidence*100}% confidence interval")
            return result

        except Exception as e:
            logger.error(f"❌ Error in confidence prediction: {e}")
            return None

    @staticmethod
    def predict_48day_arima(df, column="close"):
        """
        Dự đoán 48 ngày bằng ARIMA
        Thay thế cho Linear Regression trong simple_predict.py

        Args:
            df: DataFrame với column giá
            column: Tên column chứa giá

        Returns:
            list: 48 predictions
        """
        try:
            prices = df[column].dropna().values

            if len(prices) < 50:
                logger.warning("⚠️ Not enough data for 48-day prediction")
                return None

            # Sử dụng 100 ngày gần nhất
            prices = prices[-min(100, len(prices)):]

            # Auto-select order
            order = ARIMAPredictor.auto_select_order(prices, max_p=3, max_q=1)

            # Fit model
            model = ARIMA(prices, order=order)
            model_fit = model.fit()

            # Forecast 48 days
            forecast = model_fit.forecast(steps=48)
            predictions = [round(float(p), 2) for p in forecast]

            logger.info(f"✅ ARIMA{order} 48-day predictions generated")
            return predictions

        except Exception as e:
            logger.error(f"❌ Error in 48-day prediction: {e}")
            return None

    @staticmethod
    def calculate_accuracy_metrics(actual, predicted):
        """
        Tính các metrics đánh giá độ chính xác

        Args:
            actual: Giá thực tế
            predicted: Giá dự đoán

        Returns:
            dict: {
                'mae': Mean Absolute Error,
                'mape': Mean Absolute Percentage Error,
                'rmse': Root Mean Squared Error
            }
        """
        try:
            actual = np.array(actual)
            predicted = np.array(predicted)

            # MAE
            mae = np.mean(np.abs(actual - predicted))

            # MAPE
            mape = np.mean(np.abs((actual - predicted) / actual)) * 100

            # RMSE
            rmse = np.sqrt(np.mean((actual - predicted) ** 2))

            return {
                'mae': round(float(mae), 2),
                'mape': round(float(mape), 2),
                'rmse': round(float(rmse), 2)
            }

        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return None
