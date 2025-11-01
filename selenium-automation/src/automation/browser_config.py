"""
Browser configuration dataclass.

This module provides a configuration dataclass for browser settings,
promoting better testability and flexibility.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Tuple


@dataclass
class BrowserConfig:
    """
    Configuration for Browser initialization.

    This dataclass encapsulates all browser configuration options,
    making it easier to:
    - Test different configurations
    - Create configuration presets
    - Pass configuration between components
    - Validate configuration values

    Attributes:
        headless: Run browser in headless mode
        download_dir: Custom download directory
        window_size: Browser window size (width, height)
        timeout: Default timeout for operations in seconds
        disable_automation_flags: Disable automation detection flags
        user_agent: Custom user agent string

    Examples:
        >>> # Default configuration
        >>> config = BrowserConfig()

        >>> # Headless configuration
        >>> config = BrowserConfig(headless=True)

        >>> # Custom configuration
        >>> config = BrowserConfig(
        ...     headless=True,
        ...     window_size=(1280, 720),
        ...     timeout=60,
        ...     download_dir="/tmp/downloads"
        ... )

        >>> # Create preset configurations
        >>> def testing_config() -> BrowserConfig:
        ...     return BrowserConfig(headless=True, timeout=5)
    """

    headless: bool = False
    download_dir: Optional[str] = None
    window_size: Tuple[int, int] = (1920, 1080)
    timeout: int = 30
    disable_automation_flags: bool = True
    user_agent: Optional[str] = None

    def __post_init__(self):
        """Validate configuration after initialization."""
        # Validate window size
        if len(self.window_size) != 2:
            raise ValueError(
                f"window_size must be a tuple of (width, height), "
                f"got: {self.window_size}"
            )

        width, height = self.window_size
        if width <= 0 or height <= 0:
            raise ValueError(
                f"window_size dimensions must be positive, "
                f"got: {self.window_size}"
            )

        if width < 800 or height < 600:
            raise ValueError(
                f"window_size too small (minimum 800x600), "
                f"got: {self.window_size}"
            )

        # Validate timeout
        if self.timeout <= 0:
            raise ValueError(
                f"timeout must be positive, got: {self.timeout}"
            )

        # Validate download directory if provided
        if self.download_dir:
            path = Path(self.download_dir)
            if path.exists() and not path.is_dir():
                raise ValueError(
                    f"download_dir must be a directory, got: {self.download_dir}"
                )

    @classmethod
    def for_testing(cls) -> 'BrowserConfig':
        """
        Create configuration optimized for testing.

        Returns:
            BrowserConfig with headless mode and short timeout

        Examples:
            >>> config = BrowserConfig.for_testing()
            >>> assert config.headless is True
            >>> assert config.timeout == 5
        """
        return cls(
            headless=True,
            timeout=5,
            disable_automation_flags=True
        )

    @classmethod
    def for_development(cls) -> 'BrowserConfig':
        """
        Create configuration optimized for development.

        Returns:
            BrowserConfig with visible browser and longer timeout

        Examples:
            >>> config = BrowserConfig.for_development()
            >>> assert config.headless is False
            >>> assert config.timeout == 30
        """
        return cls(
            headless=False,
            timeout=30,
            disable_automation_flags=True
        )

    @classmethod
    def for_production(cls, download_dir: str) -> 'BrowserConfig':
        """
        Create configuration optimized for production.

        Args:
            download_dir: Directory for downloads

        Returns:
            BrowserConfig with headless mode and production settings

        Examples:
            >>> config = BrowserConfig.for_production("/var/data/downloads")
            >>> assert config.headless is True
        """
        return cls(
            headless=True,
            download_dir=download_dir,
            timeout=60,
            disable_automation_flags=True
        )

    def to_dict(self) -> dict:
        """
        Convert configuration to dictionary.

        Returns:
            Dictionary representation of configuration

        Examples:
            >>> config = BrowserConfig(headless=True)
            >>> config_dict = config.to_dict()
            >>> assert config_dict["headless"] is True
        """
        return {
            "headless": self.headless,
            "download_dir": self.download_dir,
            "window_size": self.window_size,
            "timeout": self.timeout,
            "disable_automation_flags": self.disable_automation_flags,
            "user_agent": self.user_agent,
        }
