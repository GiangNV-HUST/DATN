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


@dataclass
class AgentTask:
    """A single task for one agent in a multi-agent workflow"""
    specialist: str
    method: str
    params: Dict = field(default_factory=dict)
    depends_on: Optional[str] = None  # Task ID this depends on
    task_id: str = field(default_factory=lambda: str(id(object())))


@dataclass
class MultiAgentRoutingDecision:
    """
    Decision for multi-agent query handling

    Supports:
    - Single agent (backward compatible)
    - Sequential execution (Agent A -> Agent B)
    - Parallel execution (Agent A & Agent B simultaneously)
    """
    is_multi_agent: bool
    tasks: List[AgentTask]
    execution_mode: Literal["single", "sequential", "parallel"]
    reasoning: str
    confidence: float
    aggregation_strategy: Literal["concatenate", "summarize", "merge"] = "concatenate"
    estimated_total_time: float = 2.0

    @property
    def primary_specialist(self) -> str:
        """Get primary specialist (first task)"""
        return self.tasks[0].specialist if self.tasks else "AnalysisSpecialist"

    def to_single_decision(self) -> SpecialistRoutingDecision:
        """Convert to single routing decision (backward compatible)"""
        task = self.tasks[0] if self.tasks else AgentTask(
            specialist="AnalysisSpecialist",
            method="analyze"
        )
        return SpecialistRoutingDecision(
            specialist=task.specialist,
            method=task.method,
            reasoning=self.reasoning,
            confidence=self.confidence,
            extracted_params=task.params,
            estimated_time=self.estimated_total_time
        )


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
- Lập kế hoạch DCA cho 1 cổ phiếu cụ thể
- Phân bổ danh mục
- Chiến lược đầu tư
- Quản lý rủi ro

**Methods:**
- `create_investment_plan`: Lập kế hoạch đầu tư tổng hợp (nhiều cổ phiếu, danh mục)
- `create_dca_plan`: Kế hoạch DCA cho 1 MÃ CỔ PHIẾU CỤ THỂ (QUAN TRỌNG: dùng khi có 1 mã + từ khóa DCA/hàng tháng/mỗi tháng)

**PHÂN BIỆT METHODS:**
- `create_investment_plan`: Khi KHÔNG có mã cổ phiếu cụ thể hoặc muốn tư vấn danh mục nhiều cổ phiếu
- `create_dca_plan`: Khi CÓ 1 MÃ CỔ PHIẾU CỤ THỂ + muốn mua định kỳ hàng tháng

**Ví dụ queries:**
- "Tôi có 100 triệu muốn đầu tư" → `create_investment_plan` (không có mã cụ thể)
- "Tư vấn danh mục 500 triệu" → `create_investment_plan` (nhiều cổ phiếu)
- "Kế hoạch DCA cho FPT 5 triệu/tháng" → `create_dca_plan` (1 mã + DCA)
- "Lập kế hoạch DCA VCB với 10 triệu mỗi tháng trong 12 tháng" → `create_dca_plan`
- "Nên phân bổ vốn như thế nào với 1 tỷ?" → `create_investment_plan`

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
**Chức năng:** So sánh nhiều cổ phiếu CỤ THỂ (có MÃ cổ phiếu rõ ràng)
**Sử dụng khi:**
- So sánh 2 hoặc nhiều cổ phiếu CỤ THỂ với MÃ CỔ PHIẾU (VCB, TCB, FPT, HPG...)
- Peer comparison (so sánh cổ phiếu cụ thể trong cùng ngành)
- Relative valuation (định giá tương đối giữa các mã)
- Hỏi cổ phiếu nào tốt hơn khi có 2+ MÃ

**KHÔNG SỬ DỤNG KHI:**
- So sánh NGÀNH với nhau (ví dụ: ngành ngân hàng vs ngành công nghệ) → Dùng MarketContextSpecialist
- Không có MÃ cổ phiếu cụ thể → Dùng MarketContextSpecialist hoặc DiscoverySpecialist

**Methods:**
- `analyze`: So sánh cổ phiếu (default)
- `peer_analysis`: So sánh với peer trong ngành

**Ví dụ queries:**
- "So sánh VCB với TCB" → symbols: ["VCB", "TCB"]
- "FPT hay CMG tốt hơn?" → symbols: ["FPT", "CMG"]
- "So sánh P/E của VCB, TCB, MBB" → symbols: ["VCB", "TCB", "MBB"]
- "VCB và TCB cái nào đáng mua hơn?" → symbols: ["VCB", "TCB"]

