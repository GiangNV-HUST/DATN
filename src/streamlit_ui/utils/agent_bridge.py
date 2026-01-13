"""
Bridge between Streamlit UI and MultiAgentOrchestrator.
This is the ONLY place where we interact with the agent system.

UPGRADED: Now uses MultiAgentOrchestrator with 6 Specialized Agents:
- AnalysisSpecialist
- ScreenerSpecialist
- AlertManager
- InvestmentPlanner
- DiscoverySpecialist
- SubscriptionManager
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Callable
import logging

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)


class AgentBridge:
    """
    Bridge to communicate with the MultiAgentOrchestrator (6 Specialists).
    Keeps ALL agent logic intact - just provides an interface for Streamlit.
    """

    def __init__(self):
        self.orchestrator = None
        self._initialized = False
        self._init_lock = asyncio.Lock()

    async def initialize(self):
        """
        Lazy initialization of MultiAgentOrchestrator.
        Only imports and initializes when first needed.
        """
        if self._initialized:
            return

        async with self._init_lock:
            if self._initialized:  # Double-check after acquiring lock
                return

            try:
                # Import Multi-Agent orchestrator (upgraded from HybridOrchestrator)
                from src.ai_agent_hybrid.hybrid_system.orchestrator.multi_agent_orchestrator import MultiAgentOrchestrator

                # Initialize orchestrator with DirectMCPClient mode (in-process)
                self.orchestrator = MultiAgentOrchestrator(use_direct_client=True)
                await self.orchestrator.initialize()

                self._initialized = True

                logger.info(f"MultiAgentOrchestrator initialized with {len(self.orchestrator.specialists)} specialists!")

            except Exception as e:
                logger.error(f"Failed to initialize MultiAgentOrchestrator: {e}")
                raise

    async def process_query(
        self,
        user_query: str,
        user_id: str,
        session_id: str,
        enable_streaming: bool = True,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Process user query through the agent system.

        Args:
            user_query: The user's question/request
            user_id: User identifier
            session_id: Session identifier for conversation context
            enable_streaming: Whether to enable streaming responses
            progress_callback: Optional callback for progress updates

        Returns:
            Dict with response and metadata
        """

        # Ensure orchestrator is initialized
        if not self._initialized:
            await self.initialize()

        try:
            # Collect streaming results from orchestrator
            full_response = []
            metadata = {}

            async for event in self.orchestrator.process_query(
                user_query=user_query,
                user_id=user_id,
                mode="auto",
                session_id=session_id
            ):
                event_type = event.get("type", "")

                if event_type == "routing_decision":
                    metadata["mode"] = event["data"].get("mode", "unknown")
                    metadata["routing_time"] = event["data"].get("routing_time", 0)

                elif event_type == "chunk":
                    chunk_data = event.get("data", "")
                    # Handle both string chunks (from agent mode) and dict results (from direct mode)
                    if isinstance(chunk_data, dict):
                        chunk = chunk_data.get("response", str(chunk_data))
                        if "tools_used" in chunk_data:
                            metadata["tools_used"] = chunk_data.get("tools_used", [])
                    else:
                        chunk = str(chunk_data)
                    full_response.append(chunk)
                    # Call progress callback if provided
                    if enable_streaming and progress_callback:
                        await progress_callback(chunk)

                elif event_type == "complete":
                    metadata["execution_time"] = event["data"].get("execution_time", 0)
                    metadata["total_time"] = event["data"].get("total_time", 0)
                    metadata["tools_used"] = event["data"].get("tools_used", [])

            return {
                "response": "".join(full_response),
                **metadata
            }

        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            return {
                "response": f"Xin lỗi, đã có lỗi xảy ra: {str(e)}",
                "mode": "error",
                "execution_time": 0,
                "error": str(e)
            }

    async def _handle_streaming(self, result: Dict[str, Any], callback: Callable):
        """
        Handle streaming progress updates.
        """
        try:
            # If result has streaming data, call callback
            if "progress" in result:
                await callback(result["progress"])
        except Exception as e:
            logger.warning(f"Error in streaming callback: {e}")

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get system metrics from orchestrator.
        """
        if not self._initialized or not self.orchestrator:
            return {}

        try:
            return self.orchestrator.get_metrics()
        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            return {}

    async def get_user_alerts(self, user_id: str) -> list:
        """
        Get user's alerts through the MCP client.
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Access MCP client from orchestrator
            mcp_client = self.orchestrator.mcp_client
            result = await mcp_client.call_tool("get_user_alerts", {"user_id": user_id})
            return result.get("alerts", [])
        except Exception as e:
            logger.error(f"Error getting alerts: {e}")
            return []

    async def create_alert(
        self,
        user_id: str,
        symbol: str,
        condition: str,
        target_price: float,
        alert_type: str = "price"
    ) -> Dict[str, Any]:
        """
        Create a new alert.
        """
        if not self._initialized:
            await self.initialize()

        try:
            mcp_client = self.orchestrator.mcp_client
            result = await mcp_client.call_tool("create_alert", {
                "user_id": user_id,
                "symbol": symbol,
                "condition": condition,
                "target_price": target_price,
                "alert_type": alert_type
            })
            return result
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
            return {"success": False, "error": str(e)}

    async def delete_alert(self, alert_id: str) -> Dict[str, Any]:
        """
        Delete an alert.
        """
        if not self._initialized:
            await self.initialize()

        try:
            mcp_client = self.orchestrator.mcp_client
            result = await mcp_client.call_tool("delete_alert", {"alert_id": alert_id})
            return result
        except Exception as e:
            logger.error(f"Error deleting alert: {e}")
            return {"success": False, "error": str(e)}

    async def get_portfolio_overview(self, user_id: str) -> Dict[str, Any]:
        """
        Get portfolio overview (alerts + subscriptions).
        """
        if not self._initialized:
            await self.initialize()

        try:
            mcp_client = self.orchestrator.mcp_client

            # Get alerts and subscriptions in parallel
            alerts_task = mcp_client.call_tool("get_user_alerts", {"user_id": user_id})
            subs_task = mcp_client.call_tool("get_user_subscriptions", {"user_id": user_id})

            alerts_result, subs_result = await asyncio.gather(
                alerts_task,
                subs_task,
                return_exceptions=True
            )

            return {
                "alerts": alerts_result.get("alerts", []) if not isinstance(alerts_result, Exception) else [],
                "subscriptions": subs_result.get("subscriptions", []) if not isinstance(subs_result, Exception) else []
            }
        except Exception as e:
            logger.error(f"Error getting portfolio overview: {e}")
            return {"alerts": [], "subscriptions": []}


# Singleton instance
_agent_bridge = None


def get_agent_bridge() -> AgentBridge:
    """
    Get or create the singleton AgentBridge instance.
    """
    global _agent_bridge
    if _agent_bridge is None:
        _agent_bridge = AgentBridge()
    return _agent_bridge
