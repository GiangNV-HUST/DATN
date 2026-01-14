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
from ..core.error_recovery import (
    retry_async, RetryConfig, FallbackChain,
    error_recovery_manager, RETRY_CONFIGS
)
from ..core.task_context import (
    TaskContext, WorkflowContext, TaskContextBuilder,
    DataTypes, create_task_context
)

# Import AI-Powered Specialist Router for intelligent routing
from .specialist_router import SpecialistRouter, MultiAgentRoutingDecision, AgentTask


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
            # Check if this is a specific DCA query for a single stock
            symbols = self._extract_symbols(user_query)
            is_dca_query = "dca" in query_lower or any(kw in query_lower for kw in [
                "mỗi tháng", "moi thang", "hàng tháng", "hang thang",
                "định kỳ", "dinh ky", "/tháng", "/thang", "tích lũy", "tich luy"
            ])

            if is_dca_query and len(symbols) == 1:
                # Single stock DCA plan
                return {
                    "type": "simple",
                    "specialist": "InvestmentPlanner",
                    "method": "create_dca_plan",
                    "params": self._parse_dca_params(user_query, symbols[0])
                }
            else:
                # General investment plan
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

        # Vietnamese words to exclude (commonly misidentified as symbols)
        exclude = {"KHI", "NEN", "CAI", "NAO", "XEM", "MUA", "BAN", "GIA", "HON", "TOT",
                   "HAY", "ROI", "SAU", "CHO", "VAN", "THE", "NAY", "TAO", "TEN", "MOT",
                   "HAI", "BAO", "VON", "LOC", "TOP", "HOT", "TAT", "MAT", "DAU", "TRI",
                   "DCA", "VOI", "MOI", "LAP", "KHO", "TUY", "TAN", "DEN", "SAN", "CAN",
                   "CHI", "GOI", "THI", "TUC", "VAY", "COT", "CAO", "KEO", "DUA", "NUA"}

        symbols = []
        for match in matches:
            if match in exclude:
                continue
            if match in common or len(match) == 3:
                symbols.append(match)

        return list(set(symbols)) if symbols else []

    def _extract_capital(self, query: str) -> float:
        """Extract capital amount from query"""
        import re

        capital = 100_000_000  # Default 100M VND

        # Try to find numbers with units (Vietnamese)
        # Pattern: 100 triệu, 1.5 tỷ, 500tr, etc.
        patterns = [
            (r'(\d+(?:[.,]\d+)?)\s*(tỷ|ty)', 1_000_000_000),
            (r'(\d+(?:[.,]\d+)?)\s*(triệu|trieu|tr)', 1_000_000),
            (r'(\d+(?:[.,]\d+)?)\s*m(?:illion)?', 1_000_000),  # English million
            (r'(\d+(?:[.,]\d+)?)\s*b(?:illion)?', 1_000_000_000),  # English billion
        ]

        query_lower = query.lower()
        for pattern, multiplier in patterns:
            match = re.search(pattern, query_lower)
            if match:
                amount_str = match.group(1).replace(",", ".")
                try:
                    amount = float(amount_str)
                    capital = int(amount * multiplier)
                    break
                except ValueError:
                    continue

        return capital

    def _parse_alert_params(self, query: str, user_id: str) -> Dict:
        """Parse alert creation parameters from query"""
        import re

        symbols = self._extract_symbols(query)
        query_lower = query.lower()

        # Determine condition type (API expects "above"/"below")
        condition = "above"  # default
        if any(kw in query_lower for kw in ["dưới", "duoi", "thấp hơn", "thap hon", "giảm", "giam", "<"]):
            condition = "below"
        elif any(kw in query_lower for kw in ["trên", "tren", "vượt", "vuot", "cao hơn", "cao hon", "tăng", "tang", ">"]):
            condition = "above"

        # Extract target value (price)
        # Patterns: "80000", "80,000", "80.000", "80k", "80 nghìn"
        target_value = None
        patterns = [
            r'(\d{1,3}(?:[.,]\d{3})+)',  # 80,000 or 80.000
            r'(\d+)\s*k\b',  # 80k
            r'(\d+)\s*(?:nghìn|nghin)',  # 80 nghìn
            r'(?:>|<|vượt|vuot|dưới|duoi|trên|tren)\s*(\d+)',  # > 80000
            r'(\d{4,6})\b',  # 80000 (4-6 digits)
        ]

        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                value_str = match.group(1).replace(",", "").replace(".", "")
                try:
                    target_value = float(value_str)
                    # If pattern was "k" or "nghìn", multiply by 1000
                    if "k" in pattern or "nghìn" in pattern or "nghin" in pattern:
                        target_value *= 1000
                    break
                except ValueError:
                    continue

        # Determine alert type
        alert_type = "price"  # default
        if any(kw in query_lower for kw in ["rsi", "macd", "ma", "indicator", "chỉ báo", "chi bao"]):
            alert_type = "indicator"
        elif any(kw in query_lower for kw in ["volume", "khối lượng", "khoi luong"]):
            alert_type = "volume"

        return {
            "user_id": user_id,
            "symbol": symbols[0] if symbols else "VCB",
            "alert_type": alert_type,
            "condition": condition,
            "target_value": target_value
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

    def _parse_dca_params(self, query: str, symbol: str) -> Dict:
        """Parse DCA plan parameters from query"""
        import re

        monthly_investment = 5_000_000  # Default 5M/month
        duration_months = 12  # Default 12 months

        query_lower = query.lower()

        # Extract monthly investment amount
        # Patterns: "5 triệu/tháng", "5tr mỗi tháng", "5 triệu moi thang"
        monthly_patterns = [
            r'(\d+(?:[.,]\d+)?)\s*(triệu|trieu|tr)(?:\s*/?\s*(?:tháng|thang|month))?',
            r'(\d+(?:[.,]\d+)?)\s*m(?:illion)?(?:\s*/?\s*(?:tháng|thang|month))?',
        ]

        for pattern in monthly_patterns:
            match = re.search(pattern, query_lower)
            if match:
                amount = float(match.group(1).replace(",", "."))
                if "m" in pattern:
                    monthly_investment = int(amount * 1_000_000)
                else:
                    monthly_investment = int(amount * 1_000_000)
                break

        # Extract duration (months)
        # Patterns: "12 tháng", "1 năm", "6 months"
        duration_patterns = [
            (r'(\d+)\s*(?:tháng|thang|month)', 1),
            (r'(\d+)\s*(?:năm|nam|year)', 12),
        ]

        for pattern, multiplier in duration_patterns:
            match = re.search(pattern, query_lower)
            if match:
                duration_months = int(match.group(1)) * multiplier
                break

        # Determine price trend
        price_trend = "neutral"
        if any(kw in query_lower for kw in ["tăng", "tang", "bullish", "lạc quan", "lac quan"]):
            price_trend = "bullish"
        elif any(kw in query_lower for kw in ["giảm", "giam", "bearish", "bi quan", "thận trọng", "than trong"]):
            price_trend = "bearish"

        return {
            "symbol": symbol.upper(),
            "monthly_investment": monthly_investment,
            "duration_months": duration_months,
            "price_trend": price_trend
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

    async def _execute_single_task(
        self,
        task: AgentTask,
        session_id: str,
        user_id: str,
        shared_state,
        previous_results: Dict[str, str] = None
    ) -> AsyncIterator[Dict]:
        """
        Execute a single agent task

        Args:
            task: The task to execute
            session_id: Session ID
            user_id: User ID
            shared_state: Shared state for storing results
            previous_results: Results from previous tasks (for sequential execution)

        Yields:
            Dict with execution events
        """
        specialist_name = task.specialist
        method_name = task.method
        params = task.params.copy()

        # Ensure user_id is in params
        if "user_id" not in params:
            params["user_id"] = user_id

        # Extract symbols from user_query if not provided
        if "symbols" not in params and "user_query" in params:
            extracted_symbols = self._extract_symbols(params["user_query"])
            if extracted_symbols:
                params["symbols"] = extracted_symbols

        # Extract capital from user_query for InvestmentPlanner
        if specialist_name == "InvestmentPlanner" and "capital" not in params:
            if "user_query" in params:
                extracted_capital = self._extract_capital(params["user_query"])
                params["capital"] = extracted_capital

        # For sequential tasks, inject previous results into context
        if previous_results and task.depends_on:
            # Handle both single and list depends_on
            depends_list = task.depends_on if isinstance(task.depends_on, list) else [task.depends_on]
            prev_results_text = []
            for dep_id in depends_list:
                prev_result = previous_results.get(dep_id, "")
                if prev_result:
                    prev_results_text.append(prev_result[:1500])

            if prev_results_text:
                combined_prev = "\n\n---\n\n".join(prev_results_text)
                # Add previous result to params for context
                params["previous_context"] = combined_prev
                # Also update user_query to include context
                if "user_query" in params:
                    params["user_query"] = f"{params['user_query']}\n\n[Ket qua tu buoc truoc]:\n{combined_prev}"

        # Get specialist
        specialist = self.specialists.get(specialist_name)
        if not specialist:
            yield {
                "type": "error",
                "data": {"error": f"Specialist {specialist_name} not found"}
            }
            return

        # Method mapping for backwards compatibility
        method_mapping = {
            ("ScreenerSpecialist", "get_top"): "screen",
            ("AnalysisSpecialist", "get_price"): "analyze",
            ("AnalysisSpecialist", "predict"): "analyze",
            ("AlertManager", "list_alerts"): "get_alerts",
            ("SubscriptionManager", "list_subscriptions"): "get_subscriptions",
        }

        actual_method = method_mapping.get((specialist_name, method_name), method_name)

        # Get method from specialist
        if not hasattr(specialist, actual_method):
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

        # Filter params to match method signature
        import inspect
        sig = inspect.signature(method)
        valid_params = {}
        for param_name in sig.parameters:
            if param_name == 'self':
                continue
            if param_name in params:
                valid_params[param_name] = params[param_name]

        # Build task context for structured data passing
        task_context = TaskContextBuilder() \
            .task_id(task.task_id) \
            .specialist(specialist_name) \
            .query(params.get("user_query", ""), task.method) \
            .symbols(params.get("symbols", [])) \
            .build()

        # Add previous results to task context
        if previous_results:
            for prev_id, prev_result in previous_results.items():
                task_context.add_previous_result(prev_id, prev_result)

        # Store task context in shared state
        shared_state.set(f"task_context_{task.task_id}", task_context.to_dict(), agent=specialist_name)

        # Execute method with error recovery
        retry_count = 0
        max_retries = 2
        last_error = None

        while retry_count <= max_retries:
            try:
                result = method(**valid_params)

                # Handle async iterator
                if hasattr(result, '__aiter__'):
                    async for chunk in result:
                        # Ensure chunk is string
                        chunk_str = chunk if isinstance(chunk, str) else str(chunk)
                        full_response.append(chunk_str)
                        yield {
                            "type": "chunk",
                            "data": chunk_str,
                            "task_id": task.task_id,
                            "specialist": specialist_name
                        }
                    break  # Success, exit retry loop
                # Handle coroutine
                elif hasattr(result, '__await__'):
                    response = await result
                    # Ensure response is string
                    response_str = response if isinstance(response, str) else str(response)
                    full_response.append(response_str)
                    yield {
                        "type": "chunk",
                        "data": response_str,
                        "task_id": task.task_id,
                        "specialist": specialist_name
                    }
                    break  # Success, exit retry loop
                # Handle sync result
                else:
                    full_response.append(str(result))
                    yield {
                        "type": "chunk",
                        "data": str(result),
                        "task_id": task.task_id,
                        "specialist": specialist_name
                    }
                    break  # Success, exit retry loop

            except Exception as e:
                last_error = e
                retry_count += 1
                error_recovery_manager.record_error(
                    source=specialist_name,
                    error=e,
                    context={"task_id": task.task_id, "method": method_name}
                )

                if retry_count <= max_retries:
                    # Wait before retry (exponential backoff)
                    import asyncio
                    delay = 1.0 * (2 ** (retry_count - 1))
                    yield {
                        "type": "status",
                        "data": f"[Retry {retry_count}/{max_retries}] {specialist_name} gap loi, thu lai sau {delay:.1f}s..."
                    }
                    await asyncio.sleep(delay)
                else:
                    # All retries failed, yield error but continue
                    yield {
                        "type": "error",
                        "data": {
                            "task_id": task.task_id,
                            "specialist": specialist_name,
                            "error": str(last_error),
                            "retries": retry_count - 1
                        }
                    }
                    full_response.append(f"[Loi] {specialist_name}: {str(last_error)[:200]}")

        # Record success if no error
        if not last_error or retry_count <= max_retries:
            error_recovery_manager.record_success(specialist_name)

        # Store result in shared state - ensure all items are strings
        result_text = "".join(str(item) for item in full_response)
        shared_state.set(f"task_result_{task.task_id}", result_text, agent=specialist_name)

        # Register data in task context for subsequent agents
        if result_text:
            # Determine data type based on specialist
            data_type_map = {
                "AnalysisSpecialist": DataTypes.PRICE_DATA,
                "ScreenerSpecialist": DataTypes.SCREENING_RESULTS,
                "MarketContextSpecialist": DataTypes.MARKET_INDEX,
                "ComparisonSpecialist": DataTypes.COMPARISON_MATRIX,
                "InvestmentPlanner": DataTypes.INVESTMENT_PLAN,
                "DiscoverySpecialist": DataTypes.PRICE_DATA,
            }
            data_type = data_type_map.get(specialist_name, "result")
            task_context.add_available_data(
                key=f"task_result_{task.task_id}",
                source_agent=specialist_name,
                data_type=data_type,
                symbols=params.get("symbols", [])
            )

        yield {
            "type": "task_complete",
            "data": {
                "task_id": task.task_id,
                "specialist": specialist_name,
                "result": result_text
            }
        }

    async def _execute_multi_agent_workflow(
        self,
        routing_decision: MultiAgentRoutingDecision,
        user_query: str,
        user_id: str,
        session_id: str
    ) -> AsyncIterator[Dict]:
        """
        Execute multi-agent workflow based on routing decision

        Supports:
        - Sequential execution: Agent A -> Agent B
        - Parallel execution: Agent A & Agent B simultaneously
        - Result aggregation

        Args:
            routing_decision: Multi-agent routing decision
            user_query: Original user query
            user_id: User ID
            session_id: Session ID

        Yields:
            Dict with execution events
        """
        import asyncio

        shared_state = state_manager.get_shared_state(session_id)
        tasks = routing_decision.tasks
        execution_mode = routing_decision.execution_mode
        aggregation_strategy = routing_decision.aggregation_strategy

        all_results: Dict[str, str] = {}
        all_responses: List[str] = []

        if execution_mode == "single" or (execution_mode == "sequential" and len(tasks) == 1):
            # Single task execution
            task = tasks[0]
            task_response = []
            async for event in self._execute_single_task(
                task, session_id, user_id, shared_state, {}
            ):
                if event["type"] == "chunk":
                    chunk_data = event["data"]
                    if isinstance(chunk_data, str):
                        task_response.append(chunk_data)
                    else:
                        task_response.append(str(chunk_data))
                yield event

            result_text = "".join(task_response)
            all_results[task.task_id] = result_text
            all_responses.append(result_text)
            self.query_metrics["specialist_usage"][task.specialist] += 1

        elif execution_mode == "sequential":
            # Execute tasks one by one, passing results to next task
            for i, task in enumerate(tasks):
                yield {
                    "type": "status",
                    "data": f"Buoc {i+1}/{len(tasks)}: Dang su dung {task.specialist}..."
                }

                # Execute task with previous results
                task_response = []
                async for event in self._execute_single_task(
                    task, session_id, user_id, shared_state, all_results
                ):
                    if event["type"] == "chunk":
                        # Ensure data is string
                        chunk_data = event["data"]
                        if isinstance(chunk_data, str):
                            task_response.append(chunk_data)
                        elif isinstance(chunk_data, dict):
                            task_response.append(str(chunk_data))
                        else:
                            task_response.append(str(chunk_data))
                    yield event

                # Store result for next task
                result_text = "".join(task_response)
                all_results[task.task_id] = result_text
                all_responses.append(f"\n\n## {task.specialist}\n{result_text}")

                # Track specialist usage
                self.query_metrics["specialist_usage"][task.specialist] += 1

        elif execution_mode == "parallel":
            # Execute all tasks concurrently with streaming
            yield {
                "type": "status",
                "data": f"Dang chay {len(tasks)} agents song song..."
            }

            # Use asyncio.Queue for streaming results as they come
            result_queue = asyncio.Queue()
            completed_tasks = set()

            async def run_task_streaming(task):
                """Run task and put results in queue as they arrive"""
                responses = []
                try:
                    async for event in self._execute_single_task(
                        task, session_id, user_id, shared_state, {}
                    ):
                        if event["type"] == "chunk":
                            chunk_data = event["data"]
                            chunk_str = chunk_data if isinstance(chunk_data, str) else str(chunk_data)
                            responses.append(chunk_str)
                            # Stream chunk immediately
                            await result_queue.put(("chunk", task.task_id, task.specialist, chunk_str))

                    # Signal task completion
                    final_response = "".join(responses)
                    await result_queue.put(("complete", task.task_id, task.specialist, final_response))
                except Exception as e:
                    await result_queue.put(("error", task.task_id, task.specialist, str(e)))

            # Start all tasks
            task_futures = [asyncio.create_task(run_task_streaming(task)) for task in tasks]

            # Stream results as they arrive
            task_responses = {task.task_id: [] for task in tasks}

            while len(completed_tasks) < len(tasks):
                try:
                    result = await asyncio.wait_for(result_queue.get(), timeout=120.0)
                    event_type, task_id, specialist, data = result

                    if event_type == "chunk":
                        task_responses[task_id].append(data)
                        # Yield chunk immediately for real-time streaming
                        yield {
                            "type": "chunk",
                            "data": data,
                            "task_id": task_id,
                            "specialist": specialist
                        }

                    elif event_type == "complete":
                        completed_tasks.add(task_id)
                        final_response = "".join(task_responses[task_id])
                        all_results[task_id] = final_response
                        all_responses.append(f"\n\n## {specialist}\n{final_response}")
                        self.query_metrics["specialist_usage"][specialist] += 1

                        yield {
                            "type": "task_complete",
                            "data": {
                                "task_id": task_id,
                                "specialist": specialist,
                                "result": final_response
                            }
                        }

                    elif event_type == "error":
                        completed_tasks.add(task_id)
                        yield {
                            "type": "error",
                            "data": {"error": data, "task_id": task_id, "specialist": specialist}
                        }

                except asyncio.TimeoutError:
                    break

            # Wait for all tasks to complete
            await asyncio.gather(*task_futures, return_exceptions=True)

        # Aggregate results based on strategy
        if aggregation_strategy == "concatenate":
            # Simply concatenate all responses
            final_response = "".join(all_responses)
        elif aggregation_strategy == "summarize":
            # Add a summary header
            final_response = f"## Tong hop tu {len(tasks)} chuyen gia:\n" + "".join(all_responses)
        else:  # merge
            final_response = "".join(all_responses)

        yield {
            "type": "aggregation_complete",
            "data": {
                "strategy": aggregation_strategy,
                "num_tasks": len(tasks),
                "final_response": final_response
            }
        }

    async def process_query(
        self,
        user_query: str,
        user_id: str,
        mode: Optional[Literal["auto", "ai", "pattern"]] = None,
        session_id: Optional[str] = None,
        enable_multi_agent: bool = True,
        **kwargs
    ) -> AsyncIterator[Dict]:
        """
        Process user query with multi-agent orchestration

        Args:
            user_query: User's question
            user_id: User ID
            mode: Routing mode - "ai" (AI Router), "pattern" (keyword matching), "auto" (default from init)
            session_id: Session ID for conversation tracking
            enable_multi_agent: If True, use multi-agent routing (default True)
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
            # 1. Route query - use multi-agent routing if enabled
            if enable_multi_agent and (routing_mode == "ai" or routing_mode == "auto"):
                yield {
                    "type": "status",
                    "data": "AI Router dang phan tich va chon chuyen gia phu hop..."
                }

                # Use multi-agent routing
                multi_routing = await self.specialist_router.route_multi_agent(user_query, user_id)

                routing_time = time.time() - start_time
                self.query_metrics["ai_router_time"] += routing_time

                # Yield routing decision
                yield {
                    "type": "routing_decision",
                    "data": {
                        "mode": "multi_agent",
                        "routing_method": routing_mode,
                        "is_multi_agent": multi_routing.is_multi_agent,
                        "execution_mode": multi_routing.execution_mode,
                        "tasks": [
                            {"specialist": t.specialist, "method": t.method, "depends_on": t.depends_on}
                            for t in multi_routing.tasks
                        ],
                        "confidence": multi_routing.confidence,
                        "reasoning": multi_routing.reasoning,
                        "routing_time": routing_time
                    }
                }

                # 2. Execute based on routing decision
                if multi_routing.is_multi_agent:
                    # Multi-agent workflow
                    yield {
                        "type": "status",
                        "data": f"Se su dung {len(multi_routing.tasks)} agents ({multi_routing.execution_mode})..."
                    }

                    full_response = []
                    async for event in self._execute_multi_agent_workflow(
                        multi_routing, user_query, user_id, session_id
                    ):
                        if event["type"] == "chunk":
                            full_response.append(event["data"])
                        yield event

                    # Update execution state
                    exec_state.iterations += len(multi_routing.tasks)
                    self.query_metrics["agent_mode_count"] += len(multi_routing.tasks)

                    # Store final result
                    shared_state = state_manager.get_shared_state(session_id)
                    final_response = "".join(full_response)
                    shared_state.set(f"response_{exec_state.iterations}", final_response, agent="MultiAgent")

                    # Update conversation memory
                    memory = state_manager.get_memory(session_id)
                    memory.add_message(session_id, "user", user_query)
                    memory.add_message(session_id, "assistant", final_response)

                    # Send completion
                    elapsed_time = time.time() - start_time
                    yield {
                        "type": "complete",
                        "data": {
                            "elapsed_time": elapsed_time,
                            "mode_used": "multi_agent",
                            "execution_mode": multi_routing.execution_mode,
                            "specialists_used": [t.specialist for t in multi_routing.tasks],
                            "num_agents": len(multi_routing.tasks),
                            "response": final_response
                        }
                    }
                    return

                else:
                    # Single agent - convert to single decision and continue
                    routing_decision = multi_routing.to_single_decision()
                    specialist_name = routing_decision.specialist
                    method_name = routing_decision.method
                    params = routing_decision.extracted_params
                    routing_confidence = routing_decision.confidence
                    routing_reasoning = routing_decision.reasoning
                    # Skip yielding routing_decision again since we already yielded above
                    # Jump directly to specialist execution
                    self.query_metrics["specialist_usage"][specialist_name] += 1
                    self.query_metrics["agent_mode_count"] += 1

                    # Continue to specialist execution (skip the second routing_decision yield)
                    # We need to jump to line after the routing_decision yield
                    # So we'll use a flag or restructure the code
                    # For now, let's inline the execution here

                    # Ensure user_query and user_id are in params
                    if "user_query" not in params:
                        params["user_query"] = user_query
                    if "user_id" not in params:
                        params["user_id"] = user_id

                    # Extract symbols from user_query if not provided
                    if "symbols" not in params:
                        extracted_symbols = self._extract_symbols(user_query)
                        if extracted_symbols:
                            params["symbols"] = extracted_symbols

                    # Extract alert params for AlertManager
                    if specialist_name == "AlertManager":
                        # Detect create_alert intent even if AI chose wrong method
                        query_lower = user_query.lower()
                        if any(kw in query_lower for kw in ["tạo", "tao", "create", "đặt", "dat", "alert", "cảnh báo khi", "canh bao khi"]) and \
                           any(kw in query_lower for kw in ["vượt", "vuot", ">", "<", "trên", "tren", "dưới", "duoi"]):
                            method_name = "create_alert"  # Override to correct method

                        if method_name == "create_alert":
                            alert_params = self._parse_alert_params(user_query, user_id)
                            params.update(alert_params)

                    # Get specialist and execute
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

                    # Execute specialist
                    exec_state.iterations += 1

                    # Method mapping
                    method_mapping = {
                        ("ScreenerSpecialist", "get_top"): "screen",
                        ("AnalysisSpecialist", "get_price"): "analyze",
                        ("AnalysisSpecialist", "predict"): "analyze",
                        ("AlertManager", "list_alerts"): "get_alerts",
                        ("SubscriptionManager", "list_subscriptions"): "get_subscriptions",
                    }

                    actual_method = method_mapping.get((specialist_name, method_name), method_name)

                    if not hasattr(specialist, actual_method):
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

                    # Filter params to match method signature
                    import inspect
                    sig = inspect.signature(method)
                    valid_params = {}
                    for param_name in sig.parameters:
                        if param_name == 'self':
                            continue
                        if param_name in params:
                            valid_params[param_name] = params[param_name]

                    result = method(**valid_params)

                    if hasattr(result, '__aiter__'):
                        async for chunk in result:
                            chunk_str = chunk if isinstance(chunk, str) else str(chunk)
                            full_response.append(chunk_str)
                            yield {"type": "chunk", "data": chunk_str}
                    elif hasattr(result, '__await__'):
                        response = await result
                        response_str = response if isinstance(response, str) else str(response)
                        full_response.append(response_str)
                        yield {"type": "chunk", "data": response_str}
                    else:
                        full_response.append(str(result))
                        yield {"type": "chunk", "data": str(result)}

                    # Store result and complete
                    shared_state = state_manager.get_shared_state(session_id)
                    shared_state.set(f"response_{exec_state.iterations}", "".join(full_response), agent=specialist_name)

                    memory = state_manager.get_memory(session_id)
                    memory.add_message(session_id, "user", user_query)
                    memory.add_message(session_id, "assistant", "".join(full_response))

                    elapsed_time = time.time() - start_time
                    yield {
                        "type": "complete",
                        "data": {
                            "elapsed_time": elapsed_time,
                            "mode_used": "multi_agent",
                            "specialist_used": specialist_name,
                            "method_used": method_name,
                            "response": "".join(full_response)
                        }
                    }
                    return  # Exit after single-agent execution from multi-agent routing

            elif routing_mode == "ai" or routing_mode == "auto":
                yield {
                    "type": "status",
                    "data": "AI Router dang phan tich va chon chuyen gia phu hop..."
                }

                # Use single-agent AI routing
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
                    "data": "Dang phan tich yeu cau..."
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

            # Extract symbols from user_query if not provided
            if "symbols" not in params:
                extracted_symbols = self._extract_symbols(user_query)
                if extracted_symbols:
                    params["symbols"] = extracted_symbols

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
                    # Ensure chunk is string
                    chunk_str = chunk if isinstance(chunk, str) else str(chunk)
                    full_response.append(chunk_str)
                    yield {
                        "type": "chunk",
                        "data": chunk_str
                    }
            # Handle coroutine
            elif hasattr(result, '__await__'):
                response = await result
                # Ensure response is string
                response_str = response if isinstance(response, str) else str(response)
                full_response.append(response_str)
                yield {
                    "type": "chunk",
                    "data": response_str
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
