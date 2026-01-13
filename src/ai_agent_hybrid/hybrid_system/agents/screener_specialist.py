"""
Screener Specialist Agent

Specialized in stock screening and filtering based on:
- Financial metrics (P/E, ROE, Revenue growth, ...)
- Technical indicators (RSI, MACD, price vs MA, ...)
- Custom criteria

Based on OLD system's screener_agent.py pattern.
Updated: Now uses OpenAI instead of Gemini for consistency.
"""

import os
import sys
import json
from typing import Dict, List, Optional, AsyncIterator

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'ai_agent_mcp'))

from openai import OpenAI


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
Ban la chuyen gia sang loc co phieu Viet Nam.

## TOOLS CUA BAN (4 tools):

1. **screen_stocks(conditions, exchanges, limit)**
   - Sang loc co phieu voi 80+ tieu chi
   - conditions: {"roe": ">15", "pe": "<15", ...}
   - exchanges: ["HSX", "HNX", "UPCOM"]
   - limit: So luong ket qua (default: 20)

2. **get_screener_columns()**
   - Lay danh sach tat ca tieu chi co the loc
   - Huu ich khi user hoi "loc duoc theo gi?"

3. **filter_stocks_by_criteria(stocks, criteria)**
   - Loc them sau khi screen
   - Vi du: Loc nhung co phieu co thanh khoan cao

4. **rank_stocks_by_score(stocks, ranking_method)**
   - Xep hang co phieu
   - ranking_method: "composite", "value", "growth", "quality"

## TIEU CHI SCREENING PHO BIEN:

### Financial Metrics:
- **roe**: Return on Equity (%) - Kha nang sinh loi
- **pe**: Price-to-Earnings - Dinh gia
- **pb**: Price-to-Book - Dinh gia theo so sach
- **eps**: Earnings Per Share
- **eps_growth_1y**: Tang truong EPS 1 nam
- **revenue_growth_1y**: Tang truong doanh thu
- **profit_last_4q**: Loi nhuan 4 quy gan nhat
- **net_margin**: Ty suat loi nhuan rong

### Technical Indicators:
- **rsi14**: RSI 14 ngay
- **price_growth_1w/1m**: Tang truong gia
- **price_vs_sma20/50**: Gia so voi MA
- **macd_histogram**: MACD histogram

### Trading Metrics:
- **market_cap**: Von hoa thi truong
- **avg_trading_value_20d**: Gia tri giao dich TB
- **foreign_transaction**: Giao dich nuoc ngoai

### Operators:
- `>`, `<`, `>=`, `<=`, `==`, `!=`

## LUU Y:

- Uu tien co phieu co thanh khoan cao (avg_trading_value_20d > 5)
- Khong loc qua strict -> 0 ket qua
- Su dung 2-4 tieu chi chinh, tranh qua nhieu
- Giai thich tai sao chon cac tieu chi nay

