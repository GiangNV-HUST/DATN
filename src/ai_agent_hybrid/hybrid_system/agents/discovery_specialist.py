"""
Discovery Specialist Agent

Specialized in discovering potential stocks combining:
- Web search for market trends and potential picks
- Quantitative data from TCBS
- AI-powered analysis and recommendation

Based on OLD system's stock_discovery_agent.py pattern.
Updated: Now uses OpenAI instead of Gemini for consistency.
"""

import os
import sys
import json
from typing import Dict, List, Optional, AsyncIterator

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'ai_agent_mcp'))

from openai import OpenAI


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
Ban la chuyen gia tim kiem co phieu tiem nang tren thi truong Viet Nam.

## NHIEM VU CUA BAN:

Tim kiem va de xuat co phieu tiem nang bang cach ket hop:
1. **Web Research**: Tin tuc, xu huong, khuyen nghi tu chuyen gia
2. **Quantitative Data**: Du lieu chi tiet tu TCBS (70+ chi so)
3. **AI Analysis**: Phan tich va tong hop

## TOOLS CUA BAN (5 tools):

1. **discover_stocks_by_profile(investment_profile, num_stocks)**
   - AI-powered discovery dua tren investment profile
   - Tra ve: Danh sach co phieu phu hop voi profile

2. **search_potential_stocks(criteria, sector, market_trend)**
   - Tim kiem co phieu tiem nang
   - criteria: "growth", "value", "momentum", "quality"
   - sector: Optional nganh cu the

3. **get_stock_details_from_tcbs(symbols)**
   - Lay du lieu chi tiet tu TCBS (70+ truong)
   - Bao gom: Valuation, Growth, Profitability, Liquidity, ...

4. **gemini_search_and_summarize(query, use_search)**
   - Tim kiem web ve co phieu tiem nang
   - Vi du: "co phieu tiem nang 2025", "blue chip dang mua"

5. **get_stock_data(symbols, lookback_days)**
   - Validate va lay price data

## NGUYEN TAC:

- Luon ket hop web research + quantitative data
- Extract it nhat 10 symbols, recommend 3-5
- Giai thich TAI SAO co phieu nay tiem nang
- Validate voi TCBS data
- Uu tien co phieu co thanh khoan cao

