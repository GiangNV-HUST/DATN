"""
Agents module for Hybrid Stock Agent System

Contains:
- Hybrid Orchestrator (UPGRADED with full integration)
- Legacy Orchestrator (original version)
- 6 Specialized Agents
- MCP Tool Wrapper
"""

from .mcp_tool_wrapper import MCPToolWrapper
from .orchestrator_agent import OrchestratorAgent
from .hybrid_orchestrator import HybridOrchestrator

# Specialized Agents
from .analysis_specialist import AnalysisSpecialist
from .screener_specialist import ScreenerSpecialist
from .alert_manager import AlertManager
from .investment_planner import InvestmentPlanner
from .discovery_specialist import DiscoverySpecialist
from .subscription_manager import SubscriptionManager

__all__ = [
    'MCPToolWrapper',
    'OrchestratorAgent',
    'HybridOrchestrator',  # NEW: Upgraded version
    'AnalysisSpecialist',
    'ScreenerSpecialist',
    'AlertManager',
    'InvestmentPlanner',
    'DiscoverySpecialist',
    'SubscriptionManager',
]
