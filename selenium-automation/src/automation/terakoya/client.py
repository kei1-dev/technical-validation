"""
Terakoya automation client.

This module provides the main TerakoyaClient class for automating
invoice submission on the Terakoya platform.
"""

import logging
import os
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

from selenium.webdriver.common.by import By

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

    def _wait_for_modal_visible(self, timeout: int = 5) -> Result[None]:
        """
        Wait for modal dialog to appear.

        Args:
            timeout: Maximum wait time in seconds

        Returns:
            Result[None] indicating success
        """
        modal_result = self.browser.find_element(
            By.CSS_SELECTOR,
            self.selectors.invoice.modal,
            timeout=timeout
        )

        if modal_result.is_success:
            return Result.success(None, "Modal visible")
        else:
            return Result.failure("Modal not visible", modal_result.error)

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

            # Navigate to invoice page
            invoice_url = f"{self.base_url}/invoices"
            nav_result = self.browser.navigate(invoice_url)
            if nav_result.is_failure:
                return Result.failure(
                    "Failed to navigate to invoice page",
                    nav_result.error
                )

            # Wait for page load
            time.sleep(2)

            # TODO: Select year/month if filters are available

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
        unit_price: int = 2300
    ) -> Result[None]:
        """
        Add a single invoice item.

        Args:
            lesson: Lesson data to add as invoice item
            unit_price: Unit price per hour (default: 2300 yen)

        Returns:
            Result[None] indicating success

        Examples:
            >>> result = client.add_invoice_item(lesson, unit_price=2300)
            >>> if result.is_success:
            ...     print("Invoice item added")
        """
        try:
            logger.info(
                f"Adding invoice item: {lesson['date']} - {lesson['student_name']}"
            )

            # Validate lesson data
            validation = self.lesson_validator.validate(lesson)
            if not validation.is_valid:
                return Result.failure(f"Invalid lesson data: {validation.get_summary()}")

            # Click "Add Item" button
            add_result = self.browser.click(
                By.CSS_SELECTOR,
                self.selectors.invoice.add_item_button,
                timeout=10
            )
            if add_result.is_failure:
                self._save_screenshot("add_item_button_failed")
                return Result.failure(
                    "Failed to click add item button",
                    add_result.error
                )

            # Wait for modal to appear
            modal_wait_result = self._wait_for_modal_visible(timeout=5)
            if modal_wait_result.is_failure:
                self._save_screenshot("modal_not_visible")
                return Result.failure(
                    "Modal did not appear after clicking add item",
                    modal_wait_result.error
                )

            # Fill in form fields using standardized helper
            # Date (REQUIRED)
            date_result = self._input_field(
                self.selectors.invoice.modal_date_input,
                lesson["date"],
                "date",
                FieldImportance.REQUIRED
            )
            if date_result.is_failure:
                return date_result

            # Student ID (OPTIONAL - may not be visible on all forms)
            student_id_result = self._input_field(
                self.selectors.invoice.modal_student_id_input,
                lesson["student_id"],
                "student_id",
                FieldImportance.OPTIONAL
            )

            # Student Name (REQUIRED)
            name_result = self._input_field(
                self.selectors.invoice.modal_student_name_input,
                lesson["student_name"],
                "student_name",
                FieldImportance.REQUIRED
            )
            if name_result.is_failure:
                return name_result

            # Category (OPTIONAL - may be auto-filled)
            category_result = self._input_field(
                self.selectors.invoice.modal_category_input,
                lesson["category"],
                "category",
                FieldImportance.OPTIONAL
            )

            # Duration (REQUIRED)
            duration_result = self._input_field(
                self.selectors.invoice.modal_duration_input,
                str(lesson["duration"]),
                "duration",
                FieldImportance.REQUIRED
            )
            if duration_result.is_failure:
                return duration_result

            # Unit Price (REQUIRED)
            price_result = self._input_field(
                self.selectors.invoice.modal_unit_price_input,
                str(unit_price),
                "unit_price",
                FieldImportance.REQUIRED
            )
            if price_result.is_failure:
                return price_result

            # Click Save
            save_result = self.browser.click(
                By.CSS_SELECTOR,
                self.selectors.invoice.modal_save_button,
                timeout=5
            )
            if save_result.is_failure:
                self._save_screenshot("modal_save_failed")
                return Result.failure("Failed to click save", save_result.error)

            # Wait for modal to close
            close_wait_result = self._wait_for_modal_closed(timeout=5)
            if close_wait_result.is_failure:
                logger.warning(f"Modal close wait failed: {close_wait_result.message}")

            logger.info("Invoice item added successfully")
            return Result.success(None, "Invoice item added")

        except Exception as e:
            logger.error(f"Failed to add invoice item: {e}", exc_info=True)
            self._save_screenshot("add_item_exception")
            return Result.failure(f"Exception adding invoice item: {e}", e)

    def add_invoice_item_with_retry(
        self,
        lesson: LessonData,
        unit_price: int = 2300,
        max_retries: int = 3
    ) -> Result[None]:
        """
        Add invoice item with retry logic.

        Note: Circuit breaker is applied at client level, not per-item.
        This method provides item-level retry with exponential backoff.

        Args:
            lesson: Lesson data
            unit_price: Unit price per hour
            max_retries: Maximum retry attempts

        Returns:
            Result[None] indicating success

        Examples:
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
                result = self.add_invoice_item(lesson, unit_price)

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

    def submit_invoice(self) -> Result[None]:
        """
        Submit the invoice.

        Returns:
            Result[None] indicating success

        Examples:
            >>> result = client.submit_invoice()
            >>> if result.is_success:
            ...     print("Invoice submitted successfully")
        """
        try:
            logger.info("Submitting invoice")

            # Click submit button
            submit_result = self.browser.click(
                By.CSS_SELECTOR,
                self.selectors.invoice.submit_button,
                timeout=10
            )
            if submit_result.is_failure:
                self._save_screenshot("submit_button_failed")
                return Result.failure(
                    "Failed to click submit button",
                    submit_result.error
                )

            # Wait for page to process the submission
            wait_result = self._wait_for_navigation(timeout=10)
            if wait_result.is_failure:
                logger.warning(f"Post-submit navigation wait failed: {wait_result.message}")

            # Check for success message
            success_result = self.browser.find_element(
                By.CSS_SELECTOR,
                self.selectors.invoice.success_message,
                timeout=10
            )

            if success_result.is_success:
                logger.info("Invoice submitted successfully")
                self._save_screenshot("submit_success")
                return Result.success(None, "Invoice submitted successfully")

            # Check for error message
            error_result = self.browser.find_element(
                By.CSS_SELECTOR,
                self.selectors.invoice.error_message,
                timeout=5
            )

            if error_result.is_success:
                self._save_screenshot("submit_error")
                return Result.failure("Invoice submission failed - error message displayed")

            # Uncertain result
            self._save_screenshot("submit_uncertain")
            logger.warning("Invoice submission result uncertain")
            return Result.success(None, "Invoice submission result uncertain")

        except Exception as e:
            logger.error(f"Invoice submission failed: {e}", exc_info=True)
            self._save_screenshot("submit_exception")
            return Result.failure(f"Submit exception: {e}", e)
