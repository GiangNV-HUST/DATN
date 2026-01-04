"""
Hybrid Orchestrator Agent - UPGRADED VERSION

Integrates:
1. State Management System (SharedState, ExecutionState)
2. Message Protocol (AgentMessage, MessageBus)
3. Specialized Agents (6 agents)
4. Evaluation Layer (CriticAgent, ArbitrationAgent)
5. Resource Monitoring (Tool quotas, cost limits)
6. Termination Guards (ExecutionGuard)

This is the MAIN ORCHESTRATOR that coordinates all specialized agents.
"""

import google.generativeai as genai
import os
from typing import Optional, AsyncIterator, Dict, List
from .mcp_tool_wrapper import create_mcp_tools_for_agent

# Import core infrastructure
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.message_protocol import (
    AgentMessage, MessageType, MessagePriority, message_bus
)
from core.state_management import state_manager
from core.termination import ExecutionGuard
from core.tool_allocation import resource_monitor
from core.evaluation import critic_agent, arbitration_agent

# Import specialized agents
from .analysis_specialist import AnalysisSpecialist
from .screener_specialist import ScreenerSpecialist
from .alert_manager import AlertManager
from .investment_planner import InvestmentPlanner
from .discovery_specialist import DiscoverySpecialist
from .subscription_manager import SubscriptionManager


