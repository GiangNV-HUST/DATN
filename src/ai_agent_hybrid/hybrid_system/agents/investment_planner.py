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
            if stock_data.get("status") in ["success", "partial_success"]:
                results = stock_data.get("results", {})
                for symbol in stocks:
                    if symbol in results:
                        symbol_data = results[symbol]
                        # Handle different response formats
                        price = 0
                        if symbol_data.get("status") == "success":
                            data = symbol_data.get("data", {})
                            # Try latest first (realtime), then fall back to data array
                            if "latest" in data and data["latest"]:
                                price = data["latest"].get("close", 0) or data["latest"].get("price", 0)
                            elif "data" in data and data["data"]:
                                # Get last price from data array
                                last_record = data["data"][-1] if isinstance(data["data"], list) else data["data"]
                                price = last_record.get("close", 0)
                        stock_dicts.append({
                            "symbol": symbol,
                            "score": 7,  # Default score
                            "current_price": price  # Use current_price for investment_planning_tools
                        })
                    else:
                        stock_dicts.append({"symbol": symbol, "score": 5, "current_price": 0})
            else:
                # Fallback - create basic stock dicts
                stock_dicts = [{"symbol": s, "score": 5, "current_price": 0} for s in stocks]

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

    async def create_dca_plan(
        self,
        symbol: str,
        monthly_investment: float,
        duration_months: int = 12,
        price_trend: str = "neutral",
        shared_state: Optional[Dict] = None
    ) -> AsyncIterator[str]:
        """
        Create DCA (Dollar Cost Averaging) plan for a specific stock

        Args:
            symbol: Stock symbol (e.g., FPT, VCB)
            monthly_investment: Monthly investment amount in VND
            duration_months: Number of months for DCA
            price_trend: Expected price trend (bullish/neutral/bearish)
            shared_state: Shared state for storing results

        Yields:
            DCA plan chunks
        """
        try:
            yield f"Dang tao ke hoach DCA cho {symbol.upper()}...\n"

            # Get current price
            yield "Dang lay gia hien tai...\n"
            stock_data = await self.mcp_client.call_tool(
                "get_stock_data",
                {"symbols": [symbol.upper()], "lookback_days": 7}
            )

            current_price = 0
            if stock_data.get("status") in ["success", "partial_success"]:
                results = stock_data.get("results", {})
                if symbol.upper() in results:
                    symbol_data = results[symbol.upper()]
                    if symbol_data.get("status") == "success":
                        data = symbol_data.get("data", {})
                        if "latest" in data and data["latest"]:
                            current_price = data["latest"].get("close", 0) * 1000  # Convert to VND
                        elif "data" in data and data["data"]:
                            last_record = data["data"][-1] if isinstance(data["data"], list) else data["data"]
                            current_price = last_record.get("close", 0) * 1000

            if current_price == 0:
                yield f"[WARNING] Khong lay duoc gia {symbol}, su dung gia mac dinh\n"
                current_price = 100000

            yield f"[OK] Gia hien tai: {current_price:,.0f} VND\n"

            # Generate DCA plan
            yield "Dang tinh toan ke hoach DCA...\n"
            dca_result = await self.mcp_client.call_tool(
                "generate_dca_plan",
                {
                    "symbol": symbol.upper(),
                    "monthly_investment": monthly_investment,
                    "duration_months": duration_months,
                    "current_price": current_price,
                    "price_trend": price_trend
                }
            )

            if dca_result.get("status") != "success":
                yield f"[ERROR] Khong the tao ke hoach DCA: {dca_result.get('message', 'Unknown error')}\n"
                return

            # Format and yield DCA plan
            yield "\n" + "="*50 + "\n"
            yield f"**KE HOACH DCA CHO {symbol.upper()}**\n"
            yield "="*50 + "\n\n"

            yield self._format_dca_plan(dca_result)

            # Store in shared state
            if shared_state is not None:
                shared_state["dca_plan"] = dca_result

        except Exception as e:
            yield f"\n[ERROR] Loi khi tao ke hoach DCA: {str(e)}"

    def _format_dca_plan(self, dca_result: Dict) -> str:
        """Format DCA plan result"""
        output = []

        summary = dca_result.get("plan_summary", {})
        projections = dca_result.get("projections", {})
        monthly = dca_result.get("monthly_breakdown", [])
        recommendations = dca_result.get("recommendations", [])

        # Summary
        output.append("**1. THONG TIN KE HOACH**\n")
        output.append(f"- Co phieu: {dca_result.get('symbol', 'N/A')}")
        output.append(f"- Chien luoc: {summary.get('strategy', 'DCA')}")
        output.append(f"- So tien moi thang: {summary.get('monthly_investment', 0):,.0f} VND")
        output.append(f"- Thoi gian: {summary.get('duration_months', 0)} thang")
        output.append(f"- Gia hien tai: {summary.get('current_price', 0):,.0f} VND")
        output.append(f"- Xu huong du kien: {summary.get('price_trend', 'neutral')}\n")

        # Projections
        output.append("**2. DU BAO KET QUA**\n")
        output.append(f"- Tong dau tu: {projections.get('total_investment', 0):,.0f} VND")
        output.append(f"- Tong co phieu: {projections.get('total_shares', 0):,} CP")
        output.append(f"- Gia trung binh: {projections.get('average_price', 0):,.0f} VND/CP")
        output.append(f"- Gia tri danh muc cuoi ky: {projections.get('final_portfolio_value', 0):,.0f} VND")
        output.append(f"- Loi nhuan du kien: {projections.get('estimated_profit_loss', 0):,.0f} VND ({projections.get('estimated_return_pct', 0):.2f}%)\n")

        # Monthly breakdown (first 6 months)
        output.append("**3. LICH MUA HANG THANG**\n")
        output.append("| Thang | Ngay | Gia DK | So CP | Tong CP |")
        output.append("|-------|------|--------|-------|---------|")
        for m in monthly[:6]:
            output.append(f"| {m.get('month', 0)} | {m.get('date', 'N/A')} | {m.get('estimated_price', 0):,.0f} | {m.get('shares_to_buy', 0)} | {m.get('cumulative_shares', 0):,} |")
        if len(monthly) > 6:
            output.append(f"| ... | ... | ... | ... | ... |")
            last = monthly[-1]
            output.append(f"| {last.get('month', 0)} | {last.get('date', 'N/A')} | {last.get('estimated_price', 0):,.0f} | {last.get('shares_to_buy', 0)} | {last.get('cumulative_shares', 0):,} |")
        output.append("")

        # Recommendations
        if recommendations:
            output.append("**4. KHUYEN NGHI**\n")
            for rec in recommendations[:5]:
                output.append(f"- {rec}")
            output.append("")

        # Disclaimer
        output.append("**LUU Y:**")
        output.append(f"- {dca_result.get('disclaimer', 'Day la ke hoach du kien, gia thuc te co the khac biet.')}")

        return "\n".join(output)

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

        # 1. Profile - Extract from nested structure
        profile_data = profile.get('profile', profile)
        output.append("**1. HO SO DAU TU**\n")
        output.append(f"- Von: {capital:,.0f} VND")
        output.append(f"- Khau vi rui ro: {profile_data.get('risk_tolerance', 'N/A')}")
        output.append(f"- Thoi gian: {profile_data.get('timeframe', 'N/A')}")
        output.append(f"- Muc tieu: {profile_data.get('goals', 'N/A')}\n")

        # Show allocation recommendations
        recommendations = profile_data.get('recommendations', {})
        if recommendations:
            output.append(f"- De xuat phan bo: Co phieu {recommendations.get('equity_allocation', 'N/A')}, Trai phieu {recommendations.get('bond_allocation', 'N/A')}, Tien mat {recommendations.get('cash_allocation', 'N/A')}\n")

        # 2. Allocation - Extract from allocations key
        output.append("**2. PHAN BO DANH MUC**\n")
        alloc_data = allocation.get("allocations", {})
        if alloc_data:
            for stock, details in alloc_data.items():
                if isinstance(details, dict):
                    weight = details.get('weight', 0)
                    target = details.get('target_amount', 0)
                    shares = details.get('shares', 0)
                    output.append(f"- {stock}: {weight}% ({target:,.0f} VND) - {shares:,} co phieu")
                else:
                    output.append(f"- {stock}: {details}")

            cash_reserve = allocation.get('cash_reserve', 0)
            cash_pct = allocation.get('cash_reserve_percentage', 0)
            output.append(f"- Tien mat du phong: {cash_reserve:,.0f} VND ({cash_pct}%)")
        else:
            output.append("- Chua tinh duoc phan bo chi tiet")
        output.append("")

        # 3. Entry Strategy - Extract from strategies key
        output.append("**3. CHIEN LUOC VAO LENH**\n")
        strategies = entry_strategy.get('strategies', {})
        timeframe = entry_strategy.get('timeframe', 'N/A')
        output.append(f"- Khung thoi gian: {timeframe}\n")

        for stock, strategy in strategies.items():
            entry_method = strategy.get('entry_method', 'N/A')
            output.append(f"**{stock}**: {entry_method}")
            positions = strategy.get('positions', [])
            for pos in positions[:3]:  # Show max 3 positions
                output.append(f"  - {pos.get('condition', 'N/A')}")
        output.append("")

        # 4. Risk Management - Extract from risk_plans key
        output.append("**4. QUAN LY RUI RO**\n")
        risk_plans = risk_plan.get('risk_plans', {})
        for stock, plan in risk_plans.items():
            stop_loss = plan.get('stop_loss', {})
            take_profit = plan.get('take_profit', {})
            sl_price = stop_loss.get('price', 0)
            tp_price = take_profit.get('price', 0)
            output.append(f"**{stock}**:")
            output.append(f"  - Stop-loss: {sl_price:,.0f} VND ({stop_loss.get('percentage', 'N/A')}%)")
            output.append(f"  - Take-profit: {tp_price:,.0f} VND (+{take_profit.get('percentage', 'N/A')}%)")
        output.append("")

        # 5. Monitoring
        output.append("**5. KE HOACH GIAM SAT**\n")
        output.append(f"- Tan suat: {monitoring_plan.get('frequency', '2-3 lan/tuan')}")

        general_metrics = monitoring_plan.get('general_metrics', [])
        if general_metrics:
            output.append("- Chi so theo doi:")
            for metric in general_metrics[:5]:
                output.append(f"  + {metric}")
        output.append("")

        # Disclaimer
        output.append("**LUU Y:**")
        output.append("- Day la ke hoach dinh huong, khong phai loi khuyen dau tu")
        output.append("- Can xem xet tinh hinh ca nhan truoc khi quyet dinh")
        output.append("- Gia co phieu co the thay doi, can cap nhat truoc khi thuc hien")

        return "\n".join(output)

    def get_stats(self) -> Dict:
        """Get investment planning statistics"""
        return self.stats.copy()
