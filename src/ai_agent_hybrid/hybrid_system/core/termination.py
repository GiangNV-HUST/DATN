"""
Control Flow & Termination System

Implements safeguards to prevent infinite loops and runaway agents.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, List
import time

from .state_management import ExecutionState


@dataclass
class TerminationConfig:
    """
    Termination rules and limits

    These ensure agents don't run indefinitely or consume
    excessive resources.
    """
    # Iteration limits
    max_iterations: int = 10
    max_tool_calls: int = 20

    # Time limits
    timeout: float = 120.0  # seconds (increased for API calls)

    # Error handling
    max_retries: int = 3
    stop_on_error: bool = True

    # Quality thresholds
    min_confidence: float = 0.7
    stop_on_low_confidence: bool = True

    # Resource limits
    max_cost: float = 1.0  # USD
    stop_on_cost_exceeded: bool = True

    # Agent-specific overrides
    agent_configs: Dict[str, Dict] = field(default_factory=dict)

    def get_agent_config(self, agent_name: str) -> "TerminationConfig":
        """Get termination config for specific agent"""
        if agent_name not in self.agent_configs:
            return self

        # Create copy with agent-specific overrides
        config = TerminationConfig(
            max_iterations=self.max_iterations,
            max_tool_calls=self.max_tool_calls,
            timeout=self.timeout,
            max_retries=self.max_retries,
            stop_on_error=self.stop_on_error,
            min_confidence=self.min_confidence,
            stop_on_low_confidence=self.stop_on_low_confidence,
            max_cost=self.max_cost,
            stop_on_cost_exceeded=self.stop_on_cost_exceeded
        )

        # Apply overrides
        overrides = self.agent_configs[agent_name]
        for key, value in overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)

        return config


# Default agent-specific configs
# Timeouts increased to handle OpenAI API latency and database queries
DEFAULT_AGENT_LIMITS = {
    "AnalysisSpecialist": {
        "max_tool_calls": 10,
        "timeout": 60.0,  # Increased for API + multiple tool calls
        "max_cost": 0.50
    },
    "ScreenerSpecialist": {
        "max_tool_calls": 5,
        "timeout": 45.0,  # Increased for OpenAI parsing + database query
        "max_cost": 0.20
    },
    "InvestmentPlanner": {
        "max_tool_calls": 15,
        "timeout": 90.0,  # Complex planning needs more time
        "max_cost": 0.50
    },
    "DiscoverySpecialist": {
        "max_tool_calls": 10,
        "timeout": 60.0,
        "max_cost": 0.40
    },
    "AlertManager": {
        "max_tool_calls": 5,
        "timeout": 30.0,
        "max_cost": 0.10
    },
    "SubscriptionManager": {
        "max_tool_calls": 5,
        "timeout": 30.0,
        "max_cost": 0.10
    },
    "MarketContextSpecialist": {
        "max_tool_calls": 10,
        "timeout": 60.0,  # Market overview may need multiple API calls
        "max_cost": 0.40
    },
    "ComparisonSpecialist": {
        "max_tool_calls": 15,
        "timeout": 90.0,  # Comparison needs data from multiple stocks
        "max_cost": 0.50
    },
    "DirectExecutor": {
        "max_tool_calls": 3,
        "timeout": 15.0,
        "max_cost": 0.10
    }
}


class ExecutionGuard:
    """
    Guards against runaway execution

    Monitors execution state and enforces termination conditions.
    """

    def __init__(self, config: Optional[TerminationConfig] = None):
        self.config = config or TerminationConfig(
            agent_configs=DEFAULT_AGENT_LIMITS
        )

    def should_stop(
        self,
        state: ExecutionState,
        agent_name: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Check if execution should stop

        Args:
            state: Current execution state
            agent_name: Name of agent (for agent-specific limits)

        Returns:
            Tuple of (should_stop, reason)
        """
        # Get agent-specific config
        config = self.config
        if agent_name:
            config = self.config.get_agent_config(agent_name)

        # 1. Check iteration limit
        if state.iterations >= config.max_iterations:
            return True, (
                f"Max iterations ({config.max_iterations}) reached. "
                f"Agent may be in infinite loop."
            )

        # 2. Check tool call limit
        if state.tool_calls >= config.max_tool_calls:
            return True, (
                f"Max tool calls ({config.max_tool_calls}) reached. "
                f"Agent is calling too many tools."
            )

        # 3. Check timeout
        elapsed = state.elapsed_time()
        if elapsed >= config.timeout:
            return True, (
                f"Timeout ({config.timeout}s) reached. "
                f"Execution took {elapsed:.1f}s."
            )

        # 4. Check error threshold
        if state.error_count >= config.max_retries:
            if config.stop_on_error:
                return True, (
                    f"Max retries ({config.max_retries}) exceeded. "
                    f"Too many errors occurred."
                )

        # 5. Check confidence threshold
        if state.confidence < config.min_confidence:
            if config.stop_on_low_confidence:
                return True, (
                    f"Confidence ({state.confidence:.2f}) below threshold "
                    f"({config.min_confidence}). Results may be unreliable."
                )

        # 6. Check cost limit
        total_cost = state.total_cost()
        if total_cost >= config.max_cost:
            if config.stop_on_cost_exceeded:
                return True, (
                    f"Cost limit (${config.max_cost}) exceeded. "
                    f"Current cost: ${total_cost:.2f}"
                )

        return False, ""

    def check_or_raise(
        self,
        state: ExecutionState,
        agent_name: Optional[str] = None
    ):
        """
        Check termination conditions and raise if should stop

        Args:
            state: Current execution state
            agent_name: Name of agent

        Raises:
            ExecutionTerminatedError if should stop
        """
        should_stop, reason = self.should_stop(state, agent_name)
        if should_stop:
            raise ExecutionTerminatedError(reason)

    def record_tool_call(
        self,
        state: ExecutionState,
        tool_name: str,
        cost: float = 0.0,
        agent_name: Optional[str] = None
    ):
        """
        Record a tool call and check limits

        Args:
            state: Execution state
            tool_name: Name of tool called
            cost: Cost of tool call (USD)
            agent_name: Name of agent

        Raises:
            ExecutionTerminatedError if limits exceeded
        """
        state.record_tool_call(tool_name, cost)
        self.check_or_raise(state, agent_name)

    def record_iteration(
        self,
        state: ExecutionState,
        agent_name: Optional[str] = None
    ):
        """
        Record an iteration and check limits

        Args:
            state: Execution state
            agent_name: Name of agent

        Raises:
            ExecutionTerminatedError if limits exceeded
        """
        state.next_iteration()
        self.check_or_raise(state, agent_name)

    def get_remaining_budget(
        self,
        state: ExecutionState,
        agent_name: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Get remaining resource budget

        Returns:
            Dictionary with remaining iterations, tool calls, time, cost
        """
        config = self.config
        if agent_name:
            config = self.config.get_agent_config(agent_name)

        elapsed = state.elapsed_time()
        total_cost = state.total_cost()

        return {
            "iterations": {
                "used": state.iterations,
                "max": config.max_iterations,
                "remaining": max(0, config.max_iterations - state.iterations)
            },
            "tool_calls": {
                "used": state.tool_calls,
                "max": config.max_tool_calls,
                "remaining": max(0, config.max_tool_calls - state.tool_calls)
            },
            "time": {
                "elapsed": elapsed,
                "max": config.timeout,
                "remaining": max(0, config.timeout - elapsed)
            },
            "cost": {
                "used": total_cost,
                "max": config.max_cost,
                "remaining": max(0, config.max_cost - total_cost)
            }
        }


class ExecutionTerminatedError(Exception):
    """Raised when execution is terminated by guards"""
    pass


class CircuitBreaker:
    """
    Circuit breaker pattern for failing operations

    Prevents repeated calls to failing operations by
    "opening" the circuit after too many failures.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        # Per-operation state
        self._states: Dict[str, str] = {}  # operation -> state (closed/open/half-open)
        self._failure_counts: Dict[str, int] = {}
        self._last_failure_time: Dict[str, float] = {}
        self._half_open_calls: Dict[str, int] = {}

    def call(self, operation: str, func: callable, *args, **kwargs):
        """
        Execute operation with circuit breaker

        Args:
            operation: Operation identifier
            func: Function to call
            *args, **kwargs: Arguments to function

        Returns:
            Result from function

        Raises:
            CircuitOpenError if circuit is open
        """
        # Check circuit state
        state = self._get_state(operation)

        if state == "open":
            # Check if recovery timeout passed
            if time.time() - self._last_failure_time[operation] >= self.recovery_timeout:
                # Transition to half-open
                self._states[operation] = "half-open"
                self._half_open_calls[operation] = 0
            else:
                raise CircuitOpenError(
                    f"Circuit open for '{operation}'. "
                    f"Wait {self.recovery_timeout}s before retry."
                )

        # Try to execute
        try:
            result = func(*args, **kwargs)

            # Success
            if state == "half-open":
                self._half_open_calls[operation] += 1
                if self._half_open_calls[operation] >= self.half_open_max_calls:
                    # Transition to closed
                    self._states[operation] = "closed"
                    self._failure_counts[operation] = 0

            elif state == "closed":
                # Reset failure count on success
                self._failure_counts[operation] = 0

            return result

        except Exception as e:
            # Failure
            self._failure_counts[operation] = self._failure_counts.get(operation, 0) + 1
            self._last_failure_time[operation] = time.time()

            # Check if should open circuit
            if self._failure_counts[operation] >= self.failure_threshold:
                self._states[operation] = "open"

            raise e

    def _get_state(self, operation: str) -> str:
        """Get current state of circuit"""
        return self._states.get(operation, "closed")

    def reset(self, operation: str):
        """Manually reset circuit"""
        self._states[operation] = "closed"
        self._failure_counts[operation] = 0
        if operation in self._last_failure_time:
            del self._last_failure_time[operation]
        if operation in self._half_open_calls:
            del self._half_open_calls[operation]


class CircuitOpenError(Exception):
    """Raised when circuit is open"""
    pass
