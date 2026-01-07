"""
Training script for Ensemble 5-Model

Usage:
    python scripts/train_ensemble.py --ticker VCB --horizon 3
    python scripts/train_ensemble.py --ticker VIC --horizon 48
    python scripts/train_ensemble.py --all  # Train for all VN30 stocks
"""

import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

import argparse
import pandas as pd
import numpy as np
from datetime import datetime

from prediction.ensemble_stacking import EnsembleStacking
from prediction.utils.feature_engineering import create_features, prepare_training_data


# VN30 stocks
VN30_STOCKS = [
    'ACB', 'BCM', 'BID', 'BVH', 'CTG', 'FPT', 'GAS', 'GVR', 'HDB',
    'HPG', 'LPB', 'MBB', 'MSN', 'MWG', 'PLX', 'SAB', 'SHB', 'SSB',
    'SSI', 'STB', 'TCB', 'TPB', 'VCB', 'VHM', 'VIB', 'VIC', 'VJC',
    'VNM', 'VPB', 'VRE'
]


def load_stock_data(ticker: str, start_date: str = '2015-01-01') -> pd.DataFrame:
    """
    Load stock data from database or CSV

    Args:
        ticker: Stock ticker
        start_date: Start date

    Returns:
        DataFrame with OHLCV data
    """
    # TODO: Replace with actual database query
    # For now, generate dummy data for demonstration
    print(f"Loading data for {ticker}...")

    # This should be replaced with:
    # df = pd.read_sql(f"SELECT * FROM stock_prices WHERE ticker='{ticker}'", conn)

    # Dummy data for demo
    dates = pd.date_range(start=start_date, end='2024-12-31', freq='D')
    n = len(dates)

    df = pd.DataFrame({
        'date': dates,
        'open': np.random.randn(n).cumsum() + 100,
        'high': np.random.randn(n).cumsum() + 102,
        'low': np.random.randn(n).cumsum() + 98,
        'close': np.random.randn(n).cumsum() + 100,
        'volume': np.random.randint(100000, 10000000, n)
    })

    df['close'] = df['close'].abs()  # Ensure positive
    df.set_index('date', inplace=True)

    print(f"✓ Loaded {len(df)} days of data")
    return df


def train_for_ticker(ticker: str, horizon: int = 3, save_dir: str = 'src/prediction/trained_models'):
    """
    Train ensemble for a specific ticker

    Args:
        ticker: Stock ticker
        horizon: Days ahead to predict (3 or 48)
        save_dir: Directory to save models
    """
    print("\n" + "=" * 70)
    print(f"TRAINING ENSEMBLE FOR {ticker} - {horizon}-DAY FORECAST")
    print("=" * 70)

    # Step 1: Load data
    df = load_stock_data(ticker)

    # Step 2: Create features
    print("\nCreating features...")
    features = create_features(df)
    print(f"✓ Created {len(features.columns)} features")

    # Step 3: Prepare training data
    print(f"\nPreparing training data (horizon={horizon} days)...")
    X_train, X_test, y_train, y_test = prepare_training_data(
        features,
        target_col='close',
        horizon=horizon,
        test_size=0.2
    )
    print(f"✓ Train: {len(X_train)} samples")
    print(f"✓ Test:  {len(X_test)} samples")

    # Step 4: Train ensemble
    print("\nTraining Ensemble Stacking...")
    ensemble = EnsembleStacking(n_folds=5)
    ensemble.fit(X_train, y_train)

    # Step 5: Evaluate on test set
    print("\n" + "=" * 70)
    print("TEST SET EVALUATION")
    print("=" * 70)

    y_pred = ensemble.predict(X_test)

    from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, r2_score

    test_mae = mean_absolute_error(y_test, y_pred)
    test_mape = mean_absolute_percentage_error(y_test, y_pred)
    test_r2 = r2_score(y_test, y_pred)

    print(f"Test MAPE: {test_mape * 100:.2f}%")
    print(f"Test MAE:  {test_mae:.4f}")
    print(f"Test R²:   {test_r2:.4f}")

    # Step 6: Save model
    save_path = Path(save_dir) / f"{ticker}_{horizon}day_ensemble.pkl"
    ensemble.save(str(save_path))

    # Step 7: Save metrics summary
    metrics_df = ensemble.get_metrics_summary()
    if metrics_df is not None:
        metrics_df['test_mape'] = test_mape * 100
        metrics_df['test_r2'] = test_r2

        csv_path = Path(save_dir) / f"{ticker}_{horizon}day_metrics.csv"
        metrics_df.to_csv(csv_path)
        print(f"\n✓ Metrics saved to {csv_path}")

    print(f"\n✅ Training completed for {ticker} ({horizon}-day forecast)")
    print(f"Model saved to: {save_path}")

    return ensemble, metrics_df


def main():
    parser = argparse.ArgumentParser(description='Train Ensemble 5-Model for stock prediction')
    parser.add_argument('--ticker', type=str, help='Stock ticker (e.g., VCB, VIC)')
    parser.add_argument('--horizon', type=int, default=3, choices=[3, 48],
                        help='Forecast horizon: 3 or 48 days')
    parser.add_argument('--all', action='store_true', help='Train for all VN30 stocks')
    parser.add_argument('--save-dir', type=str, default='src/prediction/trained_models',
                        help='Directory to save models')

    args = parser.parse_args()

    if args.all:
        # Train for all VN30 stocks
        print("\n" + "=" * 70)
        print(f"TRAINING FOR ALL VN30 STOCKS ({len(VN30_STOCKS)} stocks)")
        print("=" * 70)

        results = {}
        for i, ticker in enumerate(VN30_STOCKS, 1):
            print(f"\n[{i}/{len(VN30_STOCKS)}] Processing {ticker}...")
            try:
                ensemble, metrics = train_for_ticker(ticker, args.horizon, args.save_dir)
                results[ticker] = metrics
            except Exception as e:
                print(f"✗ Error training {ticker}: {e}")
                continue

        # Summary
        print("\n" + "=" * 70)
        print("TRAINING SUMMARY")
        print("=" * 70)
        print(f"Successfully trained: {len(results)}/{len(VN30_STOCKS)} stocks")

    elif args.ticker:
        # Train for single ticker
        train_for_ticker(args.ticker, args.horizon, args.save_dir)

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
