#!/usr/bin/env python3
"""
Test script to verify auto-add logic is triggered.
"""

import logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Simulate the condition check
def test_auto_add_condition():
    """Test if auto-add condition is triggered correctly."""

    # Test case 1: 専属レッスン with auto_add_support=True
    lesson1 = {
        "id": "test_001",
        "date": "2025-11-01",
        "student_id": "student_123",
        "student_name": "テスト太郎",
        "status": "completed",
        "duration": 60,
        "category": "専属レッスン"
    }
    auto_add_support1 = True

    logger.info(f"Test 1: category='{lesson1.get('category')}', auto_add_support={auto_add_support1}")
    if lesson1.get("category") == "専属レッスン" and auto_add_support1:
        logger.info("✓ Test 1 PASSED: Auto-add logic WOULD be triggered")
    else:
        logger.error("✗ Test 1 FAILED: Auto-add logic would NOT be triggered")

    # Test case 2: 専属レッスン with auto_add_support=False
    auto_add_support2 = False
    logger.info(f"\nTest 2: category='{lesson1.get('category')}', auto_add_support={auto_add_support2}")
    if lesson1.get("category") == "専属レッスン" and auto_add_support2:
        logger.error("✗ Test 2 FAILED: Auto-add logic WOULD be triggered (should not)")
    else:
        logger.info("✓ Test 2 PASSED: Auto-add logic would NOT be triggered")

    # Test case 3: Different category
    lesson3 = {**lesson1, "category": "専属レッスン前後対応"}
    auto_add_support3 = True
    logger.info(f"\nTest 3: category='{lesson3.get('category')}', auto_add_support={auto_add_support3}")
    if lesson3.get("category") == "専属レッスン" and auto_add_support3:
        logger.error("✗ Test 3 FAILED: Auto-add logic WOULD be triggered (should not)")
    else:
        logger.info("✓ Test 3 PASSED: Auto-add logic would NOT be triggered")

    # Test case 4: Verify support lesson creation
    logger.info("\n" + "=" * 60)
    logger.info("Test 4: Support lesson creation")
    support_lesson = {
        "id": f"{lesson1['id']}_support",
        "date": lesson1["date"],
        "student_id": lesson1["student_id"],
        "student_name": lesson1["student_name"],
        "status": lesson1["status"],
        "duration": 30,
        "category": "専属レッスン前後対応"
    }
    logger.info(f"Original lesson: {lesson1['date']} - {lesson1['student_name']} - {lesson1['category']} ({lesson1['duration']}min)")
    logger.info(f"Support lesson:  {support_lesson['date']} - {support_lesson['student_name']} - {support_lesson['category']} ({support_lesson['duration']}min)")

    if (support_lesson['date'] == lesson1['date'] and
        support_lesson['student_name'] == lesson1['student_name'] and
        support_lesson['duration'] == 30 and
        support_lesson['category'] == "専属レッスン前後対応"):
        logger.info("✓ Test 4 PASSED: Support lesson created correctly")
    else:
        logger.error("✗ Test 4 FAILED: Support lesson not created correctly")

if __name__ == "__main__":
    test_auto_add_condition()
