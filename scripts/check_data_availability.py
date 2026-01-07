"""
Script to check data availability for training ensemble models

This helps you determine:
1. How many days of data you have per ticker
2. Which tickers are ready for training
3. Recommended training parameters based on data length
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

import pandas as pd
from datetime import datetime, timedelta

# Import your database connection
# from database.connection import get_connection


VN30_STOCKS = [
    'ACB', 'BCM', 'BID', 'BVH', 'CTG', 'FPT', 'GAS', 'GVR', 'HDB',
    'HPG', 'LPB', 'MBB', 'MSN', 'MWG', 'PLX', 'SAB', 'SHB', 'SSB',
    'SSI', 'STB', 'TCB', 'TPB', 'VCB', 'VHM', 'VIB', 'VIC', 'VJC',
    'VNM', 'VPB', 'VRE'
]


def check_data_availability():
    """Check data availability for all VN30 stocks"""

    print("=" * 80)
    print("📊 STOCK DATA AVAILABILITY CHECKER")
    print("=" * 80)

    # TODO: Replace with actual database query
    # conn = get_connection()

    query = """
    SELECT
        ticker,
        MIN(time) as earliest_date,
        MAX(time) as latest_date,
        COUNT(*) as total_days,
        COUNT(*) / 365.0 as years_of_data
    FROM stock_prices
    WHERE ticker IN ({tickers})
    GROUP BY ticker
    ORDER BY total_days DESC
    """

    # Format ticker list for SQL
    ticker_list = "'" + "','".join(VN30_STOCKS) + "'"
    query = query.format(tickers=ticker_list)

    print("\n⚠️  NOTE: Replace database connection with your actual connection")
    print(f"Query to run:\n{query}\n")

    # Example results (replace with actual query)
    # df = pd.read_sql(query, conn)

    # For demo, simulate results
    print("📋 Data Availability Summary:\n")
    print("=" * 80)
    print(f"{'Ticker':<8} {'Days':<8} {'Years':<8} {'Start Date':<12} {'End Date':<12} {'Recommendation'}")
    print("=" * 80)

    # Simulate some example data
    examples = [
        ('VCB', 1500, '2019-01-01', '2024-12-31', '✅ EXCELLENT - Ready for all'),
        ('VHM', 1200, '2019-06-01', '2024-12-31', '✅ GOOD - Ready for 3d & 48d'),
        ('HPG', 800, '2021-01-01', '2024-12-31', '⚠️  OK - Only 3d recommended'),
        ('VIC', 500, '2022-07-01', '2024-12-31', '⚠️  MINIMUM - 3d only, risky'),
        ('VNM', 300, '2023-03-01', '2024-12-31', '❌ INSUFFICIENT - Need more data'),
    ]

    for ticker, days, start, end, rec in examples:
        years = days / 365.0
        print(f"{ticker:<8} {days:<8} {years:<8.2f} {start:<12} {end:<12} {rec}")

    print("=" * 80)

    print("\n📊 RECOMMENDATIONS:\n")
    print("Data Length          | Recommendation")
    print("-" * 80)
    print("< 300 days          | ❌ DO NOT TRAIN - Insufficient data")
    print("300-500 days        | ⚠️  3-day only, expect lower accuracy")
    print("500-1000 days       | ✅ 3-day GOOD, 48-day OK")
    print("1000-1500 days      | ✅ EXCELLENT - Both 3d & 48d")
    print("> 1500 days         | ✅ OPTIMAL - Full ensemble capability")

    print("\n🎯 TRAINING STRATEGY:\n")
    print("1. Priority 1 (>1000 days):")
    print("   - Train both 3-day and 48-day forecasts")
    print("   - Use default parameters (5-fold CV)")
    print("   - Expect best accuracy")

    print("\n2. Priority 2 (500-1000 days):")
    print("   - Train 3-day first (higher priority)")
    print("   - Train 48-day with caution")
    print("   - Consider using 3-fold CV instead of 5-fold")

    print("\n3. Priority 3 (300-500 days):")
    print("   - Only train 3-day forecast")
    print("   - Use 3-fold CV")
    print("   - Accept lower accuracy")
    print("   - Consider simpler models (Prophet, LightGBM only)")

    print("\n4. Skip (<300 days):")
    print("   - Do not train ensemble")
    print("   - Collect more data first")
    print("   - Or use simple moving average fallback")

    print("\n🔧 PARAMETER ADJUSTMENTS:\n")
    print("Based on data length, adjust training parameters:")
    print("")
    print("# For 300-500 days:")
    print("ensemble = EnsembleStacking(n_folds=3)  # Reduce from 5 to 3")
    print("")
    print("# For 500-1000 days:")
    print("ensemble = EnsembleStacking(n_folds=4)  # Use 4 folds")
    print("")
    print("# For >1000 days:")
    print("ensemble = EnsembleStacking(n_folds=5)  # Default")

    print("\n" + "=" * 80)

    return


def get_training_recommendations(days: int) -> dict:
    """
    Get training recommendations based on data length

    Args:
        days: Number of days of historical data

    Returns:
        Dictionary with recommendations
    """
    if days < 300:
        return {
            "status": "insufficient",
            "train_3day": False,
            "train_48day": False,
            "n_folds": 3,
            "message": "❌ Insufficient data. Need at least 300 days. Collect more data first.",
            "fallback": "Use simple moving average or Prophet with minimal features"
        }
    elif days < 500:
        return {
            "status": "minimum",
            "train_3day": True,
            "train_48day": False,
            "n_folds": 3,
            "message": "⚠️ Minimum data. Only train 3-day forecast. Expect lower accuracy.",
            "expected_mape_3d": "1.5-2.5%",
            "test_size": 0.15  # Use smaller test set
        }
    elif days < 1000:
        return {
            "status": "good",
            "train_3day": True,
            "train_48day": True,
            "n_folds": 4,
            "message": "✅ Good data length. Can train both horizons.",
            "expected_mape_3d": "1.0-1.5%",
            "expected_mape_48d": "3.0-4.0%",
            "test_size": 0.2
        }
    else:  # >= 1000
        return {
            "status": "excellent",
            "train_3day": True,
            "train_48day": True,
            "n_folds": 5,
            "message": "✅ Excellent data length. Full ensemble capability.",
            "expected_mape_3d": "0.8-1.2%",
            "expected_mape_48d": "2.5-3.5%",
            "test_size": 0.2
        }


if __name__ == "__main__":
    check_data_availability()

    print("\n\n🧪 EXAMPLE USAGE:\n")
    print("from check_data_availability import get_training_recommendations")
    print("")
    print("# Check if ticker has enough data")
    print("rec = get_training_recommendations(days=1200)")
    print("print(rec)")
    print("")
    print("if rec['train_3day']:")
    print("    print(f\"Training 3-day with {rec['n_folds']} folds\")")
    print("    # ensemble = EnsembleStacking(n_folds=rec['n_folds'])")
