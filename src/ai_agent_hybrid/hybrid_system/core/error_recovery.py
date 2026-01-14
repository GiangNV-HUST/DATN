"""
Error Recovery & Retry System

Implements automatic retry with exponential backoff,
fallback strategies, and error recovery mechanisms.
"""

import asyncio
import time
import random
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ErrorType(Enum):
    """Classification of error types"""
    TRANSIENT = "transient"       # Temporary errors (network, timeout)
    PERMANENT = "permanent"       # Permanent errors (invalid input, not found)
    RATE_LIMIT = "rate_limit"     # Rate limiting errors
    API_ERROR = "api_error"       # External API errors
    DATABASE = "database"         # Database errors
    UNKNOWN = "unknown"           # Unknown errors


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_retries: int = 3
    base_delay: float = 1.0       # Initial delay in seconds
    max_delay: float = 30.0       # Maximum delay
    exponential_base: float = 2.0 # Exponential backoff multiplier
    jitter: bool = True           # Add randomness to prevent thundering herd

    # Error type specific configs
    retry_on_transient: bool = True
    retry_on_rate_limit: bool = True
    retry_on_api_error: bool = True
    retry_on_database: bool = True
    retry_on_permanent: bool = False

    # Timeout per attempt
    timeout_per_attempt: float = 30.0


@dataclass
class RetryResult:
    """Result of a retry operation"""
    success: bool
    value: Any = None
    error: Optional[Exception] = None
    attempts: int = 0
    total_time: float = 0.0
    errors_by_attempt: List[Dict] = field(default_factory=list)


def classify_error(error: Exception) -> ErrorType:
    """Classify an error to determine retry strategy"""
    error_str = str(error).lower()
    error_type = type(error).__name__.lower()

    # Rate limit errors
    if any(kw in error_str for kw in ["rate limit", "too many requests", "429", "quota"]):
        return ErrorType.RATE_LIMIT

    # Transient network errors
    if any(kw in error_str for kw in ["timeout", "connection", "network", "temporary", "503", "502", "504"]):
        return ErrorType.TRANSIENT

    # Database errors
    if any(kw in error_str for kw in ["database", "relation", "does not exist", "connection refused"]):
        return ErrorType.DATABASE

    # Permanent errors
    if any(kw in error_str for kw in ["not found", "invalid", "400", "401", "403", "404"]):
        return ErrorType.PERMANENT

    # API errors
    if any(kw in error_str for kw in ["api", "500", "internal server error"]):
        return ErrorType.API_ERROR

    return ErrorType.UNKNOWN


def should_retry(error: Exception, config: RetryConfig) -> bool:
    """Determine if an error should be retried"""
    error_type = classify_error(error)

    if error_type == ErrorType.TRANSIENT:
        return config.retry_on_transient
    elif error_type == ErrorType.RATE_LIMIT:
        return config.retry_on_rate_limit
    elif error_type == ErrorType.API_ERROR:
        return config.retry_on_api_error
    elif error_type == ErrorType.DATABASE:
        return config.retry_on_database
    elif error_type == ErrorType.PERMANENT:
        return config.retry_on_permanent
    else:
        return True  # Retry unknown errors by default


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """Calculate delay before next retry with exponential backoff"""
    delay = config.base_delay * (config.exponential_base ** attempt)
    delay = min(delay, config.max_delay)

    if config.jitter:
        # Add random jitter between 0-25% of delay
        jitter = delay * random.uniform(0, 0.25)
        delay += jitter

    return delay


