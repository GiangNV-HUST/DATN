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
        """Lấy cursor"""
        if not self.connection:
            self.connect()
        return self.connection.cursor()
        
