"""
Multi-Agent Orchestrator - Upgrade from Main Orchestrator

Integrates the Multi-Specialist Agents architecture into the main orchestrator,
providing the same interface as HybridOrchestrator but with:
- 8 Specialized Agents (AnalysisSpecialist, ScreenerSpecialist, MarketContextSpecialist,
  ComparisonSpecialist, AlertManager, InvestmentPlanner, DiscoverySpecialist, SubscriptionManager)
- AI-Powered Specialist Router (OpenAI GPT-4o-mini) for intelligent routing
- Message Protocol (AgentMessage, MessageBus)
- State Management (SharedState, ExecutionState)
- Evaluation Layer (CriticAgent, ArbitrationAgent)
- Resource Monitoring (Tool quotas, cost limits)

UPGRADED: Now uses SpecialistRouter (AI-powered) instead of pattern matching
for more accurate query routing to appropriate specialists.

NEW v2.0: Added MarketContextSpecialist and ComparisonSpecialist for:
- Market overview (VN-Index, sector performance, market breadth)
- Stock comparison (side-by-side, peer comparison, relative valuation)
"""

import sys
import os
import time
from typing import AsyncIterator, Optional, Dict, Literal, List

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'ai_agent_mcp'))

# Import MCP clients
mcp_client_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'mcp_client')
if mcp_client_path not in sys.path:
    sys.path.insert(0, mcp_client_path)

# Import specialists (8 agents)
from ..agents.analysis_specialist import AnalysisSpecialist
from ..agents.screener_specialist import ScreenerSpecialist
from ..agents.alert_manager import AlertManager
from ..agents.investment_planner import InvestmentPlanner
from ..agents.discovery_specialist import DiscoverySpecialist
from ..agents.subscription_manager import SubscriptionManager
from ..agents.market_context_specialist import MarketContextSpecialist
from ..agents.comparison_specialist import ComparisonSpecialist

# Import core infrastructure
from ..core.message_protocol import (
    AgentMessage, MessageType, MessagePriority, message_bus
)
from ..core.state_management import state_manager
from ..core.termination import ExecutionGuard
from ..core.tool_allocation import resource_monitor
from ..core.evaluation import critic_agent, arbitration_agent

# Import AI-Powered Specialist Router for intelligent routing
from .specialist_router import SpecialistRouter


