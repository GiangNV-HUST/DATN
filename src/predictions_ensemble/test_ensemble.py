"""
Test Ensemble vs ARIMAX vs XGBoost vs MA
So sánh hiệu suất của tất cả models
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
from src.predictions_arima.arimax_predict import ARIMAXPredictor
from src.predictions_xgboost.xgboost_predict import XGBoostPredictor
from src.predictions_ensemble.ensemble_predict import EnsemblePredictor
from src.config import Config
import psycopg2

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class EnsembleTester:
    """Test và so sánh tất cả models"""

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
        Test 1 ticker với tất cả models

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

        # Test MA (Baseline)
        logger.info("🔵 Testing Moving Average...")
        ma_start = datetime.now()
        ma_pred = SimplePredictor.predict_3day_ma(df)
        ma_time = (datetime.now() - ma_start).total_seconds()

        if ma_pred:
            logger.info(f"✅ MA: {ma_pred}")
            logger.info(f"   Time: {ma_time:.3f}s\n")

        # Test ARIMAX
        logger.info("🟣 Testing ARIMAX...")
        arimax_start = datetime.now()
        arimax_result = ARIMAXPredictor.predict_with_confidence(df)
        arimax_time = (datetime.now() - arimax_start).total_seconds()

        if arimax_result:
            logger.info(f"✅ ARIMAX: {arimax_result['predictions']}")
            logger.info(f"   Order: ARIMAX{arimax_result['order']}")
            logger.info(f"   Time: {arimax_time:.3f}s\n")

        # Test XGBoost
        logger.info("🔵 Testing XGBoost...")
        xgb_start = datetime.now()
        xgb_result = XGBoostPredictor.predict_with_metrics(df)
        xgb_time = (datetime.now() - xgb_start).total_seconds()

        if xgb_result:
            logger.info(f"✅ XGBoost: {xgb_result['predictions']}")
            logger.info(f"   MAE: {xgb_result['mae']:.2f}")
            logger.info(f"   Time: {xgb_time:.3f}s\n")

        # Test Ensemble
        logger.info("🏆 Testing Ensemble (ARIMAX + XGBoost)...")
        ensemble_start = datetime.now()
        ensemble_result = EnsemblePredictor.predict_3day_ensemble(df)
        ensemble_time = (datetime.now() - ensemble_start).total_seconds()

        if ensemble_result:
            logger.info(f"✅ Ensemble: {ensemble_result['predictions']}")
            logger.info(f"   Weights: ARIMAX={ensemble_result['weights']['arimax']}, XGBoost={ensemble_result['weights']['xgboost']}")
            logger.info(f"   Time: {ensemble_time:.3f}s\n")

        # So sánh
        if ma_pred and arimax_result and xgb_result and ensemble_result:
            logger.info("📊 COMPARISON:")
            logger.info(f"   Last actual: {last_price:,.0f}đ\n")

            arimax_pred = arimax_result['predictions']
            xgb_pred = xgb_result['predictions']
            ensemble_pred = ensemble_result['predictions']

            for day in range(3):
                logger.info(f"   Day {day+1}:")
                logger.info(f"      MA:       {ma_pred[day]:,.2f}đ")
                logger.info(f"      ARIMAX:   {arimax_pred[day]:,.2f}đ")
                logger.info(f"      XGBoost:  {xgb_pred[day]:,.2f}đ")
                logger.info(f"      Ensemble: {ensemble_pred[day]:,.2f}đ")

                # Confidence Interval
                if ensemble_result.get('confidence_interval'):
                    ci = ensemble_result['confidence_interval']
                    logger.info(f"      95% CI:   [{ci['lower'][day]:,.2f}, {ci['upper'][day]:,.2f}]")

                logger.info("")

            logger.info("   Speed:")
            logger.info(f"      MA:       {ma_time:.3f}s")
            logger.info(f"      ARIMAX:   {arimax_time:.3f}s")
            logger.info(f"      XGBoost:  {xgb_time:.3f}s")
            logger.info(f"      Ensemble: {ensemble_time:.3f}s")

        return {
            'ticker': ticker,
            'last_price': last_price,
            'ma': {'predictions': ma_pred, 'time': ma_time},
            'arimax': {
                'predictions': arimax_pred if arimax_result else None,
                'time': arimax_time
            },
            'xgboost': {
                'predictions': xgb_pred if xgb_result else None,
                'time': xgb_time,
                'mae': xgb_result['mae'] if xgb_result else None
            },
            'ensemble': {
                'predictions': ensemble_pred if ensemble_result else None,
                'time': ensemble_time
            }
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
            arimax_times = [r['arimax']['time'] for r in results]
            xgb_times = [r['xgboost']['time'] for r in results]
            ensemble_times = [r['ensemble']['time'] for r in results]

            logger.info(f"Stocks tested: {len(results)}\n")
            logger.info(f"Average time:")
            logger.info(f"   MA:       {sum(ma_times)/len(ma_times):.3f}s")
            logger.info(f"   ARIMAX:   {sum(arimax_times)/len(arimax_times):.3f}s")
            logger.info(f"   XGBoost:  {sum(xgb_times)/len(xgb_times):.3f}s")
            logger.info(f"   Ensemble: {sum(ensemble_times)/len(ensemble_times):.3f}s\n")

            # Speed comparison
            avg_arimax = sum(arimax_times)/len(arimax_times)
            avg_xgb = sum(xgb_times)/len(xgb_times)
            avg_ensemble = sum(ensemble_times)/len(ensemble_times)

            logger.info(f"Speed Improvement:")
            logger.info(f"   XGBoost vs ARIMAX: {avg_arimax/avg_xgb:.1f}x faster")
            logger.info(f"   Ensemble vs ARIMAX: {avg_arimax/avg_ensemble:.1f}x")

            # XGBoost MAE
            xgb_maes = [r['xgboost']['mae'] for r in results if r['xgboost']['mae']]
            if xgb_maes:
                logger.info(f"\nXGBoost average MAE: {sum(xgb_maes)/len(xgb_maes):.2f}đ")

        return results


def main():
    """Main test function"""
    logger.info("\n🚀 Starting Ensemble Testing\n")

    tester = EnsembleTester()

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
