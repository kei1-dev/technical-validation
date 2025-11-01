"""
HTML scraping and data extraction.

This module provides HTML parsing and data extraction using BeautifulSoup
with support for tables, structured data, and text extraction.
"""

import logging
from typing import List, Dict, Any, Optional

import pandas as pd
from bs4 import BeautifulSoup


logger = logging.getLogger(__name__)


class Scraper:
    """
    HTML scraper using BeautifulSoup.

    Provides methods for:
    - Text extraction
    - Table extraction to DataFrame
    - Structured data extraction

    Examples:
        >>> html = browser.get_page_source().value
        >>> scraper = Scraper(html)
        >>> text = scraper.get_text(".content")
        >>> df = scraper.extract_table("table.data")
    """

    def __init__(self, html: str, parser: str = "lxml"):
        """
        Initialize scraper with HTML content.

        Args:
            html: HTML string to parse
            parser: Parser to use (default: "lxml")

        Examples:
            >>> scraper = Scraper(html_string)
            >>> scraper = Scraper(html_string, parser="html.parser")
        """
        self.html = html
        self.soup = BeautifulSoup(html, parser)

        logger.debug(f"Scraper initialized with {len(html)} bytes of HTML")

    def get_text(self, selector: Optional[str] = None) -> str:
        """
        Extract text content.

        Args:
            selector: CSS selector (if None, extracts all text)

        Returns:
            Extracted text content

        Examples:
            >>> # All text
            >>> text = scraper.get_text()

            >>> # Specific element
            >>> title = scraper.get_text(".page-title")
        """
        if selector is None:
            text = self.soup.get_text(separator=' ', strip=True)
        else:
            element = self.soup.select_one(selector)
            if element:
                text = element.get_text(separator=' ', strip=True)
            else:
                logger.warning(f"Element not found: {selector}")
                text = ""

        return text

    def extract_table(
        self,
        selector: str = "table"
    ) -> Optional[pd.DataFrame]:
        """
        Extract table data as DataFrame.

        Args:
            selector: CSS selector for table element

        Returns:
            DataFrame with table data, or None if not found

        Examples:
            >>> df = scraper.extract_table("table.lesson-list")
            >>> if df is not None:
            ...     print(df.head())
        """
        try:
            table = self.soup.select_one(selector)

            if not table:
                logger.warning(f"Table not found: {selector}")
                return None

            # Extract table to DataFrame
            df = pd.read_html(str(table))[0]

            logger.debug(
                f"Extracted table: {df.shape[0]} rows, {df.shape[1]} columns"
            )

            return df

        except Exception as e:
            logger.error(f"Failed to extract table: {e}")
            return None

    def extract_tables(
        self,
        selector: str = "table"
    ) -> List[pd.DataFrame]:
        """
        Extract all matching tables as DataFrames.

        Args:
            selector: CSS selector for table elements

        Returns:
            List of DataFrames

        Examples:
            >>> tables = scraper.extract_tables("table")
            >>> for i, df in enumerate(tables):
            ...     print(f"Table {i}: {df.shape}")
        """
        try:
            tables = self.soup.select(selector)

            if not tables:
                logger.warning(f"No tables found: {selector}")
                return []

            dataframes = []
            for table in tables:
                try:
                    df = pd.read_html(str(table))[0]
                    dataframes.append(df)
                except Exception as e:
                    logger.warning(f"Failed to parse table: {e}")

            logger.debug(f"Extracted {len(dataframes)} tables")

            return dataframes

        except Exception as e:
            logger.error(f"Failed to extract tables: {e}")
            return []

    def extract_structured_data(
        self,
        item_selector: str,
        field_selectors: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Extract structured data from repeating elements.

        Args:
            item_selector: CSS selector for each item container
            field_selectors: Dict mapping field names to CSS selectors

        Returns:
            List of dictionaries with extracted data

        Examples:
            >>> # Extract lesson items
            >>> lessons = scraper.extract_structured_data(
            ...     item_selector=".lesson-item",
            ...     field_selectors={
            ...         "date": ".lesson-date",
            ...         "student_name": ".student-name",
            ...         "status": ".lesson-status"
            ...     }
            ... )
            >>> for lesson in lessons:
            ...     print(f"{lesson['date']}: {lesson['student_name']}")
        """
        items = self.soup.select(item_selector)

        if not items:
            logger.warning(f"No items found: {item_selector}")
            return []

        results = []

        for item in items:
            data = {}

            for field_name, field_selector in field_selectors.items():
                element = item.select_one(field_selector)

                if element:
                    # Get text content
                    data[field_name] = element.get_text(strip=True)
                else:
                    # Field not found
                    data[field_name] = None

            results.append(data)

        logger.debug(f"Extracted {len(results)} items")

        return results

    def find_element_text(
        self,
        selector: str,
        default: str = ""
    ) -> str:
        """
        Find element and return its text.

        Args:
            selector: CSS selector
            default: Default value if not found

        Returns:
            Element text or default

        Examples:
            >>> title = scraper.find_element_text(".page-title", "No Title")
        """
        element = self.soup.select_one(selector)

        if element:
            return element.get_text(strip=True)

        return default

    def find_elements_text(
        self,
        selector: str
    ) -> List[str]:
        """
        Find all matching elements and return their texts.

        Args:
            selector: CSS selector

        Returns:
            List of element texts

        Examples:
            >>> names = scraper.find_elements_text(".student-name")
        """
        elements = self.soup.select(selector)
        return [el.get_text(strip=True) for el in elements]

    def get_attribute(
        self,
        selector: str,
        attribute: str,
        default: Optional[str] = None
    ) -> Optional[str]:
        """
        Get attribute value from element.

        Args:
            selector: CSS selector
            attribute: Attribute name
            default: Default value if not found

        Returns:
            Attribute value or default

        Examples:
            >>> url = scraper.get_attribute("a.link", "href")
            >>> img_src = scraper.get_attribute("img", "src")
        """
        element = self.soup.select_one(selector)

        if element and attribute in element.attrs:
            return element[attribute]

        return default

    def has_element(self, selector: str) -> bool:
        """
        Check if element exists.

        Args:
            selector: CSS selector

        Returns:
            True if element exists

        Examples:
            >>> if scraper.has_element(".error-message"):
            ...     print("Error detected")
        """
        return self.soup.select_one(selector) is not None
