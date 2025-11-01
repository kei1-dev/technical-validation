"""
Schema versioning for data structure evolution.

This module provides versioning support for data structures
to enable backward compatibility and data migration.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any


class SchemaVersion(Enum):
    """
    Schema version identifiers.

    Versions:
        V1_0: Initial version
        V1_1: Minor updates (added optional fields)
        V2_0: Major update (breaking changes)
    """

    V1_0 = "1.0"
    V1_1 = "1.1"
    V2_0 = "2.0"


@dataclass
class VersionedData:
    """
    Data with version information.

    Attributes:
        schema_version: Version identifier
        data: Actual data content

    Examples:
        >>> versioned = VersionedData(
        ...     schema_version=SchemaVersion.V1_0.value,
        ...     data={"lessons": [...]}
        ... )
    """

    schema_version: str
    data: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary format.

        Returns:
            Dictionary with schema_version and data
        """
        return {
            "schema_version": self.schema_version,
            "data": self.data
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'VersionedData':
        """
        Create instance from dictionary.

        Args:
            d: Dictionary with schema_version and data

        Returns:
            VersionedData instance
        """
        return cls(
            schema_version=d.get("schema_version", SchemaVersion.V1_0.value),
            data=d.get("data", {})
        )

    @property
    def version_enum(self) -> SchemaVersion:
        """
        Get schema version as enum.

        Returns:
            SchemaVersion enum value
        """
        return SchemaVersion(self.schema_version)