class HybridOrchestrator:
    """
    Enhanced Orchestrator with multi-agent coordination

    Architecture:
    - Routes simple queries directly to appropriate specialist
    - Handles complex queries by coordinating multiple agents
    - Enforces resource limits and termination guards
    - Evaluates response quality
    - Maintains state and conversation context
    """

    AGENT_INSTRUCTION = """
Bạn là Orchestrator - điều phối viên thông minh cho hệ thống phân tích chứng khoán.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## VAI TRÒ CỦA BẠN:

Bạn KHÔNG trực tiếp xử lý queries. Thay vào đó, bạn **điều phối** các chuyên gia:

1. **AnalysisSpecialist** - Phân tích cổ phiếu (giá, kỹ thuật, cơ bản, tin tức)
2. **ScreenerSpecialist** - Sàng lọc cổ phiếu theo tiêu chí
3. **AlertManager** - Quản lý cảnh báo
4. **InvestmentPlanner** - Lập kế hoạch đầu tư
5. **DiscoverySpecialist** - Khám phá cổ phiếu tiềm năng
6. **SubscriptionManager** - Quản lý gói đăng ký

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## ROUTING LOGIC:

### 1. ANALYSIS queries → AnalysisSpecialist:
- "Phân tích VCB"
- "Giá VCB hiện tại?"
- "VCB có nên mua không?"
- "Báo cáo tài chính FPT"
- "So sánh VCB và ACB"

### 2. SCREENING queries → ScreenerSpecialist:
- "Tìm cổ phiếu ROE > 15%, PE < 15"
- "Cổ phiếu tốt để đầu tư dài hạn"
- "Top cổ phiếu ngân hàng"
- "Cổ phiếu có tăng trưởng cao"

### 3. ALERT queries → AlertManager:
- "Tạo cảnh báo VCB khi giá > 100,000"
- "Xem cảnh báo của tôi"
- "Xóa cảnh báo #123"

### 4. INVESTMENT PLANNING queries → InvestmentPlanner:
- "Tư vấn đầu tư 100 triệu"
- "Lập kế hoạch đầu tư dài hạn"
- "Phân bổ danh mục cho tôi"

### 5. DISCOVERY queries → DiscoverySpecialist:
- "Tìm cổ phiếu tốt trong ngành công nghệ"
- "Cổ phiếu nào đang được chuyên gia khuyến nghị?"
- "Khám phá cổ phiếu mới"

### 6. SUBSCRIPTION queries → SubscriptionManager:
- "Đăng ký gói premium"
- "Xem gói đăng ký của tôi"
- "Hủy gói đăng ký"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## COMPLEX QUERIES (cần nhiều agents):

### Example 1: "Tư vấn đầu tư 50 triệu vào ngành ngân hàng"
```
1. ScreenerSpecialist: Lọc cổ phiếu ngân hàng tốt
2. AnalysisSpecialist: Phân tích từng cổ phiếu
3. InvestmentPlanner: Lập kế hoạch với 50 triệu
```

### Example 2: "Phân tích và tạo cảnh báo cho VCB"
```
1. AnalysisSpecialist: Phân tích VCB
2. AlertManager: Tạo cảnh báo dựa trên phân tích
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## OUTPUT FORMAT:

Bạn chỉ cần trả lời:
1. Agent nào sẽ xử lý
2. (Nếu complex) Workflow gồm những bước nào

Ví dụ:
```
User: "Phân tích VCB"
You: {
    "agent": "AnalysisSpecialist",
    "symbols": ["VCB"],
    "query": "Phân tích VCB"
}
```

```
User: "Tư vấn đầu tư 100 triệu vào ngành công nghệ"
You: {
    "workflow": [
        {"agent": "ScreenerSpecialist", "query": "Lọc cổ phiếu công nghệ tốt"},
        {"agent": "AnalysisSpecialist", "symbols": ["results_from_step1"]},
        {"agent": "InvestmentPlanner", "capital": 100000000}
    ]
}
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Hãy phân loại và route query một cách thông minh!
"""

    def __init__(self, mcp_client):
        """
        Initialize Hybrid Orchestrator

        Args:
            mcp_client: EnhancedMCPClient instance
        """
        self.mcp_client = mcp_client
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        # Initialize specialized agents
        self.agents = {
            "AnalysisSpecialist": AnalysisSpecialist(mcp_client),
            "ScreenerSpecialist": ScreenerSpecialist(mcp_client),
            "AlertManager": AlertManager(mcp_client),
            "InvestmentPlanner": InvestmentPlanner(mcp_client),
            "DiscoverySpecialist": DiscoverySpecialist(mcp_client),
            "SubscriptionManager": SubscriptionManager(mcp_client),
        }

        # Execution guard
        self.execution_guard = ExecutionGuard()

        # Statistics
        self.stats = {
            "total_queries": 0,
            "simple_queries": 0,
            "complex_queries": 0,
            "agent_usage": {name: 0 for name in self.agents.keys()},
            "avg_response_time": 0.0
        }

        print(f"✅ Hybrid Orchestrator initialized with {len(self.agents)} specialized agents")

    def _classify_query(self, user_query: str, user_id: str) -> Dict:
        """
        Classify query and determine routing

        Args:
            user_query: User's query
            user_id: User ID

        Returns:
            Dict with routing information
        """
        query_lower = user_query.lower()

        # Simple keyword-based routing (can be enhanced with AI)

        # ANALYSIS
        if any(kw in query_lower for kw in ["phân tích", "giá", "analyze", "báo cáo tài chính", "so sánh"]):
            return {
                "type": "simple",
                "agent": "AnalysisSpecialist",
                "method": "analyze",
                "params": {
                    "symbols": self._extract_symbols(user_query),
                    "user_query": user_query
                }
            }

        # SCREENING
        if any(kw in query_lower for kw in ["tìm", "lọc", "sàng lọc", "screen", "top", "cổ phiếu tốt"]):
            return {
                "type": "simple",
                "agent": "ScreenerSpecialist",
                "method": "screen",
                "params": {
                    "user_query": user_query
                }
            }

        # ALERTS
        if any(kw in query_lower for kw in ["cảnh báo", "alert", "thông báo"]):
            if "tạo" in query_lower or "create" in query_lower:
                return {
                    "type": "simple",
                    "agent": "AlertManager",
                    "method": "create_alert",
                    "params": self._parse_alert_params(user_query, user_id)
                }
            elif "xem" in query_lower or "list" in query_lower:
                return {
                    "type": "simple",
                    "agent": "AlertManager",
                    "method": "get_alerts",
                    "params": {"user_id": user_id}
                }
            else:
                return {
                    "type": "simple",
                    "agent": "AlertManager",
                    "method": "get_alerts",
                    "params": {"user_id": user_id}
                }

        # INVESTMENT PLANNING
        if any(kw in query_lower for kw in ["đầu tư", "investment", "tư vấn", "kế hoạch", "phân bổ"]):
            return {
                "type": "simple",
                "agent": "InvestmentPlanner",
                "method": "create_investment_plan",
                "params": self._parse_investment_params(user_query, user_id)
            }

        # DISCOVERY
        if any(kw in query_lower for kw in ["khám phá", "discover", "tiềm năng", "khuyến nghị"]):
            return {
                "type": "simple",
                "agent": "DiscoverySpecialist",
                "method": "discover",
                "params": {
                    "user_query": user_query
                }
            }

        # SUBSCRIPTION
        if any(kw in query_lower for kw in ["đăng ký", "subscription", "gói", "premium"]):
            if "xem" in query_lower:
                return {
                    "type": "simple",
                    "agent": "SubscriptionManager",
                    "method": "get_subscriptions",
                    "params": {"user_id": user_id}
                }
            else:
                return {
                    "type": "simple",
                    "agent": "SubscriptionManager",
                    "method": "create_subscription",
                    "params": self._parse_subscription_params(user_query, user_id)
                }

        # Default: Analysis
        return {
            "type": "simple",
            "agent": "AnalysisSpecialist",
            "method": "analyze",
            "params": {
                "symbols": self._extract_symbols(user_query),
                "user_query": user_query
            }
        }

    def _extract_symbols(self, query: str) -> List[str]:
        """Extract stock symbols from query"""
        # Simple regex for Vietnamese stock symbols (3-4 uppercase letters)
        import re
        matches = re.findall(r'\b[A-Z]{3,4}\b', query)

        # Common Vietnamese stocks
        common = ["VCB", "FPT", "HPG", "VIC", "VNM", "ACB", "MSN", "TCB", "VHM", "VPB"]

        symbols = []
        for match in matches:
            if match in common or len(match) == 3:
                symbols.append(match)

        return symbols if symbols else []

    def _parse_alert_params(self, query: str, user_id: str) -> Dict:
        """Parse alert creation parameters"""
        symbols = self._extract_symbols(query)

        return {
            "user_id": user_id,
            "symbol": symbols[0] if symbols else "VCB",
            "alert_type": "price",
            "condition": ">",
            "target_value": None  # Would need better parsing
        }

    def _parse_investment_params(self, query: str, user_id: str) -> Dict:
        """Parse investment planning parameters"""
        # Extract capital (numbers in millions/billions)
        import re

        capital = 100_000_000  # Default 100M

        # Try to find numbers
        numbers = re.findall(r'(\d+)\s*(triệu|tr|tỷ|ty)', query.lower())
        if numbers:
            amount, unit = numbers[0]
            amount = int(amount)
            if unit in ["triệu", "tr"]:
                capital = amount * 1_000_000
            elif unit in ["tỷ", "ty"]:
                capital = amount * 1_000_000_000

        # Risk tolerance
        risk = "medium"
        if any(kw in query.lower() for kw in ["an toàn", "thấp", "bảo thủ"]):
            risk = "low"
        elif any(kw in query.lower() for kw in ["cao", "mạo hiểm", "tích cực"]):
            risk = "high"

        # Time horizon
        horizon = "medium"
        if any(kw in query.lower() for kw in ["ngắn hạn", "short"]):
            horizon = "short"
        elif any(kw in query.lower() for kw in ["dài hạn", "long"]):
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
        session_id: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        Process user query with multi-agent orchestration

        Args:
            user_query: User's question
            user_id: User ID
            session_id: Session ID for conversation tracking

        Yields:
            Response chunks as they arrive
        """
        session_id = session_id or user_id
        self.stats["total_queries"] += 1

        # Create session if not exists
        if not state_manager.session_exists(session_id):
            state_manager.create_session(session_id, user_id, f"User {user_id}")

        # Get execution state
        exec_state = state_manager.get_execution_state(session_id)

        # Get shared state
        shared_state = state_manager.get_shared_state(session_id)

        # Check if should stop
        should_stop, reason = self.execution_guard.should_stop(exec_state, agent_name="Orchestrator")
        if should_stop:
            yield f"⚠️ Execution stopped: {reason}"
            return

        try:
            # Classify query
            routing = self._classify_query(user_query, user_id)

            agent_name = routing["agent"]
            method_name = routing["method"]
            params = routing["params"]

            self.stats["agent_usage"][agent_name] += 1

            # Get agent
            agent = self.agents[agent_name]

            # Get method
            method = getattr(agent, method_name)

            # Send message to message bus
            msg = AgentMessage(
                type=MessageType.QUERY,
                from_agent="Orchestrator",
                to_agent=agent_name,
                payload={"query": user_query, "params": params},
                priority=MessagePriority.NORMAL
            )
            message_bus.publish(msg)

            # Check resource limits
            can_proceed, limit_reason = resource_monitor.check_can_proceed(
                session_id=session_id,
                agent_name=agent_name
            )

            if not can_proceed:
                yield f"⚠️ Resource limit reached: {limit_reason}"
                return

            # Update execution state
            exec_state.iterations += 1

            # Call agent method
            full_response = []

            # If method is async generator
            if hasattr(method, '__call__'):
                result = method(**params)

                # If it's an async iterator
                if hasattr(result, '__aiter__'):
                    async for chunk in result:
                        full_response.append(chunk)
                        yield chunk
                # If it's a coroutine
                elif hasattr(result, '__await__'):
                    response = await result
                    full_response.append(response)
                    yield response
                # If it's synchronous
                else:
                    full_response.append(str(result))
                    yield str(result)

            # Store result in shared state
            shared_state.set(
                f"response_{exec_state.iterations}",
                "".join(full_response),
                agent=agent_name
            )

            # Evaluate response quality
            evaluation = critic_agent.evaluate(
                user_query=user_query,
                agent_response="".join(full_response),
                context={"agent": agent_name, "method": method_name},
                agent_name=agent_name
            )

            # If failed evaluation
            if not evaluation.passed:
                yield f"\n\n⚠️ **Quality Check:** Score {evaluation.score}/10 - {evaluation.action}"

                if evaluation.action == "RETRY" and exec_state.iterations < 3:
                    yield f"\n🔄 Retrying with improvements..."
                    # Could implement retry logic here

            # Update conversation memory
            memory = state_manager.get_conversation_memory(session_id)
            memory.add_message("user", user_query)
            memory.add_message("assistant", "".join(full_response))

        except Exception as e:
            error_msg = f"❌ Orchestrator error: {str(e)}"
            yield error_msg

            # Record error
            exec_state.errors.append(str(e))

    def get_stats(self) -> Dict:
        """Get orchestrator statistics"""
        stats = self.stats.copy()

        # Add agent stats
        stats["agent_stats"] = {}
        for name, agent in self.agents.items():
            if hasattr(agent, 'get_stats'):
                stats["agent_stats"][name] = agent.get_stats()

        return stats

    def clear_session(self, session_id: str):
        """Clear session state"""
        state_manager.clear_session(session_id)
