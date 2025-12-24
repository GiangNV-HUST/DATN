import pandas as pd
import numpy as np


class TechnicalIndicators:
    """Tính toán các chỉ báo kỹ thuật"""

    @staticmethod
    def calculate_avg_volume(df, column="volume", periods=[5, 10, 20]):
        """Hàm tính trung bình volume"""
        df = df.copy()
        for period in periods:
            df[f"avg_volume_{period}"] = df[column].rolling(window=period).mean()
        return df

    @staticmethod
    def calculate_ma(df, column="close", periods=[5, 10, 20, 50, 100]):
        """
        Tính toán Moving Average

        Args:
            df: DataFrame với column 'close'
            periods: List các periods (VD: [5, 10, 20, 50, 100])

        Returns:
            DataFrame với các cột ma5, ma10, ma20, ma50, ma100
        """
        df = df.copy()
        for period in periods:
            df[f"ma{period}"] = df[column].rolling(window=period).mean()
        return df

    @staticmethod
    def calculate_rsi(df, column="close", period=14):
        """
        Tính RSI (Relative Strength Index)

        Args:
            df: DataFrame
            period: Period (mặc định 14)

        Return:
            DataFrame với cột 'rsi'
        """
        df = df.copy()
        delta = df[column].diff()

        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()

        rs = avg_gain / avg_loss

        df["rsi"] = 100 - (100 / (1 + rs))

        return df

    @staticmethod
    def calculate_macd(df, column="close", fast=12, slow=26, signal=9):
        """
        Tính MACD

        Args:
            df: DataFrame
            fast: Fast EMA period (mặc định 12)
            slow: Slow EMA period (mặc định 26)
            signal: Signal line period (mặc định 9)

        Returns:
            DataFrame với macd_main, macd_signal, macd_diff
        """
        df = df.copy()

        ema_fast = df[column].ewm(span=fast, adjust=False).mean()
        ema_slow = df[column].ewm(span=slow, adjust=False).mean()

        df["macd_main"] = ema_fast - ema_slow
        df["macd_signal"] = df["macd_main"].ewm(span=signal, adjust=False).mean()
        df["macd_diff"] = df["macd_main"] - df["macd_signal"]

        return df

    @staticmethod
    def calculate_bollinger_bands(df, column="close", period=20, std_dev=2):
        """
        Tính Bollinger Bands

        Returns:
            DataFrame với bb_upper, bb_middle, bb_lower
        """

        df = df.copy()

        df["bb_middle"] = df[column].rolling(window=period).mean()
        std = df[column].rolling(window=period).std()

        df["bb_upper"] = df["bb_middle"] + (std * std_dev)
        df["bb_lower"] = df["bb_middle"] - (std * std_dev)
        return df

    @staticmethod
    def calculate_all(df):
        """
        Tính tất cả indicators cơ bản
        
        Args:
            df: DataFrame với columns: time, open, high, low, close, volume
        
        Returns:
            DataFrame với tất cả indicators
        """
        df = df.copy()
        
        # Average Volume
        df = TechnicalIndicators.calculate_avg_volume(df, periods=[5,10,20])
        
        # Moving Average
        df = TechnicalIndicators.calculate_ma(df, periods=[5,10,20,50,100])
        
        # Bolling Bands
        df = TechnicalIndicators.calculate_bollinger_bands(df)
        
        # RSI
        df = TechnicalIndicators.calculate_rsi(df)
        
        # MACD
        df = TechnicalIndicators.calculate_macd(df) 
        
        return df 
     