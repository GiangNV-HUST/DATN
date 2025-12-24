"""Scipts chạy Kafka Consumer"""

import sys
from pathlib import Path

# Thêm thư mục gốc của project vào Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from src.kafka_consumer.consumer import StockDataConsumer

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

def main():
    """Main Function"""
    logger.info("="*60)
    logger.info("KAFKA CONSUMER - STOCK DATA PROCESSOR")
    logger.info("="*60)
    
    # Khởi tạo consumer
    consumer = StockDataConsumer(group_id='stock-consumer-v2')
    
    # Bắt đầu lắng nghe
    consumer.start()
    
if __name__ =="__main__":
    main()
    