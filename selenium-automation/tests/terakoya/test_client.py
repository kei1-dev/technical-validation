"""
Unit tests for TerakoyaClient.

Tests client methods with mocked browser.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from src.automation.terakoya.client import TerakoyaClient
from src.models.result import Result
from src.models.lesson import LessonData
from src.utils.config import SecureString


class TestTerakoyaClient:
    """Test suite for TerakoyaClient."""

    @pytest.fixture
    def mock_browser(self):
        """Create mock browser."""
        browser = Mock()
        browser.screenshot.return_value = Result.success(True, "Screenshot saved")
        return browser

    @pytest.fixture
    def client(self, mock_browser, tmp_path):
        """Create TerakoyaClient instance with mock browser."""
        return TerakoyaClient(
            browser=mock_browser,
            base_url="https://test.terakoya.net",
            screenshot_dir=tmp_path
        )

    def test_initialization(self, client):
        """Test client initialization."""
        assert client.base_url == "https://test.terakoya.net"
        assert client.selectors is not None
        assert client.session is not None
        assert client.lesson_validator is not None
        assert client.invoice_validator is not None

    def test_ensure_logged_in_success(self, client):
        """Test ensure_logged_in when session is valid."""
        client.session.mark_logged_in()

        # Mock valid session
        client.browser.find_element.return_value = Result.success(
            Mock(),
            "Logout link found"
        )

        result = client.ensure_logged_in()

        assert result.is_success

    def test_ensure_logged_in_failure(self, client):
        """Test ensure_logged_in when not logged in."""
        result = client.ensure_logged_in()

        assert result.is_failure

    def test_login_success(self, client, mock_browser):
        """Test successful login."""
        # Mock browser responses
        mock_browser.navigate.return_value = Result.success(None, "Navigated")
        mock_browser.wait_for_page_load.return_value = Result.success(None, "Loaded")
        mock_browser.input_text.return_value = Result.success(None, "Input success")
        mock_browser.click.return_value = Result.success(None, "Clicked")

        # Mock no error message
        mock_browser.find_element.side_effect = [
            Result.failure("No error"),  # Error message check
            Result.success(Mock(), "Logout link found")  # Logout link check
        ]

        password = SecureString("test_password")
        result = client.login("test@example.com", password)

        assert result.is_success
        assert client.session.is_logged_in

    def test_login_navigation_failure(self, client, mock_browser):
        """Test login with navigation failure."""
        mock_browser.navigate.return_value = Result.failure("Navigation failed")

        password = SecureString("test_password")
        result = client.login("test@example.com", password)

        assert result.is_failure
        assert not client.session.is_logged_in

    def test_login_email_input_failure(self, client, mock_browser):
        """Test login with email input failure."""
        mock_browser.navigate.return_value = Result.success(None, "Navigated")
        mock_browser.wait_for_page_load.return_value = Result.success(None, "Loaded")
        mock_browser.input_text.return_value = Result.failure("Input failed")

        password = SecureString("test_password")
        result = client.login("test@example.com", password)

        assert result.is_failure

    def test_login_with_error_message(self, client, mock_browser):
        """Test login when error message is displayed."""
        mock_browser.navigate.return_value = Result.success(None, "Navigated")
        mock_browser.wait_for_page_load.return_value = Result.success(None, "Loaded")
        mock_browser.input_text.return_value = Result.success(None, "Input success")
        mock_browser.click.return_value = Result.success(None, "Clicked")

        # Mock error message found
        mock_browser.find_element.return_value = Result.success(
            Mock(),
            "Error message found"
        )

        password = SecureString("test_password")
        result = client.login("test@example.com", password)

        assert result.is_failure
        assert "credentials may be incorrect" in result.message.lower()

    def test_get_lessons_for_month_not_logged_in(self, client):
        """Test get_lessons_for_month when not logged in."""
        result = client.get_lessons_for_month(2025, 10)

        assert result.is_failure
        assert "not logged in" in result.message.lower()

    def test_get_lessons_for_month_navigation_failure(self, client, mock_browser):
        """Test get_lessons_for_month with navigation failure."""
        client.session.mark_logged_in()

        # Mock valid session
        mock_browser.find_element.return_value = Result.success(
            Mock(),
            "Logout link"
        )

        mock_browser.navigate.return_value = Result.failure("Navigation failed")

        result = client.get_lessons_for_month(2025, 10)

        assert result.is_failure

    def test_is_duplicate_by_date_and_student_id(self, client):
        """Test duplicate detection by date and student_id."""
        lesson: LessonData = {
            "id": "lesson_1",
            "date": "2025-10-15",
            "student_id": "student_123",
            "student_name": "山田太郎",
            "status": "completed",
            "duration": 60,
            "category": "専属レッスン"
        }

        existing = [
            {
                "date": "2025-10-15",
                "student_id": "student_123",
                "student_name": "山田太郎"
            }
        ]

        assert client.is_duplicate(lesson, existing) is True

    def test_is_duplicate_by_date_and_student_name(self, client):
        """Test duplicate detection by date and student_name."""
        lesson: LessonData = {
            "id": "lesson_1",
            "date": "2025-10-15",
            "student_id": "student_123",
            "student_name": "山田太郎",
            "status": "completed",
            "duration": 60,
            "category": "専属レッスン"
        }

        existing = [
            {
                "date": "2025-10-15",
                "student_id": "different_id",
                "student_name": "山田太郎"
            }
        ]

        assert client.is_duplicate(lesson, existing) is True

    def test_is_not_duplicate(self, client):
        """Test when lesson is not a duplicate."""
        lesson: LessonData = {
            "id": "lesson_1",
            "date": "2025-10-15",
            "student_id": "student_123",
            "student_name": "山田太郎",
            "status": "completed",
            "duration": 60,
            "category": "専属レッスン"
        }

        existing = [
            {
                "date": "2025-10-16",  # Different date
                "student_id": "student_123",
                "student_name": "山田太郎"
            }
        ]

        assert client.is_duplicate(lesson, existing) is False

    def test_add_invoice_item_invalid_lesson_data(self, client):
        """Test add_invoice_item with invalid lesson data."""
        invalid_lesson: LessonData = {
            "id": "",  # Invalid: empty ID
            "date": "invalid-date",  # Invalid date format
            "student_id": "student_123",
            "student_name": "山田太郎",
            "status": "completed",
            "duration": 60,
            "category": "専属レッスン"
        }

        result = client.add_invoice_item(invalid_lesson)

        assert result.is_failure
        assert "invalid" in result.message.lower()

    def test_navigate_to_invoice_page_not_logged_in(self, client):
        """Test navigate_to_invoice_page when not logged in."""
        result = client.navigate_to_invoice_page(2025, 10)

        assert result.is_failure
        assert "not logged in" in result.message.lower()

    def test_navigate_to_invoice_page_success(self, client, mock_browser):
        """Test successful navigation to invoice page."""
        client.session.mark_logged_in()

        # Mock valid session
        mock_browser.find_element.return_value = Result.success(
            Mock(),
            "Logout link"
        )

        mock_browser.navigate.return_value = Result.success(None, "Navigated")

        result = client.navigate_to_invoice_page(2025, 10)

        assert result.is_success

    def test_get_existing_invoices_no_invoices(self, client, mock_browser):
        """Test get_existing_invoices when table not found."""
        mock_browser.find_elements.return_value = Result.failure(
            "Table not found"
        )

        result = client.get_existing_invoices()

        assert result.is_success
        assert result.value == []

    def test_save_screenshot(self, client, mock_browser, tmp_path):
        """Test screenshot saving."""
        result = client._save_screenshot("test")

        assert result.is_success

        # Verify screenshot was called
        mock_browser.screenshot.assert_called_once()

        # Verify filename contains timestamp
        call_args = mock_browser.screenshot.call_args[0][0]
        assert "test_" in call_args
        assert call_args.endswith(".png")
