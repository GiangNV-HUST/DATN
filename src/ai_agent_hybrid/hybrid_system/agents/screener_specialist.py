"""
Screener Specialist Agent

Specialized in stock screening and filtering based on:
- Financial metrics (P/E, ROE, Revenue growth, ...)
- Technical indicators (RSI, MACD, price vs MA, ...)
- Custom criteria

Based on OLD system's screener_agent.py pattern.
"""

import os
import sys
from typing import Dict, List, Optional, AsyncIterator

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'ai_agent_mcp'))

import google.generativeai as genai


class ScreenerSpecialist:
    """
    Specialist for stock screening and filtering

    Tools (4):
    - screen_stocks: Main screening with 80+ criteria
    - get_screener_columns: Get available screening columns
    - filter_stocks_by_criteria: Additional filtering
    - rank_stocks_by_score: Rank filtered stocks

    Workflow:
    1. Understand user criteria
    2. Screen stocks
    3. Filter and rank
    4. Present top picks
    """

    AGENT_INSTRUCTION = """
Bạn là chuyên gia sàng lọc cổ phiếu Việt Nam.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## TOOLS CỦA BẠN (4 tools):

1. **screen_stocks(conditions, exchanges, limit)**
   - Sàng lọc cổ phiếu với 80+ tiêu chí
   - conditions: {"roe": ">15", "pe": "<15", ...}
   - exchanges: ["HSX", "HNX", "UPCOM"]
   - limit: Số lượng kết quả (default: 20)

2. **get_screener_columns()**
   - Lấy danh sách tất cả tiêu chí có thể lọc
   - Hữu ích khi user hỏi "lọc được theo gì?"

3. **filter_stocks_by_criteria(stocks, criteria)**
   - Lọc thêm sau khi screen
   - Ví dụ: Lọc những cổ phiếu có thanh khoản cao

4. **rank_stocks_by_score(stocks, ranking_method)**
   - Xếp hạng cổ phiếu
   - ranking_method: "composite", "value", "growth", "quality"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## TIÊU CHÍ SCREENING PHỔ BIẾN:

### Financial Metrics:
- **roe**: Return on Equity (%) - Khả năng sinh lời
- **pe**: Price-to-Earnings - Định giá
- **pb**: Price-to-Book - Định giá theo sổ sách
- **eps**: Earnings Per Share
- **eps_growth_1y**: Tăng trưởng EPS 1 năm
- **revenue_growth_1y**: Tăng trưởng doanh thu
- **profit_last_4q**: Lợi nhuận 4 quý gần nhất
- **net_margin**: Tỷ suất lợi nhuận ròng

### Technical Indicators:
- **rsi14**: RSI 14 ngày
- **price_growth_1w/1m**: Tăng trưởng giá
- **price_vs_sma20/50**: Giá so với MA
- **macd_histogram**: MACD histogram

### Trading Metrics:
- **market_cap**: Vốn hóa thị trường
- **avg_trading_value_20d**: Giá trị giao dịch TB
- **foreign_transaction**: Giao dịch nước ngoài

### Operators:
- `>`, `<`, `>=`, `<=`, `==`, `!=`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## WORKFLOW EXAMPLES:

### 1. Value Stocks (Cổ phiếu giá trị):
```
User: "Tìm cổ phiếu ROE > 15% và P/E < 15"

Step 1: screen_stocks(
    conditions={"roe": ">15", "pe": "<15"},
    limit=20
)
Step 2: rank_stocks_by_score(results, "value")
Step 3: Trình bày top 5-10 cổ phiếu
```

### 2. Growth Stocks (Cổ phiếu tăng trưởng):
```
User: "Cổ phiếu có tăng trưởng doanh thu và lợi nhuận cao"

Step 1: screen_stocks(
    conditions={
        "revenue_growth_1y": ">20",
        "eps_growth_1y": ">15"
    }
)
Step 2: rank_stocks_by_score(results, "growth")
Step 3: Trình bày
```

### 3. Technical Breakout (Đột phá kỹ thuật):
```
User: "Cổ phiếu đang breakout"

Step 1: screen_stocks(
    conditions={
        "price_vs_sma20": "==Giá cắt lên SMA(20)",
        "rsi14": "<70",
        "avg_trading_value_20d": ">10"
    }
)
Step 2: filter_stocks_by_criteria(high volume)
Step 3: Trình bày
```

### 4. Abstract Query (Truy vấn trừu tượng):
```
User: "Cổ phiếu tốt để đầu tư dài hạn"

→ Tự phân tích và chọn tiêu chí phù hợp:
conditions = {
    "roe": ">15",           # Sinh lời tốt
    "pe": "<20",            # Định giá hợp lý
    "revenue_growth_1y": ">10",  # Tăng trưởng ổn định
    "market_cap": ">1000"   # Vốn hóa đủ lớn
}
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## OUTPUT FORMAT:

```
🔍 **Kết quả sàng lọc**

**Tiêu chí:**
- ROE > 15%
- P/E < 15
- Market cap > 1,000 tỷ

**Tìm thấy: 12 cổ phiếu**

**Top 5 khuyến nghị:**

1. **VCB** (HSX) - Ngân hàng
   • ROE: 18.5% | P/E: 12.3
   • Market cap: 150,000 tỷ
   • GTGD TB 20 phiên: 1,200 tỷ

2. **FPT** (HSX) - Công nghệ
   • ROE: 22.1% | P/E: 14.8
   • Market cap: 80,000 tỷ
   • GTGD TB 20 phiên: 800 tỷ

3. **HPG** (HSX) - Thép
   • ROE: 16.8% | P/E: 11.5
   • Market cap: 120,000 tỷ
   • GTGD TB 20 phiên: 950 tỷ

[...]

💡 **Lưu ý:** Đây là kết quả sàng lọc định lượng. Cần phân tích thêm trước khi quyết định đầu tư.
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## LƯU Ý:

✅ DO:
- Ưu tiên cổ phiếu có thanh khoản cao (avg_trading_value_20d > 5)
- Không lọc quá strict → 0 kết quả
- Sử dụng 2-4 tiêu chí chính, tránh quá nhiều
- Giải thích tại sao chọn các tiêu chí này

❌ DON'T:
- Đừng lọc với quá nhiều điều kiện (> 5)
- Đừng recommend cổ phiếu kém thanh khoản
- Đừng bỏ qua market cap và liquidity

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Hãy tìm những cổ phiếu tốt nhất cho user!
"""

    def __init__(self, mcp_client):
        self.mcp_client = mcp_client
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        self.stats = {
            "total_screenings": 0,
            "avg_results_per_screening": 0.0,
            "most_used_criteria": {}
        }

    async def screen(
        self,
        user_query: str,
        shared_state: Optional[Dict] = None
    ) -> AsyncIterator[str]:
        """
        Screen stocks based on user criteria

        Args:
            user_query: User's screening request
            shared_state: Shared state for storing results

        Yields:
            Screening results
        """
        self.stats["total_screenings"] += 1

        try:
            # Parse criteria from query
            criteria = await self._parse_criteria(user_query)

            # Screen stocks
            results = await self.mcp_client.call_tool(
                "screen_stocks",
                {
                    "conditions": criteria,
                    "exchanges": ["HSX", "HNX", "UPCOM"],
                    "limit": 20
                }
            )

            if shared_state is not None:
                shared_state["screening_results"] = results

            # Format and yield results
            formatted = self._format_results(results, criteria)
            yield formatted

        except Exception as e:
            yield f"❌ Lỗi khi sàng lọc: {str(e)}"

    async def _parse_criteria(self, user_query: str) -> Dict[str, str]:
        """Parse screening criteria from natural language query"""
        # Use Gemini to parse criteria
        prompt = f"""
Phân tích yêu cầu sau và trả về tiêu chí sàng lọc dưới dạng JSON:

User query: "{user_query}"

Trả về format:
{{
    "roe": ">15",
    "pe": "<15",
    ...
}}

Chỉ trả về JSON, không giải thích.
"""

        response = self.client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[prompt],
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json"
            )
        )

        import json
        return json.loads(response.text)

    def _format_results(self, results: Dict, criteria: Dict) -> str:
        """Format screening results for output"""
        if results.get("status") != "success":
            return f"❌ {results.get('message', 'Unknown error')}"

        stocks = results.get("results", [])
        if not stocks:
            return "📭 Không tìm thấy cổ phiếu phù hợp với tiêu chí."

        # Build output
        output = ["🔍 **Kết quả sàng lọc**\n"]

        # Show criteria
        output.append("**Tiêu chí:**")
        for key, value in criteria.items():
            output.append(f"- {key} {value}")

        output.append(f"\n**Tìm thấy: {len(stocks)} cổ phiếu**\n")

        # Show top picks
        output.append("**Top khuyến nghị:**\n")

        for i, stock in enumerate(stocks[:10], 1):
            ticker = stock.get("ticker", "N/A")
            exchange = stock.get("exchange", "N/A")
            industry = stock.get("industry", "N/A")

            output.append(
                f"{i}. **{ticker}** ({exchange}) - {industry}\n"
                f"   • Các chỉ số: [Hiển thị từ data]\n"
            )

        output.append("\n💡 **Lưu ý:** Đây là kết quả sàng lọc định lượng.")

        return "\n".join(output)

    def get_stats(self) -> Dict:
        return self.stats.copy()
