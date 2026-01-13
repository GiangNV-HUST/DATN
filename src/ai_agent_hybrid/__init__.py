"""
Multi-Agent Stock Analysis System

A Multi-Agent AI system for Vietnamese stock market analysis with 8 Specialist Agents:
1. AnalysisSpecialist - Stock analysis (technical, fundamental)
2. ScreenerSpecialist - Stock screening and filtering
3. AlertManager - Price alert management
4. InvestmentPlanner - Investment planning
5. DiscoverySpecialist - Stock discovery
6. SubscriptionManager - Subscription management
7. MarketContextSpecialist - Market overview (VN-Index, sectors)
8. ComparisonSpecialist - Stock comparison
"""

__version__ = "2.0.0"
__author__ = "AI Agent Team"

from .hybrid_system.orchestrator import MultiAgentOrchestrator, SpecialistRouter
from .mcp_client import EnhancedMCPClient, DirectMCPClient

__all__ = [
    'MultiAgentOrchestrator',
    'SpecialistRouter',
    'EnhancedMCPClient',
    'DirectMCPClient',
]
