"""
Task-Based Model Selector
Phân loại query thành task types và chọn model phù hợp
"""

from enum import Enum
from typing import Dict, Optional
import json


class TaskType(Enum):
    """Task types trong hệ thống"""
    DATA_QUERY = "data_query"           # Simple data lookup
    SCREENING = "screening"              # Filter stocks by criteria
    ANALYSIS = "analysis"                # Technical/fundamental analysis
    ADVISORY = "advisory"                # Investment advice, recommendations
    DISCOVERY = "discovery"              # Search, explore stocks
    CRUD = "crud"                        # Create/update/delete operations
    CONVERSATION = "conversation"        # General chat, greetings


class TaskBasedModelSelector:
    """
    Task-based model selection strategy

    Phân loại query → chọn model tối ưu cho task type
    """

    # Task → Model mapping (4 models)
    TASK_MODEL_MAP = {
        TaskType.DATA_QUERY: "gemini-flash",      # Simple, fast, cheap (Gemini 2.0 Flash)
        TaskType.SCREENING: "claude-sonnet",      # Medium-high complexity (Claude Sonnet 4.5)
        TaskType.ANALYSIS: "claude-sonnet",       # Complex reasoning (Claude Sonnet 4.5)
        TaskType.ADVISORY: "gpt-4o",              # Creative planning (GPT-4o)
        TaskType.DISCOVERY: "claude-opus",        # Most complex, deep analysis (Claude Opus 4.5)
        TaskType.CRUD: "gemini-flash",            # Simple operations (Gemini 2.0 Flash)
        TaskType.CONVERSATION: "gemini-flash"     # General chat (Gemini 2.0 Flash)
    }

    # Model costs (per 1M tokens) - Updated for 2025 (4 models)
    MODEL_COSTS = {
        "gemini-flash": {"input": 0.000075, "output": 0.0003},      # Gemini 2.0 Flash
        "claude-sonnet": {"input": 0.003, "output": 0.015},         # Claude Sonnet 4.5
        "claude-opus": {"input": 0.015, "output": 0.075},           # Claude Opus 4.5
        "gpt-4o": {"input": 0.0025, "output": 0.01}                 # GPT-4o
    }

    # Classification keywords for quick matching
    TASK_KEYWORDS = {
        TaskType.DATA_QUERY: [
            "giá", "price", "volume", "khối lượng",
            "là bao nhiêu", "what is", "bao nhiêu",
            "hiện tại", "current", "latest",
            "thông tin", "info", "information"
        ],
        TaskType.SCREENING: [
            "lọc", "filter", "tìm", "find", "search",
            "cổ phiếu nào", "stocks that",
            "rsi", "pe", "roe", "macd",
            "điều kiện", "criteria", "conditions"
        ],
        TaskType.ANALYSIS: [
            "phân tích", "analyze", "analysis",
            "đánh giá", "evaluate", "assessment",
            "kỹ thuật", "technical", "cơ bản", "fundamental",
            "xu hướng", "trend", "momentum"
        ],
        TaskType.ADVISORY: [
            "tư vấn", "advise", "advisory",
            "nên", "should", "khuyến nghị", "recommend",
            "mua", "buy", "bán", "sell", "giữ", "hold",
            "đầu tư", "invest", "investment"
        ],
        TaskType.DISCOVERY: [
            "khám phá", "discover", "tìm kiếm", "explore",
            "tiềm năng", "potential", "tốt nhất", "best",
            "công nghệ", "technology", "ngành", "sector"
        ],
        TaskType.CRUD: [
            "tạo", "create", "xóa", "delete", "sửa", "update",
            "đăng ký", "subscribe", "hủy", "unsubscribe",
            "alert", "cảnh báo", "theo dõi", "track"
        ],
        TaskType.CONVERSATION: [
            "xin chào", "hello", "hi", "chào",
            "cảm ơn", "thank", "bye", "tạm biệt",
            "giúp", "help", "hướng dẫn", "guide"
        ]
    }

    def __init__(self, fallback_model: str = "gemini-pro"):
        """
        Initialize task classifier

        Args:
            fallback_model: Model to use when classification uncertain
        """
        self.fallback_model = fallback_model
        self.classification_cache = {}

    def classify_task(self, query: str) -> TaskType:
        """
        Phân loại query thành task type

        Strategy: Keyword matching (fast) + heuristics

        Args:
            query: User query

        Returns:
            TaskType
        """
        query_lower = query.lower()

        # Check cache
        if query_lower in self.classification_cache:
            return self.classification_cache[query_lower]

        # Keyword matching với scoring
        scores = {task: 0 for task in TaskType}

        for task_type, keywords in self.TASK_KEYWORDS.items():
            for keyword in keywords:
                if keyword in query_lower:
                    scores[task_type] += 1

        # Heuristics bổ sung

        # Nếu có dấu hỏi đơn giản → DATA_QUERY
        if any(q in query_lower for q in ["là gì", "là bao nhiêu", "what is", "how much"]):
            scores[TaskType.DATA_QUERY] += 2

        # Nếu có từ so sánh → ANALYSIS
        if any(w in query_lower for w in ["so sánh", "compare", "vs", "hay hơn", "better"]):
            scores[TaskType.ANALYSIS] += 2

        # Nếu có số tiền → ADVISORY
        if any(w in query_lower for w in ["triệu", "tỷ", "million", "vnd", "đồng"]):
            scores[TaskType.ADVISORY] += 2

        # Nếu query dài (>100 chars) và phức tạp → ANALYSIS hoặc ADVISORY
        if len(query) > 100:
            scores[TaskType.ANALYSIS] += 1
            scores[TaskType.ADVISORY] += 1

        # Get highest score
        max_score = max(scores.values())

        if max_score == 0:
            # No matches → default to CONVERSATION
            task_type = TaskType.CONVERSATION
        else:
            # Get task with highest score
            task_type = max(scores, key=scores.get)

        # Cache result
        self.classification_cache[query_lower] = task_type

        return task_type

    def get_model_for_task(self, task_type: TaskType) -> str:
        """
        Get model name cho task type

        Args:
            task_type: TaskType enum

        Returns:
            Model name (string)
        """
        return self.TASK_MODEL_MAP.get(task_type, self.fallback_model)

    def get_model_for_query(self, query: str) -> str:
        """
        One-shot: Classify query → return model name

        Args:
            query: User query

        Returns:
            Model name
        """
        task_type = self.classify_task(query)
        return self.get_model_for_task(task_type)

    def get_task_and_model(self, query: str) -> tuple[TaskType, str]:
        """
        Return both task type and model name

        Args:
            query: User query

        Returns:
            (TaskType, model_name)
        """
        task_type = self.classify_task(query)
        model_name = self.get_model_for_task(task_type)
        return task_type, model_name

    def estimate_cost(
        self,
        task_type: TaskType,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        Estimate cost cho task

        Args:
            task_type: Task type
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        model_name = self.get_model_for_task(task_type)

        if model_name not in self.MODEL_COSTS:
            return 0.0

        costs = self.MODEL_COSTS[model_name]

        # Calculate cost
        input_cost = (input_tokens / 1_000_000) * costs["input"]
        output_cost = (output_tokens / 1_000_000) * costs["output"]

        total_cost = input_cost + output_cost

        return total_cost

    def get_all_models(self) -> list[str]:
        """Get list of all available models"""
        return list(set(self.TASK_MODEL_MAP.values()))

    def get_task_distribution_stats(self) -> Dict:
        """
        Get statistics về task classification từ cache

        Returns:
            Dict với task counts
        """
        task_counts = {}

        for task_type in self.classification_cache.values():
            task_name = task_type.value
            task_counts[task_name] = task_counts.get(task_name, 0) + 1

        return {
            "total_queries": len(self.classification_cache),
            "task_counts": task_counts,
            "cache_size": len(self.classification_cache)
        }

    def override_model_for_task(self, task_type: TaskType, model_name: str):
        """
        Override model cho task type (runtime configuration)

        Args:
            task_type: Task type to override
            model_name: New model name
        """
        self.TASK_MODEL_MAP[task_type] = model_name
        print(f"✅ Overridden: {task_type.value} → {model_name}")

    def clear_cache(self):
        """Clear classification cache"""
        self.classification_cache.clear()
        print("✅ Classification cache cleared")


# Example usage
if __name__ == "__main__":
    selector = TaskBasedModelSelector()

    # Test queries
    test_queries = [
        "Giá VCB hiện tại là bao nhiêu?",
        "Lọc cổ phiếu có RSI < 30 và PE < 15",
        "Phân tích kỹ thuật và cơ bản của VCB",
        "Tư vấn đầu tư 100 triệu VNĐ",
        "Tìm cổ phiếu công nghệ tiềm năng",
        "Tạo cảnh báo khi VCB > 100",
        "Xin chào, bạn có thể giúp gì?"
    ]

    print("=" * 60)
    print("Task Classification & Model Selection Demo")
    print("=" * 60)

    for query in test_queries:
        task_type, model = selector.get_task_and_model(query)
        print(f"\n📝 Query: {query}")
        print(f"   Task: {task_type.value}")
        print(f"   Model: {model}")

        # Estimate cost
        cost = selector.estimate_cost(task_type, input_tokens=100, output_tokens=500)
        print(f"   Est. Cost: ${cost:.6f}")

    print("\n" + "=" * 60)
    print("Statistics:")
    print(json.dumps(selector.get_task_distribution_stats(), indent=2))