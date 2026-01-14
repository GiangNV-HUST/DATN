"""
Structured Task Context System

Provides rich context passing between agents in multi-agent workflows.
Ensures agents have all necessary information without redundant API calls.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set
from enum import Enum
import time
import json
import hashlib


class TaskPriority(Enum):
    """Priority level for tasks"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class DataFreshness(Enum):
    """Freshness requirement for data"""
    REALTIME = "realtime"       # Must be fresh (<1 min)
    RECENT = "recent"           # Recent data OK (<5 min)
    CACHED = "cached"           # Cached data OK (<1 hour)
    ANY = "any"                 # Any data OK


@dataclass
class DataReference:
    """Reference to data in shared context"""
    key: str                    # Key in shared_state
    source_agent: str           # Agent that produced this data
    timestamp: float            # When data was produced
    data_type: str              # Type of data (price, financial, etc.)
    symbols: List[str] = field(default_factory=list)  # Related symbols

    def is_fresh(self, max_age: float = 300) -> bool:
        """Check if data is fresh (default 5 min)"""
        return time.time() - self.timestamp < max_age

    def to_dict(self) -> Dict:
        return {
            "key": self.key,
            "source_agent": self.source_agent,
            "timestamp": self.timestamp,
            "data_type": self.data_type,
            "symbols": self.symbols
        }


@dataclass
class TaskContext:
    """
    Structured context for a task in multi-agent workflow

    This provides all necessary information for an agent to execute
    without needing to re-fetch data that previous agents already have.
    """
    # Task identification
    task_id: str
    parent_task_id: Optional[str] = None
    workflow_id: str = ""

    # Task details
    specialist: str = ""
    user_query: str = ""
    sub_query: str = ""         # Specific part for this task
    priority: TaskPriority = TaskPriority.NORMAL

    # Symbols and entities
    symbols: List[str] = field(default_factory=list)
    entities: Dict[str, List[str]] = field(default_factory=dict)  # type -> values

    # Data requirements
    required_data: List[str] = field(default_factory=list)
    data_freshness: DataFreshness = DataFreshness.CACHED

    # Available data from previous agents
    available_data: Dict[str, DataReference] = field(default_factory=dict)

    # Previous results from other agents in workflow
    previous_results: Dict[str, str] = field(default_factory=dict)  # agent -> result
    previous_context: Dict[str, Any] = field(default_factory=dict)

    # Execution constraints
    timeout: float = 60.0
    max_tool_calls: int = 10

    # Metadata
    created_at: float = field(default_factory=time.time)
    tags: Set[str] = field(default_factory=set)

    def add_available_data(
        self,
        key: str,
        source_agent: str,
        data_type: str,
        symbols: List[str] = None
    ):
        """Record data that is available for use"""
        self.available_data[key] = DataReference(
            key=key,
            source_agent=source_agent,
            timestamp=time.time(),
            data_type=data_type,
            symbols=symbols or []
        )

    def has_data(self, data_type: str, symbols: List[str] = None) -> bool:
        """Check if required data is available"""
        for ref in self.available_data.values():
            if ref.data_type == data_type:
                if symbols is None:
                    return True
                if all(s in ref.symbols for s in symbols):
                    return True
        return False

    def get_data_keys(self, data_type: str) -> List[str]:
        """Get keys for available data of a type"""
        return [
            ref.key for ref in self.available_data.values()
            if ref.data_type == data_type
        ]

    def get_fresh_data_keys(self, data_type: str, max_age: float = 300) -> List[str]:
        """Get keys for fresh data of a type"""
        return [
            ref.key for ref in self.available_data.values()
            if ref.data_type == data_type and ref.is_fresh(max_age)
        ]

    def add_previous_result(self, agent: str, result: str):
        """Add result from previous agent"""
        self.previous_results[agent] = result

    def get_previous_result(self, agent: str) -> Optional[str]:
        """Get result from specific previous agent"""
        return self.previous_results.get(agent)

    def to_dict(self) -> Dict:
        """Serialize to dictionary"""
        return {
            "task_id": self.task_id,
            "parent_task_id": self.parent_task_id,
            "workflow_id": self.workflow_id,
            "specialist": self.specialist,
            "user_query": self.user_query,
            "sub_query": self.sub_query,
            "priority": self.priority.value,
            "symbols": self.symbols,
            "entities": self.entities,
            "required_data": self.required_data,
            "data_freshness": self.data_freshness.value,
            "available_data": {k: v.to_dict() for k, v in self.available_data.items()},
            "previous_results": self.previous_results,
            "previous_context": self.previous_context,
            "timeout": self.timeout,
            "max_tool_calls": self.max_tool_calls,
            "created_at": self.created_at,
            "tags": list(self.tags)
        }

    def to_prompt_context(self) -> str:
        """Convert to context string for agent prompts"""
        lines = []

        if self.previous_results:
            lines.append("## Ket qua tu cac agent truoc:")
            for agent, result in self.previous_results.items():
                # Truncate long results
                truncated = result[:1000] + "..." if len(result) > 1000 else result
                lines.append(f"\n### {agent}:\n{truncated}")
            lines.append("")

        if self.available_data:
            lines.append("## Du lieu co san:")
            for key, ref in self.available_data.items():
                age = time.time() - ref.timestamp
                lines.append(f"- {ref.data_type} ({key}): {', '.join(ref.symbols)} - {age:.0f}s ago")
            lines.append("")

        if self.previous_context:
            lines.append("## Context tu workflow:")
            for key, value in self.previous_context.items():
                if isinstance(value, (dict, list)):
                    lines.append(f"- {key}: {json.dumps(value, ensure_ascii=False)[:200]}")
                else:
                    lines.append(f"- {key}: {value}")
            lines.append("")

        return "\n".join(lines)