Hay tim nhung co phieu thuc su tiem nang!
"""

    def __init__(self, mcp_client):
        """
        Initialize Discovery Specialist

        Args:
            mcp_client: EnhancedMCPClient or DirectMCPClient instance
        """
        self.mcp_client = mcp_client
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

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
            # Determine candidate stocks based on query/profile
            yield "Dang phan tich yeu cau tim kiem...\n"
            candidate_symbols = self._get_candidate_symbols(user_query, investment_profile)

            yield f"[OK] Danh sach ung vien: {len(candidate_symbols)} co phieu\n"

            # Step 1: Try discover_stocks_by_profile tool first
            profile_results = None
            try:
                if investment_profile:
                    profile_results = await self.mcp_client.call_tool(
                        "discover_stocks_by_profile",
                        {
                            "investment_profile": investment_profile,
                            "num_stocks": num_stocks * 2
                        }
                    )
                    if profile_results.get("status") == "success":
                        discovered = profile_results.get("stocks", [])
                        if discovered:
                            candidate_symbols = discovered + candidate_symbols
            except (ValueError, Exception):
                pass  # Tool not available

            # Step 2: Get price data for validation
            yield "Dang lay du lieu gia...\n"
            price_data = await self.mcp_client.call_tool(
                "get_stock_data",
                {"symbols": candidate_symbols[:10], "lookback_days": 30}
            )

            # Step 3: Get prediction data
            yield "Dang lay du doan gia...\n"
            prediction_data = None
            try:
                prediction_data = await self.mcp_client.call_tool(
                    "get_stock_price_prediction",
                    {"symbols": candidate_symbols[:10], "table_type": "3d"}
                )
            except Exception:
                pass

            # Step 4: Analyze and rank using AI
            yield "Dang phan tich va xep hang...\n"
            ranked_stocks = await self._analyze_and_rank_direct(
                symbols=candidate_symbols[:10],
                price_data=price_data,
                prediction_data=prediction_data,
                user_query=user_query,
                num_recommendations=num_stocks
            )

            if shared_state is not None:
                shared_state["discovered_stocks"] = ranked_stocks

            # Step 5: Format and yield results
            yield "\n" + "="*50 + "\n"
            yield "**CO PHIEU TIEM NANG**\n"
            yield "="*50 + "\n\n"

            formatted = self._format_discovery_results(
                ranked_stocks=ranked_stocks,
                web_summary="Phan tich dua tren du lieu thi truong hien tai",
                total_found=len(candidate_symbols)
            )

            yield formatted

        except Exception as e:
            yield f"\n[ERROR] Loi khi tim kiem co phieu: {str(e)}"
            yield "\n**Khuyen nghi mac dinh:**\n"
            yield self._get_default_recommendations(user_query)

    def _get_candidate_symbols(self, user_query: str, profile: Optional[Dict]) -> List[str]:
        """Get candidate stock symbols based on query/profile"""
        query_lower = user_query.lower()

        # Default blue chips
        default_stocks = ["VCB", "FPT", "VNM", "HPG", "VIC", "MWG", "GAS", "MSN", "TCB", "VHM"]

        # Sector-specific
        if any(kw in query_lower for kw in ["ngan hang", "bank", "tai chinh"]):
            return ["VCB", "TCB", "MBB", "ACB", "BID", "CTG", "STB", "HDB", "VPB", "TPB"]
        elif any(kw in query_lower for kw in ["bat dong san", "bds", "dia oc"]):
            return ["VHM", "VIC", "NVL", "KDH", "DXG", "HDG", "PDR", "NLG", "DIG", "CEO"]
        elif any(kw in query_lower for kw in ["cong nghe", "tech", "it"]):
            return ["FPT", "CMG", "ELC", "CTR", "VGI"]
        elif any(kw in query_lower for kw in ["thep", "xay dung", "vat lieu"]):
            return ["HPG", "HSG", "NKG", "TLH", "VGC", "CTD", "HBC", "VCG", "FCN", "HUT"]
        elif any(kw in query_lower for kw in ["dien", "nang luong", "energy"]):
            return ["GAS", "POW", "PVD", "PVS", "PLX", "BSR", "OIL", "PVC", "PVT", "REE"]
        elif any(kw in query_lower for kw in ["tieu dung", "ban le", "retail"]):
            return ["VNM", "MWG", "MSN", "PNJ", "DGW", "FRT", "HAX", "VGT", "SAB", "BHN"]

        # Profile-based
        if profile:
            risk = profile.get("risk_tolerance", "medium")
            if risk == "low":
                return ["VCB", "VNM", "GAS", "FPT", "BID", "CTG", "HPG", "VIC", "PNJ", "REE"]
            elif risk == "high":
                return ["FPT", "MWG", "TCB", "VHM", "HPG", "MBB", "VPB", "STB", "VIC", "NVL"]

        return default_stocks

    async def _analyze_and_rank_direct(
        self,
        symbols: List[str],
        price_data: Dict,
        prediction_data: Optional[Dict],
        user_query: str,
        num_recommendations: int
    ) -> List[Dict]:
        """Analyze and rank stocks using AI without web search"""
        # Build analysis prompt
        prompt = f"""
Dua tren du lieu sau, hay xep hang va chon top {num_recommendations} co phieu tiem nang nhat:

**Yeu cau cua user:** {user_query}

**Du lieu gia (30 ngay):**
{str(price_data)[:2000]}

**Du doan gia (3 ngay toi):**
{str(prediction_data)[:1000] if prediction_data else "Khong co du lieu du doan"}

**Cac symbols can phan tich:** {symbols}

Hay phan tich va tra ve JSON format:
{{
    "stocks": [
        {{
            "symbol": "VCB",
            "rank": 1,
            "score": 9.5,
            "reasons": ["reason1", "reason2", "reason3"],
            "fundamentals_summary": "Ngan hang lon nhat, ROE cao, tang truong on dinh",
            "technical_summary": "RSI = 60, xu huong tang, gia tren MA20"
        }},
        ...
    ]
}}

