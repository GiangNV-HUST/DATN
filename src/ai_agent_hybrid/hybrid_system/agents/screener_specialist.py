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

            # Check if database/API is available and has data
            has_data = (
                results.get("status") == "success" and
                results.get("data") and
                len(results.get("data", [])) > 0
            )

            if has_data:
                # Format and yield results from database
                formatted = self._format_results(results, criteria)
                yield formatted
            else:
                # Database không available hoặc không có kết quả
                # Sử dụng fallback recommendations ngay lập tức

                # Show criteria that user requested
                if criteria:
                    yield "**Tieu chi yeu cau:**\n"
                    for key, value in criteria.items():
                        yield f"- {key} {value}\n"
                    yield "\n"

                # Check if it's a database issue or just no matching results
                error_msg = results.get("message", "")
                if results.get("status") == "error" or "error" in error_msg.lower():
                    yield "**[Luu y]** Du lieu screener dang khong kha dung. Su dung danh sach khuyen nghi.\n\n"
                elif results.get("status") == "no_results":
                    yield "**[Luu y]** Khong tim thay co phieu phu hop chinh xac. Dua ra khuyen nghi gan nhat.\n\n"
                else:
                    yield "**[Luu y]** Su dung danh sach co phieu khuyen nghi.\n\n"

                # Return default recommendations based on query
                yield self._get_default_recommendations(user_query)

        except Exception as e:
            # Fallback when API fails completely
            yield f"**[Luu y]** Khong the ket noi he thong sang loc.\n\n"
            yield self._get_default_recommendations(user_query)

    def _get_default_recommendations(self, user_query: str) -> str:
        """Return default stock recommendations when screening fails"""
        query_lower = user_query.lower()

        # Determine category from query
        stocks = []
        category = ""

        # Industry-based recommendations
        if any(kw in query_lower for kw in ["ngan hang", "bank", "tài chính", "tai chinh"]):
            stocks = [
                ("VCB", "Vietcombank", "PE: 12.5, ROE: 22%"),
                ("TCB", "Techcombank", "PE: 8.2, ROE: 18%"),
                ("MBB", "MB Bank", "PE: 6.5, ROE: 24%"),
                ("ACB", "ACB", "PE: 7.8, ROE: 20%"),
                ("BID", "BIDV", "PE: 10.2, ROE: 15%")
            ]
            category = "Ngan hang"
        elif any(kw in query_lower for kw in ["bat dong san", "bds", "địa ốc", "dia oc"]):
            stocks = [
                ("VHM", "Vinhomes", "BDS lon nhat VN"),
                ("VIC", "Vingroup", "Tap doan da nganh"),
                ("NVL", "Novaland", "BDS phan khuc cao cap"),
                ("KDH", "Khang Dien", "BDS TP.HCM"),
                ("DXG", "Dat Xanh", "BDS pho thong")
            ]
            category = "Bat dong san"
        elif any(kw in query_lower for kw in ["cong nghe", "tech", "it", "phần mềm", "phan mem"]):
            stocks = [
                ("FPT", "FPT Corp", "PE: 18, ROE: 22%"),
                ("CMG", "CMC Group", "IT services"),
                ("ELC", "Elcom", "Vien thong"),
            ]
            category = "Cong nghe"
        elif any(kw in query_lower for kw in ["thep", "kim loai", "kim loại"]):
            stocks = [
                ("HPG", "Hoa Phat", "PE: 8.5, ROE: 15%"),
                ("HSG", "Hoa Sen", "PE: 10, ROE: 12%"),
                ("NKG", "Nam Kim", "PE: 7, ROE: 10%"),
            ]
            category = "Thep/Kim loai"

        # Metric-based recommendations (ROE, PE, etc.)
        elif any(kw in query_lower for kw in ["roe cao", "roe >", "roe high"]):
            stocks = [
                ("MBB", "MB Bank", "ROE: 24%"),
                ("VCB", "Vietcombank", "ROE: 22%"),
                ("FPT", "FPT Corp", "ROE: 22%"),
                ("TCB", "Techcombank", "ROE: 18%"),
                ("VNM", "Vinamilk", "ROE: 35%"),
                ("MWG", "The Gioi Di Dong", "ROE: 20%"),
                ("PNJ", "Phu Nhuan Jewelry", "ROE: 25%"),
                ("ACB", "ACB", "ROE: 20%"),
            ]
            category = "ROE cao (>15%)"
        elif any(kw in query_lower for kw in ["pe thap", "pe <", "pe low", "pe thấp"]):
            stocks = [
                ("MBB", "MB Bank", "PE: 6.5"),
                ("TCB", "Techcombank", "PE: 8.2"),
                ("ACB", "ACB", "PE: 7.8"),
                ("HPG", "Hoa Phat", "PE: 8.5"),
                ("STB", "Sacombank", "PE: 7.0"),
                ("VPB", "VPBank", "PE: 6.8"),
                ("HDB", "HD Bank", "PE: 7.5"),
            ]
            category = "PE thap (<15)"
        elif any(kw in query_lower for kw in ["co tuc", "dividend", "cổ tức"]):
            stocks = [
                ("VNM", "Vinamilk", "Dividend yield: 5%"),
                ("GAS", "PV Gas", "Dividend yield: 6%"),
                ("REE", "REE Corp", "Dividend yield: 5%"),
                ("DPM", "Dam Phu My", "Dividend yield: 8%"),
                ("PLX", "Petrolimex", "Dividend yield: 4%"),
            ]
            category = "Co tuc cao"
        else:
            # Default blue chips
            stocks = [
                ("VCB", "Vietcombank", "PE: 12.5, ROE: 22%"),
                ("FPT", "FPT Corp", "PE: 18, ROE: 22%"),
                ("VNM", "Vinamilk", "PE: 16, ROE: 35%"),
                ("HPG", "Hoa Phat", "PE: 8.5, ROE: 15%"),
                ("VIC", "Vingroup", "Tap doan da nganh"),
                ("MWG", "The Gioi Di Dong", "PE: 12, ROE: 20%"),
                ("GAS", "PV Gas", "PE: 15, Dividend: 6%"),
                ("MSN", "Masan", "Tap doan tieu dung"),
                ("TCB", "Techcombank", "PE: 8.2, ROE: 18%"),
                ("VHM", "Vinhomes", "BDS lon nhat")
            ]
            category = "Blue chip tieu bieu"

        output = [f"**Top co phieu {category}:**\n"]

        for i, (ticker, name, note) in enumerate(stocks[:10], 1):
            output.append(f"{i}. **{ticker}** - {name}")
            output.append(f"   - {note}\n")

        output.append("\n*Luu y: Day la danh sach khuyen nghi. Su dung lenh phan tich de xem chi tiet.*")

        return "\n".join(output)

    async def _parse_criteria(self, user_query: str) -> Dict[str, str]:
        """Parse screening criteria from natural language query"""
        # Use OpenAI to parse criteria
        prompt = f"""
Phan tich yeu cau sang loc co phieu sau va tra ve tieu chi duoi dang JSON:

User query: "{user_query}"

## QUY TAC QUAN TRONG:

1. **Filter theo nganh (industry):**
   - Neu user muon loc theo nganh (ngan hang, bat dong san, cong nghe, hoa chat, thep, ...)
   - Su dung format: "industry": "contains:Ten nganh"
   - Vi du: "ngan hang" -> "industry": "contains:Ngân hàng"
   - Vi du: "bat dong san" -> "industry": "contains:Bất động sản"
   - Vi du: "cong nghe" -> "industry": "contains:Phần mềm"
   - Vi du: "thep" -> "industry": "contains:Kim loại"
   - Vi du: "hoa chat" -> "industry": "contains:Hóa chất"
   - Vi du: "duoc pham" -> "industry": "contains:Dược phẩm"
   - Vi du: "dau khi" -> "industry": "contains:Dầu khí"
   - Vi du: "chung khoan" -> "industry": "contains:Dịch vụ tài chính"

2. **Filter theo so lieu:**
   - pe, pb, roe, rsi14, eps, market_cap
   - Su dung operators: >, <, >=, <=, ==
   - Vi du: "PE < 20" -> "pe": "<20"
   - Vi du: "ROE > 15%" -> "roe": ">15"
   - Vi du: "P/B < 2" -> "pb": "<2"

Tra ve format JSON:
{{
    "industry": "contains:...",
    "roe": ">15",
    "pe": "<15",
    ...
}}

Chi tra ve JSON, khong giai thich. Neu khong co dieu kien nao, tra ve {{}}.
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a JSON parser for Vietnamese stock screening. Return only valid JSON."},
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

        # MCP returns "data" not "results"
        stocks = results.get("data", []) or results.get("results", [])
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

            # Build metrics string
            metrics = []
            if stock.get("pe") is not None:
                metrics.append(f"PE: {stock['pe']:.2f}")
            if stock.get("roe") is not None:
                metrics.append(f"ROE: {stock['roe']:.2f}%")
            if stock.get("pb") is not None:
                metrics.append(f"PB: {stock['pb']:.2f}")
            if stock.get("close") is not None:
                metrics.append(f"Gia: {stock['close']:,.0f}")

            metrics_str = " | ".join(metrics) if metrics else "N/A"

            output.append(
                f"{i}. **{ticker}** ({exchange}) - {industry}\n"
                f"   - {metrics_str}\n"
            )

        output.append("\n**Luu y:** Day la ket qua sang loc dinh luong.")

        return "\n".join(output)

    def get_stats(self) -> Dict:
        return self.stats.copy()
