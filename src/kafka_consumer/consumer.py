"""Kafka Consumer - Nhận stock data từ Kafka và xử lý"""

import json
import logging
from kafka import KafkaConsumer
from kafka.errors import KafkaError
import pandas as pd
from src.config import Config
from src.indicators.technical_indicators import TechnicalIndicators
from src.database.data_saver import DataSaver

logger = logging.getLogger(__name__)


class StockDataConsumer:
    """Consumer để nhận và xử lý dữ liệu cổ phiếu từ Kafka"""

    def __init__(self, group_id="stock-consumer-group"):
        """
        Khởi tạo kafka consumer

        Args:
            group_id: Consumer group ID (để kafka track offset)
        """
        try:
            self.consumer = KafkaConsumer(
                Config.KAFKA_TOPIC_STOCK_PRICES,
                bootstrap_servers=Config.KAFKA_BOOTSTRAP_SERVERS,
                group_id=group_id,
                auto_offset_reset="earliest",  # Đọc từ đầu nếu chưa có offset
                enable_auto_commit=True,  # Tự động commit offset
                auto_commit_interval_ms=1000,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                key_deserializer=lambda k: k.decode("utf-8") if k else None,
            )
            logger.info(
                f"✅ Kafka Consumer connected to {Config.KAFKA_BOOTSTRAP_SERVERS}"
            )
            logger.info(f" Subcribed to topic: {Config.KAFKA_TOPIC_STOCK_PRICES}")
            logger.info(f"Consumer group: {group_id}")
        except Exception as e:
            logger.error(f"❌ Failed to create Kafka Consumer: {e}")
            raise

    def process_message(self, message):
        """
        Xử lý một message từ kafka

        Args:
            message: Kafka message object

        Returns:
            bool: True nếu xử lý thành công
        """
        try:
            # Extract data từ message
            ticker = message.key
            data = message.value

            logger.info(f"Received message for {ticker}")
            logger.debug(f"Message data: {data}")

            # Convert data thành DataFrame
            if "data" in data and isinstance(data["data"], list):
                df = pd.DataFrame(data["data"])
            else:
                logger.warning(f"Empty dataframe for {ticker}")
                return False

            if df.empty:
                logger.warning(f"Empty dataframe for {ticker}")
                return False

            # Tính toán indicators
            logger.info(f"Calculating indicators for {ticker}...")
            df_with_indicators = TechnicalIndicators.calculate_all(df)

            # Lưu vào database
            logger.info(f"Saving {ticker} to database...")
            saver = DataSaver()
            saved = saver.save_1d_data(ticker, df_with_indicators)
            saver.close()

            if saved > 0:
                logger.info(f"✅ Successfully processed {ticker} ({saved} records)")
                return True
            else:
                logger.warning(f"⚠️ No records saved for {ticker}")
                return False

        except Exception as e:
            logger.error(f"❌ Error processing message: {e}")
            import traceback

            logger.error(traceback.format_exc())
            return False

    def start(self):
        """
        Bắt đầu lắng nghe và xử lý messages
        Chạy vô hạn cho đến khi bị interupt
        """
        logger.info("🚀 Consumer started. Waiting for messages...")
        logger.info("Press Ctrl+C to stop")

        try:
            message_count = 0

            for message in self.consumer:
                message_count += 1

                logger.info(f"\n{'='*60}")
                logger.info(f"Message #{message_count}")
                logger.info(f"Topic: {message.topic}")
                logger.info(f"Partition: {message.partition}")
                logger.info(f"Offset: {message.offset}")
                logger.info(f"Key: {message.key}")
                logger.info(f"{'='*60}")

                # Xử lý message
                success = self.process_message(message)
                if success:
                    logger.info(f"✅ Message #{message_count} processed successfully")
                else:
                    logger.error(f"❌ Failed to process message #{message_count}")
        except KeyboardInterrupt:
            logger.info("\n⚠️ Consumer interrupted by user")

        except Exception as e:
            logger.error(f"❌ Consumer error: {e}")
            import traceback

            logger.error(traceback.format_exc())

        finally:
            self.close()

    def close(self):
        """Đóng Consumer"""
        if self.consumer:
            self.consumer.close()
            logger.info("👋 Kafka Consumer closed")