Hay tim nhung co phieu tot nhat cho user!
"""

    def __init__(self, mcp_client):
        self.mcp_client = mcp_client
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

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

            # Screen stocks (params: conditions, sort_by, ascending, limit)
            results = await self.mcp_client.call_tool(
                "screen_stocks",
                {
                    "conditions": criteria,
                    "sort_by": "avg_trading_value_20d",
                    "ascending": False,
                    "limit": 20
                }
            )

            if shared_state is not None:
                shared_state["screening_results"] = results

            # Format and yield results
            formatted = self._format_results(results, criteria)

            # If no results found, try with relaxed criteria or fallback
            if "Khong tim thay" in formatted or results.get("status") != "success":
                yield "Dang thu voi tieu chi rong hon...\n"
                # Try with empty/relaxed criteria for top stocks by liquidity
                fallback_results = await self.mcp_client.call_tool(
                    "screen_stocks",
                    {
                        "conditions": {},  # Empty = get all, sorted by trading value
                        "sort_by": "avg_trading_value_20d",
                        "ascending": False,
                        "limit": 20
                    }
                )

                if fallback_results.get("status") == "success" and fallback_results.get("results"):
                    formatted = self._format_results(fallback_results, {"thanh_khoan": "cao nhat"})
                    yield formatted
                else:
                    # Ultimate fallback - recommend default blue chips
                    yield self._get_default_recommendations(user_query)
            else:
                yield formatted

        except Exception as e:
            # Fallback when API fails
            yield f"[WARNING] Khong the ket noi API sang loc. Dua ra khuyen nghi mac dinh.\n\n"
            yield self._get_default_recommendations(user_query)

    def _get_default_recommendations(self, user_query: str) -> str:
        """Return default stock recommendations when screening fails"""
        query_lower = user_query.lower()

        # Determine category from query
        if any(kw in query_lower for kw in ["ngan hang", "bank", "tài chính", "tai chinh"]):
            stocks = [
                ("VCB", "Vietcombank", "Ngan hang lon nhat"),
                ("TCB", "Techcombank", "Tang truong manh"),
                ("MBB", "MB Bank", "Hieu qua cao"),
                ("ACB", "ACB", "On dinh"),
                ("BID", "BIDV", "Quy mo lon")
            ]
            category = "Ngan hang"
        elif any(kw in query_lower for kw in ["bat dong san", "bds", "địa ốc", "dia oc"]):
            stocks = [
                ("VHM", "Vinhomes", "BDS lon nhat"),
                ("VIC", "Vingroup", "Tap doan da nganh"),
                ("NVL", "Novaland", "BDS tiem nang"),
                ("KDH", "Khang Dien", "BDS TP.HCM"),
                ("DXG", "Dat Xanh", "BDS pho thong")
            ]
            category = "Bat dong san"
        elif any(kw in query_lower for kw in ["cong nghe", "tech", "it", "phần mềm", "phan mem"]):
            stocks = [
                ("FPT", "FPT Corp", "Cong nghe hang dau"),
                ("CMG", "CMC Group", "IT services"),
                ("ELC", "Elcom", "Cong nghe vien thong"),
            ]
            category = "Cong nghe"
        else:
            # Default blue chips
            stocks = [
                ("VCB", "Vietcombank", "Blue chip ngan hang"),
                ("FPT", "FPT Corp", "Blue chip cong nghe"),
                ("VNM", "Vinamilk", "Blue chip tieu dung"),
                ("HPG", "Hoa Phat", "Blue chip thep"),
                ("VIC", "Vingroup", "Blue chip BDS"),
                ("MWG", "The Gioi Di Dong", "Blue chip ban le"),
                ("GAS", "PV Gas", "Blue chip nang luong"),
                ("MSN", "Masan", "Blue chip tieu dung"),
                ("TCB", "Techcombank", "Blue chip ngan hang"),
                ("VHM", "Vinhomes", "Blue chip BDS")
            ]
            category = "Blue chip"

        output = [f"**Top co phieu {category} duoc khuyen nghi:**\n"]

        for i, (ticker, name, note) in enumerate(stocks[:10], 1):
            output.append(f"{i}. **{ticker}** - {name}")
            output.append(f"   - {note}\n")

        output.append("\n**Luu y:** Day la khuyen nghi mac dinh khi API khong kha dung.")
        output.append("Su dung lenh phan tich de xem chi tiet tung co phieu.")

        return "\n".join(output)

    async def _parse_criteria(self, user_query: str) -> Dict[str, str]:
        """Parse screening criteria from natural language query"""
        # Use OpenAI to parse criteria
        prompt = f"""
Phan tich yeu cau sau va tra ve tieu chi sang loc duoi dang JSON:

User query: "{user_query}"

Tra ve format:
{{
    "roe": ">15",
    "pe": "<15",
    ...
}}

Chi tra ve JSON, khong giai thich.
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a JSON parser. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        return json.loads(response.choices[0].message.content)

    def _format_results(self, results: Dict, criteria: Dict) -> str:
        """Format screening results for output"""
        if results.get("status") != "success":
            return f"[ERROR] {results.get('message', 'Unknown error')}"

        stocks = results.get("results", [])
        if not stocks:
            return "Khong tim thay co phieu phu hop voi tieu chi."

        # Build output
        output = ["**Ket qua sang loc**\n"]

        # Show criteria
        output.append("**Tieu chi:**")
        for key, value in criteria.items():
            output.append(f"- {key} {value}")

        output.append(f"\n**Tim thay: {len(stocks)} co phieu**\n")

        # Show top picks
        output.append("**Top khuyen nghi:**\n")

        for i, stock in enumerate(stocks[:10], 1):
            ticker = stock.get("ticker", "N/A")
            exchange = stock.get("exchange", "N/A")
            industry = stock.get("industry", "N/A")

            output.append(
                f"{i}. **{ticker}** ({exchange}) - {industry}\n"
                f"   - Cac chi so: [Hien thi tu data]\n"
            )

        output.append("\n**Luu y:** Day la ket qua sang loc dinh luong.")

        return "\n".join(output)

    def get_stats(self) -> Dict:
        return self.stats.copy()
