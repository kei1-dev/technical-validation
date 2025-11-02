"""
Dependency Injection Container.

This module provides a simple DI container for managing dependencies
and promoting loose coupling.
"""

import logging
from typing import Dict, Type, Callable, Any, Optional


logger = logging.getLogger(__name__)


class DIContainer:
    """
    Simple dependency injection container.

    Supports:
    - Service registration with factory functions
    - Singleton pattern for shared instances
    - Service resolution
    - Clear error messages for missing services

    Examples:
        >>> # Create container
        >>> container = DIContainer()

        >>> # Register services
        >>> container.register(Logger, lambda: setup_logger("app"))
        >>> container.register(Config, lambda: Config(), singleton=True)

        >>> # Resolve services
        >>> logger = container.resolve(Logger)
        >>> config = container.resolve(Config)

        >>> # Register with dependencies
        >>> def create_browser():
        ...     config = container.resolve(Config)
        ...     return Browser(headless=config.browser_headless)
        >>> container.register(Browser, create_browser)
    """

    def __init__(self):
        """Initialize empty container."""
        self._services: Dict[Type, Callable] = {}
        self._singletons: Dict[Type, Any] = {}
        self._singleton_flags: Dict[Type, bool] = {}

        logger.debug("DI Container initialized")

    def register(
        self,
        interface: Type,
        implementation: Callable,
        singleton: bool = False
    ):
        """
        Register a service in the container.

        Args:
            interface: Service interface or type
            implementation: Factory function that creates the service
            singleton: Whether to create a single shared instance

        Examples:
            >>> # Transient (new instance each time)
            >>> container.register(Logger, lambda: setup_logger())

            >>> # Singleton (shared instance)
            >>> container.register(Config, lambda: Config(), singleton=True)
        """
        self._services[interface] = implementation
        self._singleton_flags[interface] = singleton

        if singleton:
            self._singletons[interface] = None  # Lazy initialization

        logger.debug(
            f"Registered service: {interface.__name__} "
            f"(singleton={singleton})"
        )

    def resolve(self, interface: Type) -> Any:
        """
        Resolve a service from the container.

        Args:
            interface: Service interface or type to resolve

        Returns:
            Service instance

        Raises:
            ValueError: If service is not registered

        Examples:
            >>> config = container.resolve(Config)
            >>> browser = container.resolve(Browser)
        """
        # Check if service is registered
        if interface not in self._services:
            raise ValueError(
                f"Service not registered: {interface.__name__}. "
                f"Available services: {', '.join(s.__name__ for s in self._services.keys())}"
            )

        # Singleton: return cached instance or create new one
        if self._singleton_flags.get(interface, False):
            if self._singletons[interface] is None:
                logger.debug(f"Creating singleton instance: {interface.__name__}")
                self._singletons[interface] = self._services[interface]()
            return self._singletons[interface]

        # Transient: create new instance
        logger.debug(f"Creating transient instance: {interface.__name__}")
        return self._services[interface]()

    def is_registered(self, interface: Type) -> bool:
        """
        Check if a service is registered.

        Args:
            interface: Service interface or type

        Returns:
            True if service is registered
        """
        return interface in self._services

    def clear(self):
        """Clear all registered services."""
        self._services.clear()
        self._singletons.clear()
        self._singleton_flags.clear()
        logger.debug("DI Container cleared")

    def get_registered_services(self) -> list:
        """
        Get list of all registered service types.

        Returns:
            List of registered service type names
        """
        return [service.__name__ for service in self._services.keys()]


def configure_default_services(container: DIContainer):
    """
    Configure default services for the application.

    This is a convenience function that registers common services.
    Can be customized or extended as needed.

    Args:
        container: DI container to configure

    Examples:
        >>> container = DIContainer()
        >>> configure_default_services(container)
        >>> config = container.resolve(Config)
    """
    from .config import Config, config
    from .logger import setup_logger

    # Singleton services
    container.register(Config, lambda: config, singleton=True)

    container.register(
        logging.Logger,
        lambda: setup_logger(
            "terakoya_automation",
            level=logging.INFO
        ),
        singleton=True
    )

    logger.info("Default services configured")
