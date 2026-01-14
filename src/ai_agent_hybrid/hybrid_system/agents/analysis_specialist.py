"""
Analysis Specialist Agent

Specialized in stock analysis combining:
- Price data & technical indicators
- Fundamental analysis
- News & sentiment
- AI-powered insights

Based on OLD system's analysis_agent.py pattern.
Updated: Now uses OpenAI instead of Gemini for consistency.
"""

import os
import sys
from typing import Dict, List, Optional, AsyncIterator
from openai import OpenAI

# Add ai_agent_mcp to path for MCP client
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'ai_agent_mcp'))


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
Ban la chuyen gia phan tich co phieu Viet Nam voi kha nang:
- Phan tich ky thuat (RSI, MACD, MA, Volume, ...)
- Phan tich co ban (P/E, ROE, EPS, Revenue, ...)
- Phan tich tin tuc va sentiment
- Du doan xu huong gia

## TOOLS CUA BAN (5 tools):

1. **get_stock_data(symbols, lookback_days)**
   - Lay du lieu gia + indicators (MA5, MA10, MA20, RSI, MACD, Volume)
   - Vi du: get_stock_data(["VCB"], 30) -> 30 ngay data

2. **get_stock_price_prediction(symbols, table_type)**
   - Du doan gia tuong lai bang ENSEMBLE 5-MODEL (PatchTST + LightGBM + LSTM + Prophet + XGBoost)
   - Do chinh xac cao: MAPE 0.8-1.2% (3 ngay), 2.5-3.5% (48 ngay)
   - table_type: "3d" (3 ngay) hoac "48d" (48 ngay)
   - Tra ve: predicted_price, confidence_lower, confidence_upper, change_percent

3. **get_financial_data(tickers, is_income_statement, is_balance_sheet, ...)**
   - Bao cao tai chinh (income, balance sheet, cash flow, ratios)
   - Vi du: get_financial_data(["VCB"], is_income_statement=True)

4. **generate_chart_from_data(symbols, lookback_days)**
   - Tao bieu do nen + volume
   - CHU Y: Phai goi get_stock_data truoc!

5. **gemini_search_and_summarize(query, use_search)**
   - Tim kiem tin tuc va tom tat
   - Vi du: gemini_search_and_summarize("VCB tin tuc moi nhat", True)

## OUTPUT FORMAT:

### Simple Price Query:
- **Gia hien tai:** 94,000 VND (+2.5%)
- **Phan tich ky thuat:**
  - RSI(14): 65 -> Trung tinh
  - MACD: Tich cuc (histogram > 0)
  - MA20: Gia tren MA -> Xu huong tang
- **Tin tuc:** [Tu search...]
- **Danh gia:** NAM GIU

### Full Analysis:
1. Thong tin gia
2. Phan tich ky thuat
3. Phan tich co ban (neu co)
4. Du bao
5. Tin tuc & Sentiment
6. Khuyen nghi: MUA/BAN/NAM GIU

