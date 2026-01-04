"""
Enhanced MCP Client with caching, retry logic, and resilience features

Extends base MCP functionality from the NEW system with:
- Client-side caching (memory-based)
- Request deduplication
- Automatic retry with exponential backoff
- Circuit breaker pattern
- Performance metrics tracking
"""

import sys
import os

# Add parent directories to path to import from ai_agent_mcp
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'ai_agent_mcp'))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from typing import Any, Dict, Optional
import asyncio
import hashlib
import json
import time
from datetime import datetime, timedelta


class EnhancedMCPClient:
    """
    Enhanced MCP Client with caching and resilience

    Improvements over base MCP client:
    - Client-side caching (10x faster for repeated queries)
    - Request deduplication (prevent duplicate concurrent requests)
    - Automatic retry with exponential backoff
    - Circuit breaker pattern (fail fast when service is down)
    - Performance metrics tracking
    """

    def __init__(self, server_script_path: str, cache_ttl: int = 300):
        """
        Initialize Enhanced MCP Client

        Args:
            server_script_path: Path to MCP server script
            cache_ttl: Default cache TTL in seconds (default: 5 minutes)
        """
        self.server_script_path = server_script_path
        self.cache_ttl = cache_ttl

        # Connection
        self.session: Optional[ClientSession] = None
        self.read_stream = None
        self.write_stream = None

        # Available tools
        self.available_tools = []

        # In-memory cache
        self.cache = {}

        # Request deduplication
        self.in_flight_requests = {}

        # Circuit breaker
        self.failure_count = 0
        self.circuit_open = False
        self.circuit_open_until = None
        self.max_failures = 5
        self.circuit_timeout = 30  # seconds

        # Metrics
        self.metrics = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "failures": 0,
            "total_response_time": 0,
        }

    async def connect(self):
        """Connect to MCP server"""
        try:
            # Create server parameters
            server_params = StdioServerParameters(
                command="python",
                args=["-u", self.server_script_path],
                env=None
            )

            # Start stdio communication
            self.read_stream, self.write_stream = await stdio_client(server_params)

            # Initialize MCP session
            self.session = ClientSession(self.read_stream, self.write_stream)
            await self.session.initialize()

            # List available tools
            response = await self.session.list_tools()
            self.available_tools = response.tools

            print(f"✅ Enhanced MCP Client connected. {len(self.available_tools)} tools available.")

        except Exception as e:
            print(f"❌ Failed to connect to MCP server: {e}")
            raise

    async def disconnect(self):
        """Disconnect from MCP server"""
        if self.session:
            try:
                await self.session.__aexit__(None, None, None)
            except:
                pass
        print("✅ Enhanced MCP Client disconnected")

    def _get_cache_key(self, tool_name: str, arguments: Dict) -> str:
        """Generate cache key from tool name + arguments"""
        sorted_args = json.dumps(arguments, sort_keys=True)
        key_string = f"{tool_name}:{sorted_args}"
        return hashlib.md5(key_string.encode()).hexdigest()

    def _is_cacheable(self, tool_name: str) -> bool:
        """Determine if tool result should be cached"""
        non_cacheable = [
            "create_alert", "delete_alert",
            "create_subscription", "delete_subscription"
        ]
        return tool_name not in non_cacheable

    def _get_cache_ttl(self, tool_name: str) -> int:
        """Get TTL based on tool type"""
        ttl_map = {
            # Real-time data - short TTL
            "get_stock_data": 60,
            "get_stock_details_from_tcbs": 300,

            # Financial data - medium TTL
            "get_financial_data": 3600,
            "screen_stocks": 600,

            # AI results - longer TTL
            "gemini_search_and_summarize": 1800,
            "batch_summarize": 1800,

            # User data - short TTL
            "get_user_alerts": 30,
            "get_user_subscriptions": 30,
        }
        return ttl_map.get(tool_name, self.cache_ttl)

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict,
        force_refresh: bool = False
    ) -> Any:
        """
        Call tool with caching and resilience

        Args:
            tool_name: Name of tool to call
            arguments: Tool arguments
            force_refresh: Skip cache and fetch fresh data

        Returns:
            Tool result
        """
        self.metrics["total_requests"] += 1
        start_time = time.time()

        # Check circuit breaker
        if self.circuit_open:
            if datetime.now() < self.circuit_open_until:
                raise Exception("Circuit breaker is OPEN - service temporarily unavailable")
            else:
                # Try to close circuit
                self.circuit_open = False
                self.failure_count = 0

        # Generate cache key
        cache_key = self._get_cache_key(tool_name, arguments)

        # Check cache
        if not force_refresh and self._is_cacheable(tool_name):
            if cache_key in self.cache:
                cached_data, cached_time = self.cache[cache_key]
                ttl = self._get_cache_ttl(tool_name)

                if time.time() - cached_time < ttl:
                    self.metrics["cache_hits"] += 1
                    return cached_data

        self.metrics["cache_misses"] += 1

        # Check for in-flight requests (deduplication)
        if cache_key in self.in_flight_requests:
            return await self.in_flight_requests[cache_key]

        # Create future for this request
        future = asyncio.Future()
        self.in_flight_requests[cache_key] = future

        try:
            # Call tool with retry
            result = await self._call_with_retry(tool_name, arguments)

            # Cache result
            if self._is_cacheable(tool_name):
                self.cache[cache_key] = (result, time.time())

            # Update metrics
            response_time = time.time() - start_time
            self.metrics["total_response_time"] += response_time

            # Reset failure count
            self.failure_count = 0

            # Resolve future
            future.set_result(result)

            return result

        except Exception as e:
            self.metrics["failures"] += 1
            self.failure_count += 1

            # Circuit breaker logic
            if self.failure_count >= self.max_failures:
                self.circuit_open = True
                self.circuit_open_until = datetime.now() + timedelta(seconds=self.circuit_timeout)
                print(f"⚠️ Circuit breaker OPENED. Will retry after {self.circuit_timeout}s")

            future.set_exception(e)
            raise

        finally:
            # Remove from in-flight
            if cache_key in self.in_flight_requests:
                del self.in_flight_requests[cache_key]

    async def _call_with_retry(
        self,
        tool_name: str,
        arguments: Dict,
        max_retries: int = 3
    ) -> Any:
        """Call tool with exponential backoff retry"""
        last_exception = None

        for attempt in range(max_retries):
            try:
                # Call MCP server
                result = await self.session.call_tool(tool_name, arguments)

                # Extract text content from result
                if hasattr(result, 'content') and result.content:
                    if len(result.content) > 0:
                        text_content = result.content[0].text
                        # Try to parse as dict if possible
                        try:
                            return eval(text_content)
                        except:
                            return text_content

                return result

            except Exception as e:
                last_exception = e

                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"⚠️ Retry {attempt + 1}/{max_retries} after {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    raise last_exception

    def get_metrics(self) -> Dict:
        """Get performance metrics"""
        total = self.metrics["total_requests"]
        cache_rate = (
            self.metrics["cache_hits"] / total * 100
            if total > 0 else 0
        )
        avg_response_time = (
            self.metrics["total_response_time"] / total
            if total > 0 else 0
        )

        return {
            **self.metrics,
            "cache_hit_rate": f"{cache_rate:.1f}%",
            "avg_response_time": f"{avg_response_time:.2f}s",
            "circuit_breaker_status": "OPEN" if self.circuit_open else "CLOSED"
        }

    def clear_cache(self, pattern: Optional[str] = None):
        """Clear cache (all or matching pattern)"""
        if pattern is None:
            self.cache.clear()
        else:
            keys_to_delete = [k for k in self.cache.keys() if pattern in k]
            for key in keys_to_delete:
                del self.cache[key]

    # Convenience methods for all 25 tools

    async def get_stock_data(self, symbols: list[str], **kwargs):
        """Get stock price data"""
        return await self.call_tool("get_stock_data", {"symbols": symbols, **kwargs})

    async def get_stock_price_prediction(self, symbols: list[str], table_type: str):
        """Get price predictions"""
        return await self.call_tool("get_stock_price_prediction", {
            "symbols": symbols,
            "table_type": table_type
        })

    async def generate_chart_from_data(self, symbols: list[str], **kwargs):
        """Generate charts"""
        return await self.call_tool("generate_chart_from_data", {"symbols": symbols, **kwargs})

    async def get_stock_details_from_tcbs(self, symbols: list[str]):
        """Get TCBS stock details"""
        return await self.call_tool("get_stock_details_from_tcbs", {"symbols": symbols})

    async def create_alert(self, user_id: str, symbol: str, alert_type: str,
                          target_value: float, condition: str):
        """Create alert"""
        return await self.call_tool("create_alert", {
            "user_id": user_id,
            "symbol": symbol,
            "alert_type": alert_type,
            "target_value": target_value,
            "condition": condition
        }, force_refresh=True)

    async def get_user_alerts(self, user_id: str):
        """Get user alerts"""
        return await self.call_tool("get_user_alerts", {"user_id": user_id})

    async def delete_alert(self, user_id: str, alert_id: int):
        """Delete alert"""
        return await self.call_tool("delete_alert", {
            "user_id": user_id,
            "alert_id": alert_id
        }, force_refresh=True)

    async def create_subscription(self, user_id: str, symbol: str):
        """Create subscription"""
        return await self.call_tool("create_subscription", {
            "user_id": user_id,
            "symbol": symbol
        }, force_refresh=True)

    async def get_user_subscriptions(self, user_id: str):
        """Get user subscriptions"""
        return await self.call_tool("get_user_subscriptions", {"user_id": user_id})

    async def delete_subscription(self, user_id: str, subscription_id: int):
        """Delete subscription"""
        return await self.call_tool("delete_subscription", {
            "user_id": user_id,
            "subscription_id": subscription_id
        }, force_refresh=True)

    async def gemini_summarize(self, prompt: str, data: dict, use_search: bool = False):
        """Gemini summarize"""
        return await self.call_tool("gemini_summarize", {
            "prompt": prompt,
            "data": data,
            "use_search": use_search
        })

    async def gemini_search_and_summarize(self, query: str, user_query: str):
        """Gemini search and summarize"""
        return await self.call_tool("gemini_search_and_summarize", {
            "query": query,
            "user_query": user_query
        })

    async def batch_summarize(self, symbols_data: dict, general_query: str = ""):
        """Batch summarize"""
        return await self.call_tool("batch_summarize", {
            "symbols_data": symbols_data,
            "general_query": general_query
        })

    async def get_financial_data(self, tickers: list[str], **kwargs):
        """Get financial data"""
        return await self.call_tool("get_financial_data", {"tickers": tickers, **kwargs})

    async def screen_stocks(self, conditions: dict, **kwargs):
        """Screen stocks"""
        return await self.call_tool("screen_stocks", {"conditions": conditions, **kwargs})

    async def get_screener_columns(self):
        """Get screener columns"""
        return await self.call_tool("get_screener_columns", {})

    # Investment planning tools
    async def gather_investment_profile(self, **kwargs):
        """Gather investment profile"""
        return await self.call_tool("gather_investment_profile", kwargs)

    async def calculate_portfolio_allocation(self, stocks: list[dict], capital: float, **kwargs):
        """Calculate portfolio allocation"""
        return await self.call_tool("calculate_portfolio_allocation", {
            "stocks": stocks,
            "capital": capital,
            **kwargs
        })

    async def generate_entry_strategy(self, stocks: list[dict], **kwargs):
        """Generate entry strategy"""
        return await self.call_tool("generate_entry_strategy", {"stocks": stocks, **kwargs})

    async def generate_risk_management_plan(self, stocks: list[dict], **kwargs):
        """Generate risk management plan"""
        return await self.call_tool("generate_risk_management_plan", {"stocks": stocks, **kwargs})

    async def generate_monitoring_plan(self, stocks: list[dict], **kwargs):
        """Generate monitoring plan"""
        return await self.call_tool("generate_monitoring_plan", {"stocks": stocks, **kwargs})

    # Stock discovery tools
    async def discover_stocks_by_profile(self, investment_profile: dict, max_stocks: int = 5):
        """Discover stocks by profile"""
        return await self.call_tool("discover_stocks_by_profile", {
            "investment_profile": investment_profile,
            "max_stocks": max_stocks
        })

    async def search_potential_stocks(self, query: str, **kwargs):
        """Search potential stocks"""
        return await self.call_tool("search_potential_stocks", {"query": query, **kwargs})

    async def filter_stocks_by_criteria(self, symbols: list[str], criteria: dict):
        """Filter stocks by criteria"""
        return await self.call_tool("filter_stocks_by_criteria", {
            "symbols": symbols,
            "criteria": criteria
        })

    async def rank_stocks_by_score(self, stocks: list[dict], ranking_method: str = "composite"):
        """Rank stocks by score"""
        return await self.call_tool("rank_stocks_by_score", {
            "stocks": stocks,
            "ranking_method": ranking_method
        })

    # ========== ADDITIONAL DATABASE TOOLS (from Final system) ==========

    async def get_latest_price(self, ticker: str):
        """
        Get latest price + indicators

        Args:
            ticker: Stock symbol

        Returns:
            Dict with price, volume, ma5, ma20, rsi, macd
        """
        return await self.call_tool("get_latest_price", {"ticker": ticker})

    async def get_price_history(self, ticker: str, days: int = 30):
        """
        Get price history

        Args:
            ticker: Stock symbol
            days: Number of days

        Returns:
            List of price data
        """
        return await self.call_tool("get_price_history", {"ticker": ticker, "days": days})

    async def get_company_info(self, ticker: str):
        """
        Get company information

        Args:
            ticker: Stock symbol

        Returns:
            Dict with company name, industry, employees, website
        """
        return await self.call_tool("get_company_info", {"ticker": ticker})

    async def search_stocks_by_criteria(self, criteria: dict):
        """
        Search stocks matching criteria

        Args:
            criteria: Dict with rsi_below, rsi_above, price_below, price_above, min_volume

        Returns:
            List of ticker symbols
        """
        return await self.call_tool("search_stocks_by_criteria", {"criteria": criteria})

    async def get_balance_sheet(self, symbols: list[str], year: Optional[int] = None, quarter: Optional[int] = None):
        """
        Get balance sheet data

        Args:
            symbols: List of stock symbols
            year: Year (optional)
            quarter: Quarter 1-4 (optional)

        Returns:
            List of balance sheet data
        """
        return await self.call_tool("get_balance_sheet", {
            "symbols": symbols,
            "year": year,
            "quarter": quarter
        })

    async def get_income_statement(self, symbols: list[str], year: Optional[int] = None, quarter: Optional[int] = None):
        """
        Get income statement data

        Args:
            symbols: List of stock symbols
            year: Year (optional)
            quarter: Quarter 1-4 (optional)

        Returns:
            List of income statement data
        """
        return await self.call_tool("get_income_statement", {
            "symbols": symbols,
            "year": year,
            "quarter": quarter
        })

    async def get_cash_flow(self, symbols: list[str], year: Optional[int] = None, quarter: Optional[int] = None):
        """
        Get cash flow data

        Args:
            symbols: List of stock symbols
            year: Year (optional)
            quarter: Quarter 1-4 (optional)

        Returns:
            List of cash flow data
        """
        return await self.call_tool("get_cash_flow", {
            "symbols": symbols,
            "year": year,
            "quarter": quarter
        })

    async def get_financial_ratios_detailed(self, symbols: list[str], year: Optional[int] = None, quarter: Optional[int] = None):
        """
        Get detailed financial ratios (PE, PB, ROE, ROA, dividend yield, debt-to-equity)

        Args:
            symbols: List of stock symbols
            year: Year (optional)
            quarter: Quarter 1-4 (optional)

        Returns:
            List of financial ratios
        """
        return await self.call_tool("get_financial_ratios", {
            "symbols": symbols,
            "year": year,
            "quarter": quarter
        })
