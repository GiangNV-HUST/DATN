import logging
from datetime import datetime
from src.data_collector.vnstock_client import VnStockClient
from src.indicators.technical_indicators import TechnicalIndicators
from src.database.data_saver import DataSaver

# Setup Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Main Function - Thu thập và xử lý data"""

    # Danh sách cổ phiếu cần crawl
    tickers = ["VNM", "VCB", "HPG", "VHM", "VIC"]

    # Khởi tạo
    client = VnStockClient()
    saver = DataSaver()

    logger.info("Starting data colection...")

    for ticker in tickers:
        logger.info(f"\n{'='*50}")
        logger.info(f"Processing: {ticker}")
        logger.info(f"{'='*50}")

        try:
            # 1. Lấy dữ liệu ngày (150 ngày gần nhất)
            logger.info(f"Fetching daily data for {ticker}...")
            df_daily = client.get_daily_data(ticker)
            if df_daily is None or df_daily.empty:
                logger.warning(f"No daily data for {ticker}, skiping...")
                continue

            # 2. Tính toán indicators
            logger.info(f"Calculating indicators for {ticker}...")
            df_with_indicators = TechnicalIndicators.calculate_all(df_daily)

            # 3. Lưu vào database
            logger.info(f"Saving to database...")
            saver.save_1d_data(ticker, df_with_indicators)

            logger.info(f"✅ Completed {ticker}")

        except Exception as e:
            logger.error(f"Error processing {ticker}: {e}")
            continue

    # Đóng kết nối
    saver.close()
    logger.info("\n Data colection completed!")


if __name__ == "__main__":
    main()
