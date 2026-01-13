"""
AI-Powered Specialist Router using OpenAI

Routes user queries to the most appropriate specialist agent:
1. AnalysisSpecialist - Stock analysis (price, technical, fundamental)
2. ScreenerSpecialist - Stock screening and filtering
3. AlertManager - Price alerts management
4. InvestmentPlanner - Investment planning and portfolio allocation
5. DiscoverySpecialist - Discover potential stocks
6. SubscriptionManager - Subscription management
7. MarketContextSpecialist - Market overview (VN-Index, sectors, breadth) [NEW]
8. ComparisonSpecialist - Stock comparison (side-by-side, peer) [NEW]

Uses GPT-4o-mini for intelligent routing with Vietnamese language support.
"""

from openai import OpenAI
import json
import os
import re
from typing import Literal, Optional, List, Dict
from dataclasses import dataclass, field
import asyncio
import time


@dataclass
class SpecialistRoutingDecision:
    """Decision from Specialist Router"""
    specialist: Literal[
        "AnalysisSpecialist",
        "ScreenerSpecialist",
        "AlertManager",
        "InvestmentPlanner",
        "DiscoverySpecialist",
        "SubscriptionManager",
        "MarketContextSpecialist",
        "ComparisonSpecialist"
    ]
    method: str
    reasoning: str
    confidence: float
    extracted_params: Dict = field(default_factory=dict)
    estimated_time: float = 2.0


