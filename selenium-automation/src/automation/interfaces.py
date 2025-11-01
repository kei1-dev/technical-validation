"""
Abstract interfaces for automation components.

This module defines abstract base classes that enable dependency inversion
and make testing easier through mocking.
"""

from abc import ABC, abstractmethod
from typing import List
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from ..models.result import Result


class WebBrowser(ABC):
    """
    Abstract interface for browser operations.

    This interface enables:
    - Dependency inversion (depend on abstraction, not concrete Browser)
    - Easy mocking for unit tests
    - Swappable browser implementations

    Implementing classes must provide all browser operations
    and return Result<T> for consistent error handling.
    """

    @abstractmethod
    def navigate(self, url: str) -> Result[None]:
        """
        Navigate to the specified URL.

        Args:
            url: Target URL

        Returns:
            Result with None value on success, error information on failure
        """
        pass

    @abstractmethod
    def find_element(
        self,
        by: By,
        value: str,
        timeout: int = 10
    ) -> Result[WebElement]:
        """
        Find a single element with explicit wait.

        Args:
            by: Selenium locator strategy (By.ID, By.CSS_SELECTOR, etc.)
            value: Locator value
            timeout: Maximum wait time in seconds

        Returns:
            Result containing the WebElement on success, error on failure
        """
        pass

    @abstractmethod
    def find_elements(
        self,
        by: By,
        value: str,
        timeout: int = 10
    ) -> Result[List[WebElement]]:
        """
        Find multiple elements with explicit wait.

        Args:
            by: Selenium locator strategy
            value: Locator value
            timeout: Maximum wait time in seconds

        Returns:
            Result containing list of WebElements on success, error on failure
        """
        pass

    @abstractmethod
    def click(
        self,
        by: By,
        value: str,
        timeout: int = 10
    ) -> Result[None]:
        """
        Click an element.

        Args:
            by: Selenium locator strategy
            value: Locator value
            timeout: Maximum wait time in seconds

        Returns:
            Result with None on success, error on failure
        """
        pass

    @abstractmethod
    def input_text(
        self,
        by: By,
        value: str,
        text: str,
        timeout: int = 10
    ) -> Result[None]:
        """
        Input text into an element.

        Args:
            by: Selenium locator strategy
            value: Locator value
            text: Text to input
            timeout: Maximum wait time in seconds

        Returns:
            Result with None on success, error on failure
        """
        pass

    @abstractmethod
    def get_page_source(self) -> Result[str]:
        """
        Get current page HTML source.

        Returns:
            Result containing HTML source string on success
        """
        pass

    @abstractmethod
    def screenshot(self, filepath: str) -> Result[bool]:
        """
        Take a screenshot and save to file.

        Args:
            filepath: Path to save screenshot

        Returns:
            Result with True on success, False on failure
        """
        pass

    @abstractmethod
    def wait_for_page_load(self, timeout: int = 30) -> Result[None]:
        """
        Wait for page to fully load.

        Args:
            timeout: Maximum wait time in seconds

        Returns:
            Result with None on success, error on timeout
        """
        pass

    @abstractmethod
    def close(self):
        """
        Close the browser and clean up resources.

        This method should not raise exceptions.
        """
        pass

    @abstractmethod
    def __enter__(self):
        """Context manager entry."""
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass
