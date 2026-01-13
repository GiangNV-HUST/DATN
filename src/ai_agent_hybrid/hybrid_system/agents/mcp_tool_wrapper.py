"""
MCP Tool Wrapper - Bridges Async MCP Tools with Sync Google ADK Agents

This is the KEY component that allows:
- Google ADK Agents (sync) to use MCP Tools (async)
- Proper event loop management
- Thread pool execution for nested async contexts

From OLD system: Concept of tool wrapping for agents
From NEW system: Async MCP tools
Hybrid: Bridge between the two
"""

import asyncio
import concurrent.futures
from typing import Any, Dict, Callable
import inspect


class MCPToolWrapper:
    """
    Wrapper to convert async MCP tools into sync functions for Google ADK

    Google ADK expects synchronous tool functions:
        def my_tool(**kwargs) -> result

    But MCP tools are async:
        async def mcp_tool(**kwargs) -> result

    This wrapper bridges the gap.
    """

    def __init__(self, mcp_client, tool_name: str, description: str = ""):
        """
        Initialize wrapper

        Args:
            mcp_client: EnhancedMCPClient instance
            tool_name: Name of MCP tool
            description: Tool description for agent
        """
        self.mcp_client = mcp_client
        self.tool_name = tool_name
        self.description = description or f"MCP tool: {tool_name}"

        # Add __name__ attribute for OpenAI adapter compatibility
        self.__name__ = tool_name
        self.__doc__ = description or f"MCP tool: {tool_name}"

        # Stats
        self.call_count = 0
        self.error_count = 0

    def __call__(self, **kwargs) -> Any:
        """
        Make wrapper callable as a sync function

        This is called by Google ADK agent when it decides to use this tool.

        Handles two scenarios:
        1. Called from sync context → Run async directly
        2. Called from running async context → Use ThreadPoolExecutor
        """
        self.call_count += 1

        try:
            # Get or create event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # No event loop in current thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Check if loop is already running
            if loop.is_running():
                # We're in an async context (e.g., Discord bot, FastAPI)
                # Cannot use loop.run_until_complete (would block)
                # Use ThreadPoolExecutor to run in separate thread
                return self._run_in_thread(kwargs)
            else:
                # Not in async context (e.g., CLI, simple script)
                # Can run directly
                return loop.run_until_complete(
                    self.mcp_client.call_tool(self.tool_name, kwargs)
                )

        except Exception as e:
            self.error_count += 1
            return {
                "status": "error",
                "error": str(e),
                "tool": self.tool_name
            }

    def _run_in_thread(self, kwargs: Dict) -> Any:
        """
        Run async MCP call in a separate thread

        This is needed when called from an already-running event loop
        (e.g., Discord bot, FastAPI)
        """
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                asyncio.run,
                self.mcp_client.call_tool(self.tool_name, kwargs)
            )
            return future.result()

    def get_stats(self) -> Dict:
        """Get wrapper statistics"""
        return {
            "tool_name": self.tool_name,
            "call_count": self.call_count,
            "error_count": self.error_count,
            "error_rate": (
                f"{self.error_count / self.call_count * 100:.1f}%"
                if self.call_count > 0 else "0%"
            )
        }


def create_mcp_tools_for_agent(mcp_client, tool_names: list = None) -> list:
    """
    Create wrapped MCP tools for Google ADK agent

    Args:
        mcp_client: EnhancedMCPClient instance
        tool_names: List of tool names to wrap, or "all" for all tools

    Returns:
        List of MCPToolWrapper instances (callable sync functions)
    """

    # All available MCP tools
    ALL_TOOLS = {
        # Stock Data Tools
        "get_stock_data": "Fetch stock price data with technical indicators",
        "get_stock_price_prediction": "Get stock price predictions (3-day or 48-day)",
        "generate_chart_from_data": "Generate candlestick charts for stocks",
        "get_stock_details_from_tcbs": "Get detailed stock info from TCBS (70+ fields)",

        # Alert Tools
        "create_alert": "Create a new price/indicator alert",
        "get_user_alerts": "Get all alerts for a user",
        "delete_alert": "Delete a specific alert",

        # Subscription Tools
        "create_subscription": "Subscribe to a stock symbol",
        "get_user_subscriptions": "Get all subscriptions for a user",
        "delete_subscription": "Delete a subscription",

        # Gemini AI Tools
        "gemini_summarize": "Summarize data using Gemini AI",
        "gemini_search_and_summarize": "Search web and summarize with Gemini",
        "batch_summarize": "Batch summarize multiple symbols in parallel",

        # Financial Data Tools
        "get_financial_data": "Get financial reports (balance sheet, income, cash flow, ratios)",
        "screen_stocks": "Screen Vietnamese stocks with 80+ criteria",
        "get_screener_columns": "Get available screening columns and operators",

        # Investment Planning Tools
        "gather_investment_profile": "Gather user investment profile",
        "calculate_portfolio_allocation": "Calculate portfolio allocation",
        "generate_entry_strategy": "Generate entry strategy for stocks",
        "generate_risk_management_plan": "Generate risk management plan",
        "generate_monitoring_plan": "Generate monitoring plan",

        # Stock Discovery Tools
        "discover_stocks_by_profile": "Discover stocks matching investment profile",
        "search_potential_stocks": "Search for potential stocks",
        "filter_stocks_by_criteria": "Filter stocks by quantitative criteria",
        "rank_stocks_by_score": "Rank stocks by composite score",
    }

    # Determine which tools to wrap
    if tool_names == "all" or tool_names is None:
        tools_to_wrap = ALL_TOOLS.keys()
    else:
        tools_to_wrap = tool_names

    # Create wrappers
    wrapped_tools = []
    for tool_name in tools_to_wrap:
        if tool_name in ALL_TOOLS:
            wrapper = MCPToolWrapper(
                mcp_client=mcp_client,
                tool_name=tool_name,
                description=ALL_TOOLS[tool_name]
            )
            wrapped_tools.append(wrapper)

    return wrapped_tools


def get_tool_stats(wrapped_tools: list) -> Dict:
    """
    Get statistics for all wrapped tools

    Args:
        wrapped_tools: List of MCPToolWrapper instances

    Returns:
        Dictionary with aggregated stats
    """
    total_calls = sum(tool.call_count for tool in wrapped_tools)
    total_errors = sum(tool.error_count for tool in wrapped_tools)

    return {
        "total_tools": len(wrapped_tools),
        "total_calls": total_calls,
        "total_errors": total_errors,
        "overall_error_rate": (
            f"{total_errors / total_calls * 100:.1f}%"
            if total_calls > 0 else "0%"
        ),
        "tools": [tool.get_stats() for tool in wrapped_tools]
    }
