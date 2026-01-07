"""
Feature engineering for stock price prediction
"""

import numpy as np
import pandas as pd
from typing import Tuple


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """Calculate RSI indicator"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(prices: pd.Series) -> Tuple[pd.Series, pd.Series]:
    """Calculate MACD indicator"""
    exp1 = prices.ewm(span=12, adjust=False).mean()
    exp2 = prices.ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal


def calculate_bollinger_bands(prices: pd.Series, period: int = 20) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate Bollinger Bands"""
    ma = prices.rolling(period).mean()
    std = prices.rolling(period).std()
    upper = ma + (std * 2)
    lower = ma - (std * 2)
    return upper, ma, lower


def create_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create comprehensive features for stock prediction

    Args:
        df: DataFrame with columns ['open', 'high', 'low', 'close', 'volume']

    Returns:
        DataFrame with features
    """
    features = pd.DataFrame(index=df.index)

    # Price features
    features['close'] = df['close']
    features['high'] = df['high']
    features['low'] = df['low']
    features['open'] = df['open']

    # Lag features (past prices)
    for lag in [1, 2, 3, 5, 10, 20]:
        features[f'close_lag_{lag}'] = df['close'].shift(lag)

    # Moving averages
    for window in [5, 10, 20, 50, 100]:
        features[f'ma_{window}'] = df['close'].rolling(window).mean()

    # MA ratios
    features['ma_5_20_ratio'] = features['ma_5'] / features['ma_20']
    features['ma_20_50_ratio'] = features['ma_20'] / features['ma_50']

    # Price to MA distance
    features['price_to_ma5'] = df['close'] / features['ma_5']
    features['price_to_ma20'] = df['close'] / features['ma_20']

    # Technical indicators
    features['rsi'] = calculate_rsi(df['close'], 14)
    features['rsi_9'] = calculate_rsi(df['close'], 9)

    macd, macd_signal = calculate_macd(df['close'])
    features['macd'] = macd
    features['macd_signal'] = macd_signal
    features['macd_diff'] = macd - macd_signal

    # Bollinger Bands
    bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(df['close'], 20)
    features['bb_upper'] = bb_upper
    features['bb_middle'] = bb_middle
    features['bb_lower'] = bb_lower
    features['bb_width'] = (bb_upper - bb_lower) / bb_middle
    features['bb_position'] = (df['close'] - bb_lower) / (bb_upper - bb_lower)

    # Volume features
    features['volume'] = df['volume']
    features['volume_ma_5'] = df['volume'].rolling(5).mean()
    features['volume_ma_20'] = df['volume'].rolling(20).mean()
    features['volume_ratio'] = df['volume'] / features['volume_ma_20']

    # Price changes (returns)
    for period in [1, 3, 5, 10, 20]:
        features[f'return_{period}d'] = df['close'].pct_change(period)

    # Volatility
    for window in [5, 10, 20]:
        features[f'volatility_{window}d'] = df['close'].rolling(window).std()
        features[f'volatility_{window}d_norm'] = features[f'volatility_{window}d'] / df['close']

    # High-Low range
    features['hl_ratio'] = df['high'] / df['low']
    features['hl_range'] = df['high'] - df['low']
    features['hl_range_norm'] = features['hl_range'] / df['close']

    # Close position in daily range
    features['close_position'] = (df['close'] - df['low']) / (df['high'] - df['low'])

    # Momentum
    features['momentum_10'] = df['close'] - df['close'].shift(10)
    features['momentum_20'] = df['close'] - df['close'].shift(20)

    # Rate of change
    features['roc_10'] = ((df['close'] - df['close'].shift(10)) / df['close'].shift(10)) * 100
    features['roc_20'] = ((df['close'] - df['close'].shift(20)) / df['close'].shift(20)) * 100

    # Time features
    features['day_of_week'] = df.index.dayofweek
    features['month'] = df.index.month
    features['quarter'] = df.index.quarter
    features['day_of_month'] = df.index.day

    # Fill NaN values
    features = features.fillna(method='ffill').fillna(method='bfill')

    return features


def prepare_training_data(
    features: pd.DataFrame,
    target_col: str = 'close',
    horizon: int = 3,
    test_size: float = 0.2
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Prepare data for training

    Args:
        features: DataFrame with features
        target_col: Column name for target
        horizon: Days ahead to predict
        test_size: Proportion of test set

    Returns:
        X_train, X_test, y_train, y_test
    """
    # Create target (price after 'horizon' days)
    y = features[target_col].shift(-horizon)

    # Remove target from features
    X = features.drop(columns=[target_col])

    # Remove rows with NaN in target
    valid_indices = ~y.isna()
    X = X[valid_indices]
    y = y[valid_indices]

    # Convert to numpy
    X = X.values
    y = y.values

    # Train/test split (time-based)
    split_idx = int(len(X) * (1 - test_size))
    X_train = X[:split_idx]
    X_test = X[split_idx:]
    y_train = y[:split_idx]
    y_test = y[split_idx:]

    return X_train, X_test, y_train, y_test
