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

        try:
            # Step 1: Get stock data
            stock_data = await self.mcp_client.call_tool(
                "get_stock_data",
                {"symbols": symbols, "lookback_days": 30}
            )

            if shared_state is not None:
                for symbol in symbols:
                    shared_state[f"stock_data_{symbol}"] = stock_data.get("results", {}).get(symbol)

            financial_data = None
            prediction = None

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

            # Step 4: Search for news (skip if tool not available)
            news_results = {"status": "skipped", "message": "News search not available"}
            try:
                news_results = await self.mcp_client.call_tool(
                    "gemini_search_and_summarize",
                    {
                        "query": f"{' '.join(symbols)} tin tuc moi nhat",
                        "use_search": True
                    }
                )
            except (ValueError, Exception):
                # Tool not available in DirectMCPClient, skip news search
                pass

            # Step 5: Generate comprehensive analysis with OpenAI
            analysis_prompt = self._build_final_analysis_prompt(
                symbols,
                user_query,
                stock_data,
                financial_data if analysis_type in ["fundamental", "full"] else None,
                prediction if analysis_type in ["price", "full"] else None,
                news_results
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
        news: Dict
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

        # Add user query
        prompt_parts.append(f"\n**Yeu cau cua user:** {user_query}\n")

        prompt_parts.append("""
Hay tong hop va phan tich theo format:
1. Thong tin gia hien tai
2. Phan tich ky thuat
3. Phan tich co ban (neu co)
4. Tin tuc va sentiment
5. Khuyen nghi ro rang (MUA/BAN/NAM GIU)
""")

        return "".join(prompt_parts)

    def get_stats(self) -> Dict:
        """Get analysis statistics"""
        return self.stats.copy()
