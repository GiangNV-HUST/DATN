"""
TCBS API Integration for Stock Screening

Implements real-time stock screening from TCBS API as required in design documentation.

TCBS API provides:
- 80+ screening criteria
- Real-time market data
- Financial ratios
- Technical indicators

Author: Enhanced by AI Assistant
Date: 2026-01-06
"""

import requests
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import time

logger = logging.getLogger(__name__)


class TCBSClient:
    """
    Client for TCBS (Techcombank Securities) Public API

    TCBS provides comprehensive stock market data for Vietnamese stocks.

    Available APIs:
    - Stock screening with 80+ criteria
    - Real-time quotes
    - Financial reports
    - Market overview
    - Industry analysis
    """

    BASE_URL = "https://apipubaws.tcbs.com.vn"

    # API Endpoints
    ENDPOINTS = {
        "screen_stocks": "/stock-insight/v1/stock/sec-filter-result",
        "stock_detail": "/tcanalysis/v1/ticker/{symbol}/overview",
        "financial_ratio": "/tcanalysis/v1/finance/{symbol}/financialratio",
        "balance_sheet": "/tcanalysis/v1/finance/{symbol}/balancesheet",
        "income_statement": "/tcanalysis/v1/finance/{symbol}/incomestatement",
        "cash_flow": "/tcanalysis/v1/finance/{symbol}/cashflow",
        "price_data": "/stock-insight/v1/stock/bars-long-term",
        "market_cap": "/tcanalysis/v1/eva/marketCap",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        })

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.5  # 500ms between requests

        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cache_hits": 0
        }

        # Simple cache
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes

    def _rate_limit(self):
        """Enforce rate limiting"""
        now = time.time()
        time_since_last = now - self.last_request_time

        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """
        Make HTTP request with error handling and rate limiting

        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint
            **kwargs: Additional request parameters

        Returns:
            Response JSON or None if failed
        """
        self._rate_limit()
        self.stats["total_requests"] += 1

        url = f"{self.BASE_URL}{endpoint}"

        try:
            response = self.session.request(method, url, timeout=10, **kwargs)
            response.raise_for_status()

            self.stats["successful_requests"] += 1
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"TCBS API request failed: {e}")
            self.stats["failed_requests"] += 1
            return None

    def screen_stocks(
        self,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        Screen stocks using TCBS filtering API

        TCBS supports 80+ criteria including:
        - Technical: RSI, MACD, MA cross, volume spike, etc.
        - Fundamental: PE, PB, ROE, ROA, EPS growth, debt ratio, etc.
        - Market cap, liquidity, sector, exchange

        Args:
            filters: Dictionary of filter criteria. Examples:
                {
                    "rsi": {"min": 30, "max": 70},
                    "pe": {"min": 5, "max": 20},
                    "pb": {"max": 3},
                    "roe": {"min": 15},
                    "marketCap": {"min": 1000000000000},  # 1T VND
                    "exchange": ["HOSE", "HNX"],
                    "sector": ["Ngân hàng", "Bất động sản"]
                }
            sort_by: Sort field (e.g., "marketCap", "pe", "roe")
            limit: Maximum number of results

        Returns:
            List of stock dictionaries matching criteria
        """
        # Check cache
        cache_key = f"screen_{str(filters)}_{sort_by}_{limit}"
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if time.time() - cache_entry["time"] < self.cache_ttl:
                self.stats["cache_hits"] += 1
                logger.info("📦 Returning cached screening results")
                return cache_entry["data"]

        # Build request payload
        payload = {
            "filter": filters or {},
            "sort": {"sortBy": sort_by or "marketCap", "sortOrder": "desc"},
            "size": limit
        }

        logger.info(f"🔍 Screening stocks with filters: {filters}")

        response = self._request(
            "POST",
            self.ENDPOINTS["screen_stocks"],
            json=payload
        )

        if not response or "data" not in response:
            logger.warning("No screening results returned from TCBS")
            return []

        results = response.get("data", [])

        # Cache results
        self.cache[cache_key] = {
            "data": results,
            "time": time.time()
        }

        logger.info(f"✅ Found {len(results)} stocks matching criteria")
        return results

    def get_stock_detail(self, symbol: str) -> Optional[Dict]:
        """
        Get comprehensive stock details from TCBS

        Returns 70+ fields including:
        - Price data
        - Market cap
        - PE, PB, PS ratios
        - EPS, BVPS
        - Dividend yield
        - Beta
        - 52-week high/low
        - Average volume
        - Outstanding shares
        - Float shares
        """
        endpoint = self.ENDPOINTS["stock_detail"].format(symbol=symbol)

        logger.info(f"📊 Getting stock details for {symbol}")

        response = self._request("GET", endpoint)

        if not response:
            return None

        return response

    def get_financial_ratios(
        self,
        symbol: str,
        period: str = "YEAR",
        count: int = 4
    ) -> Optional[List[Dict]]:
        """
        Get financial ratios time series

        Args:
            symbol: Stock ticker
            period: "YEAR" or "QUARTER"
            count: Number of periods

        Returns:
            List of ratio dictionaries with fields:
            - PE, PB, PS, EV/EBITDA
            - ROE, ROA, ROIC
            - Current ratio, quick ratio
            - Debt/Equity, Debt/Assets
            - Gross margin, operating margin, net margin
            - Asset turnover, inventory turnover
            - EPS, BVPS, revenue per share
        """
        endpoint = self.ENDPOINTS["financial_ratio"].format(symbol=symbol)

        response = self._request(
            "GET",
            endpoint,
            params={"period": period, "count": count}
        )

        if not response or "data" not in response:
            return None

        return response["data"]

    def get_balance_sheet(
        self,
        symbol: str,
        period: str = "YEAR",
        count: int = 4
    ) -> Optional[List[Dict]]:
        """Get balance sheet data"""
        endpoint = self.ENDPOINTS["balance_sheet"].format(symbol=symbol)

        response = self._request(
            "GET",
            endpoint,
            params={"period": period, "count": count}
        )

        if not response or "data" not in response:
            return None

        return response["data"]

    def get_income_statement(
        self,
        symbol: str,
        period: str = "YEAR",
        count: int = 4
    ) -> Optional[List[Dict]]:
        """Get income statement data"""
        endpoint = self.ENDPOINTS["income_statement"].format(symbol=symbol)

        response = self._request(
            "GET",
            endpoint,
            params={"period": period, "count": count}
        )

        if not response or "data" not in response:
            return None

        return response["data"]

    def get_price_data(
        self,
        symbol: str,
        resolution: str = "1D",
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> Optional[List[Dict]]:
        """
        Get historical price data

        Args:
            symbol: Stock ticker
            resolution: "1", "5", "15", "30", "1H", "1D", "1W", "1M"
            from_date: Start date (Unix timestamp)
            to_date: End date (Unix timestamp)

        Returns:
            List of OHLCV bars
        """
        if not from_date:
            # Default: last 90 days
            from_date = str(int(time.time()) - 90 * 24 * 60 * 60)
        if not to_date:
            to_date = str(int(time.time()))

        params = {
            "ticker": symbol,
            "type": resolution,
            "from": from_date,
            "to": to_date
        }

        response = self._request(
            "GET",
            self.ENDPOINTS["price_data"],
            params=params
        )

        if not response or "data" not in response:
            return None

        return response["data"]

    def quick_screen_by_criteria(
        self,
        min_roe: Optional[float] = None,
        max_pe: Optional[float] = None,
        min_market_cap: Optional[float] = None,
        min_rsi: Optional[float] = None,
        max_rsi: Optional[float] = None,
        exchanges: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        Quick screening with common criteria

        Simplified interface for common screening scenarios.

        Args:
            min_roe: Minimum ROE (%)
            max_pe: Maximum PE ratio
            min_market_cap: Minimum market cap (VND)
            min_rsi: Minimum RSI (0-100)
            max_rsi: Maximum RSI (0-100)
            exchanges: List of exchanges ["HOSE", "HNX", "UPCOM"]
            limit: Max results

        Returns:
            List of matching stocks
        """
        filters = {}

        if min_roe is not None:
            filters["roe"] = {"min": min_roe}

        if max_pe is not None:
            filters["pe"] = {"max": max_pe}

        if min_market_cap is not None:
            filters["marketCap"] = {"min": min_market_cap}

        if min_rsi is not None or max_rsi is not None:
            filters["rsi"] = {}
            if min_rsi is not None:
                filters["rsi"]["min"] = min_rsi
            if max_rsi is not None:
                filters["rsi"]["max"] = max_rsi

        if exchanges:
            filters["exchange"] = exchanges

        return self.screen_stocks(filters=filters, limit=limit)

    def get_stats(self) -> Dict:
        """Get API usage statistics"""
        return self.stats.copy()


# ══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════

def translate_criteria_to_tcbs(criteria: Dict) -> Dict:
    """
    Translate generic criteria to TCBS filter format

    This allows compatibility with existing database_tools interface
    while leveraging TCBS API power.

    Args:
        criteria: Generic format like:
            {
                "rsi_below": 70,
                "rsi_above": 30,
                "pe_below": 15,
                "roe_above": 10
            }

    Returns:
        TCBS filter format:
            {
                "rsi": {"min": 30, "max": 70},
                "pe": {"max": 15},
                "roe": {"min": 10}
            }
    """
    tcbs_filter = {}

    # RSI
    if "rsi_above" in criteria or "rsi_below" in criteria:
        tcbs_filter["rsi"] = {}
        if "rsi_above" in criteria:
            tcbs_filter["rsi"]["min"] = criteria["rsi_above"]
        if "rsi_below" in criteria:
            tcbs_filter["rsi"]["max"] = criteria["rsi_below"]

    # PE
    if "pe_below" in criteria:
        tcbs_filter["pe"] = {"max": criteria["pe_below"]}
    if "pe_above" in criteria:
        tcbs_filter["pe"] = tcbs_filter.get("pe", {})
        tcbs_filter["pe"]["min"] = criteria["pe_above"]

    # PB
    if "pb_below" in criteria:
        tcbs_filter["pb"] = {"max": criteria["pb_below"]}
    if "pb_above" in criteria:
        tcbs_filter["pb"] = tcbs_filter.get("pb", {})
        tcbs_filter["pb"]["min"] = criteria["pb_above"]

    # ROE
    if "roe_above" in criteria:
        tcbs_filter["roe"] = {"min": criteria["roe_above"]}
    if "roe_below" in criteria:
        tcbs_filter["roe"] = tcbs_filter.get("roe", {})
        tcbs_filter["roe"]["max"] = criteria["roe_below"]

    # ROA
    if "roa_above" in criteria:
        tcbs_filter["roa"] = {"min": criteria["roa_above"]}

    # Debt/Equity
    if "debt_equity_below" in criteria:
        tcbs_filter["debtOnEquity"] = {"max": criteria["debt_equity_below"]}

    # Market cap
    if "market_cap_above" in criteria:
        tcbs_filter["marketCap"] = {"min": criteria["market_cap_above"]}

    # Price
    if "price_above" in criteria:
        tcbs_filter["price"] = {"min": criteria["price_above"]}
    if "price_below" in criteria:
        tcbs_filter["price"] = tcbs_filter.get("price", {})
        tcbs_filter["price"]["max"] = criteria["price_below"]

    # Volume
    if "volume_above" in criteria:
        tcbs_filter["volume"] = {"min": criteria["volume_above"]}

    # Exchange
    if "exchange" in criteria:
        tcbs_filter["exchange"] = criteria["exchange"]

    # Sector
    if "sector" in criteria:
        tcbs_filter["sector"] = criteria["sector"]

    return tcbs_filter


# ══════════════════════════════════════════════════════════════
# USAGE EXAMPLES (for documentation)
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Example usage
    client = TCBSClient()

    # Example 1: Find value stocks
    print("\n📊 Example 1: Value Stocks (PE < 15, ROE > 15%)")
    value_stocks = client.quick_screen_by_criteria(
        max_pe=15,
        min_roe=15,
        exchanges=["HOSE"],
        limit=10
    )
    print(f"Found {len(value_stocks)} stocks")

    # Example 2: Technical screening
    print("\n📊 Example 2: Oversold stocks (RSI 30-40)")
    oversold = client.quick_screen_by_criteria(
        min_rsi=30,
        max_rsi=40,
        limit=10
    )
    print(f"Found {len(oversold)} stocks")

    # Example 3: Large cap stocks
    print("\n📊 Example 3: Large caps (Market cap > 10T VND)")
    large_caps = client.quick_screen_by_criteria(
        min_market_cap=10_000_000_000_000,
        exchanges=["HOSE"],
        limit=10
    )
    print(f"Found {len(large_caps)} stocks")

    # Stats
    print(f"\n📈 API Stats: {client.get_stats()}")
