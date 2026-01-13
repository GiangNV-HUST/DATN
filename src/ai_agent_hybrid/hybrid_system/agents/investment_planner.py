"""
Investment Planner Agent

Specialized in investment planning and portfolio management:
- Gathering investment profile
- Portfolio allocation
- Entry strategy
- Risk management
- Monitoring plan

NEW agent - khong co trong OLD system.
Updated: Now uses OpenAI instead of Gemini for consistency.
"""

import os
import sys
from typing import Dict, List, Optional, AsyncIterator

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'ai_agent_mcp'))

from openai import OpenAI


class InvestmentPlanner:
    """
    Specialist for investment planning and portfolio management

    Tools (7):
    - gather_investment_profile: Thu thap profile (risk, capital, goals)
    - calculate_portfolio_allocation: Tinh phan bo danh muc
    - generate_entry_strategy: Chien luoc vao lenh
    - generate_risk_management_plan: Quan ly rui ro
    - generate_monitoring_plan: Ke hoach giam sat
    - get_stock_data: Validate stock selections
    - get_financial_data: Analyze fundamentals

    Workflow:
    1. Gather investment profile
    2. Discover/screen suitable stocks
    3. Calculate portfolio allocation
    4. Generate entry strategy
    5. Create risk management plan
    6. Setup monitoring plan
    """

    AGENT_INSTRUCTION = """
Ban la chuyen gia tu van dau tu chung khoan Viet Nam.

## NHIEM VU CUA BAN:

Giup nha dau tu xay dung **KE HOACH DAU TU HOAN CHINH** bao gom:
1. **Profile**: Hieu ro muc tieu, rui ro, von
2. **Allocation**: Phan bo danh muc hop ly
3. **Entry Strategy**: Chien luoc vao lenh
4. **Risk Management**: Quan ly rui ro (stop-loss, take-profit)
5. **Monitoring**: Ke hoach theo doi

## TOOLS CUA BAN (7 tools):

### Investment Planning Tools (5):

1. **gather_investment_profile(user_id, capital, risk_tolerance, time_horizon, goals)**
   - Thu thap ho so dau tu
   - risk_tolerance: "low", "medium", "high"
   - time_horizon: "short" (<1 nam), "medium" (1-3 nam), "long" (>3 nam)
   - goals: ["growth", "income", "balanced"]

2. **calculate_portfolio_allocation(profile, stocks, capital)**
   - Tinh phan bo danh muc
   - Tra ve: % phan bo cho moi stock + cash

3. **generate_entry_strategy(stocks, capital_per_stock, strategy_type)**
   - Chien luoc vao lenh
   - strategy_type: "lump_sum", "dca", "value_averaging"

4. **generate_risk_management_plan(stocks, allocation, risk_tolerance)**
   - Ke hoach quan ly rui ro
   - Stop-loss, take-profit levels
   - Position sizing rules

5. **generate_monitoring_plan(stocks, monitoring_frequency)**
   - Ke hoach giam sat
   - monitoring_frequency: "daily", "weekly", "monthly"

### Data Tools (2):

6. **get_stock_data(symbols, lookback_days)**
   - Validate stock selections

7. **get_financial_data(tickers, ...)**
   - Analyze fundamentals

## NGUYEN TAC QUAN TRONG:

- Luon gather profile truoc khi plan
- Diversification: It nhat 3-5 stocks khac nganh
- Risk management: Luon co stop-loss
- Cash reserve: Giu 5-15% cash
- Realistic expectations: Khong hua loi nhuan cao

Hay tao ke hoach dau tu chuyen nghiep va co trach nhiem!
"""

    def __init__(self, mcp_client):
        """
        Initialize Investment Planner

        Args:
            mcp_client: EnhancedMCPClient or DirectMCPClient instance
        """
        self.mcp_client = mcp_client
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        self.stats = {
            "total_plans": 0,
            "avg_capital": 0.0,
            "risk_distribution": {
                "low": 0,
                "medium": 0,
                "high": 0
            }
        }

    async def create_investment_plan(
        self,
        user_id: str,
        capital: float,
        risk_tolerance: str = "medium",
        time_horizon: str = "medium",
        goals: List[str] = None,
        preferred_stocks: Optional[List[str]] = None,
        shared_state: Optional[Dict] = None
    ) -> AsyncIterator[str]:
        """
        Create comprehensive investment plan

        Args:
            user_id: User identifier
            capital: Investment capital (VND)
            risk_tolerance: low/medium/high
            time_horizon: short/medium/long
            goals: List of goals (growth, income, balanced)
            preferred_stocks: Optional list of preferred stocks
            shared_state: Shared state for storing results

        Yields:
            Investment plan chunks
        """
        self.stats["total_plans"] += 1
        self.stats["risk_distribution"][risk_tolerance] += 1

        try:
            # Step 1: Gather investment profile
            yield "Dang thu thap ho so dau tu...\n"

            # Map risk_tolerance and time_horizon to tool params
            risk_map = {"low": "conservative", "medium": "moderate", "high": "aggressive"}
            horizon_map = {"short": "short-term", "medium": "medium-term", "long": "long-term"}
            goals_str = goals[0] if goals else "growth"

            profile = await self.mcp_client.call_tool(
                "gather_investment_profile",
                {
                    "goals": goals_str,
                    "risk_tolerance": risk_map.get(risk_tolerance, "moderate"),
                    "timeframe": horizon_map.get(time_horizon, "medium-term"),
                    "capital": capital
                }
            )

            if shared_state is not None:
                shared_state["investment_profile"] = profile

            # Step 2: Get suitable stocks (either from preferred or discover)
            if preferred_stocks:
                stocks = preferred_stocks
                yield f"[OK] Su dung danh sach co phieu: {', '.join(stocks)}\n"
            else:
                yield "Dang tim co phieu phu hop...\n"
                # Use discovery or screener
                # For now, use default conservative list
                stocks = ["VCB", "FPT", "VNM", "HPG", "VIC"]
                yield f"[OK] De xuat: {', '.join(stocks)}\n"

            # Step 3: Validate stocks
            yield "Dang phan tich co phieu...\n"
            stock_data = await self.mcp_client.call_tool(
                "get_stock_data",
                {"symbols": stocks, "lookback_days": 30}
            )

            # Step 4: Calculate portfolio allocation
            yield "Dang tinh phan bo danh muc...\n"
            # Convert stock symbols to stock dict format required by the tool
            stock_dicts = []
            if stock_data.get("status") == "success":
                results = stock_data.get("results", {})
                for symbol in stocks:
                    if symbol in results:
                        data = results[symbol]
                        stock_dicts.append({
                            "symbol": symbol,
                            "score": 7,  # Default score
                            "price": data.get("latest_price", {}).get("close", 0) if data else 0
                        })
                    else:
                        stock_dicts.append({"symbol": symbol, "score": 5, "price": 0})
            else:
                # Fallback - create basic stock dicts
                stock_dicts = [{"symbol": s, "score": 5} for s in stocks]

            allocation = await self.mcp_client.call_tool(
                "calculate_portfolio_allocation",
                {
                    "stocks": stock_dicts,
                    "capital": capital,
                    "risk_tolerance": risk_map.get(risk_tolerance, "moderate")
                }
            )

            if shared_state is not None:
                shared_state["portfolio_allocation"] = allocation

            # Step 5: Generate entry strategy (params: stocks: List[Dict], timeframe: str)
            yield "Dang tao chien luoc vao lenh...\n"
            entry_strategy = await self.mcp_client.call_tool(
                "generate_entry_strategy",
                {
                    "stocks": stock_dicts,  # Use stock_dicts which is List[Dict]
                    "timeframe": horizon_map.get(time_horizon, "medium-term")
                }
            )

            # Step 6: Generate risk management plan (params: stocks: List[Dict], risk_tolerance: str)
            yield "Dang tao ke hoach quan ly rui ro...\n"
            risk_plan = await self.mcp_client.call_tool(
                "generate_risk_management_plan",
                {
                    "stocks": stock_dicts,
                    "risk_tolerance": risk_map.get(risk_tolerance, "moderate")
                }
            )

            # Step 7: Generate monitoring plan (params: stocks: List[Dict], timeframe: str)
            yield "Dang tao ke hoach giam sat...\n"
            monitoring_plan = await self.mcp_client.call_tool(
                "generate_monitoring_plan",
                {
                    "stocks": stock_dicts,
                    "timeframe": horizon_map.get(time_horizon, "medium-term")
                }
            )

            # Step 8: Generate final report
            yield "\n" + "="*50 + "\n"
            yield "**KE HOACH DAU TU HOAN CHINH**\n"
            yield "="*50 + "\n\n"

            # Format and yield complete plan
            final_plan = self._format_investment_plan(
                profile=profile,
                stocks=stocks,
                allocation=allocation,
                entry_strategy=entry_strategy,
                risk_plan=risk_plan,
                monitoring_plan=monitoring_plan,
                capital=capital
            )

            yield final_plan

        except Exception as e:
            yield f"\n[ERROR] Loi khi tao ke hoach dau tu: {str(e)}"

    def _determine_strategy_type(self, risk_tolerance: str, time_horizon: str) -> str:
        """Determine entry strategy type based on profile"""
        if time_horizon == "short" or risk_tolerance == "high":
            return "lump_sum"  # Ngan han/risk cao -> lump sum
        elif time_horizon == "long":
            return "dca"  # Dai han -> DCA
        else:
            return "value_averaging"  # Trung binh -> Value averaging

    def _determine_monitoring_frequency(self, time_horizon: str) -> str:
        """Determine monitoring frequency"""
        if time_horizon == "short":
            return "daily"
        elif time_horizon == "medium":
            return "weekly"
        else:
            return "monthly"

    def _format_investment_plan(
        self,
        profile: Dict,
        stocks: List[str],
        allocation: Dict,
        entry_strategy: Dict,
        risk_plan: Dict,
        monitoring_plan: Dict,
        capital: float
    ) -> str:
        """Format complete investment plan"""
        output = []

        # 1. Profile
        output.append("**1. HO SO DAU TU**\n")
        output.append(f"- Von: {capital:,.0f} VND")
        output.append(f"- Khau vi rui ro: {profile.get('risk_tolerance', 'N/A')}")
        output.append(f"- Thoi gian: {profile.get('time_horizon', 'N/A')}")
        output.append(f"- Muc tieu: {', '.join(profile.get('goals', []))}\n")

        # 2. Allocation
        output.append("**2. PHAN BO DANH MUC**\n")
        alloc_data = allocation.get("allocation", {})
        for stock, pct in alloc_data.items():
            amount = capital * pct / 100
            output.append(f"- {stock}: {pct}% ({amount:,.0f} VND)")
        output.append("")

        # 3. Entry Strategy
        output.append("**3. CHIEN LUOC VAO LENH**\n")
        output.append(f"- Phuong phap: {entry_strategy.get('type', 'N/A')}")
        output.append(f"- Chi tiet: {entry_strategy.get('description', 'N/A')}\n")

        # 4. Risk Management
        output.append("**4. QUAN LY RUI RO**\n")
        for stock in stocks:
            output.append(f"- {stock}: Stop-loss, Take-profit (xem chi tiet)\n")

        # 5. Monitoring
        output.append("**5. KE HOACH GIAM SAT**\n")
        output.append(f"- Tan suat: {monitoring_plan.get('frequency', 'N/A')}")
        output.append(f"- Chi so theo doi: Price, Volume, News\n")

        # Disclaimer
        output.append("**LUU Y:**")
        output.append("- Day la ke hoach dinh huong, khong phai loi khuyen dau tu")
        output.append("- Can xem xet tinh hinh ca nhan truoc khi quyet dinh")

        return "\n".join(output)

    def get_stats(self) -> Dict:
        """Get investment planning statistics"""
        return self.stats.copy()
