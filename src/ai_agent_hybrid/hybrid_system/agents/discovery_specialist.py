"""
Discovery Specialist Agent

Specialized in discovering potential stocks combining:
- Web search for market trends and potential picks
- Quantitative data from TCBS
- AI-powered analysis and recommendation

Based on OLD system's stock_discovery_agent.py pattern.
"""

import os
import sys
from typing import Dict, List, Optional, AsyncIterator

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'ai_agent_mcp'))

import google.generativeai as genai


class DiscoverySpecialist:
    """
    Specialist for discovering potential stocks

    Tools (5):
    - discover_stocks_by_profile: AI-powered discovery by investment profile
    - search_potential_stocks: Search for potential stocks
    - get_stock_details_from_tcbs: 70+ fields detailed data
    - gemini_search_and_summarize: Web research
    - get_stock_data: Validate discoveries

    Workflow (from OLD stock_discovery_agent):
    1. Search web for potential stocks/trends
    2. Extract stock symbols from results
    3. Get detailed TCBS data
    4. Combine qualitative + quantitative analysis
    5. Recommend top picks
    """

    AGENT_INSTRUCTION = """
Bạn là chuyên gia tìm kiếm cổ phiếu tiềm năng trên thị trường Việt Nam.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## NHIỆM VỤ CỦA BẠN:

Tìm kiếm và đề xuất cổ phiếu tiềm năng bằng cách kết hợp:
1. **Web Research**: Tin tức, xu hướng, khuyến nghị từ chuyên gia
2. **Quantitative Data**: Dữ liệu chi tiết từ TCBS (70+ chỉ số)
3. **AI Analysis**: Phân tích và tổng hợp

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## TOOLS CỦA BẠN (5 tools):

1. **discover_stocks_by_profile(investment_profile, num_stocks)**
   - AI-powered discovery dựa trên investment profile
   - Trả về: Danh sách cổ phiếu phù hợp với profile

2. **search_potential_stocks(criteria, sector, market_trend)**
   - Tìm kiếm cổ phiếu tiềm năng
   - criteria: "growth", "value", "momentum", "quality"
   - sector: Optional ngành cụ thể

3. **get_stock_details_from_tcbs(symbols)**
   - Lấy dữ liệu chi tiết từ TCBS (70+ trường)
   - Bao gồm: Valuation, Growth, Profitability, Liquidity, ...

4. **gemini_search_and_summarize(query, use_search)**
   - Tìm kiếm web về cổ phiếu tiềm năng
   - Ví dụ: "cổ phiếu tiềm năng 2025", "blue chip đáng mua"

5. **get_stock_data(symbols, lookback_days)**
   - Validate và lấy price data

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## WORKFLOW CHUẨN (Học từ OLD stock_discovery_agent):

### Step 1: Web Search (Qualitative)
```
User: "Tìm cổ phiếu tiềm năng cho tôi"

→ gemini_search_and_summarize(
    query="cổ phiếu Việt Nam tiềm năng 2025",
    use_search=True
)

→ Kết quả: Tin tức, khuyến nghị, xu hướng
→ Extract symbols: VCB, FPT, HPG, VNM, ...
```

### Step 2: Get Detailed Data (Quantitative)
```
→ get_stock_details_from_tcbs(["VCB", "FPT", "HPG", "VNM"])

→ Kết quả: 70+ trường dữ liệu:
  - Valuation: P/E, P/B, EV/EBITDA
  - Growth: Revenue growth, EPS growth
  - Profitability: ROE, ROA, Margins
  - Liquidity: Current ratio, Quick ratio
  - Financial health: Debt/Equity
```

### Step 3: Validate with Price Data
```
→ get_stock_data(["VCB", "FPT", "HPG", "VNM"], 30)

→ Kết quả: Price, Volume, Technical indicators
```

### Step 4: Combine & Analyze
```
→ Kết hợp:
  * Qualitative: Tại sao chuyên gia recommend?
  * Quantitative: Số liệu có xác nhận không?
  * Technical: Xu hướng giá như thế nào?

→ Đánh giá từng cổ phiếu
→ Rank theo tiềm năng
→ Recommend top 3-5 picks
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## USE CASES:

### 1. General Discovery:
```
User: "Tìm cổ phiếu tiềm năng"

Step 1: Search web → Extract 10+ symbols
Step 2: Get TCBS data → Filter good fundamentals
Step 3: Validate price → Check technical strength
Step 4: Recommend top 3-5
```

### 2. Sector-specific:
```
User: "Cổ phiếu ngân hàng nào tốt?"

Step 1: search_potential_stocks(sector="banking")
Step 2: get_stock_details_from_tcbs(banking_stocks)
Step 3: Rank by fundamentals
Step 4: Recommend
```

### 3. Profile-based:
```
User: "Cổ phiếu phù hợp với risk thấp, dài hạn"

Step 1: discover_stocks_by_profile(
    profile={"risk": "low", "horizon": "long"}
)
Step 2: get_stock_details_from_tcbs(results)
Step 3: Validate and recommend
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## OUTPUT FORMAT:

```
🔍 **CỔ PHIẾU TIỀM NĂNG**

**Nguồn tìm kiếm:**
- Web research: 15 cổ phiếu được nhắc đến
- Quantitative filter: 8 cổ phiếu đạt tiêu chí
- Final picks: Top 5 khuyến nghị

**TOP 5 KHUYẾN NGHỊ:**

**1. VCB - Vietcombank** ⭐⭐⭐⭐⭐
**Lý do web research:**
- Được nhiều chuyên gia khuyến nghị
- Lãi suất tăng có lợi cho ngân hàng
- Blue chip ổn định

**Phân tích định lượng (TCBS):**
- P/E: 12.3 (hấp dẫn)
- ROE: 18.5% (xuất sắc)
- Revenue growth: +15% YoY
- Debt/Equity: 8.2 (an toàn cho ngân hàng)

**Technical:**
- Giá: 94,000 (+2.5% tuần)
- Volume: Cao
- Xu hướng: Tăng

💡 **Đánh giá**: MẠNH - Kết hợp tốt giữa fundamentals và technical

---

**2. FPT - FPT Corporation** ⭐⭐⭐⭐
[Similar format...]

---

**3. HPG - Hòa Phát Group** ⭐⭐⭐⭐
[...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 **Tổng kết:**
- 5 cổ phiếu trên đều có fundamentals tốt
- Được market đánh giá cao
- Phù hợp cho danh mục dài hạn
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## NGUYÊN TẮC:

✅ DO:
1. Luôn kết hợp web research + quantitative data
2. Extract ít nhất 10 symbols, recommend 3-5
3. Giải thích TẠI SAO cổ phiếu này tiềm năng
4. Validate với TCBS data
5. Ưu tiên cổ phiếu có thanh khoản cao

❌ DON'T:
1. Đừng chỉ dựa vào web search
2. Đừng recommend cổ phiếu kém thanh khoản
3. Đừng bỏ qua fundamental check
4. Đừng recommend quá nhiều (>5 stocks)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Hãy tìm những cổ phiếu thực sự tiềm năng!
"""

    def __init__(self, mcp_client):
        """
        Initialize Discovery Specialist

        Args:
            mcp_client: EnhancedMCPClient instance
        """
        self.mcp_client = mcp_client
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        self.stats = {
            "total_discoveries": 0,
            "avg_stocks_found": 0.0,
            "top_recommended_stocks": {}
        }

    async def discover(
        self,
        user_query: str,
        investment_profile: Optional[Dict] = None,
        num_stocks: int = 5,
        shared_state: Optional[Dict] = None
    ) -> AsyncIterator[str]:
        """
        Discover potential stocks

        Args:
            user_query: User's discovery request
            investment_profile: Optional investment profile
            num_stocks: Number of stocks to recommend
            shared_state: Shared state for storing results

        Yields:
            Discovery results
        """
        self.stats["total_discoveries"] += 1

        try:
            # Step 1: Web search for potential stocks
            yield "🔍 Đang tìm kiếm cổ phiếu tiềm năng trên web...\n"

            search_query = self._build_search_query(user_query, investment_profile)
            web_results = await self.mcp_client.call_tool(
                "gemini_search_and_summarize",
                {
                    "query": search_query,
                    "use_search": True
                }
            )

            # Step 2: Extract stock symbols from web results
            yield "📊 Đang phân tích kết quả tìm kiếm...\n"
            symbols = await self._extract_symbols_from_results(web_results)

            yield f"✅ Tìm thấy {len(symbols)} cổ phiếu được nhắc đến\n"

            # Step 3: Get detailed TCBS data
            yield "📈 Đang lấy dữ liệu chi tiết từ TCBS...\n"
            tcbs_data = await self.mcp_client.call_tool(
                "get_stock_details_from_tcbs",
                {"symbols": symbols[:10]}  # Limit to 10
            )

            # Step 4: Get price data for validation
            yield "💹 Đang kiểm tra dữ liệu giá...\n"
            price_data = await self.mcp_client.call_tool(
                "get_stock_data",
                {"symbols": symbols[:10], "lookback_days": 30}
            )

            # Step 5: Analyze and rank
            yield "🎯 Đang phân tích và xếp hạng...\n"
            ranked_stocks = await self._analyze_and_rank(
                symbols=symbols[:10],
                web_results=web_results,
                tcbs_data=tcbs_data,
                price_data=price_data,
                num_recommendations=num_stocks
            )

            if shared_state is not None:
                shared_state["discovered_stocks"] = ranked_stocks

            # Step 6: Format and yield results
            yield "\n" + "="*50 + "\n"
            yield "🔍 **CỔ PHIẾU TIỀM NĂNG**\n"
            yield "="*50 + "\n\n"

            formatted = self._format_discovery_results(
                ranked_stocks=ranked_stocks,
                web_summary=web_results.get("summary", ""),
                total_found=len(symbols)
            )

            yield formatted

        except Exception as e:
            yield f"\n❌ Lỗi khi tìm kiếm cổ phiếu: {str(e)}"

    def _build_search_query(self, user_query: str, profile: Optional[Dict]) -> str:
        """Build search query based on user request and profile"""
        base_query = user_query

        if profile:
            risk = profile.get("risk_tolerance", "medium")
            horizon = profile.get("time_horizon", "medium")

            if risk == "low":
                base_query += " blue chip ổn định"
            elif risk == "high":
                base_query += " tăng trưởng cao"

            if horizon == "long":
                base_query += " dài hạn"

        return base_query + " Việt Nam 2025"

    async def _extract_symbols_from_results(self, web_results: Dict) -> List[str]:
        """Extract stock symbols from web search results using AI"""
        prompt = f"""
Phân tích kết quả search sau và trích xuất TẤT CẢ các mã cổ phiếu được nhắc đến:

{web_results.get("summary", "")}

Trả về danh sách mã cổ phiếu dưới dạng JSON array:
{{"symbols": ["VCB", "FPT", ...]}}

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
        result = json.loads(response.text)
        return result.get("symbols", [])

    async def _analyze_and_rank(
        self,
        symbols: List[str],
        web_results: Dict,
        tcbs_data: Dict,
        price_data: Dict,
        num_recommendations: int
    ) -> List[Dict]:
        """Analyze and rank stocks using AI"""
        # Use Gemini to analyze and rank
        prompt = f"""
