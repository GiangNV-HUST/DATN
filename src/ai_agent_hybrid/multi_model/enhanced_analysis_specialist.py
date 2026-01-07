"""
Enhanced Analysis Specialist với Multi-Model Support

Demonstrates cách integrate task-based model selection vào agent
"""

import os
import sys
from typing import Dict, Optional

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'ai_agent_mcp'))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from multi_model import (
    TaskType,
    TaskBasedModelSelector,
    ModelClientFactory,
    ModelResponse,
    get_usage_tracker
)


class EnhancedAnalysisSpecialist:
    """
    Analysis Specialist với Multi-Model Support

    Key improvements:
    - Task-based model selection
    - Sub-tasks use cheaper models (Gemini Flash)
    - Main analysis uses Claude Sonnet (reasoning)
    - Recommendations use GPT-4o (creative)
    - Cost tracking & monitoring
    """

    def __init__(self, mcp_client):
        """
        Initialize agent

        Args:
            mcp_client: Enhanced MCP Client instance
        """
        self.mcp_client = mcp_client
        self.name = "EnhancedAnalysisSpecialist"

        # Multi-model components
        self.model_selector = TaskBasedModelSelector()
        self.usage_tracker = get_usage_tracker()

        # Capabilities
        self.capabilities = [
            "technical_analysis",
            "fundamental_analysis",
            "news_analysis",
            "price_prediction",
            "comprehensive_analysis"
        ]

    async def analyze_stock(
        self,
        ticker: str,
        user_query: str,
        analysis_type: str = "comprehensive"
    ) -> Dict:
        """
        Main analysis workflow với multi-model

        Args:
            ticker: Stock symbol
            user_query: Original user query
            analysis_type: Type of analysis (technical, fundamental, comprehensive)

        Returns:
            Dict với analysis results
        """
        print(f"\n🔍 Starting analysis for {ticker}...")
        print(f"   Query: {user_query}")
        print(f"   Type: {analysis_type}")

        # Classify main task
        main_task, main_model = self.model_selector.get_task_and_model(user_query)
        print(f"   Main Task: {main_task.value}")
        print(f"   Main Model: {main_model}")

        results = {
            "ticker": ticker,
            "analysis_type": analysis_type,
            "main_task": main_task.value,
            "models_used": {}
        }

        # === STEP 1: Fetch price data (simple sub-task) ===
        price_data = await self._fetch_price_data(ticker)
        results["price_data"] = price_data
        results["models_used"]["price_data"] = "gemini-flash"

        # === STEP 2: Fetch financial data (simple sub-task) ===
        if analysis_type in ["fundamental", "comprehensive"]:
            financial_data = await self._fetch_financial_data(ticker)
            results["financial_data"] = financial_data
            results["models_used"]["financial_data"] = "gemini-flash"
        else:
            financial_data = None

        # === STEP 3: Fetch news (simple sub-task) ===
        news_summary = await self._fetch_news_summary(ticker)
        results["news_summary"] = news_summary
        results["models_used"]["news"] = "gemini-flash"

        # === STEP 4: Main analysis (complex - use main model) ===
        analysis = await self._synthesize_analysis(
            ticker=ticker,
            price_data=price_data,
            financial_data=financial_data,
            news_summary=news_summary,
            model_name=main_model
        )
        results["analysis"] = analysis
        results["models_used"]["analysis"] = main_model

        # === STEP 5: Generate recommendation (advisory - use GPT-4o) ===
        recommendation = await self._generate_recommendation(
            ticker=ticker,
            analysis=analysis
        )
        results["recommendation"] = recommendation
        results["models_used"]["recommendation"] = "gpt-4o"

        print(f"\n✅ Analysis complete!")
        print(f"   Models used: {list(set(results['models_used'].values()))}")

        return results

    async def _fetch_price_data(self, ticker: str) -> str:
        """
        Fetch price data using Gemini Flash (cheap, fast)

        Sub-task: DATA_QUERY
        """
        print(f"   📊 Fetching price data...")

        # Get data from MCP
        mcp_data = await self.mcp_client.get_stock_data(
            symbols=[ticker],
            lookback_days=30
        )

        # Use Gemini Flash to format
        model = ModelClientFactory.get_client("gemini-flash")

        prompt = f"""
        Summarize price data for {ticker}:

        Data: {mcp_data}

        Format:
        - Current price
        - Price change (% từ đầu tháng)
        - Key indicators: MA5, MA20, RSI, MACD
        - Volume trend

        Concise, 3-4 sentences.
        """

        response = await model.generate(prompt, temperature=0.3, max_tokens=300)

        # Track usage
        self.usage_tracker.track_usage(
            model_name="gemini-flash",
            task_type="data_query",
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            cost=response.cost,
            latency_ms=response.latency_ms
        )

        return response.content

    async def _fetch_financial_data(self, ticker: str) -> str:
        """
        Fetch financial data using Gemini Flash

        Sub-task: DATA_QUERY
        """
        print(f"   💰 Fetching financial data...")

        # Get data from MCP
        mcp_data = await self.mcp_client.get_financial_data(
            tickers=[ticker],
            is_income_statement=True,
            is_balance_sheet=True
        )

        # Use Gemini Flash
        model = ModelClientFactory.get_client("gemini-flash")

        prompt = f"""
        Summarize financial data for {ticker}:

        Data: {mcp_data}

        Format:
        - P/E, P/B ratios
        - ROE, ROA
        - Revenue & profit trends
        - Debt levels

        Concise, 3-4 sentences.
        """

        response = await model.generate(prompt, temperature=0.3, max_tokens=300)

        # Track usage
        self.usage_tracker.track_usage(
            model_name="gemini-flash",
            task_type="data_query",
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            cost=response.cost,
            latency_ms=response.latency_ms
        )

        return response.content

    async def _fetch_news_summary(self, ticker: str) -> str:
        """
        Fetch news summary using Gemini Flash

        Sub-task: DATA_QUERY
        """
        print(f"   📰 Fetching news...")

        # Get news from MCP
        try:
            news = await self.mcp_client.gemini_search_and_summarize(
                query=f"{ticker} tin tức mới nhất thị trường chứng khoán Việt Nam",
                user_query=f"Tin tức về {ticker}"
            )
            return news
        except Exception as e:
            return f"No recent news available. ({e})"

    async def _synthesize_analysis(
        self,
        ticker: str,
        price_data: str,
        financial_data: Optional[str],
        news_summary: str,
        model_name: str
    ) -> str:
        """
        Synthesize analysis using main model (Claude Sonnet)

        Main task: ANALYSIS (complex reasoning)
        """
        print(f"   🧠 Synthesizing analysis with {model_name}...")

        model = ModelClientFactory.get_client(model_name)

        # Construct prompt
        prompt = f"""
        Phân tích chuyên sâu cổ phiếu {ticker}:

        ## Dữ liệu giá & kỹ thuật:
        {price_data}

        ## Dữ liệu tài chính:
        {financial_data if financial_data else "N/A"}

        ## Tin tức & sentiment:
        {news_summary}

        ## Yêu cầu phân tích:

        1. **Phân tích kỹ thuật**:
           - Xu hướng hiện tại (tăng/giảm/sideway)
           - Các mức hỗ trợ/kháng cự
           - Tín hiệu từ RSI, MACD, MA
           - Volume analysis

        2. **Phân tích cơ bản** (nếu có dữ liệu):
           - Định giá (P/E, P/B so với ngành)
           - Hiệu quả kinh doanh (ROE, ROA)
           - Tăng trưởng doanh thu/lợi nhuận
           - Sức khỏe tài chính

        3. **Phân tích sentiment**:
           - Sentiment từ tin tức
           - Catalyst tích cực/tiêu cực
           - Rủi ro cần lưu ý

        4. **Nhận định tổng quan**:
           - Điểm mạnh (3 điểm)
           - Điểm yếu (2 điểm)
           - Xu hướng ngắn hạn (1-2 tuần)
           - Xu hướng trung hạn (1-3 tháng)

        Format: Vietnamese, professional, data-driven.
        """

        response = await model.generate(
            prompt,
            temperature=0.3,  # Lower for analysis
            max_tokens=2000
        )

        # Track usage
        self.usage_tracker.track_usage(
            model_name=model_name,
            task_type="analysis",
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            cost=response.cost,
            latency_ms=response.latency_ms
        )

        return response.content

    async def _generate_recommendation(
        self,
        ticker: str,
        analysis: str
    ) -> str:
        """
        Generate investment recommendation using GPT-4o

        Sub-task: ADVISORY (creative thinking)
        """
        print(f"   💡 Generating recommendation with GPT-4o...")

        model = ModelClientFactory.get_client("gpt-4o")

        prompt = f"""
        Dựa trên phân tích sau về {ticker}, hãy đưa ra khuyến nghị đầu tư:

        {analysis}

        ## Yêu cầu:

        **Quyết định**: BUY / HOLD / SELL

        **Giá mục tiêu**: [số] VNĐ (timeframe: 1-3 tháng)

        **Lý do chính** (3-5 điểm):
        1. [Lý do 1]
        2. [Lý do 2]
        ...

        **Rủi ro cần lưu ý** (2-3 điểm):
        1. [Rủi ro 1]
        2. [Rủi ro 2]

        **Chiến lược vào lệnh** (nếu BUY):
        - Entry point: [giá]
        - Stop loss: [giá] (-X%)
        - Take profit: [giá] (+X%)
        - Position size: Khuyến nghị % danh mục

        Format: Clear, actionable, risk-aware.
        """

        response = await model.generate(
            prompt,
            temperature=0.7,  # Higher for creativity
            max_tokens=800
        )

        # Track usage
        self.usage_tracker.track_usage(
            model_name="gpt-4o",
            task_type="advisory",
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            cost=response.cost,
            latency_ms=response.latency_ms
        )

        return response.content

    def get_capabilities(self) -> list:
        """Get agent capabilities"""
        return self.capabilities

    def get_usage_stats(self) -> Dict:
        """Get usage statistics"""
        return self.usage_tracker.get_summary()


# Example usage
if __name__ == "__main__":
    import asyncio
    from mcp_client import EnhancedMCPClient

    async def demo():
        # Initialize MCP client
        mcp_client = EnhancedMCPClient(
            server_script_path="../../../ai_agent_mcp/mcp_server/server.py"
        )
        await mcp_client.connect()

        # Initialize agent
        agent = EnhancedAnalysisSpecialist(mcp_client)

        # Run analysis
        result = await agent.analyze_stock(
            ticker="VCB",
            user_query="Phân tích toàn diện cổ phiếu VCB",
            analysis_type="comprehensive"
        )

        print("\n" + "=" * 60)
        print("ANALYSIS RESULT")
        print("=" * 60)
        print(f"\n{result['analysis']}")
        print(f"\n{result['recommendation']}")

        # Print usage stats
        agent.usage_tracker.print_summary()

        await mcp_client.disconnect()

    asyncio.run(demo())