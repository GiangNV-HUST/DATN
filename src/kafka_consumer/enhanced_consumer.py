"""
Enhanced Kafka Consumer
Consumer với đầy đủ tính năng: indicators, predictions, alerts
"""

import json
import logging
from kafka import KafkaConsumer
import pandas as pd
from datetime import datetime

from src.config import Config
from src.indicators.technical_indicators import TechnicalIndicators
from src.database.data_saver import DataSaver
from src.predictions.simple_predict import SimplePredictor
from src.alerts.alert_detector import AlertDetector
from src.alerts.discord_sender import DiscordAlertSender

logger = logging.getLogger(__name__)


class EnhancedStockConsumer:
    """Enhanced Consumer với predictions và alerts"""

    def __init__(self, group_id="stock-enhanced-consumer"):
        """ "Khởi tạo Enhanced Consumer"""
        try:
            # Kafka Consumer
            self.consumer = KafkaConsumer(
                Config.KAFKA_TOPIC_STOCK_PRICES,
                bootstrap_servers=Config.KAFKA_BOOTSTRAP_SERVERS,
                group_id=group_id,
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                auto_commit_interval_ms=1000,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                key_deserializer=lambda k: k.decode("utf-8") if k else None,
            )

            # Components
            self.predictor = SimplePredictor()
            self.alert_detector = AlertDetector()
            self.discord_sender = DiscordAlertSender()

            logger.info(f"✅ Enhanced Consumer initialized")
            logger.info(f"📥 Topic: {Config.KAFKA_TOPIC_STOCK_PRICES}")
            logger.info(f"👥 Group: {group_id}")

        except Exception as e:
            logger.error(f"❌ Failed to create Enhanced Consumer: {e}")
            raise

    def process_message(self, message):
        """
        Xử lý message đầy đủ với pipeline

        Args:
            message: Kafka message

        Returns:
            dict: Processing results
        """

        results = {
            "ticker": None,
            "success": False,
            "indicators": False,
            "predictions": False,
            "alerts": 0,
            "screener": False,
        }

        try:
            # 1. Extract data
            ticker = message.key
            data = message.value
            results["ticker"] = ticker

            logger.info(f"\n{'='*60}")
            logger.info(f"Processing: {ticker}")
            logger.info(f"{'='*60}")

            # Check message format - support both old and new formats
            # New format from kafka_stock_importer: {ticker, price_history, overview, fundamentals}
            # Old format: {ticker, data, timestamp}
            overview = data.get("overview", {})
            fundamentals = data.get("fundamentals", {})

            if "price_history" in data:
                # New format from kafka_stock_importer
                df = pd.DataFrame(data["price_history"])
                logger.info(f"📊 New format detected (with overview/fundamentals)")
            elif "data" in data and isinstance(data["data"], list):
                # Old format
                df = pd.DataFrame(data["data"])
            else:
                logger.warning(f"Invalid message format for {ticker}")
                return results

            if df.empty:
                logger.warning(f"Empty dataframe for {ticker}")
                return results

            # Thêm ticker vào df
            df["ticker"] = ticker

            # 2. Calculate Indicators
            logger.info(f"📈 Calculating indicators...")
            df_with_indicators = TechnicalIndicators.calculate_all(df)

            # 3. Detect alerts
            logger.info(f"🚨 Detecting alerts...")
            alerts = self.alert_detector.detect_all_alerts(df_with_indicators)

            if alerts:
                logger.info(f"⚠️ Found {len(alerts)} alerts for {ticker}")

                # Send alerts to Discord
                sent = self.discord_sender.send_batch_alerts(alerts)
                logger.info(f"📥 {sent}/{len(alerts)} alerts to Discord")
                results["alerts"] = sent
            else:
                logger.info(f"✅ No alerts for {ticker}")

            # 4. Generate Predictions
            logger.info(f"🔮 Generating predictions...")

            # 3-day prediction
            pred_3d = self.predictor.predict_3day_ma(df_with_indicators)
            if pred_3d:
                logger.info(f"3-day predictions: {pred_3d}")
            else:
                logger.warning(f"⚠️ Failed to generate 3-day predictions")

            # 48-day prediction
            pred_48d = self.predictor.predict_48day_lr(df_with_indicators)
            if pred_48d:
                logger.info(f"✅ 48-day predictions generated ({len(pred_48d)} values)")
            else:
                logger.warning(f"⚠️ Failed to generate 48-day predictions")

            # 5. Save to Database
            logger.info(f"💾 Saving to database...")
            saver = DataSaver()

            # Save indicators to stock_prices_1d
            saved_1d = saver.save_1d_data(ticker, df_with_indicators)
            if saved_1d > 0:
                logger.info(f"✅ Saved {saved_1d} records to stock_prices_1d")
                results["indicators"] = True

            # Save to stock_screener (for screening functionality)
            screener_saved = saver.save_screener_data(
                ticker, df_with_indicators, overview, fundamentals
            )
            if screener_saved:
                logger.info(f"✅ Saved screener data for {ticker}")
                results["screener"] = True

            # Save historical data to stock_1d
            hist_saved = saver.save_historical_1d(ticker, df_with_indicators)
            if hist_saved > 0:
                logger.info(f"✅ Saved {hist_saved} historical records to stock_1d")

            # Save predictions
            if pred_3d or pred_48d:
                latest_time = df_with_indicators["time"].max()

                if pred_3d:
                    saver.save_3d_prediction(ticker, latest_time, pred_3d)

                if pred_48d:
                    saver.save_48d_prediction(ticker, latest_time, pred_48d)

                results["predictions"] = True

            saver.close()

            results["success"] = True
            logger.info(f"✅ Successfully processed {ticker}")
            logger.info(f"{'='*60}\n")

            return results

        except Exception as e:
            logger.error(f"❌ Error processing {ticker}:{e}")
            import traceback

            logger.error(traceback.format_exc())
            return results

    def start(self):
        """Bắt đầu lắng nghe và xử lý messages"""
        logger.info("=" * 60)
        logger.info("🚀 ENHANCED KAFKA CONSUMER STARTED")
        logger.info("=" * 60)
        logger.info("Features")
        logger.info("   ✅ Technical Indicators")
        logger.info("   ✅ Price Predictions (3d & 48d)")
        logger.info("   ✅ Alert Detection")
        logger.info("=" * 60)
        logger.info("Press Ctrl+C to stop")

        try:
            message_count = 0
            stats = {"total": 0, "success": 0, "failed": 0, "alerts_sent": 0}
            
            for message in self.consumer:
                message_count += 1
                stats['total'] += 1
                
                logger.info(f"\n 📬 Message #{message_count}")
                logger.info(f"Partition: {message.partition} | Offset: {message.offset}")
                
                # Process
                result = self.process_message(message)
                
                # Update stats
                if result['success']:
                    stats['success'] += 1
                else:
                    stats["failed"] += 1
                    
                stats["alerts_sent"] += result["alerts"]
                
                # Show stats every 10 messages:
                if message_count % 10 == 0:
                    self._print_stats(stats)
            
        except KeyboardInterrupt:
            logger.info("\n ⚠️ Consumer stopped by user")
            self._print_stats(stats)
        
        except Exception as e:
            logger.error(f"❌ Consumer error: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            self.close()
    
    def _print_stats(self, stats):
        """Print statistics"""
        logger.info("\n"+ "="*60)
        logger.info("📊 STATISTICS")
        logger.info(f"  Total Messages: {stats['total']}")
        logger.info(f"  ✅ Success: {stats['success']}")
        logger.info(f"  ❌ Failed: {stats['failed']}")
        logger.info(f"  🚨 Alerts sent: {stats['alerts_sent']}")
        success_rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
        logger.info(f"  📈 Success rate: {success_rate:.1f}%")
        logger.info("="*60 + "\n")
        
        
    def close(self):
        """Đóng Consumer"""
        if self.consumer:
            self.consumer.close()
            logger.info("👋 Enhanced Consumer Closed")
            
        
                
