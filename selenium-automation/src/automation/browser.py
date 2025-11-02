"""
Browser automation using Selenium WebDriver.

This module provides a wrapper around Selenium WebDriver with:
- Result<T> pattern for consistent error handling
- Explicit waits for reliable element location
- Context manager support for automatic cleanup
- Screenshot capabilities for debugging
"""

import logging
from pathlib import Path
from typing import List, Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
    ElementNotInteractableException
)
from webdriver_manager.chrome import ChromeDriverManager

from .interfaces import WebBrowser
from .browser_config import BrowserConfig
from ..models.result import Result


logger = logging.getLogger(__name__)


class Browser(WebBrowser):
    """
    Chrome WebDriver wrapper implementing WebBrowser interface.

    This class provides:
    - Automatic ChromeDriver management via webdriver-manager
    - Configurable headless mode
    - Custom download directory support
    - Explicit waits for all operations
    - Automatic resource cleanup

    Examples:
        >>> # Basic usage
        >>> browser = Browser(headless=False)
        >>> result = browser.navigate("https://example.com")
        >>> if result.is_success:
        ...     print("Navigation successful")
        >>> browser.close()

        >>> # Context manager usage (recommended)
        >>> with Browser(headless=True) as browser:
        ...     browser.navigate("https://example.com")
        ...     # Automatically closed
    """

    def __init__(
        self,
        config: Optional[BrowserConfig] = None,
        headless: bool = False,
        download_dir: Optional[str] = None
    ):
        """
        Initialize Browser instance.

        Args:
            config: Browser configuration (recommended). If provided,
                   headless and download_dir are ignored.
            headless: Run browser in headless mode (default: False).
                     Only used if config is None.
            download_dir: Custom download directory (default: None).
                         Only used if config is None.

        Raises:
            WebDriverException: If ChromeDriver initialization fails

        Examples:
            >>> # Using BrowserConfig (recommended)
            >>> config = BrowserConfig(headless=True, timeout=60)
            >>> browser = Browser(config=config)

            >>> # Using individual parameters (backward compatible)
            >>> browser = Browser(headless=True)

            >>> # Using preset configurations
            >>> browser = Browser(config=BrowserConfig.for_testing())
        """
        # Use config if provided, otherwise create from parameters
        if config is None:
            config = BrowserConfig(
                headless=headless,
                download_dir=download_dir
            )

        self.config = config
        self.driver = None

        try:
            # Configure Chrome options
            options = Options()

            if config.headless:
                options.add_argument("--headless")
                options.add_argument("--disable-gpu")

            # Set window size
            width, height = config.window_size
            options.add_argument(f"--window-size={width},{height}")

            # Disable automation flags if requested
            if config.disable_automation_flags:
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option("useAutomationExtension", False)

            # Set custom user agent if provided
            if config.user_agent:
                options.add_argument(f"--user-agent={config.user_agent}")

            # Custom download directory
            if config.download_dir:
                prefs = {
                    "download.default_directory": str(Path(config.download_dir).absolute()),
                    "download.prompt_for_download": False,
                }
                options.add_experimental_option("prefs", prefs)

            # Initialize ChromeDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)

            logger.info(
                f"Browser initialized (headless={config.headless}, "
                f"window_size={config.window_size}, timeout={config.timeout})"
            )

        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}", exc_info=True)
            # Clean up any partially initialized driver
            self.close()
            raise WebDriverException(f"Browser initialization failed: {e}")

    def navigate(self, url: str) -> Result[None]:
        """Navigate to URL."""
        try:
            logger.debug(f"Navigating to: {url}")
            self.driver.get(url)
            return Result.success(None, f"Navigated to {url}")

        except WebDriverException as e:
            logger.error(f"Navigation failed: {e}")
            return Result.failure(f"Navigation failed: {url}", e)

    def find_element(
        self,
        by: By,
        value: str,
        timeout: Optional[int] = None
    ) -> Result[WebElement]:
        """Find a single element with explicit wait."""
        if timeout is None:
            timeout = self.config.timeout

        try:
            logger.debug(f"Finding element: {by}={value} (timeout={timeout}s)")

            wait = WebDriverWait(self.driver, timeout)
            element = wait.until(
                EC.presence_of_element_located((by, value))
            )

            return Result.success(element, f"Element found: {by}={value}")

        except TimeoutException as e:
            logger.warning(f"Element not found within {timeout}s: {by}={value}")
            return Result.failure(
                f"Element not found: {by}={value} (timeout={timeout}s)",
                e
            )

        except Exception as e:
            logger.error(f"Error finding element: {e}")
            return Result.failure(f"Error finding element: {by}={value}", e)

    def find_elements(
        self,
        by: By,
        value: str,
        timeout: Optional[int] = None
    ) -> Result[List[WebElement]]:
        """Find multiple elements with explicit wait."""
        if timeout is None:
            timeout = self.config.timeout

        try:
            logger.debug(f"Finding elements: {by}={value} (timeout={timeout}s)")

            wait = WebDriverWait(self.driver, timeout)
            elements = wait.until(
                EC.presence_of_all_elements_located((by, value))
            )

            return Result.success(
                elements,
                f"Found {len(elements)} elements: {by}={value}"
            )

        except TimeoutException as e:
            logger.warning(f"Elements not found within {timeout}s: {by}={value}")
            return Result.failure(
                f"Elements not found: {by}={value} (timeout={timeout}s)",
                e
            )

        except Exception as e:
            logger.error(f"Error finding elements: {e}")
            return Result.failure(f"Error finding elements: {by}={value}", e)

    def click(
        self,
        by: By,
        value: str,
        timeout: Optional[int] = None
    ) -> Result[None]:
        """Click an element."""
        if timeout is None:
            timeout = self.config.timeout

        try:
            logger.debug(f"Clicking element: {by}={value}")

            # Find element
            element_result = self.find_element(by, value, timeout)
            if element_result.is_failure:
                return Result.failure(
                    f"Cannot click: element not found",
                    element_result.error
                )

            # Wait for element to be clickable
            wait = WebDriverWait(self.driver, timeout)
            element = wait.until(
                EC.element_to_be_clickable((by, value))
            )

            # Click
            element.click()

            return Result.success(None, f"Clicked: {by}={value}")

        except ElementNotInteractableException as e:
            logger.error(f"Element not clickable: {by}={value}")
            return Result.failure(f"Element not clickable: {by}={value}", e)

        except Exception as e:
            logger.error(f"Click failed: {e}")
            return Result.failure(f"Click failed: {by}={value}", e)

    def click_javascript(
        self,
        by: By,
        value: str,
        timeout: Optional[int] = None
    ) -> Result[None]:
        """
        Click an element using JavaScript.

        This method is useful when normal click fails due to element
        being obscured by other elements or overlays.

        Args:
            by: By locator strategy
            value: Locator value
            timeout: Optional timeout in seconds

        Returns:
            Result indicating success or failure
        """
        if timeout is None:
            timeout = self.config.timeout

        try:
            logger.debug(f"Clicking element with JavaScript: {by}={value}")

            # Find element
            element_result = self.find_element(by, value, timeout)
            if element_result.is_failure:
                return Result.failure(
                    f"Cannot click: element not found",
                    element_result.error
                )

            element = element_result.value

            # Log element details for debugging
            is_displayed = element.is_displayed()
            is_enabled = element.is_enabled()
            location = element.location
            size = element.size
            logger.info(f"Element details - displayed: {is_displayed}, enabled: {is_enabled}, location: {location}, size: {size}")

            # Scroll element into view
            logger.info("Scrolling element into view...")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)

            # Wait a moment for scroll to complete
            import time
            time.sleep(0.5)

            # Click using JavaScript
            logger.info("Executing JavaScript click...")
            self.driver.execute_script("arguments[0].click();", element)

            logger.info(f"Successfully clicked with JavaScript: {by}={value}")
            return Result.success(None, f"Clicked (JS): {by}={value}")

        except Exception as e:
            logger.error(f"JavaScript click failed: {e}")
            return Result.failure(f"JavaScript click failed: {by}={value}", e)

    def input_text(
        self,
        by: By,
        value: str,
        text: str,
        timeout: Optional[int] = None
    ) -> Result[None]:
        """Input text into an element."""
        if timeout is None:
            timeout = self.config.timeout

        try:
            logger.debug(f"Inputting text into: {by}={value}")

            # Find element
            element_result = self.find_element(by, value, timeout)
            if element_result.is_failure:
                return Result.failure(
                    f"Cannot input text: element not found",
                    element_result.error
                )

            element = element_result.value

            # Clear existing text
            element.clear()

            # Input text
            element.send_keys(text)

            return Result.success(None, f"Text input: {by}={value}")

        except ElementNotInteractableException as e:
            logger.error(f"Element not interactable: {by}={value}")
            return Result.failure(f"Element not interactable: {by}={value}", e)

        except Exception as e:
            logger.error(f"Text input failed: {e}")
            return Result.failure(f"Text input failed: {by}={value}", e)

    def set_value_javascript(
        self,
        by: By,
        value: str,
        text: str,
        timeout: Optional[int] = None
    ) -> Result[None]:
        """
        Set value of an input element using JavaScript.

        This method is useful for readonly inputs like React DatePicker
        where normal input methods don't work.

        Args:
            by: By locator strategy
            value: Locator value
            text: Text to set
            timeout: Optional timeout in seconds

        Returns:
            Result indicating success or failure
        """
        if timeout is None:
            timeout = self.config.timeout

        try:
            logger.debug(f"Setting value with JavaScript: {by}={value}")

            # Find element
            element_result = self.find_element(by, value, timeout)
            if element_result.is_failure:
                return Result.failure(
                    f"Cannot set value: element not found",
                    element_result.error
                )

            element = element_result.value

            # Set value using React-friendly JavaScript sequence
            # Use the native value setter so React's internal value tracker is updated
            script = """
                const element = arguments[0];
                const value = arguments[1];
                const lastValue = element.value;

                const prototype = Object.getPrototypeOf(element);
                const descriptor = Object.getOwnPropertyDescriptor(element, 'value')
                    || Object.getOwnPropertyDescriptor(prototype, 'value');
                if (!descriptor || typeof descriptor.set !== 'function') {
                    throw new Error('Unable to locate native value setter');
                }

                descriptor.set.call(element, value);

                const tracker = element._valueTracker;
                if (tracker) {
                    tracker.setValue(lastValue);
                }

                element.dispatchEvent(new Event('input', { bubbles: true }));
                element.dispatchEvent(new Event('change', { bubbles: true }));
            """

            self.driver.execute_script(script, element, text)

            logger.debug(f"Successfully set value with JavaScript: {by}={value}")
            return Result.success(None, f"Set value (JS): {by}={value}")

        except Exception as e:
            logger.error(f"Set value (JS) failed: {e}")
            return Result.failure(f"Set value (JS) failed: {by}={value}", e)

    def select_dropdown(
        self,
        by: By,
        value: str,
        option_value: str,
        timeout: Optional[int] = None
    ) -> Result[None]:
        """
        Select an option from a dropdown (SELECT element) by value.

        Args:
            by: Locator strategy (e.g., By.CSS_SELECTOR, By.ID)
            value: Locator value (e.g., selector, id)
            option_value: Value attribute of the option to select
            timeout: Wait timeout in seconds

        Returns:
            Result[None] indicating success or failure

        Examples:
            >>> # Select option with value="1"
            >>> result = browser.select_dropdown(By.ID, "category", "1")
            >>> if result.is_success:
            ...     print("Option selected")
        """
        if timeout is None:
            timeout = self.config.timeout

        try:
            logger.debug(f"Selecting dropdown option: {by}={value}, option_value={option_value}")

            # Find SELECT element
            element_result = self.find_element(by, value, timeout)
            if element_result.is_failure:
                return Result.failure(
                    f"Cannot select dropdown: element not found",
                    element_result.error
                )

            element = element_result.value

            # Create Select object
            select = Select(element)

            # Select by value
            select.select_by_value(option_value)

            return Result.success(
                None,
                f"Selected dropdown option: {by}={value}, value={option_value}"
            )

        except NoSuchElementException as e:
            logger.error(f"Dropdown option not found: value={option_value}")
            return Result.failure(
                f"Dropdown option not found: {by}={value}, value={option_value}",
                e
            )

        except ElementNotInteractableException as e:
            logger.error(f"Dropdown not interactable: {by}={value}")
            return Result.failure(f"Dropdown not interactable: {by}={value}", e)

        except Exception as e:
            logger.error(f"Dropdown selection failed: {e}")
            return Result.failure(
                f"Dropdown selection failed: {by}={value}, value={option_value}",
                e
            )

    def get_page_source(self) -> Result[str]:
        """Get current page HTML source."""
        try:
            source = self.driver.page_source
            return Result.success(source, "Page source retrieved")

        except Exception as e:
            logger.error(f"Failed to get page source: {e}")
            return Result.failure("Failed to get page source", e)

    def screenshot(self, filepath: str) -> Result[bool]:
        """Take screenshot and save to file."""
        try:
            # Ensure parent directory exists
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)

            # Take screenshot
            success = self.driver.save_screenshot(str(path))

            if success:
                logger.debug(f"Screenshot saved: {filepath}")
                return Result.success(True, f"Screenshot saved: {filepath}")
            else:
                return Result.failure("Screenshot save failed")

        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return Result.failure(f"Screenshot failed: {filepath}", e)

    def wait_for_page_load(self, timeout: Optional[int] = None) -> Result[None]:
        """Wait for page to fully load."""
        if timeout is None:
            timeout = self.config.timeout

        try:
            wait = WebDriverWait(self.driver, timeout)
            wait.until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )

            return Result.success(None, "Page loaded")

        except TimeoutException as e:
            logger.warning(f"Page load timeout after {timeout}s")
            return Result.failure(f"Page load timeout ({timeout}s)", e)

        except Exception as e:
            logger.error(f"Page load wait failed: {e}")
            return Result.failure("Page load wait failed", e)

    def close(self):
        """Close browser and clean up resources."""
        try:
            if self.driver:
                self.driver.quit()
                logger.info("Browser closed")

        except Exception as e:
            logger.warning(f"Error closing browser: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False
