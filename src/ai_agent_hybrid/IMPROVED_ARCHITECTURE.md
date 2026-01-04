# 🏗️ IMPROVED HYBRID ARCHITECTURE

## 📋 Tổng Quan

Hệ thống Hybrid được cải tiến dựa trên:
- ✅ **OLD System**: Multi-Agent patterns, State Management, Sequential workflows
- ✅ **MCP System**: MCP Protocol, 25 tools, Stateless design
- ✅ **Multi-Agent Best Practices**: 7 yếu tố quan trọng

---

## 🎯 7 YẾU TỐ MULTI-AGENT ĐÃ CẢI THIỆN

### 1️⃣ **Role & Responsibility (5/10 → 9/10)**

#### OLD System Pattern:
```
ROOT_AGENT (Gemini 2.5)
  ├─ Analysis Agent → Phân tích cổ phiếu
  ├─ Screener Agent → Lọc cổ phiếu
  ├─ Alert Agent → Quản lý cảnh báo
  ├─ Subscription Agent → Quản lý đăng ký
  ├─ General Agent → Câu hỏi chung
  └─ Stock Discovery Agent → Tìm cổ phiếu tiềm năng
```

#### NEW Hybrid Architecture:
```
ROUTING_LAYER (ROOT_AGENT)
  ↓
MODE_SELECTION
  ├─ DIRECT_MODE → Simple queries (0.5-1s)
  │   └─ DirectExecutor (pattern matching)
  │
  └─ AGENT_MODE → Complex queries (3-10s)
      ↓
      ORCHESTRATOR_LAYER
        ├─ AnalysisSpecialist
        │   Tools: [get_stock_data, get_financial_data, generate_chart, gemini_search]
        │   Role: Phân tích cổ phiếu (price + fundamental + news)
        │
        ├─ ScreenerSpecialist
        │   Tools: [screen_stocks, filter_stocks, rank_stocks]
        │   Role: Lọc và xếp hạng cổ phiếu
        │
        ├─ InvestmentPlanner
        │   Tools: [gather_profile, calculate_allocation, generate_entry_strategy, risk_management, monitoring]
        │   Role: Tư vấn đầu tư và quản lý danh mục
        │
        ├─ DiscoverySpecialist
        │   Tools: [discover_stocks_by_profile, search_potential_stocks, get_stock_details_from_tcbs]
        │   Role: Tìm cổ phiếu tiềm năng (web search + TCBS data)
        │
        ├─ AlertManager
        │   Tools: [create_alert, get_user_alerts, delete_alert]
        │   Role: Quản lý cảnh báo
        │
        └─ SubscriptionManager
            Tools: [create_subscription, get_user_subscriptions, delete_subscription]
            Role: Quản lý đăng ký
```

**Nguyên tắc:**
- ✅ Mỗi agent CHỈ có 3-6 tools liên quan
- ✅ Clear boundaries: Agent KHÔNG được gọi tools ngoài scope
- ✅ Single Responsibility: 1 agent = 1 domain expertise

---

### 2️⃣ **Coordination & Communication Protocol (2/10 → 9/10)**

#### Message Schema:
```python
@dataclass
class AgentMessage:
    """Standard message format giữa agents"""
    type: Literal["query", "result", "handoff", "error", "request"]
    from_agent: str
    to_agent: Optional[str]  # None = broadcast
    payload: Dict[str, Any]
    priority: int  # 1=low, 5=high, 10=critical
    timestamp: float
    context: Dict[str, Any]  # Shared state reference
```

#### State Machine:
```
[IDLE] → User query
   ↓
[ROUTING] → AI Router decides mode
   ↓
[AGENT_MODE]
   ├─ [PLANNING] → Orchestrator plans workflow
   ├─ [EXECUTING] → Specialists execute tasks
   ├─ [EVALUATING] → Critic evaluates results
   ├─ [ARBITRATING] → Arbitrator resolves conflicts (if needed)
   └─ [RESPONDING] → Format and return
   ↓
[COMPLETED]
```

#### Communication Patterns:

**1. Request-Response:**
```python
Orchestrator → AnalysisSpecialist: "Phân tích VCB"
AnalysisSpecialist → Orchestrator: {result: "..."}
```

**2. Handoff:**
```python
AnalysisSpecialist → ScreenerSpecialist:
  "Tôi đã phân tích VCB. Bạn hãy tìm cổ phiếu tương tự."
```

**3. Broadcast:**
```python
Orchestrator → ALL: "User yêu cầu so sánh VCB, FPT, HPG"
```

**4. State Update:**
```python
AnalysisSpecialist: store_state("VCB_analysis", result)
ScreenerSpecialist: retrieve_state("VCB_analysis")
```

---

