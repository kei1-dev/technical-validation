"""
Unit tests for validation layer.
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from validation.validators import ValidationResult
from validation.lesson_validator import LessonValidator
from validation.invoice_validator import InvoiceItemValidator


class TestValidationResult:
    """Test cases for ValidationResult."""

    def test_valid_result(self):
        """Test creating a valid result."""
        result = ValidationResult(is_valid=True)

        assert result.is_valid
        assert not result.has_errors
        assert not result.has_warnings

    def test_add_error(self):
        """Test adding errors."""
        result = ValidationResult(is_valid=True)
        result.add_error("First error")
        result.add_error("Second error")

        assert not result.is_valid
        assert result.has_errors
        assert len(result.errors) == 2

    def test_add_warning(self):
        """Test adding warnings."""
        result = ValidationResult(is_valid=True)
        result.add_warning("Warning message")

        assert result.is_valid  # Warnings don't affect validity
        assert result.has_warnings
        assert len(result.warnings) == 1

    def test_get_summary_valid(self):
        """Test summary for valid result."""
        result = ValidationResult(is_valid=True)
        summary = result.get_summary()

        assert summary == "Validation passed"

    def test_get_summary_with_errors(self):
        """Test summary with errors."""
        result = ValidationResult(is_valid=True)
        result.add_error("Error 1")
        result.add_error("Error 2")

        summary = result.get_summary()

        assert "Errors (2)" in summary
        assert "Error 1" in summary
        assert "Error 2" in summary


class TestLessonValidator:
    """Test cases for LessonValidator."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return LessonValidator()

    @pytest.fixture
    def valid_lesson(self):
        """Create valid lesson data."""
        return {
            "id": "lesson_12345",
            "date": "2025-10-15",
            "student_id": "student_789",
            "student_name": "山田太郎",
            "status": "completed",
            "duration": 60,
            "category": "専属レッスン"
        }

    def test_valid_lesson(self, validator, valid_lesson):
        """Test validation of valid lesson."""
        result = validator.validate(valid_lesson)

        assert result.is_valid
        assert not result.has_errors

    def test_missing_required_field(self, validator, valid_lesson):
        """Test missing required field."""
        del valid_lesson["student_name"]

        result = validator.validate(valid_lesson)

        assert not result.is_valid
        assert result.has_errors
        assert any("student_name" in error for error in result.errors)

    def test_invalid_date_format(self, validator, valid_lesson):
        """Test invalid date format."""
        valid_lesson["date"] = "2025/10/15"  # Wrong format

        result = validator.validate(valid_lesson)

        assert not result.is_valid
        assert any("date format" in error.lower() for error in result.errors)

    def test_invalid_status(self, validator, valid_lesson):
        """Test invalid status."""
        valid_lesson["status"] = "invalid_status"

        result = validator.validate(valid_lesson)

        assert not result.is_valid
        assert any("status" in error.lower() for error in result.errors)

    def test_duration_too_short(self, validator, valid_lesson):
        """Test duration below minimum."""
        valid_lesson["duration"] = 10  # Below MIN_DURATION (15)

        result = validator.validate(valid_lesson)

        assert not result.is_valid
        assert any("duration too short" in error.lower() for error in result.errors)

    def test_duration_too_long(self, validator, valid_lesson):
        """Test duration above maximum (warning)."""
        valid_lesson["duration"] = 200  # Above MAX_DURATION (180)

        result = validator.validate(valid_lesson)

        assert result.is_valid  # Still valid, but has warning
        assert result.has_warnings
        assert any("duration" in warning.lower() for warning in result.warnings)

    def test_empty_student_name(self, validator, valid_lesson):
        """Test empty student name."""
        valid_lesson["student_name"] = ""

        result = validator.validate(valid_lesson)

        assert not result.is_valid


class TestInvoiceItemValidator:
    """Test cases for InvoiceItemValidator."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return InvoiceItemValidator()

    @pytest.fixture
    def valid_invoice(self):
        """Create valid invoice item data."""
        return {
            "date": "2025-10-15",
            "category": "専属レッスン",
            "student_id": "student_789",
            "student_name": "山田太郎",
            "duration": 60,
            "unit_price": 2300
        }

    def test_valid_invoice_item(self, validator, valid_invoice):
        """Test validation of valid invoice item."""
        result = validator.validate(valid_invoice)

        assert result.is_valid
        assert not result.has_errors

    def test_missing_required_field(self, validator, valid_invoice):
        """Test missing required field."""
        del valid_invoice["student_name"]

        result = validator.validate(valid_invoice)

        assert not result.is_valid
        assert result.has_errors

    def test_unit_price_too_low(self, validator, valid_invoice):
        """Test unit price below minimum."""
        valid_invoice["unit_price"] = 500  # Below MIN_UNIT_PRICE (1000)

        result = validator.validate(valid_invoice)

        assert not result.is_valid
        assert any("unit price too low" in error.lower() for error in result.errors)

    def test_unit_price_unusual(self, validator, valid_invoice):
        """Test unusual unit price (warning)."""
        valid_invoice["unit_price"] = 4000  # Different from typical 2300

        result = validator.validate(valid_invoice)

        assert result.is_valid  # Still valid
        assert result.has_warnings

    def test_total_calculation(self, validator, valid_invoice):
        """Test total amount calculation validation."""
        valid_invoice["total"] = 2300  # Correct: 60/60 * 2300

        result = validator.validate(valid_invoice)

        assert result.is_valid

    def test_total_calculation_mismatch(self, validator, valid_invoice):
        """Test total amount mismatch."""
        valid_invoice["total"] = 3000  # Wrong

        result = validator.validate(valid_invoice)

        assert not result.is_valid
        assert any("total amount mismatch" in error.lower() for error in result.errors)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
