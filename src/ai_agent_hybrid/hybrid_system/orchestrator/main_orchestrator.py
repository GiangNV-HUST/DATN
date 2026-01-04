"""
Main Orchestrator - The Heart of Hybrid System

Connects:
- AI Router (intelligent routing)
- Enhanced MCP Client (caching + resilience)
- Orchestrator Agent (reasoning)
- Direct Executor (fast path)

Provides unified interface for dual-mode execution.
"""

from .ai_router import AIRouter, AIRoutingDecision
from ..agents.orchestrator_agent import OrchestratorAgent
from ..executors.direct_executor import DirectExecutor
import sys
import os

# Add ai_agent_mcp to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'ai_agent_mcp'))

from typing import AsyncIterator, Optional, Dict, Literal
import time


class HybridOrchestrator:
    """
    Main orchestrator for Hybrid System

    Features:
    - AI-powered routing (ROOT_AGENT concept from OLD)
    - Dual-mode execution (agent vs direct)
    - Enhanced MCP client with caching
    - Event streaming
    - Comprehensive metrics

    Usage:
        orchestrator = HybridOrchestrator()
        await orchestrator.initialize()

        async for event in orchestrator.process_query("Phân tích VCB", "user123"):
            if event["type"] == "chunk":
                print(event["data"])
    """

    def __init__(self, server_script_path: str = None):
        """
        Initialize Hybrid Orchestrator

        Args:
            server_script_path: Path to MCP server script
                              (default: ../ai_agent_mcp/mcp_server/server.py)
        """
        # Default MCP server path
        if server_script_path is None:
            server_script_path = os.path.join(
                os.path.dirname(__file__),
                "..", "..", "..", "ai_agent_mcp", "mcp_server", "server.py"
            )

        self.server_script_path = server_script_path

        # Import EnhancedMCPClient
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from mcp_client import EnhancedMCPClient

        # Initialize components
        self.mcp_client = EnhancedMCPClient(server_script_path)
        self.ai_router = AIRouter()
        self.agent = None  # Lazy init
        self.direct_executor = DirectExecutor(self.mcp_client)

        # Metrics
        self.query_metrics = {
            "agent_mode_count": 0,
            "direct_mode_count": 0,
            "total_time_saved": 0,
            "ai_router_time": 0,
            "routing_decisions": [],
        }

    async def initialize(self):
        """Initialize orchestrator - connect to MCP server"""
        await self.mcp_client.connect()
        print("✅ Hybrid Orchestrator initialized")

    async def _get_agent(self):
        """Lazy initialization of agent (only when needed for agent mode)"""
        if self.agent is None:
            self.agent = OrchestratorAgent(self.mcp_client)
        return self.agent

    async def process_query(
        self,
        user_query: str,
        user_id: str,
        mode: Optional[Literal["auto", "agent", "direct"]] = None,
        session_id: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[Dict]:
        """
        Process user query with intelligent routing

        Args:
            user_query: User's question
            user_id: User ID
            mode: Execution mode:
                  - "auto": AI router decides (default)
                  - "agent": Force agent mode
                  - "direct": Force direct mode
            session_id: Session ID for conversation tracking
            **kwargs: Additional parameters

        Yields:
            Dict with:
                - type: "status", "routing_decision", "chunk", "complete", "error"
                - data: Event data
        """
        start_time = time.time()
        mode = mode or "auto"

        # 1. AI-Powered Routing (if auto mode)
        if mode == "auto":
            routing_start = time.time()

            yield {
                "type": "status",
                "data": "🧠 AI Router đang phân tích query..."
            }

            try:
                decision = await self.ai_router.analyze(user_query)
                selected_mode = decision.mode

                routing_time = time.time() - routing_start
                self.query_metrics["ai_router_time"] += routing_time

                # Track decision
                self.query_metrics["routing_decisions"].append({
                    "query": user_query,
                    "decision": decision,
                    "routing_time": routing_time
                })

                # Yield routing decision
                yield {
                    "type": "routing_decision",
                    "data": {
                        "mode": selected_mode,
                        "complexity": decision.complexity,
                        "confidence": decision.confidence,
                        "reasoning": decision.reasoning,
                        "estimated_time": decision.estimated_time,
                        "routing_time": routing_time,
                        "suggested_tools": decision.suggested_tools
                    }
                }

            except Exception as e:
                # Fallback to agent mode if router fails
                print(f"⚠️ AI Router failed: {e}, defaulting to agent mode")
                selected_mode = "agent"
                decision = None

        else:
            # Manual mode selection
            selected_mode = mode
            decision = None

        # 2. Execute based on selected mode
        try:
            if selected_mode == "agent":
                # AGENT MODE - Complex reasoning
                self.query_metrics["agent_mode_count"] += 1

                yield {
                    "type": "status",
                    "data": "🤖 Agent Mode: Đang phân tích với AI reasoning..."
                }

                agent = await self._get_agent()

                async for chunk in agent.process_query(
                    user_query,
                    user_id,
                    session_id
                ):
                    yield {
                        "type": "chunk",
                        "data": chunk
                    }

            else:
                # DIRECT MODE - Fast execution
                self.query_metrics["direct_mode_count"] += 1

                yield {
                    "type": "status",
                    "data": "⚡ Direct Mode: Thực thi nhanh..."
                }

                result = await self.direct_executor.execute(
                    user_query,
                    user_id,
                    suggested_tools=decision.suggested_tools if decision else None
                )

                yield {
                    "type": "chunk",
                    "data": result
                }

            # 3. Send completion metadata
            elapsed_time = time.time() - start_time

            if decision:
                time_saved = decision.estimated_time - elapsed_time
                self.query_metrics["total_time_saved"] += max(0, time_saved)
            else:
                time_saved = None

            yield {
                "type": "complete",
                "data": {
                    "elapsed_time": elapsed_time,
                    "mode_used": selected_mode,
                    "estimated_time": decision.estimated_time if decision else None,
                    "time_saved": time_saved
                }
            }

        except Exception as e:
            yield {
                "type": "error",
                "data": {
                    "error": str(e),
                    "mode": selected_mode
                }
            }

    async def get_stock_info(self, symbol: str) -> Dict:
        """
        Quick helper for getting stock info (always direct mode)

        Args:
            symbol: Stock symbol

        Returns:
            Stock data dict
        """
        result = await self.mcp_client.get_stock_data([symbol], lookback_days=7)
        return result

    async def analyze_stock(self, symbol: str, user_id: str = "system") -> AsyncIterator[str]:
        """
        Deep analysis (always agent mode)

        Args:
            symbol: Stock symbol
            user_id: User ID (default: "system")

        Yields:
            Analysis chunks
        """
        async for event in self.process_query(
            f"Phân tích chuyên sâu cổ phiếu {symbol}",
            user_id=user_id,
            mode="agent"
        ):
            if event["type"] == "chunk":
                yield event["data"]

    def get_metrics(self) -> Dict:
        """Get comprehensive system metrics"""
        client_metrics = self.mcp_client.get_metrics()
        router_stats = self.ai_router.get_stats()

        total_queries = (
            self.query_metrics["agent_mode_count"] +
            self.query_metrics["direct_mode_count"]
        )

        avg_routing_time = (
            self.query_metrics["ai_router_time"] / total_queries
            if total_queries > 0 else 0
        )

        return {
            # Query metrics
            "total_queries": total_queries,
            "agent_mode_count": self.query_metrics["agent_mode_count"],
            "direct_mode_count": self.query_metrics["direct_mode_count"],
            "agent_mode_percentage": (
                self.query_metrics["agent_mode_count"] / total_queries * 100
                if total_queries > 0 else 0
            ),
            "total_time_saved": self.query_metrics["total_time_saved"],
            "avg_routing_time": avg_routing_time,

            # MCP Client metrics
            **client_metrics,

            # AI Router stats
            "router_stats": router_stats,

            # Executor stats
            "direct_executor_stats": self.direct_executor.get_stats(),
        }

    def get_routing_analysis(self) -> Dict:
        """Analyze routing decisions"""
        decisions = self.query_metrics["routing_decisions"]

        if not decisions:
            return {"message": "No routing decisions yet"}

        agent_decisions = [d for d in decisions if d["decision"].mode == "agent"]
        direct_decisions = [d for d in decisions if d["decision"].mode == "direct"]

        return {
            "total_decisions": len(decisions),
            "agent_mode_count": len(agent_decisions),
            "direct_mode_count": len(direct_decisions),
            "avg_confidence": sum(d["decision"].confidence for d in decisions) / len(decisions),
            "avg_complexity": sum(d["decision"].complexity for d in decisions) / len(decisions),
            "avg_routing_time": sum(d["routing_time"] for d in decisions) / len(decisions),
            "recent_decisions": [
                {
                    "query": d["query"][:50] + "..." if len(d["query"]) > 50 else d["query"],
                    "mode": d["decision"].mode,
                    "confidence": d["decision"].confidence,
                    "complexity": d["decision"].complexity,
                    "reasoning": d["decision"].reasoning[:100] + "..." if len(d["decision"].reasoning) > 100 else d["decision"].reasoning
                }
                for d in decisions[-10:]  # Last 10
            ]
        }

    def clear_router_cache(self):
        """Clear AI router decision cache"""
        self.ai_router.clear_cache()

    def clear_mcp_cache(self, pattern: Optional[str] = None):
        """Clear MCP client cache"""
        self.mcp_client.clear_cache(pattern)

    def clear_agent_history(self, session_id: str):
        """Clear agent conversation history"""
        if self.agent:
            self.agent.clear_history(session_id)

    async def cleanup(self):
        """Cleanup resources"""
        await self.mcp_client.disconnect()
        print("✅ Hybrid Orchestrator cleaned up")
