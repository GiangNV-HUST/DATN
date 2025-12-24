"""
Example: Sử dụng ARIMA Predictor
Demo đơn giản để test ARIMA predictions
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Fix encoding for Windows console
if sys.platform == 'win32':
    import locale
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

# Add parent directories to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.predictions_arima.arima_predict import ARIMAPredictor


def example_1_basic():
    """Example 1: Dự đoán cơ bản với sample data"""
    print("\n" + "="*60)
    print("Example 1: Basic ARIMA Prediction")
    print("="*60 + "\n")

    # Tạo sample data (giả lập giá VCB)
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', periods=60, freq='D')

    # Giả lập giá cổ phiếu với trend tăng nhẹ + noise
    base_price = 95000
    trend = np.linspace(0, 5000, 60)
    noise = np.random.normal(0, 1000, 60)
    prices = base_price + trend + noise

    df = pd.DataFrame({
        'time': dates,
        'close': prices
    })

    print(f"📊 Sample data:")
    print(f"   Total points: {len(df)}")
    print(f"   Date range: {df['time'].min()} to {df['time'].max()}")
    print(f"   Last 5 prices:")
    print(df[['time', 'close']].tail().to_string(index=False))
    print()

    # Dự đoán 3 ngày
    print("🔮 Predicting next 3 days...")
    predictions = ARIMAPredictor.predict_3day_arima(df)

    if predictions:
        print(f"\n✅ Predictions:")
        print(f"   Day 1: {predictions[0]:,.2f}đ")
        print(f"   Day 2: {predictions[1]:,.2f}đ")
        print(f"   Day 3: {predictions[2]:,.2f}đ")
        print(f"\n   Last actual: {df['close'].iloc[-1]:,.2f}đ")
        print(f"   Change Day 1: {((predictions[0]/df['close'].iloc[-1])-1)*100:+.2f}%")
    else:
        print("❌ Prediction failed")


def example_2_confidence_interval():
    """Example 2: Dự đoán với confidence interval"""
    print("\n" + "="*60)
    print("Example 2: Prediction with Confidence Interval")
    print("="*60 + "\n")

    # Sample data
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', periods=60, freq='D')
    base_price = 95000
    trend = np.linspace(0, 5000, 60)
    noise = np.random.normal(0, 1000, 60)
    prices = base_price + trend + noise

    df = pd.DataFrame({
        'time': dates,
        'close': prices
    })

    print("🔮 Predicting with 95% confidence interval...")
    result = ARIMAPredictor.predict_with_confidence(df, confidence=0.95)

    if result:
        print(f"\n✅ ARIMA{result['order']} Results:")
        print(f"\n   Predictions:")
        for i in range(3):
            print(f"   Day {i+1}: {result['predictions'][i]:,.2f}đ")
            print(f"      95% CI: [{result['lower_bound'][i]:,.2f}, {result['upper_bound'][i]:,.2f}]")
            print()


def example_3_comparison():
    """Example 3: So sánh nhiều scenarios"""
    print("\n" + "="*60)
    print("Example 3: Comparing Different Scenarios")
    print("="*60 + "\n")

    scenarios = {
        "Uptrend": (95000, 5000, 500),    # base, trend, noise
        "Downtrend": (95000, -3000, 500),
        "Sideways": (95000, 0, 1000)
    }

    for name, (base, trend_value, noise_std) in scenarios.items():
        print(f"\n📊 Scenario: {name}")
        print("-" * 40)

        np.random.seed(42)
        dates = pd.date_range(start='2024-01-01', periods=60, freq='D')
        trend = np.linspace(0, trend_value, 60)
        noise = np.random.normal(0, noise_std, 60)
        prices = base + trend + noise

        df = pd.DataFrame({
            'time': dates,
            'close': prices
        })

        predictions = ARIMAPredictor.predict_3day_arima(df)

        if predictions:
            last_price = df['close'].iloc[-1]
            print(f"   Last price: {last_price:,.2f}đ")
            print(f"   Predictions: {[f'{p:,.0f}đ' for p in predictions]}")
            print(f"   Trend: {((predictions[0]/last_price)-1)*100:+.2f}%")
        else:
            print("   ❌ Prediction failed")


def example_4_48day():
    """Example 4: Dự đoán dài hạn 48 ngày"""
    print("\n" + "="*60)
    print("Example 4: Long-term 48-day Prediction")
    print("="*60 + "\n")

    # Sample data với nhiều điểm hơn
    np.random.seed(42)
    dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
    base_price = 90000
    trend = np.linspace(0, 10000, 100)
    noise = np.random.normal(0, 1000, 100)
    prices = base_price + trend + noise

    df = pd.DataFrame({
        'time': dates,
        'close': prices
    })

    print(f"📊 Training data: {len(df)} days")
    print(f"   Last price: {df['close'].iloc[-1]:,.2f}đ")
    print()

    print("🔮 Predicting next 48 days...")
    predictions_48d = ARIMAPredictor.predict_48day_arima(df)

    if predictions_48d:
        print(f"\n✅ 48-day predictions generated")
        print(f"   First week (days 1-7):")
        for i in range(7):
            print(f"      Day {i+1}: {predictions_48d[i]:,.2f}đ")
        print(f"   ...")
        print(f"   Last week (days 42-48):")
        for i in range(42, 48):
            print(f"      Day {i+1}: {predictions_48d[i]:,.2f}đ")

        last_pred = predictions_48d[-1]
        last_actual = df['close'].iloc[-1]
        print(f"\n   48-day change: {((last_pred/last_actual)-1)*100:+.2f}%")
    else:
        print("❌ Prediction failed")


def main():
    """Run all examples"""
    print("\n" + "="*60)
    print("🚀 ARIMA PREDICTOR - USAGE EXAMPLES")
    print("="*60)

    try:
        example_1_basic()
        example_2_confidence_interval()
        example_3_comparison()
        example_4_48day()

        print("\n" + "="*60)
        print("✅ All examples completed!")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
