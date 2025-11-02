"""
Result<T> Pattern for unified error handling.

This module implements the Result pattern (Railway-oriented programming)
to provide consistent error handling across the application.
"""

from dataclasses import dataclass
from typing import Optional, Generic, TypeVar, Callable
from enum import Enum


T = TypeVar('T')
U = TypeVar('U')


class ResultStatus(Enum):
    """Status of a Result."""
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass
class Result(Generic[T]):
    """
    Unified result wrapper for operations that may succeed or fail.

    This pattern provides:
    - Consistent error handling across the application
    - Explicit success/failure states
    - Error information propagation
    - Railway-oriented programming support

    Attributes:
        status: Result status (SUCCESS or FAILURE)
        value: The result value if successful (None if failure)
        error: The exception that caused failure (None if success)
        message: Optional message describing the result

    Examples:
        >>> # Success case
        >>> result = Result.success(42, "Operation completed")
        >>> if result.is_success:
        ...     print(f"Value: {result.value}")

        >>> # Failure case
        >>> result = Result.failure("Something went wrong", ValueError("Invalid input"))
        >>> if not result.is_success:
        ...     print(f"Error: {result.message}")
    """

    status: ResultStatus
    value: Optional[T] = None
    error: Optional[Exception] = None
    message: Optional[str] = None

    @property
    def is_success(self) -> bool:
        """Check if the result represents success."""
        return self.status == ResultStatus.SUCCESS

    @property
    def is_failure(self) -> bool:
        """Check if the result represents failure."""
        return self.status == ResultStatus.FAILURE

    @classmethod
    def success(cls, value: T, message: Optional[str] = None) -> 'Result[T]':
        """
        Create a successful result.

        Args:
            value: The result value
            message: Optional success message

        Returns:
            Result instance with SUCCESS status
        """
        return cls(
            status=ResultStatus.SUCCESS,
            value=value,
            message=message
        )

    @classmethod
    def failure(
        cls,
        message: str,
        error: Optional[Exception] = None
    ) -> 'Result[T]':
        """
        Create a failure result.

        Args:
            message: Error message describing the failure
            error: Optional exception that caused the failure

        Returns:
            Result instance with FAILURE status
        """
        return cls(
            status=ResultStatus.FAILURE,
            message=message,
            error=error
        )

    def unwrap(self) -> T:
        """
        Unwrap the result value.

        Returns:
            The result value if successful

        Raises:
            ValueError: If the result is a failure
        """
        if self.is_failure:
            raise ValueError(
                f"Cannot unwrap failure result: {self.message}"
            )
        return self.value

    def unwrap_or(self, default: T) -> T:
        """
        Unwrap the result value or return a default.

        Args:
            default: Default value to return if result is failure

        Returns:
            The result value if successful, otherwise the default
        """
        return self.value if self.is_success else default

    def map(self, func: Callable[[T], U]) -> 'Result[U]':
        """
        Map a function over the success value.

        Args:
            func: Function to apply to the value (T -> U)

        Returns:
            New Result with mapped value if success, original failure otherwise

        Examples:
            >>> result = Result.success(5)
            >>> mapped = result.map(lambda x: str(x))  # Result[str]
            >>> mapped.value  # "5"
        """
        if self.is_failure:
            # Type-safe: return failure with same error info
            return Result.failure(self.message, self.error)

        try:
            new_value = func(self.value)
            return Result.success(new_value, self.message)
        except Exception as e:
            return Result.failure(str(e), e)