@dataclass
class WorkflowContext:
    """
    Context for entire multi-agent workflow

    Tracks all tasks, data, and results across the workflow.
    """
    workflow_id: str
    user_query: str
    session_id: str
    user_id: str

    # All tasks in workflow
    tasks: List[TaskContext] = field(default_factory=list)
    task_order: List[str] = field(default_factory=list)  # Execution order

    # Global shared data
    shared_data: Dict[str, Any] = field(default_factory=dict)
    data_registry: Dict[str, DataReference] = field(default_factory=dict)

    # Workflow results
    results: Dict[str, str] = field(default_factory=dict)  # task_id -> result
    final_response: str = ""

    # Execution mode
    execution_mode: str = "sequential"  # sequential, parallel

    # Timing
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def add_task(self, task: TaskContext):
        """Add task to workflow"""
        task.workflow_id = self.workflow_id

        # Inherit available data from previous tasks
        for key, ref in self.data_registry.items():
            if key not in task.available_data:
                task.available_data[key] = ref

        # Add previous results
        for task_id, result in self.results.items():
            prev_task = self.get_task(task_id)
            if prev_task:
                task.previous_results[prev_task.specialist] = result

        self.tasks.append(task)
        self.task_order.append(task.task_id)

    def get_task(self, task_id: str) -> Optional[TaskContext]:
        """Get task by ID"""
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None

    def record_result(self, task_id: str, result: str):
        """Record task result"""
        self.results[task_id] = result

    def register_data(
        self,
        key: str,
        source_agent: str,
        data_type: str,
        symbols: List[str] = None,
        data: Any = None
    ):
        """Register data produced by an agent"""
        ref = DataReference(
            key=key,
            source_agent=source_agent,
            timestamp=time.time(),
            data_type=data_type,
            symbols=symbols or []
        )
        self.data_registry[key] = ref

        if data is not None:
            self.shared_data[key] = data

    def get_data(self, key: str) -> Optional[Any]:
        """Get data by key"""
        return self.shared_data.get(key)

    def get_all_results(self) -> Dict[str, str]:
        """Get all results keyed by specialist name"""
        result_by_specialist = {}
        for task in self.tasks:
            if task.task_id in self.results:
                result_by_specialist[task.specialist] = self.results[task.task_id]
        return result_by_specialist

    def is_complete(self) -> bool:
        """Check if all tasks completed"""
        return len(self.results) == len(self.tasks)

    def elapsed_time(self) -> float:
        """Get elapsed time"""
        if self.completed_at:
            return self.completed_at - self.started_at
        return time.time() - self.started_at

    def to_summary(self) -> Dict:
        """Generate workflow summary"""
        return {
            "workflow_id": self.workflow_id,
            "user_query": self.user_query,
            "total_tasks": len(self.tasks),
            "completed_tasks": len(self.results),
            "execution_mode": self.execution_mode,
            "elapsed_time": self.elapsed_time(),
            "tasks": [
                {
                    "task_id": t.task_id,
                    "specialist": t.specialist,
                    "completed": t.task_id in self.results
                }
                for t in self.tasks
            ]
        }


