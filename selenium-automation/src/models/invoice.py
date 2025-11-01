"""
Invoice data models.

This module provides data structures for invoice processing
including invoice items and processing results.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, Literal
from enum import Enum


# Type alias for invoice status
InvoiceStatusType = Literal["added", "failed", "skipped"]


class InvoiceStatus(Enum):
    """Invoice processing status."""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    PENDING = "pending"


@dataclass
class InvoiceResult:
    """
    Result of invoice item processing.

    Attributes:
        lesson: Lesson data that was processed
        status: Processing status
        error_message: Error message if failed
        retry_count: Number of retries attempted
        screenshot_path: Path to error screenshot if available

    Examples:
        >>> result = InvoiceResult(
        ...     lesson=lesson_data,
        ...     status=InvoiceStatus.SUCCESS,
        ...     retry_count=0
        ... )
        >>> if result.status == InvoiceStatus.SUCCESS:
        ...     print("Invoice added successfully")
    """

    lesson: Dict[str, Any]
    status: InvoiceStatus
    error_message: Optional[str] = None
    retry_count: int = 0
    screenshot_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary format.

        Returns:
            Dictionary representation of the result
        """
        return {
            "lesson_id": self.lesson.get("id"),
            "date": self.lesson.get("date"),
            "student_name": self.lesson.get("student_name"),
            "status": self.status.value,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "screenshot_path": self.screenshot_path
        }

    @property
    def is_success(self) -> bool:
        """Check if processing was successful."""
        return self.status == InvoiceStatus.SUCCESS

    @property
    def is_failure(self) -> bool:
        """Check if processing failed."""
        return self.status == InvoiceStatus.FAILED

    @property
    def is_skipped(self) -> bool:
        """Check if processing was skipped."""
        return self.status == InvoiceStatus.SKIPPED


@dataclass
class InvoiceSummary:
    """
    Summary of batch invoice processing.

    Attributes:
        target_month: Target month (YYYY-MM format)
        execution_time: Execution timestamp (ISO 8601)
        total_lessons: Total number of lessons retrieved
        existing_invoices: Number of existing invoices
        processed: Number of items processed
        success: Number of successful additions
        failed: Number of failures
        skipped: Number of skipped items
        dry_run: Whether this was a dry run
        submitted: Whether the invoice was submitted
        results: List of individual results
        errors: List of error details

    Examples:
        >>> summary = InvoiceSummary(
        ...     target_month="2025-10",
        ...     execution_time="2025-11-01T10:30:00+09:00",
        ...     total_lessons=25,
        ...     existing_invoices=5,
        ...     processed=20,
        ...     success=18,
        ...     failed=2,
        ...     skipped=5,
        ...     dry_run=False,
        ...     submitted=True,
        ...     results=[],
        ...     errors=[]
        ... )
    """

    target_month: str
    execution_time: str
    total_lessons: int
    existing_invoices: int
    processed: int
    success: int
    failed: int
    skipped: int
    dry_run: bool
    submitted: bool
    results: list = None
    errors: list = None

    def __post_init__(self):
        """Initialize default values for lists."""
        if self.results is None:
            self.results = []
        if self.errors is None:
            self.errors = []

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary format.

        Returns:
            Dictionary representation of the summary
        """
        return {
            "target_month": self.target_month,
            "execution_time": self.execution_time,
            "total_lessons": self.total_lessons,
            "existing_invoices": self.existing_invoices,
            "processed": self.processed,
            "success": self.success,
            "failed": self.failed,
            "skipped": self.skipped,
            "dry_run": self.dry_run,
            "submitted": self.submitted,
            "results": self.results,
            "errors": self.errors
        }
