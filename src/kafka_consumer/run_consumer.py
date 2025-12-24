"""
Scipt chạy Enhanced Kafka Consumer 
"""

import sys
from pathlib import Path

# Thêm thư mục gốc vào Python path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

import logging
import sys
from src.kafka_consumer.enhanced_consumer import EnhancedStockConsumer

# Setup logging với UTF-8 encoding
import io

# StreamHandler với UTF-8 cho console
console_handler = logging.StreamHandler(
    io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
)
console_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)

# FileHandler với UTF-8 cho file
file_handler = logging.FileHandler("enhanced_consumer.log", encoding='utf-8')
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)

logging.basicConfig(
    level=logging.INFO,
    handlers=[console_handler, file_handler]
)

logger = logging.getLogger(__name__)

def main():
    """Main Function"""
    logger.info("="*60)
    logger.info("ENHANCED KAFKA CONSUMER")
    logger.info("Stock Data Processor with Predictions & Alerts")
    logger.info("="*60)
    
    # Khởi tạo enhanced consumer
    consumer = EnhancedStockConsumer(group_id="stock-enhanced-consumer")

    # Bắt đầu lắng nghe
    consumer.start()
    
if __name__ == "__main__":
    main()    
    