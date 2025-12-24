"""
Database Query Tools for AI Agent
Tools để AI query database
"""

import logging
from datetime import datetime, timedelta
from src.database.connection import Database

logger = logging.getLogger(__name__)


class DatabaseTools:
    """Tools để query stock data từ database"""

    def __init__(self):
        self.db = Database()
        self.db.connect()

    def get_latest_price(self, ticker):
        """
        Lấy giá mới nhất của ticker

        Returns:
            dict: {ticker, time, price, indicators}
        """
        try:
            cursor = self.db.get_cursor()

            cursor.execute(
                """
                    SELECT ticker, time, close, open, high, low, volume, 
                            ma5, ma20, rsi, macd_main, macd_signal
                    FROM stock.stock_prices_1d
                    WHERE ticker = %s
                    ORDER BY time DESC
                    LIMIT 1
                """,
                (ticker,),
            )

            row = cursor.fetchone()

            if row:
                return {
                    "ticker": row["ticker"],
                    "time": str(row["time"]),
                    "close": float(row["close"]),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "volume": int(row["volume"]),
                    "ma5": float(row["ma5"]) if row["ma5"] else None,
                    "ma20": float(row["ma20"]) if row["ma20"] else None,
                    "rsi": float(row["rsi"]) if row["rsi"] else None,
                    "macd": float(row["macd_main"]) if row["macd_main"] else None,
                }
            return None

        except Exception as e:
            logger.error(f"Error getting latest price for {ticker}: {e}")
            return None

    def get_price_history(self, ticker, days=30):
        """
        Lấy lịch sử giá

        Args:
            ticker: mã cổ phiếu
            days: Số ngày lịch sử

        Returns:
            list: Danh sách giá theo ngày
        """
        try:
            cursor = self.db.get_cursor()

            cursor.execute(
                """
                    SELECT time, close, volume, rsi, ma20
                    FROM stock.stock_prices_1d
                    WHERE ticker = %s 
                    ORDER BY time DESC
                    LIMIT %s
                """,
                (ticker, days),
            )

            rows = cursor.fetchall()

            return [
                {
                    "time": str(row["time"]),
                    "close": float(row["close"]),
                    "volume": int(row["volume"]),
                    "rsi": float(row["rsi"]) if row["rsi"] else None,
                    "ma20": float(row["ma20"]) if row["ma20"] else None,
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Error getting price history: {e}")
            return []

    def get_predictions(self, ticker):
        """
        Lấy dự đoán giá 3 ngày

        Returns:
            dict: {day1, day2, day3}
        """
        try:
            cursor = self.db.get_cursor()

            cursor.execute(
                """
                           SELECT close_next_1, close_next_2, close_next_3
                           FROM stock.stock_prices_3d_predict
                           WHERE ticker = %s
                           ORDER BY time DESC
                           LIMIT 1
                           """,
                (ticker,),
            )

            row = cursor.fetchone()

            if row:
                return {
                    "day1": float(row["close_next_1"]),
                    "day2": float(row["close_next_2"]),
                    "day3": float(row["close_next_3"]),
                }
            return None
        except Exception as e:
            logger.warning(f"Predictions not available for {ticker}: {e}")
            # Rollback transaction to continue
            if self.db.connection:
                self.db.connection.rollback()
            return None

    def search_stocks_by_criteria(self, criteria):
        """
        Tìm cổ phiếu theo tiêu chí

        Args:
            criteria: Dict với các điều kiện
                - rsi_below: RSI < value
                - rsi_above: RSI > value
                - price_below: Price < value
                - price_above: Price < value

        Returns:
            list: Danh sách cổ phiếu matching
        """
        try:
            cursor = self.db.get_cursor()

            conditions = []
            params = []

            if "rsi_below" in criteria:
                conditions.append("rsi < %s")
                params.append(criteria["rsi_below"])

            if "rsi_above" in criteria:
                conditions.append("rsi > %s")
                params.append(criteria["rsi_above"])

            if "price_below" in criteria:
                conditions.append("close < %s")
                params.append(criteria["price_below"])

            if "price_above" in criteria:
                conditions.append("close > %s")
                params.append(criteria["price_above"])

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            query = f"""
                SELECT ticker, close, rsi, ma5, ma20
                FROM stock.stock_prices_1d
                WHERE time = (SELECT MAX(time) FROM stock.stock_prices_1d)
                AND {where_clause}
                ORDER BY close DESC
                LIMIT 20
            """

            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()

            return [
                {
                    "ticker": row["ticker"],
                    "close": float(row["close"]),
                    "rsi": float(row["rsi"]) if row["rsi"] else None,
                    "ma5": float(row["ma5"]) if row["ma5"] else None,
                    "ma20": float(row["ma20"]) if row["ma20"] else None,
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Error searching stocks: {e}")
            return []

    def get_company_info(self, ticker):
        """
        Lấy thông tin công ty
        Returns:
            dict: Company Infomation
        """
        try:
            cursor = self.db.get_cursor()

            cursor.execute(
                """
                  SELECT ticker, company_name, industry, no_employees, website
                  FROM stock.infomation
                  WHERE ticker = %s
                        
                           """,
                (ticker,),
            )

            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

        except Exception as e:
            logger.error(f"Error getting company info: {e}")
            return None
    
    def close(self):
        """Đóng database connection"""
        if self.db:
            self.db.close()
            
