"""
Lesson data validator.

Validates lesson data structure and business rules.
"""

from typing import Dict, Any

from .validators import Validator, ValidationResult


class LessonValidator(Validator):
    """
    Validator for lesson data.

    Validates:
    - Required fields
    - Data types
    - Date format
    - Business rules (duration, status)

    Examples:
        >>> validator = LessonValidator()
        >>> lesson = {
        ...     "id": "lesson_12345",
        ...     "date": "2025-10-15",
        ...     "student_id": "student_789",
        ...     "student_name": "山田太郎",
        ...     "status": "completed",
        ...     "duration": 60,
        ...     "category": "専属レッスン"
        ... }
        >>> result = validator.validate(lesson)
        >>> if result.is_valid:
        ...     print("Lesson data is valid")
    """

    # Valid status values
    VALID_STATUSES = ["completed", "pending", "cancelled"]

    # Business rule constraints
    MIN_DURATION = 15  # minutes
    MAX_DURATION = 180  # minutes

    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """
        Validate lesson data.

        Args:
            data: Lesson data dictionary

        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult(is_valid=True)

        # Required fields
        required_fields = [
            "id",
            "date",
            "student_id",
            "student_name",
            "status",
            "duration",
            "category"
        ]

        errors = self.validate_required_fields(data, required_fields)
        for error in errors:
            result.add_error(error)

        if not result.is_valid:
            return result

        # Validate id
        error = self.validate_string_length(
            data["id"],
            "id",
            min_length=1,
            max_length=100
        )
        if error:
            result.add_error(error)

        # Validate date format
        error = self.validate_date_format(data["date"], "date")
        if error:
            result.add_error(error)

        # Validate student_id
        error = self.validate_string_length(
            data["student_id"],
            "student_id",
            min_length=1,
            max_length=100
        )
        if error:
            result.add_error(error)

        # Validate student_name
        error = self.validate_string_length(
            data["student_name"],
            "student_name",
            min_length=1,
            max_length=200
        )
        if error:
            result.add_error(error)

        # Validate status
        if data["status"] not in self.VALID_STATUSES:
            result.add_error(
                f"Invalid status: {data['status']} "
                f"(must be one of: {', '.join(self.VALID_STATUSES)})"
            )

        # Validate duration
        error = self.validate_positive_number(data["duration"], "duration")
        if error:
            result.add_error(error)
        else:
            # Business rule: duration range
            duration = data["duration"]
            if duration < self.MIN_DURATION:
                result.add_error(
                    f"Duration too short: {duration} minutes "
                    f"(minimum: {self.MIN_DURATION})"
                )
            elif duration > self.MAX_DURATION:
                result.add_warning(
                    f"Duration unusually long: {duration} minutes "
                    f"(maximum recommended: {self.MAX_DURATION})"
                )

        # Validate category
        error = self.validate_string_length(
            data["category"],
            "category",
            min_length=1,
            max_length=100
        )
        if error:
            result.add_error(error)

        return result
