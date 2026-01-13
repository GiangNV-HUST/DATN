"""
8 Specialist Agents for Multi-Agent Stock System

Agents:
1. AnalysisSpecialist - Stock analysis (technical, fundamental, prediction)
2. ScreenerSpecialist - Stock screening and filtering
3. AlertManager - Price alert management
4. InvestmentPlanner - Investment planning and portfolio
5. DiscoverySpecialist - Stock discovery and recommendations
6. SubscriptionManager - Subscription/watchlist management
7. MarketContextSpecialist - Market overview (VN-Index, sectors, breadth)
8. ComparisonSpecialist - Stock comparison (side-by-side, peer)
"""

from .mcp_tool_wrapper import MCPToolWrapper

# 8 Specialized Agents
from .analysis_specialist import AnalysisSpecialist
from .screener_specialist import ScreenerSpecialist
from .alert_manager import AlertManager
from .investment_planner import InvestmentPlanner
from .discovery_specialist import DiscoverySpecialist
from .subscription_manager import SubscriptionManager
from .market_context_specialist import MarketContextSpecialist
from .comparison_specialist import ComparisonSpecialist

__all__ = [
    'MCPToolWrapper',
    # 8 Specialists
    'AnalysisSpecialist',
    'ScreenerSpecialist',
    'AlertManager',
    'InvestmentPlanner',
    'DiscoverySpecialist',
    'SubscriptionManager',
    'MarketContextSpecialist',
    'ComparisonSpecialist',
]
