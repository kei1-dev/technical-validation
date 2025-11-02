"""
Terakoya automation client.

This module provides the main TerakoyaClient class for automating
invoice submission on the Terakoya platform.
"""

import logging
import os
import time
import platform
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import StaleElementReferenceException

from ..browser import Browser
from .selectors import TerakoyaSelectors
from .session import SessionManager
from ...models.result import Result
from ...models.lesson import LessonData
from ...models.invoice import InvoiceResult, InvoiceSummary
from ...validation.lesson_validator import LessonValidator
from ...validation.invoice_validator import InvoiceItemValidator
from ...resilience.circuit_breaker import CircuitBreaker
from ...utils.config import SecureString
from ...utils.ai_extractor import AIExtractor


logger = logging.getLogger(__name__)


class FieldImportance(Enum):
    """Importance level for form fields."""

    REQUIRED = "required"
    OPTIONAL = "optional"


class TerakoyaClient:
    """
    Client for automating Terakoya invoice submissions.

    This class provides high-level methods for:
    - Authentication
    - Lesson data retrieval
    - Invoice submission
    - Duplicate detection
    - Error handling and retry

    Examples:
        >>> from src.automation.browser import Browser
        >>> from src.automation.terakoya.client import TerakoyaClient
        >>> from src.utils.config import SecureString
        >>>
        >>> browser = Browser(headless=True)
        >>> client = TerakoyaClient(browser, base_url="https://terakoya.sejuku.net")
        >>>
        >>> # Login
        >>> result = client.login("user@example.com", SecureString("password"))
        >>> if result.is_success:
        ...     # Get lessons
        ...     lessons_result = client.get_lessons_for_month(2025, 10)
        ...     # Submit invoice
        ...     invoice_result = client.submit_invoice_for_lessons(lessons_result.value)
    """

    def __init__(
        self,
        browser: Browser,
        base_url: str = "https://terakoya.sejuku.net",
        screenshot_dir: Optional[Path] = None
    ):
        """
        Initialize TerakoyaClient.

        Args:
            browser: Browser instance
            base_url: Base URL of Terakoya site
            screenshot_dir: Directory for saving screenshots (optional)
        """
        self.browser = browser
        self.base_url = base_url.rstrip('/')
        self.screenshot_dir = screenshot_dir or Path("output/terakoya_screenshots")
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

        self.debug_dir = Path("output/terakoya_debug")
        self.debug_dir.mkdir(parents=True, exist_ok=True)

        self.selectors = TerakoyaSelectors()
        self.session = SessionManager(browser)

        # Validators
        self.lesson_validator = LessonValidator()
        self.invoice_validator = InvoiceItemValidator()

        # Circuit breaker for resilience
        from datetime import timedelta
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            timeout=timedelta(seconds=60),
            expected_exception=Exception
        )

        # AI Extraction
        self.use_ai_extraction = os.getenv("TERAKOYA_USE_AI_EXTRACTION", "false").lower() == "true"
        self.ai_batch_size = int(os.getenv("TERAKOYA_AI_BATCH_SIZE", "10"))
        self.ai_extractor = None

        if self.use_ai_extraction:
            try:
                self.ai_extractor = AIExtractor()
                logger.info("AI extraction enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize AI extractor: {e}")
                logger.warning("Falling back to regex-based extraction")
                self.use_ai_extraction = False

        logger.info(f"TerakoyaClient initialized with base_url: {base_url}")

    def _extract_text_safe(
        self,
        element: "WebElement",
        selector: str,
        default: str = ""
    ) -> str:
        """
        Safely extract text from an element using a selector.

        Args:
            element: Parent WebElement
            selector: CSS selector
            default: Default value if extraction fails

        Returns:
            Extracted text or default value
        """
        try:
            sub_element = element.find_element(By.CSS_SELECTOR, selector)
            return sub_element.text.strip()
        except Exception as e:
            logger.debug(f"Failed to extract text with selector '{selector}': {e}")
            return default

    def _parse_date(self, date_text: str) -> str:
        """
        Parse date text to YYYY-MM-DD format.

        Handles various Japanese date formats:
        - "2025年10月15日" -> "2025-10-15"
        - "2025/10/15" -> "2025-10-15"
        - "2025-10-15" -> "2025-10-15" (already correct)

        Args:
            date_text: Date string in various formats

        Returns:
            Date in YYYY-MM-DD format

        Raises:
            ValueError: If date cannot be parsed
        """
        import re

        date_text = date_text.strip()

        # Already in correct format
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_text):
            return date_text

        # Japanese format: 2025年10月15日
        match = re.match(r'(\d{4})年(\d{1,2})月(\d{1,2})日', date_text)
        if match:
            year, month, day = match.groups()
            return f"{year}-{int(month):02d}-{int(day):02d}"

        # Slash format: 2025/10/15
        match = re.match(r'(\d{4})/(\d{1,2})/(\d{1,2})', date_text)
        if match:
            year, month, day = match.groups()
            return f"{year}-{int(month):02d}-{int(day):02d}"

        # Fallback: try to extract numbers
        numbers = re.findall(r'\d+', date_text)
        if len(numbers) >= 3:
            year, month, day = numbers[:3]
            return f"{year}-{int(month):02d}-{int(day):02d}"

        raise ValueError(f"Cannot parse date: {date_text}")

    def _parse_duration(self, duration_text: str) -> int:
        """
        Parse duration text to minutes.

        Handles:
        - "60分" -> 60
        - "60" -> 60
        - "1時間" -> 60
        - "1.5時間" -> 90

        Args:
            duration_text: Duration string

        Returns:
            Duration in minutes

        Raises:
            ValueError: If duration cannot be parsed
        """
        import re

        duration_text = duration_text.strip()

        # Minutes format: "60分"
        match = re.search(r'(\d+)分', duration_text)
        if match:
            return int(match.group(1))

        # Hours format: "1時間" or "1.5時間"
        match = re.search(r'([\d.]+)時間', duration_text)
        if match:
            hours = float(match.group(1))
            return int(hours * 60)

        # Plain number
        match = re.search(r'\d+', duration_text)
        if match:
            return int(match.group(0))

        raise ValueError(f"Cannot parse duration: {duration_text}")

    def _extract_student_id(self, row: "WebElement") -> str:
        """
        Extract student ID from lesson row.

        Tries multiple strategies:
        1. data-student-id attribute
        2. Dedicated student ID cell
        3. Extract from link href
        4. Generate from row index

        Args:
            row: Lesson row WebElement

        Returns:
            Student ID string
        """
        # Strategy 1: data attribute
        student_id = row.get_attribute("data-student-id")
        if student_id:
            return student_id

        # Strategy 2: dedicated cell
        try:
            id_elem = row.find_element(
                By.CSS_SELECTOR,
                self.selectors.lesson.lesson_id
            )
            if id_elem.text:
                return id_elem.text.strip()
        except Exception:
            pass

        # Strategy 3: extract from student link
        try:
            student_elem = row.find_element(
                By.CSS_SELECTOR,
                self.selectors.lesson.lesson_student
            )
            href = student_elem.get_attribute("href")
            if href and "/student/" in href:
                # Extract ID from URL like /student/12345
                import re
                match = re.search(r'/student/(\d+)', href)
                if match:
                    return f"student_{match.group(1)}"
        except Exception:
            pass

        # Strategy 4: fallback to row ID
        row_id = row.get_attribute("id") or row.get_attribute("data-id")
        if row_id:
            return f"student_{row_id}"

        # Last resort: generate from row position
        return f"student_unknown_{id(row)}"

    def _extract_lesson_from_row(self, row: "WebElement", row_index: int) -> Optional[LessonData]:
        """
        Extract lesson data from a table row.

        Args:
            row: Selenium WebElement representing a lesson row
            row_index: Row index for fallback ID generation

        Returns:
            LessonData or None if extraction fails
        """
        try:
            # Extract lesson ID
            lesson_id = (
                row.get_attribute("data-lesson-id") or
                row.get_attribute("id") or
                f"lesson_{row_index}"
            )

            # Extract date
            date_text = self._extract_text_safe(
                row,
                self.selectors.lesson.lesson_date,
                default=""
            )
            if not date_text:
                logger.warning(f"Row {row_index}: No date found")
                return None

            try:
                parsed_date = self._parse_date(date_text)
            except ValueError as e:
                logger.warning(f"Row {row_index}: {e}")
                return None

            # Extract student name
            student_name = self._extract_text_safe(
                row,
                self.selectors.lesson.lesson_student,
                default=""
            )
            if not student_name:
                logger.warning(f"Row {row_index}: No student name found")
                return None

            # Extract student ID
            student_id = self._extract_student_id(row)

            # Extract category
            category = self._extract_text_safe(
                row,
                self.selectors.lesson.lesson_category,
                default="専属レッスン"
            )

            # Extract duration
            duration_text = self._extract_text_safe(
                row,
                self.selectors.lesson.lesson_duration,
                default="60"
            )
            try:
                duration = self._parse_duration(duration_text)
            except ValueError as e:
                logger.warning(f"Row {row_index}: {e}, using default 60")
                duration = 60

            # Extract status
            status_text = self._extract_text_safe(
                row,
                self.selectors.lesson.lesson_status,
                default="completed"
            )
            # Normalize status
            status_lower = status_text.lower()
            if "完了" in status_text or "completed" in status_lower:
                status = "completed"
            elif "pending" in status_lower or "保留" in status_text:
                status = "pending"
            elif "cancelled" in status_lower or "キャンセル" in status_text:
                status = "cancelled"
            else:
                status = "completed"  # Default

            # Create lesson data
            lesson_data: LessonData = {
                "id": lesson_id,
                "date": parsed_date,
                "student_id": student_id,
                "student_name": student_name,
                "status": status,
                "duration": duration,
                "category": category
            }

            return lesson_data

        except Exception as e:
            logger.error(f"Failed to extract lesson from row {row_index}: {e}")
            return None

    def _extract_lesson_from_card(self, card: "WebElement", card_index: int, target_year: int) -> Optional[LessonData]:
        """
        Extract lesson data from a card-based layout.

        Args:
            card: Selenium WebElement representing a lesson card
            card_index: Card index for fallback ID generation
            target_year: Year to use for date parsing (e.g., 2025)

        Returns:
            LessonData or None if extraction fails
        """
        try:
            import re
            from datetime import datetime

            # Get all text from the card
            card_text = card.text
            if not card_text:
                logger.debug(f"Card {card_index}: No text content")
                return None

            # Extract date in format: 08/05(木)
            date_match = re.search(r'(\d{2})/(\d{2})\([日月火水木金土]\)', card_text)
            if not date_match:
                logger.debug(f"Card {card_index}: No date pattern found in text")
                return None

            month = int(date_match.group(1))
            day = int(date_match.group(2))
            parsed_date = f"{target_year}-{month:02d}-{day:02d}"

            # Extract time in format: 20:30~21:30 or 10:00-11:00
            time_match = re.search(r'(\d{1,2}):(\d{2})[~\-](\d{1,2}):(\d{2})', card_text)
            duration = 60  # Default
            if time_match:
                start_hour = int(time_match.group(1))
                start_min = int(time_match.group(2))
                end_hour = int(time_match.group(3))
                end_min = int(time_match.group(4))

                # Calculate duration in minutes
                start_minutes = start_hour * 60 + start_min
                end_minutes = end_hour * 60 + end_min
                duration = end_minutes - start_minutes
                if duration <= 0:
                    duration = 60  # Fallback

            # Card format: MM/DD(曜)HH:MM~HH:MM【タイトル】テーマ生徒名マンツー編集...
            # Example: 11/01(土)20:00~21:00【第2回】Github林晃司マンツー編集受講履歴登録

            # Remove lesson title in brackets 【】 and the theme word after it
            # Pattern: 【...】 followed by non-Japanese characters (like "Github", "Django", "AWS")
            # Keep Japanese characters (student names)
            text_without_brackets = re.sub(r'【[^】]+】[A-Za-z0-9\s]*', '', card_text)

            # Extract student name before lesson type keywords
            # Pattern: Find text before マンツー/専属レッスン/初回/エキスパート
            student_pattern = r'(\d{2}:\d{2})([^\s]+?)(マンツー|専属レッスン|初回レッスン|初回|エキスパートコース|専属)'
            student_match = re.search(student_pattern, text_without_brackets)

            student_name = None
            category = "専属レッスン"  # Default

            if student_match:
                # Group 2 is the text between time and lesson type (student name)
                potential_name = student_match.group(2)
                lesson_type = student_match.group(3)

                # Clean up the student name (remove any non-name characters)
                # Student names are typically 2-4 kanji/hiragana/katakana characters
                name_match = re.search(r'([\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]{2,4})', potential_name)
                if name_match:
                    student_name = name_match.group(1)

                    # Determine category from lesson type
                    if "エキスパート" in lesson_type:
                        category = "エキスパートコース"
                    elif "初回" in lesson_type:
                        category = "初回レッスン"
                    elif "マンツー" in lesson_type:
                        category = "専属レッスン"

            if not student_name:
                logger.debug(f"Card {card_index}: Could not extract student name from: {card_text[:100]}")
                return None

            # Generate lesson ID
            lesson_id = (
                card.get_attribute("data-lesson-id") or
                card.get_attribute("id") or
                f"lesson_{target_year}{month:02d}{day:02d}_{card_index}"
            )

            # Generate student ID from name (simplified)
            student_id = f"student_{hash(student_name) % 100000:05d}"

            # Status: assume completed for past lessons
            status = "completed"

            # Create lesson data
            lesson_data: LessonData = {
                "id": lesson_id,
                "date": parsed_date,
                "student_id": student_id,
                "student_name": student_name,
                "status": status,
                "duration": duration,
                "category": category
            }

            return lesson_data

        except Exception as e:
            logger.error(f"Failed to extract lesson from card {card_index}: {e}", exc_info=True)
            return None

    def _extract_invoice_from_row(self, row: "WebElement", row_index: int) -> Optional[Dict[str, Any]]:
        """
        Extract invoice item data from a table row.

        Args:
            row: Selenium WebElement representing an invoice row
            row_index: Row index for logging

        Returns:
            Dictionary with invoice data or None if extraction fails
        """
        try:
            # Extract date
            date_text = self._extract_text_safe(
                row,
                self.selectors.invoice.item_date,
                default=""
            )
            if not date_text:
                return None

            try:
                parsed_date = self._parse_date(date_text)
            except ValueError as e:
                logger.warning(f"Invoice row {row_index}: {e}")
                return None

            # Extract student info
            student_id = self._extract_text_safe(
                row,
                self.selectors.invoice.item_student_id,
                default=""
            )
            student_name = self._extract_text_safe(
                row,
                self.selectors.invoice.item_student,
                default=""
            )

            # Extract category
            category = self._extract_text_safe(
                row,
                self.selectors.invoice.item_category,
                default=""
            )

            # Extract duration
            duration_text = self._extract_text_safe(
                row,
                self.selectors.invoice.item_duration,
                default="60"
            )
            try:
                duration = self._parse_duration(duration_text)
            except ValueError:
                duration = 60

            # Extract unit price
            unit_price_text = self._extract_text_safe(
                row,
                self.selectors.invoice.item_unit_price,
                default="2300"
            )
            # Extract numbers from text like "¥2,300" or "2300円"
            import re
            numbers = re.sub(r'[^\d]', '', unit_price_text)
            unit_price = int(numbers) if numbers else 2300

            invoice_item = {
                "date": parsed_date,
                "student_id": student_id,
                "student_name": student_name,
                "category": category,
                "duration": duration,
                "unit_price": unit_price,
            }

            return invoice_item

        except Exception as e:
            logger.error(f"Failed to extract invoice from row {row_index}: {e}")
            return None

    def _wait_for_navigation(self, timeout: int = 10) -> Result[None]:
        """
        Wait for page navigation to complete.

        Args:
            timeout: Maximum wait time in seconds

        Returns:
            Result[None] indicating success
        """
        return self.browser.wait_for_page_load(timeout=timeout)

    def _wait_for_lesson_options_loaded(self, timeout: int = 10) -> Result[None]:
        """
        Wait for lesson SELECT options to load from API after date selection.

        Uses explicit wait to check for options beyond the default placeholder.

        Args:
            timeout: Maximum wait time in seconds (default: 10)

        Returns:
            Result[None]: Success if options loaded, Failure if timeout

        Examples:
            >>> wait_result = self._wait_for_lesson_options_loaded(timeout=10)
            >>> if wait_result.is_success:
            ...     # Options are loaded, can proceed to selection
        """
        from selenium.webdriver.support.ui import WebDriverWait, Select
        from selenium.common.exceptions import TimeoutException

        try:
            logger.info("Waiting for lesson options to load from API...")

            # Find lesson select element
            lesson_select_result = self.browser.find_element(
                By.CSS_SELECTOR,
                self.selectors.invoice.modal_lesson_select,
                timeout=timeout
            )
            if lesson_select_result.is_failure:
                lesson_select_result = self.browser.find_element(
                    By.XPATH,
                    self.selectors.invoice.modal_lesson_select_xpath,
                    timeout=timeout
                )
            if lesson_select_result.is_failure:
                return Result.failure(
                    "Lesson select element not found",
                    lesson_select_result.error
                )

            select_element = lesson_select_result.value

            # Wait until options are loaded (more than just default option)
            wait = WebDriverWait(self.browser.driver, timeout)
            wait.until(
                lambda driver: len(Select(select_element).options) > 1,
                message="Lesson options not loaded within timeout"
            )

            options_count = len(Select(select_element).options)
            logger.info(f"Lesson options loaded successfully: {options_count} options")
            return Result.success(None, f"Loaded {options_count} lesson options")

        except TimeoutException as e:
            logger.warning(f"Lesson options did not load within {timeout}s: {e}")
            return Result.failure(f"Lesson options not loaded within {timeout}s", e)
        except Exception as e:
            logger.error(f"Failed to wait for lesson options: {e}", exc_info=True)
            return Result.failure(f"Error waiting for lesson options: {e}", e)

    def _wait_for_select_options(
        self,
        by: By,
        locator: str,
        description: str,
        timeout: int = 10,
        min_meaningful_options: int = 2
    ) -> Result[None]:
        """Generic helper to wait until a SELECT element has enough options."""
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.common.exceptions import TimeoutException

        try:
            logger.debug(
                f"Waiting for {description} options (min {min_meaningful_options}) to be available..."
            )

            def options_loaded(driver) -> bool:
                try:
                    element = driver.find_element(by, locator)
                    options = element.find_elements(By.TAG_NAME, "option")
                    meaningful_options = [
                        opt for opt in options
                        if (opt.get_attribute("value") or opt.text or "").strip()
                    ]
                    logger.debug(
                        f"{description} options check: total={len(options)}, meaningful={len(meaningful_options)}"
                    )
                    return len(meaningful_options) >= min_meaningful_options
                except Exception:
                    return False

            wait = WebDriverWait(self.browser.driver, timeout)
            wait.until(
                options_loaded,
                message=f"{description} options not loaded within {timeout}s"
            )

            logger.debug(f"{description} options loaded successfully")
            return Result.success(None, f"{description} options ready")

        except TimeoutException as e:
            logger.warning(f"{description} options did not load within {timeout}s: {e}")
            return Result.failure(f"{description} options not loaded within {timeout}s", e)
        except Exception as e:
            logger.error(f"Error waiting for {description} options: {e}", exc_info=True)
            return Result.failure(
                f"Error waiting for {description} options: {e}",
                e
            )

    @staticmethod
    def _normalize_student_label(label: Optional[str]) -> str:
        """Normalize student names for comparison (remove whitespace)."""
        if label is None:
            return ""
        return label.replace(" ", "").replace("\u3000", "").strip()

    def _select_student_for_lesson(
        self,
        lesson: LessonData,
        timeout: int = 10
    ) -> Result[bool]:
        """Select the student in the invoice modal if the field is present."""
        student_selector = self.selectors.invoice.modal_student_select

        student_field_result = self.browser.find_element(
            By.CSS_SELECTOR,
            student_selector,
            timeout=3
        )

        if student_field_result.is_failure:
            logger.debug(
                "Student select element not present in modal; attempting custom dropdown handler"
            )
            return self._select_student_custom_dropdown(lesson, timeout)

        wait_result = self._wait_for_select_options(
            By.CSS_SELECTOR,
            student_selector,
            description="Student",
            timeout=timeout,
            min_meaningful_options=2
        )

        if wait_result.is_failure:
            logger.debug(
                "Standard student SELECT options did not load; attempting custom dropdown handler"
            )
            fallback_result = self._select_student_custom_dropdown(lesson, timeout)
            if fallback_result.is_success:
                return fallback_result
            return Result.failure(
                (wait_result.message or "Student options not loaded") +
                f"; fallback: {fallback_result.message}",
                fallback_result.error or wait_result.error
            )

        # Re-fetch select element to avoid stale references
        student_field_result = self.browser.find_element(
            By.CSS_SELECTOR,
            student_selector,
            timeout=3
        )

        if student_field_result.is_failure:
            return Result.failure(
                "Student select element disappeared after wait",
                student_field_result.error
            )

        select_element = student_field_result.value

        try:
            from selenium.webdriver.support.ui import Select

            select = Select(select_element)
            options = select.options
        except Exception as e:
            logger.debug(f"Student field is not a standard SELECT element: {e}")
            return self._select_student_custom_dropdown(lesson, timeout)

        if len(options) <= 1:
            fallback_result = self._select_student_custom_dropdown(lesson, timeout)
            if fallback_result.is_success:
                return fallback_result
            return Result.failure(
                "Student select only has default option after waiting"
                + f"; fallback: {fallback_result.message}",
                fallback_result.error
            )

        normalized_target = self._normalize_student_label(lesson.get("student_name"))
        candidate_value: Optional[str] = None
        candidate_visible_text: Optional[str] = None
        fallback_value: Optional[str] = None
        fallback_visible: Optional[str] = None

        for option in options:
            value = (option.get_attribute("value") or "").strip()
            text = (option.text or "").strip()

            if not value and not text:
                continue

            normalized_text = self._normalize_student_label(text)

            if value and value == lesson.get("student_id"):
                candidate_value = value
                break

            if normalized_target and normalized_text == normalized_target:
                if value:
                    candidate_value = value
                else:
                    candidate_visible_text = text
                break

            if fallback_value is None and value:
                fallback_value = value
                fallback_visible = text or value
            elif fallback_visible is None and text:
                fallback_visible = text

        try:
            selected_label: str

            if candidate_value:
                select.select_by_value(candidate_value)
                selected_label = candidate_value
            elif candidate_visible_text:
                select.select_by_visible_text(candidate_visible_text)
                selected_label = candidate_visible_text
            elif fallback_value:
                logger.warning(
                    f"Student '{lesson['student_name']}' not matched; using fallback option '{fallback_visible}'"
                )
                select.select_by_value(fallback_value)
                selected_label = fallback_visible or fallback_value
            else:
                return Result.failure("No suitable student option available for selection")

            try:
                self.browser.driver.execute_script(
                    "arguments[0].dispatchEvent(new Event('change', { bubbles: true }));",
                    select_element
                )
            except Exception as event_error:
                logger.debug(
                    f"Failed to dispatch change event for student select: {event_error}"
                )

            return Result.success(True, f"Student option selected: {selected_label}")

        except Exception as e:
            return Result.failure(f"Failed to select student option: {e}", e)

    def _select_student_custom_dropdown(
        self,
        lesson: LessonData,
        timeout: int = 10
    ) -> Result[bool]:
        """
        Handle custom React-style dropdowns for student selection.
        """
        dropdown_container_result = self.browser.find_element(
            By.CSS_SELECTOR,
            self.selectors.invoice.modal_student_dropdown,
            timeout=3
        )

        if dropdown_container_result.is_failure:
            dropdown_container_result = self.browser.find_element(
                By.XPATH,
                self.selectors.invoice.modal_student_dropdown_xpath,
                timeout=3
            )

        if dropdown_container_result.is_failure:
            logger.debug("Student dropdown container not detected; skipping selection")
            self._save_modal_html_snapshot("student_dropdown_missing")
            return Result.success(False, "Student dropdown container not present")

        dropdown_container = dropdown_container_result.value

        try:
            self.browser.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});",
                dropdown_container
            )
        except Exception as scroll_error:
            logger.debug(f"Failed to scroll student dropdown into view: {scroll_error}")

        try:
            display_element = dropdown_container.find_element(
                By.CSS_SELECTOR,
                self.selectors.invoice.modal_student_dropdown_display
            )
        except Exception:
            try:
                display_element = dropdown_container.find_element(
                    By.XPATH,
                    ".//div[contains(@class,'sc-eVrRMb')]"
                )
            except Exception as e:
                self._save_modal_html_snapshot("student_dropdown_display_missing")
                return Result.failure("Student dropdown display element not found", e)

        try:
            display_element.click()
        except Exception as click_error:
            try:
                self.browser.driver.execute_script(
                    "arguments[0].click();",
                    display_element
                )
            except Exception as js_click_error:
                message = (
                    f"Failed to open student dropdown: {click_error}; "
                    f"JS click error: {js_click_error}"
                )
                self._save_modal_html_snapshot("student_dropdown_click_failed")
                return Result.failure(message, js_click_error)

        time.sleep(0.2)

        try:
            search_input = dropdown_container.find_element(
                By.CSS_SELECTOR,
                self.selectors.invoice.modal_student_dropdown_search_input
            )
        except Exception:
            try:
                search_input = dropdown_container.find_element(
                    By.XPATH,
                    ".//input[@placeholder='検索']"
                )
            except Exception as e:
                self._save_modal_html_snapshot("student_dropdown_input_missing")
                return Result.failure("Student dropdown search input not found", e)

        try:
            search_input.clear()
        except Exception:
            pass

        search_query = lesson.get("student_name", "") or lesson.get("student_id", "")
        if not search_query:
            logger.debug("Lesson data missing student name/id; cannot search dropdown")
            self._save_modal_html_snapshot("student_dropdown_no_query")
            return Result.failure("Lesson missing student name for dropdown search")

        from selenium.webdriver.common.keys import Keys

        search_input.send_keys(search_query)
        time.sleep(0.2)
        search_input.send_keys(Keys.ENTER)

        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.common.exceptions import TimeoutException

        driver = self.browser.driver

        def _options_ready() -> bool:
            try:
                options = dropdown_container.find_elements(
                    By.CSS_SELECTOR,
                    self.selectors.invoice.modal_student_dropdown_options
                )
                for option in options:
                    try:
                        text = option.text or option.get_attribute("innerText") or ""
                        if text.strip():
                            return True
                    except StaleElementReferenceException:
                        return False
                return False
            except StaleElementReferenceException:
                return False

        try:
            WebDriverWait(driver, timeout).until(lambda _: _options_ready())
        except TimeoutException as e:
            self._save_modal_html_snapshot("student_dropdown_no_options")
            return Result.failure("Student dropdown options not available", e)

        try:
            options = dropdown_container.find_elements(
                By.CSS_SELECTOR,
                self.selectors.invoice.modal_student_dropdown_options
            )
        except StaleElementReferenceException:
            dropdown_container_result = self.browser.find_element(
                By.CSS_SELECTOR,
                self.selectors.invoice.modal_student_dropdown,
                timeout=2
            )
            if dropdown_container_result.is_failure:
                dropdown_container_result = self.browser.find_element(
                    By.XPATH,
                    self.selectors.invoice.modal_student_dropdown_xpath,
                    timeout=2
                )
            if dropdown_container_result.is_failure:
                self._save_modal_html_snapshot("student_dropdown_container_stale")
                return Result.failure("Student dropdown container became stale")
            dropdown_container = dropdown_container_result.value
            options = dropdown_container.find_elements(
                By.CSS_SELECTOR,
                self.selectors.invoice.modal_student_dropdown_options
            )

        if not options:
            self._save_modal_html_snapshot("student_dropdown_no_options")
            return Result.failure("Student dropdown has no selectable options")

        normalized_target = self._normalize_student_label(lesson.get("student_name"))
        candidate_option = None
        fallback_option = None

        for option in options:
            option_text = (option.text or option.get_attribute("innerText") or "").strip()
            normalized_text = self._normalize_student_label(option_text)

            if normalized_target and normalized_text == normalized_target:
                candidate_option = option
                break

            if normalized_target and normalized_target in normalized_text:
                candidate_option = option
                break

            if fallback_option is None:
                fallback_option = option

        target_option = candidate_option or fallback_option

        if target_option is None:
            self._save_modal_html_snapshot("student_dropdown_no_match")
            return Result.failure("No matching student option found in dropdown")

        try:
            target_option.click()
        except Exception as click_error:
            try:
                self.browser.driver.execute_script(
                    "arguments[0].click();",
                    target_option
                )
            except Exception as js_click_error:
                message = (
                    f"Failed to select student option via click: {click_error}; "
                    f"JS click error: {js_click_error}"
                )
                self._save_modal_html_snapshot("student_dropdown_click_failed")
                return Result.failure(message, js_click_error)

        try:
            search_input.send_keys(Keys.TAB)
        except Exception:
            pass

        time.sleep(0.2)

        try:
            display_after = dropdown_container.find_element(
                By.CSS_SELECTOR,
                self.selectors.invoice.modal_student_dropdown_display
            )
            displayed_text = self._normalize_student_label(display_after.text)
            if normalized_target and displayed_text and normalized_target != displayed_text:
                logger.debug(
                    "Student dropdown displayed text does not match target: "
                    f"target='{normalized_target}', displayed='{displayed_text}'"
                )
                self._save_modal_html_snapshot("student_dropdown_mismatch")
        except Exception as e:
            logger.debug(f"Unable to confirm student dropdown selection: {e}")

        try:
            self.browser.driver.execute_script(
                "arguments[0].dispatchEvent(new Event('change', { bubbles: true }));",
                dropdown_container
            )
        except Exception:
            pass

        return Result.success(True, "Student option selected via custom dropdown")

    def _save_modal_html_snapshot(self, tag: str) -> None:
        """Capture current page source for debugging modal state."""
        try:
            source_result = self.browser.get_page_source()
            if source_result.is_failure or not source_result.value:
                logger.debug(
                    f"Skipping modal HTML snapshot (page source unavailable): {source_result.message}"
                )
                return

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"modal_{tag}_{timestamp}.html"
            filepath = self.debug_dir / filename
            filepath.write_text(source_result.value, encoding="utf-8")
            logger.info(f"Saved modal HTML snapshot: {filepath}")

        except Exception as e:
            logger.debug(f"Failed to save modal HTML snapshot ({tag}): {e}")

    def _wait_for_modal_visible(self, timeout: int = 5) -> Result[None]:
        """
        Wait for modal dialog to appear.

        Instead of checking for the modal container (which has dynamic classes),
        we check for the presence of modal-specific form fields.

        Args:
            timeout: Maximum wait time in seconds

        Returns:
            Result[None] indicating success
        """
        # Check for date input field (only visible when modal is open)
        date_field_result = self.browser.find_element(
            By.CSS_SELECTOR,
            self.selectors.invoice.modal_date_input,
            timeout=timeout
        )

        if date_field_result.is_success:
            logger.debug("Modal detected via date input field")
            return Result.success(None, "Modal visible")

        # Fallback: check for category select (alternative modal indicator)
        category_field_result = self.browser.find_element(
            By.CSS_SELECTOR,
            self.selectors.invoice.modal_category_select,
            timeout=1
        )

        if category_field_result.is_success:
            logger.debug("Modal detected via category select field")
            return Result.success(None, "Modal visible")

        return Result.failure("Modal not visible (form fields not found)")

    def _input_field(
        self,
        selector: str,
        value: str,
        field_name: str,
        importance: FieldImportance = FieldImportance.REQUIRED,
        timeout: int = 5
    ) -> Result[None]:
        """
        Input text into a form field with importance level.

        Args:
            selector: CSS selector
            value: Value to input
            field_name: Field name for error messages
            importance: Whether field is required or optional
            timeout: Operation timeout

        Returns:
            Result indicating success or failure
        """
        result = self.browser.input_text(
            By.CSS_SELECTOR,
            selector,
            value,
            timeout=timeout
        )

        if result.is_failure:
            if importance == FieldImportance.REQUIRED:
                self._save_screenshot(f"{field_name}_input_failed")
                return Result.failure(
                    f"Failed to input required field '{field_name}': {result.message}",
                    result.error
                )
            else:
                logger.warning(
                    f"Failed to input optional field '{field_name}': {result.message}"
                )
                # Return success for optional fields
                return Result.success(None, f"Optional field '{field_name}' skipped")

        return result

    def _wait_for_modal_closed(self, timeout: int = 5) -> Result[None]:
        """
        Wait for modal dialog to close.

        Waits until modal element is no longer present or visible.

        Args:
            timeout: Maximum wait time in seconds

        Returns:
            Result[None] indicating success
        """
        # Wait a moment for modal animation to start
        import time
        time.sleep(0.3)

        # Try to find modal - it should fail (not present)
        modal_result = self.browser.find_element(
            By.CSS_SELECTOR,
            self.selectors.invoice.modal,
            timeout=2
        )

        # If modal is still found, it hasn't closed yet
        if modal_result.is_success:
            logger.warning("Modal still visible after expected close")
            # Give it more time
            time.sleep(timeout - 2)

        return Result.success(None, "Modal closed or not found")

    def _save_screenshot(self, name: str) -> Result[bool]:
        """
        Save a screenshot with timestamp.

        Args:
            name: Base name for screenshot

        Returns:
            Result[bool] indicating success
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.png"
        filepath = self.screenshot_dir / filename

        return self.browser.screenshot(str(filepath))

    def ensure_logged_in(self) -> Result[None]:
        """
        Ensure user is logged in.

        Checks session validity. If session is invalid, returns failure
        indicating login is required.

        Returns:
            Result[None] - Success if logged in, Failure if login needed

        Examples:
            >>> result = client.ensure_logged_in()
            >>> if result.is_failure:
            ...     client.login(email, password)
        """
        return self.session.require_login()

    def login(self, email: str, password: SecureString) -> Result[None]:
        """
        Log in to Terakoya.

        Args:
            email: Login email address
            password: Login password (SecureString)

        Returns:
            Result[None] indicating success or failure

        Examples:
            >>> from src.utils.config import SecureString
            >>> result = client.login("user@example.com", SecureString("pass"))
            >>> if result.is_success:
            ...     print("Login successful")
        """
        try:
            # Validate inputs
            if not email or "@" not in email:
                return Result.failure("Invalid email address")

            # Validate password (without exposing it)
            pwd_value = password.get_value()
            if not pwd_value or len(pwd_value) < 8:
                return Result.failure(
                    "Invalid password: must be at least 8 characters"
                )

            logger.info(f"Logging in with email: {email}")

            # Navigate to base URL first
            nav_result = self.browser.navigate(self.base_url)
            if nav_result.is_failure:
                return nav_result

            # Wait for page load
            wait_result = self.browser.wait_for_page_load()
            if wait_result.is_failure:
                logger.warning("Page load wait failed, continuing anyway")

            # Wait for JavaScript to render (Terakoya uses client-side rendering)
            import time
            logger.info("Waiting for JavaScript to render page...")
            time.sleep(3)  # Give JavaScript time to render

            # Click "ログイン" button to open login modal
            # The login button is a div element that requires JavaScript click
            login_button_xpath = "/html/body/div[1]/header/div/div/div[2]/div[1]"

            login_element_result = self.browser.find_element(
                By.XPATH,
                login_button_xpath,
                timeout=10
            )

            if login_element_result.is_failure:
                self._save_screenshot("login_button_not_found")
                return Result.failure("Could not find login button on homepage")

            # Use JavaScript click (regular click doesn't work on this div)
            login_element = login_element_result.value
            try:
                self.browser.driver.execute_script("arguments[0].click();", login_element)
                logger.info("Clicked login button using JavaScript")

                # Wait for login modal to appear
                time.sleep(2)
            except Exception as e:
                self._save_screenshot("login_button_click_failed")
                return Result.failure(f"Failed to click login button: {e}")

            # Find and fill email
            email_result = self.browser.input_text(
                By.CSS_SELECTOR,
                self.selectors.login.email_input,
                email,
                timeout=10
            )
            if email_result.is_failure:
                self._save_screenshot("login_email_failed")
                return Result.failure(
                    "Failed to input email",
                    email_result.error
                )

            # Find and fill password
            password_result = self.browser.input_text(
                By.CSS_SELECTOR,
                self.selectors.login.password_input,
                pwd_value,  # Use already-validated password
                timeout=10
            )
            if password_result.is_failure:
                self._save_screenshot("login_password_failed")
                return Result.failure(
                    "Failed to input password",
                    password_result.error
                )

            # Click login button (find by text since it's dynamically enabled/disabled)
            login_button_xpath = "//button[contains(text(), 'ログイン') and not(contains(text(), 'Google')) and not(contains(text(), 'Facebook'))]"

            # Wait for button to become enabled (it starts disabled)
            import time
            time.sleep(1)

            click_result = self.browser.click(
                By.XPATH,
                login_button_xpath,
                timeout=10
            )
            if click_result.is_failure:
                self._save_screenshot("login_button_failed")
                return Result.failure(
                    "Failed to click login button",
                    click_result.error
                )

            # Wait for page navigation to complete
            wait_result = self._wait_for_navigation(timeout=10)
            if wait_result.is_failure:
                logger.warning(f"Navigation wait failed: {wait_result.message}")

            # Check for error messages
            error_result = self.browser.find_element(
                By.CSS_SELECTOR,
                self.selectors.login.error_message,
                timeout=3
            )
            if error_result.is_success:
                self._save_screenshot("login_error")
                return Result.failure("Login failed - credentials may be incorrect")

            # Mark session as logged in (skip logout link verification)
            self.session.mark_logged_in()

            # Log session information
            session_info = self.session.get_session_info()
            logger.info(
                f"Login successful - Session started at {session_info['login_time']}"
            )
            logger.debug(f"Session details: {session_info}")

            return Result.success(None, "Login successful")

        except Exception as e:
            logger.error(f"Login failed with exception: {e}", exc_info=True)
            self._save_screenshot("login_exception")
            return Result.failure(f"Login exception: {e}", e)

    def get_lessons_for_month(
        self,
        year: int,
        month: int
    ) -> Result[List[LessonData]]:
        """
        Retrieve lessons for a specific month.

        Args:
            year: Year (e.g., 2025)
            month: Month (1-12)

        Returns:
            Result[List[LessonData]] containing lesson data

        Examples:
            >>> result = client.get_lessons_for_month(2025, 10)
            >>> if result.is_success:
            ...     for lesson in result.value:
            ...         print(f"Lesson: {lesson['date']} - {lesson['student_name']}")
        """
        try:
            # Ensure logged in
            login_check = self.ensure_logged_in()
            if login_check.is_failure:
                return Result.failure("Not logged in", login_check.error)

            logger.info(f"Retrieving lessons for {year}-{month:02d}")

            # Navigate to lessons page
            lessons_url = f"{self.base_url}/lessons"
            nav_result = self.browser.navigate(lessons_url)
            if nav_result.is_failure:
                return Result.failure(
                    "Failed to navigate to lessons page",
                    nav_result.error
                )

            # Wait for page to load
            wait_result = self._wait_for_navigation(timeout=10)
            if wait_result.is_failure:
                logger.warning(f"Page load wait failed: {wait_result.message}")

            # Wait for JavaScript rendering
            import time
            time.sleep(3)

            lessons: List[LessonData] = []

            # Find lesson cards by "編集" (Edit) buttons - each lesson has one
            # Use div[3] element as container
            base_xpath = "/html/body/div[1]/div[2]/div/div/main/div/section[2]/div/div/div/div[3]"

            try:
                # Use JavaScript to mark first 100 edit buttons within div[3] with a data attribute
                marked_count = self.browser.driver.execute_script("""
                    const container = document.evaluate(arguments[0], document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                    if (!container) return 0;

                    // Find all edit buttons within container and limit to 100
                    // Use exact match to exclude "受講履歴編集" buttons (only get "編集" buttons)
                    const buttons = container.querySelectorAll('button');
                    const editButtons = Array.from(buttons)
                        .filter(btn => btn.textContent.trim() === '編集')
                        .slice(0, 100);

                    // Mark each button with a data attribute
                    editButtons.forEach(btn => {
                        btn.setAttribute('data-terakoya-target', 'true');
                    });

                    return editButtons.length;
                """, base_xpath)

                if marked_count == 0:
                    self._save_screenshot("lessons_not_found")
                    return Result.failure(
                        "Failed to find lesson edit buttons within div[3]"
                    )

                logger.info(f"Marked {marked_count} lesson edit buttons (limited to 100, exact match '編集' only)")

                # Now find the marked buttons using Selenium
                edit_buttons_result = self.browser.find_elements(
                    By.CSS_SELECTOR,
                    "button[data-terakoya-target='true']",
                    timeout=5
                )

                if edit_buttons_result.is_failure or not edit_buttons_result.value:
                    self._save_screenshot("marked_buttons_not_found")
                    return Result.failure("Failed to retrieve marked buttons")

                edit_buttons = edit_buttons_result.value
                logger.info(f"Retrieved {len(edit_buttons)} marked buttons via Selenium")

            except Exception as e:
                self._save_screenshot("h3_base_element_not_found")
                return Result.failure(
                    f"Failed to find h3[2] base element: {e}",
                    e
                )

            # Extract data from each edit button's parent (lesson card)
            import re

            # First, collect all card texts
            card_texts = []
            for idx, button in enumerate(edit_buttons):
                try:
                    # Use JavaScript to find the card text by going up the DOM tree
                    card_text = self.browser.driver.execute_script("""
                        const button = arguments[0];
                        let parent = button;

                        // Go up the DOM tree to find the lesson card
                        for (let i = 0; i < 6; i++) {
                            parent = parent.parentElement;
                            if (!parent) break;

                            const text = parent.textContent;
                            const hasDate = /\\d{2}\\/\\d{2}\\([日月火水木金土]\\)/.test(text);
                            const hasTime = /\\d{2}:\\d{2}[~\\-]\\d{2}:\\d{2}/.test(text);

                            if (hasDate && hasTime && text.length < 300) {
                                return text;
                            }
                        }
                        return null;
                    """, button)

                    card_texts.append(card_text if card_text else "")

                except Exception as e:
                    logger.debug(f"Failed to get card text for button {idx}: {e}")
                    card_texts.append("")

            # Extract lessons using AI or regex
            if self.use_ai_extraction and self.ai_extractor:
                logger.info(f"Using AI extraction for {len(card_texts)} cards (batch size: {self.ai_batch_size})")
                try:
                    # AI batch extraction
                    extracted_results = self.ai_extractor.extract_lessons_batch(
                        card_texts,
                        year,
                        batch_size=self.ai_batch_size
                    )

                    for idx, lesson_data in enumerate(extracted_results):
                        if lesson_data is None:
                            logger.debug(f"Skipping card {idx}: AI extraction returned None")
                            continue

                        # Validate lesson data
                        validation = self.lesson_validator.validate(lesson_data)
                        if validation.is_valid:
                            lessons.append(lesson_data)
                        else:
                            logger.warning(
                                f"Invalid lesson data at card {idx}: "
                                f"{validation.get_summary()}"
                            )

                except Exception as e:
                    logger.error(f"AI extraction failed: {e}", exc_info=True)
                    logger.warning("Falling back to regex extraction")
                    self.use_ai_extraction = False

            # Fallback to regex extraction
            if not self.use_ai_extraction:
                logger.info(f"Using regex extraction for {len(card_texts)} cards")
                for idx, card_text in enumerate(card_texts):
                    if not card_text:
                        logger.debug(f"Could not find lesson card for button {idx}")
                        continue

                    try:
                        # Create a simple object to pass card_text to extraction method
                        class CardText:
                            def __init__(self, text):
                                self.text = text

                            def get_attribute(self, name):
                                # Return None for all attributes
                                return None

                        lesson_data = self._extract_lesson_from_card(CardText(card_text), idx, year)

                        if lesson_data is None:
                            logger.debug(f"Skipping row {idx}: extraction failed")
                            continue

                        # Validate lesson data
                        validation = self.lesson_validator.validate(lesson_data)
                        if validation.is_valid:
                            lessons.append(lesson_data)
                        else:
                            logger.warning(
                                f"Invalid lesson data at row {idx}: "
                                f"{validation.get_summary()}"
                            )

                    except Exception as e:
                        logger.debug(f"Failed to extract lesson {idx}: {e}")
                        continue

            # Filter by month
            target_month_str = f"{year}-{month:02d}"
            filtered_lessons = [
                lesson for lesson in lessons
                if lesson["date"].startswith(target_month_str)
            ]

            # Remove duplicates (safety fallback) - keep first occurrence of each (date, student_name) pair
            seen_keys = set()
            unique_lessons = []
            duplicates_removed = 0

            for lesson in filtered_lessons:
                key = (lesson["date"], lesson["student_name"])
                if key not in seen_keys:
                    seen_keys.add(key)
                    unique_lessons.append(lesson)
                else:
                    duplicates_removed += 1
                    logger.debug(
                        f"Duplicate removed: {lesson['date']} - {lesson['student_name']}"
                    )

            if duplicates_removed > 0:
                logger.warning(
                    f"Removed {duplicates_removed} duplicate lessons (safety fallback)"
                )

            logger.info(
                f"Retrieved {len(unique_lessons)} unique lessons for {year}-{month:02d}"
            )

            return Result.success(
                unique_lessons,
                f"Retrieved {len(unique_lessons)} lessons"
            )

        except Exception as e:
            logger.error(f"Failed to get lessons: {e}", exc_info=True)
            self._save_screenshot("get_lessons_exception")
            return Result.failure(f"Exception getting lessons: {e}", e)

    def navigate_to_invoice_page(self, year: int, month: int) -> Result[None]:
        """
        Navigate to invoice submission page for specific month.

        Args:
            year: Year (e.g., 2025)
            month: Month (1-12)

        Returns:
            Result[None] indicating success

        Examples:
            >>> result = client.navigate_to_invoice_page(2025, 10)
            >>> if result.is_success:
            ...     print("Ready to submit invoices")
        """
        try:
            # Ensure logged in
            login_check = self.ensure_logged_in()
            if login_check.is_failure:
                return Result.failure("Not logged in", login_check.error)

            logger.info(f"Navigating to invoice page for {year}-{month:02d}")

            # Navigate to invoice page (claim submission page)
            invoice_url = f"{self.base_url}/claim"
            nav_result = self.browser.navigate(invoice_url)
            if nav_result.is_failure:
                return Result.failure(
                    "Failed to navigate to invoice page",
                    nav_result.error
                )

            # Wait for page load
            time.sleep(2)

            # Select year/month if filter is available
            month_selector = self.selectors.invoice.invoice_month
            month_value = f"{year}/{month:02d}"  # Format: "2025/10"

            logger.info(f"Attempting to select month: {month_value}")
            select_result = self.browser.select_dropdown(
                By.CSS_SELECTOR,
                month_selector,
                month_value,
                timeout=5
            )

            if select_result.is_success:
                logger.info(f"Successfully selected month: {month_value}")
                # Wait for page to update after month selection
                time.sleep(2)
            else:
                logger.warning(f"Failed to select month dropdown: {select_result.message}")
                # Continue anyway - the dropdown might not exist or month might already be selected

            logger.info("Successfully navigated to invoice page")
            return Result.success(None, "Navigation successful")

        except Exception as e:
            logger.error(f"Navigation failed: {e}", exc_info=True)
            self._save_screenshot("invoice_nav_exception")
            return Result.failure(f"Navigation exception: {e}", e)

    def get_existing_invoices(self) -> Result[List[Dict[str, Any]]]:
        """
        Get existing invoice items on current page.

        Used for duplicate detection.

        Returns:
            Result[List[Dict]] containing existing invoice items

        Examples:
            >>> result = client.get_existing_invoices()
            >>> if result.is_success:
            ...     print(f"Found {len(result.value)} existing invoices")
        """
        try:
            logger.info("Retrieving existing invoices")

            # Find invoice item rows
            rows_result = self.browser.find_elements(
                By.CSS_SELECTOR,
                self.selectors.invoice.invoice_item_rows,
                timeout=5
            )

            if rows_result.is_failure:
                # No existing invoices (or table not found)
                logger.info("No existing invoices found")
                return Result.success([], "No existing invoices")

            existing_invoices = []

            # Extract data from each row
            for idx, row in enumerate(rows_result.value):
                invoice_item = self._extract_invoice_from_row(row, idx)

                if invoice_item is not None:
                    existing_invoices.append(invoice_item)
                else:
                    logger.debug(f"Skipping invoice row {idx}: extraction failed")

            logger.info(f"Found {len(existing_invoices)} existing invoices")
            return Result.success(
                existing_invoices,
                f"Found {len(existing_invoices)} invoices"
            )

        except Exception as e:
            logger.error(f"Failed to get existing invoices: {e}", exc_info=True)
            return Result.failure(f"Exception getting existing invoices: {e}", e)

    def is_duplicate(
        self,
        lesson: LessonData,
        existing_invoices: List[Dict[str, Any]]
    ) -> bool:
        """
        Check if lesson is already invoiced.

        Args:
            lesson: Lesson data to check
            existing_invoices: List of existing invoice items

        Returns:
            True if duplicate found

        Examples:
            >>> existing = client.get_existing_invoices().value
            >>> if client.is_duplicate(lesson, existing):
            ...     print("Already invoiced, skipping")
        """
        for invoice in existing_invoices:
            # Check by date + student_id
            if (invoice.get("date") == lesson["date"] and
                invoice.get("student_id") == lesson["student_id"]):
                return True

            # Or check by date + student_name (fallback)
            if (invoice.get("date") == lesson["date"] and
                invoice.get("student_name") == lesson["student_name"]):
                return True

        return False

    def add_invoice_item(
        self,
        lesson: LessonData,
        unit_price: int = 2300,
        dry_run: bool = False
    ) -> Result[None]:
        """
        Add a single invoice item.

        Args:
            lesson: Lesson data to add as invoice item
            unit_price: Unit price per hour (default: 2300 yen)
            dry_run: If True, fill form but don't submit (default: False)

        Returns:
            Result[None] indicating success

        Examples:
            >>> # Dry-run mode (fill form only)
            >>> result = client.add_invoice_item(lesson, unit_price=2300, dry_run=True)
            >>>
            >>> # Normal mode (fill and submit)
            >>> result = client.add_invoice_item(lesson, unit_price=2300, dry_run=False)
        """
        try:
            logger.info(
                f"Adding invoice item: {lesson['date']} - {lesson['student_name']}"
            )

            # Validate lesson data
            validation = self.lesson_validator.validate(lesson)
            if not validation.is_valid:
                return Result.failure(f"Invalid lesson data: {validation.get_summary()}")

            # Click "Add Item" button to open modal
            logger.debug(f"Clicking 'Add Item' button: {self.selectors.invoice.add_item_button}")
            time.sleep(0.5)  # Ensure page is stable

            add_result = self.browser.click_javascript(
                By.XPATH,
                self.selectors.invoice.add_item_button,
                timeout=10
            )

            if add_result.is_failure:
                logger.error(f"Failed to click add item button: {add_result.message}")
                self._save_screenshot("add_item_button_failed")
                return Result.failure(
                    "Failed to click add item button",
                    add_result.error
                )

            # Wait for modal to appear and become fully interactive
            logger.debug("Waiting for modal to appear...")
            time.sleep(1.5)  # Increased wait for modal animation

            # Verify modal appeared
            modal_wait_result = self._wait_for_modal_visible(timeout=5)
            if modal_wait_result.is_failure:
                self._save_screenshot("modal_not_visible")
                return Result.failure(
                    "Modal did not appear after clicking add item",
                    modal_wait_result.error
                )

            # Fill in form fields
            auto_date_mode = self._category_uses_auto_date(lesson.get("category", ""))

            if auto_date_mode:
                logger.info(
                    "Skipping manual date input because dedicated lesson selection populates the date"
                )
            else:
                # Date (REQUIRED) - React DatePicker input
                # Primary strategy dispatches React-compatible events via JavaScript
                # Convert date format from YYYY-MM-DD to YYYY年MM月DD日
                from datetime import datetime
                date_obj = datetime.strptime(lesson["date"], "%Y-%m-%d")
                date_formatted = date_obj.strftime("%Y年%m月%d日")  # e.g., "2025年10月01日"
                logger.info(f"Preparing date input value: {date_formatted}")

                # Find date input field
                date_elem_result = self.browser.find_element(
                    By.CSS_SELECTOR,
                    self.selectors.invoice.modal_date_input,
                    timeout=5
                )
                if date_elem_result.is_failure:
                    self._save_screenshot("date_field_not_found")
                    return Result.failure(
                        f"Date field not found: {date_elem_result.message}",
                        date_elem_result.error
                    )

                date_element = date_elem_result.value

                # Focus the field before injecting the value so React DatePicker is ready
                try:
                    date_element.click()
                except Exception as click_error:
                    logger.debug(f"Failed to click date field directly: {click_error}")
                    try:
                        self.browser.driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center'});",
                            date_element
                        )
                        self.browser.driver.execute_script("arguments[0].click();", date_element)
                    except Exception as js_click_error:
                        logger.debug(f"JavaScript click on date field also failed: {js_click_error}")

                time.sleep(0.2)

                # Primary approach: use JavaScript value setter compatible with React inputs
                logger.info(f"Setting date via JavaScript dispatcher: {date_formatted}")
                set_date_result = self.browser.set_value_javascript(
                    By.CSS_SELECTOR,
                    self.selectors.invoice.modal_date_input,
                    date_formatted,
                    timeout=5
                )

                if set_date_result.is_failure:
                    logger.warning(
                        f"JavaScript date injection failed ({set_date_result.message}); falling back to send_keys"
                    )
                    try:
                        # Fallback to manual typing to avoid hard failure
                        time.sleep(0.2)
                        try:
                            date_element.clear()
                        except Exception:
                            is_mac = platform.system() == "Darwin"
                            keys = Keys.COMMAND if is_mac else Keys.CONTROL
                            date_element.send_keys(keys + "a")
                            date_element.send_keys(Keys.DELETE)

                        time.sleep(0.1)
                        date_element.send_keys(date_formatted)
                        date_element.send_keys(Keys.TAB)
                    except Exception as fallback_error:
                        self._save_screenshot("date_input_failed")
                        return Result.failure(
                            f"Failed to set date field via all strategies: {fallback_error}",
                            fallback_error
                        )
                else:
                    logger.debug(set_date_result.message)
                    # Trigger blur to align with user behaviour and any validation hooks
                    try:
                        date_element.send_keys(Keys.TAB)
                    except Exception as tab_error:
                        logger.debug(f"TAB send failed after JS date input: {tab_error}")
                        try:
                            self.browser.driver.execute_script(
                                "arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));",
                                date_element
                            )
                        except Exception as blur_error:
                            logger.debug(f"Failed to dispatch blur event: {blur_error}")

            # Verify modal is still open after date processing/input
            modal_check = self.browser.find_element(
                By.CSS_SELECTOR,
                self.selectors.invoice.modal_category_select,
                timeout=3
            )
            if modal_check.is_failure:
                self._save_screenshot("modal_closed_after_date")
                return Result.failure("Modal closed unexpectedly after date input")

            # Category (REQUIRED) - SELECT dropdown
            # Map lesson category to dropdown value
            logger.info(f"Selecting category: {lesson['category']}")
            category_value = self._map_category_to_value(lesson["category"])
            logger.info(f"Category mapped to value: {category_value}")

            # First verify the select element exists and get its options
            category_elem_result = self.browser.find_element(
                By.CSS_SELECTOR,
                self.selectors.invoice.modal_category_select,
                timeout=5
            )
            if category_elem_result.is_failure:
                self._save_screenshot("category_element_not_found")
                return Result.failure(
                    f"Category select element not found",
                    category_elem_result.error
                )

            # Log available options for debugging
            try:
                from selenium.webdriver.support.ui import Select
                select_elem = Select(category_elem_result.value)
                available_options = [opt.get_attribute("value") for opt in select_elem.options]
                logger.info(f"Available category options: {available_options[:10]}")  # First 10
            except Exception as e:
                logger.warning(f"Failed to get category options: {e}")

            # Now select the category
            category_result = self.browser.select_dropdown(
                By.CSS_SELECTOR,
                self.selectors.invoice.modal_category_select,
                category_value,
                timeout=5
            )
            if category_result.is_failure:
                self._save_screenshot("category_select_failed")
                return Result.failure(
                    f"Failed to select category '{lesson['category']}' (value: {category_value})",
                    category_result.error
                )

            logger.info(f"Category selected successfully: {category_value}")

            # Wait for form to stabilize after category selection
            # Category selection may trigger JavaScript validation that affects other fields
            logger.info("Waiting for form to stabilize after category selection...")
            time.sleep(1)

            # Student (OPTIONAL) - Attempt selection to trigger lesson options for dedicated categories
            student_select_result = self._select_student_for_lesson(lesson)
            if student_select_result.is_success:
                if student_select_result.value:
                    logger.info(
                        student_select_result.message or "Student option selection completed"
                    )
                else:
                    logger.debug(
                        student_select_result.message or "Student selection not required"
                    )
            else:
                logger.warning(
                    f"Student selection may not have completed: {student_select_result.message}"
                )

            # After student selection (if any), wait for lesson options to load
            lesson_select_probe = self.browser.find_element(
                By.CSS_SELECTOR,
                self.selectors.invoice.modal_lesson_select,
                timeout=3
            )
            if lesson_select_probe.is_failure:
                lesson_select_probe = self.browser.find_element(
                    By.XPATH,
                    self.selectors.invoice.modal_lesson_select_xpath,
                    timeout=3
                )
            if lesson_select_probe.is_success:
                logger.info("Waiting for lesson options to load after student selection...")
                wait_result = self._wait_for_lesson_options_loaded(timeout=12)
                if wait_result.is_failure:
                    logger.warning(f"Lesson options may not have loaded: {wait_result.message}")
            else:
                logger.debug("Lesson select field not present; skipping lesson option wait")

            # Dedicated Lesson (REQUIRED for 専属レッスン category) - SELECT dropdown
            # After date is set, the lesson options should be loaded
            logger.info(f"Checking for lesson options after date selection...")

            # Verify lesson select has options
            lesson_select_result = self.browser.find_element(
                By.CSS_SELECTOR,
                self.selectors.invoice.modal_lesson_select,
                timeout=5
            )
            if lesson_select_result.is_failure:
                lesson_select_result = self.browser.find_element(
                    By.XPATH,
                    self.selectors.invoice.modal_lesson_select_xpath,
                    timeout=5
                )

            if lesson_select_result.is_success:
                from selenium.webdriver.support.ui import Select
                try:
                    # Re-fetch select element to ensure latest options after waits
                    lesson_select_refresh = self.browser.find_element(
                        By.CSS_SELECTOR,
                        self.selectors.invoice.modal_lesson_select,
                        timeout=3
                    )
                    if lesson_select_refresh.is_failure:
                        lesson_select_refresh = self.browser.find_element(
                            By.XPATH,
                            self.selectors.invoice.modal_lesson_select_xpath,
                            timeout=3
                        )
                    target_select_element = (
                        lesson_select_refresh.value
                        if lesson_select_refresh.is_success
                        else lesson_select_result.value
                    )
                    select_elem = Select(target_select_element)
                    option_values_preview = [
                        opt.get_attribute("value") for opt in select_elem.options[:5]
                    ]
                    logger.info(
                        f"Lesson select has {len(select_elem.options)} options: {option_values_preview}"
                    )

                    chosen_option = self._pick_lesson_option(select_elem, lesson)

                    if chosen_option is not None:
                        chosen_value = chosen_option.get_attribute("value")
                        chosen_label = (chosen_option.text or "").strip()
                        logger.info(
                            f"Selecting lesson option value={chosen_value} label='{chosen_label}'"
                        )

                        try:
                            select_elem.select_by_value(chosen_value)
                            self.browser.driver.execute_script(
                                "arguments[0].dispatchEvent(new Event('change', { bubbles: true }));",
                                target_select_element
                            )
                            logger.info("Lesson selected successfully")
                        except Exception as select_error:
                            logger.warning(
                                f"Failed to select lesson option {chosen_value}: {select_error}"
                            )
                    else:
                        logger.warning(
                            "No dedicated lesson option matched the lesson date; leaving default"
                        )

                except Exception as e:
                    logger.warning(f"Failed to process lesson options: {e}")

            # Duration (REQUIRED) - Number input in minutes
            # Use JavaScript to set value (similar to date field) to avoid interactability issues
            logger.info(f"Setting duration field to: {lesson['duration']}")
            duration_result = self.browser.set_value_javascript(
                By.CSS_SELECTOR,
                self.selectors.invoice.modal_duration_input,
                str(lesson["duration"]),
                timeout=5
            )
            if duration_result.is_failure:
                self._save_screenshot("duration_input_failed")
                return Result.failure(
                    f"Failed to set duration field: {duration_result.message}",
                    duration_result.error
                )

            # Unit Price (REQUIRED) - Text input (yen per hour)
            # Use JavaScript to set value for consistency
            logger.info(f"Setting unit price field to: {unit_price}")
            price_result = self.browser.set_value_javascript(
                By.CSS_SELECTOR,
                self.selectors.invoice.modal_unit_price_input,
                str(unit_price),
                timeout=5
            )
            if price_result.is_failure:
                self._save_screenshot("unit_price_input_failed")
                return Result.failure(
                    f"Failed to set unit price field: {price_result.message}",
                    price_result.error
                )

            # Handle dry-run vs normal mode
            if dry_run:
                # Dry-run mode: Leave modal open for inspection
                logger.info("Dry-run mode: Form filled, leaving modal open for inspection")
                logger.info("⚠️  Modal will remain open - check form values manually")

                # Take screenshot of filled form
                self._save_screenshot("dry_run_form_filled")

                logger.info("Invoice item form filled successfully (dry-run mode - not submitted)")
                return Result.success(None, "Invoice item form filled (not submitted)")
            else:
                # Normal mode: Click save button to submit
                logger.info("Normal mode: Saving invoice item")
                save_result = self.browser.click(
                    By.XPATH,
                    self.selectors.invoice.modal_save_button,
                    timeout=5
                )
                if save_result.is_failure:
                    self._save_screenshot("modal_save_failed")
                    return Result.failure("Failed to click save button", save_result.error)

                # Wait for modal to close
                close_wait_result = self._wait_for_modal_closed(timeout=5)
                if close_wait_result.is_failure:
                    logger.warning(f"Modal close wait failed: {close_wait_result.message}")

                logger.info("Invoice item saved successfully")
                return Result.success(None, "Invoice item saved")

        except Exception as e:
            logger.error(f"Failed to add invoice item: {e}", exc_info=True)
            self._save_screenshot("add_item_exception")
            return Result.failure(f"Exception adding invoice item: {e}", e)

    def _map_category_to_value(self, category: str) -> str:
        """
        Map lesson category to invoice form dropdown value.

        The invoice form has a category dropdown with specific values:
        - 1: 専属レッスン (Dedicated Lesson)
        - 2: 専属レッスン前後対応
        - 15: 単発レッスン (Spot Lesson)
        - etc.

        Args:
            category: Lesson category from lesson data

        Returns:
            Dropdown value (string number like "1", "2", etc.)
        """
        # Category mapping based on actual dropdown options
        category_map = {
            "専属レッスン": "1",
            "専属レッスン前後対応": "2",
            "質問対応(担当生徒)": "3",
            "カリキュラム作成": "4",
            "専属レッスンキャンセル": "5",
            "キャッチアップ": "6",
            "コンサル相談": "7",
            "メンタリング": "8",
            "質問対応(Q&A)": "9",
            "運営側依頼対応": "10",
            "書籍(教材)費用": "11",
            "リファラルインセンティブ": "12",
            "その他": "13",
            "教材開発": "14",
            "単発レッスン": "15",
            "タイムライン投稿": "16",
            "課題レビュー時給制": "17",
            "リスキルカレッジ対応": "18",
            "シゴトル対応": "19",
            "課題レビュー単価制": "20",
            "法人側依頼対応": "21",
            "道場レッスン": "22",
            "常駐レッスン対応": "23",
            "道場コンテンツ開発": "24",
            "転職コミュニティ対応": "25",
            "公開講座対応": "26",
        }

        # Try exact match first
        if category in category_map:
            return category_map[category]

        # Try partial match (e.g., "専属" in "専属レッスン")
        for key, value in category_map.items():
            if category in key or key in category:
                logger.debug(f"Partial category match: '{category}' -> '{key}' (value: {value})")
                return value

        # Default to "専属レッスン" (value 1) if no match
        logger.warning(
            f"Unknown category '{category}', defaulting to '専属レッスン' (value: 1)"
        )
        return "1"

    @staticmethod
    def _category_uses_auto_date(category: str) -> bool:
        """Return True if the category auto-populates the date when lesson is selected."""
        if not category:
            return False

        auto_categories = {
            "専属レッスン",
            "専属レッスン前後対応",
        }

        return any(key in category for key in auto_categories)

    @staticmethod
    def _pick_lesson_option(
        select_elem: "Select",
        lesson: LessonData
    ) -> Optional["WebElement"]:
        """Pick the most suitable dedicated-lesson option for the given lesson."""
        from datetime import datetime

        try:
            target_date = datetime.strptime(lesson["date"], "%Y-%m-%d")
        except Exception:
            target_date = None

        target_date_full = target_date.strftime("%Y/%m/%d") if target_date else None
        target_date_short = target_date.strftime("%m/%d") if target_date else None

        options = [opt for opt in select_elem.options if (opt.get_attribute("value") or "").strip()]
        if not options:
            return None

        # Skip first option if it's the placeholder
        filtered_options = [opt for opt in options if "選択してください" not in (opt.text or "")]
        if filtered_options:
            options = filtered_options

        def matches_date(option_text: str) -> bool:
            if target_date_full and target_date_full in option_text:
                return True
            if target_date_short and target_date_short in option_text:
                return True
            return False

        for option in options:
            text = (option.text or option.get_attribute("innerText") or "").strip()
            if text and matches_date(text):
                return option

        # Fallback: return first meaningful option
        return options[0]

    def add_invoice_item_with_retry(
        self,
        lesson: LessonData,
        unit_price: int = 2300,
        max_retries: int = 3,
        dry_run: bool = False
    ) -> Result[None]:
        """
        Add invoice item with retry logic.

        Note: Circuit breaker is applied at client level, not per-item.
        This method provides item-level retry with exponential backoff.

        Args:
            lesson: Lesson data
            unit_price: Unit price per hour
            max_retries: Maximum retry attempts
            dry_run: If True, fill form but don't submit (default: False)

        Returns:
            Result[None] indicating success

        Examples:
            >>> # Dry-run mode
            >>> result = client.add_invoice_item_with_retry(lesson, dry_run=True)
            >>>
            >>> # Normal mode with retries
            >>> result = client.add_invoice_item_with_retry(lesson, max_retries=3)
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Adding invoice item (attempt {attempt + 1}/{max_retries}): "
                    f"{lesson['date']} - {lesson['student_name']}"
                )

                # Direct call without circuit breaker (already applied at client level)
                result = self.add_invoice_item(lesson, unit_price, dry_run=dry_run)

                if result.is_success:
                    return result

                last_error = result.message
                logger.warning(
                    f"Attempt {attempt + 1} failed: {result.message}"
                )

                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 10)  # Cap at 10 seconds
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)

            except Exception as e:
                last_error = str(e)
                logger.error(f"Attempt {attempt + 1} exception: {e}")

                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 10)
                    time.sleep(wait_time)

        return Result.failure(
            f"Failed after {max_retries} attempts. Last error: {last_error}"
        )