Hay phan tich chuyen nghiep va dua ra insights co gia tri!
"""

    def __init__(self, mcp_client):
        """
        Initialize Analysis Specialist

        Args:
            mcp_client: EnhancedMCPClient or DirectMCPClient instance
        """
        self.mcp_client = mcp_client
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

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
        """Wrap MCP tool for use with OpenAI"""
        async def wrapped(**kwargs):
            # Check if tool exists before calling to avoid async exception warnings
            if hasattr(self.mcp_client, 'has_tool') and not self.mcp_client.has_tool(tool_name):
                return {"status": "skipped", "message": f"Tool {tool_name} not available"}

            try:
                result = await self.mcp_client.call_tool(tool_name, kwargs)
                return result
            except ValueError as e:
                # Tool not available in DirectMCPClient
                return {"status": "skipped", "message": f"Tool {tool_name} not available"}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        return wrapped

    async def analyze(
        self,
        symbols: List[str] = None,
        user_query: str = "",
        shared_state: Optional[Dict] = None,
        analysis_type: str = "auto",  # auto, price, fundamental, full
        previous_context: str = ""  # Context from previous agent (e.g., screener results)
    ) -> AsyncIterator[str]:
        """
        Perform stock analysis

        Args:
            symbols: List of stock symbols (can be None if extracted from previous_context)
            user_query: User's analysis request
            shared_state: Shared state for storing intermediate results
            analysis_type: Type of analysis (auto/price/fundamental/full)

        Yields:
            Analysis chunks as they're generated
        """
        self.stats["total_analyses"] += 1

        # Extract symbols from previous_context if not provided
        if not symbols and previous_context:
            symbols = self._extract_symbols_from_context(previous_context)

        # Default to empty list if still no symbols
        if not symbols:
            yield "[ERROR] Khong tim thay ma co phieu de phan tich. Vui long cung cap ma co phieu."
            return

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

        try:
            # Check if user wants a chart
            needs_chart = self._needs_chart(user_query)
            lookback_days = self._extract_lookback_days(user_query)

            # Step 1: Get stock data
            stock_data = await self.mcp_client.call_tool(
                "get_stock_data",
                {"symbols": symbols, "lookback_days": lookback_days}
            )

            if shared_state is not None:
                for symbol in symbols:
                    shared_state[f"stock_data_{symbol}"] = stock_data.get("results", {}).get(symbol)

            financial_data = None
            prediction = None
            chart_result = None

            # Step 2: Generate chart if requested
            if needs_chart:
                try:
                    chart_result = await self.mcp_client.call_tool(
                        "generate_chart_from_data",
                        {"symbols": symbols, "lookback_days": lookback_days}
                    )
                    if shared_state is not None:
                        shared_state["chart_result"] = chart_result
                except Exception as chart_error:
                    chart_result = {"status": "error", "message": str(chart_error)}

            # Step 3: Get financial data if needed
            if analysis_type in ["fundamental", "full"]:
                financial_data = await self.mcp_client.call_tool(
                    "get_financial_data",
                    {
                        "tickers": symbols,
                        "is_income_statement": True,
                        "is_balance_sheet": True,
                        "is_financial_ratios": True
                    }
                )

                if shared_state is not None:
                    for symbol in symbols:
                        shared_state[f"financial_data_{symbol}"] = financial_data.get("results", {}).get(symbol)

            # Step 4: Get price prediction
            if analysis_type in ["price", "full"]:
                prediction = await self.mcp_client.call_tool(
                    "get_stock_price_prediction",
                    {"symbols": symbols, "table_type": "3d"}
                )

                if shared_state is not None:
                    for symbol in symbols:
                        shared_state[f"prediction_{symbol}"] = prediction.get("results", {}).get(symbol)

            # Step 5: Search for news (skip if tool not available)
            # Use wrapped tool to gracefully handle missing tool
            news_results = await self.tools["gemini_search_and_summarize"](
                query=f"{' '.join(symbols)} tin tuc moi nhat",
                use_search=True
            )

            # Step 6: Generate comprehensive analysis with OpenAI
            analysis_prompt = self._build_final_analysis_prompt(
                symbols,
                user_query,
                stock_data,
                financial_data if analysis_type in ["fundamental", "full"] else None,
                prediction if analysis_type in ["price", "full"] else None,
                news_results,
                chart_result
            )

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.AGENT_INSTRUCTION},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.7,
                max_tokens=2048
            )

            # Yield response
            yield response.choices[0].message.content

            # If chart was generated, yield chart info separately
            if chart_result and chart_result.get("status") == "success":
                html_paths = chart_result.get("html_paths", {})
                if html_paths:
                    chart_info = "\n\n📊 **Biểu đồ đã được tạo và mở trong trình duyệt:**\n"
                    for symbol, path in html_paths.items():
                        chart_info += f"- {symbol}: {path}\n"
                    yield chart_info

        except Exception as e:
            yield f"[ERROR] Loi khi phan tich: {str(e)}"

    def _determine_analysis_type(self, user_query: str) -> str:
        """Determine analysis type from query"""
        query_lower = user_query.lower()

        if any(kw in query_lower for kw in ["tai chinh", "fundamental", "co ban", "bao cao"]):
            return "fundamental"
        elif any(kw in query_lower for kw in ["toan dien", "chi tiet", "day du", "comprehensive"]):
            return "full"
        else:
            return "price"

    def _needs_chart(self, user_query: str) -> bool:
        """Check if user wants a chart"""
        query_lower = user_query.lower()
        chart_keywords = [
            "bieu do", "biểu đồ", "chart", "ve", "vẽ", "nen", "nến",
            "candlestick", "graph", "do thi", "đồ thị"
        ]
        return any(kw in query_lower for kw in chart_keywords)

    def _extract_lookback_days(self, user_query: str) -> int:
        """Extract number of days from query"""
        import re
        query_lower = user_query.lower()

        # Find patterns like "30 ngày", "30 phien", "30 days", "30d"
        patterns = [
            r'(\d+)\s*(?:ngay|ngày|phien|phiên|days?|d\b)',
            r'(\d+)\s*(?:tuan|tuần|weeks?|w\b)',
            r'(\d+)\s*(?:thang|tháng|months?|m\b)',
        ]

        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                num = int(match.group(1))
                if 'tuan' in pattern or 'week' in pattern:
                    return num * 7
                elif 'thang' in pattern or 'month' in pattern:
                    return num * 30
                return num

        return 30  # Default 30 days

    def _extract_symbols_from_context(self, context: str) -> List[str]:
        """
        Extract stock symbols from previous context (e.g., screener results)

        Args:
            context: Text from previous agent's output

        Returns:
            List of extracted stock symbols
        """
        import re

        # Common Vietnamese stock symbols
        common_symbols = {
            "VCB", "FPT", "HPG", "VIC", "VNM", "ACB", "MSN", "TCB", "VHM", "VPB",
            "MBB", "BID", "CTG", "STB", "HDB", "SSI", "VND", "HCM", "GAS", "PNJ",
            "MWG", "REE", "DPM", "PVD", "PLX", "PVS", "GVR", "POW", "VJC", "HVN",
            "SHB", "TPB", "LPB", "OCB", "VIB", "MSB", "KBC", "DXG", "NVL", "PDR"
        }

        # Words to exclude (Vietnamese words that look like symbols)
        exclude = {
            "KHI", "NEN", "CAI", "NAO", "XEM", "MUA", "BAN", "GIA", "HON", "TOT",
            "HAY", "ROI", "SAU", "CHO", "VAN", "THE", "NAY", "TAO", "TEN", "MOT",
            "HAI", "BAO", "VON", "LOC", "TOP", "HOT", "TAT", "MAT", "DAU", "TRI",
            "DCA", "VOI", "MOI", "LAP", "KHO", "TUY", "TAN", "DEN", "SAN", "CAN",
            "CHI", "GOI", "THI", "TUC", "VAY", "COT", "CAO", "KEO", "DUA", "NUA"
        }

        # Find all 3-4 letter uppercase words
        matches = re.findall(r'\b([A-Z]{3,4})\b', context.upper())

        symbols = []
        for match in matches:
            if match in exclude:
                continue
            if match in common_symbols or len(match) == 3:
                if match not in symbols:
                    symbols.append(match)

        # Limit to top 5 for analysis
        return symbols[:5]

    def _build_analysis_prompt(
        self,
        symbols: List[str],
        user_query: str,
        analysis_type: str
    ) -> str:
        """Build initial analysis prompt"""
        return f"""