### 3️⃣ **Shared Goal + Local Goal (5/10 → 8/10)**

#### Global Goal:
```
Trả lời user query một cách chính xác, đầy đủ và nhanh nhất có thể
```

#### Local Goals:

**AnalysisSpecialist:**
```python
LocalGoal:
  - Phân tích cổ phiếu với confidence > 0.8
  - Sử dụng ≤ 3 tool calls
  - Thời gian ≤ 5s
  - Bao gồm: price analysis + fundamentals + news (nếu có)

AlignmentCheck:
  - Không phân tích quá chi tiết nếu user chỉ hỏi giá đơn giản
  - Không gọi unnecessary tools
```

**ScreenerSpecialist:**
```python
LocalGoal:
  - Lọc cổ phiếu với ≥ 5 results (tối ưu là 10-20)
  - Thời gian ≤ 3s
  - Sử dụng tối đa 3 tiêu chí lọc cùng lúc

AlignmentCheck:
  - Không lọc quá strict → 0 results
  - Ưu tiên thanh khoản cao
```

**InvestmentPlanner:**
```python
LocalGoal:
  - Tạo plan đầy đủ: allocation + entry + risk + monitoring
  - Thời gian ≤ 8s
  - Đề xuất 3-5 stocks

AlignmentCheck:
  - Phù hợp với risk profile của user
  - Phù hợp với vốn của user
```

---

### 4️⃣ **Control Flow & Termination (4/10 → 9/10)**

#### Termination Configuration:
```python
@dataclass
class TerminationConfig:
    """Termination rules for each agent"""
    max_iterations: int = 10
    max_tool_calls: int = 20
    timeout: float = 60.0  # seconds
    max_retries: int = 3
    min_confidence: float = 0.7

    # Stop conditions
    stop_on_error: bool = True
    stop_on_low_confidence: bool = True
    stop_on_timeout: bool = True

    # Agent-specific overrides
    agent_configs: Dict[str, Dict] = field(default_factory=dict)
```

#### Per-Agent Limits:
```python
AGENT_LIMITS = {
    "AnalysisSpecialist": {
        "max_tool_calls": 5,
        "timeout": 10.0,
        "allowed_tools": ["get_stock_data", "get_financial_data", "generate_chart", "gemini_search"]
    },
    "ScreenerSpecialist": {
        "max_tool_calls": 3,
        "timeout": 5.0,
        "allowed_tools": ["screen_stocks", "filter_stocks", "rank_stocks"]
    },
    "InvestmentPlanner": {
        "max_tool_calls": 8,
        "timeout": 15.0,
        "allowed_tools": ["gather_profile", "calculate_allocation", "generate_entry_strategy", ...]
    }
}
```

#### Fail-Safe Mechanisms:
```python
class ExecutionGuard:
    """Protects against infinite loops and runaway agents"""

    def should_stop(self, state: ExecutionState) -> Tuple[bool, str]:
        # 1. Iteration limit
        if state.iterations >= self.config.max_iterations:
            return True, f"Max iterations ({self.config.max_iterations}) reached"

        # 2. Tool call limit
        if state.tool_calls >= self.config.max_tool_calls:
            return True, f"Max tool calls ({self.config.max_tool_calls}) reached"

        # 3. Timeout
        elapsed = time.time() - state.start_time
        if elapsed >= self.config.timeout:
            return True, f"Timeout ({self.config.timeout}s) reached"

        # 4. Error threshold
        if state.error_count >= self.config.max_retries:
            return True, f"Max retries ({self.config.max_retries}) exceeded"

        # 5. Confidence too low
        if state.confidence < self.config.min_confidence:
            return True, f"Confidence ({state.confidence}) below threshold"

        return False, ""
```

---

### 5️⃣ **Tool & Resource Allocation (3/10 → 8/10)**

#### Least Privilege Principle:
```python
TOOL_ALLOCATION = {
    "AnalysisSpecialist": {
        "allowed_tools": [
            "get_stock_data",
            "get_financial_data",
            "generate_chart",
            "gemini_search_and_summarize",
        ],
        "quotas": {
            "gemini_search_and_summarize": 2,  # Max 2 calls per query
            "get_financial_data": 1,            # Max 1 call
        },
        "cost_limit": 0.50  # USD per query
    },

    "ScreenerSpecialist": {
        "allowed_tools": [
            "screen_stocks",
            "filter_stocks_by_criteria",
            "rank_stocks_by_score",
        ],
        "quotas": {
            "screen_stocks": 3,  # Max 3 screening iterations
        },
        "cost_limit": 0.10
    },

    "InvestmentPlanner": {
        "allowed_tools": [
            "gather_investment_profile",
            "calculate_portfolio_allocation",
            "generate_entry_strategy",
            "generate_risk_management_plan",
            "generate_monitoring_plan",
        ],
        "quotas": {
            "gather_investment_profile": 1,
            "calculate_portfolio_allocation": 1,
        },
        "cost_limit": 0.30
    },

    "DiscoverySpecialist": {
        "allowed_tools": [
            "discover_stocks_by_profile",
            "search_potential_stocks",
            "get_stock_details_from_tcbs",
            "gemini_search_and_summarize",
        ],
        "quotas": {
            "gemini_search_and_summarize": 3,
            "get_stock_details_from_tcbs": 10,  # Max 10 stocks
        },
        "cost_limit": 0.40
    }
}
```

