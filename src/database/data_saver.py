import pandas as pd
from datetime import datetime
import logging
from src.database.connection import Database

logger = logging.getLogger(__name__)


class DataSaver:
    def __init__(self):
        self.db = Database()
        self.db.connect()

    def save_1m_data(self, ticker, df):
        """
        Lưu dữ liệu 1 phút vào database

        Args:
            ticker: Mã cổ phiếu
            df: DataFrame với columns: time, open, high, low, close, volume
        """
        try:
            cursor = self.db.get_cursor()

            inserted = 0
            for _, row in df.iterrows():
                try:
                    cursor.execute(
                        """
                                   INSERT INTO stock.stock_price_1m(time, ticker, open, high, low, close, volume)
                                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                                   ON CONFLICT (time, ticker) DO NOTHING""",
                        (
                            row["time"],
                            ticker,
                            float(row["open"]),
                            float(row["high"]),
                            float(row["low"]),
                            float(row["close"]),
                            int(row["volume"]),
                        ),
                    )
                    inserted += 1
                except Exception as e:
                    logger.error(f"Error inserting row: {e}")
                    continue
            self.db.connection.commit()
            logger.info(f"✅ Saved {inserted}/{len(df)} records for {ticker}")
        except Exception as e:
            logger.error(f"❌ Error saving 1m data: {e}")
            self.db.connection.rollback()
            return 0

    def save_1d_data(self, ticker, df):
        """
        Lưu dữ liệu ngày vào database

        Args:
            ticker: Mã cổ phiếu
            df: DataFrame với indicators đã tính
        """
        try:
            cursor = self.db.get_cursor()

            inserted = 0
            for _, row in df.iterrows():
                try:
                    cursor.execute(
                        """
                                    INSERT INTO stock.stock_prices_1d
                                    (time, ticker, open, high, low, close, volume, avg_volume_5, avg_volume_10, avg_volume_20, ma5, ma10, ma20, ma50, ma100, bb_upper, bb_middle, bb_lower, rsi, macd_main, macd_signal, macd_diff) 
                                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                                    ON CONFLICT (time, ticker) DO UPDATE SET
                                        open = EXCLUDED.open,
                                        high = EXCLUDED.high,
                                        low = EXCLUDED.low,
                                        close = EXCLUDED.close, 
                                        volume = EXCLUDED.volume,
                                        avg_volume_5 = EXCLUDED.avg_volume_5,
                                        avg_volume_10 = EXCLUDED.avg_volume_10,
                                        avg_volume_20 = EXCLUDED.avg_volume_20,
                                        ma5 = EXCLUDED.ma5,
                                        ma10 = EXCLUDED.ma10,
                                        ma20 = EXCLUDED.ma20,
                                        ma50 = EXCLUDED.ma50,
                                        ma100 = EXCLUDED.ma100,
                                        bb_upper = EXCLUDED.bb_upper,
                                        bb_middle = EXCLUDED.bb_middle,
                                        bb_lower = EXCLUDED.bb_lower,
                                        rsi = EXCLUDED.rsi,
                                        macd_main = EXCLUDED.macd_main,
                                        macd_signal = EXCLUDED.macd_signal,
                                        macd_diff = EXCLUDED.macd_diff
                                   """,
                        (
                            row["time"],
                            ticker,
                            float(row["open"]),
                            float(row["high"]),
                            float(row["low"]),
                            float(row["close"]),
                            int(row["volume"]),
                            row.get("avg_volume_5", None),
                            row.get("avg_volume_10", None),
                            row.get("avg_volume_20", None),
                            row.get("ma5", None),
                            row.get("ma10", None),
                            row.get("ma20", None),
                            row.get("ma50", None),
                            row.get("ma100", None),
                            row.get("bb_upper", None),
                            row.get("bb_middle", None),
                            row.get("bb_lower", None),
                            row.get("rsi", None),
                            row.get("macd_main", None),
                            row.get("macd_signal", None),
                            row.get("macd_diff", None),
                        ),
                    )
                    inserted += 1
                except Exception as e:
                    logger.error(f"Error inserting daily row: {e}")
                    continue

            self.db.connection.commit()
            logger.info(f"✅ Saved {inserted}/{len(df)} daily records for {ticker}")
            return inserted
        except Exception as e:
            logger.error(f"❌ Error saving daily data: {e}")
            self.db.connection.rollback()
            return 0

    def save_3d_prediction(self, ticker, time, predictions):
        """
        Lưu dự đoán 3 ngày

        Args:
            ticker: mã cổ phiếu
            time: Thời gian dự đoán (date)
            predictions: List [day1, day2, day3]
        """
        try:
            cursor = self.db.get_cursor()

            cursor.execute(
                """
                   INSERT INTO stock.stock_prices_3d_predict
                   (time, ticker, close_next_1, close_next_2, close_next_3) VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (time, ticker) DO UPDATE SET
                        close_next_1 = EXCLUDED.close_next_1,
                        close_next_2 = EXCLUDED.close_next_2,
                        close_next_3 = EXCLUDED.close_next_3
                           """,
                (time, ticker, predictions[0], predictions[1], predictions[2]),
            )

            self.db.connection.commit()
            logger.info(f"✅ Saved 3-day prediction for {ticker}")
            return True

        except Exception as e:
            logger.error(f"❌ Error saving 3-day prediction: {e}")
            self.db.connection.rollback()
            return False

    def save_48d_prediction(self, ticker, time, predictions):
        """
        Lưu dự đoán 48 ngày

        Args:
            ticker: mã cổ phiếu
            time: thời gian dự đoán (Date)
            predictions: List [day1, day2, ..., day48]
        """
        if not predictions or len(predictions) < 48:
            logger.warning(f"Invalid 48-day predictions for {ticker}")
            return False

        try:
            cursor = self.db.get_cursor()

            # Tạo placeholders động
            columns = ["time", "ticker"] + [f"close_next_{i+1}" for i in range(48)]
            placeholders = ", ".join(["%s"] * len(columns))
            update_clause = ", ".join(
                [f"{col} = EXCLUDED.{col}" for col in columns[2:]]
            )

            query = f"""
                INSERT INTO stock.stock_prices_48d_predict ({', '.join(columns)})
                VALUES ({placeholders})
                ON CONFLICT (time, ticker) DO UPDATE SET
                {update_clause}
            """

            # Tạo values tuple
            values = [time, ticker] + predictions

            cursor.execute(query, values)
            self.db.connection.commit()
            logger.info(f"✅ Saved 48-day prediction for {ticker}")
            return True

        except Exception as e:
            logger.error(f"❌ Error saving 48-day prediction: {e}")
            self.db.connection.rollback()
            return False

    def close(self):
        """Đóng kết nối với database"""
        self.db.close()