Hay phan tich co phieu {', '.join(symbols)} theo yeu cau:

**User query:** {user_query}

**Loai phan tich:** {analysis_type}

Su dung cac tools co san de thu thap du lieu va phan tich.
"""

    def _build_final_analysis_prompt(
        self,
        symbols: List[str],
        user_query: str,
        stock_data: Dict,
        financial_data: Optional[Dict],
        prediction: Optional[Dict],
        news: Dict,
        chart_result: Optional[Dict] = None
    ) -> str:
        """Build final analysis prompt with all data"""
        prompt_parts = [
            f"Dua tren du lieu sau, hay phan tich co phieu {', '.join(symbols)}:\n"
        ]

        # Add stock data
        prompt_parts.append(f"**Du lieu gia:** {stock_data}\n")

        # Add financial data if available
        if financial_data:
            prompt_parts.append(f"**Du lieu tai chinh:** {financial_data}\n")

        # Add prediction if available
        if prediction:
            prompt_parts.append(f"**Du bao gia:** {prediction}\n")

        # Add news
        prompt_parts.append(f"**Tin tuc:** {news}\n")

        # Add chart info if available
        if chart_result and chart_result.get("status") == "success":
            prompt_parts.append(f"\n**Bieu do da duoc tao:** {chart_result.get('html_paths', {})}\n")
            prompt_parts.append("(Bieu do nen da duoc mo trong trinh duyet)\n")

        # Add user query
        prompt_parts.append(f"\n**Yeu cau cua user:** {user_query}\n")

        prompt_parts.append("""
Hay tong hop va phan tich theo format:
1. Thong tin gia hien tai
2. Phan tich ky thuat
3. Phan tich co ban (neu co)
4. Tin tuc va sentiment
5. Khuyen nghi ro rang (MUA/BAN/NAM GIU)

Neu user yeu cau bieu do, hay xac nhan rang bieu do da duoc tao va mo trong trinh duyet.
""")

        return "".join(prompt_parts)

    def get_stats(self) -> Dict:
        """Get analysis statistics"""
        return self.stats.copy()
