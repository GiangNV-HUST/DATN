"""
Migration Script: Chuyển từ Moving Average sang ARIMA
Cập nhật predictions trong database sử dụng ARIMA thay vì MA
"""

import sys
import os
import pandas as pd
import psycopg2
from datetime import datetime
import logging

# Add parent directories to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.predictions_arima.arima_predict import ARIMAPredictor
from src.config import Config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ARIMAPredictionMigrator:
    """Migrate predictions to ARIMA"""

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

    def get_all_tickers(self):
        """Lấy danh sách tất cả ticker"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()

            cur.execute("""
                SELECT DISTINCT ticker
                FROM stock.stock_prices_1d
                ORDER BY ticker
            """)

            tickers = [row[0] for row in cur.fetchall()]

            cur.close()
            conn.close()

            return tickers

        except Exception as e:
            logger.error(f"Error getting tickers: {e}")
            return []

    def get_stock_data(self, ticker: str, days: int = 60):
        """Lấy dữ liệu cổ phiếu"""
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
            df = df.sort_values('time')

            cur.close()
            conn.close()

            return df

        except Exception as e:
            logger.error(f"Error getting data for {ticker}: {e}")
            return None

    def update_predictions(self, ticker: str, predictions: list):
        """
        Cập nhật predictions vào database

        Args:
            ticker: Mã cổ phiếu
            predictions: [day1, day2, day3]
        """
        try:
            conn = self.get_connection()
            cur = conn.cursor()

            # Xóa prediction cũ (nếu có)
            cur.execute("""
                DELETE FROM stock.stock_prices_3d_predict
                WHERE ticker = %s
            """, (ticker,))

            # Insert prediction mới
            now = datetime.now()
            cur.execute("""
                INSERT INTO stock.stock_prices_3d_predict
                (ticker, time, close_next_1, close_next_2, close_next_3)
                VALUES (%s, %s, %s, %s, %s)
            """, (ticker, now, predictions[0], predictions[1], predictions[2]))

            conn.commit()
            cur.close()
            conn.close()

            logger.info(f"✅ Updated predictions for {ticker}: {predictions}")
            return True

        except Exception as e:
            logger.error(f"Error updating predictions for {ticker}: {e}")
            return False

    def migrate_single_ticker(self, ticker: str):
        """
        Migrate predictions cho 1 ticker

        Args:
            ticker: Mã cổ phiếu

        Returns:
            bool: Success or not
        """
        try:
            logger.info(f"🔄 Processing {ticker}...")

            # Lấy data
            df = self.get_stock_data(ticker)

            if df is None or df.empty:
                logger.warning(f"⚠️ No data for {ticker}")
                return False

            # Dự đoán bằng ARIMA
            predictions = ARIMAPredictor.predict_3day_arima(df)

            if predictions is None:
                logger.warning(f"⚠️ Could not predict for {ticker}")
                return False

            # Update database
            success = self.update_predictions(ticker, predictions)

            return success

        except Exception as e:
            logger.error(f"❌ Error migrating {ticker}: {e}")
            return False

    def migrate_all(self, limit: int = None):
        """
        Migrate predictions cho tất cả tickers

        Args:
            limit: Giới hạn số lượng tickers (None = all)
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"🚀 Starting ARIMA Migration")
        logger.info(f"{'='*60}\n")

        # Lấy danh sách tickers
        tickers = self.get_all_tickers()

        if limit:
            tickers = tickers[:limit]

        logger.info(f"📊 Found {len(tickers)} tickers to process\n")

        # Process từng ticker
        success_count = 0
        failed_count = 0

        for i, ticker in enumerate(tickers, 1):
            logger.info(f"[{i}/{len(tickers)}] {ticker}")

            success = self.migrate_single_ticker(ticker)

            if success:
                success_count += 1
            else:
                failed_count += 1

            logger.info("")  # Empty line for readability

        # Summary
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 MIGRATION SUMMARY")
        logger.info(f"{'='*60}\n")
        logger.info(f"Total tickers: {len(tickers)}")
        logger.info(f"✅ Success: {success_count}")
        logger.info(f"❌ Failed: {failed_count}")
        logger.info(f"Success rate: {success_count/len(tickers)*100:.1f}%")


def main():
    """Main migration function"""
    import argparse

    parser = argparse.ArgumentParser(description="Migrate predictions to ARIMA")
    parser.add_argument("--ticker", type=str, help="Migrate single ticker")
    parser.add_argument("--limit", type=int, help="Limit number of tickers")
    parser.add_argument("--all", action="store_true", help="Migrate all tickers")

    args = parser.parse_args()

    migrator = ARIMAPredictionMigrator()

    if args.ticker:
        # Migrate single ticker
        logger.info(f"🎯 Migrating single ticker: {args.ticker}\n")
        migrator.migrate_single_ticker(args.ticker)

    elif args.all or args.limit:
        # Migrate all or limited
        migrator.migrate_all(limit=args.limit)

    else:
        # Default: migrate 5 tickers for testing
        logger.info("🧪 Test mode: Migrating 5 tickers\n")
        migrator.migrate_all(limit=5)

    logger.info("\n✅ Migration completed!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\n👋 Migration stopped by user")
    except Exception as e:
        logger.error(f"❌ Migration error: {e}", exc_info=True)
