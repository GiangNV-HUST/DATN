import sys
from unittest.mock import MagicMock

# Workaround: Mock wordcloud module trước khi import vnstock
# Vì vnstock_ezchart cần wordcloud nhưng chúng ta không dùng chart
sys.modules['wordcloud'] = MagicMock()

from vnstock import Vnstock
import pandas as pd
from datetime import datetime, timedelta
import pytz
import logging

logger = logging.getLogger(__name__)


class VnStockClient:
    def __init__(self, source="VCI"):
        self.source = source

    def get_intraday_data(self, ticker, date=None, interval="1m"):
        """
        Lấy dữ liệu phút từ VnStock

        Args:
            ticker: Mã cổ phiếu (VD: 'VNM', 'VCB')
            date: Ngày lấy dữ liệu (YYYY-MM-DD). Mặc định ngày hôm nay
            interval: Khoảng thời gian ('1m', '5m', '15m', '30m', '1h')

        Returns:
            DataFrame hoặc None nếu có lỗi
        """
        try:
            if date is None:
                vietnam_tz = pytz.timezone("Asia/Ho_Chi_Minh")
                date = datetime.now(vietnam_tz).strftime("%Y-%m-%d")

            stock = Vnstock().stock(symbol=ticker, source=self.source)
            df = stock.quote.history(start=date, end=date, interval=interval)

            if df.empty:
                logger.warning(f"No data for {ticker} on {date}")
                return None

            # Xử lý dữ liệu
            df = df.dropna(subset=["open"])
            logger.info(f"✅ Fetch {len(df)} records for {ticker}")
            return df

        except Exception as e:
            logger.error(f"❌ Error fetching {ticker}: {e}")
            return None

    def get_daily_data(self, ticker, start_date=None, end_date=None):
        """
        Lấy dữ liệu ngày

        Args:
            ticker: Mã cổ phiếu
            start_date: Ngày bắt đầu (YYYY-MM-DD)
            end_date: Ngày kết thúc (YYYY-MM-DD)

        Returns:
            DataFrame
        """
        try:
            if end_date is None:
                end_date = datetime.now().strftime("%Y-%m-%d")
            if start_date is None:
                # Lấy 150 ngày gần nhất
                start_date = (datetime.now() - timedelta(days=150)).strftime("%Y-%m-%d")

            stock = Vnstock().stock(symbol=ticker, source=self.source)
            df = stock.quote.history(start=start_date, end=end_date, interval="1D")

            if df.empty:
                logger.warning(f"No daily data for {ticker}")

            df = df.dropna(subset=["open"])
            logger.info(f"✅ Fetched {len(df)} daily records for {ticker}")
            return df

        except Exception as e:
            logger.error(f"❌ Error fetching daily data for {ticker}: {e}")
            return None

