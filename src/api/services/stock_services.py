"""
Business logic cho stock data
"""

import psycopg2
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import math

from src.config import Config
from src.api.models.schemas import (
    StockListResponse,
    StockPrice,
    StockPriceWithIndicators,
    StockSummary,
)

logger = logging.getLogger(__name__)


class StockService:
    """Service xử lý business logic cho stocks"""

    def __init__(self):
        self.db_config = {
            "host": Config.DB_HOST,
            "port": Config.DB_PORT,
            "database": Config.DB_NAME,
            "user": Config.DB_USER,
            "password": Config.DB_PASSWORD,
        }

    def get_connection(self):
        """Tạo database connection"""
        return psycopg2.connect(**self.db_config)

    def sanitize_float(self, value: Any) -> Optional[float]:
        """Chuyển đổi giá trị float không hợp lệ thành None"""
        if value is None:
            return None
        try:
            if math.isnan(value) or math.isinf(value):
                return None
            return float(value)
        except (ValueError, TypeError):
            return None

    def sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Làm sạch tất cả các giá trị float và datetime trong Dictionary"""
        result = {}
        for key, value in data.items():
            if isinstance(value, datetime):
                # Convert datetime to ISO format string
                result[key] = value.isoformat()
            elif isinstance(value, float):
                result[key] = self.sanitize_float(value)
            elif isinstance(value, dict):
                result[key] = self.sanitize_dict(value)
            elif isinstance(value, list):
                result[key] = [
                    self.sanitize_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                result[key] = value
        return result

    def get_all_tickers(self) -> List[str]:
        """Lấy danh sách tất cả ticker"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()

            cur.execute(
                """
                    SELECT DISTINCT ticker
                    FROM stock.stock_prices_1d
                    ORDER BY ticker
                        """
            )

            ticker = [row[0] for row in cur.fetchall()]
            cur.close()
            conn.close()
            return ticker

        except Exception as e:
            logger.error(f"Error getting tickers: {e}")
            return []

    def get_stock_history(self, ticker: str, days: int = 30) -> List[Dict[str, Any]]:
        """Lấy lịch sử giá cổ phiếu"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()

            cur.execute(
                """
                    SELECT ticker, time, open, high, low, close, volume,
                            ma5, ma10, ma20, ma50, ma100, rsi, macd_main, macd_signal,
                            macd_diff, bb_upper, bb_middle, bb_lower
                    FROM stock.stock_prices_1d
                    WHERE ticker = %s
                    ORDER BY time DESC
                    LIMIT %s
                        """,
                (ticker, days * 2),
            )

            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()

            results = []
            for row in rows:
                data = dict(zip(columns, row))
                results.append(self.sanitize_dict(data))

            cur.close()
            conn.close()

            return results

        except Exception as e:
            logger.error(f"Error getting stock history: {e}")
            return []

    def get_latest_price(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Lấy giá mới nhất của cổ phiếu"""
        history = self.get_stock_history(ticker, days=1)
        return history[0] if history else None

    def get_predictions(self, ticker: str) -> Dict[str, Any]:
        """Lấy predictions cho ticker"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()

            # 3-day predictions
            cur.execute(
                """
                    SELECT time, close_next_1, close_next_2, close_next_3
                    FROM stock.stock_prices_3d_predict
                    WHERE ticker = %s
                    ORDER BY time DESC
                    LIMIT 1
                        """,
                (ticker,),
            )

            pred_3d = cur.fetchone()

            results = {}
            if pred_3d:
                results["3day"] = {
                    "time": pred_3d[0],
                    "predictions": [
                        self.sanitize_float(pred_3d[1]),
                        self.sanitize_float(pred_3d[2]),
                        self.sanitize_float(pred_3d[3]),
                    ],
                }

            cur.close()
            conn.close()

            return results

        except Exception as e:
            logger.error(f"Error getting predictions: {e}")
            return {}

    def get_recent_alerts(
        self, ticker: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Lấy user alerts gần đây"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()

            query = """
                SELECT id, ticker, type, condition, price_value, create_at, user_id, user_name
                FROM stock.alert
                WHERE 1=1
            """
            params = []

            if ticker:
                query += " AND ticker = %s"
                params.append(ticker)

            query += " ORDER BY create_at DESC LIMIT %s"
            params.append(limit)

            cur.execute(query, params)

            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()

            results = []
            for row in rows:
                data = dict(zip(columns, row))
                results.append(self.sanitize_dict(data))

            cur.close()
            conn.close()

            return results

        except Exception as e:
            logger.error(f"Error getting alerts: {e}")
            return []

    def get_technical_alerts(
        self, ticker: Optional[str] = None, limit: int = 50, alert_level: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Lấy technical alerts (cảnh báo kỹ thuật tự động)"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()

            query = """
                SELECT id, ticker, alert_type, alert_level, message,
                       indicator_value, price_at_alert, created_at, is_active
                FROM stock.technical_alerts
                WHERE is_active = TRUE
            """
            params = []

            if ticker:
                query += " AND ticker = %s"
                params.append(ticker)

            if alert_level:
                query += " AND alert_level = %s"
                params.append(alert_level)

            query += " ORDER BY created_at DESC LIMIT %s"
            params.append(limit)

            cur.execute(query, params)

            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()

            results = []
            for row in rows:
                data = dict(zip(columns, row))
                results.append(self.sanitize_dict(data))

            cur.close()
            conn.close()

            return results

        except Exception as e:
            logger.error(f"Error getting technical alerts: {e}")
            return []

    def get_stock_summary(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Lấy tóm tắt cổ phiếu"""
        latest = self.get_latest_price(ticker)
        if not latest:
            return None

        # Tính % thay đổi
        history = self.get_stock_history(ticker, days=2)
        change_percent = None
        if len(history) >= 2:
            prev_close = history[1]["close"]
            curr_close = history[0]["close"]
            if prev_close and curr_close:
                change_percent = ((curr_close - prev_close) / prev_close) * 100
                change_percent = self.sanitize_float(change_percent)
        result = {
            "ticker": ticker,
            "latest_price": latest["close"],
            "change_percent": change_percent,
            "rsi": latest.get("rsi"),
            "volume": latest.get("volume"),
            "last_updated": latest["time"],
        }
        return self.sanitize_dict(result)

    def search_stocks(
        self,
        rsi_min: Optional[float] = None,
        rsi_max: Optional[float] = None,
        volume_min: Optional[float] = None,
    ) -> List[str]:
        """Tìm kiếm cổ phiếu theo tiêu chí"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()

            # Subquery để lấy latest record của mỗi ticker
            query = """
                WITH latest_prices AS (
                    SELECT DISTINCT ON (ticker)
                        ticker, rsi, volume
                    FROM stock.stock_prices_1d
                    ORDER BY ticker, time DESC
                )
                SELECT ticker
                FROM latest_prices
                WHERE 1=1            
            """
            params = []

            if rsi_min is not None:
                query += " AND rsi >= %s"
                params.append(rsi_min)

            if rsi_max is not None:
                query += " AND rsi <= %s"
                params.append(rsi_max)

            if volume_min is not None:
                query += " AND volume >= %s"
                params.append(volume_min)

            query += "ORDER BY ticker"

            cur.execute(query, params)
            tickers = [row[0] for row in cur.fetchall()]

            cur.close()
            conn.close()

            return tickers

        except Exception as e:
            logger.error(f"Error searching stocks: {e}")
            return []
