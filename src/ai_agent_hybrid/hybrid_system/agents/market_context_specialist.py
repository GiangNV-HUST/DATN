"""
Market Context Specialist Agent

Provides market overview and context including:
- Index data (VN-Index, HNX-Index, UPCOM-Index)
- Market breadth (advancing vs declining stocks)
- Sector performance
- Market sentiment

This agent helps answer questions about the overall market,
not specific individual stocks.
"""

import os
import sys
from typing import Dict, List, Optional, AsyncIterator
from openai import OpenAI
import asyncio
from datetime import datetime, timedelta

# Add ai_agent_mcp to path for MCP client
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'ai_agent_mcp'))


class MarketContextSpecialist:
    """
    Specialist for market overview and context

    Provides:
    - Index performance (VN-Index, HNX-Index, UPCOM)
    - Market breadth (advancing/declining/unchanged)
    - Sector performance
    - Market sentiment indicators

    Tools (4):
    - get_market_overview: Overall market indices and breadth
    - get_sector_performance: Performance by industry sectors
    - get_market_top_movers: Top gainers, losers, volume leaders
    - screen_stocks: For market breadth calculations
    """

    AGENT_INSTRUCTION = """
Ban la chuyen gia phan tich thi truong chung khoan Viet Nam voi kha nang:
- Cung cap thong tin tong quan ve thi truong (VN-Index, HNX-Index, UPCOM)
- Phan tich market breadth (so ma tang/giam/dung gia)
- Phan tich hieu suat nganh (banking, real estate, technology, ...)
- Danh gia tam ly thi truong

## TOOLS CUA BAN:

1. **get_market_overview()**
   - Lay du lieu chi so chinh: VN-Index, HNX-Index
   - Market breadth: so ma tang, giam, dung gia
   - Foreign flow (khoi ngoai mua/ban rong)

2. **get_sector_performance()**
   - Hieu suat theo nganh: Ngan hang, Bat dong san, Cong nghe, ...
   - Top nganh tang/giam trong phien

3. **get_market_top_movers()**
   - Top 10 co phieu tang manh nhat
   - Top 10 co phieu giam manh nhat
   - Top 10 co phieu thanh khoan cao nhat

4. **screen_stocks(conditions, sort_by, limit)**
   - Loc co phieu de tinh market breadth
   - Loc theo nganh cu the

## OUTPUT FORMAT:

### Market Overview:
- **VN-Index:** 1,280.5 (+12.3 | +0.97%)
- **HNX-Index:** 245.8 (+2.1 | +0.86%)
- **Market Breadth:** 250 tang / 180 giam / 70 dung gia
- **Foreign Flow:** Mua rong 150 ty VND

### Sector Performance:
| Nganh | Thay doi | Top co phieu |
|-------|---------|--------------|
| Ngan hang | +1.5% | VCB, TCB, MBB |
| Bat dong san | -0.8% | VHM, VIC, NVL |

### Danh gia:
- Xu huong ngan han: Tang/Giam/Di ngang
- Tam ly thi truong: Tich cuc/Tieu cuc/Trung tinh
- Khuyen nghi: [Danh gia tong quan]

Hay cung cap cai nhin tong quan, chinh xac ve thi truong!
"""

    def __init__(self, mcp_client):
        """
        Initialize Market Context Specialist

        Args:
            mcp_client: EnhancedMCPClient or DirectMCPClient instance
        """
        self.mcp_client = mcp_client
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        # Statistics
        self.stats = {
            "total_queries": 0,
            "index_queries": 0,
            "sector_queries": 0,
            "breadth_queries": 0
        }

    async def get_market_overview(self) -> Dict:
        """
        Get overall market overview including indices and breadth

        Returns:
            Dict with market overview data
        """
        try:
            # Use screen_stocks to calculate market breadth
            # Get all stocks first
            all_stocks_result = await self.mcp_client.call_tool(
                "screen_stocks",
                {"conditions": {}, "sort_by": "avg_trading_value_20d", "limit": 500}
            )

            if all_stocks_result.get("status") != "success":
                return {"status": "error", "message": "Cannot fetch market data"}

            stocks = all_stocks_result.get("data", [])

            # Calculate market breadth
            advancing = 0
            declining = 0
            unchanged = 0

            for stock in stocks:
                change = stock.get("change_percent_1d", 0) or 0
                if change > 0:
                    advancing += 1
                elif change < 0:
                    declining += 1
                else:
                    unchanged += 1

            # Get index data (VN-Index symbol approximation using ETF E1VFVN30)
            # Note: vnstock doesn't directly support index data, so we use proxy
            index_data = await self._get_index_data()

            return {
                "status": "success",
                "indices": index_data,
                "market_breadth": {
                    "advancing": advancing,
                    "declining": declining,
                    "unchanged": unchanged,
                    "total": len(stocks),
                    "advance_decline_ratio": round(advancing / declining, 2) if declining > 0 else advancing
                },
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _get_index_data(self) -> Dict:
        """Get index data from database instead of vnstock API to avoid rate limiting"""
        try:
            # Use data from database instead of vnstock API calls
            # This is much faster and doesn't have rate limits
            major_symbols = ['VCB', 'TCB', 'FPT', 'VNM', 'HPG']

            details_result = await self.mcp_client.call_tool(
                "get_stock_details_from_tcbs",
                {"symbols": major_symbols}
            )

            results = {}

            if details_result.get("status") == "success":
                for stock in details_result.get("data", []):
                    ticker = stock.get("ticker")
                    if ticker:
                        results[ticker] = {
                            'close': stock.get('close'),
                            'change': stock.get('change_1d'),
                            'change_pct': stock.get('change_percent_1d'),
                            'volume': stock.get('avg_volume_20d')
                        }

            # Add market breadth note
            results['note'] = 'Using major stocks as market proxy (VCB, TCB, FPT, VNM, HPG)'

            return results

        except Exception as e:
            return {"error": str(e)}

    async def get_sector_performance(self, sectors_filter: List[str] = None) -> Dict:
        """
        Get performance by industry sector - OPTIMIZED to use single API call

        Args:
            sectors_filter: Optional list of specific sectors to check

        Returns:
            Dict with sector performance data
        """
        try:
            # Define major sectors and their representative stocks (reduced to 3 per sector)
            sectors = {
                "Ngan hang": ["VCB", "TCB", "MBB"],
                "Bat dong san": ["VHM", "VIC", "NVL"],
                "Cong nghe": ["FPT", "CMG", "ELC"],
                "Thep": ["HPG", "HSG", "NKG"],
                "Dau khi": ["GAS", "PLX", "PVD"],
                "Thuc pham": ["VNM", "MSN", "SAB"],
                "Dien": ["POW", "REE", "PC1"],
                "Chung khoan": ["SSI", "VCI", "HCM"]
            }

            # Filter sectors if specified
            if sectors_filter:
                sectors = {k: v for k, v in sectors.items()
                          if any(sf.lower() in k.lower() for sf in sectors_filter)}

            # Collect ALL symbols and make ONE API call
            all_symbols = []
            symbol_to_sector = {}
            for sector_name, symbols in sectors.items():
                for sym in symbols:
                    all_symbols.append(sym)
                    symbol_to_sector[sym] = sector_name

            # SINGLE API call for all symbols
            all_data = await self.mcp_client.call_tool(
                "get_stock_details_from_tcbs",
                {"symbols": all_symbols}
            )

            sector_results = {}

            if all_data.get("status") == "success":
                stocks = all_data.get("data", [])

                # Group by sector
                sector_stocks = {}
                for stock in stocks:
                    ticker = stock.get("ticker")
                    if ticker in symbol_to_sector:
                        sector_name = symbol_to_sector[ticker]
                        if sector_name not in sector_stocks:
                            sector_stocks[sector_name] = []
                        sector_stocks[sector_name].append(stock)

                # Calculate sector metrics
                for sector_name, stocks_list in sector_stocks.items():
                    changes = [s.get("change_percent_1d", 0) or 0 for s in stocks_list]
                    avg_change = sum(changes) / len(changes) if changes else 0

                    sorted_stocks = sorted(stocks_list, key=lambda x: x.get("change_percent_1d", 0) or 0, reverse=True)

                    sector_results[sector_name] = {
                        "avg_change_pct": round(avg_change, 2),
                        "top_gainer": sorted_stocks[0].get("ticker") if sorted_stocks else None,
                        "top_gainer_change": sorted_stocks[0].get("change_percent_1d") if sorted_stocks else None,
                        "top_loser": sorted_stocks[-1].get("ticker") if sorted_stocks else None,
                        "top_loser_change": sorted_stocks[-1].get("change_percent_1d") if sorted_stocks else None,
                        "stocks_count": len(stocks_list)
                    }

            # Sort sectors by performance
            sorted_sectors = dict(sorted(
                sector_results.items(),
                key=lambda x: x[1].get("avg_change_pct", 0),
                reverse=True
            ))

            return {
                "status": "success",
                "sectors": sorted_sectors,
                "top_sector": list(sorted_sectors.keys())[0] if sorted_sectors else None,
                "worst_sector": list(sorted_sectors.keys())[-1] if sorted_sectors else None,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def get_market_top_movers(self, limit: int = 10) -> Dict:
        """
        Get top market movers (gainers, losers, volume leaders)

        Args:
            limit: Number of stocks per category

        Returns:
            Dict with top movers data
        """
        try:
            # Top gainers
            top_gainers_result = await self.mcp_client.call_tool(
                "screen_stocks",
                {
                    "conditions": {"change_percent_1d": ">0"},
                    "sort_by": "change_percent_1d",
                    "ascending": False,
                    "limit": limit
                }
            )

            # Top losers
            top_losers_result = await self.mcp_client.call_tool(
                "screen_stocks",
                {
                    "conditions": {"change_percent_1d": "<0"},
                    "sort_by": "change_percent_1d",
                    "ascending": True,
                    "limit": limit
                }
            )

            # Volume leaders
            volume_leaders_result = await self.mcp_client.call_tool(
                "screen_stocks",
                {
                    "conditions": {},
                    "sort_by": "avg_trading_value_20d",
                    "ascending": False,
                    "limit": limit
                }
            )

            return {
                "status": "success",
                "top_gainers": [
                    {"ticker": s.get("ticker"), "change_pct": s.get("change_percent_1d"), "close": s.get("close")}
                    for s in top_gainers_result.get("data", [])
                ],
                "top_losers": [
                    {"ticker": s.get("ticker"), "change_pct": s.get("change_percent_1d"), "close": s.get("close")}
                    for s in top_losers_result.get("data", [])
                ],
                "volume_leaders": [
                    {"ticker": s.get("ticker"), "trading_value": s.get("avg_trading_value_20d"), "close": s.get("close")}
                    for s in volume_leaders_result.get("data", [])
                ],
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def analyze(
        self,
        user_query: str,
        shared_state: Optional[Dict] = None
    ) -> AsyncIterator[str]:
        """
        Analyze market context based on user query

        Args:
            user_query: User's question about the market
            shared_state: Shared state for storing intermediate results

        Yields:
            Analysis chunks as they're generated
        """
        self.stats["total_queries"] += 1
        query_lower = user_query.lower()

        try:
            # Gather market data with error handling for each component
            market_overview = {"status": "unavailable", "message": "Skipped"}
            sector_performance = {"status": "unavailable", "message": "Skipped"}
            top_movers = {"status": "unavailable", "message": "Skipped"}

            # Check if user is asking about specific sectors
            sector_keywords = {
                "ngan hang": ["ngan hang", "ngân hàng", "bank"],
                "cong nghe": ["cong nghe", "công nghệ", "tech"],
                "bat dong san": ["bat dong san", "bất động sản", "bds", "real estate"],
                "thep": ["thép", "thep", "steel"],
                "dau khi": ["dầu khí", "dau khi", "oil", "gas"],
                "thuc pham": ["thực phẩm", "thuc pham", "food"],
                "dien": ["điện", "dien", "electric", "power"],
                "chung khoan": ["chứng khoán", "chung khoan", "securities"]
            }

            # Detect which sectors user is asking about
            sectors_to_check = []
            for sector, keywords in sector_keywords.items():
                if any(kw in query_lower for kw in keywords):
                    sectors_to_check.append(sector)

            # Get market overview (most important)
            try:
                market_overview = await self.get_market_overview()
            except Exception as e:
                market_overview = {"status": "error", "message": str(e)}

            # Get sector performance if user asks about sectors (now optimized - single API call)
            if sectors_to_check or any(kw in query_lower for kw in ["ngành", "nganh", "sector", "hiệu suất ngành"]):
                try:
                    # Pass specific sectors or None for all
                    sector_performance = await self.get_sector_performance(
                        sectors_filter=sectors_to_check if sectors_to_check else None
                    )
                except Exception as e:
                    sector_performance = {"status": "error", "message": str(e)}

            # Get top movers from database (fast)
            try:
                top_movers = await self.get_market_top_movers(limit=5)
            except Exception as e:
                top_movers = {"status": "error", "message": str(e)}

            # Store in shared state if provided
            if shared_state is not None:
                shared_state["market_overview"] = market_overview
                shared_state["sector_performance"] = sector_performance
                shared_state["top_movers"] = top_movers

            # Build analysis prompt
            analysis_prompt = f"""
Dua tren du lieu thi truong sau, hay tra loi cau hoi cua user:

**User Query:** {user_query}

**Market Overview:**
{market_overview}

**Sector Performance:**
{sector_performance}

**Top Movers (Tang/Giam manh, Khoi luong lon):**
{top_movers}

Hay phan tich va tra loi theo format:
1. Tong quan thi truong (chi so chinh, market breadth)
2. Hieu suat nganh (neu user hoi ve nganh)
3. Co phieu dang chu y (tang/giam manh, khoi luong lon)
4. Danh gia xu huong va tam ly thi truong
5. Khuyen nghi tong quan

**NEU USER HOI SO SANH NGANH** (vi du: ngan hang vs cong nghe):
1. So sanh hieu suat (% thay doi) cua tung nganh
2. Top co phieu dai dien cua moi nganh
3. Chi so P/E, P/B, ROE trung binh cua tung nganh (neu co)
4. Nganh nao dang hap dan hon de dau tu
5. De xuat 2-3 co phieu tot nhat MỖI NGÀNH

Neu user hoi de xuat co phieu, hay de xuat 2-3 co phieu tot nhat trong nganh do.

Luu y: Neu du lieu bi loi hoac khong co, hay thong bao cho user va dua ra phan tich chung dua tren thong tin co san.
"""

            # Generate analysis with OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.AGENT_INSTRUCTION},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.7,
                max_tokens=2048
            )

            yield response.choices[0].message.content

        except Exception as e:
            yield f"[ERROR] Loi khi phan tich thi truong: {str(e)}"

    def get_stats(self) -> Dict:
        """Get analysis statistics"""
        return self.stats.copy()
