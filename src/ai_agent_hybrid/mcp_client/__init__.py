"""
MCP Client module for Multi-Agent Stock System

Provides:
- EnhancedMCPClient: Subprocess-based MCP client with caching
- DirectMCPClient: In-process MCP client (no subprocess)
"""

from .enhanced_client import EnhancedMCPClient
from .direct_client import DirectMCPClient

__all__ = [
    'EnhancedMCPClient',
    'DirectMCPClient',
]
