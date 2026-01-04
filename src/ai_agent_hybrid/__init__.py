"""
AI Agent Hybrid System

Combines the best of Multi-Agent (OLD) and MCP (NEW) systems:
- AI-powered routing (from OLD)
- MCP tools (from NEW)
- Enhanced caching and resilience (Hybrid innovation)
"""

__version__ = "1.0.0"
__author__ = "AI Agent Team"

from .hybrid_system.orchestrator import HybridOrchestrator, AIRouter
from .mcp_client import EnhancedMCPClient

__all__ = [
    'HybridOrchestrator',
    'AIRouter',
    'EnhancedMCPClient',
]