## PHÂN BIỆT QUAN TRỌNG:

### ScreenerSpecialist vs DiscoverySpecialist:
- **Screener**: Có TIÊU CHÍ CỤ THỂ với SỐ LIỆU (P/E < 15, ROE > 20%, PE < 10, PB < 2, top thanh khoản)
  - Khi có các toán tử <, >, <=, >= với số → LUÔN là Screener
  - Khi hỏi "cổ phiếu giá trị" + tiêu chí số → Screener
- **Discovery**: KHÔNG có tiêu chí số cụ thể, hỏi chung chung (cổ phiếu nào hay, gợi ý, tiềm năng)

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

### MarketContextSpecialist vs ComparisonSpecialist:
- **MarketContext**: So sánh NGÀNH với nhau (ngân hàng vs công nghệ, bất động sản vs xây dựng)
  - "So sánh hiệu suất ngành ngân hàng và công nghệ" → MarketContext (get_sector_performance)
  - "Ngành nào đang tốt hơn?" → MarketContext
- **Comparison**: So sánh CỔ PHIẾU CỤ THỂ với MÃ (VCB vs TCB, FPT vs CMG)
  - "So sánh VCB với TCB" → Comparison (có mã cụ thể)
  - Bắt buộc phải có ít nhất 2 MÃ CỔ PHIẾU (3 chữ in hoa) mới dùng Comparison

## COMPANY NAME TO SYMBOL MAPPING (QUAN TRỌNG):

Khi user nhắc đến TÊN CÔNG TY thay vì MÃ, hãy convert sang MÃ CỔ PHIẾU:
- Vietcombank, VCB Bank, Ngoại Thương → VCB
- FPT Corporation, FPT Software → FPT
- Hòa Phát, Hoa Phat → HPG
- Vingroup, Vin Group → VIC
- Vinamilk, Sữa Việt Nam → VNM
- Techcombank, TCB Bank → TCB
- ACB Bank, Á Châu → ACB
- Masan, MSN Group → MSN
- Vinhomes → VHM
- VPBank, VP Bank → VPB
- MBBank, MB Bank, Quân Đội → MBB
- BIDV, Đầu tư Phát triển → BID
- Vietinbank, Công Thương → CTG
- Sacombank → STB
- HDBank → HDB
- SSI Securities → SSI
- VNDirect → VND
- PetroVietnam Gas → GAS
- PNJ, Phú Nhuận → PNJ
- Mobile World, Thế Giới Di Động → MWG

## OUTPUT FORMAT:

Trả về JSON với cấu trúc:
{
  "specialist": "AnalysisSpecialist" | "ScreenerSpecialist" | "AlertManager" | "InvestmentPlanner" | "DiscoverySpecialist" | "SubscriptionManager" | "MarketContextSpecialist" | "ComparisonSpecialist",
  "method": "method_name",
  "reasoning": "Giải thích ngắn gọn",
  "confidence": 0.95,
  "extracted_params": {
    "symbols": ["VCB", "FPT"],  // LUÔN extract symbols nếu có (kể cả từ tên công ty)
    "capital": 100000000,       // Số tiền (convert: 100 triệu = 100000000, 1.5 tỷ = 1500000000)
    "conditions": {},           // Điều kiện lọc cho Screener
    "alert_type": "price",      // Loại alert: price, indicator, volume
    "alert_condition": "above", // above hoặc below
    "target_value": 95000       // Giá mục tiêu cho alert
  },
  "estimated_time": 2.0
}

