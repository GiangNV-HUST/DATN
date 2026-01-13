"""
Minute Data Scheduler
Lập lịch lấy dữ liệu cổ phiếu theo phút trong giờ giao dịch
Thị trường Việt Nam: 9:00-11:30 và 13:00-15:00 (GMT+7)
"""
import asyncio
import logging
import sys
import os
from datetime import datetime, time as dt_time
from typing import List, Optional
import schedule
import threading

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.database.data_saver import DataSaver
from src.mcp_server.shared.database import VN30_STOCKS

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MinuteDataScheduler:
    """
    Scheduler để lấy dữ liệu cổ phiếu theo phút

    Features:
    - Chạy trong giờ giao dịch (9:00-11:30 và 13:00-15:00)
    - Lấy dữ liệu intraday từ VCI API
    - Lưu vào database (bảng stock.stock_price_1m)
    - Hỗ trợ VN30 stocks
    """

    # Giờ giao dịch Việt Nam (GMT+7)
    TRADING_SESSIONS = [
        (dt_time(9, 0), dt_time(11, 30)),   # Phiên sáng
        (dt_time(13, 0), dt_time(15, 0)),   # Phiên chiều
    ]

    def __init__(self, symbols: Optional[List[str]] = None, interval_minutes: int = 1):
        """
        Khởi tạo scheduler

        Args:
            symbols: Danh sách mã cổ phiếu (mặc định: VN30)
            interval_minutes: Khoảng thời gian giữa các lần lấy dữ liệu (phút)
        """
        self.symbols = symbols or list(VN30_STOCKS.keys())
        self.interval_minutes = interval_minutes
        self.data_saver = None
        self.is_running = False
        self._stop_event = threading.Event()

        logger.info(f"MinuteDataScheduler initialized with {len(self.symbols)} symbols, interval: {interval_minutes} min")

    def _is_trading_hours(self) -> bool:
        """Kiểm tra xem có đang trong giờ giao dịch không"""
        now = datetime.now().time()

        for start_time, end_time in self.TRADING_SESSIONS:
            if start_time <= now <= end_time:
                return True

        return False

    def _is_trading_day(self) -> bool:
        """Kiểm tra xem có phải ngày giao dịch không (T2-T6)"""
        today = datetime.now().weekday()
        return today < 5  # 0-4: Monday to Friday

    def _fetch_intraday_data(self, symbol: str) -> Optional[dict]:
        """
        Lấy dữ liệu intraday cho 1 mã cổ phiếu

        Args:
            symbol: Mã cổ phiếu

        Returns:
            DataFrame với columns: time, open, high, low, close, volume
        """
        try:
            from vnstock import Vnstock

            stock = Vnstock().stock(symbol=symbol.upper(), source='VCI')
            intraday = stock.quote.intraday()

            if intraday is not None and not intraday.empty:
                # Chuyển đổi format
                intraday = intraday.rename(columns={
                    'price': 'close',
                    'vol': 'volume'
                })

                # Thêm OHLC nếu chưa có
                if 'open' not in intraday.columns:
                    intraday['open'] = intraday['close']
                if 'high' not in intraday.columns:
                    intraday['high'] = intraday['close']
                if 'low' not in intraday.columns:
                    intraday['low'] = intraday['close']

                return intraday

            return None

        except Exception as e:
            logger.error(f"Error fetching intraday data for {symbol}: {e}")
            return None

    def collect_minute_data(self):
        """Thu thập dữ liệu phút cho tất cả symbols"""
        if not self._is_trading_day():
            logger.info("Not a trading day, skipping data collection")
            return

        if not self._is_trading_hours():
            logger.debug("Outside trading hours, skipping data collection")
            return

        logger.info(f"Starting minute data collection for {len(self.symbols)} symbols")

        # Khởi tạo DataSaver nếu chưa có
        if self.data_saver is None:
            self.data_saver = DataSaver()

        success_count = 0
        error_count = 0

        for symbol in self.symbols:
            try:
                intraday_df = self._fetch_intraday_data(symbol)

                if intraday_df is not None and not intraday_df.empty:
                    # Chỉ lấy record mới nhất
                    latest_record = intraday_df.tail(1)

                    # Lưu vào database
                    self.data_saver.save_1m_data(symbol, latest_record)
                    success_count += 1
                else:
                    logger.warning(f"No intraday data for {symbol}")
                    error_count += 1

            except Exception as e:
                logger.error(f"Error collecting data for {symbol}: {e}")
                error_count += 1

        logger.info(f"Data collection completed: {success_count} success, {error_count} errors")

    def collect_all_intraday_data(self):
        """
        Thu thập toàn bộ dữ liệu intraday trong ngày cho tất cả symbols
        Sử dụng khi cần backfill dữ liệu
        """
        if not self._is_trading_day():
            logger.info("Not a trading day, skipping")
            return

        logger.info(f"Collecting all intraday data for {len(self.symbols)} symbols")

        if self.data_saver is None:
            self.data_saver = DataSaver()

        success_count = 0
        total_records = 0

        for symbol in self.symbols:
            try:
                intraday_df = self._fetch_intraday_data(symbol)

                if intraday_df is not None and not intraday_df.empty:
                    self.data_saver.save_1m_data(symbol, intraday_df)
                    success_count += 1
                    total_records += len(intraday_df)
                    logger.info(f"Saved {len(intraday_df)} records for {symbol}")

            except Exception as e:
                logger.error(f"Error collecting data for {symbol}: {e}")

        logger.info(f"Backfill completed: {success_count} symbols, {total_records} total records")

    def start(self):
        """Bắt đầu scheduler"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return

        self.is_running = True
        self._stop_event.clear()

        # Schedule job mỗi phút
        schedule.every(self.interval_minutes).minutes.do(self.collect_minute_data)

        logger.info(f"Scheduler started with {self.interval_minutes} minute interval")
        logger.info(f"Trading hours: {self.TRADING_SESSIONS}")

        # Chạy ngay lập tức nếu đang trong giờ giao dịch
        if self._is_trading_hours() and self._is_trading_day():
            self.collect_minute_data()

        # Vòng lặp chính
        while not self._stop_event.is_set():
            schedule.run_pending()
            self._stop_event.wait(timeout=1)

        logger.info("Scheduler stopped")

    def start_async(self):
        """Chạy scheduler trong background thread"""
        thread = threading.Thread(target=self.start, daemon=True)
        thread.start()
        return thread

    def stop(self):
        """Dừng scheduler"""
        self._stop_event.set()
        self.is_running = False

        if self.data_saver:
            self.data_saver.close()
            self.data_saver = None

        logger.info("Scheduler stopped")

    def get_status(self) -> dict:
        """Lấy trạng thái scheduler"""
        return {
            "is_running": self.is_running,
            "is_trading_hours": self._is_trading_hours(),
            "is_trading_day": self._is_trading_day(),
            "symbols_count": len(self.symbols),
            "interval_minutes": self.interval_minutes,
            "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }


def main():
    """Main function để chạy scheduler"""
    import argparse

    parser = argparse.ArgumentParser(description='Minute Data Scheduler for VN30 Stocks')
    parser.add_argument('--interval', type=int, default=1, help='Interval in minutes (default: 1)')
    parser.add_argument('--symbols', nargs='+', help='List of symbols (default: VN30)')
    parser.add_argument('--backfill', action='store_true', help='Backfill all intraday data')
    args = parser.parse_args()

    scheduler = MinuteDataScheduler(
        symbols=args.symbols,
        interval_minutes=args.interval
    )

    if args.backfill:
        scheduler.collect_all_intraday_data()
    else:
        try:
            scheduler.start()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
            scheduler.stop()


if __name__ == "__main__":
    main()
