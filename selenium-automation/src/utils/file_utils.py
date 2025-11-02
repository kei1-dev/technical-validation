"""
File operation utilities.

This module provides utilities for saving and loading data files
in various formats (JSON, CSV).
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

import pandas as pd


logger = logging.getLogger(__name__)


def save_json(data: Dict[str, Any], filepath: Path) -> bool:
    """
    Save data to JSON file.

    Args:
        data: Dictionary data to save
        filepath: Path to save the JSON file

    Returns:
        True if save successful, False otherwise

    Examples:
        >>> data = {"name": "test", "value": 42}
        >>> save_json(data, Path("output/test.json"))
        True
    """
    try:
        # Ensure parent directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Save JSON with proper formatting
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.debug(f"Saved JSON file: {filepath}")
        return True

    except Exception as e:
        logger.error(f"Failed to save JSON file {filepath}: {e}", exc_info=True)
        return False


def load_json(filepath: Path) -> Optional[Dict[str, Any]]:
    """
    Load data from JSON file.

    Args:
        filepath: Path to the JSON file

    Returns:
        Loaded data dictionary, or None if load failed

    Examples:
        >>> data = load_json(Path("output/test.json"))
        >>> if data:
        ...     print(data["name"])
    """
    try:
        if not filepath.exists():
            logger.warning(f"JSON file not found: {filepath}")
            return None

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        logger.debug(f"Loaded JSON file: {filepath}")
        return data

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in file {filepath}: {e}")
        return None

    except Exception as e:
        logger.error(f"Failed to load JSON file {filepath}: {e}", exc_info=True)
        return None


def save_csv(df: pd.DataFrame, filepath: Path) -> bool:
    """
    Save DataFrame to CSV file.

    Args:
        df: Pandas DataFrame to save
        filepath: Path to save the CSV file

    Returns:
        True if save successful, False otherwise

    Examples:
        >>> df = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
        >>> save_csv(df, Path("output/test.csv"))
        True
    """
    try:
        # Ensure parent directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Save CSV with UTF-8 encoding
        df.to_csv(filepath, index=False, encoding='utf-8')

        logger.debug(f"Saved CSV file: {filepath}")
        return True

    except Exception as e:
        logger.error(f"Failed to save CSV file {filepath}: {e}", exc_info=True)
        return False


def load_csv(filepath: Path) -> Optional[pd.DataFrame]:
    """
    Load DataFrame from CSV file.

    Args:
        filepath: Path to the CSV file

    Returns:
        Loaded DataFrame, or None if load failed

    Examples:
        >>> df = load_csv(Path("output/test.csv"))
        >>> if df is not None:
        ...     print(df.head())
    """
    try:
        if not filepath.exists():
            logger.warning(f"CSV file not found: {filepath}")
            return None

        df = pd.read_csv(filepath, encoding='utf-8')

        logger.debug(f"Loaded CSV file: {filepath}")
        return df

    except Exception as e:
        logger.error(f"Failed to load CSV file {filepath}: {e}", exc_info=True)
        return None


def generate_filename(prefix: str, extension: str) -> str:
    """
    Generate timestamped filename.

    Args:
        prefix: Filename prefix
        extension: File extension (without dot)

    Returns:
        Filename with timestamp (e.g., "prefix_20251101_103045.ext")

    Examples:
        >>> filename = generate_filename("screenshot", "png")
        >>> # Returns something like: "screenshot_20251101_103045.png"
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{extension}"


def save_json_with_integrity(
    data: Dict[str, Any],
    filepath: Path
) -> bool:
    """
    Save JSON with integrity metadata (checksum).

    Args:
        data: Dictionary data to save
        filepath: Path to save the JSON file

    Returns:
        True if save successful, False otherwise

    Note:
        This wraps the data with integrity metadata including
        a SHA-256 checksum for data validation.
    """
    import hashlib

    try:
        # Compute checksum
        serialized = json.dumps(data, sort_keys=True, ensure_ascii=False)
        checksum = hashlib.sha256(serialized.encode('utf-8')).hexdigest()

        # Wrap data with integrity metadata
        wrapped = {
            "integrity": {
                "checksum": checksum,
                "algorithm": "sha256",
                "timestamp": datetime.now().isoformat()
            },
            "data": data
        }

        return save_json(wrapped, filepath)

    except Exception as e:
        logger.error(f"Failed to save JSON with integrity: {e}", exc_info=True)
        return False


def verify_json_integrity(filepath: Path) -> bool:
    """
    Verify integrity of JSON file with checksum.

    Args:
        filepath: Path to the JSON file with integrity metadata

    Returns:
        True if integrity check passes, False otherwise
    """
    import hashlib

    try:
        wrapped = load_json(filepath)
        if not wrapped or "integrity" not in wrapped or "data" not in wrapped:
            logger.error("Invalid integrity-protected JSON format")
            return False

        expected_checksum = wrapped["integrity"]["checksum"]
        algorithm = wrapped["integrity"].get("algorithm", "sha256")
        data = wrapped["data"]

        # Compute checksum of data
        serialized = json.dumps(data, sort_keys=True, ensure_ascii=False)
        computed_checksum = hashlib.new(algorithm, serialized.encode('utf-8')).hexdigest()

        if computed_checksum != expected_checksum:
            logger.error("Integrity check failed: checksum mismatch")
            return False

        logger.debug("Integrity check passed")
        return True

    except Exception as e:
        logger.error(f"Failed to verify JSON integrity: {e}", exc_info=True)
        return False
