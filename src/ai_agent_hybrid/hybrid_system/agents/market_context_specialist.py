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
        """Get index data using proxy symbols or estimation"""
        try:
            from vnstock import Vnstock
            import asyncio

            def _sync_fetch():
                results = {}

                # Try to get VN30 ETF as proxy for VN-Index
                try:
                    stock = Vnstock().stock(symbol='E1VFVN30', source='VCI')
                    today = datetime.now().strftime('%Y-%m-%d')
                    yesterday = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
                    history = stock.quote.history(start=yesterday, end=today)

                    if history is not None and not history.empty:
                        latest = history.iloc[-1].to_dict()
                        prev = history.iloc[-2].to_dict() if len(history) > 1 else latest

                        change = latest.get('close', 0) - prev.get('close', 0)
                        change_pct = (change / prev.get('close', 1)) * 100 if prev.get('close') else 0

                        results['VN30_ETF'] = {
                            'close': latest.get('close'),
                            'change': round(change, 2),
                            'change_pct': round(change_pct, 2),
                            'volume': latest.get('volume'),
                            'note': 'Proxy for VN-Index trend'
                        }
                except Exception as e:
                    results['VN30_ETF'] = {'error': str(e)}

                # Get major bank stocks as market proxy
                major_symbols = ['VCB', 'TCB', 'FPT', 'VNM', 'VHM']
                try:
                    for sym in major_symbols[:3]:
                        stock = Vnstock().stock(symbol=sym, source='VCI')
                        today = datetime.now().strftime('%Y-%m-%d')
                        yesterday = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
                        history = stock.quote.history(start=yesterday, end=today)

                        if history is not None and not history.empty:
                            latest = history.iloc[-1].to_dict()
                            prev = history.iloc[-2].to_dict() if len(history) > 1 else latest

                            change = latest.get('close', 0) - prev.get('close', 0)
                            change_pct = (change / prev.get('close', 1)) * 100 if prev.get('close') else 0

                            results[sym] = {
                                'close': latest.get('close'),
                                'change': round(change, 2),
                                'change_pct': round(change_pct, 2)
                            }
                except Exception as e:
                    pass

                return results

            return await asyncio.to_thread(_sync_fetch)

        except Exception as e:
            return {"error": str(e)}

    async def get_sector_performance(self) -> Dict:
        """
        Get performance by industry sector

        Returns:
            Dict with sector performance data
        """
        try:
            # Define major sectors and their representative stocks
            sectors = {
                "Ngan hang": ["VCB", "TCB", "MBB", "BID", "CTG", "ACB", "VPB", "STB", "HDB", "TPB"],
                "Bat dong san": ["VHM", "VIC", "NVL", "KDH", "DXG", "NLG", "PDR", "DIG", "CEO", "LDG"],
                "Cong nghe": ["FPT", "CMG", "ELC", "SAM"],
                "Thep": ["HPG", "HSG", "NKG", "SMC", "TLH"],
                "Dau khi": ["GAS", "PLX", "PVD", "PVS", "BSR"],
                "Thuc pham": ["VNM", "MSN", "SAB", "QNS", "MCH"],
                "Dien": ["POW", "REE", "PC1", "GEG", "NT2"],
                "Chung khoan": ["SSI", "VCI", "HCM", "VND", "SHS"]
            }

            sector_results = {}

            for sector_name, symbols in sectors.items():
                # Get data for sector stocks
                sector_data = await self.mcp_client.call_tool(
                    "get_stock_details_from_tcbs",
                    {"symbols": symbols[:5]}  # Top 5 per sector
                )

                if sector_data.get("status") == "success":
                    stocks = sector_data.get("data", [])

                    # Calculate average sector change
                    changes = [s.get("change_percent_1d", 0) or 0 for s in stocks]
                    avg_change = sum(changes) / len(changes) if changes else 0

                    # Get top performers in sector
                    sorted_stocks = sorted(stocks, key=lambda x: x.get("change_percent_1d", 0) or 0, reverse=True)

                    sector_results[sector_name] = {
                        "avg_change_pct": round(avg_change, 2),
                        "top_gainer": sorted_stocks[0].get("ticker") if sorted_stocks else None,
                        "top_gainer_change": sorted_stocks[0].get("change_percent_1d") if sorted_stocks else None,
                        "top_loser": sorted_stocks[-1].get("ticker") if sorted_stocks else None,
                        "top_loser_change": sorted_stocks[-1].get("change_percent_1d") if sorted_stocks else None,
                        "stocks_count": len(stocks)
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

        try:
            # Gather market data
            market_overview = await self.get_market_overview()
            sector_performance = await self.get_sector_performance()
            top_movers = await self.get_market_top_movers()

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

**Top Movers:**
{top_movers}

Hay phan tich va tra loi theo format:
1. Tong quan thi truong (chi so chinh, market breadth)
2. Nganh noi bat (tang/giam manh)
3. Co phieu dang chu y
4. Danh gia xu huong va tam ly thi truong
5. Khuyen nghi tong quan
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
