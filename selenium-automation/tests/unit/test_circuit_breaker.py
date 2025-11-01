"""
Unit tests for Circuit Breaker pattern.
"""

import pytest
import time
import sys
from pathlib import Path
from datetime import timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerOpenError
)


class TestException(Exception):
    """Test exception for circuit breaker tests."""
    pass


class TestCircuitBreaker:
    """Test cases for CircuitBreaker."""

    def test_initial_state_closed(self):
        """Test circuit breaker starts in CLOSED state."""
        cb = CircuitBreaker(failure_threshold=3)

        assert cb.state == CircuitState.CLOSED
        assert cb.is_closed
        assert not cb.is_open
        assert not cb.is_half_open
        assert cb.failure_count == 0

    def test_successful_call(self):
        """Test successful function call."""
        cb = CircuitBreaker(failure_threshold=3, expected_exception=TestException)

        def success_func():
            return "success"

        result = cb.call(success_func)

        assert result == "success"
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_failure_increments_count(self):
        """Test failure increments counter."""
        cb = CircuitBreaker(failure_threshold=3, expected_exception=TestException)

        def failing_func():
            raise TestException("Test error")

        # First failure
        with pytest.raises(TestException):
            cb.call(failing_func)

        assert cb.failure_count == 1
        assert cb.state == CircuitState.CLOSED

    def test_circuit_opens_after_threshold(self):
        """Test circuit opens after reaching failure threshold."""
        cb = CircuitBreaker(failure_threshold=3, expected_exception=TestException)

        def failing_func():
            raise TestException("Test error")

        # Fail 3 times to reach threshold
        for i in range(3):
            with pytest.raises(TestException):
                cb.call(failing_func)

        assert cb.state == CircuitState.OPEN
        assert cb.is_open
        assert cb.failure_count == 3

    def test_open_circuit_blocks_calls(self):
        """Test OPEN circuit blocks calls."""
        cb = CircuitBreaker(failure_threshold=2, expected_exception=TestException)

        def failing_func():
            raise TestException("Test error")

        # Open the circuit
        for i in range(2):
            with pytest.raises(TestException):
                cb.call(failing_func)

        assert cb.is_open

        # Now calls should be blocked
        def success_func():
            return "success"

        with pytest.raises(CircuitBreakerOpenError):
            cb.call(success_func)

    def test_half_open_after_timeout(self):
        """Test circuit enters HALF_OPEN after timeout."""
        cb = CircuitBreaker(
            failure_threshold=2,
            timeout=timedelta(milliseconds=100),
            expected_exception=TestException
        )

        def failing_func():
            raise TestException("Test error")

        # Open the circuit
        for i in range(2):
            with pytest.raises(TestException):
                cb.call(failing_func)

        assert cb.is_open

        # Wait for timeout
        time.sleep(0.15)

        def success_func():
            return "success"

        # Should enter HALF_OPEN and succeed
        result = cb.call(success_func)

        assert result == "success"
        assert cb.state == CircuitState.CLOSED  # Back to closed after success

    def test_success_in_half_open_closes_circuit(self):
        """Test success in HALF_OPEN closes circuit."""
        cb = CircuitBreaker(
            failure_threshold=2,
            timeout=timedelta(milliseconds=50),
            expected_exception=TestException
        )

        def failing_func():
            raise TestException("Test error")

        # Open the circuit
        for i in range(2):
            with pytest.raises(TestException):
                cb.call(failing_func)

        # Wait for timeout
        time.sleep(0.1)

        def success_func():
            return "recovered"

        result = cb.call(success_func)

        assert result == "recovered"
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_failure_in_half_open_reopens_circuit(self):
        """Test failure in HALF_OPEN reopens circuit."""
        cb = CircuitBreaker(
            failure_threshold=2,
            timeout=timedelta(milliseconds=50),
            expected_exception=TestException
        )

        def failing_func():
            raise TestException("Test error")

        # Open the circuit
        for i in range(2):
            with pytest.raises(TestException):
                cb.call(failing_func)

        # Wait for timeout
        time.sleep(0.1)

        # Fail again in HALF_OPEN
        with pytest.raises(TestException):
            cb.call(failing_func)

        assert cb.state == CircuitState.OPEN

    def test_reset_circuit(self):
        """Test manual circuit reset."""
        cb = CircuitBreaker(failure_threshold=2, expected_exception=TestException)

        def failing_func():
            raise TestException("Test error")

        # Open the circuit
        for i in range(2):
            with pytest.raises(TestException):
                cb.call(failing_func)

        assert cb.is_open

        # Manual reset
        cb.reset()

        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_different_exception_not_counted(self):
        """Test different exception types are not counted."""
        cb = CircuitBreaker(failure_threshold=2, expected_exception=TestException)

        def other_error_func():
            raise ValueError("Different error")

        # This should raise but not count as failure
        with pytest.raises(ValueError):
            cb.call(other_error_func)

        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED

    def test_get_state_info(self):
        """Test getting state information."""
        cb = CircuitBreaker(failure_threshold=5)

        info = cb.get_state_info()

        assert info["state"] == "closed"
        assert info["failure_count"] == 0
        assert info["failure_threshold"] == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
