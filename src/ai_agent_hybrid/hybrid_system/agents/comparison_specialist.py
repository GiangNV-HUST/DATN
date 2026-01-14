"""
Comparison Specialist Agent

Specialized in comparing multiple stocks:
- Side-by-side comparison of 2+ stocks
- Peer comparison within the same industry
- Relative valuation analysis
- Performance comparison over time

This agent helps answer questions like:
- "So sanh VCB voi TCB"
- "FPT hay CMG tot hon?"
- "So sanh P/E cac ngan hang"
"""

import os
import sys
from typing import Dict, List, Optional, AsyncIterator
from openai import OpenAI
import asyncio

# Add ai_agent_mcp to path for MCP client
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'ai_agent_mcp'))


class ComparisonSpecialist:
    """
    Specialist for comparing multiple stocks

    Provides:
    - Side-by-side comparison of multiple stocks
    - Peer comparison within industries
    - Relative valuation metrics
    - Performance comparison

    Tools (4):
    - get_stock_data: Price and technical data
    - get_financial_data: Fundamental metrics
    - get_stock_details_from_tcbs: Comprehensive data (80+ fields)
    - screen_stocks: For peer group selection
    """

    AGENT_INSTRUCTION = """
Ban la chuyen gia so sanh co phieu Viet Nam voi kha nang:
- So sanh gia va hieu suat (price performance)
- So sanh chi so ky thuat (RSI, MACD, MA)
- So sanh chi so co ban (P/E, P/B, ROE, ROA, EPS)
- So sanh trong cung nganh (peer comparison)
- Danh gia tuong doi (relative valuation)

## TOOLS CUA BAN:

1. **get_stock_data(symbols, lookback_days)**
   - Lay du lieu gia + indicators
   - So sanh bien dong gia theo thoi gian

2. **get_financial_data(tickers, is_income_statement, is_balance_sheet, is_ratio)**
   - Lay bao cao tai chinh de so sanh
   - So sanh revenue, profit, margins

3. **get_stock_details_from_tcbs(symbols)**
   - 80+ truong du lieu chi tiet
   - Bao gom tat ca chi so can thiet de so sanh

4. **screen_stocks(conditions, sort_by, limit)**
   - Tim cac co phieu cung nganh de so sanh
   - Loc theo tieu chi cu the

## OUTPUT FORMAT:

### So sanh co ban:
| Chi so | [Symbol 1] | [Symbol 2] | Nhan xet |
|--------|------------|------------|----------|
| Gia | XX,XXX | YY,YYY | ... |
| P/E | 12.5 | 15.3 | Symbol 1 re hon |
| P/B | 2.1 | 1.8 | Symbol 2 re hon |
| ROE | 18% | 15% | Symbol 1 sinh loi tot hon |
| EPS | 5,200 | 4,800 | Symbol 1 cao hon |

### So sanh ky thuat:
| Chi so | [Symbol 1] | [Symbol 2] | Nhan xet |
|--------|------------|------------|----------|
| RSI | 65 | 72 | Symbol 2 overbought |
| MA20 | Tren | Duoi | Symbol 1 xu huong tang |

### So sanh hieu suat:
- 1 thang: Symbol 1 (+5%) vs Symbol 2 (+3%)
- 3 thang: Symbol 1 (+12%) vs Symbol 2 (+8%)

### Ket luan:
- **Tong hop:** [Danh gia tong quan]
- **Khuyen nghi:** [Symbol nao tot hon cho muc tieu dau tu]
- **Phu hop voi:** [Loai nha dau tu: an toan/tich cuc]

Hay so sanh chi tiet, khach quan va dua ra khuyen nghi ro rang!
"""

    def __init__(self, mcp_client):
        """
        Initialize Comparison Specialist

        Args:
            mcp_client: EnhancedMCPClient or DirectMCPClient instance
        """
        self.mcp_client = mcp_client
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        # Statistics
        self.stats = {
            "total_comparisons": 0,
            "two_stock_comparisons": 0,
            "multi_stock_comparisons": 0,
            "peer_comparisons": 0
        }

    async def compare_stocks(
        self,
        symbols: List[str],
        comparison_type: str = "full",  # full, price, fundamental, technical
        cached_details: Optional[Dict] = None  # Reuse cached stock details
    ) -> Dict:
        """
        Compare multiple stocks

        Args:
            symbols: List of stock symbols to compare
            comparison_type: Type of comparison
            cached_details: Optional cached result from get_stock_details_from_tcbs

        Returns:
            Dict with comparison data
        """
        try:
            comparison_data = {
                "symbols": symbols,
                "comparison_type": comparison_type,
                "data": {}
            }

            # Use cached details or fetch new
            if cached_details and cached_details.get("status") == "success":
                details_result = cached_details
            else:
                details_result = await self.mcp_client.call_tool(
                    "get_stock_details_from_tcbs",
                    {"symbols": symbols}
                )

            if details_result.get("status") == "success":
                stocks_data = details_result.get("data", [])

                # Organize by symbol
                for stock in stocks_data:
                    ticker = stock.get("ticker")
                    if ticker:
                        comparison_data["data"][ticker] = stock

            # Store raw details for potential reuse
            comparison_data["_cached_details"] = details_result

            # Get price data for performance comparison
            if comparison_type in ["full", "price", "technical"]:
                price_result = await self.mcp_client.call_tool(
                    "get_stock_data",
                    {"symbols": symbols, "lookback_days": 30}
                )

                if price_result.get("status") in ["success", "partial_success"]:
                    for symbol, data in price_result.get("results", {}).items():
                        if symbol in comparison_data["data"]:
                            comparison_data["data"][symbol]["price_history"] = data.get("data", {}).get("data", [])

            # Get financial data for fundamental comparison
            if comparison_type in ["full", "fundamental"]:
                financial_result = await self.mcp_client.call_tool(
                    "get_financial_data",
                    {
                        "tickers": symbols,
                        "is_income_statement": True,
                        "is_balance_sheet": True,
                        "is_financial_ratios": True
                    }
                )

                if financial_result.get("status") in ["success", "partial_success"]:
                    for symbol, data in financial_result.get("results", {}).items():
                        if symbol in comparison_data["data"]:
                            comparison_data["data"][symbol]["financial_details"] = data

            return {"status": "success", "comparison": comparison_data}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def get_peer_group(self, symbol: str, limit: int = 10) -> Dict:
        """
        Get peer stocks in the same industry for comparison

        Args:
            symbol: Reference stock symbol
            limit: Number of peers to return

        Returns:
            Dict with peer group data
        """
        try:
            # First, get the industry of the reference stock
            details = await self.mcp_client.call_tool(
                "get_stock_details_from_tcbs",
                {"symbols": [symbol]}
            )

            if details.get("status") != "success" or not details.get("data"):
                return {"status": "error", "message": f"Cannot get info for {symbol}"}

            industry = details["data"][0].get("industry", "")

            if not industry:
                return {"status": "error", "message": f"Cannot determine industry for {symbol}"}

            # Screen for stocks in the same industry
            peers_result = await self.mcp_client.call_tool(
                "screen_stocks",
                {
                    "conditions": {"industry": f"=={industry}"},
                    "sort_by": "market_cap",
                    "ascending": False,
                    "limit": limit + 1  # +1 to exclude the reference stock
                }
            )

            if peers_result.get("status") != "success":
                return {"status": "error", "message": "Cannot screen for peers"}

            # Filter out the reference stock
            peers = [
                s for s in peers_result.get("data", [])
                if s.get("ticker") != symbol.upper()
            ][:limit]

            return {
                "status": "success",
                "reference_symbol": symbol,
                "industry": industry,
                "peers": peers,
                "peer_count": len(peers)
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def calculate_relative_metrics(
        self,
        symbols: List[str],
        cached_details: Optional[Dict] = None
    ) -> Dict:
        """
        Calculate relative valuation metrics for comparison

        Args:
            symbols: List of stock symbols
            cached_details: Optional cached result from get_stock_details_from_tcbs

        Returns:
            Dict with relative metrics
        """
        try:
            # Use cached details or fetch new
            if cached_details and cached_details.get("status") == "success":
                details_result = cached_details
            else:
                details_result = await self.mcp_client.call_tool(
                    "get_stock_details_from_tcbs",
                    {"symbols": symbols}
                )

            if details_result.get("status") != "success":
                return {"status": "error", "message": "Cannot fetch stock details"}

            stocks = details_result.get("data", [])

            # Calculate averages for comparison
            metrics_to_compare = ["pe", "pb", "roe", "roa", "eps", "dividend_yield", "market_cap"]

            averages = {}
            for metric in metrics_to_compare:
                values = [s.get(metric) for s in stocks if s.get(metric) is not None]
                if values:
                    averages[metric] = sum(values) / len(values)

            # Calculate relative position for each stock
            relative_metrics = {}
            for stock in stocks:
                ticker = stock.get("ticker")
                relative_metrics[ticker] = {
                    "absolute": {},
                    "vs_average": {},
                    "rank": {}
                }

                for metric in metrics_to_compare:
                    value = stock.get(metric)
                    if value is not None:
                        relative_metrics[ticker]["absolute"][metric] = value

                        if metric in averages and averages[metric]:
                            diff_pct = ((value - averages[metric]) / averages[metric]) * 100
                            relative_metrics[ticker]["vs_average"][metric] = round(diff_pct, 2)

                # Calculate rank for each metric
                for metric in metrics_to_compare:
                    values_with_tickers = [
                        (s.get("ticker"), s.get(metric))
                        for s in stocks
                        if s.get(metric) is not None
                    ]

                    # Higher is better for ROE, ROA, EPS, dividend_yield
                    # Lower is better for PE, PB
                    reverse = metric in ["roe", "roa", "eps", "dividend_yield", "market_cap"]
                    sorted_values = sorted(values_with_tickers, key=lambda x: x[1] or 0, reverse=reverse)

                    for rank, (t, v) in enumerate(sorted_values, 1):
                        if t == ticker:
                            relative_metrics[ticker]["rank"][metric] = rank
                            break

            return {
                "status": "success",
                "symbols": symbols,
                "averages": averages,
                "relative_metrics": relative_metrics
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def analyze(
        self,
        symbols: List[str],
        user_query: str,
        shared_state: Optional[Dict] = None,
        comparison_type: str = "full"
    ) -> AsyncIterator[str]:
        """
        Perform stock comparison analysis

        Args:
            symbols: List of stock symbols to compare
            user_query: User's comparison request
            shared_state: Shared state for storing intermediate results
            comparison_type: Type of comparison

        Yields:
            Analysis chunks as they're generated
        """
        self.stats["total_comparisons"] += 1

        if len(symbols) == 2:
            self.stats["two_stock_comparisons"] += 1
        else:
            self.stats["multi_stock_comparisons"] += 1

        try:
            # Get comparison data (this also caches stock details)
            comparison_result = await self.compare_stocks(symbols, comparison_type)

            # Reuse cached details for relative metrics (avoids redundant API call)
            cached_details = comparison_result.get("comparison", {}).get("_cached_details")
            relative_metrics = await self.calculate_relative_metrics(symbols, cached_details)

            # Store in shared state if provided
            if shared_state is not None:
                shared_state["comparison_data"] = comparison_result
                shared_state["relative_metrics"] = relative_metrics

            # Build analysis prompt
            analysis_prompt = f"""
Dua tren du lieu sau, hay so sanh cac co phieu {', '.join(symbols)}:

**User Query:** {user_query}

**Du lieu so sanh:**
{comparison_result}

**Chi so tuong doi:**
{relative_metrics}

Hay so sanh chi tiet theo format:
1. Bang so sanh chi so co ban (P/E, P/B, ROE, EPS, Market Cap)
2. Bang so sanh chi so ky thuat (RSI, MA, xu huong)
3. So sanh hieu suat (1 thang, 3 thang, 1 nam neu co)
4. Phan tich diem manh/yeu cua tung co phieu
5. Ket luan va khuyen nghi ro rang: Co phieu nao tot hon cho muc tieu gi
"""

            # Generate analysis with OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.AGENT_INSTRUCTION},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.7,
                max_tokens=2500
            )

            yield response.choices[0].message.content

        except Exception as e:
            yield f"[ERROR] Loi khi so sanh co phieu: {str(e)}"

    async def peer_analysis(
        self,
        symbol: str,
        user_query: str,
        shared_state: Optional[Dict] = None
    ) -> AsyncIterator[str]:
        """
        Perform peer comparison analysis

        Args:
            symbol: Reference stock symbol
            user_query: User's query
            shared_state: Shared state

        Yields:
            Analysis chunks
        """
        self.stats["peer_comparisons"] += 1

        try:
            # Get peer group
            peer_result = await self.get_peer_group(symbol, limit=5)

            if peer_result.get("status") != "success":
                yield f"[ERROR] Khong the tim peer group: {peer_result.get('message')}"
                return

            # Get symbols for comparison
            peer_symbols = [p.get("ticker") for p in peer_result.get("peers", [])]
            all_symbols = [symbol] + peer_symbols

            # Compare with peers (this caches stock details)
            comparison_result = await self.compare_stocks(all_symbols, "fundamental")

            # Reuse cached details for relative metrics (avoids redundant API call)
            cached_details = comparison_result.get("comparison", {}).get("_cached_details")
            relative_metrics = await self.calculate_relative_metrics(all_symbols, cached_details)

            # Store in shared state
            if shared_state is not None:
                shared_state["peer_analysis"] = {
                    "reference": symbol,
                    "peers": peer_result,
                    "comparison": comparison_result,
                    "relative_metrics": relative_metrics
                }

            # Build analysis prompt
            analysis_prompt = f"""
So sanh {symbol} voi cac co phieu cung nganh {peer_result.get('industry')}:

**User Query:** {user_query}

**Reference Stock:** {symbol}
**Peer Stocks:** {', '.join(peer_symbols)}
**Industry:** {peer_result.get('industry')}

**Du lieu so sanh:**
{comparison_result}

**Chi so tuong doi:**
{relative_metrics}

Hay phan tich:
1. Vi tri cua {symbol} trong nganh (dung dau/giua/duoi)
2. Diem manh so voi peers
3. Diem yeu so voi peers
4. Co phieu nao trong nganh dang hap dan nhat
5. Khuyen nghi cu the cho {symbol}
"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.AGENT_INSTRUCTION},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.7,
                max_tokens=2500
            )

            yield response.choices[0].message.content

        except Exception as e:
            yield f"[ERROR] Loi khi phan tich peer: {str(e)}"

    def get_stats(self) -> Dict:
        """Get comparison statistics"""
        return self.stats.copy()