Dựa trên dữ liệu sau, hãy xếp hạng và chọn top {num_recommendations} cổ phiếu tiềm năng:

**Web Research:**
{web_results.get("summary", "")}

**TCBS Data:**
{str(tcbs_data)[:2000]}  # Limit length

**Price Data:**
{str(price_data)[:1000]}

Trả về JSON format:
{{
    "stocks": [
        {{
            "symbol": "VCB",
            "rank": 1,
            "score": 9.5,
            "reasons": ["reason1", "reason2"],
            "fundamentals_summary": "...",
            "technical_summary": "..."
        }},
        ...
    ]
}}
"""

        response = self.client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[prompt],
            config=types.GenerateContentConfig(
                temperature=0.3,
                response_mime_type="application/json"
            )
        )

        import json
        result = json.loads(response.text)
        return result.get("stocks", [])

    def _format_discovery_results(
        self,
        ranked_stocks: List[Dict],
        web_summary: str,
        total_found: int
    ) -> str:
        """Format discovery results for output"""
        output = []

        output.append(f"**Nguồn tìm kiếm:**")
        output.append(f"- Web research: {total_found} cổ phiếu được nhắc đến")
        output.append(f"- Final picks: Top {len(ranked_stocks)} khuyến nghị\n")

        output.append("**TOP KHUYẾN NGHỊ:**\n")

        for stock in ranked_stocks:
            symbol = stock.get("symbol", "N/A")
            rank = stock.get("rank", 0)
            score = stock.get("score", 0)
            reasons = stock.get("reasons", [])

            stars = "⭐" * min(5, int(score))

            output.append(f"**{rank}. {symbol}** {stars}")
            output.append(f"**Điểm: {score}/10**\n")

            output.append("**Lý do:**")
            for reason in reasons:
                output.append(f"- {reason}")

            output.append(f"\n**Fundamentals:** {stock.get('fundamentals_summary', 'N/A')}")
            output.append(f"**Technical:** {stock.get('technical_summary', 'N/A')}\n")
            output.append("---\n")

        output.append("\n💡 **Lưu ý:** Đây là kết quả phân tích tự động, cần nghiên cứu thêm trước khi đầu tư.")

        return "\n".join(output)

    def get_stats(self) -> Dict:
        """Get discovery statistics"""
        return self.stats.copy()
