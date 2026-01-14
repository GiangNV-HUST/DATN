"""
Kafka Producer - Gửi stock data vào kafka topic
"""

import json
import logging
from kafka import KafkaProducer
from kafka.errors import KafkaError
from datetime import datetime
from src.config import Config

logger = logging.getLogger(__name__)


class StockDataProducer:
    """Producer gửi dữ liệu cổ phiếu vào kafka"""

    def __init__(self):
        """Khởi tạo Kafka Producer"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=Config.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",  # Đợi tất cả replicas confirm
                retries=3,
                max_in_flight_requests_per_connection=1,  # Đảm bảo thứ tự
            )
            logger.info(
                f"✅ Kafka Producer connected to {Config.KAFKA_BOOTSTRAP_SERVERS}"
            )

        except Exception as e:
            logger.error(f"❌ Failed to create Kafka Producer: {e}")
            raise

    def send_stock_data(self, ticker, data):
        """
        Gửi dữ liệu cổ phiếu vào kafka

        Args:
            ticker: Mã cổ phiếu (VD: 'VNM)
            data: DataFrame hoặc dict với stock data
                  - DataFrame: Convert to old format {ticker, data, timestamp}
                  - Dict with 'price_history': Pass through as-is (new format)
                  - Dict without 'price_history': Wrap in old format

        Returns:
            bool: True nếu gửi thành công
        """
        try:
            # Check if data is already in new format (from kafka_stock_importer)
            if isinstance(data, dict) and "price_history" in data:
                # New format - pass through directly
                message = data
            elif hasattr(data, "to_dict"):
                # DataFrame - convert to old format
                data_dict = data.to_dict(orient="records")
                message = {
                    "ticker": ticker,
                    "data": data_dict,
                    "timestamp": datetime.now().isoformat(),
                }
            else:
                # Other dict - wrap in old format
                message = {
                    "ticker": ticker,
                    "data": data,
                    "timestamp": datetime.now().isoformat(),
                }

            # Gửi vào kafka với ticker làm key (để partition theo ticker)
            future = self.producer.send(
                Config.KAFKA_TOPIC_STOCK_PRICES, key=ticker, value=message
            )

            # Đợi confirm (blocking)
            record_metadata = future.get(timeout=10)

            logger.info(
                f"✅ Sent {ticker} to Kafka [topic={record_metadata.topic},partition={record_metadata.partition}, offset={record_metadata.offset}]",
            )
            return True

        except KafkaError as e:
            logger.error(f"❌ Kafka error sending {ticker}: {e}")
            return False

        except Exception as e:
            logger.error(f"❌ Error sending {ticker}: {e}")
            return False

    def send_batch(self, ticker_data_dict):
        """
        Gửi batch nhiều tickers

        Args:
            ticker_data_dict: Dict {ticker: Data}

        Returns:
            dict: {ticker: success_status}
        """
        results = {}
        for ticker, data in ticker_data_dict.items():
            results[ticker] = self.send_stock_data(ticker, data)

        # Flush để đảm bảo tất cả các message được gửi
        self.producer.flush()

        return results

    def close(self):
        """Đóng producer"""
        if self.producer:
            self.producer.close()
            logger.info("Kafka Producer Closed")
