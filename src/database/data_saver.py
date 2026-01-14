import pandas as pd
import numpy as np
from datetime import datetime
import logging
from src.database.connection import Database

logger = logging.getLogger(__name__)


def _to_python(val):
    """Convert numpy types to Python native types for database insertion"""
    if val is None:
        return None
    if isinstance(val, (np.integer, np.int64, np.int32)):
        return int(val)
    if isinstance(val, (np.floating, np.float64, np.float32)):
        if np.isnan(val):
            return None
        return float(val)
    if isinstance(val, np.ndarray):
        return val.tolist()
    if pd.isna(val):
        return None
    return val


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
                (time, ticker, _to_python(predictions[0]), _to_python(predictions[1]), _to_python(predictions[2])),
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

            # Tạo values tuple - convert numpy types to Python
            values = [time, ticker] + [_to_python(p) for p in predictions]

            cursor.execute(query, values)
            self.db.connection.commit()
            logger.info(f"✅ Saved 48-day prediction for {ticker}")
            return True

        except Exception as e:
            logger.error(f"❌ Error saving 48-day prediction: {e}")
            self.db.connection.rollback()
            return False

    def save_screener_data(self, ticker, df, overview=None, fundamentals=None):
        """
        Lưu dữ liệu screening vào bảng stock_screener

        Args:
            ticker: Mã cổ phiếu
            df: DataFrame với price data và indicators
            overview: Dict với exchange, industry
            fundamentals: Dict với pe, pb, roe, eps, dividend_yield
        """
        try:
            cursor = self.db.get_cursor()

            # Get latest row
            if df.empty:
                logger.warning(f"Empty dataframe for {ticker}")
                return False

            latest = df.iloc[-1]

            # Extract values
            exchange = overview.get('exchange') if overview else None
            industry = overview.get('industry') if overview else None

            pe = fundamentals.get('pe') if fundamentals else None
            pb = fundamentals.get('pb') if fundamentals else None
            roe = fundamentals.get('roe') if fundamentals else None
            eps = fundamentals.get('eps') if fundamentals else None
            dividend_yield = fundamentals.get('dividend_yield') if fundamentals else None

            # Calculate avg trading value (close * volume) over 20 days
            avg_trading_value = None
            if len(df) >= 20:
                df['trading_value'] = df['close'] * df['volume']
                avg_trading_value = df['trading_value'].tail(20).mean()
            elif len(df) > 0:
                df['trading_value'] = df['close'] * df['volume']
                avg_trading_value = df['trading_value'].mean()

            # Calculate change percent
            change_percent = None
            if len(df) >= 2:
                prev_close = df.iloc[-2]['close']
                if prev_close > 0:
                    change_percent = ((latest['close'] - prev_close) / prev_close) * 100

            cursor.execute("""
                INSERT INTO stock.stock_screener
                (ticker, exchange, industry, close, open, high, low, volume,
                 change_percent_1d, market_cap, pe, pb, roe, eps, dividend_yield,
                 rsi14, ma5, ma10, ma20, ma50, avg_trading_value_20d, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ticker) DO UPDATE SET
                    exchange = EXCLUDED.exchange,
                    industry = EXCLUDED.industry,
                    close = EXCLUDED.close,
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    volume = EXCLUDED.volume,
                    change_percent_1d = EXCLUDED.change_percent_1d,
                    market_cap = EXCLUDED.market_cap,
                    pe = EXCLUDED.pe,
                    pb = EXCLUDED.pb,
                    roe = EXCLUDED.roe,
                    eps = EXCLUDED.eps,
                    dividend_yield = EXCLUDED.dividend_yield,
                    rsi14 = EXCLUDED.rsi14,
                    ma5 = EXCLUDED.ma5,
                    ma10 = EXCLUDED.ma10,
                    ma20 = EXCLUDED.ma20,
                    ma50 = EXCLUDED.ma50,
                    avg_trading_value_20d = EXCLUDED.avg_trading_value_20d,
                    updated_at = EXCLUDED.updated_at
            """, (
                ticker,
                exchange,
                industry,
                _to_python(latest['close']),
                _to_python(latest['open']),
                _to_python(latest['high']),
                _to_python(latest['low']),
                _to_python(latest['volume']),
                _to_python(change_percent),
                None,  # market_cap - not available from this source
                _to_python(pe),
                _to_python(pb),
                _to_python(roe),
                _to_python(eps),
                _to_python(dividend_yield),
                _to_python(latest.get('rsi')),
                _to_python(latest.get('ma5')),
                _to_python(latest.get('ma10')),
                _to_python(latest.get('ma20')),
                _to_python(latest.get('ma50')),
                _to_python(avg_trading_value),
                datetime.now()
            ))

            self.db.connection.commit()
            logger.info(f"✅ Saved screener data for {ticker}")
            return True

        except Exception as e:
            logger.error(f"❌ Error saving screener data for {ticker}: {e}")
            self.db.connection.rollback()
            return False

    def save_historical_1d(self, ticker, df):
        """
        Lưu dữ liệu lịch sử ngày vào bảng stock_1d

        Args:
            ticker: Mã cổ phiếu
            df: DataFrame với OHLCV data
        """
        try:
            cursor = self.db.get_cursor()

            inserted = 0
            for _, row in df.iterrows():
                try:
                    cursor.execute("""
                        INSERT INTO stock_1d (ticker, date, open, high, low, close, volume)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (ticker, date) DO UPDATE SET
                            open = EXCLUDED.open,
                            high = EXCLUDED.high,
                            low = EXCLUDED.low,
                            close = EXCLUDED.close,
                            volume = EXCLUDED.volume
                    """, (
                        ticker,
                        row['time'],
                        _to_python(row['open']),
                        _to_python(row['high']),
                        _to_python(row['low']),
                        _to_python(row['close']),
                        _to_python(row['volume'])
                    ))
                    inserted += 1
                except Exception as e:
                    logger.debug(f"Error inserting historical row: {e}")
                    continue

            self.db.connection.commit()
            logger.info(f"✅ Saved {inserted}/{len(df)} historical records for {ticker}")
            return inserted

        except Exception as e:
            logger.error(f"❌ Error saving historical data for {ticker}: {e}")
            self.db.connection.rollback()
            return 0

    def close(self):
        """Đóng kết nối với database"""
        self.db.close()