async def retry_async(
    func: Callable[..., T],
    *args,
    config: Optional[RetryConfig] = None,
    **kwargs
) -> RetryResult:
    """
    Execute async function with retry logic

    Args:
        func: Async function to execute
        *args: Positional arguments
        config: Retry configuration
        **kwargs: Keyword arguments

    Returns:
        RetryResult with success status and value/error
    """
    config = config or RetryConfig()
    start_time = time.time()
    errors_by_attempt = []

    for attempt in range(config.max_retries + 1):
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=config.timeout_per_attempt
            )

            return RetryResult(
                success=True,
                value=result,
                attempts=attempt + 1,
                total_time=time.time() - start_time,
                errors_by_attempt=errors_by_attempt
            )

        except asyncio.TimeoutError as e:
            error_info = {
                "attempt": attempt + 1,
                "error_type": "timeout",
                "message": f"Timeout after {config.timeout_per_attempt}s"
            }
            errors_by_attempt.append(error_info)
            logger.warning(f"Attempt {attempt + 1} timed out: {e}")

            if attempt < config.max_retries:
                delay = calculate_delay(attempt, config)
                logger.info(f"Retrying in {delay:.2f}s...")
                await asyncio.sleep(delay)
            else:
                return RetryResult(
                    success=False,
                    error=e,
                    attempts=attempt + 1,
                    total_time=time.time() - start_time,
                    errors_by_attempt=errors_by_attempt
                )

        except Exception as e:
            error_type = classify_error(e)
            error_info = {
                "attempt": attempt + 1,
                "error_type": error_type.value,
                "message": str(e),
                "exception_type": type(e).__name__
            }
            errors_by_attempt.append(error_info)

            logger.warning(f"Attempt {attempt + 1} failed ({error_type.value}): {e}")

            # Check if should retry
            if not should_retry(e, config) or attempt >= config.max_retries:
                return RetryResult(
                    success=False,
                    error=e,
                    attempts=attempt + 1,
                    total_time=time.time() - start_time,
                    errors_by_attempt=errors_by_attempt
                )

            # Calculate and wait delay
            delay = calculate_delay(attempt, config)

            # Extra delay for rate limit errors
            if error_type == ErrorType.RATE_LIMIT:
                delay *= 2

            logger.info(f"Retrying in {delay:.2f}s...")
            await asyncio.sleep(delay)

    # Should not reach here, but just in case
    return RetryResult(
        success=False,
        error=Exception("Max retries exceeded"),
        attempts=config.max_retries + 1,
        total_time=time.time() - start_time,
        errors_by_attempt=errors_by_attempt
    )


