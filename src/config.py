import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Database
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5434")
    DB_NAME = os.getenv("DB_NAME", "stock")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres123")

    # VNSTOCK
    VNSTOCK_SOURCE = os.getenv("VNSTOCK_SOURCE", "VCI")

    # Kafka Configuration
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    KAFKA_TOPIC_STOCK_PRICES = os.getenv(
        "KAFKA_TOPIC_STOCK_PRICES", "stock_prices_daily"
    )

    # Discord Webhook
    DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

    # Google Gemini
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

    # Discord bot
    DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")

    @property
    def DATABASE_URL(self):
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    def __repr__(self) -> str:
        return f"Config(DB={self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}, Kafka={self.KAFKA_BOOTSTRAP_SERVERS})"


config = Config()