## QUY TẮC:
1. Luôn trả về VALID JSON, không thêm text khác
2. confidence > 0.9 nếu chắc chắn
3. **QUAN TRỌNG**: Luôn extract symbols từ cả MÃ (VCB, FPT) và TÊN CÔNG TY (Vietcombank, FPT Corporation)
4. Convert số tiền: "100 triệu" → 100000000, "1.5 tỷ" → 1500000000
5. Nếu không chắc, ưu tiên AnalysisSpecialist cho queries về cổ phiếu cụ thể
6. Nếu không chắc và không có mã cụ thể, ưu tiên DiscoverySpecialist

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

        # SCREENING patterns - check BEFORE Discovery
        # Important: any query with numeric conditions (<, >, PE, ROE, PB) should go to Screener
        has_numeric_condition = any(op in query for op in ["<", ">", "<=", ">="])
        has_metric_keywords = any(kw in query_lower for kw in ["pe", "p/e", "roe", "pb", "p/b", "eps", "rsi"])

        if any(kw in query_lower for kw in [
            "lọc", "loc", "sàng lọc", "screen", "top", "filter",
            "thanh khoản", "vốn hóa", "tăng mạnh", "giảm mạnh",
            "giá trị"  # "cổ phiếu giá trị" with conditions = value investing screen
        ]) or has_numeric_condition or has_metric_keywords:
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
            # Check if this is a DCA query for single stock
            is_dca_query = "dca" in query_lower or any(kw in query_lower for kw in [
                "mỗi tháng", "moi thang", "hàng tháng", "hang thang",
                "định kỳ", "dinh ky", "/tháng", "/thang"
            ])

            if is_dca_query and len(symbols) == 1:
                return SpecialistRoutingDecision(
                    specialist="InvestmentPlanner",
                    method="create_dca_plan",
                    reasoning=f"Fallback: DCA keywords with single stock detected. AI error: {error}",
                    confidence=0.7,
                    extracted_params={
                        "symbol": symbols[0],
                        "monthly_investment": 5_000_000,
                        "duration_months": 12,
                        "price_trend": "neutral"
                    },
                    estimated_time=3.0
                )

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

        # Vietnamese words to exclude (commonly misidentified as symbols)
        exclude = {"KHI", "NEN", "CAI", "NAO", "XEM", "MUA", "BAN", "GIA", "HON", "TOT",
                   "HAY", "ROI", "SAU", "CHO", "VAN", "THE", "NAY", "TAO", "TEN", "MOT",
                   "HAI", "BAO", "VON", "LOC", "TOP", "HOT", "TAT", "MAT", "DAU", "TRI",
                   "TIN", "HOM", "QUA", "NAM", "CUA", "LAM", "CON", "RAT", "NHO", "LON",
                   "DCA", "VOI", "MOI", "LAP", "KHO", "TUY", "TAN", "DEN", "SAN", "CAN",
                   "CHI", "GOI", "THI", "TUC", "VAY", "COT", "CAO", "KEO", "DUA", "NUA"}

        symbols = []
        for match in matches:
            if match in exclude:
                continue
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

    def _get_multi_agent_system_prompt(self) -> str:
        """Get system prompt for multi-agent routing"""
        return """Ban la MULTI-AGENT ROUTER - Bo dieu phoi thong minh cho he thong phan tich chung khoan Viet Nam.

## NHIEM VU:
Phan tich query cua user va quyet dinh:
1. Can 1 hay nhieu specialist de tra loi?
2. Neu nhieu specialist, nen chay TUAN TU hay SONG SONG?
3. Ket qua se duoc tong hop nhu the nao?

## 8 SPECIALISTS:

1. **AnalysisSpecialist** - Phan tich 1 co phieu cu the (gia, ky thuat, co ban)
2. **ScreenerSpecialist** - Loc co phieu theo tieu chi (P/E < 15, ROE > 20%)
3. **AlertManager** - Quan ly canh bao gia
4. **InvestmentPlanner** - Tu van dau tu, phan bo danh muc, DCA (create_dca_plan khi co 1 ma cu the)
5. **DiscoverySpecialist** - Goi y co phieu tiem nang
6. **SubscriptionManager** - Quan ly watchlist
7. **MarketContextSpecialist** - Tong quan thi truong (VN-Index, nganh)
8. **ComparisonSpecialist** - So sanh 2+ co phieu cu the

## CAC TRUONG HOP CAN NHIEU AGENTS:

### SEQUENTIAL (Tuan tu - Agent A xong roi Agent B):
1. **Loc roi phan tich**: "Loc co phieu P/E < 15, sau do phan tich chi tiet"
   - ScreenerSpecialist -> AnalysisSpecialist

2. **Loc roi tu van dau tu**: "Loc co phieu tot, sau do lap ke hoach dau tu 100 trieu"
   - ScreenerSpecialist -> InvestmentPlanner

3. **Thi truong roi goi y**: "VN-Index hom nay the nao? Goi y co phieu dang mua"
   - MarketContextSpecialist -> DiscoverySpecialist

4. **Phan tich roi so sanh**: "Phan tich VCB va TCB, roi so sanh xem cai nao tot hon"
   - AnalysisSpecialist -> ComparisonSpecialist

### PARALLEL (Song song - Agent A & B cung luc):
1. **Thi truong + Goi y doc lap**: "Tong quan thi truong va goi y co phieu ngan hang"
   - MarketContextSpecialist || DiscoverySpecialist

2. **Phan tich nhieu ma doc lap**: "Phan tich VCB, FPT, HPG" (khong so sanh)
   - Co the chay parallel neu khong can so sanh

### SINGLE (Chi 1 agent):
- Cau hoi don gian chi can 1 specialist
- Vi du: "Gia VCB hom nay?", "Loc co phieu P/E < 15", "Canh bao cua toi"

## COMPANY NAME TO SYMBOL (QUAN TRONG):
Convert TEN CONG TY sang MA:
- Vietcombank/Ngoai Thuong -> VCB
- FPT Corporation -> FPT
- Hoa Phat -> HPG
- Vingroup -> VIC
- Vinamilk -> VNM
- Techcombank -> TCB
- MBBank/Quan Doi -> MBB
- BIDV -> BID
- Vietinbank -> CTG
- Thế Giới Di Động -> MWG

## OUTPUT FORMAT:

```json
{
  "is_multi_agent": true/false,
  "execution_mode": "single" | "sequential" | "parallel",
  "tasks": [
    {
      "specialist": "ScreenerSpecialist",
      "method": "screen",
      "params": {"user_query": "...", "symbols": ["VCB"]},
      "task_id": "task_1",
      "depends_on": null
    },
    {
      "specialist": "InvestmentPlanner",
      "method": "create_investment_plan",
      "params": {"capital": 100000000},
      "task_id": "task_2",
      "depends_on": "task_1"
    }
  ],
  "reasoning": "Giai thich ngan gon",
  "confidence": 0.95,
  "aggregation_strategy": "concatenate" | "summarize" | "merge",
  "estimated_total_time": 5.0
}
```

## QUY TAC:
1. Mac dinh la SINGLE agent neu khong ro rang can nhieu
2. Chi dung SEQUENTIAL khi task_2 CAN ket qua cua task_1
3. Dung PARALLEL khi cac tasks doc lap
4. **QUAN TRONG**: Luon extract symbols tu CA ma (VCB) va TEN CONG TY (Vietcombank)
5. Convert so tien: "100 trieu" -> 100000000, "1.5 ty" -> 1500000000
6. Luon tra ve VALID JSON

PHAN TICH QUERY VA TRA VE JSON:"""

    def _quick_multi_agent_check(self, query: str) -> Optional[MultiAgentRoutingDecision]:
        """
        Quick pattern-based check for multi-agent queries (< 1ms)

        Returns MultiAgentRoutingDecision if pattern matches, None otherwise.
        This avoids expensive AI call for obvious multi-agent patterns.
        """
        query_lower = query.lower()
        symbols = self._extract_symbols(query)

        # Pattern 1: "loc/screen ... sau do ... dau tu/tu van" -> Screen + Invest
        if any(kw in query_lower for kw in ["lọc", "loc", "sàng lọc", "screen"]) and \
           any(kw in query_lower for kw in ["sau đó", "sau do", "rồi", "roi", "tiếp", "tiep"]) and \
           any(kw in query_lower for kw in ["đầu tư", "dau tu", "tư vấn", "tu van", "kế hoạch", "ke hoach"]):
            return MultiAgentRoutingDecision(
                is_multi_agent=True,
                tasks=[
                    AgentTask(specialist="ScreenerSpecialist", method="screen",
                              params={"user_query": query}, task_id="screen_1"),
                    AgentTask(specialist="InvestmentPlanner", method="create_investment_plan",
                              params={"user_query": query}, depends_on="screen_1", task_id="invest_2")
                ],
                execution_mode="sequential",
                reasoning="Quick pattern: Screen + Invest",
                confidence=0.85,
                estimated_total_time=8.0
            )

        # Pattern 2: "thi truong ... goi y" -> Market + Discovery (parallel)
        if any(kw in query_lower for kw in ["thị trường", "thi truong", "vn-index", "vnindex"]) and \
           any(kw in query_lower for kw in ["gợi ý", "goi y", "khuyến nghị", "nên mua", "nen mua", "đáng mua"]):
            return MultiAgentRoutingDecision(
                is_multi_agent=True,
                tasks=[
                    AgentTask(specialist="MarketContextSpecialist", method="analyze",
                              params={"user_query": query}, task_id="market_1"),
                    AgentTask(specialist="DiscoverySpecialist", method="discover",
                              params={"user_query": query}, task_id="discover_2")
                ],
                execution_mode="parallel",  # These are independent, run parallel
                reasoning="Quick pattern: Market + Discovery (parallel)",
                confidence=0.85,
                estimated_total_time=5.0
            )

        # Pattern 3a: Pure comparison (no "phan tich") -> ComparisonSpecialist ONLY
        # "So sanh VCB va TCB" -> Just use ComparisonSpecialist (it fetches data internally)
        if len(symbols) >= 2 and \
           any(kw in query_lower for kw in ["so sánh", "so sanh", "vs", "hay", "tốt hơn", "tot hon"]) and \
           not any(kw in query_lower for kw in ["phân tích", "phan tich", "chi tiết", "chi tiet"]):
            return MultiAgentRoutingDecision(
                is_multi_agent=False,  # Single agent is enough
                tasks=[
                    AgentTask(specialist="ComparisonSpecialist", method="analyze",
                              params={"symbols": symbols, "user_query": query},
                              task_id="compare")
                ],
                execution_mode="single",
                reasoning="Quick pattern: Pure comparison (ComparisonSpecialist only)",
                confidence=0.90,
                estimated_total_time=3.0
            )

        # Pattern 3b: "phan tich X va Y ... so sanh" -> Analysis + Compare (sequential)
        # OPTIMIZATION: Run analysis for all symbols at once, then compare
        if len(symbols) >= 2 and \
           any(kw in query_lower for kw in ["phân tích", "phan tich"]) and \
           any(kw in query_lower for kw in ["so sánh", "so sanh", "tốt hơn", "tot hon"]):
            # Create analysis task for ALL symbols at once (agent handles multiple)
            # Then compare based on analysis results
            return MultiAgentRoutingDecision(
                is_multi_agent=True,
                tasks=[
                    # Single analysis task with all symbols (more efficient)
                    AgentTask(specialist="AnalysisSpecialist", method="analyze",
                              params={"symbols": symbols, "user_query": f"Phan tich {', '.join(symbols)}"},
                              task_id="analyze_all"),
                    AgentTask(specialist="ComparisonSpecialist", method="analyze",
                              params={"symbols": symbols, "user_query": query},
                              depends_on="analyze_all", task_id="compare")
                ],
                execution_mode="sequential",
                reasoning="Quick pattern: Analysis (all symbols) + Compare",
                confidence=0.85,
                estimated_total_time=6.0  # Faster than analyzing each separately
            )

        # Pattern 4: "loc ... phan tich chi tiet" -> Screen + Analysis
        if any(kw in query_lower for kw in ["lọc", "loc", "top"]) and \
           any(kw in query_lower for kw in ["phân tích", "phan tich", "chi tiết", "chi tiet"]):
            return MultiAgentRoutingDecision(
                is_multi_agent=True,
                tasks=[
                    AgentTask(specialist="ScreenerSpecialist", method="screen",
                              params={"user_query": query}, task_id="screen_1"),
                    AgentTask(specialist="AnalysisSpecialist", method="analyze",
                              params={"user_query": query}, depends_on="screen_1", task_id="analyze_2")
                ],
                execution_mode="sequential",
                reasoning="Quick pattern: Screen + Analysis",
                confidence=0.85,
                estimated_total_time=8.0
            )

        # Pattern 5: 3+ intents - Complex queries with market + discovery + investment
        # "Đánh giá thị trường và đề xuất cổ phiếu tiềm năng và lập kế hoạch đầu tư"
        has_market = any(kw in query_lower for kw in ["thị trường", "thi truong", "vn-index", "vnindex", "đánh giá", "danh gia", "tổng quan", "tong quan"])
        has_discovery = any(kw in query_lower for kw in ["gợi ý", "goi y", "đề xuất", "de xuat", "tiềm năng", "tiem nang", "khuyến nghị", "khuyen nghi", "nên mua", "nen mua"])
        has_investment = any(kw in query_lower for kw in ["đầu tư", "dau tu", "kế hoạch", "ke hoach", "phân bổ", "phan bo", "danh mục", "danh muc", "chiến lược", "chien luoc"])
        has_screening = any(kw in query_lower for kw in ["lọc", "loc", "sàng lọc", "screen", "top", "filter"])
        has_analysis = any(kw in query_lower for kw in ["phân tích", "phan tich", "chi tiết", "chi tiet"]) and bool(symbols)

        # Count how many intent types
        intent_count = sum([has_market, has_discovery, has_investment, has_screening, has_analysis])

        if intent_count >= 3:
            # Build tasks based on detected intents
            tasks = []
            task_num = 1

            # Order: Market -> Screen/Discovery -> Analysis -> Investment (logical flow)
            if has_market:
                tasks.append(AgentTask(
                    specialist="MarketContextSpecialist",
                    method="analyze",
                    params={"user_query": query},
                    task_id=f"task_{task_num}"
                ))
                task_num += 1

            if has_screening:
                prev_id = tasks[-1].task_id if tasks else None
                tasks.append(AgentTask(
                    specialist="ScreenerSpecialist",
                    method="screen",
                    params={"user_query": query},
                    depends_on=prev_id,
                    task_id=f"task_{task_num}"
                ))
                task_num += 1
            elif has_discovery:
                prev_id = tasks[-1].task_id if tasks else None
                tasks.append(AgentTask(
                    specialist="DiscoverySpecialist",
                    method="discover",
                    params={"user_query": query},
                    depends_on=prev_id,
                    task_id=f"task_{task_num}"
                ))
                task_num += 1

            if has_analysis and symbols:
                prev_id = tasks[-1].task_id if tasks else None
                tasks.append(AgentTask(
                    specialist="AnalysisSpecialist",
                    method="analyze",
                    params={"symbols": symbols, "user_query": query},
                    depends_on=prev_id,
                    task_id=f"task_{task_num}"
                ))
                task_num += 1

            if has_investment:
                prev_id = tasks[-1].task_id if tasks else None
                tasks.append(AgentTask(
                    specialist="InvestmentPlanner",
                    method="create_investment_plan",
                    params={"user_query": query},
                    depends_on=prev_id,
                    task_id=f"task_{task_num}"
                ))
                task_num += 1

            if len(tasks) >= 2:
                return MultiAgentRoutingDecision(
                    is_multi_agent=True,
                    tasks=tasks,
                    execution_mode="sequential",
                    reasoning=f"Quick pattern: Complex {intent_count}-intent query (market={has_market}, screen={has_screening}, discover={has_discovery}, analysis={has_analysis}, invest={has_investment})",
                    confidence=0.80,
                    aggregation_strategy="concatenate",
                    estimated_total_time=5.0 * len(tasks)
                )

        # Pattern 6: Market + Discovery + Investment (common combo)
        if has_market and has_discovery and has_investment:
            return MultiAgentRoutingDecision(
                is_multi_agent=True,
                tasks=[
                    AgentTask(specialist="MarketContextSpecialist", method="analyze",
                              params={"user_query": query}, task_id="market_1"),
                    AgentTask(specialist="DiscoverySpecialist", method="discover",
                              params={"user_query": query}, depends_on="market_1", task_id="discover_2"),
                    AgentTask(specialist="InvestmentPlanner", method="create_investment_plan",
                              params={"user_query": query}, depends_on="discover_2", task_id="invest_3")
                ],
                execution_mode="sequential",
                reasoning="Quick pattern: Market + Discovery + Investment (3 agents)",
                confidence=0.85,
                estimated_total_time=15.0
            )

        # Pattern 7: Screen + Analysis + Investment (common combo)
        if has_screening and has_analysis and has_investment:
            return MultiAgentRoutingDecision(
                is_multi_agent=True,
                tasks=[
                    AgentTask(specialist="ScreenerSpecialist", method="screen",
                              params={"user_query": query}, task_id="screen_1"),
                    AgentTask(specialist="AnalysisSpecialist", method="analyze",
                              params={"user_query": query}, depends_on="screen_1", task_id="analyze_2"),
                    AgentTask(specialist="InvestmentPlanner", method="create_investment_plan",
                              params={"user_query": query}, depends_on="analyze_2", task_id="invest_3")
                ],
                execution_mode="sequential",
                reasoning="Quick pattern: Screen + Analysis + Investment (3 agents)",
                confidence=0.85,
                estimated_total_time=15.0
            )

        # Pattern 8: DCA for single stock - "DCA cho FPT 5 trieu/thang"
        # This should route to InvestmentPlanner.create_dca_plan
        is_dca_query = "dca" in query_lower or any(kw in query_lower for kw in [
            "mỗi tháng", "moi thang", "hàng tháng", "hang thang",
            "định kỳ", "dinh ky", "/tháng", "/thang", "tích lũy", "tich luy"
        ])

        if is_dca_query and len(symbols) == 1:
            # Extract DCA params
            import re
            monthly = 5_000_000  # Default 5M
            duration = 12  # Default 12 months

            # Extract monthly amount
            monthly_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(triệu|trieu|tr)', query_lower)
            if monthly_match:
                monthly = int(float(monthly_match.group(1).replace(",", ".")) * 1_000_000)

            # Extract duration
            duration_match = re.search(r'(\d+)\s*(?:tháng|thang|month)', query_lower)
            if duration_match:
                duration = int(duration_match.group(1))

            return MultiAgentRoutingDecision(
                is_multi_agent=False,
                tasks=[
                    AgentTask(
                        specialist="InvestmentPlanner",
                        method="create_dca_plan",
                        params={
                            "symbol": symbols[0],
                            "monthly_investment": monthly,
                            "duration_months": duration,
                            "price_trend": "neutral"
                        },
                        task_id="dca_plan"
                    )
                ],
                execution_mode="single",
                reasoning=f"Quick pattern: DCA plan for single stock {symbols[0]}",
                confidence=0.95,
                estimated_total_time=3.0
            )

        return None  # No quick pattern matched, need AI routing

    async def route_multi_agent(
        self,
        user_query: str,
        user_id: str = "default",
        use_quick_check: bool = True
    ) -> MultiAgentRoutingDecision:
        """
        Route user query with multi-agent support

        Optimized flow:
        1. Check cache (instant)
        2. Try quick pattern matching (< 1ms)
        3. Fall back to AI routing if needed (~2-3s)

        Args:
            user_query: User's question
            user_id: User ID for context
            use_quick_check: If True, try pattern matching first (default True)

        Returns:
            MultiAgentRoutingDecision with tasks and execution mode
        """
        start_time = time.time()

        # Check cache for multi-agent decisions
        cache_key = f"multi:{user_id}:{user_query}"
        if self.use_cache and cache_key in self.decision_cache:
            self.stats["cache_hits"] += 1
            return self.decision_cache[cache_key]

        # Try quick pattern matching first (< 1ms)
        if use_quick_check:
            quick_result = self._quick_multi_agent_check(user_query)
            if quick_result is not None:
                self.stats["total_routings"] += 1
                if self.use_cache:
                    self.decision_cache[cache_key] = quick_result
                return quick_result

        try:
            # Call OpenAI for multi-agent routing
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self._get_multi_agent_system_prompt()},
                    {"role": "user", "content": user_query}
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
                max_tokens=800
            )

            response_text = response.choices[0].message.content
            decision = self._parse_multi_agent_decision(response_text, user_query)

            # Update stats
            self.stats["ai_success"] += 1
            self.stats["total_routings"] += 1

            # Cache decision
            if self.use_cache:
                self.decision_cache[cache_key] = decision

            return decision

        except Exception as e:
            # Fallback to single-agent routing
            self.stats["ai_failures"] += 1
            self.stats["fallback_used"] += 1
            return self._fallback_multi_agent_routing(user_query, user_id, str(e))

    def _parse_multi_agent_decision(self, response_text: str, user_query: str) -> MultiAgentRoutingDecision:
        """Parse AI response into MultiAgentRoutingDecision"""
        try:
            data = json.loads(response_text)

            tasks = []
            for task_data in data.get("tasks", []):
                task = AgentTask(
                    specialist=task_data["specialist"],
                    method=task_data.get("method", "analyze"),
                    params=task_data.get("params", {"user_query": user_query}),
                    depends_on=task_data.get("depends_on"),
                    task_id=task_data.get("task_id", str(len(tasks)))
                )
                # Ensure user_query is in params
                if "user_query" not in task.params:
                    task.params["user_query"] = user_query
                tasks.append(task)

            # Ensure at least one task
            if not tasks:
                tasks = [AgentTask(
                    specialist="AnalysisSpecialist",
                    method="analyze",
                    params={"user_query": user_query}
                )]

            return MultiAgentRoutingDecision(
                is_multi_agent=data.get("is_multi_agent", len(tasks) > 1),
                tasks=tasks,
                execution_mode=data.get("execution_mode", "single"),
                reasoning=data.get("reasoning", ""),
                confidence=float(data.get("confidence", 0.8)),
                aggregation_strategy=data.get("aggregation_strategy", "concatenate"),
                estimated_total_time=float(data.get("estimated_total_time", 3.0))
            )

        except Exception as e:
            raise ValueError(f"Failed to parse multi-agent decision: {e}\nResponse: {response_text}")

    def _fallback_multi_agent_routing(
        self, query: str, user_id: str, error: str
    ) -> MultiAgentRoutingDecision:
        """
        Fallback multi-agent routing using pattern matching

        Detects common multi-agent patterns in Vietnamese queries.
        """
        query_lower = query.lower()
        symbols = self._extract_symbols(query)

        # Pattern 1: Screen then invest ("loc ... sau do dau tu/tu van")
        if any(kw in query_lower for kw in ["lọc", "loc", "sàng lọc"]) and \
           any(kw in query_lower for kw in ["đầu tư", "dau tu", "tư vấn", "tu van", "kế hoạch", "ke hoach"]):
            return MultiAgentRoutingDecision(
                is_multi_agent=True,
                tasks=[
                    AgentTask(
                        specialist="ScreenerSpecialist",
                        method="screen",
                        params={"user_query": query},
                        task_id="screen_1"
                    ),
                    AgentTask(
                        specialist="InvestmentPlanner",
                        method="create_investment_plan",
                        params={"user_query": query, "user_id": user_id},
                        depends_on="screen_1",
                        task_id="invest_2"
                    )
                ],
                execution_mode="sequential",
                reasoning=f"Fallback: Detected screen + invest pattern. Error: {error}",
                confidence=0.7,
                aggregation_strategy="concatenate",
                estimated_total_time=8.0
            )

        # Pattern 2: Market context then discover ("thi truong ... goi y")
        if any(kw in query_lower for kw in ["thị trường", "thi truong", "vn-index", "vnindex"]) and \
           any(kw in query_lower for kw in ["gợi ý", "goi y", "khuyến nghị", "khuyen nghi", "nên mua", "nen mua"]):
            return MultiAgentRoutingDecision(
                is_multi_agent=True,
                tasks=[
                    AgentTask(
                        specialist="MarketContextSpecialist",
                        method="analyze",
                        params={"user_query": query},
                        task_id="market_1"
                    ),
                    AgentTask(
                        specialist="DiscoverySpecialist",
                        method="discover",
                        params={"user_query": query},
                        depends_on="market_1",
                        task_id="discover_2"
                    )
                ],
                execution_mode="sequential",
                reasoning=f"Fallback: Detected market + discover pattern. Error: {error}",
                confidence=0.7,
                aggregation_strategy="concatenate",
                estimated_total_time=8.0
            )

        # Pattern 3: Analyze then compare ("phan tich ... so sanh")
        if len(symbols) >= 2 and \
           any(kw in query_lower for kw in ["phân tích", "phan tich"]) and \
           any(kw in query_lower for kw in ["so sánh", "so sanh", "tốt hơn", "tot hon"]):
            return MultiAgentRoutingDecision(
                is_multi_agent=True,
                tasks=[
                    AgentTask(
                        specialist="AnalysisSpecialist",
                        method="analyze",
                        params={"symbols": symbols, "user_query": query},
                        task_id="analyze_1"
                    ),
                    AgentTask(
                        specialist="ComparisonSpecialist",
                        method="analyze",
                        params={"symbols": symbols, "user_query": query},
                        depends_on="analyze_1",
                        task_id="compare_2"
                    )
                ],
                execution_mode="sequential",
                reasoning=f"Fallback: Detected analyze + compare pattern. Error: {error}",
                confidence=0.7,
                aggregation_strategy="concatenate",
                estimated_total_time=8.0
            )

        # Pattern 4: Screen then analyze ("loc ... phan tich chi tiet")
        if any(kw in query_lower for kw in ["lọc", "loc", "top"]) and \
           any(kw in query_lower for kw in ["phân tích", "phan tich", "chi tiết", "chi tiet"]):
            return MultiAgentRoutingDecision(
                is_multi_agent=True,
                tasks=[
                    AgentTask(
                        specialist="ScreenerSpecialist",
                        method="screen",
                        params={"user_query": query},
                        task_id="screen_1"
                    ),
                    AgentTask(
                        specialist="AnalysisSpecialist",
                        method="analyze",
                        params={"user_query": query},
                        depends_on="screen_1",
                        task_id="analyze_2"
                    )
                ],
                execution_mode="sequential",
                reasoning=f"Fallback: Detected screen + analyze pattern. Error: {error}",
                confidence=0.7,
                aggregation_strategy="concatenate",
                estimated_total_time=8.0
            )

        # Default: Single agent routing
        single_decision = self._fallback_routing(query, user_id, error)
        return MultiAgentRoutingDecision(
            is_multi_agent=False,
            tasks=[AgentTask(
                specialist=single_decision.specialist,
                method=single_decision.method,
                params=single_decision.extracted_params
            )],
            execution_mode="single",
            reasoning=single_decision.reasoning,
            confidence=single_decision.confidence,
            estimated_total_time=single_decision.estimated_time
        )


# Convenience function for synchronous usage
def route_query_sync(user_query: str, user_id: str = "default") -> SpecialistRoutingDecision:
    """Synchronous wrapper for routing"""
    router = SpecialistRouter()
    return asyncio.run(router.route(user_query, user_id))
