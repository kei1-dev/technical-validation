"""
Invoice item validator.

Validates invoice item data structure and business rules.
"""

from typing import Dict, Any

from .validators import Validator, ValidationResult


class InvoiceItemValidator(Validator):
    """
    Validator for invoice item data.

    Validates:
    - Required fields
    - Data types
    - Date format
    - Business rules (unit price, duration)

    Examples:
        >>> validator = InvoiceItemValidator()
        >>> item = {
        ...     "date": "2025-10-15",
        ...     "category": "専属レッスン",
        ...     "student_id": "student_789",
        ...     "student_name": "山田太郎",
        ...     "duration": 60,
        ...     "unit_price": 2300
        ... }
        >>> result = validator.validate(item)
        >>> if result.is_valid:
        ...     print("Invoice item is valid")
    """

    # Business rule constraints
    MIN_UNIT_PRICE = 1000  # yen
    MAX_UNIT_PRICE = 10000  # yen
    TYPICAL_UNIT_PRICE = 2300  # yen
    MIN_DURATION = 15  # minutes
    MAX_DURATION = 180  # minutes
    TYPICAL_DURATION = 60  # minutes

    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """
        Validate invoice item data.

        Args:
            data: Invoice item data dictionary

        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult(is_valid=True)

        # Required fields
        required_fields = [
            "date",
            "category",
            "student_id",
            "student_name",
            "duration",
            "unit_price"
        ]

        errors = self.validate_required_fields(data, required_fields)
        for error in errors:
            result.add_error(error)

        if not result.is_valid:
            return result

        # Validate date format
        error = self.validate_date_format(data["date"], "date")
        if error:
            result.add_error(error)

        # Validate category
        error = self.validate_string_length(
            data["category"],
            "category",
            min_length=1,
            max_length=100
        )
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
                    f"(typical: {self.TYPICAL_DURATION})"
                )

        # Validate unit_price
        error = self.validate_positive_number(data["unit_price"], "unit_price")
        if error:
            result.add_error(error)
        else:
            # Business rule: unit price range
            unit_price = data["unit_price"]
            if unit_price < self.MIN_UNIT_PRICE:
                result.add_error(
                    f"Unit price too low: {unit_price} yen "
                    f"(minimum: {self.MIN_UNIT_PRICE})"
                )
            elif unit_price > self.MAX_UNIT_PRICE:
                result.add_warning(
                    f"Unit price unusually high: {unit_price} yen "
                    f"(typical: {self.TYPICAL_UNIT_PRICE})"
                )
            elif abs(unit_price - self.TYPICAL_UNIT_PRICE) > 500:
                result.add_warning(
                    f"Unit price differs from typical: {unit_price} yen "
                    f"(typical: {self.TYPICAL_UNIT_PRICE})"
                )

        # Validate total (if provided)
        if "total" in data:
            error = self.validate_positive_number(data["total"], "total")
            if error:
                result.add_error(error)
            else:
                # Verify calculation
                expected_total = (data["duration"] / 60) * data["unit_price"]
                if abs(data["total"] - expected_total) > 1:  # Allow 1 yen rounding
                    result.add_error(
                        f"Total amount mismatch: {data['total']} yen "
                        f"(expected: {expected_total:.0f} = "
                        f"{data['duration']}/60 * {data['unit_price']})"
                    )

        return result
