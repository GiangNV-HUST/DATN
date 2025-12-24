"""Test Kafka Producer"""

import logging
import sys
import os

# Fix encoding for Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.kafka_producer.producer import StockDataProducer
from src.data_collector.vnstock_client import VnStockClient

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def test_producer():
    """Test gửi data vào kafka"""

    # 1. Khởi tạo
    logger.info("Starting Kafka Producer test...")
    client = VnStockClient()
    producer = StockDataProducer()

    # 2. Lấy data
    tickers = ["VNM", "VCB", "HPG", "VHM", "VIC","FPT", "MSN", "MWG", "VRE", "GAS","TCB", "BID", "CTG", "VPB", "POW"]

    for ticker in tickers:
        logger.info(f"\n{'='*50}")
        logger.info(f"Processing: {ticker}")

        # Crawl data
        df = client.get_daily_data(ticker)

        if df is None or df.empty:
            logger.warning(f"No data for {ticker}")
            continue

        # Gửi vào kafka
        success = producer.send_stock_data(ticker, df)
        
        if success:
            logger.info(f"✅ Successfully sent {ticker} to Kafka")
        else:
            logger.error(f"❌ Failed to send {ticker}")
    
    # 3. Đóng producer
    producer.close()
    logger.info("\n Test completed!")
    
if __name__ == "__main__":
    test_producer()
