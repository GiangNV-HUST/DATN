"""
Test và so sánh ARIMA vs Moving Average
"""

import sys
import os
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta

# Add parent directories to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.predictions.simple_predict import SimplePredictor
from src.predictions_arima.arima_predict import ARIMAPredictor
from src.config import Config
import psycopg2

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ComparisonTest:
    """So sánh ARIMA vs MA"""

    def __init__(self):
        self.db_config = {
            "host": Config.DB_HOST,
            "port": Config.DB_PORT,
            "database": Config.DB_NAME,
            "user": Config.DB_USER,
            "password": Config.DB_PASSWORD,
        }

    def get_connection(self):
        """Tạo database connection"""
        return psycopg2.connect(**self.db_config)

    def get_stock_data(self, ticker: str, days: int = 100):
        """Lấy dữ liệu cổ phiếu từ database"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()

            query = """
                SELECT time, close
                FROM stock.stock_prices_1d
                WHERE ticker = %s
                ORDER BY time DESC
                LIMIT %s
            """

            cur.execute(query, (ticker, days))
            rows = cur.fetchall()

            df = pd.DataFrame(rows, columns=['time', 'close'])
            df = df.sort_values('time')  # Sắp xếp theo thời gian tăng dần

            cur.close()
            conn.close()

            return df

        except Exception as e:
            logger.error(f"Error getting stock data: {e}")
            return None

    def compare_predictions(self, ticker: str):
        """
        So sánh dự đoán ARIMA vs MA cho 1 cổ phiếu

        Args:
            ticker: Mã cổ phiếu

        Returns:
            dict: Kết quả so sánh
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 Testing predictions for {ticker}")
        logger.info(f"{'='*60}\n")

        # Lấy data
        df = self.get_stock_data(ticker, days=100)

        if df is None or df.empty:
            logger.error(f"❌ No data found for {ticker}")
            return None

        logger.info(f"✅ Loaded {len(df)} data points for {ticker}")
        logger.info(f"   Last price: {df['close'].iloc[-1]:,.0f}đ")
        logger.info(f"   Date range: {df['time'].min()} to {df['time'].max()}\n")

        # Test MA prediction
        logger.info("🔵 Testing Moving Average...")
        ma_start = datetime.now()
        ma_predictions = SimplePredictor.predict_3day_ma(df)
        ma_time = (datetime.now() - ma_start).total_seconds()

        if ma_predictions:
            logger.info(f"✅ MA Predictions: {ma_predictions}")
            logger.info(f"   Time: {ma_time:.3f}s\n")
        else:
            logger.error("❌ MA prediction failed\n")

        # Test ARIMA prediction
        logger.info("🟢 Testing ARIMA...")
        arima_start = datetime.now()
        arima_predictions = ARIMAPredictor.predict_3day_arima(df)
        arima_time = (datetime.now() - arima_start).total_seconds()

        if arima_predictions:
            logger.info(f"✅ ARIMA Predictions: {arima_predictions}")
            logger.info(f"   Time: {arima_time:.3f}s\n")
        else:
            logger.error("❌ ARIMA prediction failed\n")

        # Test ARIMA with confidence interval
        logger.info("🟢 Testing ARIMA with Confidence Interval...")
        arima_conf = ARIMAPredictor.predict_with_confidence(df)

        if arima_conf:
            logger.info(f"✅ ARIMA with 95% Confidence:")
            logger.info(f"   Predictions: {arima_conf['predictions']}")
            logger.info(f"   Lower bound: {arima_conf['lower_bound']}")
            logger.info(f"   Upper bound: {arima_conf['upper_bound']}")
            logger.info(f"   Order: ARIMA{arima_conf['order']}\n")
        else:
            logger.error("❌ ARIMA confidence prediction failed\n")

        # So sánh kết quả
        if ma_predictions and arima_predictions:
            logger.info("📈 Comparison:")
            logger.info(f"   Last actual price: {df['close'].iloc[-1]:,.0f}đ")
            logger.info(f"")
            logger.info(f"   Day 1:")
            logger.info(f"      MA:    {ma_predictions[0]:,.0f}đ")
            logger.info(f"      ARIMA: {arima_predictions[0]:,.0f}đ")
            logger.info(f"      Diff:  {abs(ma_predictions[0] - arima_predictions[0]):,.0f}đ")
            logger.info(f"")
            logger.info(f"   Day 2:")
            logger.info(f"      MA:    {ma_predictions[1]:,.0f}đ")
            logger.info(f"      ARIMA: {arima_predictions[1]:,.0f}đ")
            logger.info(f"      Diff:  {abs(ma_predictions[1] - arima_predictions[1]):,.0f}đ")
            logger.info(f"")
            logger.info(f"   Day 3:")
            logger.info(f"      MA:    {ma_predictions[2]:,.0f}đ")
            logger.info(f"      ARIMA: {arima_predictions[2]:,.0f}đ")
            logger.info(f"      Diff:  {abs(ma_predictions[2] - arima_predictions[2]):,.0f}đ")
            logger.info(f"")
            logger.info(f"   Speed:")
            logger.info(f"      MA:    {ma_time:.3f}s")
            logger.info(f"      ARIMA: {arima_time:.3f}s")

        return {
            'ticker': ticker,
            'ma_predictions': ma_predictions,
            'ma_time': ma_time,
            'arima_predictions': arima_predictions,
            'arima_time': arima_time,
            'arima_confidence': arima_conf,
            'last_price': float(df['close'].iloc[-1])
        }

    def batch_test(self, tickers: list):
        """
        Test nhiều cổ phiếu cùng lúc

        Args:
            tickers: Danh sách mã cổ phiếu
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"🧪 BATCH TESTING: {len(tickers)} stocks")
        logger.info(f"{'='*60}\n")

        results = []

        for ticker in tickers:
            result = self.compare_predictions(ticker)
            if result:
                results.append(result)

        # Summary
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 SUMMARY")
        logger.info(f"{'='*60}\n")

        ma_times = [r['ma_time'] for r in results if r.get('ma_time')]
        arima_times = [r['arima_time'] for r in results if r.get('arima_time')]

        logger.info(f"Total stocks tested: {len(results)}")
        logger.info(f"")
        logger.info(f"Average prediction time:")
        logger.info(f"   MA:    {np.mean(ma_times):.3f}s")
        logger.info(f"   ARIMA: {np.mean(arima_times):.3f}s")
        logger.info(f"")
        logger.info(f"Speed comparison: MA is {np.mean(ma_times)/np.mean(arima_times):.1f}x faster")

        return results


def main():
    """Main test function"""
    logger.info("🚀 Starting ARIMA vs MA Comparison Test\n")

    tester = ComparisonTest()

    # Test với 1 cổ phiếu trước
    test_ticker = "VCB"
    logger.info(f"Testing single stock: {test_ticker}")
    result = tester.compare_predictions(test_ticker)

    # Test batch với nhiều cổ phiếu
    test_tickers = ["VCB", "VNM", "FPT", "TCB", "HPG"]
    logger.info(f"\nTesting batch: {', '.join(test_tickers)}")
    batch_results = tester.batch_test(test_tickers)

    logger.info("\n✅ All tests completed!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n👋 Test stopped by user")
    except Exception as e:
        logger.error(f"❌ Test error: {e}", exc_info=True)
