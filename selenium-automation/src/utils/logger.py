"""
Logging utilities with security features.

This module provides logging setup with:
- Configurable log levels and output destinations
- Log rotation for file handlers
- Sensitive data masking (passwords, emails)
- Structured log format
"""

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


def mask_email(email: str) -> str:
    """
    Mask email address for safe logging.

    Args:
        email: Email address to mask

    Returns:
        Masked email (e.g., "u***@example.com")

    Examples:
        >>> mask_email("user@example.com")
        'u***@example.com'
        >>> mask_email("invalid")
        '***'
    """
    if not email or "@" not in email:
        return "***"

    local, domain = email.split("@", 1)
    masked_local = local[0] + "***" if len(local) > 0 else "***"
    return f"{masked_local}@{domain}"


def mask_password(password: str) -> str:
    """
    Completely mask password for safe logging.

    Args:
        password: Password to mask

    Returns:
        Always returns "********"

    Examples:
        >>> mask_password("secret123")
        '********'
    """
    return "********"


class SensitiveDataFilter(logging.Filter):
    """
    Logging filter that automatically masks sensitive information.

    This filter scans log messages for patterns that might contain
    passwords or other sensitive data and masks them before output.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter and mask sensitive data in log record.

        Args:
            record: Log record to filter

        Returns:
            Always True (allows all records through after masking)
        """
        # Mask password patterns
        record.msg = re.sub(
            r'password["\']?\s*[:=]\s*["\']?([^"\'\s]+)',
            r'password: ********',
            str(record.msg),
            flags=re.IGNORECASE
        )

        # Mask "pass=" or "pwd=" patterns
        record.msg = re.sub(
            r'(pass|pwd)["\']?\s*[:=]\s*["\']?([^"\'\s]+)',
            r'\1: ********',
            str(record.msg),
            flags=re.IGNORECASE
        )

        return True


def setup_logger(
    name: str = "selenium_automation",
    level: int = logging.INFO,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Set up and configure a logger instance.

    Args:
        name: Logger name (default: "selenium_automation")
        level: Logging level (default: logging.INFO)
        log_file: Optional path to log file for file output

    Returns:
        Configured logger instance

    Examples:
        >>> # Basic console logging
        >>> logger = setup_logger()
        >>> logger.info("Application started")

        >>> # File logging with rotation
        >>> logger = setup_logger(
        ...     name="terakoya",
        ...     level=logging.DEBUG,
        ...     log_file="output/logs/app.log"
        ... )
    """
    logger = logging.getLogger(name)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # Define log format
    formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)s] %(name)s:%(funcName)s:%(lineno)d %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler with rotation (if log file specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Add sensitive data filter
    logger.addFilter(SensitiveDataFilter())

    return logger
