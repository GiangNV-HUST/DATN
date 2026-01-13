"""
Direct MCP Client - Calls tools directly without subprocess

This client imports and calls MCP tool functions directly in-process,
avoiding subprocess creation issues when running inside Claude Desktop MCP server.

Used as a drop-in replacement for EnhancedMCPClient when subprocess spawning fails.
"""

import sys
import os
from pathlib import Path
from typing import Any, Dict, Optional
import asyncio
import hashlib
import json
import time
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class DirectMCPClient:
    """
    Direct MCP Client - calls tool functions directly without subprocess

    This is a drop-in replacement for EnhancedMCPClient that works when
    subprocess creation is not possible (e.g., inside Claude Desktop MCP server).

    Features:
    - Same interface as EnhancedMCPClient
    - In-memory caching
    - Circuit breaker pattern
    - Direct function calls (no subprocess)
    """

    def __init__(self, server_script_path: str = None, cache_ttl: int = 300):
        """Initialize Direct MCP Client"""
        self.server_script_path = server_script_path
        self.cache_ttl = cache_ttl

        # Tools registry (populated on connect)
        self._tools = {}
        self.available_tools = []

        # In-memory cache
        self.cache = {}

        # Request deduplication
        self.in_flight_requests = {}

        # Circuit breaker - more lenient settings for better UX
        self.failure_count = 0
        self.circuit_open = False
        self.circuit_open_until = None
        self.max_failures = 10  # More failures allowed before opening
        self.circuit_timeout = 15  # Shorter timeout to recover faster

        # Metrics
        self.metrics = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "failures": 0,
            "total_response_time": 0,
        }

    @classmethod
    async def create(cls, server_script_path: str = None, cache_ttl: int = 300):
        """Factory method to create and connect client"""
        client = cls(server_script_path=server_script_path, cache_ttl=cache_ttl)
        await client.connect()
        return client

    async def connect(self):
        """Import and register all tool functions"""
        try:
            # Import tool functions directly
            from src.mcp_server.tools.stock_tools import (
                get_stock_data_mcp,
                get_stock_price_prediction_mcp,
                generate_chart_from_data_mcp,
                get_stock_details_from_tcbs_mcp
            )
            from src.mcp_server.tools.finance_tools import (
                get_financial_data_mcp
            )
            from src.mcp_server.tools.screener_tools import (
                screen_stocks_mcp,
                get_screener_columns_mcp
            )
            from src.mcp_server.tools.alert_tools import (
                create_alert_mcp,
                get_user_alerts_mcp,
                delete_alert_mcp
            )
            from src.mcp_server.tools.subscription_tools import (
                create_subscription_mcp,
                get_user_subscriptions_mcp,
                delete_subscription_mcp
            )
            from src.mcp_server.tools.investment_planning_tools import (
                gather_investment_profile,
                calculate_portfolio_allocation,
                generate_entry_strategy,
                generate_risk_management_plan,
                generate_monitoring_plan,
                generate_dca_plan
            )
            from src.mcp_server.tools.stock_discovery_tools import (
                discover_stocks_by_profile,
                search_potential_stocks,
                filter_stocks_by_criteria,
                rank_stocks_by_score
            )
            from src.mcp_server.tools.tcbs_tools import (
                get_company_overview_mcp,
                get_company_profile_mcp,
                get_financial_ratios_mcp,
                get_income_statement_mcp,
                get_balance_sheet_mcp,
                get_cash_flow_mcp,
                get_price_history_mcp,
                get_intraday_data_mcp,
                get_stock_full_info_mcp
            )

            # Register tools
            self._tools = {
                "get_stock_data": get_stock_data_mcp,
                "get_stock_price_prediction": get_stock_price_prediction_mcp,
                "generate_chart_from_data": generate_chart_from_data_mcp,
                "get_stock_details_from_tcbs": get_stock_details_from_tcbs_mcp,
                "get_financial_data": get_financial_data_mcp,
                "screen_stocks": screen_stocks_mcp,
                "get_screener_columns": get_screener_columns_mcp,
                "create_alert": create_alert_mcp,
                "get_user_alerts": get_user_alerts_mcp,
                "delete_alert": delete_alert_mcp,
                "create_subscription": create_subscription_mcp,
                "get_user_subscriptions": get_user_subscriptions_mcp,
                "delete_subscription": delete_subscription_mcp,
                "gather_investment_profile": gather_investment_profile,
                "calculate_portfolio_allocation": calculate_portfolio_allocation,
                "generate_entry_strategy": generate_entry_strategy,
                "generate_risk_management_plan": generate_risk_management_plan,
                "generate_monitoring_plan": generate_monitoring_plan,
                "generate_dca_plan": generate_dca_plan,
                "discover_stocks_by_profile": discover_stocks_by_profile,
                "search_potential_stocks": search_potential_stocks,
                "filter_stocks_by_criteria": filter_stocks_by_criteria,
                "rank_stocks_by_score": rank_stocks_by_score,
                # TCBS/VCI tools
                "get_company_overview": get_company_overview_mcp,
                "get_company_profile": get_company_profile_mcp,
                "get_financial_ratios": get_financial_ratios_mcp,
                "get_income_statement": get_income_statement_mcp,
                "get_balance_sheet": get_balance_sheet_mcp,
                "get_cash_flow": get_cash_flow_mcp,
                "get_price_history": get_price_history_mcp,
                "get_intraday_data": get_intraday_data_mcp,
                "get_stock_full_info": get_stock_full_info_mcp,
            }

            # Create tool info for available_tools
            self.available_tools = [
                type('Tool', (), {'name': name})()
                for name in self._tools.keys()
            ]

        except Exception as e:
            import traceback
            traceback.print_exc()
            raise

    async def disconnect(self):
        """No-op for direct client"""
        pass

    def _get_cache_key(self, tool_name: str, arguments: Dict) -> str:
        """Generate cache key"""
        sorted_args = json.dumps(arguments, sort_keys=True, default=str)
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
            "get_stock_data": 60,
            "get_stock_details_from_tcbs": 300,
            "get_financial_data": 3600,
            "screen_stocks": 600,
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
        """Call tool directly"""
        self.metrics["total_requests"] += 1
        start_time = time.time()

        # Check circuit breaker
        if self.circuit_open:
            if datetime.now() < self.circuit_open_until:
                raise Exception(f"Circuit breaker is OPEN - too many failures. Will reset automatically.")
            else:
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

        # Check in-flight requests
        if cache_key in self.in_flight_requests:
            return await self.in_flight_requests[cache_key]

        # Create future
        future = asyncio.Future()
        self.in_flight_requests[cache_key] = future

        try:
            # Get tool function
            if tool_name not in self._tools:
                raise ValueError(f"Unknown tool: {tool_name}")

            tool_func = self._tools[tool_name]

            # Call tool function directly
            if asyncio.iscoroutinefunction(tool_func):
                result = await tool_func(**arguments)
            else:
                result = tool_func(**arguments)

            # Cache result
            if self._is_cacheable(tool_name):
                self.cache[cache_key] = (result, time.time())

            # Update metrics
            response_time = time.time() - start_time
            self.metrics["total_response_time"] += response_time

            # Reset failure count
            self.failure_count = 0

            future.set_result(result)
            return result

        except Exception as e:
            self.metrics["failures"] += 1
            self.failure_count += 1

            if self.failure_count >= self.max_failures:
                self.circuit_open = True
                self.circuit_open_until = datetime.now() + timedelta(seconds=self.circuit_timeout)

            future.set_exception(e)
            raise

        finally:
            if cache_key in self.in_flight_requests:
                del self.in_flight_requests[cache_key]

    def get_metrics(self) -> Dict:
        """Get performance metrics"""
        total = self.metrics["total_requests"]
        cache_rate = self.metrics["cache_hits"] / total * 100 if total > 0 else 0
        avg_response_time = self.metrics["total_response_time"] / total if total > 0 else 0

        return {
            **self.metrics,
            "cache_hit_rate": f"{cache_rate:.1f}%",
            "avg_response_time": f"{avg_response_time:.2f}s",
            "circuit_breaker_status": "OPEN" if self.circuit_open else "CLOSED"
        }

    def clear_cache(self, pattern: Optional[str] = None):
        """Clear cache"""
        if pattern is None:
            self.cache.clear()
        else:
            keys_to_delete = [k for k in self.cache.keys() if pattern in k]
            for key in keys_to_delete:
                del self.cache[key]

    def reset_circuit_breaker(self):
        """Manually reset circuit breaker"""
        self.circuit_open = False
        self.circuit_open_until = None
        self.failure_count = 0

    # Convenience methods - same interface as EnhancedMCPClient

    async def get_stock_data(self, symbols: list, **kwargs):
        return await self.call_tool("get_stock_data", {"symbols": symbols, **kwargs})

    async def get_stock_price_prediction(self, symbols: list, table_type: str):
        return await self.call_tool("get_stock_price_prediction", {
            "symbols": symbols, "table_type": table_type
        })

    async def generate_chart_from_data(self, symbols: list, **kwargs):
        return await self.call_tool("generate_chart_from_data", {"symbols": symbols, **kwargs})

    async def get_stock_details_from_tcbs(self, symbols: list):
        return await self.call_tool("get_stock_details_from_tcbs", {"symbols": symbols})

    async def create_alert(self, user_id: str, symbol: str, alert_type: str,
                          target_value: float, condition: str):
        return await self.call_tool("create_alert", {
            "user_id": user_id, "symbol": symbol, "alert_type": alert_type,
            "target_value": target_value, "condition": condition
        }, force_refresh=True)

    async def get_user_alerts(self, user_id: str):
        return await self.call_tool("get_user_alerts", {"user_id": user_id})

    async def delete_alert(self, user_id: str, alert_id: int):
        return await self.call_tool("delete_alert", {
            "user_id": user_id, "alert_id": alert_id
        }, force_refresh=True)

    async def create_subscription(self, user_id: str, symbol: str):
        return await self.call_tool("create_subscription", {
            "user_id": user_id, "symbol": symbol
        }, force_refresh=True)

    async def get_user_subscriptions(self, user_id: str):
        return await self.call_tool("get_user_subscriptions", {"user_id": user_id})

    async def delete_subscription(self, user_id: str, subscription_id: int):
        return await self.call_tool("delete_subscription", {
            "user_id": user_id, "subscription_id": subscription_id
        }, force_refresh=True)

    async def get_financial_data(self, tickers: list, **kwargs):
        return await self.call_tool("get_financial_data", {"tickers": tickers, **kwargs})

    async def screen_stocks(self, conditions: dict, **kwargs):
        return await self.call_tool("screen_stocks", {"conditions": conditions, **kwargs})

    async def get_screener_columns(self):
        return await self.call_tool("get_screener_columns", {})

    async def gather_investment_profile(self, **kwargs):
        return await self.call_tool("gather_investment_profile", kwargs)

    async def calculate_portfolio_allocation(self, stocks: list, capital: float, **kwargs):
        return await self.call_tool("calculate_portfolio_allocation", {
            "stocks": stocks, "capital": capital, **kwargs
        })

    async def generate_entry_strategy(self, stocks: list, **kwargs):
        return await self.call_tool("generate_entry_strategy", {"stocks": stocks, **kwargs})

    async def generate_risk_management_plan(self, stocks: list, **kwargs):
        return await self.call_tool("generate_risk_management_plan", {"stocks": stocks, **kwargs})

    async def generate_monitoring_plan(self, stocks: list, **kwargs):
        return await self.call_tool("generate_monitoring_plan", {"stocks": stocks, **kwargs})

    async def discover_stocks_by_profile(self, investment_profile: dict, max_stocks: int = 5):
        return await self.call_tool("discover_stocks_by_profile", {
            "investment_profile": investment_profile, "max_stocks": max_stocks
        })

    async def search_potential_stocks(self, query: str, **kwargs):
        return await self.call_tool("search_potential_stocks", {"query": query, **kwargs})

    async def filter_stocks_by_criteria(self, symbols: list, criteria: dict):
        return await self.call_tool("filter_stocks_by_criteria", {
            "symbols": symbols, "criteria": criteria
        })

    async def rank_stocks_by_score(self, stocks: list, ranking_method: str = "composite"):
        return await self.call_tool("rank_stocks_by_score", {
            "stocks": stocks, "ranking_method": ranking_method
        })
