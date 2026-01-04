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

    def get_predictions(self, ticker, table_type="3d"):
        """
        Lấy dự đoán giá (hỗ trợ cả 3 ngày và 48 ngày)

        Args:
            ticker: Mã cổ phiếu
            table_type: "3d" cho dự đoán 3 ngày, "48d" cho dự đoán 48 ngày

        Returns:
            dict: Predictions dựa vào table_type
                - 3d: {day1, day2, day3}
                - 48d: {day1, day2, ..., day48}
        """
        try:
            cursor = self.db.get_cursor()

            if table_type == "3d":
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

            elif table_type == "48d":
                # Tạo danh sách cột động cho 48 ngày
                columns = ", ".join([f"close_next_{i}" for i in range(1, 49)])

                cursor.execute(
                    f"""
                    SELECT {columns}
                    FROM stock.stock_prices_48d_predict
                    WHERE ticker = %s
                    ORDER BY time DESC
                    LIMIT 1
                    """,
                    (ticker,),
                )

                row = cursor.fetchone()

                if row:
                    # Tạo dict kết quả với day1 đến day48
                    result = {}
                    for i in range(1, 49):
                        col_name = f"close_next_{i}"
                        if row[col_name] is not None:
                            result[f"day{i}"] = float(row[col_name])
                    return result

            return None

        except Exception as e:
            logger.warning(f"Predictions not available for {ticker} (table_type={table_type}): {e}")
            # Rollback transaction để tiếp tục
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
                  FROM stock.information
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
    
    # ========== FINANCIAL DATA METHODS ==========

    def get_balance_sheet(self, symbols, year=None, quarter=None):
        """
        Lấy bảng cân đối kế toán

        Args:
            symbols: List mã cổ phiếu hoặc 1 mã
            year: Năm (None = mới nhất)
            quarter: Quý (None = mới nhất)

        Returns:
            dict: {ticker: balance_sheet_data}
        """
        try:
            if isinstance(symbols, str):
                symbols = [symbols]

            cursor = self.db.get_cursor()
            result = {}

            for ticker in symbols:
                query = """
                    SELECT ticker, year, quarter,
                           short_asset, long_asset, short_debt, long_debt, equity
                    FROM stock.balance_sheet
                    WHERE ticker = %s
                """
                params = [ticker]

                if year:
                    query += " AND year = %s"
                    params.append(year)
                if quarter:
                    query += " AND quarter = %s"
                    params.append(quarter)

                query += " ORDER BY year DESC, quarter DESC LIMIT 1"

                cursor.execute(query, tuple(params))
                row = cursor.fetchone()

                if row:
                    result[ticker] = dict(row)

            return result

        except Exception as e:
            logger.error(f"Error getting balance sheet: {e}")
            return {}

    def get_income_statement(self, symbols, year=None, quarter=None):
        """
        Lấy báo cáo kết quả kinh doanh

        Args:
            symbols: List mã cổ phiếu hoặc 1 mã
            year: Năm (None = mới nhất)
            quarter: Quý (None = mới nhất)

        Returns:
            dict: {ticker: income_statement_data}
        """
        try:
            if isinstance(symbols, str):
                symbols = [symbols]

            cursor = self.db.get_cursor()
            result = {}

            for ticker in symbols:
                query = """
                    SELECT ticker, year, quarter,
                           revenue, cost_of_good_sold, gross_profit,
                           operating_profit, net_income, ebitda
                    FROM stock.income_statement
                    WHERE ticker = %s
                """
                params = [ticker]

                if year:
                    query += " AND year = %s"
                    params.append(year)
                if quarter:
                    query += " AND quarter = %s"
                    params.append(quarter)

                query += " ORDER BY year DESC, quarter DESC LIMIT 1"

                cursor.execute(query, tuple(params))
                row = cursor.fetchone()

                if row:
                    result[ticker] = dict(row)

            return result

        except Exception as e:
            logger.error(f"Error getting income statement: {e}")
            return {}

    def get_cash_flow(self, symbols, year=None, quarter=None):
        """
        Lấy báo cáo lưu chuyển tiền tệ

        Args:
            symbols: List mã cổ phiếu hoặc 1 mã
            year: Năm (None = mới nhất)
            quarter: Quý (None = mới nhất)

        Returns:
            dict: {ticker: cash_flow_data}
        """
        try:
            if isinstance(symbols, str):
                symbols = [symbols]

            cursor = self.db.get_cursor()
            result = {}

            for ticker in symbols:
                query = """
                    SELECT ticker, year, quarter,
                           operating_cf, investing_cf, financing_cf, net_cf
                    FROM stock.cash_flow
                    WHERE ticker = %s
                """
                params = [ticker]

                if year:
                    query += " AND year = %s"
                    params.append(year)
                if quarter:
                    query += " AND quarter = %s"
                    params.append(quarter)

                query += " ORDER BY year DESC, quarter DESC LIMIT 1"

                cursor.execute(query, tuple(params))
                row = cursor.fetchone()

                if row:
                    result[ticker] = dict(row)

            return result

        except Exception as e:
            logger.error(f"Error getting cash flow: {e}")
            return {}

    def get_financial_ratios(self, symbols, year=None, quarter=None):
        """
        Lấy các chỉ số tài chính

        Args:
            symbols: List mã cổ phiếu hoặc 1 mã
            year: Năm (None = mới nhất)
            quarter: Quý (None = mới nhất)

        Returns:
            dict: {ticker: ratios_data}
        """
        try:
            if isinstance(symbols, str):
                symbols = [symbols]

            cursor = self.db.get_cursor()
            result = {}

            for ticker in symbols:
                query = """
                    SELECT ticker, year, quarter,
                           pe, pb, roe, roa, current_ratio, quick_ratio,
                           debt_equity, dividend_yfield
                    FROM stock.ratio
                    WHERE ticker = %s
                """
                params = [ticker]

                if year:
                    query += " AND year = %s"
                    params.append(year)
                if quarter:
                    query += " AND quarter = %s"
                    params.append(quarter)

                query += " ORDER BY year DESC, quarter DESC LIMIT 1"

                cursor.execute(query, tuple(params))
                row = cursor.fetchone()

                if row:
                    result[ticker] = dict(row)

            return result

        except Exception as e:
            logger.error(f"Error getting financial ratios: {e}")
            return {}

    # ========== ALERT MANAGEMENT METHODS ==========

    def create_alert(self, user_id, ticker, alert_type, condition, value):
        """
        Tạo cảnh báo giá cho user

        Args:
            user_id: ID user
            ticker: Mã cổ phiếu
            alert_type: Loại cảnh báo (price, rsi, volume...)
            condition: Điều kiện (above, below, cross_above, cross_below)
            value: Giá trị ngưỡng

        Returns:
            int: alert_id nếu thành công, None nếu thất bại
        """
        try:
            cursor = self.db.get_cursor()

            cursor.execute(
                """
                INSERT INTO stock.alert (user_id, ticker, alert_type, condition, value, is_active)
                VALUES (%s, %s, %s, %s, %s, TRUE)
                RETURNING id
                """,
                (user_id, ticker, alert_type, condition, value)
            )

            alert_id = cursor.fetchone()['id']
            self.db.connection.commit()

            logger.info(f"Created alert {alert_id} for user {user_id}: {ticker} {condition} {value}")
            return alert_id

        except Exception as e:
            logger.error(f"Error creating alert: {e}")
            if self.db.connection:
                self.db.connection.rollback()
            return None

    def get_user_alerts(self, user_id, active_only=True):
        """
        Lấy danh sách cảnh báo của user

        Args:
            user_id: ID user
            active_only: Chỉ lấy alert đang active

        Returns:
            list: Danh sách alerts
        """
        try:
            cursor = self.db.get_cursor()

            query = """
                SELECT id, ticker, alert_type, condition, value, is_active, created_at
                FROM stock.alert
                WHERE user_id = %s
            """

            if active_only:
                query += " AND is_active = TRUE"

            query += " ORDER BY created_at DESC"

            cursor.execute(query, (user_id,))
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Error getting user alerts: {e}")
            return []

    def delete_alert(self, alert_id):
        """
        Xóa cảnh báo

        Args:
            alert_id: ID của alert

        Returns:
            bool: True nếu xóa thành công
        """
        try:
            cursor = self.db.get_cursor()

            cursor.execute(
                """
                DELETE FROM stock.alert
                WHERE id = %s
                """,
                (alert_id,)
            )

            self.db.connection.commit()
            logger.info(f"Deleted alert {alert_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting alert: {e}")
            if self.db.connection:
                self.db.connection.rollback()
            return False

    # ========== SUBSCRIPTION MANAGEMENT METHODS ==========

    def create_subscription(self, user_id, ticker):
        """
        Tạo subscription theo dõi cổ phiếu

        Args:
            user_id: ID user
            ticker: Mã cổ phiếu

        Returns:
            int: subscription_id nếu thành công, None nếu thất bại
        """
        try:
            cursor = self.db.get_cursor()

            # Check if subscription already exists
            cursor.execute(
                """
                SELECT id FROM stock.subscribe
                WHERE user_id = %s AND ticker = %s AND is_active = TRUE
                """,
                (user_id, ticker)
            )

            existing = cursor.fetchone()
            if existing:
                logger.info(f"Subscription already exists for user {user_id}: {ticker}")
                return existing['id']

            # Create new subscription
            cursor.execute(
                """
                INSERT INTO stock.subscribe (user_id, ticker, is_active)
                VALUES (%s, %s, TRUE)
                RETURNING id
                """,
                (user_id, ticker)
            )

            sub_id = cursor.fetchone()['id']
            self.db.connection.commit()

            logger.info(f"Created subscription {sub_id} for user {user_id}: {ticker}")
            return sub_id

        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            if self.db.connection:
                self.db.connection.rollback()
            return None

    def get_user_subscriptions(self, user_id, active_only=True):
        """
        Lấy danh sách cổ phiếu user đang theo dõi

        Args:
            user_id: ID user
            active_only: Chỉ lấy subscription đang active

        Returns:
            list: Danh sách subscriptions
        """
        try:
            cursor = self.db.get_cursor()

            query = """
                SELECT id, ticker, is_active, created_at
                FROM stock.subscribe
                WHERE user_id = %s
            """

            if active_only:
                query += " AND is_active = TRUE"

            query += " ORDER BY created_at DESC"

            cursor.execute(query, (user_id,))
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Error getting user subscriptions: {e}")
            return []

    def delete_subscription(self, subscription_id):
        """
        Xóa subscription

        Args:
            subscription_id: ID của subscription

        Returns:
            bool: True nếu xóa thành công
        """
        try:
            cursor = self.db.get_cursor()

            cursor.execute(
                """
                DELETE FROM stock.subscribe
                WHERE id = %s
                """,
                (subscription_id,)
            )

            self.db.connection.commit()
            logger.info(f"Deleted subscription {subscription_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting subscription: {e}")
            if self.db.connection:
                self.db.connection.rollback()
            return False

    # ========== INTRADAY 1M DATA METHODS (REAL-TIME) ==========

    def get_current_price(self, ticker):
        """
        Lấy giá hiện tại (real-time từ 1M)

        Args:
            ticker: Mã cổ phiếu

        Returns:
            dict: {ticker, time, price, volume, change_from_open}
        """
        try:
            cursor = self.db.get_cursor()

            cursor.execute(
                """
                SELECT ticker, time, close, open, high, low, volume
                FROM stock.stock_prices_1m
                WHERE ticker = %s
                ORDER BY time DESC
                LIMIT 1
                """,
                (ticker,),
            )

            row = cursor.fetchone()

            if row:
                change_pct = ((row['close'] - row['open']) / row['open'] * 100) if row['open'] else 0

                return {
                    "ticker": row["ticker"],
                    "time": str(row["time"]),
                    "close": float(row["close"]),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "volume": int(row["volume"]),
                    "change_from_open_pct": round(change_pct, 2),
                }
            return None

        except Exception as e:
            logger.error(f"Error getting current price for {ticker}: {e}")
            return None

    def get_intraday_movement(self, ticker):
        """
        Lấy biến động trong ngày (từ mở cửa đến giờ)

        Args:
            ticker: Mã cổ phiếu

        Returns:
            dict: {open_price, current_price, high, low, change_pct, volume_today}
        """
        try:
            cursor = self.db.get_cursor()

            cursor.execute(
                """
                SELECT
                    MIN(time) as first_time,
                    MAX(time) as last_time,
                    (array_agg(close ORDER BY time ASC))[1] as open_price,
                    (array_agg(close ORDER BY time DESC))[1] as current_price,
                    MAX(high) as high,
                    MIN(low) as low,
                    SUM(volume) as volume_today
                FROM stock.stock_prices_1m
                WHERE ticker = %s
                AND time >= CURRENT_DATE
                """,
                (ticker,),
            )

            row = cursor.fetchone()

            if row and row['open_price']:
                change_pct = (
                    (row['current_price'] - row['open_price'])
                    / row['open_price'] * 100
                )

                return {
                    "ticker": ticker,
                    "first_time": str(row['first_time']),
                    "last_time": str(row['last_time']),
                    "open_price": float(row['open_price']),
                    "current_price": float(row['current_price']),
                    "high": float(row['high']),
                    "low": float(row['low']),
                    "change_pct": round(change_pct, 2),
                    "volume_today": int(row['volume_today']),
                }
            return None

        except Exception as e:
            logger.error(f"Error getting intraday movement for {ticker}: {e}")
            return None

    def detect_price_spike(self, ticker, threshold_pct=2.0, window_minutes=15):
        """
        Phát hiện tăng/giảm đột biến trong N phút

        Args:
            ticker: Mã cổ phiếu
            threshold_pct: Ngưỡng % thay đổi (default: 2%)
            window_minutes: Cửa sổ thời gian (default: 15 phút)

        Returns:
            dict: {spike_detected, change_pct, from_price, to_price, from_time, to_time}
        """
        try:
            cursor = self.db.get_cursor()

            cursor.execute(
                """
                WITH price_window AS (
                    SELECT time, close
                    FROM stock.stock_prices_1m
                    WHERE ticker = %s
                    AND time >= NOW() - INTERVAL '%s minutes'
                    ORDER BY time
                )
                SELECT
                    MIN(time) as first_time,
                    MAX(time) as last_time,
                    (array_agg(close ORDER BY time ASC))[1] as first_price,
                    (array_agg(close ORDER BY time DESC))[1] as last_price
                FROM price_window
                """,
                (ticker, window_minutes),
            )

            row = cursor.fetchone()

            if row and row['first_price']:
                change_pct = (
                    (row['last_price'] - row['first_price'])
                    / row['first_price'] * 100
                )

                spike_detected = abs(change_pct) >= threshold_pct

                return {
                    "ticker": ticker,
                    "spike_detected": spike_detected,
                    "change_pct": round(change_pct, 2),
                    "from_price": float(row['first_price']),
                    "to_price": float(row['last_price']),
                    "from_time": str(row['first_time']),
                    "to_time": str(row['last_time']),
                    "duration_minutes": window_minutes,
                    "threshold_pct": threshold_pct,
                }
            return None

        except Exception as e:
            logger.error(f"Error detecting price spike for {ticker}: {e}")
            return None

    def get_volume_profile(self, ticker, interval_minutes=30):
        """
        Lấy phân bố volume trong ngày

        Args:
            ticker: Mã cổ phiếu
            interval_minutes: Nhóm theo khung giờ (15, 30, 60 phút)

        Returns:
            list: [{time_bucket, avg_price, total_volume, num_trades}, ...]
        """
        try:
            cursor = self.db.get_cursor()

            # Create time buckets based on interval
            cursor.execute(
                f"""
                SELECT
                    date_trunc('hour', time) +
                    INTERVAL '{interval_minutes} min' *
                    (EXTRACT(minute FROM time)::int / {interval_minutes}) as time_bucket,
                    AVG(close) as avg_price,
                    SUM(volume) as total_volume,
                    COUNT(*) as num_records,
                    MIN(low) as period_low,
                    MAX(high) as period_high
                FROM stock.stock_prices_1m
                WHERE ticker = %s
                AND time >= CURRENT_DATE
                GROUP BY time_bucket
                ORDER BY time_bucket
                """,
                (ticker,),
            )

            rows = cursor.fetchall()

            return [
                {
                    "time_bucket": str(row['time_bucket']),
                    "avg_price": float(row['avg_price']),
                    "total_volume": int(row['total_volume']),
                    "num_records": int(row['num_records']),
                    "period_low": float(row['period_low']),
                    "period_high": float(row['period_high']),
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Error getting volume profile for {ticker}: {e}")
            return []

    def check_alert_conditions_1m(self, ticker, alert_type, condition, value):
        """
        Kiểm tra điều kiện alert với data 1M (real-time)

        Args:
            ticker: Mã cổ phiếu
            alert_type: 'price', 'volume'
            condition: 'above', 'below', 'cross_above', 'cross_below'
            value: Giá trị ngưỡng

        Returns:
            dict: {triggered, current_value, message}
        """
        try:
            cursor = self.db.get_cursor()

            # Lấy data mới nhất (2 records để check cross conditions)
            cursor.execute(
                """
                SELECT time, close, volume
                FROM stock.stock_prices_1m
                WHERE ticker = %s
                ORDER BY time DESC
                LIMIT 2
                """,
                (ticker,),
            )

            rows = cursor.fetchall()

            if not rows or len(rows) < 1:
                return {"triggered": False, "message": "No data available"}

            current = rows[0]
            triggered = False
            message = ""

            if alert_type == 'price':
                current_value = float(current['close'])

                if condition == 'above':
                    triggered = current_value > value
                    message = f"Price {current_value} is above {value}" if triggered else f"Price {current_value} is not above {value}"

                elif condition == 'below':
                    triggered = current_value < value
                    message = f"Price {current_value} is below {value}" if triggered else f"Price {current_value} is not below {value}"

                elif condition == 'cross_above' and len(rows) == 2:
                    prev_value = float(rows[1]['close'])
                    triggered = prev_value <= value < current_value
                    message = f"Price crossed above {value} (from {prev_value} to {current_value})" if triggered else "No cross above detected"

                elif condition == 'cross_below' and len(rows) == 2:
                    prev_value = float(rows[1]['close'])
                    triggered = prev_value >= value > current_value
                    message = f"Price crossed below {value} (from {prev_value} to {current_value})" if triggered else "No cross below detected"

                return {
                    "triggered": triggered,
                    "current_value": current_value,
                    "threshold": value,
                    "message": message,
                    "time": str(current['time']),
                }

            elif alert_type == 'volume':
                current_value = int(current['volume'])
                triggered = current_value > value
                message = f"Volume {current_value} is above threshold {value}" if triggered else f"Volume {current_value} is not above {value}"

                return {
                    "triggered": triggered,
                    "current_value": current_value,
                    "threshold": value,
                    "message": message,
                    "time": str(current['time']),
                }

            return {"triggered": False, "message": f"Unknown alert type: {alert_type}"}

        except Exception as e:
            logger.error(f"Error checking alert conditions: {e}")
            return {"triggered": False, "message": f"Error: {str(e)}"}

    def get_intraday_history(self, ticker, hours=2):
        """
        Lấy lịch sử giá intraday trong N giờ gần nhất

        Args:
            ticker: Mã cổ phiếu
            hours: Số giờ lịch sử (default: 2)

        Returns:
            list: Danh sách giá theo phút
        """
        try:
            cursor = self.db.get_cursor()

            cursor.execute(
                """
                SELECT time, close, volume, high, low
                FROM stock.stock_prices_1m
                WHERE ticker = %s
                AND time >= NOW() - INTERVAL '%s hours'
                ORDER BY time DESC
                """,
                (ticker, hours),
            )

            rows = cursor.fetchall()

            return [
                {
                    "time": str(row["time"]),
                    "close": float(row["close"]),
                    "volume": int(row["volume"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Error getting intraday history: {e}")
            return []

    # ========== TECHNICAL ALERTS METHODS ==========

    def get_technical_alerts(self, ticker=None, alert_type=None, alert_level=None, is_active=True, limit=50):
        """
        Lấy danh sách technical alerts

        Args:
            ticker: Mã cổ phiếu (optional, None = all tickers)
            alert_type: Loại alert (rsi_overbought, golden_cross, etc.) (optional)
            alert_level: Mức độ (critical, warning, info) (optional)
            is_active: Lọc theo trạng thái active (default: True)
            limit: Số lượng alerts tối đa (default: 50)

        Returns:
            list: Danh sách technical alerts
        """
        try:
            cursor = self.db.get_cursor()

            # Build query với các filters
            conditions = []
            params = []

            if ticker:
                conditions.append("ticker = %s")
                params.append(ticker)

            if alert_type:
                conditions.append("alert_type = %s")
                params.append(alert_type)

            if alert_level:
                conditions.append("alert_level = %s")
                params.append(alert_level)

            if is_active is not None:
                conditions.append("is_active = %s")
                params.append(is_active)

            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

            params.append(limit)

            cursor.execute(
                f"""
                SELECT id, ticker, alert_type, alert_level, message,
                       indicator_value, price_at_alert, created_at, is_active
                FROM stock.technical_alerts
                {where_clause}
                ORDER BY created_at DESC
                LIMIT %s
                """,
                tuple(params),
            )

            rows = cursor.fetchall()

            return [
                {
                    "id": row["id"],
                    "ticker": row["ticker"],
                    "alert_type": row["alert_type"],
                    "alert_level": row["alert_level"],
                    "message": row["message"],
                    "indicator_value": row["indicator_value"],
                    "price_at_alert": float(row["price_at_alert"]) if row["price_at_alert"] else None,
                    "created_at": str(row["created_at"]),
                    "is_active": row["is_active"],
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Error getting technical alerts: {e}")
            return []

    def create_technical_alert(self, ticker, alert_type, alert_level, message,
                              indicator_value=None, price_at_alert=None):
        """
        Tạo technical alert mới

        Args:
            ticker: Mã cổ phiếu
            alert_type: Loại alert (rsi_overbought, golden_cross, etc.)
            alert_level: Mức độ (critical, warning, info)
            message: Thông điệp alert
            indicator_value: Giá trị chỉ báo (optional, JSON string)
            price_at_alert: Giá tại thời điểm alert (optional)

        Returns:
            int: Alert ID nếu thành công, None nếu lỗi
        """
        try:
            cursor = self.db.get_cursor()

            cursor.execute(
                """
                INSERT INTO stock.technical_alerts
                (ticker, alert_type, alert_level, message, indicator_value, price_at_alert)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (ticker, alert_type, alert_level, message, indicator_value, price_at_alert),
            )

            result = cursor.fetchone()
            self.db.connection.commit()

            return result["id"] if result else None

        except Exception as e:
            logger.error(f"Error creating technical alert: {e}")
            if self.db.connection:
                self.db.connection.rollback()
            return None

    def mark_technical_alert_inactive(self, alert_id):
        """
        Đánh dấu technical alert là inactive (không xóa, chỉ deactivate)

        Args:
            alert_id: ID của alert

        Returns:
            bool: True nếu thành công
        """
        try:
            cursor = self.db.get_cursor()

            cursor.execute(
                """
                UPDATE stock.technical_alerts
                SET is_active = false
                WHERE id = %s
                """,
                (alert_id,),
            )

            self.db.connection.commit()
            return True

        except Exception as e:
            logger.error(f"Error marking technical alert inactive: {e}")
            if self.db.connection:
                self.db.connection.rollback()
            return False

    def get_latest_technical_alerts_by_ticker(self, ticker, hours=24):
        """
        Lấy các technical alerts mới nhất cho ticker trong N giờ

        Args:
            ticker: Mã cổ phiếu
            hours: Số giờ gần nhất (default: 24)

        Returns:
            list: Danh sách alerts
        """
        try:
            cursor = self.db.get_cursor()

            cursor.execute(
                """
                SELECT id, ticker, alert_type, alert_level, message,
                       indicator_value, price_at_alert, created_at, is_active
                FROM stock.technical_alerts
                WHERE ticker = %s
                AND created_at >= NOW() - INTERVAL '%s hours'
                AND is_active = true
                ORDER BY created_at DESC
                """,
                (ticker, hours),
            )

            rows = cursor.fetchall()

            return [
                {
                    "id": row["id"],
                    "ticker": row["ticker"],
                    "alert_type": row["alert_type"],
                    "alert_level": row["alert_level"],
                    "message": row["message"],
                    "indicator_value": row["indicator_value"],
                    "price_at_alert": float(row["price_at_alert"]) if row["price_at_alert"] else None,
                    "created_at": str(row["created_at"]),
                    "is_active": row["is_active"],
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Error getting latest technical alerts: {e}")
            return []

    def get_critical_technical_alerts(self, hours=24):
        """
        Lấy tất cả critical alerts trong N giờ (cho tất cả tickers)

        Args:
            hours: Số giờ gần nhất (default: 24)

        Returns:
            list: Danh sách critical alerts
        """
        try:
            cursor = self.db.get_cursor()

            cursor.execute(
                """
                SELECT id, ticker, alert_type, alert_level, message,
                       indicator_value, price_at_alert, created_at, is_active
                FROM stock.technical_alerts
                WHERE alert_level = 'critical'
                AND created_at >= NOW() - INTERVAL '%s hours'
                AND is_active = true
                ORDER BY created_at DESC
                """,
                (hours,),
            )

            rows = cursor.fetchall()

            return [
                {
                    "id": row["id"],
                    "ticker": row["ticker"],
                    "alert_type": row["alert_type"],
                    "alert_level": row["alert_level"],
                    "message": row["message"],
                    "indicator_value": row["indicator_value"],
                    "price_at_alert": float(row["price_at_alert"]) if row["price_at_alert"] else None,
                    "created_at": str(row["created_at"]),
                    "is_active": row["is_active"],
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Error getting critical technical alerts: {e}")
            return []

    def close(self):
        """Đóng database connection"""
        if self.db:
            self.db.close()

