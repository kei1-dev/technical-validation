"""
Unit tests for SessionManager.

Tests session state management and login validation.
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timedelta

from src.automation.terakoya.session import SessionManager, SessionState
from src.models.result import Result


class TestSessionManager:
    """Test suite for SessionManager."""

    @pytest.fixture
    def mock_browser(self):
        """Create mock browser."""
        browser = Mock()
        return browser

    @pytest.fixture
    def session(self, mock_browser):
        """Create SessionManager instance."""
        return SessionManager(mock_browser)

    def test_initial_state_not_logged_in(self, session):
        """Test initial state is NOT_LOGGED_IN."""
        assert session.state == SessionState.NOT_LOGGED_IN
        assert not session.is_logged_in

    def test_mark_logged_in(self, session):
        """Test marking session as logged in."""
        session.mark_logged_in()

        assert session.state == SessionState.LOGGED_IN
        assert session.is_logged_in
        assert session._login_time is not None
        assert session._last_activity is not None

    def test_mark_logged_out(self, session):
        """Test marking session as logged out."""
        # First log in
        session.mark_logged_in()

        # Then log out
        session.mark_logged_out()

        assert session.state == SessionState.NOT_LOGGED_IN
        assert not session.is_logged_in
        assert session._login_time is None
        assert session._last_activity is None

    def test_update_activity(self, session):
        """Test updating last activity timestamp."""
        session.mark_logged_in()
        original_activity = session._last_activity

        # Wait a bit
        import time
        time.sleep(0.1)

        # Update activity
        session.update_activity()

        assert session._last_activity > original_activity

    def test_is_session_expired_when_not_logged_in(self, session):
        """Test session expiration when not logged in."""
        assert session.is_session_expired() is True

    def test_is_session_expired_when_active(self, session):
        """Test session not expired when recently active."""
        session.mark_logged_in()
        session.update_activity()

        assert session.is_session_expired() is False

    def test_is_session_expired_after_timeout(self, session):
        """Test session expiration after timeout."""
        session.mark_logged_in()

        # Simulate old activity
        session._last_activity = datetime.now() - timedelta(minutes=31)

        assert session.is_session_expired() is True

    def test_is_session_valid_with_logout_link(self, session, mock_browser):
        """Test session validation when logout link found."""
        session.mark_logged_in()

        # Mock browser to return logout link
        mock_browser.find_element.return_value = Result.success(
            Mock(),
            "Logout link found"
        )

        result = session.is_session_valid()

        assert result.is_success
        assert result.value is True
        assert "valid" in result.message.lower()

    def test_is_session_valid_with_login_form(self, session, mock_browser):
        """Test session validation when login form found."""
        session.mark_logged_in()

        # Mock browser to fail on logout link, succeed on login form
        mock_browser.find_element.side_effect = [
            Result.failure("Logout link not found"),
            Result.success(Mock(), "Login form found")
        ]

        result = session.is_session_valid()

        assert result.is_success
        assert result.value is False
        assert session.state == SessionState.NOT_LOGGED_IN

    def test_is_session_valid_uncertain_state(self, session, mock_browser):
        """Test session validation with uncertain state."""
        session.mark_logged_in()

        # Mock browser to fail both checks
        mock_browser.find_element.side_effect = [
            Result.failure("Logout link not found"),
            Result.failure("Login form not found")
        ]

        result = session.is_session_valid()

        assert result.is_success
        assert result.value is False
        assert session.state == SessionState.UNKNOWN

    def test_get_session_info(self, session):
        """Test getting session information."""
        session.mark_logged_in()
        session.update_activity()

        info = session.get_session_info()

        assert info["state"] == SessionState.LOGGED_IN.value
        assert info["logged_in"] is True
        assert info["login_time"] is not None
        assert info["last_activity"] is not None
        assert info["expired"] is False
        assert "session_duration_seconds" in info
        assert "time_since_activity_seconds" in info

    def test_get_session_info_not_logged_in(self, session):
        """Test getting session info when not logged in."""
        info = session.get_session_info()

        assert info["state"] == SessionState.NOT_LOGGED_IN.value
        assert info["logged_in"] is False
        assert info["login_time"] is None
        assert info["last_activity"] is None
        assert info["expired"] is True

    def test_require_login_when_logged_in(self, session, mock_browser):
        """Test require_login when already logged in."""
        session.mark_logged_in()

        # Mock valid session
        mock_browser.find_element.return_value = Result.success(
            Mock(),
            "Logout link found"
        )

        result = session.require_login()

        assert result.is_success

    def test_require_login_when_not_logged_in(self, session):
        """Test require_login when not logged in."""
        result = session.require_login()

        assert result.is_failure
        assert "not logged in" in result.message.lower()

    def test_require_login_when_expired(self, session):
        """Test require_login when session expired."""
        session.mark_logged_in()

        # Simulate expired session
        session._last_activity = datetime.now() - timedelta(minutes=31)

        result = session.require_login()

        assert result.is_failure
        assert "expired" in result.message.lower()
        assert session.state == SessionState.EXPIRED
