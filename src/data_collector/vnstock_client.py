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

    # ========================================================================
    # FINANCIAL DATA METHODS
    # ========================================================================

    def get_balance_sheet(self, ticker, period='quarter'):
        """
        Lấy bảng cân đối kế toán

        Args:
            ticker: Mã cổ phiếu
            period: 'quarter' hoặc 'year'

        Returns:
            DataFrame hoặc None
        """
        try:
            stock = Vnstock().stock(symbol=ticker, source=self.source)
            df = stock.finance.balance_sheet(period=period)

            if df is None or df.empty:
                logger.warning(f"No balance sheet data for {ticker} ({period})")
                return None

            logger.info(f"✅ Fetched balance sheet for {ticker} ({period}): {len(df)} records")
            return df

        except Exception as e:
            logger.error(f"❌ Error fetching balance sheet for {ticker}: {e}")
            return None

    def get_cash_flow(self, ticker, period='quarter'):
        """
        Lấy báo cáo lưu chuyển tiền tệ

        Args:
            ticker: Mã cổ phiếu
            period: 'quarter' hoặc 'year'

        Returns:
            DataFrame hoặc None
        """
        try:
            stock = Vnstock().stock(symbol=ticker, source=self.source)
            df = stock.finance.cash_flow(period=period)

            if df is None or df.empty:
                logger.warning(f"No cash flow data for {ticker} ({period})")
                return None

            logger.info(f"✅ Fetched cash flow for {ticker} ({period}): {len(df)} records")
            return df

        except Exception as e:
            logger.error(f"❌ Error fetching cash flow for {ticker}: {e}")
            return None

    def get_income_statement(self, ticker, period='quarter'):
        """
        Lấy báo cáo kết quả kinh doanh

        Args:
            ticker: Mã cổ phiếu
            period: 'quarter' hoặc 'year'

        Returns:
            DataFrame hoặc None
        """
        try:
            stock = Vnstock().stock(symbol=ticker, source=self.source)
            df = stock.finance.income_statement(period=period)

            if df is None or df.empty:
                logger.warning(f"No income statement data for {ticker} ({period})")
                return None

            logger.info(f"✅ Fetched income statement for {ticker} ({period}): {len(df)} records")
            return df

        except Exception as e:
            logger.error(f"❌ Error fetching income statement for {ticker}: {e}")
            return None

    def get_financial_ratios(self, ticker, period='quarter'):
        """
        Lấy các chỉ số tài chính

        Args:
            ticker: Mã cổ phiếu
            period: 'quarter' hoặc 'year'

        Returns:
            DataFrame hoặc None
        """
        try:
            stock = Vnstock().stock(symbol=ticker, source=self.source)
            df = stock.finance.ratio(period=period)

            if df is None or df.empty:
                logger.warning(f"No financial ratios data for {ticker} ({period})")
                return None

            logger.info(f"✅ Fetched financial ratios for {ticker} ({period}): {len(df)} records")
            return df

        except Exception as e:
            logger.error(f"❌ Error fetching financial ratios for {ticker}: {e}")
            return None

    # ========================================================================
    # COMPANY INFORMATION METHODS
    # ========================================================================

    def get_company_profile(self, ticker):
        """
        Lấy thông tin cơ bản công ty

        Args:
            ticker: Mã cổ phiếu

        Returns:
            dict hoặc DataFrame hoặc None
        """
        try:
            stock = Vnstock().stock(symbol=ticker, source=self.source)
            data = stock.company.profile()

            if data is None or (isinstance(data, pd.DataFrame) and data.empty):
                logger.warning(f"No company profile for {ticker}")
                return None

            logger.info(f"✅ Fetched company profile for {ticker}")
            return data

        except Exception as e:
            logger.error(f"❌ Error fetching company profile for {ticker}: {e}")
            return None

    def get_company_overview(self, ticker):
        """
        Lấy tổng quan công ty

        Args:
            ticker: Mã cổ phiếu

        Returns:
            dict hoặc DataFrame hoặc None
        """
        try:
            stock = Vnstock().stock(symbol=ticker, source=self.source)
            data = stock.company.overview()

            if data is None or (isinstance(data, pd.DataFrame) and data.empty):
                logger.warning(f"No company overview for {ticker}")
                return None

            logger.info(f"✅ Fetched company overview for {ticker}")
            return data

        except Exception as e:
            logger.error(f"❌ Error fetching company overview for {ticker}: {e}")
            return None

    def get_company_officers(self, ticker):
        """
        Lấy thông tin ban lãnh đạo

        Args:
            ticker: Mã cổ phiếu

        Returns:
            DataFrame hoặc None
        """
        try:
            stock = Vnstock().stock(symbol=ticker, source=self.source)
            df = stock.company.officers()

            if df is None or df.empty:
                logger.warning(f"No officers data for {ticker}")
                return None

            logger.info(f"✅ Fetched officers for {ticker}: {len(df)} records")
            return df

        except Exception as e:
            logger.error(f"❌ Error fetching officers for {ticker}: {e}")
            return None

    def get_company_shareholders(self, ticker):
        """
        Lấy thông tin cổ đông

        Args:
            ticker: Mã cổ phiếu

        Returns:
            DataFrame hoặc None
        """
        try:
            stock = Vnstock().stock(symbol=ticker, source=self.source)
            df = stock.company.shareholders()

            if df is None or df.empty:
                logger.warning(f"No shareholders data for {ticker}")
                return None

            logger.info(f"✅ Fetched shareholders for {ticker}: {len(df)} records")
            return df

        except Exception as e:
            logger.error(f"❌ Error fetching shareholders for {ticker}: {e}")
            return None

