"""
Validation framework with Strategy pattern.

This module provides:
- Abstract Validator interface
- ValidationResult for consistent validation reporting
- Extensible validation strategies
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class ValidationResult:
    """
    Result of data validation.

    Attributes:
        is_valid: Whether validation passed
        errors: List of error messages
        warnings: List of warning messages (non-fatal)
    """

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, message: str) -> 'ValidationResult':
        """
        Add an error message.

        Args:
            message: Error message to add

        Returns:
            Self for method chaining

        Examples:
            >>> result = ValidationResult(is_valid=True)
            >>> result.add_error("Error 1").add_error("Error 2")
        """
        self.errors.append(message)
        self.is_valid = False
        return self

    def add_warning(self, message: str) -> 'ValidationResult':
        """
        Add a warning message.

        Args:
            message: Warning message to add

        Returns:
            Self for method chaining

        Examples:
            >>> result = ValidationResult(is_valid=True)
            >>> result.add_warning("Warning 1").add_warning("Warning 2")
        """
        self.warnings.append(message)
        return self

    @property
    def has_errors(self) -> bool:
        """Check if there are errors."""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if there are warnings."""
        return len(self.warnings) > 0

    def get_summary(self) -> str:
        """
        Get validation summary.

        Returns:
            Human-readable summary of validation results
        """
        if self.is_valid and not self.has_warnings:
            return "Validation passed"

        parts = []

        if self.has_errors:
            parts.append(f"Errors ({len(self.errors)}):")
            for error in self.errors:
                parts.append(f"  - {error}")

        if self.has_warnings:
            parts.append(f"Warnings ({len(self.warnings)}):")
            for warning in self.warnings:
                parts.append(f"  - {warning}")

        return "\n".join(parts)


class Validator(ABC):
    """
    Abstract base class for validators.

    Subclasses must implement the validate() method to perform
    specific validation logic.

    This enables:
    - Strategy pattern for different validation approaches
    - Consistent validation interface
    - Reusable validation logic
    """

    @abstractmethod
    def validate(self, data: Any) -> ValidationResult:
        """
        Validate data.

        Args:
            data: Data to validate

        Returns:
            ValidationResult with errors and warnings
        """
        pass

    def validate_required_fields(
        self,
        data: dict,
        required_fields: List[str]
    ) -> List[str]:
        """
        Validate that required fields exist.

        Args:
            data: Dictionary to check
            required_fields: List of required field names

        Returns:
            List of error messages for missing fields
        """
        errors = []
        for field in required_fields:
            if field not in data or data[field] is None:
                errors.append(f"Missing required field: {field}")
        return errors

    def validate_date_format(
        self,
        date_str: str,
        field_name: str = "date"
    ) -> Optional[str]:
        """
        Validate date format (YYYY-MM-DD).

        Args:
            date_str: Date string to validate
            field_name: Name of the field (for error message)

        Returns:
            Error message if invalid, None if valid
        """
        pattern = r'^\d{4}-\d{2}-\d{2}$'
        if not re.match(pattern, date_str):
            return f"Invalid {field_name} format: {date_str} (expected YYYY-MM-DD)"
        return None

    def validate_positive_number(
        self,
        value: Any,
        field_name: str
    ) -> Optional[str]:
        """
        Validate that value is a positive number.

        Args:
            value: Value to validate
            field_name: Name of the field (for error message)

        Returns:
            Error message if invalid, None if valid
        """
        if not isinstance(value, (int, float)):
            return f"{field_name} must be a number, got {type(value).__name__}"

        if value <= 0:
            return f"{field_name} must be positive, got {value}"

        return None

    def validate_email_format(
        self,
        email: str,
        field_name: str = "email"
    ) -> Optional[str]:
        """
        Validate email format.

        Args:
            email: Email string to validate
            field_name: Name of the field (for error message)

        Returns:
            Error message if invalid, None if valid
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            return f"Invalid {field_name} format: {email}"
        return None

    def validate_string_length(
        self,
        value: str,
        field_name: str,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None
    ) -> Optional[str]:
        """
        Validate string length.

        Args:
            value: String to validate
            field_name: Name of the field (for error message)
            min_length: Minimum length (optional)
            max_length: Maximum length (optional)

        Returns:
            Error message if invalid, None if valid
        """
        if not isinstance(value, str):
            return f"{field_name} must be a string, got {type(value).__name__}"

        length = len(value)

        if min_length is not None and length < min_length:
            return f"{field_name} must be at least {min_length} characters, got {length}"

        if max_length is not None and length > max_length:
            return f"{field_name} must be at most {max_length} characters, got {length}"

        return None
