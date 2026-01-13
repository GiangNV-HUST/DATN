"""
Hybrid Multi-Agent System

This module provides the Multi-Agent Orchestrator with 8 Specialist Agents:
1. AnalysisSpecialist - Stock analysis (technical, fundamental)
2. ScreenerSpecialist - Stock screening and filtering
3. AlertManager - Price alert management
4. InvestmentPlanner - Investment planning
5. DiscoverySpecialist - Stock discovery
6. SubscriptionManager - Subscription management
7. MarketContextSpecialist - Market overview (VN-Index, sectors)
8. ComparisonSpecialist - Stock comparison
"""

from .orchestrator import MultiAgentOrchestrator, SpecialistRouter

__all__ = [
    'MultiAgentOrchestrator',
    'SpecialistRouter',
]
