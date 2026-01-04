"""
AI-Powered Router using ROOT_AGENT concept from OLD Multi-Agent System

This router uses Gemini AI to intelligently decide:
- Which mode to use (agent vs direct)
- Which tools to suggest
- Confidence and complexity scores

Replaces rule-based routing with intelligent decision making.
"""

import google.generativeai as genai
import json
import os
import re
from typing import Literal
from dataclasses import dataclass, asdict
import asyncio


@dataclass
class AIRoutingDecision:
    """Decision from AI Router"""
    mode: Literal["agent", "direct"]
    suggested_tools: list[str]
    reasoning: str
    confidence: float
    complexity: float
    estimated_time: float


class AIRouter:
    """
    AI-Powered Router using Gemini Agent

    Concept from OLD Multi-Agent System:
    - ROOT_AGENT intelligent routing
    - AI-powered decision making
    - Adaptive based on query analysis

    Differences from OLD:
    - Routes to MODES (not sub-agents)
    - Structured JSON output
    - Dual-mode decision (agent vs direct)
    """

    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.root_agent = self._create_root_agent()

        # Cache routing decisions for identical queries
        self.decision_cache = {}

        # Stats
        self.stats = {
            "total_routings": 0,
            "agent_mode_decisions": 0,
            "direct_mode_decisions": 0,
            "cache_hits": 0,
        }

    def _create_root_agent(self):
        """
        Create ROOT_AGENT with AI routing capability

        Similar to ROOT_AGENT in OLD system, but:
        - Routes to modes (not agents)
        - Returns structured decision
        - Optimized for dual-mode selection
        """

        instruction = """
Bạn là ROOT_AGENT - Bộ điều phối thông minh cho hệ thống phân tích chứng khoán.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## NHIỆM VỤ CỦA BẠN:

Phân tích user query và quyết định **EXECUTION MODE** phù hợp nhất:

### 🎯 HAI MODES:

**1. DIRECT MODE** (Nhanh, đơn giản):
   - Sử dụng cho: Queries đơn giản, rõ ràng, 1-2 tool calls
   - Ưu điểm: Sub-second response, không overhead
   - Nhược điểm: Không có reasoning, chỉ execute tools

   Ví dụ queries cho DIRECT MODE:
   - "Giá VCB?"
   - "Biểu đồ FPT 30 ngày"
   - "Cảnh báo của tôi"
   - "Đăng ký theo dõi HPG"
   - "Xóa alert số 5"
   - "Danh sách cổ phiếu theo dõi"

**2. AGENT MODE** (Thông minh, phức tạp):
   - Sử dụng cho: Queries cần reasoning, nhiều bước, phân tích
   - Ưu điểm: Autonomous decision, adaptive workflow
   - Nhược điểm: Chậm hơn (3-10s), tốn AI cost

   Ví dụ queries cho AGENT MODE:
   - "Phân tích VCB"
   - "So sánh VCB với FPT"
   - "Tìm cổ phiếu tốt để đầu tư 100 triệu"
   - "Tư vấn danh mục đầu tư cho người mới"
   - "Giải thích tại sao VCB tăng giá?"
   - "Nên mua VCB hay FPT?"
   - "Cổ phiếu nào có ROE > 15%?"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## CÁC TOOLS KHẢ DỤNG (25 tools):

### 📊 Stock Data Tools (4):
- get_stock_data: Lấy giá + indicators (MA, RSI, MACD, ...)
- get_stock_price_prediction: Dự đoán giá 3d/48d
- generate_chart_from_data: Tạo biểu đồ nến
- get_stock_details_from_tcbs: 70+ trường dữ liệu chi tiết

### 🔔 Alert & Subscription Tools (6):
- create_alert, get_user_alerts, delete_alert
- create_subscription, get_user_subscriptions, delete_subscription

### 🤖 AI Tools (3):
- gemini_summarize: Tóm tắt dữ liệu
- gemini_search_and_summarize: Search web + tóm tắt
- batch_summarize: Tóm tắt nhiều symbols (song song)

### 💰 Investment Planning Tools (5):
- gather_investment_profile
- calculate_portfolio_allocation
- generate_entry_strategy
- generate_risk_management_plan
- generate_monitoring_plan

### 🔍 Stock Discovery Tools (4):
- discover_stocks_by_profile
- search_potential_stocks
- filter_stocks_by_criteria
- rank_stocks_by_score

### 📈 Financial & Screener Tools (3):
- get_financial_data: Báo cáo tài chính
- screen_stocks: Lọc cổ phiếu (80+ tiêu chí)
- get_screener_columns: Xem các cột có thể lọc

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## DECISION CRITERIA:

### Chọn DIRECT MODE nếu:
✅ Query có thể giải quyết bằng 1-2 tool calls
✅ Không cần reasoning hay giải thích
✅ Mục tiêu rõ ràng, không mơ hồ
✅ Không cần so sánh hay phân tích sâu
✅ User muốn câu trả lời nhanh
✅ CRUD operations (create, read, update, delete)

### Chọn AGENT MODE nếu:
✅ Cần nhiều bước (multi-step reasoning)
✅ Cần so sánh, đánh giá, phân tích
✅ Mục tiêu không rõ ràng, cần clarification
✅ Cần search thông tin bổ sung
✅ Cần tư vấn, gợi ý, khuyến nghị
✅ Query có từ: "phân tích", "so sánh", "tại sao", "nên", "tốt nhất", "tìm", "gợi ý"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## OUTPUT FORMAT:

Trả về JSON với cấu trúc SAU ĐÂY VÀ KHÔNG THÊM TEXT NÀO KHÁC:

{
  "mode": "direct" hoặc "agent",
  "suggested_tools": ["tool1", "tool2"],
  "reasoning": "Giải thích ngắn gọn tại sao chọn mode này",
  "confidence": 0.95,
  "complexity": 0.3,
  "estimated_time": 1.5
}

**CHÚ THÍCH:**
- mode: "direct" hoặc "agent"
- suggested_tools: Danh sách tools (CHỈ cho DIRECT MODE, AGENT MODE để [])
- reasoning: Giải thích quyết định (1-2 câu)
- confidence: Mức độ tự tin (0.0-1.0)
- complexity: Độ phức tạp query (0.0=đơn giản, 1.0=rất phức tạp)
- estimated_time: Thời gian dự kiến (giây)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## EXAMPLES:

User: "Giá VCB?"
{
  "mode": "direct",
  "suggested_tools": ["get_stock_data"],
  "reasoning": "Query đơn giản chỉ hỏi giá, 1 tool call là đủ",
  "confidence": 0.98,
  "complexity": 0.1,
  "estimated_time": 1.0
}

User: "Phân tích VCB và so sánh với FPT"
{
  "mode": "agent",
  "suggested_tools": [],
  "reasoning": "Cần phân tích chuyên sâu và so sánh 2 cổ phiếu, đòi hỏi reasoning và tổng hợp nhiều nguồn dữ liệu",
  "confidence": 0.95,
  "complexity": 0.8,
  "estimated_time": 6.0
}

User: "Tìm cổ phiếu ngân hàng tốt để đầu tư"
{
  "mode": "agent",
  "suggested_tools": [],
  "reasoning": "Cần research, screening, và đánh giá nhiều cổ phiếu. Đòi hỏi multi-step reasoning và gợi ý",
  "confidence": 0.92,
  "complexity": 0.9,
  "estimated_time": 10.0
}

User: "Tạo cảnh báo VCB trên 100000"
{
  "mode": "direct",
  "suggested_tools": ["create_alert"],
  "reasoning": "CRUD operation đơn giản, không cần reasoning",
  "confidence": 0.99,
  "complexity": 0.2,
  "estimated_time": 1.0
}

User: "Cảnh báo của tôi"
{
  "mode": "direct",
  "suggested_tools": ["get_user_alerts"],
  "reasoning": "Query thông tin đơn giản, 1 tool call",
  "confidence": 0.99,
  "complexity": 0.1,
  "estimated_time": 0.5
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## QUAN TRỌNG:

1. **Ưu tiên DIRECT MODE** khi có thể → Faster, cheaper
2. **Chỉ dùng AGENT MODE** khi thực sự cần reasoning
3. **Trả về VALID JSON**, KHÔNG thêm text khác
4. **Confidence > 0.9** nếu chắc chắn
5. **Complexity > 0.6** → Xem xét AGENT MODE

PHÂN TÍCH USER QUERY VÀ TRẢ VỀ JSON:
"""

        # Create agent without tools (just reasoning)
        agent = self.client.agents.create(
            model="gemini-2.5-flash-preview-04-17",
            name="root_agent_router",
            description="AI-powered routing agent",
            instruction=instruction,
            config=types.AgentConfig(
                temperature=0.3,  # Low temperature for consistent routing
                top_p=0.9,
            )
        )

        return agent

    async def analyze(self, user_query: str, use_cache: bool = True) -> AIRoutingDecision:
        """
        Analyze user query using AI and return routing decision

        Args:
            user_query: User's question
            use_cache: Whether to use cached decisions

        Returns:
            AIRoutingDecision with mode, tools, reasoning, etc.
        """
        # Check cache
        if use_cache and user_query in self.decision_cache:
            self.stats["cache_hits"] += 1
            return self.decision_cache[user_query]

        self.stats["total_routings"] += 1

        # Run ROOT_AGENT
        from google.adk.runners import Runner

        runner = Runner(
            app_name="AI Router",
            agent=self.root_agent
        )

        full_response = []

        try:
            async for event in runner.run_async(
                user_id="system",
                session_id=f"routing_{self.stats['total_routings']}",
                new_message=types.Content(
                    role="user",
                    parts=[types.Part(text=user_query)]
                )
            ):
                if event.content and event.content.parts:
                    text = event.content.parts[0].text
                    full_response.append(text)

            response_text = "".join(full_response)

            # Parse JSON response
            decision = self._parse_decision(response_text)

            # Update stats
            if decision.mode == "agent":
                self.stats["agent_mode_decisions"] += 1
            else:
                self.stats["direct_mode_decisions"] += 1

            # Cache decision
            if use_cache:
                self.decision_cache[user_query] = decision

            return decision

        except Exception as e:
            print(f"⚠️ AI Router error: {e}")
            # Fallback to safe default
            return self._get_fallback_decision(user_query, str(e))

    def _parse_decision(self, response_text: str) -> AIRoutingDecision:
        """Parse AI response into AIRoutingDecision"""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
            if json_match:
                decision_dict = json.loads(json_match.group())
            else:
                decision_dict = json.loads(response_text)

            return AIRoutingDecision(
                mode=decision_dict["mode"],
                suggested_tools=decision_dict.get("suggested_tools", []),
                reasoning=decision_dict.get("reasoning", ""),
                confidence=float(decision_dict.get("confidence", 0.8)),
                complexity=float(decision_dict.get("complexity", 0.5)),
                estimated_time=float(decision_dict.get("estimated_time", 2.0))
            )

        except Exception as e:
            raise ValueError(f"Failed to parse AI decision: {e}\nResponse: {response_text}")

    def _get_fallback_decision(self, query: str, error: str) -> AIRoutingDecision:
        """Fallback decision if AI router fails"""
        # Simple heuristics as fallback
        query_lower = query.lower()

        # Check for simple patterns
        simple_patterns = [
            r'^giá\s+\w+\?*$',
            r'^(cảnh báo|alert|đăng ký|subscription).*của tôi',
            r'^(tạo|xóa|delete)\s+(cảnh báo|alert)',
        ]

        for pattern in simple_patterns:
            if re.search(pattern, query_lower):
                return AIRoutingDecision(
                    mode="direct",
                    suggested_tools=[],
                    reasoning=f"Fallback: Simple pattern matched. AI error: {error}",
                    confidence=0.6,
                    complexity=0.3,
                    estimated_time=1.5
                )

        # Default to agent mode if uncertain
        return AIRoutingDecision(
            mode="agent",
            suggested_tools=[],
            reasoning=f"Fallback: Defaulting to agent mode for safety. AI error: {error}",
            confidence=0.5,
            complexity=0.7,
            estimated_time=5.0
        )

    def get_stats(self) -> dict:
        """Get routing statistics"""
        total = self.stats["total_routings"]
        return {
            **self.stats,
            "cache_hit_rate": (
                f"{self.stats['cache_hits'] / total * 100:.1f}%"
                if total > 0 else "0%"
            ),
            "agent_mode_rate": (
                f"{self.stats['agent_mode_decisions'] / total * 100:.1f}%"
                if total > 0 else "0%"
            ),
        }

    def clear_cache(self):
        """Clear decision cache"""
        self.decision_cache.clear()
