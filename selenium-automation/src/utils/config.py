"""
Configuration management with environment variables.

This module provides centralized configuration management
with validation and type safety.
"""

import os
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
from dotenv import load_dotenv


class SecureString:
    """
    Wrapper for sensitive strings that prevents accidental exposure.

    This class wraps sensitive data (like passwords) to prevent
    accidental logging or printing.

    Examples:
        >>> password = SecureString("secret123")
        >>> str(password)  # Returns "********"
        >>> password.get_value()  # Returns actual value
    """

    def __init__(self, value: str):
        """
        Initialize SecureString with sensitive value.

        Args:
            value: Sensitive string to protect
        """
        self._value = value

    def get_value(self) -> str:
        """
        Get the actual value (use with caution).

        Returns:
            The actual sensitive string value

        Warning:
            This exposes the sensitive value. Use only when necessary
            (e.g., for authentication) and never log the result.
        """
        return self._value

    def __str__(self) -> str:
        """Return masked string representation."""
        return "********"

    def __repr__(self) -> str:
        """Return masked repr."""
        return "SecureString(********)"

    def __eq__(self, other) -> bool:
        """Compare SecureString values."""
        if isinstance(other, SecureString):
            return self._value == other._value
        return False


class Config:
    """
    Application configuration manager.

    Loads configuration from environment variables and provides
    validated access to configuration values.

    Attributes:
        terakoya_email: Terakoya login email
        terakoya_password: Terakoya login password
        terakoya_url: Terakoya site URL
        lesson_duration: Default lesson duration in minutes
        lesson_unit_price: Default unit price for lessons
        output_dir: Output directory for logs, screenshots, data
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Examples:
        >>> config = Config()
        >>> if config.validate():
        ...     email = config.terakoya_email
        ...     print(f"Loaded config for: {email}")
    """

    @staticmethod
    def _validate_url(url: str, name: str) -> str:
        """
        Validate URL format and scheme.

        Args:
            url: URL to validate
            name: Variable name for error message

        Returns:
            Validated URL

        Raises:
            ValueError: If URL is invalid
        """
        try:
            parsed = urlparse(url)

            if not parsed.scheme:
                raise ValueError(f"{name} must include URL scheme (http/https)")

            if parsed.scheme not in ['http', 'https']:
                raise ValueError(f"{name} must use http or https scheme, got: {parsed.scheme}")

            if not parsed.netloc:
                raise ValueError(f"{name} must have a valid domain")

            return url

        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Invalid {name}: {url} - {e}")

    def __init__(self):
        """Initialize configuration by loading environment variables."""
        # Load .env file if it exists
        load_dotenv()

        # Terakoya credentials
        self._terakoya_email = os.getenv("TERAKOYA_EMAIL")

        # Wrap password in SecureString for protection
        pwd = os.getenv("TERAKOYA_PASSWORD")
        self._terakoya_password = SecureString(pwd) if pwd else None

        # Validate and store URL
        url = os.getenv("TERAKOYA_URL", "https://terakoya.sejuku.net/")
        self._terakoya_url = self._validate_url(url, "TERAKOYA_URL")

        # Invoice settings
        self._lesson_duration = int(os.getenv("TERAKOYA_LESSON_DURATION", "60"))
        self._lesson_unit_price = int(os.getenv("TERAKOYA_LESSON_UNIT_PRICE", "2300"))

        # Output settings
        self._output_dir = Path(os.getenv("OUTPUT_DIR", "output"))
        self._log_level = os.getenv("LOG_LEVEL", "INFO").upper()

        # Browser settings
        self._browser_headless = os.getenv("BROWSER_HEADLESS", "false").lower() == "true"
        self._browser_timeout = int(os.getenv("BROWSER_TIMEOUT", "30"))

    @property
    def terakoya_email(self) -> str:
        """
        Get Terakoya login email.

        Returns:
            Email address

        Raises:
            ValueError: If email is not set
        """
        if not self._terakoya_email:
            raise ValueError("TERAKOYA_EMAIL is not set in environment")
        return self._terakoya_email

    @property
    def terakoya_password(self) -> Optional[SecureString]:
        """
        Get Terakoya login password (wrapped in SecureString).

        Returns:
            SecureString wrapper containing password, or None if not set

        Usage:
            >>> password = config.terakoya_password
            >>> if password:
            ...     pwd_value = password.get_value()
            >>> # Never log or print config.terakoya_password directly!

        Note:
            Password can be provided via TERAKOYA_PASSWORD environment variable
            or via command-line argument in the script.

        Warning:
            Use get_value() to extract the actual password only when needed
            for authentication. Never log the result.
        """
        return self._terakoya_password

    @property
    def terakoya_url(self) -> str:
        """Get Terakoya site URL."""
        return self._terakoya_url

    @property
    def lesson_duration(self) -> int:
        """Get default lesson duration in minutes."""
        return self._lesson_duration

    @property
    def lesson_unit_price(self) -> int:
        """Get default unit price for lessons in yen."""
        return self._lesson_unit_price

    @property
    def output_dir(self) -> Path:
        """Get output directory path."""
        return self._output_dir

    @property
    def log_level(self) -> str:
        """Get logging level."""
        return self._log_level

    @property
    def browser_headless(self) -> bool:
        """Get whether to run browser in headless mode."""
        return self._browser_headless

    @property
    def browser_timeout(self) -> int:
        """Get browser operation timeout in seconds."""
        return self._browser_timeout

    def validate(self) -> bool:
        """
        Validate configuration values.

        Returns:
            True if all required configuration is valid

        Raises:
            ValueError: If validation fails
        """
        errors = []

        # Check required fields
        if not self._terakoya_email:
            errors.append("TERAKOYA_EMAIL is required")

        if not self._terakoya_url:
            errors.append("TERAKOYA_URL is required")

        # Validate email format
        if self._terakoya_email and "@" not in self._terakoya_email:
            errors.append("TERAKOYA_EMAIL must be a valid email address")

        # Validate password length if provided (unwrap SecureString for validation)
        # Note: Password is now optional in config (can be provided via CLI)
        if self._terakoya_password:
            pwd_value = self._terakoya_password.get_value()
            if len(pwd_value) < 8:
                errors.append("TERAKOYA_PASSWORD must be at least 8 characters (if provided)")

        # Validate numeric values
        if self._lesson_duration <= 0:
            errors.append("TERAKOYA_LESSON_DURATION must be positive")

        if self._lesson_unit_price <= 0:
            errors.append("TERAKOYA_LESSON_UNIT_PRICE must be positive")

        if self._browser_timeout <= 0:
            errors.append("BROWSER_TIMEOUT must be positive")

        # Validate log level
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self._log_level not in valid_levels:
            errors.append(
                f"LOG_LEVEL must be one of: {', '.join(valid_levels)}"
            )

        if errors:
            error_msg = "Configuration validation failed:\n  - " + "\n  - ".join(errors)
            raise ValueError(error_msg)

        return True

    def create_output_directories(self):
        """Create output directories if they don't exist."""
        directories = [
            self.output_dir / "terakoya_logs",
            self.output_dir / "terakoya_screenshots",
            self.output_dir / "terakoya_data",
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)


# Singleton instance
config = Config()