class MultiAgentOrchestrator:
    """
    Multi-Agent Orchestrator with 8 Specialized Agents + AI-Powered Routing

    Architecture:
    - AI-Powered Specialist Router (OpenAI GPT-4o-mini) for intelligent routing
    - Routes queries to appropriate specialist agents based on intent
    - Coordinates multi-agent workflows for complex queries
    - Maintains conversation state and memory
    - Evaluates response quality
    - Enforces resource limits

    Routing Modes:
    - "ai": Use AI Router (default) - Best accuracy, ~200-500ms latency
    - "pattern": Use pattern matching - Fast (~1ms), ~85% accuracy
    - "auto": AI with pattern fallback

    Specialists (8 agents):
    1. AnalysisSpecialist - Stock analysis (price, technical, fundamental)
    2. ScreenerSpecialist - Stock screening and filtering
    3. AlertManager - Price alerts management
    4. InvestmentPlanner - Investment planning and portfolio allocation
    5. DiscoverySpecialist - Discover potential stocks
    6. SubscriptionManager - Subscription management
    7. MarketContextSpecialist - Market overview (VN-Index, sectors, breadth) [NEW]
    8. ComparisonSpecialist - Stock comparison (side-by-side, peer) [NEW]

    Usage:
        orchestrator = MultiAgentOrchestrator()
        await orchestrator.initialize()

        async for event in orchestrator.process_query("Phan tich VCB", "user123"):
            if event["type"] == "chunk":
                print(event["data"])
    """

    def __init__(self, server_script_path: str = None, use_direct_client: bool = False, routing_mode: str = "ai"):
        """
        Initialize Multi-Agent Orchestrator

        Args:
            server_script_path: Path to MCP server script
            use_direct_client: If True, use DirectMCPClient (in-process)
            routing_mode: Routing strategy - "ai" (default), "pattern", or "auto"
        """
        # Default MCP server path
        if server_script_path is None:
            server_script_path = os.path.join(
                os.path.dirname(__file__),
                "..", "..", "..", "ai_agent_mcp", "mcp_server", "server.py"
            )

        self.server_script_path = server_script_path
        self.use_direct_client = use_direct_client
        self.routing_mode = routing_mode  # "ai", "pattern", or "auto"

        # Choose client type based on mode
        if use_direct_client:
            from direct_client import DirectMCPClient
            self.mcp_client = DirectMCPClient(server_script_path)
        else:
            from enhanced_client import EnhancedMCPClient
            self.mcp_client = EnhancedMCPClient(server_script_path)

        # Initialize AI-Powered Specialist Router
        self.specialist_router = SpecialistRouter(use_cache=True)

        # Specialists will be initialized after MCP client connects
        self.specialists = {}

        # Execution guard
        self.execution_guard = ExecutionGuard()

        # Metrics
        self.query_metrics = {
            "agent_mode_count": 0,
            "direct_mode_count": 0,
            "total_time_saved": 0,
            "ai_router_time": 0,
            "routing_decisions": [],
            "specialist_usage": {
                "AnalysisSpecialist": 0,
                "ScreenerSpecialist": 0,
                "AlertManager": 0,
                "InvestmentPlanner": 0,
                "DiscoverySpecialist": 0,
                "SubscriptionManager": 0,
                "MarketContextSpecialist": 0,
                "ComparisonSpecialist": 0,
            }
        }

    async def initialize(self):
        """Initialize orchestrator - connect to MCP server and create specialists"""
        await self.mcp_client.connect()

        # Initialize all 8 specialized agents after MCP client is connected
        self.specialists = {
            "AnalysisSpecialist": AnalysisSpecialist(self.mcp_client),
            "ScreenerSpecialist": ScreenerSpecialist(self.mcp_client),
            "AlertManager": AlertManager(self.mcp_client),
            "InvestmentPlanner": InvestmentPlanner(self.mcp_client),
            "DiscoverySpecialist": DiscoverySpecialist(self.mcp_client),
            "SubscriptionManager": SubscriptionManager(self.mcp_client),
            "MarketContextSpecialist": MarketContextSpecialist(self.mcp_client),
            "ComparisonSpecialist": ComparisonSpecialist(self.mcp_client),
        }

    def _classify_query(self, user_query: str, user_id: str) -> Dict:
        """
        Classify query and determine which specialist to use

        Args:
            user_query: User's query
            user_id: User ID

        Returns:
            Dict with routing information
        """
        query_lower = user_query.lower()

        # MARKET CONTEXT - Market overview (check FIRST for market-wide queries!)
        if any(kw in query_lower for kw in [
            "vn-index", "vnindex", "hnx-index", "hnxindex", "upcom",
            "thi truong", "thị trường", "market",
            "tang giam", "tăng giảm", "nganh", "ngành", "sector",
            "breadth", "market breadth", "khoi ngoai", "khối ngoại", "foreign",
            "tong quan", "tổng quan", "overview",
            "tai sao thi truong", "tại sao thị trường", "why market"
        ]) and not self._extract_symbols(user_query):
            return {
                "type": "simple",
                "specialist": "MarketContextSpecialist",
                "method": "analyze",
                "params": {
                    "user_query": user_query
                }
            }

        # COMPARISON - Stock comparison (check BEFORE analysis!)
        symbols = self._extract_symbols(user_query)
        if len(symbols) >= 2 and any(kw in query_lower for kw in [
            "so sanh", "so sánh", "compare", "vs", "hay", "với",
            "tot hon", "tốt hơn", "better", "hơn",
            "khac nhau", "khác nhau", "difference"
        ]):
            return {
                "type": "simple",
                "specialist": "ComparisonSpecialist",
                "method": "analyze",
                "params": {
                    "symbols": symbols,
                    "user_query": user_query
                }
            }

        # SCREENING - Stock filtering (check FIRST before analysis!)
        # Keywords like "loc", "tim" with criteria like "<", ">" indicate screening
        if any(kw in query_lower for kw in [
            "lọc", "loc", "sàng lọc", "sang loc", "screen",
            "top", "cổ phiếu tốt", "co phieu tot",
            "thanh khoản", "thanh khoan", "vốn hóa", "von hoa",
            "tăng mạnh", "tang manh", "giảm mạnh", "giam manh",
            "tăng giá", "tang gia", "giảm giá", "giam gia"
        ]) or (
            # Also match filtering patterns like "P/E < 15" or "ROE > 15"
            any(op in user_query for op in ["<", ">", "<=", ">="]) and
            any(kw in query_lower for kw in ["loc", "tim", "tìm", "find", "filter"])
        ):
            return {
                "type": "simple",
                "specialist": "ScreenerSpecialist",
                "method": "screen",
                "params": {
                    "user_query": user_query
                }
            }

        # DISCOVERY - Find potential stocks (check before analysis!)
        if any(kw in query_lower for kw in [
            "khám phá", "kham pha", "discover", "tiềm năng", "tiem nang",
            "khuyến nghị", "khuyen nghi", "recommend", "gợi ý", "goi y",
            "co phieu nao", "cổ phiếu nào", "nên mua gì", "nen mua gi",
            "đáng mua", "dang mua", "xu hướng", "xu huong", "hot", "trend",
            "thị trường", "thi truong"
        ]) and not self._extract_symbols(user_query):
            return {
                "type": "simple",
                "specialist": "DiscoverySpecialist",
                "method": "discover",
                "params": {
                    "user_query": user_query
                }
            }

        # ANALYSIS - Price, technical, fundamental analysis (single stock)
        if any(kw in query_lower for kw in [
            "phan tich", "phân tích", "giá", "gia", "analyze",
            "báo cáo tài chính", "bao cao tai chinh",
            "kỹ thuật", "ky thuat", "cơ bản", "co ban", "dự đoán", "du doan",
            "predict", "rsi", "macd", "ma", "p/e", "pe", "roe", "eps"
        ]):
            return {
                "type": "simple",
                "specialist": "AnalysisSpecialist",
                "method": "analyze",
                "params": {
                    "symbols": self._extract_symbols(user_query),
                    "user_query": user_query
                }
            }

        # ALERTS - Price alerts
        if any(kw in query_lower for kw in [
            "cảnh báo", "canh bao", "alert", "thông báo", "thong bao"
        ]):
            if any(w in query_lower for w in ["tạo", "tao", "create", "đặt", "dat"]):
                return {
                    "type": "simple",
                    "specialist": "AlertManager",
                    "method": "create_alert",
                    "params": self._parse_alert_params(user_query, user_id)
                }
            else:
                return {
                    "type": "simple",
                    "specialist": "AlertManager",
                    "method": "get_alerts",
                    "params": {"user_id": user_id}
                }

        # INVESTMENT PLANNING - Portfolio, advice, DCA
        if any(kw in query_lower for kw in [
            "đầu tư", "dau tu", "investment", "tư vấn", "tu van",
            "kế hoạch", "ke hoach", "phân bổ", "phan bo", "danh mục", "danh muc",
            "portfolio", "dca", "vốn", "von", "triệu", "trieu", "tỷ", "ty"
        ]):
            return {
                "type": "simple",
                "specialist": "InvestmentPlanner",
                "method": "create_investment_plan",
                "params": self._parse_investment_params(user_query, user_id)
            }

        # SUBSCRIPTION - Subscription management / Watchlist
        if any(kw in query_lower for kw in [
            "đăng ký", "dang ky", "subscription", "gói", "goi", "premium",
            "theo dõi", "theo doi", "watchlist", "danh sách theo dõi"
        ]):
            if any(w in query_lower for w in ["xem", "view", "danh sách", "danh sach", "list"]):
                return {
                    "type": "simple",
                    "specialist": "SubscriptionManager",
                    "method": "get_subscriptions",
                    "params": {"user_id": user_id}
                }
            elif any(w in query_lower for w in ["bỏ", "bo", "xóa", "xoa", "hủy", "huy", "remove", "delete"]):
                return {
                    "type": "simple",
                    "specialist": "SubscriptionManager",
                    "method": "delete_subscription",
                    "params": self._parse_subscription_params(user_query, user_id)
                }
            else:
                return {
                    "type": "simple",
                    "specialist": "SubscriptionManager",
                    "method": "create_subscription",
                    "params": self._parse_subscription_params(user_query, user_id)
                }

        # Default: AnalysisSpecialist for general stock questions
        return {
            "type": "simple",
            "specialist": "AnalysisSpecialist",
            "method": "analyze",
            "params": {
                "symbols": self._extract_symbols(user_query),
                "user_query": user_query
            }
        }

    def _extract_symbols(self, query: str) -> List[str]:
        """Extract stock symbols from query"""
        import re
        matches = re.findall(r'\b[A-Z]{3,4}\b', query.upper())

        # Common Vietnamese stocks
        common = ["VCB", "FPT", "HPG", "VIC", "VNM", "ACB", "MSN", "TCB", "VHM", "VPB",
                  "MBB", "BID", "CTG", "STB", "HDB", "SSI", "VND", "HCM", "GAS", "PNJ",
                  "MWG", "REE", "DPM", "PVD", "PLX", "PVS", "GVR", "POW", "VJC", "HVN"]

        symbols = []
        for match in matches:
            if match in common or len(match) == 3:
                symbols.append(match)

        return list(set(symbols)) if symbols else []

    def _parse_alert_params(self, query: str, user_id: str) -> Dict:
        """Parse alert creation parameters"""
        symbols = self._extract_symbols(query)
        return {
            "user_id": user_id,
            "symbol": symbols[0] if symbols else "VCB",
            "alert_type": "price",
            "condition": ">",
            "target_value": None
        }

    def _parse_investment_params(self, query: str, user_id: str) -> Dict:
        """Parse investment planning parameters"""
        import re

        capital = 100_000_000  # Default 100M

        # Try to find numbers with units
        numbers = re.findall(r'(\d+(?:[.,]\d+)?)\s*(triệu|trieu|tr|tỷ|ty)', query.lower())
        if numbers:
            amount, unit = numbers[0]
            amount = float(amount.replace(",", "."))
            if unit in ["triệu", "trieu", "tr"]:
                capital = int(amount * 1_000_000)
            elif unit in ["tỷ", "ty"]:
                capital = int(amount * 1_000_000_000)

        # Risk tolerance
        risk = "medium"
        if any(kw in query.lower() for kw in ["an toàn", "an toan", "thấp", "thap", "bảo thủ", "bao thu"]):
            risk = "low"
        elif any(kw in query.lower() for kw in ["cao", "mạo hiểm", "mao hiem", "tích cực", "tich cuc"]):
            risk = "high"

        # Time horizon
        horizon = "medium"
        if any(kw in query.lower() for kw in ["ngắn hạn", "ngan han", "short"]):
            horizon = "short"
        elif any(kw in query.lower() for kw in ["dài hạn", "dai han", "long"]):
            horizon = "long"

        return {
            "user_id": user_id,
            "capital": capital,
            "risk_tolerance": risk,
            "time_horizon": horizon
        }

    def _parse_subscription_params(self, query: str, user_id: str) -> Dict:
        """Parse subscription parameters"""
        sub_type = "premium"
        if "basic" in query.lower():
            sub_type = "basic"
        elif "pro" in query.lower():
            sub_type = "pro"

        return {
            "user_id": user_id,
            "subscription_type": sub_type,
            "duration_months": 1,
            "auto_renew": False
        }

    async def process_query(
        self,
        user_query: str,
        user_id: str,
        mode: Optional[Literal["auto", "ai", "pattern"]] = None,
        session_id: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[Dict]:
        """
        Process user query with multi-agent orchestration

        Args:
            user_query: User's question
            user_id: User ID
            mode: Routing mode - "ai" (AI Router), "pattern" (keyword matching), "auto" (default from init)
            session_id: Session ID for conversation tracking
            **kwargs: Additional parameters

        Yields:
            Dict with:
                - type: "status", "routing_decision", "chunk", "complete", "error"
                - data: Event data
        """
        start_time = time.time()
        session_id = session_id or f"{user_id}_{int(time.time())}"

        # Determine routing mode
        routing_mode = mode or self.routing_mode

        # Create session if not exists
        if not state_manager.has_session(session_id):
            state_manager.create_session(session_id, user_id, f"User {user_id}")

        # Get execution state
        exec_state = state_manager.get_execution_state(session_id)

        # Check if should stop
        should_stop, reason = self.execution_guard.should_stop(exec_state, agent_name="MultiAgentOrchestrator")
        if should_stop:
            yield {
                "type": "error",
                "data": {"error": f"Execution stopped: {reason}"}
            }
            return

        try:
            # 1. Route query to specialist using AI or pattern matching
            if routing_mode == "ai" or routing_mode == "auto":
                yield {
                    "type": "status",
                    "data": "🧠 AI Router đang phân tích và chọn chuyên gia phù hợp..."
                }

                # Use AI-powered routing
                routing_decision = await self.specialist_router.route(user_query, user_id)
                specialist_name = routing_decision.specialist
                method_name = routing_decision.method
                params = routing_decision.extracted_params
                routing_confidence = routing_decision.confidence
                routing_reasoning = routing_decision.reasoning

            else:
                # Fallback to pattern matching
                yield {
                    "type": "status",
                    "data": "Đang phân tích yêu cầu..."
                }

                routing = self._classify_query(user_query, user_id)
                specialist_name = routing["specialist"]
                method_name = routing["method"]
                params = routing["params"]
                routing_confidence = 0.7
                routing_reasoning = "Pattern matching"

            # Track specialist usage
            self.query_metrics["specialist_usage"][specialist_name] += 1
            self.query_metrics["agent_mode_count"] += 1

            routing_time = time.time() - start_time
            self.query_metrics["ai_router_time"] += routing_time

            # Yield routing decision with AI insights
            yield {
                "type": "routing_decision",
                "data": {
                    "mode": "multi_agent",
                    "routing_method": routing_mode,
                    "specialist": specialist_name,
                    "method": method_name,
                    "confidence": routing_confidence,
                    "reasoning": routing_reasoning,
                    "routing_time": routing_time
                }
            }

            # Ensure user_query and user_id are in params
            if "user_query" not in params:
                params["user_query"] = user_query
            if "user_id" not in params:
                params["user_id"] = user_id

            # 2. Get specialist and execute
            specialist = self.specialists.get(specialist_name)
            if not specialist:
                yield {
                    "type": "error",
                    "data": {"error": f"Specialist {specialist_name} not found"}
                }
                return

            yield {
                "type": "status",
                "data": f"Dang su dung {specialist_name} de xu ly..."
            }

            # Send message to message bus
            msg = AgentMessage(
                type=MessageType.QUERY,
                from_agent="MultiAgentOrchestrator",
                to_agent=specialist_name,
                payload={"query": user_query, "params": params},
                priority=MessagePriority.NORMAL
            )
            message_bus.publish(msg)

            # Note: Resource limits are checked at tool call level, not agent level
            # The resource_monitor.check_can_call() is called when tools are invoked

            # Update execution state
            exec_state.iterations += 1

            # 3. Call specialist method
            # Method mapping for backwards compatibility
            method_mapping = {
                # ScreenerSpecialist
                ("ScreenerSpecialist", "get_top"): "screen",
                # AnalysisSpecialist
                ("AnalysisSpecialist", "get_price"): "analyze",
                ("AnalysisSpecialist", "predict"): "analyze",
                # AlertManager
                ("AlertManager", "list_alerts"): "get_alerts",
                # SubscriptionManager
                ("SubscriptionManager", "list_subscriptions"): "get_subscriptions",
            }

            # Apply method mapping if needed
            actual_method = method_mapping.get((specialist_name, method_name), method_name)

            # Get method from specialist
            if not hasattr(specialist, actual_method):
                # Fallback to default method for each specialist
                default_methods = {
                    "AnalysisSpecialist": "analyze",
                    "ScreenerSpecialist": "screen",
                    "AlertManager": "get_alerts",
                    "InvestmentPlanner": "create_investment_plan",
                    "DiscoverySpecialist": "discover",
                    "SubscriptionManager": "get_subscriptions",
                    "MarketContextSpecialist": "analyze",
                    "ComparisonSpecialist": "analyze",
                }
                actual_method = default_methods.get(specialist_name, method_name)

            method = getattr(specialist, actual_method)
            full_response = []
            tools_used = []

            # Filter params to match method signature
            import inspect
            sig = inspect.signature(method)
            valid_params = {}
            for param_name in sig.parameters:
                if param_name == 'self':
                    continue
                if param_name in params:
                    valid_params[param_name] = params[param_name]

            # Execute method with filtered params
            result = method(**valid_params)

            # Handle async iterator
            if hasattr(result, '__aiter__'):
                async for chunk in result:
                    full_response.append(chunk)
                    yield {
                        "type": "chunk",
                        "data": chunk
                    }
            # Handle coroutine
            elif hasattr(result, '__await__'):
                response = await result
                full_response.append(response)
                yield {
                    "type": "chunk",
                    "data": response
                }
            # Handle sync result
            else:
                full_response.append(str(result))
                yield {
                    "type": "chunk",
                    "data": str(result)
                }

            # 4. Store result in shared state
            shared_state = state_manager.get_shared_state(session_id)
            shared_state.set(
                f"response_{exec_state.iterations}",
                "".join(full_response),
                agent=specialist_name
            )

            # 5. Evaluate response quality (if critic agent is available)
            evaluation_score = 8  # Default score
            evaluation_passed = True
            if critic_agent is not None:
                try:
                    evaluation = critic_agent.evaluate(
                        user_query=user_query,
                        agent_response="".join(full_response),
                        context={"specialist": specialist_name, "method": method_name},
                        agent_name=specialist_name
                    )
                    evaluation_score = evaluation.score
                    evaluation_passed = evaluation.passed

                    # Add quality info if low score
                    if not evaluation.passed:
                        yield {
                            "type": "chunk",
                            "data": f"\n\n**Danh gia chat luong:** {evaluation.score}/10"
                        }
                except Exception:
                    pass  # Skip evaluation if it fails

            # 6. Update conversation memory
            memory = state_manager.get_memory(session_id)
            memory.add_message(session_id, "user", user_query)
            memory.add_message(session_id, "assistant", "".join(full_response))

            # 7. Send completion
            elapsed_time = time.time() - start_time

            yield {
                "type": "complete",
                "data": {
                    "elapsed_time": elapsed_time,
                    "mode_used": "multi_agent",
                    "specialist_used": specialist_name,
                    "method_used": method_name,
                    "quality_score": evaluation_score,
                    "response": "".join(full_response),
                    "tools_used": tools_used
                }
            }

        except Exception as e:
            yield {
                "type": "error",
                "data": {
                    "error": str(e),
                    "mode": "multi_agent"
                }
            }

    async def get_stock_info(self, symbol: str) -> Dict:
        """Quick helper for getting stock info"""
        result = await self.mcp_client.call_tool(
            "get_stock_data",
            {"symbols": [symbol], "lookback_days": 7}
        )
        return result

    async def analyze_stock(self, symbol: str, user_id: str = "system") -> AsyncIterator[str]:
        """Deep analysis using AnalysisSpecialist"""
        async for event in self.process_query(
            f"Phan tich chuyen sau co phieu {symbol}",
            user_id=user_id
        ):
            if event["type"] == "chunk":
                yield event["data"]

    def get_metrics(self) -> Dict:
        """Get comprehensive system metrics"""
        client_metrics = self.mcp_client.get_metrics()
        router_stats = self.specialist_router.get_stats()

        total_queries = self.query_metrics["agent_mode_count"]

        return {
            # Query metrics
            "total_queries": total_queries,
            "agent_mode_count": self.query_metrics["agent_mode_count"],
            "direct_mode_count": self.query_metrics["direct_mode_count"],
            "routing_mode": self.routing_mode,

            # Specialist usage
            "specialist_usage": self.query_metrics["specialist_usage"],

            # Average routing time
            "avg_routing_time": (
                self.query_metrics["ai_router_time"] / total_queries
                if total_queries > 0 else 0
            ),

            # MCP Client metrics
            **client_metrics,

            # AI Specialist Router stats
            "specialist_router_stats": router_stats,

            # Specialist stats
            "specialist_stats": {
                name: specialist.get_stats()
                for name, specialist in self.specialists.items()
                if hasattr(specialist, 'get_stats')
            }
        }

    def get_routing_analysis(self) -> Dict:
        """Analyze routing decisions"""
        return {
            "total_queries": self.query_metrics["agent_mode_count"],
            "specialist_usage": self.query_metrics["specialist_usage"],
            "most_used_specialist": max(
                self.query_metrics["specialist_usage"].items(),
                key=lambda x: x[1],
                default=("None", 0)
            )[0]
        }

    def clear_mcp_cache(self, pattern: Optional[str] = None):
        """Clear MCP client cache"""
        self.mcp_client.clear_cache(pattern)

    def clear_router_cache(self):
        """Clear AI Specialist Router decision cache"""
        self.specialist_router.clear_cache()

    def clear_session(self, session_id: str):
        """Clear session state"""
        state_manager.clear_session(session_id)

    def set_routing_mode(self, mode: str):
        """
        Change routing mode at runtime

        Args:
            mode: "ai", "pattern", or "auto"
        """
        if mode in ["ai", "pattern", "auto"]:
            self.routing_mode = mode

    async def cleanup(self):
        """Cleanup resources"""
        await self.mcp_client.disconnect()
