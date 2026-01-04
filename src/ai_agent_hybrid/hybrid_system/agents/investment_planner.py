"""
Investment Planner Agent

Specialized in investment planning and portfolio management:
- Gathering investment profile
- Portfolio allocation
- Entry strategy
- Risk management
- Monitoring plan

NEW agent - không có trong OLD system.
"""

import os
import sys
from typing import Dict, List, Optional, AsyncIterator

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'ai_agent_mcp'))

import google.generativeai as genai


class InvestmentPlanner:
    """
    Specialist for investment planning and portfolio management

    Tools (7):
    - gather_investment_profile: Thu thập profile (risk, capital, goals)
    - calculate_portfolio_allocation: Tính phân bổ danh mục
    - generate_entry_strategy: Chiến lược vào lệnh
    - generate_risk_management_plan: Quản lý rủi ro
    - generate_monitoring_plan: Kế hoạch giám sát
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
Bạn là chuyên gia tư vấn đầu tư chứng khoán Việt Nam.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## NHIỆM VỤ CỦA BẠN:

Giúp nhà đầu tư xây dựng **KẾ HOẠCH ĐẦU TƯ HOÀN CHỈNH** bao gồm:
1. **Profile**: Hiểu rõ mục tiêu, rủi ro, vốn
2. **Allocation**: Phân bổ danh mục hợp lý
3. **Entry Strategy**: Chiến lược vào lệnh
4. **Risk Management**: Quản lý rủi ro (stop-loss, take-profit)
5. **Monitoring**: Kế hoạch theo dõi

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## TOOLS CỦA BẠN (7 tools):

### Investment Planning Tools (5):

1. **gather_investment_profile(user_id, capital, risk_tolerance, time_horizon, goals)**
   - Thu thập hồ sơ đầu tư
   - risk_tolerance: "low", "medium", "high"
   - time_horizon: "short" (<1 năm), "medium" (1-3 năm), "long" (>3 năm)
   - goals: ["growth", "income", "balanced"]

2. **calculate_portfolio_allocation(profile, stocks, capital)**
   - Tính phân bổ danh mục
   - Trả về: % phân bổ cho mỗi stock + cash

3. **generate_entry_strategy(stocks, capital_per_stock, strategy_type)**
   - Chiến lược vào lệnh
   - strategy_type: "lump_sum", "dca", "value_averaging"

4. **generate_risk_management_plan(stocks, allocation, risk_tolerance)**
   - Kế hoạch quản lý rủi ro
   - Stop-loss, take-profit levels
   - Position sizing rules

5. **generate_monitoring_plan(stocks, monitoring_frequency)**
   - Kế hoạch giám sát
   - monitoring_frequency: "daily", "weekly", "monthly"

### Data Tools (2):

6. **get_stock_data(symbols, lookback_days)**
   - Validate stock selections

7. **get_financial_data(tickers, ...)**
   - Analyze fundamentals

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## WORKFLOW CHUẨN:

### Use Case 1: "Tư vấn đầu tư 100 triệu"
```
User: "Tôi có 100 triệu, tư vấn đầu tư cho tôi"

Step 1: gather_investment_profile(
    capital=100_000_000,
    risk_tolerance="medium",  # Hỏi user nếu chưa rõ
    time_horizon="medium",
    goals=["balanced"]
)

Step 2: Discover stocks (dùng DiscoverySpecialist hoặc ScreenerSpecialist)
    → Ví dụ: VCB, FPT, HPG, VNM, VIC

Step 3: get_stock_data(["VCB", "FPT", "HPG", "VNM", "VIC"])
    → Validate selections

Step 4: calculate_portfolio_allocation(
    profile=profile,
    stocks=["VCB", "FPT", "HPG", "VNM", "VIC"],
    capital=100_000_000
)
    → VCB: 25%, FPT: 20%, HPG: 20%, VNM: 15%, VIC: 10%, Cash: 10%

Step 5: generate_entry_strategy(
    stocks=...,
    strategy_type="dca"  # Dollar Cost Averaging for medium risk
)

Step 6: generate_risk_management_plan(
    stocks=...,
    allocation=...,
    risk_tolerance="medium"
)

Step 7: generate_monitoring_plan(
    stocks=...,
    monitoring_frequency="weekly"
)

Step 8: Tổng hợp thành BÁO CÁO ĐẦU TƯ
```

### Use Case 2: "Đầu tư ngắn hạn 50 triệu"
```
User: "50 triệu đầu tư ngắn hạn"

Step 1: gather_investment_profile(
    capital=50_000_000,
    risk_tolerance="high",  # Ngắn hạn thường risk cao
    time_horizon="short",
    goals=["growth"]
)

Step 2: Screen stocks phù hợp ngắn hạn
    → Technical strength, momentum stocks

Step 3: calculate_portfolio_allocation
    → Tập trung hơn: 2-3 stocks

Step 4: generate_entry_strategy(strategy_type="lump_sum")
    → Ngắn hạn thường lump sum

Step 5-7: Risk management + Monitoring (tight controls)
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## OUTPUT FORMAT:

```
📊 **KẾ HOẠCH ĐẦU TƯ**

**1. HỒ SƠ ĐẦU TƯ**
- Vốn: 100,000,000 VNĐ
- Khẩu vị rủi ro: Trung bình
- Thời gian: 1-3 năm
- Mục tiêu: Tăng trưởng cân bằng

**2. PHÂN BỔ DANH MỤC**

| Mã CP | Ngành | Tỷ trọng | Số tiền |
|-------|-------|----------|---------|
| VCB   | Ngân hàng | 25% | 25,000,000 |
| FPT   | Công nghệ | 20% | 20,000,000 |
| HPG   | Thép | 20% | 20,000,000 |
| VNM   | Tiêu dùng | 15% | 15,000,000 |
| VIC   | Bất động sản | 10% | 10,000,000 |
| Cash  | Dự phòng | 10% | 10,000,000 |

**3. CHIẾN LƯỢC VÀO LỆNH**
- Phương pháp: DCA (Dollar Cost Averaging)
- Kế hoạch:
  * Tuần 1-2: Mua 40% vốn
  * Tuần 3-4: Mua 30% vốn
  * Tuần 5-8: Mua 20% vốn còn lại
  * 10% cash dự phòng

**4. QUẢN LÝ RỦI RO**

VCB:
- Entry: 94,000
- Stop-loss: 89,300 (-5%)
- Take-profit: 103,400 (+10%)

FPT:
- Entry: 145,000
- Stop-loss: 137,750 (-5%)
- Take-profit: 159,500 (+10%)

[...]

**5. KẾ HOẠCH GIÁM SÁT**
- Tần suất: Hàng tuần
- Chỉ số theo dõi:
  * Giá và volume
  * Tin tức ngành
  * Báo cáo tài chính quý
- Rebalance: Mỗi 3 tháng hoặc khi lệch > 5%

💡 **LƯU Ý:**
- Đây là kế hoạch định hướng, không phải lời khuyên đầu tư
- Cần xem xét tình hình cá nhân trước khi quyết định
- Luôn tuân thủ kỷ luật stop-loss
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## NGUYÊN TẮC QUAN TRỌNG:

✅ DO:
1. Luôn gather profile trước khi plan
2. Diversification: Ít nhất 3-5 stocks khác ngành
3. Risk management: Luôn có stop-loss
4. Cash reserve: Giữ 5-15% cash
5. Realistic expectations: Không hứa lợi nhuận cao

❌ DON'T:
1. Đừng recommend 100% vào 1 stock
2. Đừng bỏ qua risk tolerance
3. Đừng plan mà không có monitoring
4. Đừng recommend stocks kém thanh khoản
5. Đừng hứa "chắc chắn lời"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Hãy tạo kế hoạch đầu tư chuyên nghiệp và có trách nhiệm!
"""

    def __init__(self, mcp_client):
        """
        Initialize Investment Planner

        Args:
            mcp_client: EnhancedMCPClient instance
        """
        self.mcp_client = mcp_client
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

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
            yield "📊 Đang thu thập hồ sơ đầu tư...\n"

            profile = await self.mcp_client.call_tool(
                "gather_investment_profile",
                {
                    "user_id": user_id,
                    "capital": capital,
                    "risk_tolerance": risk_tolerance,
                    "time_horizon": time_horizon,
                    "goals": goals or ["balanced"]
                }
            )

            if shared_state is not None:
                shared_state["investment_profile"] = profile

            # Step 2: Get suitable stocks (either from preferred or discover)
            if preferred_stocks:
                stocks = preferred_stocks
                yield f"✅ Sử dụng danh sách cổ phiếu: {', '.join(stocks)}\n"
            else:
                yield "🔍 Đang tìm cổ phiếu phù hợp...\n"
                # Use discovery or screener
                # For now, use default conservative list
                stocks = ["VCB", "FPT", "VNM", "HPG", "VIC"]
                yield f"✅ Đề xuất: {', '.join(stocks)}\n"

            # Step 3: Validate stocks
            yield "📈 Đang phân tích cổ phiếu...\n"
            stock_data = await self.mcp_client.call_tool(
                "get_stock_data",
                {"symbols": stocks, "lookback_days": 30}
            )

            # Step 4: Calculate portfolio allocation
            yield "💼 Đang tính phân bổ danh mục...\n"
            allocation = await self.mcp_client.call_tool(
                "calculate_portfolio_allocation",
                {
                    "profile": profile,
                    "stocks": stocks,
                    "capital": capital
                }
            )

            if shared_state is not None:
                shared_state["portfolio_allocation"] = allocation

            # Step 5: Generate entry strategy
            yield "📍 Đang tạo chiến lược vào lệnh...\n"
            entry_strategy = await self.mcp_client.call_tool(
                "generate_entry_strategy",
                {
                    "stocks": stocks,
                    "capital_per_stock": allocation.get("allocation", {}),
                    "strategy_type": self._determine_strategy_type(risk_tolerance, time_horizon)
                }
            )

            # Step 6: Generate risk management plan
            yield "🛡️ Đang tạo kế hoạch quản lý rủi ro...\n"
            risk_plan = await self.mcp_client.call_tool(
                "generate_risk_management_plan",
                {
                    "stocks": stocks,
                    "allocation": allocation,
                    "risk_tolerance": risk_tolerance
                }
            )

            # Step 7: Generate monitoring plan
            yield "📊 Đang tạo kế hoạch giám sát...\n"
            monitoring_plan = await self.mcp_client.call_tool(
                "generate_monitoring_plan",
                {
                    "stocks": stocks,
                    "monitoring_frequency": self._determine_monitoring_frequency(time_horizon)
                }
            )

            # Step 8: Generate final report
            yield "\n" + "="*50 + "\n"
            yield "📊 **KẾ HOẠCH ĐẦU TƯ HOÀN CHỈNH**\n"
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
            yield f"\n❌ Lỗi khi tạo kế hoạch đầu tư: {str(e)}"

    def _determine_strategy_type(self, risk_tolerance: str, time_horizon: str) -> str:
        """Determine entry strategy type based on profile"""
        if time_horizon == "short" or risk_tolerance == "high":
            return "lump_sum"  # Ngắn hạn/risk cao → lump sum
        elif time_horizon == "long":
            return "dca"  # Dài hạn → DCA
        else:
            return "value_averaging"  # Trung bình → Value averaging

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
        output.append("**1. HỒ SƠ ĐẦU TƯ**\n")
        output.append(f"- Vốn: {capital:,.0f} VNĐ")
        output.append(f"- Khẩu vị rủi ro: {profile.get('risk_tolerance', 'N/A')}")
        output.append(f"- Thời gian: {profile.get('time_horizon', 'N/A')}")
        output.append(f"- Mục tiêu: {', '.join(profile.get('goals', []))}\n")

        # 2. Allocation
        output.append("**2. PHÂN BỔ DANH MỤC**\n")
        alloc_data = allocation.get("allocation", {})
        for stock, pct in alloc_data.items():
            amount = capital * pct / 100
            output.append(f"- {stock}: {pct}% ({amount:,.0f} VNĐ)")
        output.append("")

        # 3. Entry Strategy
        output.append("**3. CHIẾN LƯỢC VÀO LỆNH**\n")
        output.append(f"- Phương pháp: {entry_strategy.get('type', 'N/A')}")
        output.append(f"- Chi tiết: {entry_strategy.get('description', 'N/A')}\n")

        # 4. Risk Management
        output.append("**4. QUẢN LÝ RỦI RO**\n")
        for stock in stocks:
            output.append(f"- {stock}: Stop-loss, Take-profit (xem chi tiết)\n")

        # 5. Monitoring
        output.append("**5. KẾ HOẠCH GIÁM SÁT**\n")
        output.append(f"- Tần suất: {monitoring_plan.get('frequency', 'N/A')}")
        output.append(f"- Chỉ số theo dõi: Price, Volume, News\n")

        # Disclaimer
        output.append("💡 **LƯU Ý:**")
        output.append("- Đây là kế hoạch định hướng, không phải lời khuyên đầu tư")
        output.append("- Cần xem xét tình hình cá nhân trước khi quyết định")

        return "\n".join(output)

    def get_stats(self) -> Dict:
        """Get investment planning statistics"""
        return self.stats.copy()
