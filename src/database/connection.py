import psycopg2
from psycopg2.extras import RealDictCursor
from src.config import Config
import logging

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        self.connection = None

    def connect(self):
        """Tạo kết nối đến database"""
        try:
            self.connection = psycopg2.connect(
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                database=Config.DB_NAME,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                cursor_factory=RealDictCursor,
            )
            logger.info("✅ Database connected successfully!")
            return self.connection
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise
        
    def close(self):
        """Đóng kết nối"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")
            
    def get_cursor(self):
        """Lấy cursor với auto-reconnect"""
        # Check if connection is alive
        if not self.connection or self.connection.closed:
            logger.warning("⚠️ Connection closed, reconnecting...")
            self.connect()

        # Test connection
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
        except Exception as e:
            logger.warning(f"⚠️ Connection test failed: {e}, reconnecting...")
            self.connect()

        return self.connection.cursor()
        
