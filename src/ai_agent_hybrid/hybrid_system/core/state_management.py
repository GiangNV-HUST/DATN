"""
State Management System

Implements stateful context sharing between agents,
similar to OLD system's ToolContext pattern.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import time
import threading


@dataclass
class ExecutionState:
    """
    Tracks execution state for control flow and termination
    """
    start_time: float = field(default_factory=time.time)
    iterations: int = 0
    tool_calls: int = 0
    error_count: int = 0
    confidence: float = 1.0
    current_agent: Optional[str] = None
    phase: str = "idle"  # idle, routing, executing, evaluating, responding

    # Resource tracking
    costs: Dict[str, float] = field(default_factory=dict)
    tool_usage: Dict[str, int] = field(default_factory=dict)

    def elapsed_time(self) -> float:
        """Get elapsed time since start"""
        return time.time() - self.start_time

    def record_tool_call(self, tool_name: str, cost: float = 0.0):
        """Record a tool call"""
        self.tool_calls += 1
        self.tool_usage[tool_name] = self.tool_usage.get(tool_name, 0) + 1
        self.costs[tool_name] = self.costs.get(tool_name, 0.0) + cost

    def record_error(self):
        """Record an error"""
        self.error_count += 1

    def next_iteration(self):
        """Move to next iteration"""
        self.iterations += 1

    def total_cost(self) -> float:
        """Get total cost across all tools"""
        return sum(self.costs.values())


class SharedState:
    """
    Shared state container for agents

    Similar to OLD system's ToolContext.state, this allows
    agents to store and retrieve data between steps.

    Example from OLD:
        tool_context.state[f"stock_data_{symbol}"] = result
        data = tool_context.state.get(f"stock_data_{symbol}")
    """

    def __init__(self):
        self._state: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._access_log: List[Dict] = []

    def set(self, key: str, value: Any, agent: str = "unknown"):
        """
        Store a value in shared state

        Args:
            key: State key
            value: Value to store
            agent: Agent name storing the value (for tracking)
        """
        with self._lock:
            self._state[key] = value
            self._log_access("SET", key, agent)

    def get(self, key: str, default: Any = None, agent: str = "unknown") -> Any:
        """
        Retrieve a value from shared state

        Args:
            key: State key
            default: Default value if key not found
            agent: Agent name retrieving the value (for tracking)

        Returns:
            Stored value or default
        """
        with self._lock:
            value = self._state.get(key, default)
            self._log_access("GET", key, agent, found=(key in self._state))
            return value

    def update(self, updates: Dict[str, Any], agent: str = "unknown"):
        """
        Update multiple values at once

        Args:
            updates: Dictionary of key-value pairs to update
            agent: Agent name updating the values
        """
        with self._lock:
            self._state.update(updates)
            for key in updates:
                self._log_access("UPDATE", key, agent)

    def delete(self, key: str, agent: str = "unknown") -> bool:
        """
        Delete a value from shared state

        Args:
            key: State key to delete
            agent: Agent name deleting the value

        Returns:
            True if key existed, False otherwise
        """
        with self._lock:
            existed = key in self._state
            if existed:
                del self._state[key]
                self._log_access("DELETE", key, agent)
            return existed

    def has(self, key: str) -> bool:
        """Check if key exists in state"""
        with self._lock:
            return key in self._state

    def keys(self) -> List[str]:
        """Get all keys in state"""
        with self._lock:
            return list(self._state.keys())

    def clear(self):
        """Clear all state"""
        with self._lock:
            self._state.clear()
            self._access_log.clear()

    def _log_access(self, operation: str, key: str, agent: str, found: bool = True):
        """Log state access for debugging"""
        self._access_log.append({
            "operation": operation,
            "key": key,
            "agent": agent,
            "found": found,
            "timestamp": time.time()
        })

        # Keep only last 1000 accesses
        if len(self._access_log) > 1000:
            self._access_log.pop(0)

    def get_access_log(self, limit: int = 100) -> List[Dict]:
        """Get state access log for debugging"""
        return self._access_log[-limit:]

    def __repr__(self) -> str:
        return f"<SharedState keys={len(self._state)}>"


class ConversationMemory:
    """
    Conversation memory per user session

    Similar to OLD system's InMemoryMemoryService
    """

    def __init__(self, max_turns: int = 20):
        self.max_turns = max_turns
        self._memory: Dict[str, List[Dict]] = {}  # session_id -> messages
        self._lock = threading.RLock()

    def add_message(self, session_id: str, role: str, content: str):
        """
        Add a message to conversation history

        Args:
            session_id: Session identifier
            role: Message role (user/assistant)
            content: Message content
        """
        with self._lock:
            if session_id not in self._memory:
                self._memory[session_id] = []

            self._memory[session_id].append({
                "role": role,
                "content": content,
                "timestamp": time.time()
            })

            # Prune old messages
            if len(self._memory[session_id]) > self.max_turns * 2:
                self._memory[session_id] = self._memory[session_id][-(self.max_turns * 2):]

    def get_history(self, session_id: str, limit: Optional[int] = None) -> List[Dict]:
        """
        Get conversation history

        Args:
            session_id: Session identifier
            limit: Maximum number of messages (default: all)

        Returns:
            List of messages
        """
        with self._lock:
            messages = self._memory.get(session_id, [])
            if limit:
                return messages[-limit:]
            return messages

    def clear_session(self, session_id: str):
        """Clear conversation history for a session"""
        with self._lock:
            if session_id in self._memory:
                del self._memory[session_id]

    def has_session(self, session_id: str) -> bool:
        """Check if session exists"""
        with self._lock:
            return session_id in self._memory


class UserContext:
    """
    User context information

    Similar to OLD system's session state["context"]
    """

    def __init__(
        self,
        user_id: str,
        user_name: str = "Unknown",
        preferences: Optional[Dict] = None
    ):
        self.user_id = user_id
        self.user_name = user_name
        self.preferences = preferences or {}

        # User-specific state
        self.investment_profile: Optional[Dict] = None
        self.watchlist: List[str] = []
        self.alerts: List[Dict] = []
        self.subscriptions: List[str] = []

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "user_id": self.user_id,
            "user_name": self.user_name,
            "preferences": self.preferences,
            "investment_profile": self.investment_profile,
            "watchlist": self.watchlist,
            "alerts": self.alerts,
            "subscriptions": self.subscriptions
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "UserContext":
        """Create from dictionary"""
        context = cls(
            user_id=data["user_id"],
            user_name=data.get("user_name", "Unknown"),
            preferences=data.get("preferences", {})
        )
        context.investment_profile = data.get("investment_profile")
        context.watchlist = data.get("watchlist", [])
        context.alerts = data.get("alerts", [])
        context.subscriptions = data.get("subscriptions", [])
        return context


class StateManager:
    """
    Central state manager coordinating all state types

    This is the equivalent of OLD system's session_service + ToolContext
    """

    def __init__(self):
        # Per-session states
        self._execution_states: Dict[str, ExecutionState] = {}
        self._shared_states: Dict[str, SharedState] = {}
        self._conversation_memories: Dict[str, ConversationMemory] = {}
        self._user_contexts: Dict[str, UserContext] = {}

        self._lock = threading.RLock()

    def create_session(
        self,
        session_id: str,
        user_id: str,
        user_name: str = "Unknown"
    ):
        """
        Create a new session with all required state

        Args:
            session_id: Session identifier
            user_id: User identifier
            user_name: User display name
        """
        with self._lock:
            self._execution_states[session_id] = ExecutionState()
            self._shared_states[session_id] = SharedState()
            self._conversation_memories[session_id] = ConversationMemory()
            self._user_contexts[session_id] = UserContext(
                user_id=user_id,
                user_name=user_name
            )

    def get_execution_state(self, session_id: str) -> ExecutionState:
        """Get execution state for session"""
        return self._execution_states.get(session_id, ExecutionState())

    def get_shared_state(self, session_id: str) -> SharedState:
        """Get shared state for session"""
        if session_id not in self._shared_states:
            self._shared_states[session_id] = SharedState()
        return self._shared_states[session_id]

    def get_memory(self, session_id: str) -> ConversationMemory:
        """Get conversation memory for session"""
        if session_id not in self._conversation_memories:
            self._conversation_memories[session_id] = ConversationMemory()
        return self._conversation_memories[session_id]

    def get_user_context(self, session_id: str) -> Optional[UserContext]:
        """Get user context for session"""
        return self._user_contexts.get(session_id)

    def clear_session(self, session_id: str):
        """Clear all state for a session"""
        with self._lock:
            if session_id in self._execution_states:
                del self._execution_states[session_id]
            if session_id in self._shared_states:
                del self._shared_states[session_id]
            if session_id in self._conversation_memories:
                del self._conversation_memories[session_id]
            if session_id in self._user_contexts:
                del self._user_contexts[session_id]

    def has_session(self, session_id: str) -> bool:
        """Check if session exists"""
        return session_id in self._execution_states


# Global state manager instance
state_manager = StateManager()