Danh gia dua tren: xu huong gia, chi so ky thuat, tiem nang tang truong, do an toan.
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a Vietnamese stock analyst. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        return result.get("stocks", [])

    def _get_default_recommendations(self, user_query: str) -> str:
        """Return default recommendations when discovery fails"""
        query_lower = user_query.lower()

        if any(kw in query_lower for kw in ["ngan hang", "bank"]):
            stocks = ["VCB - Vietcombank (Blue chip)", "TCB - Techcombank (Tang truong)", "MBB - MB Bank (Hieu qua)"]
        elif any(kw in query_lower for kw in ["cong nghe", "tech"]):
            stocks = ["FPT - FPT Corp (Cong nghe hang dau)", "CMG - CMC Group (IT services)"]
        else:
            stocks = [
                "VCB - Blue chip ngan hang",
                "FPT - Blue chip cong nghe",
                "VNM - Blue chip tieu dung",
                "HPG - Blue chip thep",
                "VIC - Blue chip bat dong san"
            ]

        return "\n".join([f"- {s}" for s in stocks])

    def _build_search_query(self, user_query: str, profile: Optional[Dict]) -> str:
        """Build search query based on user request and profile"""
        base_query = user_query

        if profile:
            risk = profile.get("risk_tolerance", "medium")
            horizon = profile.get("time_horizon", "medium")

            if risk == "low":
                base_query += " blue chip on dinh"
            elif risk == "high":
                base_query += " tang truong cao"

            if horizon == "long":
                base_query += " dai han"

        return base_query + " Viet Nam 2025"

    async def _extract_symbols_from_results(self, web_results: Dict) -> List[str]:
        """Extract stock symbols from web search results using AI"""
        prompt = f"""
Phan tich ket qua search sau va trich xuat TAT CA cac ma co phieu duoc nhac den:

{web_results.get("summary", "")}

Tra ve danh sach ma co phieu duoi dang JSON array:
{{"symbols": ["VCB", "FPT", ...]}}

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

        result = json.loads(response.choices[0].message.content)
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
        # Use OpenAI to analyze and rank
        prompt = f"""
Dua tren du lieu sau, hay xep hang va chon top {num_recommendations} co phieu tiem nang:

**Web Research:**
{web_results.get("summary", "")}

**TCBS Data:**
{str(tcbs_data)[:2000]}

**Price Data:**
{str(price_data)[:1000]}

Tra ve JSON format:
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

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a stock analyst. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        return result.get("stocks", [])

    def _format_discovery_results(
        self,
        ranked_stocks: List[Dict],
        web_summary: str,
        total_found: int
    ) -> str:
        """Format discovery results for output"""
        output = []

        output.append(f"**Nguon tim kiem:**")
        output.append(f"- Web research: {total_found} co phieu duoc nhac den")
        output.append(f"- Final picks: Top {len(ranked_stocks)} khuyen nghi\n")

        output.append("**TOP KHUYEN NGHI:**\n")

        for stock in ranked_stocks:
            symbol = stock.get("symbol", "N/A")
            rank = stock.get("rank", 0)
            score = stock.get("score", 0)
            reasons = stock.get("reasons", [])

            stars = "*" * min(5, int(score))

            output.append(f"**{rank}. {symbol}** {stars}")
            output.append(f"**Diem: {score}/10**\n")

            output.append("**Ly do:**")
            for reason in reasons:
                output.append(f"- {reason}")

            output.append(f"\n**Fundamentals:** {stock.get('fundamentals_summary', 'N/A')}")
            output.append(f"**Technical:** {stock.get('technical_summary', 'N/A')}\n")
            output.append("---\n")

        output.append("\n**Luu y:** Day la ket qua phan tich tu dong, can nghien cuu them truoc khi dau tu.")

        return "\n".join(output)

    def get_stats(self) -> Dict:
        """Get discovery statistics"""
        return self.stats.copy()
