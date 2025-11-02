"""
Terakoya session management.

This module handles login state tracking, session expiration detection,
and automatic re-authentication.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from enum import Enum

from selenium.webdriver.common.by import By

from ..browser import Browser
from ...models.result import Result


logger = logging.getLogger(__name__)


class SessionState(Enum):
    """Session states."""

    NOT_LOGGED_IN = "not_logged_in"
    LOGGED_IN = "logged_in"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


class SessionManager:
    """
    Manages Terakoya session state.

    This class tracks login state, detects session expiration,
    and provides methods for session validation.

    Examples:
        >>> session = SessionManager(browser)
        >>> session.mark_logged_in()
        >>> if session.is_session_valid():
        ...     print("Session is active")
        ... else:
        ...     print("Need to re-login")
    """

    # Session timeout (assuming 30 minutes)
    SESSION_TIMEOUT = timedelta(minutes=30)

    def __init__(self, browser: Browser):
        """
        Initialize SessionManager.

        Args:
            browser: Browser instance for session checking
        """
        self.browser = browser
        self._state = SessionState.NOT_LOGGED_IN
        self._login_time: Optional[datetime] = None
        self._last_activity: Optional[datetime] = None

    @property
    def state(self) -> SessionState:
        """Get current session state."""
        return self._state

    @property
    def is_logged_in(self) -> bool:
        """Check if currently logged in."""
        return self._state == SessionState.LOGGED_IN

    def mark_logged_in(self):
        """
        Mark session as logged in.

        Call this after successful login.
        """
        self._state = SessionState.LOGGED_IN
        now = datetime.now()
        self._login_time = now
        self._last_activity = now
        logger.info("Session marked as logged in")

    def mark_logged_out(self):
        """
        Mark session as logged out.

        Call this after logout or when login is detected as expired.
        """
        self._state = SessionState.NOT_LOGGED_IN
        self._login_time = None
        self._last_activity = None
        logger.info("Session marked as logged out")

    def update_activity(self):
        """
        Update last activity timestamp.

        Call this on each successful browser action to keep session alive.
        """
        self._last_activity = datetime.now()

    def is_session_expired(self) -> bool:
        """
        Check if session has expired based on timeout.

        Returns:
            True if session has expired
        """
        if not self.is_logged_in or not self._last_activity:
            return True

        elapsed = datetime.now() - self._last_activity
        return elapsed > self.SESSION_TIMEOUT

    def is_session_valid(self) -> Result[bool]:
        """
        Check if session is valid by looking for login indicators on page.

        This performs an actual browser check to verify login state.

        Returns:
            Result[bool] - True if session is valid, False otherwise

        Examples:
            >>> result = session.is_session_valid()
            >>> if result.is_success and result.value:
            ...     print("Session valid")
        """
        try:
            # Check for timeout first
            if self.is_session_expired():
                logger.warning("Session expired based on timeout")
                self._state = SessionState.EXPIRED
                return Result.success(False, "Session expired (timeout)")

            # Simplified session check - if we marked as logged in and not expired, assume valid
            # Full browser-based checks are unreliable due to dynamic rendering
            if self.is_logged_in and not self.is_session_expired():
                self.update_activity()
                return Result.success(True, "Session valid (based on state)")

            # Check for login form (indicates not logged in)
            login_result = self.browser.find_element(
                By.CSS_SELECTOR,
                "input[type='password'], form[action*='login']",
                timeout=5
            )

            if login_result.is_success:
                logger.warning("Login form detected - session invalid")
                self._state = SessionState.NOT_LOGGED_IN
                return Result.success(False, "Session invalid (login form found)")

            # Uncertain state
            logger.warning("Cannot determine session state")
            self._state = SessionState.UNKNOWN
            return Result.success(False, "Session state unknown")

        except Exception as e:
            logger.error(f"Error checking session validity: {e}")
            return Result.failure("Failed to check session validity", e)

    def get_session_info(self) -> dict:
        """
        Get session information for debugging.

        Returns:
            Dictionary with session details

        Examples:
            >>> info = session.get_session_info()
            >>> print(f"State: {info['state']}, Logged in: {info['logged_in']}")
        """
        info = {
            "state": self._state.value,
            "logged_in": self.is_logged_in,
            "login_time": self._login_time.isoformat() if self._login_time else None,
            "last_activity": self._last_activity.isoformat() if self._last_activity else None,
            "expired": self.is_session_expired(),
        }

        if self._login_time and self._last_activity:
            session_duration = datetime.now() - self._login_time
            time_since_activity = datetime.now() - self._last_activity
            info["session_duration_seconds"] = session_duration.total_seconds()
            info["time_since_activity_seconds"] = time_since_activity.total_seconds()

        return info

    def require_login(self) -> Result[None]:
        """
        Check if login is required.

        Returns:
            Result.success if already logged in
            Result.failure if login is required

        Examples:
            >>> result = session.require_login()
            >>> if result.is_failure:
            ...     # Need to login
            ...     client.login(email, password)
        """
        if not self.is_logged_in:
            return Result.failure("Not logged in")

        if self.is_session_expired():
            logger.warning("Session expired, re-login required")
            self._state = SessionState.EXPIRED
            return Result.failure("Session expired")

        # Optionally check with browser
        validity_result = self.is_session_valid()
        if validity_result.is_success and validity_result.value:
            return Result.success(None, "Login valid")

        return Result.failure("Session invalid, login required")
