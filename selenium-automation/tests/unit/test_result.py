"""
Unit tests for Result<T> pattern.
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from models.result import Result, ResultStatus


class TestResult:
    """Test cases for Result class."""

    def test_success_creation(self):
        """Test creating a successful result."""
        result = Result.success(42, "Operation completed")

        assert result.is_success
        assert not result.is_failure
        assert result.status == ResultStatus.SUCCESS
        assert result.value == 42
        assert result.message == "Operation completed"
        assert result.error is None

    def test_failure_creation(self):
        """Test creating a failure result."""
        error = ValueError("Invalid input")
        result = Result.failure("Operation failed", error)

        assert result.is_failure
        assert not result.is_success
        assert result.status == ResultStatus.FAILURE
        assert result.value is None
        assert result.message == "Operation failed"
        assert result.error == error

    def test_success_without_message(self):
        """Test success without message."""
        result = Result.success(100)

        assert result.is_success
        assert result.value == 100
        assert result.message is None

    def test_failure_without_exception(self):
        """Test failure without exception object."""
        result = Result.failure("Something went wrong")

        assert result.is_failure
        assert result.message == "Something went wrong"
        assert result.error is None

    def test_unwrap_success(self):
        """Test unwrapping successful result."""
        result = Result.success("data")
        value = result.unwrap()

        assert value == "data"

    def test_unwrap_failure_raises(self):
        """Test unwrapping failure raises exception."""
        result = Result.failure("Error occurred")

        with pytest.raises(ValueError, match="Cannot unwrap failure result"):
            result.unwrap()

    def test_unwrap_or_with_success(self):
        """Test unwrap_or with successful result."""
        result = Result.success(42)
        value = result.unwrap_or(0)

        assert value == 42

    def test_unwrap_or_with_failure(self):
        """Test unwrap_or with failure result."""
        result = Result.failure("Error")
        value = result.unwrap_or(0)

        assert value == 0

    def test_map_success(self):
        """Test mapping over successful result."""
        result = Result.success(5)
        mapped = result.map(lambda x: x * 2)

        assert mapped.is_success
        assert mapped.value == 10

    def test_map_failure(self):
        """Test mapping over failure returns original."""
        result = Result.failure("Error")
        mapped = result.map(lambda x: x * 2)

        assert mapped.is_failure
        assert mapped.message == "Error"

    def test_map_with_exception(self):
        """Test mapping with function that raises exception."""
        result = Result.success(5)
        mapped = result.map(lambda x: 1 / 0)  # Division by zero

        assert mapped.is_failure
        assert mapped.error is not None
        assert isinstance(mapped.error, ZeroDivisionError)

    def test_result_with_none_value(self):
        """Test result with None as valid value."""
        result = Result.success(None, "Completed with no value")

        assert result.is_success
        assert result.value is None

    def test_result_with_complex_types(self):
        """Test result with complex types."""
        data = {"key": "value", "list": [1, 2, 3]}
        result = Result.success(data)

        assert result.is_success
        assert result.value == data
        assert result.value["key"] == "value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
