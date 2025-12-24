"""
Discord Alert Sender
Gửi alerts đến Discord channel qua webhook
"""

from discord_webhook import DiscordWebhook, DiscordEmbed
from src.config import Config
import logging
import psycopg2
import json
import numpy as np

logger = logging.getLogger(__name__)


class DiscordAlertSender:
    """Gửi alerts đến Discord"""

    def __init__(self):
        self.webhook_url = Config.DISCORD_WEBHOOK_URL
        self.db_config = {
            "host": Config.DB_HOST,
            "port": Config.DB_PORT,
            "database": Config.DB_NAME,
            "user": Config.DB_USER,
            "password": Config.DB_PASSWORD,
        }

        if not self.webhook_url:
            logger.warning("Discord webhook URL is not configured.")

    def get_connection(self):
        """Tạo database connection"""
        return psycopg2.connect(**self.db_config)

    def _save_to_database(self, alert):
        """Lưu alert vào database"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()

            # Map severity to alert_level
            severity_to_level = {
                "HIGH": "critical",
                "WARNING": "warning",
                "INFO": "info",
                "LOW": "info"
            }
            alert_level = severity_to_level.get(alert.get("severity", "INFO"), "info")

            # Map type to alert_type
            type_mapping = {
                "GOLDEN_CROSS": "golden_cross",
                "DEATH_CROSS": "death_cross",
                "RSI_OVERBOUGHT": "rsi_overbought",
                "RSI_OVERSOLD": "rsi_oversold",
                "VOLUME_SPIKE": "volume_spike",
                "MACD_BULLISH": "macd_bullish",
                "MACD_BEARISH": "macd_bearish",
                "BB_BREAKOUT": "bb_breakout"
            }
            alert_type = type_mapping.get(alert.get("type", ""), alert.get("type", "").lower())

            # Check if alert already exists in last 24 hours
            cur.execute(
                """
                SELECT id FROM stock.technical_alerts
                WHERE ticker = %s
                  AND alert_type = %s
                  AND created_at > NOW() - INTERVAL '24 hours'
                LIMIT 1
                """,
                (alert['ticker'], alert_type)
            )

            existing = cur.fetchone()
            if existing:
                logger.info(f"Alert already exists in database for {alert['ticker']} - {alert_type}")
                cur.close()
                conn.close()
                return False

            # Insert new alert
            # Convert value dict to JSON string for PostgreSQL
            # Handle numpy types (int64, float64, etc.)
            def convert_numpy(obj):
                if isinstance(obj, (np.integer, np.floating)):
                    return obj.item()
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                return obj

            indicator_value = alert.get('value')
            if indicator_value and isinstance(indicator_value, dict):
                # Convert numpy types to Python types
                indicator_value = {k: convert_numpy(v) for k, v in indicator_value.items()}
                indicator_value = json.dumps(indicator_value)

            cur.execute(
                """
                INSERT INTO stock.technical_alerts
                (ticker, alert_type, alert_level, message, indicator_value, price_at_alert)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    alert['ticker'],
                    alert_type,
                    alert_level,
                    alert['message'],
                    indicator_value,
                    alert.get('price')
                )
            )

            conn.commit()
            cur.close()
            conn.close()

            logger.info(f"💾 Saved alert to database: {alert['ticker']} - {alert_type}")
            return True

        except Exception as e:
            logger.error(f"Error saving alert to database: {e}")
            return False

    def send_alert(self, alert):
        """
        Gửi 1 alert đến Discord và lưu vào database

        Args:
            alert: Dict chứa thông tin alert
        """
        # Save to database first
        self._save_to_database(alert)

        if not self.webhook_url:
            logger.warning("⚠️ Cannot send alert: webhook not configured")
            return False

        try:
            webhook = DiscordWebhook(url=self.webhook_url)

            # Tạo embed message
            embed = DiscordEmbed(
                title=f"📊 Stock Alert: {alert['ticker']}",
                description=alert["message"],
                color=self._get_color(alert["severity"]),
            )

            # Thêm fields
            embed.add_embed_field(name="Type", value=alert["type"], inline=True)
            embed.add_embed_field(name="Severity", value=alert["severity"], inline=True)

            if "value" in alert:
                embed.add_embed_field(
                    name="Value", value=str(alert["value"]), inline=False
                )

            # Thêm timestamp
            embed.set_timestamp()

            webhook.add_embed(embed)

            # Gửi
            response = webhook.execute()

            if response.status_code == 200:
                logger.info(f"✅ Sent alert to Discord: {alert['ticker']}")
                return True
            else:
                logger.error(f"❌ Failed to send alert: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error sending Discord alert: {e}")
            return False

    def send_batch_alerts(self, alerts):
        """
        Gửi nhiều alerts

        Args:
            int: Số lượng alerts đã gửi thành công
        """
        success_count = 0

        for alert in alerts:
            if self.send_alert(alert):
                success_count += 1

        return success_count

    @staticmethod
    def _get_color(severity):
        """Map severity to Discord color"""
        colors = {
            "HIGH": 0xFF0000,  # Red
            "WARNING": 0xFFA500,  # Orange
            "INFO": 0x00FF00,  # Green
            "LOW": 0x808080,  # Gray
        }
        return colors.get(severity, 0x808080)
    