class SpecialistRouter:
    """
    AI-Powered Router for Multi-Specialist System

    Uses OpenAI GPT-4o-mini to:
    - Understand user intent (Vietnamese + English)
    - Route to appropriate specialist
    - Extract relevant parameters (symbols, amounts, etc.)
    - Handle complex/ambiguous queries

    Features:
    - Intelligent Vietnamese language understanding
    - Context-aware routing
    - Parameter extraction
    - Fallback to pattern matching if AI fails
    - Decision caching for performance
    """

    def __init__(self, use_cache: bool = True):
        """
        Initialize Specialist Router

        Args:
            use_cache: Whether to cache routing decisions (default True)
        """
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.use_cache = use_cache

        # Cache routing decisions for identical queries
        self.decision_cache: Dict[str, SpecialistRoutingDecision] = {}

        # Stats
        self.stats = {
            "total_routings": 0,
            "cache_hits": 0,
            "ai_success": 0,
            "ai_failures": 0,
            "fallback_used": 0,
            "avg_routing_time": 0,
            "specialist_counts": {
                "AnalysisSpecialist": 0,
                "ScreenerSpecialist": 0,
                "AlertManager": 0,
                "InvestmentPlanner": 0,
                "DiscoverySpecialist": 0,
                "SubscriptionManager": 0,
                "MarketContextSpecialist": 0,
                "ComparisonSpecialist": 0,
            }
        }

        self._total_routing_time = 0

    def _get_system_prompt(self) -> str:
        """Get system prompt for specialist routing"""
        return """Bạn là SPECIALIST ROUTER - Bộ điều phối thông minh cho hệ thống phân tích chứng khoán Việt Nam.

## NHIỆM VỤ:
Phân tích query của user và quyết định chuyển đến SPECIALIST phù hợp nhất.

## 8 SPECIALISTS:

### 1. AnalysisSpecialist
**Chức năng:** Phân tích cổ phiếu chi tiết
**Sử dụng khi:**
- Phân tích kỹ thuật (RSI, MACD, MA, chart patterns)
- Phân tích cơ bản (P/E, ROE, EPS, revenue, profit)
- Xem giá cổ phiếu, biểu đồ
- Dự đoán giá (predict)
- So sánh 2-3 cổ phiếu cụ thể
- Hỏi về một mã cổ phiếu cụ thể

**Methods:**
- `analyze`: Phân tích tổng hợp (default)
- `get_price`: Chỉ lấy giá
- `predict`: Dự đoán giá

**Ví dụ queries:**
- "Phân tích VCB"
- "Giá FPT hôm nay"
- "Dự đoán VNM 3 ngày tới"
- "So sánh VCB với TCB"
- "RSI của HPG bao nhiêu?"
- "VCB có nên mua không?"

### 2. ScreenerSpecialist
**Chức năng:** Lọc và sàng lọc cổ phiếu theo tiêu chí
**Sử dụng khi:**
- Lọc cổ phiếu theo điều kiện (P/E < 15, ROE > 15%, etc.)
- Tìm top cổ phiếu (thanh khoản, tăng giá, giảm giá)
- Sàng lọc theo ngành
- Tìm cổ phiếu thỏa mãn nhiều tiêu chí

**Methods:**
- `screen`: Lọc theo tiêu chí (default)
- `get_top`: Lấy top N cổ phiếu

**Ví dụ queries:**
- "Lọc cổ phiếu P/E < 15 và ROE > 20%"
- "Top 10 cổ phiếu thanh khoản cao nhất"
- "Tìm cổ phiếu ngân hàng có P/B < 2"
- "Cổ phiếu nào tăng mạnh nhất tuần này?"
- "Sàng lọc cổ phiếu vốn hóa lớn"

### 3. AlertManager
**Chức năng:** Quản lý cảnh báo giá
**Sử dụng khi:**
- Tạo cảnh báo giá (alert khi VCB > 90000)
- Xem danh sách cảnh báo
- Xóa cảnh báo

**Methods:**
- `create_alert`: Tạo cảnh báo mới
- `get_alerts`: Xem cảnh báo (default nếu không có action cụ thể)
- `delete_alert`: Xóa cảnh báo

**Ví dụ queries:**
- "Tạo cảnh báo khi VCB vượt 95000"
- "Cảnh báo của tôi"
- "Xem các alert đang có"
- "Xóa cảnh báo số 3"
- "Alert HPG < 25000"

### 4. InvestmentPlanner
**Chức năng:** Tư vấn và lập kế hoạch đầu tư
**Sử dụng khi:**
- Tư vấn đầu tư với số vốn cụ thể
- Lập kế hoạch DCA
- Phân bổ danh mục
- Chiến lược đầu tư
- Quản lý rủi ro

**Methods:**
- `create_investment_plan`: Lập kế hoạch đầu tư (default)
- `create_dca_plan`: Kế hoạch DCA

**Ví dụ queries:**
- "Tôi có 100 triệu muốn đầu tư"
- "Tư vấn danh mục 500 triệu"
- "Kế hoạch DCA cho VCB 10 triệu/tháng"
- "Nên phân bổ vốn như thế nào với 1 tỷ?"
- "Chiến lược đầu tư an toàn cho người mới"

### 5. DiscoverySpecialist
**Chức năng:** Khám phá và gợi ý cổ phiếu tiềm năng
**Sử dụng khi:**
- Tìm cổ phiếu tiềm năng (không có tiêu chí cụ thể)
- Gợi ý/khuyến nghị cổ phiếu
- Khám phá cơ hội đầu tư
- Tìm cổ phiếu theo xu hướng/theme
- Câu hỏi mở về "nên mua cổ phiếu nào"

**Methods:**
- `discover`: Khám phá cổ phiếu tiềm năng (default)

**Ví dụ queries:**
- "Cổ phiếu nào đáng mua nhất bây giờ?"
- "Gợi ý cổ phiếu tiềm năng"
- "Khám phá cơ hội đầu tư ngành công nghệ"
- "Nên mua cổ phiếu gì?"
- "Xu hướng cổ phiếu hot nhất"

### 6. SubscriptionManager
**Chức năng:** Quản lý theo dõi cổ phiếu (watchlist)
**Sử dụng khi:**
- Theo dõi/đăng ký cổ phiếu
- Xem danh sách đang theo dõi
- Bỏ theo dõi

**Methods:**
- `create_subscription`: Thêm vào watchlist
- `get_subscriptions`: Xem watchlist (default)
- `delete_subscription`: Bỏ theo dõi

**Ví dụ queries:**
- "Theo dõi cổ phiếu FPT"
- "Danh sách cổ phiếu tôi đang theo dõi"
- "Bỏ theo dõi VCB"
- "Subscribe HPG"
- "Watchlist của tôi"

### 7. MarketContextSpecialist [NEW]
**Chức năng:** Tổng quan thị trường và bối cảnh
**Sử dụng khi:**
- Hỏi về VN-Index, HNX-Index, UPCOM
- Hỏi về thị trường chung (không phải cổ phiếu cụ thể)
- Hỏi về ngành/sector nào đang tốt/xấu
- Hỏi về market breadth (số mã tăng/giảm)
- Hỏi về khối ngoại (foreign flow)
- Hỏi tại sao thị trường tăng/giảm hôm nay

**Methods:**
- `analyze`: Phân tích thị trường tổng quan (default)
- `get_sector_performance`: Hiệu suất theo ngành
- `get_market_top_movers`: Top tăng/giảm/thanh khoản

**Ví dụ queries:**
- "VN-Index hôm nay như thế nào?"
- "Tại sao thị trường giảm?"
- "Ngành nào đang hot?"
- "Tổng quan thị trường"
- "Khối ngoại đang mua/bán ròng?"
- "Market breadth hôm nay"

### 8. ComparisonSpecialist [NEW]
**Chức năng:** So sánh nhiều cổ phiếu
**Sử dụng khi:**
- So sánh 2 hoặc nhiều cổ phiếu CỤ THỂ
- Peer comparison (so sánh trong cùng ngành)
- Relative valuation (định giá tương đối)
- Hỏi cổ phiếu nào tốt hơn khi có 2+ mã

**Methods:**
- `analyze`: So sánh cổ phiếu (default)
- `peer_analysis`: So sánh với peer trong ngành

**Ví dụ queries:**
- "So sánh VCB với TCB"
- "FPT hay CMG tốt hơn?"
- "So sánh P/E của VCB, TCB, MBB"
- "VCB và TCB cái nào đáng mua hơn?"
- "Peer comparison cho VCB trong ngành ngân hàng"

## PHÂN BIỆT QUAN TRỌNG:

### ScreenerSpecialist vs DiscoverySpecialist:
- **Screener**: Có TIÊU CHÍ CỤ THỂ (P/E < 15, ROE > 20%, top thanh khoản)
- **Discovery**: KHÔNG có tiêu chí, hỏi chung chung (cổ phiếu nào hay, gợi ý, tiềm năng)

### AnalysisSpecialist vs DiscoverySpecialist:
- **Analysis**: Hỏi về MÃ CỔ PHIẾU CỤ THỂ (VCB, FPT, HPG) - 1 mã
- **Discovery**: Hỏi chung KHÔNG có mã cụ thể (cổ phiếu nào, gợi ý gì)

### ScreenerSpecialist vs AnalysisSpecialist:
- **Screener**: TÌM NHIỀU cổ phiếu theo điều kiện
- **Analysis**: PHÂN TÍCH 1 cổ phiếu cụ thể

### AnalysisSpecialist vs ComparisonSpecialist:
- **Analysis**: Phân tích 1 cổ phiếu (hoặc hỏi về 1 mã)
- **Comparison**: SO SÁNH 2+ cổ phiếu (có từ "so sánh", "vs", "hay", "tốt hơn")

### MarketContextSpecialist vs DiscoverySpecialist:
- **MarketContext**: Hỏi về THỊ TRƯỜNG CHUNG (VN-Index, ngành, breadth) - không có mã cụ thể
- **Discovery**: Hỏi GỢI Ý cổ phiếu để mua (không phải tổng quan thị trường)

## OUTPUT FORMAT:

Trả về JSON với cấu trúc:
{
  "specialist": "AnalysisSpecialist" | "ScreenerSpecialist" | "AlertManager" | "InvestmentPlanner" | "DiscoverySpecialist" | "SubscriptionManager" | "MarketContextSpecialist" | "ComparisonSpecialist",
  "method": "method_name",
  "reasoning": "Giải thích ngắn gọn",
  "confidence": 0.95,
  "extracted_params": {
    "symbols": ["VCB", "FPT"],  // Nếu có mã cổ phiếu
    "capital": 100000000,       // Nếu có số tiền
    "conditions": {},           // Nếu có điều kiện lọc
    "alert_type": "price",      // Nếu là alert
    "target_value": 95000       // Nếu có giá mục tiêu
  },
  "estimated_time": 2.0
}

## QUY TẮC:
1. Luôn trả về VALID JSON, không thêm text khác
2. confidence > 0.9 nếu chắc chắn
3. Trích xuất parameters khi có thể (symbols, amounts, conditions)
4. Nếu không chắc, ưu tiên AnalysisSpecialist cho queries về cổ phiếu cụ thể
5. Nếu không chắc và không có mã cụ thể, ưu tiên DiscoverySpecialist

PHÂN TÍCH QUERY VÀ TRẢ VỀ JSON:"""

    async def route(self, user_query: str, user_id: str = "default") -> SpecialistRoutingDecision:
        """
        Route user query to appropriate specialist using AI

        Args:
            user_query: User's question
            user_id: User ID for context

        Returns:
            SpecialistRoutingDecision with specialist, method, and params
        """
        start_time = time.time()
        self.stats["total_routings"] += 1

        # Check cache
        cache_key = f"{user_id}:{user_query}"
        if self.use_cache and cache_key in self.decision_cache:
            self.stats["cache_hits"] += 1
            return self.decision_cache[cache_key]

        try:
            # Call OpenAI for routing decision
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": user_query}
                ],
                temperature=0.2,  # Lower temperature for more consistent routing
                response_format={"type": "json_object"},
                max_tokens=500
            )

            response_text = response.choices[0].message.content
            decision = self._parse_decision(response_text)

            # Update stats
            self.stats["ai_success"] += 1
            self.stats["specialist_counts"][decision.specialist] += 1

            # Update timing stats
            routing_time = time.time() - start_time
            self._total_routing_time += routing_time
            self.stats["avg_routing_time"] = self._total_routing_time / self.stats["total_routings"]

            # Cache decision
            if self.use_cache:
                self.decision_cache[cache_key] = decision

            return decision

        except Exception as e:
            # Fallback to pattern matching
            self.stats["ai_failures"] += 1
            self.stats["fallback_used"] += 1
            return self._fallback_routing(user_query, user_id, str(e))

    def _parse_decision(self, response_text: str) -> SpecialistRoutingDecision:
        """Parse AI response into SpecialistRoutingDecision"""
        try:
            data = json.loads(response_text)

            return SpecialistRoutingDecision(
                specialist=data["specialist"],
                method=data.get("method", "analyze"),
                reasoning=data.get("reasoning", ""),
                confidence=float(data.get("confidence", 0.8)),
                extracted_params=data.get("extracted_params", {}),
                estimated_time=float(data.get("estimated_time", 2.0))
            )

        except Exception as e:
            raise ValueError(f"Failed to parse routing decision: {e}\nResponse: {response_text}")

    def _fallback_routing(self, query: str, user_id: str, error: str) -> SpecialistRoutingDecision:
        """
        Fallback to pattern matching if AI routing fails

        Uses simple keyword matching as backup
        """
        query_lower = query.lower()

        # Extract symbols for use in params
        symbols = self._extract_symbols(query)

        # MARKET CONTEXT patterns (check FIRST for market-wide queries)
        if any(kw in query_lower for kw in [
            "vn-index", "vnindex", "hnx", "upcom", "thị trường", "thi truong",
            "market", "ngành", "nganh", "sector", "breadth", "khối ngoại",
            "tổng quan", "tong quan", "overview"
        ]) and not symbols:
            return SpecialistRoutingDecision(
                specialist="MarketContextSpecialist",
                method="analyze",
                reasoning=f"Fallback: Market context keywords detected. AI error: {error}",
                confidence=0.6,
                extracted_params={"user_query": query},
                estimated_time=4.0
            )

        # COMPARISON patterns (check if 2+ symbols with comparison keywords)
        if len(symbols) >= 2 and any(kw in query_lower for kw in [
            "so sánh", "so sanh", "compare", "vs", "hay", "với", "voi",
            "tốt hơn", "tot hon", "better"
        ]):
            return SpecialistRoutingDecision(
                specialist="ComparisonSpecialist",
                method="analyze",
                reasoning=f"Fallback: Comparison with 2+ symbols detected. AI error: {error}",
                confidence=0.7,
                extracted_params={"symbols": symbols, "user_query": query},
                estimated_time=4.0
            )

        # SCREENING patterns
        if any(kw in query_lower for kw in [
            "lọc", "loc", "sàng lọc", "screen", "top", "filter",
            "thanh khoản", "vốn hóa", "tăng mạnh", "giảm mạnh"
        ]) or any(op in query for op in ["<", ">", "<=", ">="]):
            return SpecialistRoutingDecision(
                specialist="ScreenerSpecialist",
                method="screen",
                reasoning=f"Fallback: Screening keywords detected. AI error: {error}",
                confidence=0.6,
                extracted_params={"user_query": query},
                estimated_time=3.0
            )

        # DISCOVERY patterns
        if any(kw in query_lower for kw in [
            "tiềm năng", "gợi ý", "khuyến nghị", "recommend",
            "cổ phiếu nào", "nên mua gì", "đáng mua"
        ]) and not symbols:
            return SpecialistRoutingDecision(
                specialist="DiscoverySpecialist",
                method="discover",
                reasoning=f"Fallback: Discovery keywords without specific symbols. AI error: {error}",
                confidence=0.6,
                extracted_params={"user_query": query},
                estimated_time=5.0
            )

        # ALERT patterns
        if any(kw in query_lower for kw in ["cảnh báo", "alert", "thông báo"]):
            method = "get_alerts"
            if any(kw in query_lower for kw in ["tạo", "create", "đặt"]):
                method = "create_alert"
            elif any(kw in query_lower for kw in ["xóa", "delete", "hủy"]):
                method = "delete_alert"

            return SpecialistRoutingDecision(
                specialist="AlertManager",
                method=method,
                reasoning=f"Fallback: Alert keywords detected. AI error: {error}",
                confidence=0.6,
                extracted_params={"user_id": user_id, "symbols": symbols},
                estimated_time=1.5
            )

        # INVESTMENT patterns
        if any(kw in query_lower for kw in [
            "đầu tư", "investment", "tư vấn", "danh mục", "portfolio",
            "triệu", "tỷ", "vốn", "dca"
        ]):
            return SpecialistRoutingDecision(
                specialist="InvestmentPlanner",
                method="create_investment_plan",
                reasoning=f"Fallback: Investment keywords detected. AI error: {error}",
                confidence=0.6,
                extracted_params={"user_id": user_id, "user_query": query},
                estimated_time=5.0
            )

        # SUBSCRIPTION patterns
        if any(kw in query_lower for kw in [
            "theo dõi", "subscribe", "watchlist", "đăng ký"
        ]):
            method = "get_subscriptions"
            if any(kw in query_lower for kw in ["thêm", "add", "tạo"]):
                method = "create_subscription"
            elif any(kw in query_lower for kw in ["xóa", "bỏ", "hủy"]):
                method = "delete_subscription"

            return SpecialistRoutingDecision(
                specialist="SubscriptionManager",
                method=method,
                reasoning=f"Fallback: Subscription keywords detected. AI error: {error}",
                confidence=0.6,
                extracted_params={"user_id": user_id, "symbols": symbols},
                estimated_time=1.5
            )

        # Default: AnalysisSpecialist if has symbols, DiscoverySpecialist if not
        if symbols:
            return SpecialistRoutingDecision(
                specialist="AnalysisSpecialist",
                method="analyze",
                reasoning=f"Fallback: Default to analysis for query with symbols. AI error: {error}",
                confidence=0.5,
                extracted_params={"symbols": symbols, "user_query": query},
                estimated_time=3.0
            )
        else:
            return SpecialistRoutingDecision(
                specialist="DiscoverySpecialist",
                method="discover",
                reasoning=f"Fallback: Default to discovery for general query. AI error: {error}",
                confidence=0.5,
                extracted_params={"user_query": query},
                estimated_time=5.0
            )

    def _extract_symbols(self, query: str) -> List[str]:
        """Extract stock symbols from query"""
        matches = re.findall(r'\b[A-Z]{3,4}\b', query.upper())

        # Common Vietnamese stocks
        common = ["VCB", "FPT", "HPG", "VIC", "VNM", "ACB", "MSN", "TCB", "VHM", "VPB",
                  "MBB", "BID", "CTG", "STB", "HDB", "SSI", "VND", "HCM", "GAS", "PNJ",
                  "MWG", "REE", "DPM", "PVD", "PLX", "PVS", "GVR", "POW", "VJC", "HVN"]

        symbols = []
        for match in matches:
            if match in common or len(match) == 3:
                symbols.append(match)

        return list(set(symbols))

    def get_stats(self) -> Dict:
        """Get routing statistics"""
        total = self.stats["total_routings"]
        return {
            **self.stats,
            "cache_hit_rate": f"{self.stats['cache_hits'] / total * 100:.1f}%" if total > 0 else "0%",
            "ai_success_rate": f"{self.stats['ai_success'] / total * 100:.1f}%" if total > 0 else "0%",
            "fallback_rate": f"{self.stats['fallback_used'] / total * 100:.1f}%" if total > 0 else "0%",
        }

    def clear_cache(self):
        """Clear decision cache"""
        self.decision_cache.clear()


# Convenience function for synchronous usage
def route_query_sync(user_query: str, user_id: str = "default") -> SpecialistRoutingDecision:
    """Synchronous wrapper for routing"""
    router = SpecialistRouter()
    return asyncio.run(router.route(user_query, user_id))
