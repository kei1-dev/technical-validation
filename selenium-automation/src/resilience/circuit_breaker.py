"""
Circuit Breaker pattern implementation.

This module provides fault tolerance through the Circuit Breaker pattern,
which prevents cascading failures by stopping calls to failing services.

States:
- CLOSED: Normal operation, calls pass through
- OPEN: Too many failures, calls are blocked
- HALF_OPEN: Testing if service recovered
"""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Any, Optional, Type


logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"          # Normal operation
    OPEN = "open"              # Blocking calls due to failures
    HALF_OPEN = "half_open"    # Testing recovery


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is in OPEN state."""
    pass


class CircuitBreaker:
    """
    Circuit breaker for fault tolerance.

    Protects against cascading failures by:
    - Counting consecutive failures
    - Opening circuit after threshold reached
    - Blocking calls while circuit is open
    - Testing recovery after timeout
    - Automatically closing circuit on success

    Examples:
        >>> # Create circuit breaker
        >>> cb = CircuitBreaker(
        ...     failure_threshold=5,
        ...     timeout=timedelta(seconds=60),
        ...     expected_exception=TimeoutException
        ... )

        >>> # Use circuit breaker
        >>> def risky_operation():
        ...     # May raise TimeoutException
        ...     return fetch_data()

        >>> try:
        ...     result = cb.call(risky_operation)
        ... except CircuitBreakerOpenError:
        ...     # Circuit is open, use fallback
        ...     result = get_cached_data()
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: timedelta = timedelta(seconds=60),
        expected_exception: Type[Exception] = Exception
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Time to wait before trying again (HALF_OPEN)
            expected_exception: Exception type to count as failure
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception

        # State
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED

        logger.info(
            f"Circuit breaker initialized: "
            f"threshold={failure_threshold}, timeout={timeout}"
        )

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: If circuit is OPEN
            Exception: Any exception raised by func
        """
        # Check circuit state
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                logger.info("Circuit breaker: Entering HALF_OPEN state")
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is OPEN (failures: {self.failure_count})"
                )

        # Execute function
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result

        except self.expected_exception as e:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True

        time_since_failure = datetime.now() - self.last_failure_time
        return time_since_failure > self.timeout

    def _on_success(self):
        """Handle successful call."""
        if self.state == CircuitState.HALF_OPEN:
            logger.info("Circuit breaker: Back to CLOSED state")
            self.state = CircuitState.CLOSED

        self.failure_count = 0

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        logger.warning(
            f"Circuit breaker: Failure #{self.failure_count} "
            f"(threshold={self.failure_threshold})"
        )

        if self.failure_count >= self.failure_threshold:
            logger.error(
                f"Circuit breaker: OPEN after {self.failure_count} failures"
            )
            self.state = CircuitState.OPEN

    def reset(self):
        """Manually reset circuit breaker to CLOSED state."""
        logger.info("Circuit breaker: Manual reset to CLOSED")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None

    @property
    def is_open(self) -> bool:
        """Check if circuit is OPEN."""
        return self.state == CircuitState.OPEN

    @property
    def is_closed(self) -> bool:
        """Check if circuit is CLOSED."""
        return self.state == CircuitState.CLOSED

    @property
    def is_half_open(self) -> bool:
        """Check if circuit is HALF_OPEN."""
        return self.state == CircuitState.HALF_OPEN

    def get_state_info(self) -> dict:
        """
        Get current circuit breaker state information.

        Returns:
            Dictionary with state, failure count, and last failure time
        """
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure_time": (
                self.last_failure_time.isoformat()
                if self.last_failure_time
                else None
            ),
            "failure_threshold": self.failure_threshold,
        }
