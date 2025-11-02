"""
Lesson data models with type safety.

This module provides TypedDict definitions for lesson data
to enable IDE autocomplete and static type checking.
"""

from typing import TypedDict, Literal


# Type aliases for status values
LessonStatus = Literal["completed", "pending", "cancelled"]


class LessonData(TypedDict):
    """
    Lesson data structure (TypedDict for type safety).

    Attributes:
        id: Unique lesson identifier
        date: Lesson date (YYYY-MM-DD format)
        student_id: Student identifier
        student_name: Student name
        status: Lesson status (completed/pending/cancelled)
        duration: Lesson duration in minutes
        category: Lesson category

    Examples:
        >>> lesson: LessonData = {
        ...     "id": "lesson_12345",
        ...     "date": "2025-10-15",
        ...     "student_id": "student_789",
        ...     "student_name": "山田太郎",
        ...     "status": "completed",
        ...     "duration": 60,
        ...     "category": "専属レッスン"
        ... }
    """

    id: str
    date: str
    student_id: str
    student_name: str
    status: LessonStatus
    duration: int
    category: str
