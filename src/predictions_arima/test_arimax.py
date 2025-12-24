"""
Test ARIMAX vs ARIMA vs MA
So sánh hiệu suất của 3 models
"""

import sys
import os
import pandas as pd
import logging
from datetime import datetime

# Fix encoding
if sys.platform == 'win32':
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

# Add parent directories to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.predictions.simple_predict import SimplePredictor
from src.predictions_arima.arima_predict import ARIMAPredictor
from src.predictions_arima.arimax_predict import ARIMAXPredictor
from src.config import Config
import psycopg2

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ARIMAXTester:
    """Test và so sánh 3 models"""

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
        """
        Lấy dữ liệu cổ phiếu với technical indicators

        Returns:
            DataFrame with columns: time, close, volume, rsi, macd_main, ma5, ma20
        """
        try:
            conn = self.get_connection()
            cur = conn.cursor()

            query = """
                SELECT time, close, volume, rsi, macd_main, ma5, ma20
                FROM stock.stock_prices_1d
                WHERE ticker = %s
                ORDER BY time DESC
                LIMIT %s
            """

            cur.execute(query, (ticker, days))
            rows = cur.fetchall()

            df = pd.DataFrame(rows, columns=[
                'time', 'close', 'volume', 'rsi', 'macd_main', 'ma5', 'ma20'
            ])
            df = df.sort_values('time')

            cur.close()
            conn.close()

            return df

        except Exception as e:
            logger.error(f"Error getting data for {ticker}: {e}")
            return None

    def test_single_ticker(self, ticker: str):
        """
        Test 1 ticker với cả 3 models

        Args:
            ticker: Mã cổ phiếu

        Returns:
            dict: Kết quả so sánh
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 Testing {ticker}")
        logger.info(f"{'='*60}\n")

        # Lấy data
        df = self.get_stock_data(ticker)

        if df is None or df.empty:
            logger.error(f"❌ No data for {ticker}")
            return None

        last_price = df['close'].iloc[-1]
        logger.info(f"✅ Loaded {len(df)} data points")
        logger.info(f"   Last price: {last_price:,.0f}đ")
        logger.info(f"   Date range: {df['time'].min()} to {df['time'].max()}\n")

        # Test MA
        logger.info("🔵 Testing Moving Average...")
        ma_start = datetime.now()
        ma_pred = SimplePredictor.predict_3day_ma(df)
        ma_time = (datetime.now() - ma_start).total_seconds()

        if ma_pred:
            logger.info(f"✅ MA: {ma_pred}")
            logger.info(f"   Time: {ma_time:.3f}s\n")

        # Test ARIMA
        logger.info("🟢 Testing ARIMA (no exogenous)...")
        arima_start = datetime.now()
        arima_pred = ARIMAPredictor.predict_3day_arima(df)
        arima_time = (datetime.now() - arima_start).total_seconds()

        if arima_pred:
            logger.info(f"✅ ARIMA: {arima_pred}")
            logger.info(f"   Time: {arima_time:.3f}s\n")

        # Test ARIMAX
        logger.info("🟣 Testing ARIMAX (with exogenous features)...")
        arimax_start = datetime.now()
        arimax_result = ARIMAXPredictor.predict_3day_arimax(df)
        arimax_time = (datetime.now() - arimax_start).total_seconds()

        if arimax_result:
            arimax_pred = arimax_result['predictions']
            logger.info(f"✅ ARIMAX: {arimax_pred}")
            logger.info(f"   Order: ARIMAX{arimax_result['order']}")
            logger.info(f"   Features: {', '.join(arimax_result['features_used'])}")
            logger.info(f"   Time: {arimax_time:.3f}s\n")

        # Test ARIMAX with confidence
        logger.info("🟣 Testing ARIMAX with Confidence Interval...")
        arimax_conf = ARIMAXPredictor.predict_with_confidence(df)

        if arimax_conf:
            logger.info(f"✅ ARIMAX with 95% CI:")
            logger.info(f"   Predictions: {arimax_conf['predictions']}")
            logger.info(f"   Lower bound: {arimax_conf['lower_bound']}")
            logger.info(f"   Upper bound: {arimax_conf['upper_bound']}\n")

        # So sánh
        if ma_pred and arima_pred and arimax_result:
            logger.info("📊 COMPARISON:")
            logger.info(f"   Last actual: {last_price:,.0f}đ\n")

            for day in range(3):
                logger.info(f"   Day {day+1}:")
                logger.info(f"      MA:     {ma_pred[day]:,.2f}đ")
                logger.info(f"      ARIMA:  {arima_pred[day]:,.2f}đ")
                logger.info(f"      ARIMAX: {arimax_pred[day]:,.2f}đ")

                # Differences
                ma_diff = ma_pred[day] - last_price
                arima_diff = arima_pred[day] - last_price
                arimax_diff = arimax_pred[day] - last_price

                logger.info(f"      Changes: MA={ma_diff:+.2f}, ARIMA={arima_diff:+.2f}, ARIMAX={arimax_diff:+.2f}")
                logger.info("")

            logger.info("   Speed:")
            logger.info(f"      MA:     {ma_time:.3f}s")
            logger.info(f"      ARIMA:  {arima_time:.3f}s")
            logger.info(f"      ARIMAX: {arimax_time:.3f}s")

        return {
            'ticker': ticker,
            'last_price': last_price,
            'ma': {'predictions': ma_pred, 'time': ma_time},
            'arima': {'predictions': arima_pred, 'time': arima_time},
            'arimax': {
                'predictions': arimax_pred,
                'time': arimax_time,
                'features': arimax_result['features_used'],
                'order': arimax_result['order']
            },
            'confidence': arimax_conf
        }

    def batch_test(self, tickers: list):
        """Test nhiều tickers"""
        logger.info(f"\n{'='*60}")
        logger.info(f"🧪 BATCH TESTING: {len(tickers)} stocks")
        logger.info(f"{'='*60}\n")

        results = []

        for ticker in tickers:
            result = self.test_single_ticker(ticker)
            if result:
                results.append(result)

        # Summary
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 SUMMARY")
        logger.info(f"{'='*60}\n")

        if results:
            ma_times = [r['ma']['time'] for r in results]
            arima_times = [r['arima']['time'] for r in results]
            arimax_times = [r['arimax']['time'] for r in results]

            logger.info(f"Stocks tested: {len(results)}\n")
            logger.info(f"Average time:")
            logger.info(f"   MA:     {sum(ma_times)/len(ma_times):.3f}s")
            logger.info(f"   ARIMA:  {sum(arima_times)/len(arima_times):.3f}s")
            logger.info(f"   ARIMAX: {sum(arimax_times)/len(arimax_times):.3f}s\n")

            # Tính độ chênh lệch trung bình
            total_diff_arima_ma = 0
            total_diff_arimax_ma = 0
            count = 0

            for r in results:
                for i in range(3):
                    ma_p = r['ma']['predictions'][i]
                    arima_p = r['arima']['predictions'][i]
                    arimax_p = r['arimax']['predictions'][i]

                    total_diff_arima_ma += abs(arima_p - ma_p)
                    total_diff_arimax_ma += abs(arimax_p - ma_p)
                    count += 1

            avg_diff_arima = total_diff_arima_ma / count
            avg_diff_arimax = total_diff_arimax_ma / count

            logger.info(f"Average prediction differences:")
            logger.info(f"   |ARIMA - MA|:  {avg_diff_arima:.2f}đ")
            logger.info(f"   |ARIMAX - MA|: {avg_diff_arimax:.2f}đ\n")

            # Features được sử dụng
            all_features = set()
            for r in results:
                all_features.update(r['arimax']['features'])

            logger.info(f"Exogenous features used: {', '.join(all_features)}")

        return results


def main():
    """Main test function"""
    logger.info("\n🚀 Starting ARIMAX Testing\n")

    tester = ARIMAXTester()

    # Test single stock
    test_ticker = "VCB"
    logger.info(f"Testing single stock: {test_ticker}")
    result = tester.test_single_ticker(test_ticker)

    # Test batch
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
