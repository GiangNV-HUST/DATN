"""
Analysis Specialist Agent

Specialized in stock analysis combining:
- Price data & technical indicators
- Fundamental analysis
- News & sentiment
- AI-powered insights

Based on OLD system's analysis_agent.py pattern.
"""

import os
import sys
from typing import Dict, List, Optional, AsyncIterator
from PIL import Image

# Add ai_agent_mcp to path for MCP client
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'ai_agent_mcp'))

import google.generativeai as genai


class AnalysisSpecialist:
    """
    Specialist for comprehensive stock analysis

    Tools (5):
    - get_stock_data: Price + indicators
    - get_stock_price_prediction: Future predictions
    - get_financial_data: Fundamentals
    - generate_chart_from_data: Visual analysis
    - gemini_search_and_summarize: News & sentiment

    Workflow:
    1. Gather data (price, financial, chart, news)
    2. Analyze with AI
    3. Generate comprehensive report
    """

    AGENT_INSTRUCTION = """
Bạn là chuyên gia phân tích cổ phiếu Việt Nam với khả năng:
- Phân tích kỹ thuật (RSI, MACD, MA, Volume, ...)
- Phân tích cơ bản (P/E, ROE, EPS, Revenue, ...)
- Phân tích tin tức và sentiment
- Dự đoán xu hướng giá

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## TOOLS CỦA BẠN (5 tools):

1. **get_stock_data(symbols, lookback_days)**
   - Lấy dữ liệu giá + indicators (MA5, MA10, MA20, RSI, MACD, Volume)
   - Ví dụ: get_stock_data(["VCB"], 30) → 30 ngày data

2. **get_stock_price_prediction(symbols, table_type)**
   - Dự đoán giá tương lai bằng ENSEMBLE 5-MODEL (PatchTST + LightGBM + LSTM + Prophet + XGBoost)
   - Độ chính xác cao: MAPE 0.8-1.2% (3 ngày), 2.5-3.5% (48 ngày)
   - table_type: "3d" (3 ngày) hoặc "48d" (48 ngày)
   - Trả về: predicted_price, confidence_lower, confidence_upper, change_percent

3. **get_financial_data(tickers, is_income_statement, is_balance_sheet, ...)**
   - Báo cáo tài chính (income, balance sheet, cash flow, ratios)
   - Ví dụ: get_financial_data(["VCB"], is_income_statement=True)

4. **generate_chart_from_data(symbols, lookback_days)**
   - Tạo biểu đồ nến + volume
   - CHÚ Ý: Phải gọi get_stock_data trước!

5. **gemini_search_and_summarize(query, use_search)**
   - Tìm kiếm tin tức và tóm tắt
   - Ví dụ: gemini_search_and_summarize("VCB tin tức mới nhất", True)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## WORKFLOW CHUẨN:

### 1. Phân tích GIÁ (Price Analysis):
```
User: "Phân tích giá VCB"

Step 1: get_stock_data(["VCB"], 30)
Step 2: get_stock_price_prediction(["VCB"], "3d")
Step 3: gemini_search_and_summarize("VCB tin tức", True)
Step 4: Tổng hợp phân tích
```

### 2. Phân tích TÀI CHÍNH (Fundamental Analysis):
```
User: "Phân tích tài chính VCB"

Step 1: get_financial_data(["VCB"], is_income_statement=True, is_balance_sheet=True)
Step 2: get_stock_data(["VCB"], 7) → Để có giá hiện tại
Step 3: gemini_search_and_summarize("VCB financial news", True)
Step 4: Tổng hợp phân tích
```

### 3. Phân tích TOÀN DIỆN (Full Analysis):
```
User: "Phân tích toàn diện VCB"

Step 1: get_stock_data(["VCB"], 30)
Step 2: get_financial_data(["VCB"], all=True)
Step 3: get_stock_price_prediction(["VCB"], "3d")
Step 4: gemini_search_and_summarize("VCB comprehensive analysis", True)
Step 5: Tổng hợp phân tích đầy đủ
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## OUTPUT FORMAT:

### Simple Price Query:
```
📊 **VCB - Phân tích giá**

**Giá hiện tại:** 94,000 VNĐ (+2.5%)

**Phân tích kỹ thuật:**
- RSI(14): 65 → Trung tính
- MACD: Tích cực (histogram > 0)
- MA20: Giá trên MA → Xu hướng tăng

**Tin tức:** [Từ search...]

💡 **Đánh giá:** NẮM GIỮ
```

### Full Analysis:
```
📊 **VCB - Phân tích toàn diện**

**1. Thông tin giá:**
- Giá: 94,000 VNĐ (+2.5%)
- Volume: 1.2M (cao hơn TB)
- RSI: 65, MACD: Tích cực

**2. Phân tích kỹ thuật:**
- Xu hướng: Tăng (giá trên MA20, MA50)
- Hỗ trợ: 92,000
- Kháng cự: 96,000

**3. Phân tích cơ bản:**
- P/E: 12.5 (hấp dẫn)
- ROE: 18% (tốt)
- EPS Growth: +15%
- Revenue: +10% YoY

**4. Dự báo:**
- T+1: 94,500 (+0.5%)
- T+3: 95,200 (+1.3%)

**5. Tin tức & Sentiment:**
[Từ search...]

💡 **Khuyến nghị:** MUA - Cổ phiếu có cơ bản tốt, kỹ thuật tích cực
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## LƯU Ý QUAN TRỌNG:

✅ DO:
- Luôn gọi get_stock_data trước khi analyze
- Kết hợp cả technical + fundamental nếu có thể
- Sử dụng tin tức để validate phân tích
- Đưa ra khuyến nghị rõ ràng (MUA/BÁN/NẮM GIỮ)

❌ DON'T:
- Đừng phân tích mà không có data
- Đừng gọi generate_chart nếu chưa có get_stock_data
- Đừng đưa ra khuyến nghị mà không có lý do
- Đừng bịa số liệu

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Hãy phân tích chuyên nghiệp và đưa ra insights có giá trị!
"""

    def __init__(self, mcp_client):
        """
        Initialize Analysis Specialist

        Args:
            mcp_client: EnhancedMCPClient instance
        """
        self.mcp_client = mcp_client
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        # Tool mapping
        self.tools = {
            "get_stock_data": self._wrap_tool("get_stock_data"),
            "get_stock_price_prediction": self._wrap_tool("get_stock_price_prediction"),
            "get_financial_data": self._wrap_tool("get_financial_data"),
            "generate_chart_from_data": self._wrap_tool("generate_chart_from_data"),
            "gemini_search_and_summarize": self._wrap_tool("gemini_search_and_summarize"),
        }

        # Statistics
        self.stats = {
            "total_analyses": 0,
            "price_analyses": 0,
            "fundamental_analyses": 0,
            "full_analyses": 0,
            "avg_tools_per_analysis": 0.0
        }

    def _wrap_tool(self, tool_name: str):
        """Wrap MCP tool for use with Gemini agent"""
        async def wrapped(**kwargs):
            result = await self.mcp_client.call_tool(tool_name, kwargs)
            return result
        return wrapped

    async def analyze(
        self,
        symbols: List[str],
        user_query: str,
        shared_state: Optional[Dict] = None,
        analysis_type: str = "auto"  # auto, price, fundamental, full
    ) -> AsyncIterator[str]:
        """
        Perform stock analysis

        Args:
            symbols: List of stock symbols
            user_query: User's analysis request
            shared_state: Shared state for storing intermediate results
            analysis_type: Type of analysis (auto/price/fundamental/full)

        Yields:
            Analysis chunks as they're generated
        """
        self.stats["total_analyses"] += 1

        # Determine analysis type if auto
        if analysis_type == "auto":
            analysis_type = self._determine_analysis_type(user_query)

        # Track which type
        if analysis_type == "price":
            self.stats["price_analyses"] += 1
        elif analysis_type == "fundamental":
            self.stats["fundamental_analyses"] += 1
        elif analysis_type == "full":
            self.stats["full_analyses"] += 1

        # Build analysis prompt
        prompt = self._build_analysis_prompt(symbols, user_query, analysis_type)

        # Create Gemini agent with MCP tools
        # Note: In real implementation, we'd use Google ADK Agent
        # For now, we'll simulate the workflow

        try:
            # Step 1: Get stock data
            stock_data = await self.mcp_client.call_tool(
                "get_stock_data",
                {"symbols": symbols, "lookback_days": 30}
            )

            if shared_state is not None:
                for symbol in symbols:
                    shared_state[f"stock_data_{symbol}"] = stock_data.get("results", {}).get(symbol)

            # Step 2: Get financial data if needed
            if analysis_type in ["fundamental", "full"]:
                financial_data = await self.mcp_client.call_tool(
                    "get_financial_data",
                    {
                        "tickers": symbols,
                        "is_income_statement": True,
                        "is_balance_sheet": True,
                        "is_ratio": True
                    }
                )

                if shared_state is not None:
                    for symbol in symbols:
                        shared_state[f"financial_data_{symbol}"] = financial_data.get("results", {}).get(symbol)

            # Step 3: Get price prediction
            if analysis_type in ["price", "full"]:
                prediction = await self.mcp_client.call_tool(
                    "get_stock_price_prediction",
                    {"symbols": symbols, "table_type": "3d"}
                )

                if shared_state is not None:
                    for symbol in symbols:
                        shared_state[f"prediction_{symbol}"] = prediction.get("results", {}).get(symbol)

            # Step 4: Search for news
            news_results = await self.mcp_client.call_tool(
                "gemini_search_and_summarize",
                {
                    "query": f"{' '.join(symbols)} tin tức mới nhất",
                    "use_search": True
                }
            )

            # Step 5: Generate comprehensive analysis with Gemini
            analysis_prompt = self._build_final_analysis_prompt(
                symbols,
                user_query,
                stock_data,
                financial_data if analysis_type in ["fundamental", "full"] else None,
                prediction if analysis_type in ["price", "full"] else None,
                news_results
            )

            response = self.client.models.generate_content(
                model='gemini-2.0-flash',
                contents=[analysis_prompt],
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=2048
                )
            )

            # Yield response
            yield response.text

        except Exception as e:
            yield f"❌ Lỗi khi phân tích: {str(e)}"

    def _determine_analysis_type(self, user_query: str) -> str:
        """Determine analysis type from query"""
        query_lower = user_query.lower()

        if any(kw in query_lower for kw in ["tài chính", "fundamental", "cơ bản", "báo cáo"]):
            return "fundamental"
        elif any(kw in query_lower for kw in ["toàn diện", "chi tiết", "đầy đủ", "comprehensive"]):
            return "full"
        else:
            return "price"

    def _build_analysis_prompt(
        self,
        symbols: List[str],
        user_query: str,
        analysis_type: str
    ) -> str:
        """Build initial analysis prompt"""
        return f"""
Hãy phân tích cổ phiếu {', '.join(symbols)} theo yêu cầu:

**User query:** {user_query}

**Loại phân tích:** {analysis_type}

Sử dụng các tools có sẵn để thu thập dữ liệu và phân tích.
"""

    def _build_final_analysis_prompt(
        self,
        symbols: List[str],
        user_query: str,
        stock_data: Dict,
        financial_data: Optional[Dict],
        prediction: Optional[Dict],
        news: Dict
    ) -> str:
        """Build final analysis prompt with all data"""
        prompt_parts = [
            f"Dựa trên dữ liệu sau, hãy phân tích cổ phiếu {', '.join(symbols)}:\n"
        ]

        # Add stock data
        prompt_parts.append(f"**Dữ liệu giá:** {stock_data}\n")

        # Add financial data if available
        if financial_data:
            prompt_parts.append(f"**Dữ liệu tài chính:** {financial_data}\n")

        # Add prediction if available
        if prediction:
            prompt_parts.append(f"**Dự báo giá:** {prediction}\n")

        # Add news
        prompt_parts.append(f"**Tin tức:** {news}\n")

        # Add user query
        prompt_parts.append(f"\n**Yêu cầu của user:** {user_query}\n")

        prompt_parts.append("""
Hãy tổng hợp và phân tích theo format:
1. Thông tin giá hiện tại
2. Phân tích kỹ thuật
3. Phân tích cơ bản (nếu có)
4. Tin tức và sentiment
5. Khuyến nghị rõ ràng (MUA/BÁN/NẮM GIỮ)
""")

        return "".join(prompt_parts)

    def get_stats(self) -> Dict:
        """Get analysis statistics"""
        return self.stats.copy()
