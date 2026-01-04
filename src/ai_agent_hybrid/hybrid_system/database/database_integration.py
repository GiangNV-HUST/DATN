"""
Database Integration Layer for Hybrid System

Provides bridge between Hybrid system and Final database (DatabaseTools).
This allows Hybrid agents to access all database functionality.
"""

import sys
import os

# Add root directory to path to enable "from src..." imports
root_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')
sys.path.insert(0, root_dir)

# Now import from src (as Final's database_tools expects)
from src.AI_agent.database_tools import DatabaseTools
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class HybridDatabaseClient:
    """
    Wrapper around DatabaseTools for Hybrid System

    Provides all database functionality with caching and error handling.
    """

    def __init__(self):
        """Initialize with DatabaseTools"""
        self.db_tools = DatabaseTools()
        self.cache = {}
        self.stats = {
            "total_calls": 0,
            "errors": 0,
            "cache_hits": 0
        }

    def _cache_key(self, method: str, **kwargs) -> str:
        """Generate cache key"""
        import hashlib
        import json
        key_str = f"{method}:{json.dumps(kwargs, sort_keys=True)}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _cache_get(self, key: str, ttl: int = 60) -> Optional[Any]:
        """Get from cache with TTL check"""
        if key in self.cache:
            data, timestamp = self.cache[key]
            import time
            if time.time() - timestamp < ttl:
                self.stats["cache_hits"] += 1
                return data
        return None

    def _cache_set(self, key: str, value: Any):
        """Set cache value"""
        import time
        self.cache[key] = (value, time.time())

    # ========== STOCK DATA METHODS ==========

    def get_latest_price(self, ticker: str) -> Optional[Dict]:
        """
        Get latest price + indicators

        Args:
            ticker: Stock symbol

        Returns:
            Dict with price, volume, ma5, ma20, rsi, macd
        """
        self.stats["total_calls"] += 1
        cache_key = self._cache_key("get_latest_price", ticker=ticker)

        # Check cache (30s TTL for real-time data)
        cached = self._cache_get(cache_key, ttl=30)
        if cached:
            return cached

        try:
            result = self.db_tools.get_latest_price(ticker)
            if result:
                self._cache_set(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"Error getting latest price for {ticker}: {e}")
            self.stats["errors"] += 1
            return None

    def get_price_history(self, ticker: str, days: int = 30) -> List[Dict]:
        """
        Get price history

        Args:
            ticker: Stock symbol
            days: Number of days

        Returns:
            List of price data
        """
        self.stats["total_calls"] += 1
        cache_key = self._cache_key("get_price_history", ticker=ticker, days=days)

        # Check cache (5 minutes TTL)
        cached = self._cache_get(cache_key, ttl=300)
        if cached:
            return cached

        try:
            result = self.db_tools.get_price_history(ticker, days)
            if result:
                self._cache_set(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"Error getting price history for {ticker}: {e}")
            self.stats["errors"] += 1
            return []

    def get_company_info(self, ticker: str) -> Optional[Dict]:
        """
        Get company information

        Args:
            ticker: Stock symbol

        Returns:
            Dict with company name, industry, employees, website
        """
        self.stats["total_calls"] += 1
        cache_key = self._cache_key("get_company_info", ticker=ticker)

        # Check cache (1 hour TTL - company info doesn't change often)
        cached = self._cache_get(cache_key, ttl=3600)
        if cached:
            return cached

        try:
            result = self.db_tools.get_company_info(ticker)
            if result:
                self._cache_set(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"Error getting company info for {ticker}: {e}")
            self.stats["errors"] += 1
            return None

    def search_stocks_by_criteria(self, criteria: Dict) -> List[str]:
        """
        Search stocks matching criteria

        Args:
            criteria: Dict with rsi_below, rsi_above, price_below, price_above, min_volume

        Returns:
            List of ticker symbols
        """
        self.stats["total_calls"] += 1
        cache_key = self._cache_key("search_stocks_by_criteria", **criteria)

        # Check cache (5 minutes TTL)
        cached = self._cache_get(cache_key, ttl=300)
        if cached:
            return cached

        try:
            result = self.db_tools.search_stocks_by_criteria(criteria)
            if result:
                self._cache_set(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"Error searching stocks: {e}")
            self.stats["errors"] += 1
            return []

    # ========== PREDICTION METHODS ==========

    def get_predictions(self, ticker: str, table_type: str = "3d") -> Optional[Dict]:
        """
        Get price predictions

        Args:
            ticker: Stock symbol
            table_type: "3d" or "48d"

        Returns:
            Dict with predictions
        """
        self.stats["total_calls"] += 1
        cache_key = self._cache_key("get_predictions", ticker=ticker, table_type=table_type)

        # Check cache (1 hour TTL)
        cached = self._cache_get(cache_key, ttl=3600)
        if cached:
            return cached

        try:
            result = self.db_tools.get_predictions(ticker, table_type)
            if result:
                self._cache_set(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"Error getting predictions for {ticker}: {e}")
            self.stats["errors"] += 1
            return None

    # ========== FINANCIAL DATA METHODS ==========

    def get_balance_sheet(
        self,
        symbols: List[str],
        year: Optional[int] = None,
        quarter: Optional[int] = None
    ) -> List[Dict]:
        """
        Get balance sheet data

        Args:
            symbols: List of stock symbols
            year: Year (optional)
            quarter: Quarter 1-4 (optional)

        Returns:
            List of balance sheet data
        """
        self.stats["total_calls"] += 1
        cache_key = self._cache_key("get_balance_sheet", symbols=symbols, year=year, quarter=quarter)

        # Check cache (1 day TTL - financial reports don't change often)
        cached = self._cache_get(cache_key, ttl=86400)
        if cached:
            return cached

        try:
            result = self.db_tools.get_balance_sheet(symbols, year, quarter)
            if result:
                self._cache_set(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"Error getting balance sheet: {e}")
            self.stats["errors"] += 1
            return []

    def get_income_statement(
        self,
        symbols: List[str],
        year: Optional[int] = None,
        quarter: Optional[int] = None
    ) -> List[Dict]:
        """
        Get income statement data

        Args:
            symbols: List of stock symbols
            year: Year (optional)
            quarter: Quarter 1-4 (optional)

        Returns:
            List of income statement data
        """
        self.stats["total_calls"] += 1
        cache_key = self._cache_key("get_income_statement", symbols=symbols, year=year, quarter=quarter)

        # Check cache (1 day TTL)
        cached = self._cache_get(cache_key, ttl=86400)
        if cached:
            return cached

        try:
            result = self.db_tools.get_income_statement(symbols, year, quarter)
            if result:
                self._cache_set(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"Error getting income statement: {e}")
            self.stats["errors"] += 1
            return []

    def get_cash_flow(
        self,
        symbols: List[str],
        year: Optional[int] = None,
        quarter: Optional[int] = None
    ) -> List[Dict]:
        """
        Get cash flow data

        Args:
            symbols: List of stock symbols
            year: Year (optional)
            quarter: Quarter 1-4 (optional)

        Returns:
            List of cash flow data
        """
        self.stats["total_calls"] += 1
        cache_key = self._cache_key("get_cash_flow", symbols=symbols, year=year, quarter=quarter)

        # Check cache (1 day TTL)
        cached = self._cache_get(cache_key, ttl=86400)
        if cached:
            return cached

        try:
            result = self.db_tools.get_cash_flow(symbols, year, quarter)
            if result:
                self._cache_set(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"Error getting cash flow: {e}")
            self.stats["errors"] += 1
            return []

    def get_financial_ratios(
        self,
        symbols: List[str],
        year: Optional[int] = None,
        quarter: Optional[int] = None
    ) -> List[Dict]:
        """
        Get financial ratios

        Args:
            symbols: List of stock symbols
            year: Year (optional)
            quarter: Quarter 1-4 (optional)

        Returns:
            List of financial ratios (PE, PB, ROE, ROA, etc.)
        """
        self.stats["total_calls"] += 1
        cache_key = self._cache_key("get_financial_ratios", symbols=symbols, year=year, quarter=quarter)

        # Check cache (1 day TTL)
        cached = self._cache_get(cache_key, ttl=86400)
        if cached:
            return cached

        try:
            result = self.db_tools.get_financial_ratios(symbols, year, quarter)
            if result:
                self._cache_set(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"Error getting financial ratios: {e}")
            self.stats["errors"] += 1
            return []

    # ========== ALERT MANAGEMENT METHODS ==========

    def create_alert(
        self,
        user_id: str,
        ticker: str,
        alert_type: str,
        condition: str,
        value: float
    ) -> bool:
        """
        Create price alert

        Args:
            user_id: User ID
            ticker: Stock symbol
            alert_type: Type of alert (e.g., "price")
            condition: Condition (">", "<", ">=", "<=", "=")
            value: Target value

        Returns:
            True if successful
        """
        self.stats["total_calls"] += 1

        try:
            result = self.db_tools.create_alert(user_id, ticker, alert_type, condition, value)
            return result
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
            self.stats["errors"] += 1
            return False

    def get_user_alerts(self, user_id: str, active_only: bool = True) -> List[Dict]:
        """
        Get user alerts

        Args:
            user_id: User ID
            active_only: Only return active alerts

        Returns:
            List of alerts
        """
        self.stats["total_calls"] += 1
        cache_key = self._cache_key("get_user_alerts", user_id=user_id, active_only=active_only)

        # Check cache (30s TTL)
        cached = self._cache_get(cache_key, ttl=30)
        if cached:
            return cached

        try:
            result = self.db_tools.get_user_alerts(user_id, active_only)
            if result:
                self._cache_set(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"Error getting user alerts: {e}")
            self.stats["errors"] += 1
            return []

    def delete_alert(self, alert_id: int) -> bool:
        """
        Delete alert

        Args:
            alert_id: Alert ID

        Returns:
            True if successful
        """
        self.stats["total_calls"] += 1

        try:
            result = self.db_tools.delete_alert(alert_id)
            return result
        except Exception as e:
            logger.error(f"Error deleting alert: {e}")
            self.stats["errors"] += 1
            return False

    # ========== SUBSCRIPTION MANAGEMENT METHODS ==========

    def create_subscription(self, user_id: str, ticker: str) -> bool:
        """
        Create subscription

        Args:
            user_id: User ID
            ticker: Stock symbol

        Returns:
            True if successful
        """
        self.stats["total_calls"] += 1

        try:
            result = self.db_tools.create_subscription(user_id, ticker)
            return result
        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            self.stats["errors"] += 1
            return False

    def get_user_subscriptions(self, user_id: str, active_only: bool = True) -> List[Dict]:
        """
        Get user subscriptions

        Args:
            user_id: User ID
            active_only: Only return active subscriptions

        Returns:
            List of subscriptions
        """
        self.stats["total_calls"] += 1
        cache_key = self._cache_key("get_user_subscriptions", user_id=user_id, active_only=active_only)

        # Check cache (1 minute TTL)
        cached = self._cache_get(cache_key, ttl=60)
        if cached:
            return cached

        try:
            result = self.db_tools.get_user_subscriptions(user_id, active_only)
            if result:
                self._cache_set(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"Error getting user subscriptions: {e}")
            self.stats["errors"] += 1
            return []

    def delete_subscription(self, subscription_id: int) -> bool:
        """
        Delete subscription

        Args:
            subscription_id: Subscription ID

        Returns:
            True if successful
        """
        self.stats["total_calls"] += 1

        try:
            result = self.db_tools.delete_subscription(subscription_id)
            return result
        except Exception as e:
            logger.error(f"Error deleting subscription: {e}")
            self.stats["errors"] += 1
            return False

    # ========== INTRADAY 1M DATA METHODS (REAL-TIME) ==========

    def get_current_price(self, ticker: str) -> Optional[Dict]:
        """
        Get current price from 1M data (real-time)

        Args:
            ticker: Stock symbol

        Returns:
            Dict with current price, volume, and change from open
        """
        self.stats["total_calls"] += 1
        cache_key = self._cache_key("get_current_price", ticker=ticker)

        # Check cache (15s TTL for near real-time)
        cached = self._cache_get(cache_key, ttl=15)
        if cached:
            return cached

        try:
            result = self.db_tools.get_current_price(ticker)
            if result:
                self._cache_set(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"Error getting current price for {ticker}: {e}")
            self.stats["errors"] += 1
            return None

    def get_intraday_movement(self, ticker: str) -> Optional[Dict]:
        """
        Get intraday price movement (from open to now)

        Args:
            ticker: Stock symbol

        Returns:
            Dict with open, current, high, low, change%, volume
        """
        self.stats["total_calls"] += 1
        cache_key = self._cache_key("get_intraday_movement", ticker=ticker)

        # Cache 30s
        cached = self._cache_get(cache_key, ttl=30)
        if cached:
            return cached

        try:
            result = self.db_tools.get_intraday_movement(ticker)
            if result:
                self._cache_set(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"Error getting intraday movement for {ticker}: {e}")
            self.stats["errors"] += 1
            return None

    def detect_price_spike(
        self,
        ticker: str,
        threshold_pct: float = 2.0,
        window_minutes: int = 15
    ) -> Optional[Dict]:
        """
        Detect price spike in recent minutes

        Args:
            ticker: Stock symbol
            threshold_pct: Threshold percentage (default: 2%)
            window_minutes: Time window in minutes (default: 15)

        Returns:
            Dict with spike_detected, change%, from/to prices
        """
        self.stats["total_calls"] += 1

        # No cache - always fresh check for spikes
        try:
            result = self.db_tools.detect_price_spike(
                ticker, threshold_pct, window_minutes
            )
            return result
        except Exception as e:
            logger.error(f"Error detecting price spike for {ticker}: {e}")
            self.stats["errors"] += 1
            return None

    def get_volume_profile(
        self,
        ticker: str,
        interval_minutes: int = 30
    ) -> List[Dict]:
        """
        Get volume profile for the day

        Args:
            ticker: Stock symbol
            interval_minutes: Grouping interval (15, 30, 60 minutes)

        Returns:
            List of volume data by time bucket
        """
        self.stats["total_calls"] += 1
        cache_key = self._cache_key(
            "get_volume_profile",
            ticker=ticker,
            interval_minutes=interval_minutes
        )

        # Cache 5 minutes
        cached = self._cache_get(cache_key, ttl=300)
        if cached:
            return cached

        try:
            result = self.db_tools.get_volume_profile(ticker, interval_minutes)
            if result:
                self._cache_set(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"Error getting volume profile for {ticker}: {e}")
            self.stats["errors"] += 1
            return []

    def check_alert_conditions_1m(
        self,
        ticker: str,
        alert_type: str,
        condition: str,
        value: float
    ) -> Dict:
        """
        Check alert conditions with 1M data (real-time)

        Args:
            ticker: Stock symbol
            alert_type: 'price' or 'volume'
            condition: 'above', 'below', 'cross_above', 'cross_below'
            value: Threshold value

        Returns:
            Dict with triggered status and message
        """
        self.stats["total_calls"] += 1

        # No cache - always fresh check for alerts
        try:
            result = self.db_tools.check_alert_conditions_1m(
                ticker, alert_type, condition, value
            )
            return result
        except Exception as e:
            logger.error(f"Error checking alert conditions: {e}")
            self.stats["errors"] += 1
            return {"triggered": False, "message": f"Error: {str(e)}"}

    def get_intraday_history(
        self,
        ticker: str,
        hours: int = 2
    ) -> List[Dict]:
        """
        Get intraday price history for recent hours

        Args:
            ticker: Stock symbol
            hours: Number of hours (default: 2)

        Returns:
            List of 1-minute price data
        """
        self.stats["total_calls"] += 1
        cache_key = self._cache_key(
            "get_intraday_history",
            ticker=ticker,
            hours=hours
        )

        # Cache 1 minute
        cached = self._cache_get(cache_key, ttl=60)
        if cached:
            return cached

        try:
            result = self.db_tools.get_intraday_history(ticker, hours)
            if result:
                self._cache_set(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"Error getting intraday history for {ticker}: {e}")
            self.stats["errors"] += 1
            return []

    # ========== TECHNICAL ALERTS METHODS ==========

    def get_technical_alerts(
        self,
        ticker: Optional[str] = None,
        alert_type: Optional[str] = None,
        alert_level: Optional[str] = None,
        is_active: bool = True,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get technical alerts with filters

        Args:
            ticker: Stock symbol (optional)
            alert_type: Alert type filter (optional)
            alert_level: Alert level filter (critical, warning, info) (optional)
            is_active: Filter by active status (default: True)
            limit: Maximum number of alerts (default: 50)

        Returns:
            List of technical alerts
        """
        self.stats["total_calls"] += 1
        cache_key = self._cache_key(
            "get_technical_alerts",
            ticker=ticker,
            alert_type=alert_type,
            alert_level=alert_level,
            is_active=is_active,
            limit=limit
        )

        # Cache 2 minutes
        cached = self._cache_get(cache_key, ttl=120)
        if cached:
            return cached

        try:
            result = self.db_tools.get_technical_alerts(
                ticker, alert_type, alert_level, is_active, limit
            )
            if result:
                self._cache_set(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"Error getting technical alerts: {e}")
            self.stats["errors"] += 1
            return []

    def create_technical_alert(
        self,
        ticker: str,
        alert_type: str,
        alert_level: str,
        message: str,
        indicator_value: Optional[str] = None,
        price_at_alert: Optional[float] = None
    ) -> Optional[int]:
        """
        Create a new technical alert

        Args:
            ticker: Stock symbol
            alert_type: Alert type (rsi_overbought, golden_cross, etc.)
            alert_level: Alert level (critical, warning, info)
            message: Alert message
            indicator_value: Indicator value as JSON string (optional)
            price_at_alert: Price at alert time (optional)

        Returns:
            Alert ID if successful, None otherwise
        """
        self.stats["total_calls"] += 1

        try:
            result = self.db_tools.create_technical_alert(
                ticker, alert_type, alert_level, message,
                indicator_value, price_at_alert
            )
            return result
        except Exception as e:
            logger.error(f"Error creating technical alert: {e}")
            self.stats["errors"] += 1
            return None

    def mark_technical_alert_inactive(self, alert_id: int) -> bool:
        """
        Mark a technical alert as inactive

        Args:
            alert_id: Alert ID

        Returns:
            True if successful
        """
        self.stats["total_calls"] += 1

        try:
            result = self.db_tools.mark_technical_alert_inactive(alert_id)
            return result
        except Exception as e:
            logger.error(f"Error marking technical alert inactive: {e}")
            self.stats["errors"] += 1
            return False

    def get_latest_technical_alerts_by_ticker(
        self,
        ticker: str,
        hours: int = 24
    ) -> List[Dict]:
        """
        Get latest technical alerts for a ticker

        Args:
            ticker: Stock symbol
            hours: Number of recent hours (default: 24)

        Returns:
            List of recent technical alerts
        """
        self.stats["total_calls"] += 1
        cache_key = self._cache_key(
            "get_latest_technical_alerts_by_ticker",
            ticker=ticker,
            hours=hours
        )

        # Cache 5 minutes
        cached = self._cache_get(cache_key, ttl=300)
        if cached:
            return cached

        try:
            result = self.db_tools.get_latest_technical_alerts_by_ticker(ticker, hours)
            if result:
                self._cache_set(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"Error getting latest technical alerts: {e}")
            self.stats["errors"] += 1
            return []

    def get_critical_technical_alerts(self, hours: int = 24) -> List[Dict]:
        """
        Get all critical technical alerts

        Args:
            hours: Number of recent hours (default: 24)

        Returns:
            List of critical alerts
        """
        self.stats["total_calls"] += 1
        cache_key = self._cache_key(
            "get_critical_technical_alerts",
            hours=hours
        )

        # Cache 5 minutes
        cached = self._cache_get(cache_key, ttl=300)
        if cached:
            return cached

        try:
            result = self.db_tools.get_critical_technical_alerts(hours)
            if result:
                self._cache_set(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"Error getting critical technical alerts: {e}")
            self.stats["errors"] += 1
            return []

    # ========== UTILITY METHODS ==========

    def get_stats(self) -> Dict:
        """Get client statistics"""
        total = self.stats["total_calls"]
        return {
            **self.stats,
            "cache_hit_rate": f"{self.stats['cache_hits'] / total * 100:.1f}%" if total > 0 else "0%",
            "error_rate": f"{self.stats['errors'] / total * 100:.1f}%" if total > 0 else "0%"
        }

    def clear_cache(self):
        """Clear all cache"""
        self.cache.clear()

    def close(self):
        """Close database connection"""
        if self.db_tools:
            self.db_tools.close()


# Singleton instance
_db_client = None

def get_database_client() -> HybridDatabaseClient:
    """Get singleton database client instance"""
    global _db_client
    if _db_client is None:
        _db_client = HybridDatabaseClient()
    return _db_client
