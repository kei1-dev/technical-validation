"""
Terakoya website selectors.

This module centralizes all CSS/XPath selectors for the Terakoya website.
Centralizing selectors makes it easier to update when the site structure changes.

Usage:
    >>> from src.automation.terakoya.selectors import TerakoyaSelectors
    >>> selectors = TerakoyaSelectors()
    >>> browser.find_element(By.CSS_SELECTOR, selectors.login.email_input)
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class LoginSelectors:
    """Selectors for login page."""

    # Login form
    email_input: str = "input[type='email'], input[name='email'], #email"
    password_input: str = "input[type='password'], input[name='password'], #password"
    login_button: str = "button[type='submit'], input[type='submit']"

    # Error messages
    error_message: str = ".error, .alert-danger, [role='alert']"

    # Post-login indicators
    logout_link: str = "a[href*='logout']"
    user_menu: str = ".user-menu, .account-menu, [data-testid='user-menu']"


@dataclass(frozen=True)
class LessonSelectors:
    """Selectors for lesson list page."""

    # Navigation
    lessons_link: str = "a[href*='lesson'], a:contains('レッスン')"

    # Lesson list
    lesson_table: str = "table.lessons, .lesson-list, [data-testid='lesson-table']"
    lesson_rows: str = "tr.lesson-row, tbody tr, .lesson-item"

    # Lesson item fields
    lesson_date: str = "td.date, .lesson-date, [data-field='date']"
    lesson_student: str = "td.student, .student-name, [data-field='student']"
    lesson_category: str = "td.category, .lesson-category, [data-field='category']"
    lesson_duration: str = "td.duration, .lesson-duration, [data-field='duration']"
    lesson_status: str = "td.status, .lesson-status, [data-field='status']"
    lesson_id: str = "[data-lesson-id], .lesson-id"

    # Filters
    month_filter: str = "select[name='month'], .month-selector, [data-filter='month']"
    year_filter: str = "select[name='year'], .year-selector, [data-filter='year']"
    status_filter: str = "select[name='status'], .status-filter, [data-filter='status']"

    # Pagination
    next_page: str = "a.next, .pagination-next, [rel='next']"
    prev_page: str = "a.prev, .pagination-prev, [rel='prev']"


@dataclass(frozen=True)
class InvoiceSelectors:
    """
    Selectors for invoice submission page.

    Note: These selectors are verified against the actual Terakoya claim page
    as of 2025-11-01. The page uses styled-components (dynamic class names),
    so we rely on stable attributes like id, name, and text content.
    """

    # Navigation
    invoice_link: str = "a[href*='claim']"  # Changed from 'invoice' to 'claim'
    create_invoice_button: str = "button:contains('請求書作成'), .create-invoice, [data-action='create-invoice']"

    # Invoice form - month/year selector
    invoice_month: str = "select[name='month']"  # Actual selector from claim page
    invoice_year: str = "select[name='invoice_year'], .invoice-year, [data-field='year']"

    # Invoice items list (existing invoices)
    invoice_items_table: str = "table.invoice-items, .invoice-list, [data-testid='invoice-items']"
    invoice_item_rows: str = "tr.invoice-item, tbody tr, .invoice-row"

    # Invoice item fields (for existing items)
    item_date: str = "td.date, .item-date, [data-field='date']"
    item_student: str = "td.student, .item-student, [data-field='student']"
    item_student_id: str = "td.student-id, .item-student-id, [data-field='student-id']"
    item_category: str = "td.category, .item-category, [data-field='category']"
    item_duration: str = "td.duration, .item-duration, [data-field='duration']"
    item_unit_price: str = "td.unit-price, .item-unit-price, [data-field='unit-price']"
    item_total: str = "td.total, .item-total, [data-field='total']"

    # Add invoice item modal/form
    # IMPORTANT: Use XPath for button with exact text match (styled-components classes are dynamic)
    add_item_button: str = "//button[text()='請求項目の追加']"

    # Modal selector - unreliable due to styled-components, but kept for compatibility
    modal: str = ".modal, .dialog, [role='dialog']"

    # Modal form fields (verified from actual HTML structure)
    # Date field: React DatePicker input
    modal_date_input: str = "input.datepicker-date"

    # Category field: SELECT dropdown (requires select_dropdown method, not input_text!)
    # Options: 専属レッスン (value=1), 専属レッスン前後対応 (value=2), etc.
    modal_category_select: str = "select#category"

    # Student field: SELECT dropdown
    modal_student_select: str = "select#student"  # Student selection dropdown

    # Alternative: Custom dropdown component (if select doesn't work)
    # Structure: div.sc-eYHxxX > div.sc-eVrRMb with search input
    modal_student_dropdown: str = "div.sc-eYHxxX"  # Dropdown wrapper
    modal_student_dropdown_xpath: str = (
        "//div[@class='sc-hSQXhq fCEnGE']//div[contains(@class,'sc-eYHxxX')]"
    )
    modal_student_dropdown_display: str = "div.sc-eVrRMb"  # Click target to open list
    modal_student_dropdown_search_input: str = "input[placeholder='検索']"
    modal_student_dropdown_options: str = "ul li"

    # Dedicated lesson field: SELECT dropdown
    modal_lesson_select: str = "select#lesson"
    modal_lesson_select_xpath: str = (
        "/html/body/div[1]/div[2]/div/div/div[2]/div/div[4]/select"
    )

    # Spot lesson field: SELECT dropdown
    modal_spot_lesson_select: str = "select#spotLesson"

    # Duration field: Number input (minutes)
    modal_duration_input: str = "input#amount"

    # Unit price field: Text input (yen per hour)
    modal_unit_price_input: str = "input#unit_price"

    # Additional fields (for different billing types)
    modal_per_item_amount_input: str = "input#per_item_amount"
    modal_per_item_unit_price_input: str = "input#per_item_unit_price"
    modal_additional_payment_input: str = "input#additional_payment"
    modal_chara_num_input: str = "input#chara_num"
    modal_chara_unit_price_input: str = "input#chara_unit_price"
    modal_remark_textarea: str = "textarea#remark"

    # Modal buttons (use XPath for text-based selection due to dynamic classes)
    modal_save_button: str = "//button[text()='追加']"  # "Add" button in modal footer
    modal_cancel_button: str = "//button[text()='キャンセル']"
    modal_close_button: str = "button.close, .modal-close, img[src*='close']"

    # Submit invoice (monthly submission)
    submit_button: str = "//button[text()='月次の請求を申請する']"  # Actual text from page
    confirm_button: str = "//button[text()='請求申請の確定']"  # Confirmation modal button

    # Summary
    total_amount: str = ".total-amount, #invoice_total, [data-field='total']"
    item_count: str = ".item-count, #invoice_count, [data-field='count']"

    # Success/Error messages
    success_message: str = ".success, .alert-success, [role='status']"
    error_message: str = ".error, .alert-danger, [role='alert']"


@dataclass(frozen=True)
class NavigationSelectors:
    """Selectors for site navigation."""

    # Main navigation
    home_link: str = "a[href='/'], .home-link, [data-nav='home']"
    dashboard_link: str = "a[href*='dashboard'], .dashboard-link, [data-nav='dashboard']"

    # Loading indicators
    loading_spinner: str = ".loading, .spinner, [data-loading='true']"
    overlay: str = ".overlay, .modal-backdrop, .loading-overlay"

    # Breadcrumbs
    breadcrumb: str = ".breadcrumb, nav[aria-label='breadcrumb']"


class TerakoyaSelectors:
    """
    Centralized selectors for Terakoya website.

    This class provides access to all selectors organized by page/feature.

    Examples:
        >>> selectors = TerakoyaSelectors()
        >>> email_selector = selectors.login.email_input
        >>> browser.find_element(By.CSS_SELECTOR, email_selector)

        >>> # Access invoice selectors
        >>> add_button = selectors.invoice.add_item_button
        >>> browser.click(By.CSS_SELECTOR, add_button)
    """

    def __init__(self):
        """Initialize selector groups."""
        self.login = LoginSelectors()
        self.lesson = LessonSelectors()
        self.invoice = InvoiceSelectors()
        self.navigation = NavigationSelectors()

    def get_all_selectors(self) -> dict:
        """
        Get all selectors as a dictionary.

        Useful for debugging or documentation.

        Returns:
            Dictionary mapping selector paths to values
        """
        return {
            "login": self.login.__dict__,
            "lesson": self.lesson.__dict__,
            "invoice": self.invoice.__dict__,
            "navigation": self.navigation.__dict__,
        }


# Singleton instance for convenience
selectors = TerakoyaSelectors()
