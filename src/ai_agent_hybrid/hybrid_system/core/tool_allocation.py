"""
Tool & Resource Allocation System

Implements least privilege principle and resource quotas for agents.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum
import threading


class ToolCategory(str, Enum):
    """Categories of tools"""
    STOCK_DATA = "stock_data"
    FINANCIAL = "financial"
    ALERTS = "alerts"
    SUBSCRIPTIONS = "subscriptions"
    AI_ANALYSIS = "ai_analysis"
    SCREENING = "screening"
    INVESTMENT = "investment"
    DISCOVERY = "discovery"


@dataclass
class ToolPolicy:
    """
    Policy for a single tool

    Defines quotas and costs for tool usage.
    """
    tool_name: str
    category: ToolCategory
    max_calls_per_query: int = -1  # -1 = unlimited
    estimated_cost: float = 0.0  # USD per call
    estimated_time: float = 0.0  # seconds per call


# Tool catalog with policies
TOOL_CATALOG: Dict[str, ToolPolicy] = {
    # Stock Data Tools
    "get_stock_data": ToolPolicy(
        tool_name="get_stock_data",
        category=ToolCategory.STOCK_DATA,
        max_calls_per_query=5,
        estimated_cost=0.01,
        estimated_time=1.0
    ),
    "get_stock_price_prediction": ToolPolicy(
        tool_name="get_stock_price_prediction",
        category=ToolCategory.STOCK_DATA,
        max_calls_per_query=3,
        estimated_cost=0.02,
        estimated_time=1.5
    ),
    "generate_chart_from_data": ToolPolicy(
        tool_name="generate_chart_from_data",
        category=ToolCategory.STOCK_DATA,
        max_calls_per_query=3,
        estimated_cost=0.05,
        estimated_time=2.0
    ),
    "get_stock_details_from_tcbs": ToolPolicy(
        tool_name="get_stock_details_from_tcbs",
        category=ToolCategory.STOCK_DATA,
        max_calls_per_query=10,
        estimated_cost=0.01,
        estimated_time=0.5
    ),

    # Financial Tools
    "get_financial_data": ToolPolicy(
        tool_name="get_financial_data",
        category=ToolCategory.FINANCIAL,
        max_calls_per_query=3,
        estimated_cost=0.02,
        estimated_time=1.5
    ),
    "screen_stocks": ToolPolicy(
        tool_name="screen_stocks",
        category=ToolCategory.SCREENING,
        max_calls_per_query=3,
        estimated_cost=0.05,
        estimated_time=2.0
    ),
    "get_screener_columns": ToolPolicy(
        tool_name="get_screener_columns",
        category=ToolCategory.SCREENING,
        max_calls_per_query=1,
        estimated_cost=0.0,
        estimated_time=0.1
    ),
    "filter_stocks_by_criteria": ToolPolicy(
        tool_name="filter_stocks_by_criteria",
        category=ToolCategory.SCREENING,
        max_calls_per_query=5,
        estimated_cost=0.03,
        estimated_time=1.0
    ),
    "rank_stocks_by_score": ToolPolicy(
        tool_name="rank_stocks_by_score",
        category=ToolCategory.SCREENING,
        max_calls_per_query=3,
        estimated_cost=0.02,
        estimated_time=0.8
    ),

    # AI Tools (expensive!)
    "gemini_summarize": ToolPolicy(
        tool_name="gemini_summarize",
        category=ToolCategory.AI_ANALYSIS,
        max_calls_per_query=3,
        estimated_cost=0.10,
        estimated_time=2.0
    ),
    "gemini_search_and_summarize": ToolPolicy(
        tool_name="gemini_search_and_summarize",
        category=ToolCategory.AI_ANALYSIS,
        max_calls_per_query=2,  # Limit expensive calls
        estimated_cost=0.15,
        estimated_time=3.0
    ),
    "batch_summarize": ToolPolicy(
        tool_name="batch_summarize",
        category=ToolCategory.AI_ANALYSIS,
        max_calls_per_query=1,  # Very expensive
        estimated_cost=0.20,
        estimated_time=4.0
    ),

    # Alert Tools
    "create_alert": ToolPolicy(
        tool_name="create_alert",
        category=ToolCategory.ALERTS,
        max_calls_per_query=5,
        estimated_cost=0.01,
        estimated_time=0.3
    ),
    "get_user_alerts": ToolPolicy(
        tool_name="get_user_alerts",
        category=ToolCategory.ALERTS,
        max_calls_per_query=3,
        estimated_cost=0.01,
        estimated_time=0.2
    ),
    "delete_alert": ToolPolicy(
        tool_name="delete_alert",
        category=ToolCategory.ALERTS,
        max_calls_per_query=5,
        estimated_cost=0.01,
        estimated_time=0.3
    ),

    # Subscription Tools
    "create_subscription": ToolPolicy(
        tool_name="create_subscription",
        category=ToolCategory.SUBSCRIPTIONS,
        max_calls_per_query=5,
        estimated_cost=0.01,
        estimated_time=0.3
    ),
    "get_user_subscriptions": ToolPolicy(
        tool_name="get_user_subscriptions",
        category=ToolCategory.SUBSCRIPTIONS,
        max_calls_per_query=3,
        estimated_cost=0.01,
        estimated_time=0.2
    ),
    "delete_subscription": ToolPolicy(
        tool_name="delete_subscription",
        category=ToolCategory.SUBSCRIPTIONS,
        max_calls_per_query=5,
        estimated_cost=0.01,
        estimated_time=0.3
    ),

    # Investment Planning Tools
    "gather_investment_profile": ToolPolicy(
        tool_name="gather_investment_profile",
        category=ToolCategory.INVESTMENT,
        max_calls_per_query=1,
        estimated_cost=0.05,
        estimated_time=1.0
    ),
    "calculate_portfolio_allocation": ToolPolicy(
        tool_name="calculate_portfolio_allocation",
        category=ToolCategory.INVESTMENT,
        max_calls_per_query=1,
        estimated_cost=0.05,
        estimated_time=1.5
    ),
    "generate_entry_strategy": ToolPolicy(
        tool_name="generate_entry_strategy",
        category=ToolCategory.INVESTMENT,
        max_calls_per_query=1,
        estimated_cost=0.05,
        estimated_time=1.0
    ),
    "generate_risk_management_plan": ToolPolicy(
        tool_name="generate_risk_management_plan",
        category=ToolCategory.INVESTMENT,
        max_calls_per_query=1,
        estimated_cost=0.05,
        estimated_time=1.0
    ),
    "generate_monitoring_plan": ToolPolicy(
        tool_name="generate_monitoring_plan",
        category=ToolCategory.INVESTMENT,
        max_calls_per_query=1,
        estimated_cost=0.05,
        estimated_time=1.0
    ),

    # Stock Discovery Tools
    "discover_stocks_by_profile": ToolPolicy(
        tool_name="discover_stocks_by_profile",
        category=ToolCategory.DISCOVERY,
        max_calls_per_query=2,
        estimated_cost=0.08,
        estimated_time=2.5
    ),
    "search_potential_stocks": ToolPolicy(
        tool_name="search_potential_stocks",
        category=ToolCategory.DISCOVERY,
        max_calls_per_query=3,
        estimated_cost=0.06,
        estimated_time=2.0
    ),

    # ========== ADDITIONAL DATABASE TOOLS (from Final system) ==========

    # Direct Database Query Tools
    "get_latest_price": ToolPolicy(
        tool_name="get_latest_price",
        category=ToolCategory.STOCK_DATA,
        max_calls_per_query=10,
        estimated_cost=0.01,
        estimated_time=0.3
    ),
    "get_price_history": ToolPolicy(
        tool_name="get_price_history",
        category=ToolCategory.STOCK_DATA,
        max_calls_per_query=5,
        estimated_cost=0.01,
        estimated_time=0.5
    ),
    "get_company_info": ToolPolicy(
        tool_name="get_company_info",
        category=ToolCategory.STOCK_DATA,
        max_calls_per_query=10,
        estimated_cost=0.01,
        estimated_time=0.2
    ),
    "search_stocks_by_criteria": ToolPolicy(
        tool_name="search_stocks_by_criteria",
        category=ToolCategory.SCREENING,
        max_calls_per_query=3,
        estimated_cost=0.03,
        estimated_time=1.0
    ),

    # Detailed Financial Statement Tools
    "get_balance_sheet": ToolPolicy(
        tool_name="get_balance_sheet",
        category=ToolCategory.FINANCIAL,
        max_calls_per_query=3,
        estimated_cost=0.02,
        estimated_time=1.0
    ),
    "get_income_statement": ToolPolicy(
        tool_name="get_income_statement",
        category=ToolCategory.FINANCIAL,
        max_calls_per_query=3,
        estimated_cost=0.02,
        estimated_time=1.0
    ),
    "get_cash_flow": ToolPolicy(
        tool_name="get_cash_flow",
        category=ToolCategory.FINANCIAL,
        max_calls_per_query=3,
        estimated_cost=0.02,
        estimated_time=1.0
    ),
    "get_financial_ratios": ToolPolicy(
        tool_name="get_financial_ratios",
        category=ToolCategory.FINANCIAL,
        max_calls_per_query=5,
        estimated_cost=0.01,
        estimated_time=0.5
    ),
}


@dataclass
class AgentToolAllocation:
    """
    Defines which tools an agent can use

    Implements least privilege principle.
    """
    agent_name: str
    allowed_tools: List[str]
    quotas: Dict[str, int] = field(default_factory=dict)  # tool -> max calls
    cost_limit: float = 1.0  # Total cost limit per query

    def can_use_tool(self, tool_name: str) -> bool:
        """Check if agent can use this tool"""
        return tool_name in self.allowed_tools

    def get_quota(self, tool_name: str) -> int:
        """Get quota for specific tool"""
        # Agent-specific quota overrides global quota
        if tool_name in self.quotas:
            return self.quotas[tool_name]

        # Use global quota from tool catalog
        if tool_name in TOOL_CATALOG:
            return TOOL_CATALOG[tool_name].max_calls_per_query

        return -1  # Unlimited


# Agent tool allocations (Least Privilege Principle)
AGENT_TOOL_ALLOCATIONS = {
    "AnalysisSpecialist": AgentToolAllocation(
        agent_name="AnalysisSpecialist",
        allowed_tools=[
            "get_stock_data",
            "get_stock_price_prediction",
            "get_financial_data",
            "generate_chart_from_data",
            "gemini_search_and_summarize",
            # New database tools
            "get_latest_price",
            "get_price_history",
            "get_company_info",
            "get_balance_sheet",
            "get_income_statement",
            "get_cash_flow",
            "get_financial_ratios",
        ],
        quotas={
            "gemini_search_and_summarize": 2,  # Limit expensive calls
            "get_financial_data": 1,
        },
        cost_limit=0.50
    ),

    "ScreenerSpecialist": AgentToolAllocation(
        agent_name="ScreenerSpecialist",
        allowed_tools=[
            "screen_stocks",
            "get_screener_columns",
            "filter_stocks_by_criteria",
            "rank_stocks_by_score",
            # New database tools for enhanced screening
            "search_stocks_by_criteria",
            "get_financial_ratios",
        ],
        quotas={
            "screen_stocks": 3,
        },
        cost_limit=0.10
    ),

    "InvestmentPlanner": AgentToolAllocation(
        agent_name="InvestmentPlanner",
        allowed_tools=[
            "gather_investment_profile",
            "calculate_portfolio_allocation",
            "generate_entry_strategy",
            "generate_risk_management_plan",
            "generate_monitoring_plan",
            "get_stock_data",  # For validating selections
            "get_financial_data",  # For analysis
        ],
        quotas={
            "gather_investment_profile": 1,
            "calculate_portfolio_allocation": 1,
            "generate_entry_strategy": 1,
            "generate_risk_management_plan": 1,
            "generate_monitoring_plan": 1,
        },
        cost_limit=0.30
    ),

    "DiscoverySpecialist": AgentToolAllocation(
        agent_name="DiscoverySpecialist",
        allowed_tools=[
            "discover_stocks_by_profile",
            "search_potential_stocks",
            "get_stock_details_from_tcbs",
            "gemini_search_and_summarize",
            "get_stock_data",
        ],
        quotas={
            "gemini_search_and_summarize": 3,
            "get_stock_details_from_tcbs": 10,
        },
        cost_limit=0.40
    ),

    "AlertManager": AgentToolAllocation(
        agent_name="AlertManager",
        allowed_tools=[
            "create_alert",
            "get_user_alerts",
            "delete_alert",
        ],
        cost_limit=0.05
    ),

    "SubscriptionManager": AgentToolAllocation(
        agent_name="SubscriptionManager",
        allowed_tools=[
            "create_subscription",
            "get_user_subscriptions",
            "delete_subscription",
        ],
        cost_limit=0.05
    ),

    "DirectExecutor": AgentToolAllocation(
        agent_name="DirectExecutor",
        allowed_tools=[
            "get_stock_data",
            "generate_chart_from_data",
            "get_user_alerts",
            "get_user_subscriptions",
            "create_alert",
            "delete_alert",
            "create_subscription",
            "delete_subscription",
            "get_financial_data",
        ],
        cost_limit=0.10
    )
}


class ResourceMonitor:
    """
    Monitors and enforces resource limits

    Tracks tool usage and costs per agent per query.
    """

    def __init__(self):
        # Per-session tracking
        self._usage: Dict[str, Dict[str, Dict[str, int]]] = {}  # session -> agent -> tool -> count
        self._costs: Dict[str, Dict[str, float]] = {}  # session -> agent -> cost
        self._lock = threading.RLock()

    def check_can_call(
        self,
        session_id: str,
        agent_name: str,
        tool_name: str
    ) -> Tuple[bool, str]:
        """
        Check if agent can call tool

        Returns:
            Tuple of (can_call, reason)
        """
        with self._lock:
            # 1. Check if agent has permission
            if agent_name not in AGENT_TOOL_ALLOCATIONS:
                return False, f"Unknown agent: {agent_name}"

            allocation = AGENT_TOOL_ALLOCATIONS[agent_name]
            if not allocation.can_use_tool(tool_name):
                return False, (
                    f"Agent '{agent_name}' not allowed to use tool '{tool_name}'. "
                    f"Allowed tools: {allocation.allowed_tools}"
                )

            # 2. Check quota
            current_usage = self._get_tool_usage(session_id, agent_name, tool_name)
            quota = allocation.get_quota(tool_name)

            if quota != -1 and current_usage >= quota:
                return False, (
                    f"Quota exceeded for tool '{tool_name}'. "
                    f"Used: {current_usage}, Quota: {quota}"
                )

            # 3. Check cost limit
            current_cost = self._get_agent_cost(session_id, agent_name)
            tool_cost = TOOL_CATALOG.get(tool_name, ToolPolicy(
                tool_name=tool_name,
                category=ToolCategory.STOCK_DATA
            )).estimated_cost

            if current_cost + tool_cost > allocation.cost_limit:
                return False, (
                    f"Cost limit would be exceeded. "
                    f"Current: ${current_cost:.2f}, "
                    f"Tool cost: ${tool_cost:.2f}, "
                    f"Limit: ${allocation.cost_limit:.2f}"
                )

            return True, ""

    def record_tool_call(
        self,
        session_id: str,
        agent_name: str,
        tool_name: str
    ):
        """Record a tool call"""
        with self._lock:
            # Initialize structures
            if session_id not in self._usage:
                self._usage[session_id] = {}
            if agent_name not in self._usage[session_id]:
                self._usage[session_id][agent_name] = {}
            if tool_name not in self._usage[session_id][agent_name]:
                self._usage[session_id][agent_name][tool_name] = 0

            if session_id not in self._costs:
                self._costs[session_id] = {}
            if agent_name not in self._costs[session_id]:
                self._costs[session_id][agent_name] = 0.0

            # Record usage
            self._usage[session_id][agent_name][tool_name] += 1

            # Record cost
            tool_policy = TOOL_CATALOG.get(tool_name)
            if tool_policy:
                self._costs[session_id][agent_name] += tool_policy.estimated_cost

    def _get_tool_usage(
        self,
        session_id: str,
        agent_name: str,
        tool_name: str
    ) -> int:
        """Get current usage count for a tool"""
        if session_id not in self._usage:
            return 0
        if agent_name not in self._usage[session_id]:
            return 0
        return self._usage[session_id][agent_name].get(tool_name, 0)

    def _get_agent_cost(self, session_id: str, agent_name: str) -> float:
        """Get current cost for an agent"""
        if session_id not in self._costs:
            return 0.0
        return self._costs[session_id].get(agent_name, 0.0)

    def get_session_stats(self, session_id: str) -> Dict:
        """Get statistics for a session"""
        with self._lock:
            if session_id not in self._usage:
                return {"agents": {}, "total_cost": 0.0}

            stats = {
                "agents": {},
                "total_cost": 0.0
            }

            for agent_name in self._usage[session_id]:
                agent_stats = {
                    "tool_usage": self._usage[session_id][agent_name].copy(),
                    "total_calls": sum(self._usage[session_id][agent_name].values()),
                    "cost": self._costs[session_id].get(agent_name, 0.0)
                }
                stats["agents"][agent_name] = agent_stats
                stats["total_cost"] += agent_stats["cost"]

            return stats

    def clear_session(self, session_id: str):
        """Clear tracking for a session"""
        with self._lock:
            if session_id in self._usage:
                del self._usage[session_id]
            if session_id in self._costs:
                del self._costs[session_id]


# Global resource monitor
resource_monitor = ResourceMonitor()


class QuotaExceededError(Exception):
    """Raised when tool quota is exceeded"""
    pass


class CostLimitError(Exception):
    """Raised when cost limit is exceeded"""
    pass


class UnauthorizedToolError(Exception):
    """Raised when agent tries to use unauthorized tool"""
    pass