def with_retry(config: Optional[RetryConfig] = None):
    """
    Decorator to add retry logic to async functions

    Usage:
        @with_retry(RetryConfig(max_retries=3))
        async def my_api_call():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            result = await retry_async(func, *args, config=config, **kwargs)
            if result.success:
                return result.value
            else:
                raise result.error
        return wrapper
    return decorator


class FallbackChain:
    """
    Chain of fallback strategies for error recovery

    Usage:
        chain = FallbackChain()
        chain.add_fallback("api", api_call)
        chain.add_fallback("cache", cache_lookup)
        chain.add_fallback("default", lambda: default_value)

        result = await chain.execute()
    """

    def __init__(self, name: str = "default"):
        self.name = name
        self._fallbacks: List[Dict] = []
        self._results: List[Dict] = []

    def add_fallback(
        self,
        name: str,
        func: Callable,
        retry_config: Optional[RetryConfig] = None,
        condition: Optional[Callable[[Any], bool]] = None
    ):
        """
        Add a fallback strategy

        Args:
            name: Name of fallback strategy
            func: Async function to execute
            retry_config: Optional retry configuration
            condition: Optional condition to validate result
        """
        self._fallbacks.append({
            "name": name,
            "func": func,
            "retry_config": retry_config or RetryConfig(max_retries=1),
            "condition": condition
        })

    async def execute(self, *args, **kwargs) -> Any:
        """
        Execute fallback chain until success

        Returns:
            Result from first successful fallback

        Raises:
            AllFallbacksFailedError if all fallbacks fail
        """
        self._results = []

        for fallback in self._fallbacks:
            try:
                # Execute with retry
                result = await retry_async(
                    fallback["func"],
                    *args,
                    config=fallback["retry_config"],
                    **kwargs
                )

                if result.success:
                    # Check condition if provided
                    if fallback["condition"] and not fallback["condition"](result.value):
                        logger.info(f"Fallback '{fallback['name']}' result didn't meet condition")
                        self._results.append({
                            "name": fallback["name"],
                            "success": False,
                            "reason": "condition_not_met"
                        })
                        continue

                    logger.info(f"Fallback '{fallback['name']}' succeeded")
                    self._results.append({
                        "name": fallback["name"],
                        "success": True
                    })
                    return result.value
                else:
                    self._results.append({
                        "name": fallback["name"],
                        "success": False,
                        "error": str(result.error)
                    })

            except Exception as e:
                logger.warning(f"Fallback '{fallback['name']}' failed: {e}")
                self._results.append({
                    "name": fallback["name"],
                    "success": False,
                    "error": str(e)
                })

        raise AllFallbacksFailedError(
            f"All {len(self._fallbacks)} fallbacks failed for '{self.name}'",
            results=self._results
        )

    def get_results(self) -> List[Dict]:
        """Get execution results for all fallbacks"""
        return self._results


class AllFallbacksFailedError(Exception):
    """Raised when all fallback strategies fail"""

    def __init__(self, message: str, results: List[Dict] = None):
        super().__init__(message)
        self.results = results or []


class ErrorRecoveryManager:
    """
    Central manager for error recovery across the system

    Tracks errors, manages recovery strategies, and provides
    system-wide error statistics.
    """

    def __init__(self):
        self._error_counts: Dict[str, int] = {}
        self._error_history: List[Dict] = []
        self._recovery_strategies: Dict[str, FallbackChain] = {}
        self._max_history = 1000

    def register_strategy(self, name: str, chain: FallbackChain):
        """Register a recovery strategy"""
        self._recovery_strategies[name] = chain

    def record_error(
        self,
        source: str,
        error: Exception,
        context: Optional[Dict] = None
    ):
        """Record an error for tracking"""
        error_type = classify_error(error)
        key = f"{source}:{error_type.value}"

        self._error_counts[key] = self._error_counts.get(key, 0) + 1

        error_record = {
            "source": source,
            "error_type": error_type.value,
            "message": str(error),
            "context": context,
            "timestamp": time.time()
        }
        self._error_history.append(error_record)

        # Prune history
        if len(self._error_history) > self._max_history:
            self._error_history = self._error_history[-self._max_history:]

    def record_success(self, source: str):
        """Record a successful operation (resets error count)"""
        for key in list(self._error_counts.keys()):
            if key.startswith(f"{source}:"):
                self._error_counts[key] = 0

    def get_error_rate(self, source: str) -> float:
        """Get error rate for a source (errors per 100 operations)"""
        total_errors = sum(
            count for key, count in self._error_counts.items()
            if key.startswith(f"{source}:")
        )
        return total_errors

    def get_statistics(self) -> Dict:
        """Get error statistics"""
        recent_errors = [
            e for e in self._error_history
            if time.time() - e["timestamp"] < 3600  # Last hour
        ]

        error_by_type = {}
        for error in recent_errors:
            error_type = error["error_type"]
            error_by_type[error_type] = error_by_type.get(error_type, 0) + 1

        return {
            "total_errors": len(self._error_history),
            "errors_last_hour": len(recent_errors),
            "errors_by_type": error_by_type,
            "error_counts": dict(self._error_counts)
        }

    async def execute_with_recovery(
        self,
        strategy_name: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute operation with registered recovery strategy

        Args:
            strategy_name: Name of registered recovery strategy
            *args, **kwargs: Arguments to pass to strategy

        Returns:
            Result from strategy execution
        """
        if strategy_name not in self._recovery_strategies:
            raise ValueError(f"Unknown recovery strategy: {strategy_name}")

        chain = self._recovery_strategies[strategy_name]

        try:
            result = await chain.execute(*args, **kwargs)
            self.record_success(strategy_name)
            return result
        except AllFallbacksFailedError as e:
            self.record_error(strategy_name, e)
            raise


# Global error recovery manager
error_recovery_manager = ErrorRecoveryManager()


# Pre-configured retry configs for common scenarios
RETRY_CONFIGS = {
    "api_call": RetryConfig(
        max_retries=3,
        base_delay=1.0,
        max_delay=15.0,
        timeout_per_attempt=30.0
    ),
    "database": RetryConfig(
        max_retries=2,
        base_delay=0.5,
        max_delay=5.0,
        timeout_per_attempt=10.0,
        retry_on_database=True
    ),
    "critical": RetryConfig(
        max_retries=5,
        base_delay=2.0,
        max_delay=60.0,
        timeout_per_attempt=60.0
    ),
    "quick": RetryConfig(
        max_retries=2,
        base_delay=0.5,
        max_delay=3.0,
        timeout_per_attempt=10.0
    )
}