#### Resource Monitoring:
```python
class ResourceMonitor:
    """Tracks resource usage per agent"""

    def check_quota(self, agent: str, tool: str) -> bool:
        usage = self.usage[agent][tool]
        quota = TOOL_ALLOCATION[agent]["quotas"].get(tool, float('inf'))
        return usage < quota

    def check_cost_limit(self, agent: str) -> bool:
        cost = self.costs[agent]
        limit = TOOL_ALLOCATION[agent]["cost_limit"]
        return cost < limit

    def enforce_limits(self, agent: str, tool: str) -> None:
        if not self.check_quota(agent, tool):
            raise QuotaExceededError(f"{agent} exceeded quota for {tool}")

        if not self.check_cost_limit(agent):
            raise CostLimitError(f"{agent} exceeded cost limit")
```

---

### 6️⃣ **Evaluation & Arbitration (0/10 → 8/10)**

#### Critic Agent:
```python
class CriticAgent:
    """Đánh giá quality của kết quả"""

    def evaluate(
        self,
        user_query: str,
        agent_response: str,
        context: Dict
    ) -> Evaluation:
        """
        Tiêu chí đánh giá:
        1. Accuracy: Có trả lời đúng câu hỏi không?
        2. Completeness: Có đầy đủ thông tin không?
        3. Relevance: Có liên quan đến query không?
        4. Hallucination: Có thông tin sai lệch không?
        5. Coherence: Có mạch lạc không?
        """

        score = self._score_response(user_query, agent_response, context)

        # Low quality → retry
        if score < 0.7:
            return Evaluation(
                passed=False,
                score=score,
                reason="Response quality below threshold",
                action="RETRY",
                suggestions=["Use more tools", "Get more data"]
            )

        # Hallucination detected
        if self._detect_hallucination(agent_response, context):
            return Evaluation(
                passed=False,
                score=0.3,
                reason="Hallucination detected",
                action="RETRY",
                suggestions=["Verify facts", "Use reliable sources"]
            )

        return Evaluation(passed=True, score=score)
```

#### Arbitration Agent:
```python
class ArbitrationAgent:
    """Giải quyết conflicts giữa agents"""

    def arbitrate(
        self,
        conflicting_results: List[AgentResult]
    ) -> FinalDecision:
        """
        Scenarios:
        1. AnalysisAgent: "VCB - MUA" vs ScreenerAgent: "VCB - BÁN"
        2. Multiple discovery suggestions
        3. Different price predictions
        """

        # Rule-based arbitration
        if self._has_clear_winner(conflicting_results):
            return self._select_winner(conflicting_results)

        # AI-based arbitration (Gemini 2.5)
        return self._ai_arbitrate(conflicting_results)

    def _ai_arbitrate(self, results: List[AgentResult]) -> FinalDecision:
        """Use Gemini to make final decision"""
        prompt = f"""
        Bạn là chuyên gia đầu tư chứng khoán. Hãy phân tích các quan điểm sau:

        {self._format_results(results)}

        Hãy đưa ra quyết định cuối cùng với lý do rõ ràng.
        """

        response = self.client.models.generate_content(...)
        return FinalDecision(
            decision=response.decision,
            reasoning=response.reasoning,
            confidence=response.confidence
        )
```

---

### 7️⃣ **Observability & Debuggability (6/10 → 9/10)**

#### Tracing System:
```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter

class ObservabilityLayer:
    """Comprehensive tracing and logging"""

    def trace_agent_execution(self, agent_name: str, query: str):
        with tracer.start_as_current_span(f"{agent_name}.execute") as span:
            span.set_attribute("agent", agent_name)
            span.set_attribute("query", query)
            span.set_attribute("timestamp", time.time())

            # Trace each step
            with tracer.start_as_current_span("tool_selection"):
                tools = self._select_tools(query)
                span.set_attribute("tools_selected", tools)

            with tracer.start_as_current_span("tool_execution"):
                results = self._execute_tools(tools)
                span.set_attribute("tools_executed", len(results))

            with tracer.start_as_current_span("response_generation"):
                response = self._generate_response(results)
                span.set_attribute("response_length", len(response))

            return response
```

