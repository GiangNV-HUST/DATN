"""
Simple Stock Price Predictor
Sử dụng Moving Average và Linear Regression
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SimplePredictor:
    """Dự đoán giá cổ phiếu đơn giản"""

    @staticmethod
    def predict_3day_ma(df, column="close"):
        """
        Dự đoán 3 ngày bằng Moving Average extrapolation

        Args:
            df: DataFrame với column 'close

        Returns:
            list: [day1, day2, day3] predictions
        """
        try:
            if df is None or df.empty or len(df) < 20:
                logger.warning("⚠️ Not enough data for 3-day prediction")
                return None

            # Lấy 20 ngày gần nhất
            recent = df.tail(20)
            prices = recent[column].values

            # Tính MA của 5, 10, 20 ngày
            ma5 = np.mean(prices[-5:])
            ma10 = np.mean(prices[-10:])
            ma20 = np.mean(prices[-20:])

            # Trend: so sánh MA ngắn và MA dài
            trend = (ma5 - ma20) / 20  # % change

            # Predict dựa trên trend
            last_price = prices[-1]

            predictions = []
            for i in range(1, 4):
                # Dự đoán: giá cuối + (trend * giá cuối *days)
                predicted = last_price * (1 + trend * i * 0.3)  # 0.3 dampening factor
                predictions.append(round(predicted, 2))

            logger.info(f"3-day prediction: {predictions}")
            return predictions

        except Exception as e:
            logger.error(f"Error in 3-day prediction: {e}")
            return None

    @staticmethod
    def predict_48day_lr(df, column="close"):
        """
        Dự đoán 48 ngày bằng Linear Regression

        Args:
            df: DataFrame với column 'close'

        Returns:
            list: 48 predictions
        """
        try:
            if df is None or df.empty or len(df) < 50:
                logger.warning("⚠️ Not enough data for 48-day prediction")
                return None

            # Lấy 100 ngày gần nhất
            recent = df.tail(100)
            prices = recent[column].values

            # Chuẩn bị data cho Linear Regression
            X = np.arange(len(prices)).reshape(-1, 1)
            y = prices

            # Train model
            model = LinearRegression()
            model.fit(X, y)

            # Predict 48 ngày tiếp theo
            future_X = np.arange(len(X), len(X) + 48).reshape(-1, 1)
            predictions = model.predict(future_X)

            # Round to 2 decimals
            predictions = [round(p, 2) for p in predictions]

            logger.info(f"48-day prediction generated: {len(predictions)} values")
            return predictions

        except Exception as e:
            logger.error(f"Error in 48-day prediction: {e}")
            return None