class TaskContextBuilder:
    """Builder for creating TaskContext with proper inheritance"""

    def __init__(self, workflow: Optional[WorkflowContext] = None):
        self.workflow = workflow
        self._task_id: Optional[str] = None
        self._specialist: str = ""
        self._user_query: str = ""
        self._sub_query: str = ""
        self._symbols: List[str] = []
        self._required_data: List[str] = []
        self._priority: TaskPriority = TaskPriority.NORMAL
        self._timeout: float = 60.0

    def task_id(self, task_id: str) -> "TaskContextBuilder":
        self._task_id = task_id
        return self

    def specialist(self, specialist: str) -> "TaskContextBuilder":
        self._specialist = specialist
        return self

    def query(self, user_query: str, sub_query: str = "") -> "TaskContextBuilder":
        self._user_query = user_query
        self._sub_query = sub_query or user_query
        return self

    def symbols(self, symbols: List[str]) -> "TaskContextBuilder":
        self._symbols = symbols
        return self

    def requires(self, *data_types: str) -> "TaskContextBuilder":
        self._required_data.extend(data_types)
        return self

    def priority(self, priority: TaskPriority) -> "TaskContextBuilder":
        self._priority = priority
        return self

    def timeout(self, timeout: float) -> "TaskContextBuilder":
        self._timeout = timeout
        return self

    def build(self) -> TaskContext:
        """Build TaskContext"""
        task_id = self._task_id or self._generate_task_id()

        task = TaskContext(
            task_id=task_id,
            specialist=self._specialist,
            user_query=self._user_query,
            sub_query=self._sub_query,
            symbols=self._symbols,
            required_data=self._required_data,
            priority=self._priority,
            timeout=self._timeout
        )

        # Inherit from workflow if available
        if self.workflow:
            task.workflow_id = self.workflow.workflow_id

            # Add available data
            for key, ref in self.workflow.data_registry.items():
                task.available_data[key] = ref

            # Add previous results
            for prev_task in self.workflow.tasks:
                if prev_task.task_id in self.workflow.results:
                    task.previous_results[prev_task.specialist] = \
                        self.workflow.results[prev_task.task_id]

        return task

    def _generate_task_id(self) -> str:
        """Generate unique task ID"""
        content = f"{self._specialist}{self._sub_query}{time.time()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]


# Data type constants for consistency
class DataTypes:
    """Standard data type names"""
    PRICE_DATA = "price_data"
    FINANCIAL_DATA = "financial_data"
    PREDICTION = "prediction"
    MARKET_INDEX = "market_index"
    SCREENING_RESULTS = "screening_results"
    COMPARISON_MATRIX = "comparison_matrix"
    NEWS = "news"
    CHART = "chart"
    INVESTMENT_PLAN = "investment_plan"
    ALERT = "alert"


# Helper functions
def create_task_context(
    specialist: str,
    user_query: str,
    symbols: List[str] = None,
    workflow: WorkflowContext = None,
    **kwargs
) -> TaskContext:
    """Convenience function to create task context"""
    builder = TaskContextBuilder(workflow)
    builder.specialist(specialist)
    builder.query(user_query)

    if symbols:
        builder.symbols(symbols)

    if "timeout" in kwargs:
        builder.timeout(kwargs["timeout"])

    if "priority" in kwargs:
        builder.priority(kwargs["priority"])

    return builder.build()


def merge_contexts(
    contexts: List[TaskContext],
    target_specialist: str
) -> TaskContext:
    """
    Merge multiple task contexts into one

    Useful for creating context for final synthesis agent
    """
    if not contexts:
        raise ValueError("No contexts to merge")

    # Start with first context
    merged = TaskContext(
        task_id=f"merged_{int(time.time())}",
        specialist=target_specialist,
        user_query=contexts[0].user_query
    )

    # Merge all data
    all_symbols = set()
    for ctx in contexts:
        all_symbols.update(ctx.symbols)
        merged.available_data.update(ctx.available_data)
        merged.previous_results[ctx.specialist] = ctx.sub_query
        merged.previous_context.update(ctx.previous_context)
        merged.tags.update(ctx.tags)

    merged.symbols = list(all_symbols)

    return merged
