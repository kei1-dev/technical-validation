"""
Terakoya automation module.

This module provides automation tools for the Terakoya platform,
including client automation, session management, and selector definitions.

Usage:
    >>> from src.automation.terakoya import TerakoyaClient, selectors
    >>> from src.automation.browser import Browser
    >>>
    >>> browser = Browser(headless=True)
    >>> client = TerakoyaClient(browser)
    >>> # Use client for automation
"""

from .client import TerakoyaClient
from .selectors import TerakoyaSelectors, selectors
from .session import SessionManager, SessionState

__all__ = [
    "TerakoyaClient",
    "TerakoyaSelectors",
    "selectors",
    "SessionManager",
    "SessionState",
]

__version__ = "0.1.0"
