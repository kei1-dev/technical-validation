#!/usr/bin/env python3
"""
Test script for dedicated lesson support feature (専属レッスン前後対応).

This script demonstrates the new auto-linking feature where adding a
"専属レッスン" automatically adds a "専属レッスン前後対応" (30 minutes).

Usage:
    # Dry-run mode (recommended for testing)
    python test_dedicated_lesson_support.py --dry-run

    # Normal mode (actual submission)
    python test_dedicated_lesson_support.py
"""

from src.models.lesson import LessonData

# Test data: Create a dedicated lesson (専属レッスン)
test_dedicated_lesson: LessonData = {
    "id": "test_dedicated_001",
    "date": "2025-11-15",  # Example date
    "student_id": "student_test",
    "student_name": "テスト太郎",
    "status": "completed",
    "duration": 60,  # 60 minutes for dedicated lesson
    "category": "専属レッスン"  # This will trigger auto-add of "専属レッスン前後対応"
}

# Expected behavior:
# 1. The above lesson will be added as "専属レッスン" (60 minutes)
# 2. Automatically, a "専属レッスン前後対応" will also be added with:
#    - Same date: "2025-11-15"
#    - Same student: "テスト太郎"
#    - Fixed duration: 30 minutes
#    - Category: "専属レッスン前後対応"


def main():
    """
    Test the dedicated lesson support feature.

    To test this:
    1. Use run_terakoya.py with --dry-run flag
    2. Add the test_dedicated_lesson to your lessons list
    3. Verify that both lessons are added:
       - 専属レッスン (60 min)
       - 専属レッスン前後対応 (30 min)
    """
    import argparse

    parser = argparse.ArgumentParser(description="Test dedicated lesson support feature")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    args = parser.parse_args()

    print("=" * 70)
    print("TEST: Dedicated Lesson Support Feature")
    print("=" * 70)
    print("\nTest Data:")
    print(f"  Date: {test_dedicated_lesson['date']}")
    print(f"  Student: {test_dedicated_lesson['student_name']}")
    print(f"  Category: {test_dedicated_lesson['category']}")
    print(f"  Duration: {test_dedicated_lesson['duration']} minutes")
    print("\nExpected Behavior:")
    print("  1. Add '専属レッスン' (60 minutes)")
    print("  2. Auto-add '専属レッスン前後対応' (30 minutes)")
    print("     - Same date: 2025-11-15")
    print("     - Same student: テスト太郎")
    print("     - Fixed duration: 30 minutes")
    print("=" * 70)

    if args.dry_run:
        print("\nDRY RUN MODE - Use run_terakoya.py to test with actual browser")
    else:
        print("\nTo test, use: python run_terakoya.py --month 2025-11 --password YOUR_PASSWORD --dry-run")

    print("\nNOTE: Make sure to update run_terakoya.py or create test data")
    print("      that includes dedicated lessons (専属レッスン)")
    print()


if __name__ == "__main__":
    main()
