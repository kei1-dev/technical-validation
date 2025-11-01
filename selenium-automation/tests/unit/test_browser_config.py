"""
Unit tests for BrowserConfig.

Tests browser configuration dataclass functionality.
"""

import pytest
from pathlib import Path
from src.automation.browser_config import BrowserConfig


class TestBrowserConfig:
    """Test suite for BrowserConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = BrowserConfig()

        assert config.headless is False
        assert config.download_dir is None
        assert config.window_size == (1920, 1080)
        assert config.timeout == 30
        assert config.disable_automation_flags is True
        assert config.user_agent is None

    def test_custom_config(self):
        """Test custom configuration values."""
        config = BrowserConfig(
            headless=True,
            download_dir="/tmp/downloads",
            window_size=(1280, 720),
            timeout=60,
            disable_automation_flags=False,
            user_agent="Custom Agent"
        )

        assert config.headless is True
        assert config.download_dir == "/tmp/downloads"
        assert config.window_size == (1280, 720)
        assert config.timeout == 60
        assert config.disable_automation_flags is False
        assert config.user_agent == "Custom Agent"

    def test_for_testing_preset(self):
        """Test testing configuration preset."""
        config = BrowserConfig.for_testing()

        assert config.headless is True
        assert config.timeout == 5
        assert config.disable_automation_flags is True

    def test_for_development_preset(self):
        """Test development configuration preset."""
        config = BrowserConfig.for_development()

        assert config.headless is False
        assert config.timeout == 30
        assert config.disable_automation_flags is True

    def test_for_production_preset(self):
        """Test production configuration preset."""
        config = BrowserConfig.for_production("/var/data/downloads")

        assert config.headless is True
        assert config.download_dir == "/var/data/downloads"
        assert config.timeout == 60
        assert config.disable_automation_flags is True

    def test_to_dict(self):
        """Test conversion to dictionary."""
        config = BrowserConfig(
            headless=True,
            timeout=45
        )

        config_dict = config.to_dict()

        assert config_dict["headless"] is True
        assert config_dict["timeout"] == 45
        assert config_dict["window_size"] == (1920, 1080)
        assert config_dict["download_dir"] is None

    def test_invalid_window_size_dimensions(self):
        """Test validation of window size dimensions."""
        with pytest.raises(ValueError, match="window_size must be a tuple"):
            BrowserConfig(window_size=(1920,))

    def test_invalid_window_size_negative(self):
        """Test validation of negative window size."""
        with pytest.raises(ValueError, match="dimensions must be positive"):
            BrowserConfig(window_size=(-100, 800))

    def test_window_size_too_small(self):
        """Test validation of minimum window size."""
        with pytest.raises(ValueError, match="window_size too small"):
            BrowserConfig(window_size=(640, 480))

    def test_invalid_timeout_zero(self):
        """Test validation of zero timeout."""
        with pytest.raises(ValueError, match="timeout must be positive"):
            BrowserConfig(timeout=0)

    def test_invalid_timeout_negative(self):
        """Test validation of negative timeout."""
        with pytest.raises(ValueError, match="timeout must be positive"):
            BrowserConfig(timeout=-10)

    def test_download_dir_not_directory(self, tmp_path):
        """Test validation when download_dir is a file, not directory."""
        # Create a file instead of directory
        file_path = tmp_path / "not_a_dir.txt"
        file_path.write_text("test")

        with pytest.raises(ValueError, match="must be a directory"):
            BrowserConfig(download_dir=str(file_path))

    def test_download_dir_valid_directory(self, tmp_path):
        """Test that valid directory is accepted."""
        config = BrowserConfig(download_dir=str(tmp_path))
        assert config.download_dir == str(tmp_path)

    def test_download_dir_nonexistent_allowed(self):
        """Test that non-existent directory is allowed (will be created)."""
        config = BrowserConfig(download_dir="/tmp/nonexistent_test_dir_12345")
        assert config.download_dir == "/tmp/nonexistent_test_dir_12345"
