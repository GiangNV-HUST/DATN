"""
Orchestrator Agent - High-Level Agent with Reasoning Capabilities

From OLD Multi-Agent system:
- Autonomous reasoning
- Dynamic tool selection
- Conversation memory

From NEW MCP system:
- Access to 25 MCP tools
- Stateless design

Hybrid:
- Single agent replaces multiple specialized agents
- Has ALL tools, decides which to use
- Adaptive workflows
"""

import google.generativeai as genai
import os
from typing import Optional, AsyncIterator, Dict
from .mcp_tool_wrapper import create_mcp_tools_for_agent


class OrchestratorAgent:
    """
    High-level orchestrator agent with autonomous reasoning

    Capabilities:
    - Access to ALL 25 MCP tools
    - Intelligent tool selection
    - Multi-step reasoning
    - Conversation context
    - Adaptive workflows
    """

    def __init__(self, mcp_client):
        """
        Initialize Orchestrator Agent

        Args:
            mcp_client: EnhancedMCPClient instance
        """
        self.mcp_client = mcp_client
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        # Conversation history per session
        self.conversation_history = {}

        # Wrapped MCP tools for agent
        self.mcp_tools = create_mcp_tools_for_agent(
            mcp_client=mcp_client,
            tool_names="all"  # ALL 25 tools
        )

        # Create the agent
        self.agent = self._create_agent()

        print(f"✅ Orchestrator Agent created with {len(self.mcp_tools)} tools")

    def _create_agent(self):
        """
        Create Gemini agent with all MCP tools

        This is the heart of the AGENT MODE
        """

        instruction = """
Bạn là chuyên gia phân tích chứng khoán Việt Nam với quyền truy cập vào 25 công cụ chuyên nghiệp.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## NHIỆM VỤ CỦA BẠN:

1. **Phân tích yêu cầu** của user một cách thông minh
2. **Lập kế hoạch** sử dụng tools phù hợp
3. **Thực thi tools** theo thứ tự hợp lý (có thể song song nếu được)
4. **Phân tích kết quả** và đưa ra insights
5. **Trả lời** bằng tiếng Việt chuyên nghiệp, dễ hiểu

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## CÔNG CỤ CỦA BẠN (25 tools):

### 📊 Stock Data Tools (4):
- **get_stock_data**: Lấy giá + indicators (MA5, MA10, MA20, RSI, MACD, volume, ...)
- **get_stock_price_prediction**: Dự đoán giá 3 ngày/48 ngày
- **generate_chart_from_data**: Tạo biểu đồ nến
- **get_stock_details_from_tcbs**: 70+ trường dữ liệu chi tiết từ TCBS

### 🔔 Alert & Subscription Tools (6):
- **create_alert**: Tạo cảnh báo giá/chỉ số
- **get_user_alerts**: Xem danh sách cảnh báo
- **delete_alert**: Xóa cảnh báo
- **create_subscription**: Đăng ký theo dõi cổ phiếu
- **get_user_subscriptions**: Xem danh sách theo dõi
- **delete_subscription**: Hủy theo dõi

### 🤖 AI Tools (3):
- **gemini_summarize**: Tóm tắt dữ liệu với AI, có thể dùng Google Search
- **gemini_search_and_summarize**: Tìm kiếm web + tóm tắt
- **batch_summarize**: Tóm tắt hàng loạt (SONG SONG, NHANH HƠN nhiều lần!)

### 💰 Investment Planning Tools (5):
- **gather_investment_profile**: Thu thập hồ sơ đầu tư (mục tiêu, rủi ro, vốn, ...)
- **calculate_portfolio_allocation**: Tính phân bổ danh mục
- **generate_entry_strategy**: Chiến lược vào lệnh
- **generate_risk_management_plan**: Kế hoạch quản lý rủi ro
- **generate_monitoring_plan**: Kế hoạch giám sát

### 🔍 Stock Discovery Tools (4):
- **discover_stocks_by_profile**: Tìm cổ phiếu phù hợp với profile
- **search_potential_stocks**: Tìm kiếm cổ phiếu tiềm năng
- **filter_stocks_by_criteria**: Lọc theo tiêu chí (PE, ROE, market cap, ...)
- **rank_stocks_by_score**: Xếp hạng theo điểm số

### 📈 Financial & Screener Tools (3):
- **get_financial_data**: Báo cáo tài chính (balance sheet, income, cash flow, ratios)
- **screen_stocks**: Sàng lọc 80+ tiêu chí
- **get_screener_columns**: Xem các tiêu chí có thể lọc

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## CHIẾN LƯỢC SỬ DỤNG TOOLS:

### 1. Cho queries đơn giản (giá, thông tin cơ bản):
```
User: "Giá VCB?"
→ Gọi get_stock_data(symbols=["VCB"], lookback_days=1)
→ Trả lời ngắn gọn
```

### 2. Cho phân tích cơ bản (1 cổ phiếu):
```
User: "Phân tích VCB"
→ get_stock_data(["VCB"], lookback_days=30) - Giá + indicators
→ get_financial_data(["VCB"], is_income_statement=True) - Tài chính
→ gemini_search_and_summarize(query="VCB news", ...) - Tin tức
→ Tổng hợp và phân tích
```

### 3. Cho so sánh nhiều cổ phiếu:
```
User: "So sánh VCB, FPT, HPG"
→ get_stock_data(["VCB", "FPT", "HPG"]) - 1 CALL CHO TẤT CẢ!
→ batch_summarize({
    "VCB": {"data": ..., "query": "So sánh với FPT, HPG"},
    "FPT": {"data": ..., "query": "So sánh với VCB, HPG"},
    "HPG": {"data": ..., "query": "So sánh với VCB, FPT"}
  }) - SONG SONG!
→ So sánh và kết luận
```

### 4. Cho investment planning (đầu tư):
```
User: "Tư vấn đầu tư 100 triệu vào cổ phiếu ngân hàng"
→ gather_investment_profile(capital=100000000, ...)
→ screen_stocks(conditions={"sector": "banking", ...})
→ get_stock_data(top_stocks)
→ calculate_portfolio_allocation(stocks, capital)
→ generate_entry_strategy(stocks)
→ generate_risk_management_plan(stocks)
→ generate_monitoring_plan(stocks)
→ Tạo báo cáo đầu tư đầy đủ
```

### 5. Cho stock screening (tìm cổ phiếu):
```
User: "Tìm cổ phiếu ROE > 15%, PE < 15"
→ screen_stocks(conditions={"roe": ">15", "pe": "<15"})
→ get_stock_data(top_results)
→ rank_stocks_by_score(stocks, ranking_method="composite")
→ Giới thiệu top picks với lý do
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## LƯU Ý QUAN TRỌNG:

### ✅ DO:
1. **Batch operations**: Dùng batch_summarize thay vì nhiều lần gemini_summarize
2. **List parameters**: Gọi get_stock_data([VCB, FPT, HPG]) thay vì 3 lần riêng
3. **Adaptive**: Nếu kết quả thiếu data, tự động gọi thêm tools
4. **Context-aware**: Sử dụng kết quả tool trước để quyết định tool sau
5. **Concise**: Ngắn gọn cho simple queries, chi tiết cho complex analysis

### ❌ DON'T:
1. Đừng gọi gemini_summarize nhiều lần → Dùng batch_summarize
2. Đừng gọi get_stock_data riêng lẻ → Dùng list symbols
3. Đừng fetch tất cả data nếu user chỉ hỏi giá
4. Đừng dùng financial data tools nếu không cần
5. Đừng quá dài dòng

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## RESPONSE FORMAT:

### Simple queries (giá, thông tin cơ bản):
```
📊 VCB: 94,000 VNĐ (+2.5%)
Khối lượng: 1,250,000
```

### Analysis queries:
```
📊 **Phân tích VCB**

**1. Thông tin giá:**
- Giá: 94,000 VNĐ (+2.5%)
- RSI: 65 (trung tính)
- MACD: Tích cực

**2. Phân tích kỹ thuật:**
- Xu hướng: Tăng
- Hỗ trợ: 92,000
- Kháng cự: 96,000

**3. Phân tích cơ bản:**
- P/E: 12.5 (hấp dẫn)
- ROE: 18% (tốt)

**4. Tin tức:**
[Từ search...]

💡 **Khuyến nghị:** NẮM GIỮ
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Hãy phân tích user query và thực thi tools một cách thông minh!
"""

        # Create Gemini agent with wrapped MCP tools
        agent = self.client.agents.create(
            model="gemini-2.5-flash-preview-04-17",
            name="orchestrator_agent",
            description="High-level orchestrator with reasoning capabilities",
            instruction=instruction,
            tools=self.mcp_tools,  # All 25 wrapped tools
            config=types.AgentConfig(
                temperature=0.7,
                top_p=0.95,
                max_output_tokens=4096,
            )
        )

        return agent

    async def process_query(
        self,
        user_query: str,
        user_id: str,
        session_id: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        Process user query with agent reasoning

        Args:
            user_query: User's question
            user_id: User ID
            session_id: Session ID for conversation tracking

        Yields:
            Response chunks as they arrive
        """
        session_id = session_id or user_id

        # Get conversation history
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []

        history = self.conversation_history[session_id]

        # Run agent
        from google.adk.runners import Runner

        runner = Runner(
            app_name="Orchestrator Agent",
            agent=self.agent
        )

        full_response = []

        try:
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=types.Content(
                    role="user",
                    parts=[types.Part(text=user_query)]
                )
            ):
                if event.content and event.content.parts:
                    text = event.content.parts[0].text
                    full_response.append(text)
                    yield text

            # Update history
            history.append({
                "role": "user",
                "content": user_query
            })
            history.append({
                "role": "assistant",
                "content": "".join(full_response)
            })

            # Keep only last 10 exchanges
            if len(history) > 20:
                self.conversation_history[session_id] = history[-20:]

        except Exception as e:
            error_msg = f"❌ Agent error: {str(e)}"
            yield error_msg

    def clear_history(self, session_id: str):
        """Clear conversation history for session"""
        if session_id in self.conversation_history:
            del self.conversation_history[session_id]

    def get_history(self, session_id: str) -> list:
        """Get conversation history for session"""
        return self.conversation_history.get(session_id, [])

    def get_tool_stats(self) -> Dict:
        """Get statistics for all wrapped tools"""
        from .mcp_tool_wrapper import get_tool_stats
        return get_tool_stats(self.mcp_tools)