#### Execution Trace:
```
Trace ID: abc123 | User: user_001 | Query: "Phân tích VCB"
├─ 00:00.000 | RootAgent | analyze_query("Phân tích VCB")
├─ 00:00.250 | RootAgent | decision=AGENT_MODE, confidence=0.95
├─ 00:00.300 | Orchestrator | start
├─ 00:00.400 | Orchestrator | select_specialist → AnalysisSpecialist
│  │
│  ├─ 00:00.500 | AnalysisSpecialist | start
│  ├─ 00:00.600 | AnalysisSpecialist | tool_call(get_stock_data, ["VCB"])
│  ├─ 00:01.800 | MCPClient | cache_miss → fetch_from_db
│  ├─ 00:02.100 | AnalysisSpecialist | tool_call(gemini_search, "VCB news")
│  ├─ 00:04.300 | AnalysisSpecialist | generate_response
│  └─ 00:04.500 | AnalysisSpecialist | complete
│
├─ 00:04.600 | CriticAgent | evaluate_result
├─ 00:04.700 | CriticAgent | score=0.9, passed=True
├─ 00:04.800 | Orchestrator | format_response
└─ 00:04.900 | Orchestrator | return_to_user
```

#### Decision Audit Log:
```python
@dataclass
class DecisionLog:
    """Audit log for agent decisions"""
    timestamp: datetime
    agent: str
    decision: str
    reasoning: str
    alternatives_considered: List[str]
    confidence: float
    context: Dict
    outcome: Optional[str] = None

# Example:
DecisionLog(
    timestamp="2025-01-02 10:30:45",
    agent="RootAgent",
    decision="AGENT_MODE",
    reasoning="Query requires analysis with news search",
    alternatives_considered=["DIRECT_MODE"],
    confidence=0.95,
    context={"query": "Phân tích VCB", "complexity": "high"},
    outcome="Success"
)
```

---

## 🏗️ KIẾN TRÚC LAYER

```
┌─────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                         │
│  Discord Bot | Web API | CLI | Telegram Bot                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     ROUTING LAYER                            │
│  RootAgent (Gemini 2.5) → DIRECT_MODE / AGENT_MODE         │
└─────────────────────────────────────────────────────────────┘
                            ↓
            ┌───────────────┴───────────────┐
            ↓                               ↓
┌─────────────────────┐      ┌─────────────────────────────┐
│   DIRECT_MODE       │      │      AGENT_MODE             │
│  DirectExecutor     │      │   Orchestrator Layer        │
│  (Pattern Match)    │      │                             │
│                     │      │  ┌─── AnalysisSpecialist   │
│  - Price queries    │      │  ├─── ScreenerSpecialist   │
│  - Alert CRUD       │      │  ├─── InvestmentPlanner    │
│  - Sub CRUD         │      │  ├─── DiscoverySpecialist  │
│  - Chart gen        │      │  ├─── AlertManager         │
│                     │      │  └─── SubscriptionManager  │
└─────────────────────┘      └─────────────────────────────┘
            │                               │
            │                               ↓
            │              ┌─────────────────────────────┐
            │              │   EVALUATION LAYER          │
            │              │  - CriticAgent              │
            │              │  - ArbitrationAgent         │
            │              └─────────────────────────────┘
            │                               │
            └───────────────┬───────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   STATE MANAGEMENT LAYER                     │
│  - SharedState (ToolContext pattern from OLD)               │
│  - ConversationMemory                                        │
│  - ExecutionState                                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   MCP CLIENT LAYER                           │
│  EnhancedMCPClient with:                                    │
│  - Caching (10x faster)                                     │
│  - Retry logic                                              │
│  - Circuit breaker                                          │
│  - Resource monitoring                                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   MCP SERVER LAYER                           │
│  25 Tools organized by domain                               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      DATA LAYER                              │
│  PostgreSQL + External APIs (TCBS, VNStock)                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 PERFORMANCE TARGETS

| Metric | Target | Measured By |
|--------|--------|-------------|
| Simple Query (DIRECT) | < 1s | DirectExecutor |
| Complex Query (AGENT) | < 10s | OrchestratorAgent |
| Agent Selection Time | < 0.3s | RootAgent |
| Tool Call Overhead | < 0.1s | MCPClient |
| Cache Hit Rate | > 70% | EnhancedMCPClient |
| Error Rate | < 5% | ExecutionGuard |
| Confidence Score | > 0.8 | CriticAgent |

---

## 🚀 NEXT STEPS

1. ✅ Implement Core Components
2. ✅ Implement Specialized Agents
3. ✅ Implement State Management
4. ✅ Implement Evaluation Layer
5. ✅ Add Observability
6. ✅ Build Discord Bot
7. ✅ Testing & Validation
