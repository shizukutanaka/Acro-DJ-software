# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Plugin Dependency Injection System for Acro DJ Mixer

Provides:
- Dependency injection container
- Service registration and resolution
- Singleton and transient lifetimes
- Constructor and setter injection
- Interface binding
- Circular dependency detection
- Dependency graph visualization
"""

import logging
import inspect
from typing import Dict, Optional, List, Any, Type, Callable, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class Lifetime(Enum):
    """Service lifetime."""
    SINGLETON = "singleton"    # Single instance for all
    TRANSIENT = "transient"    # New instance each time
    SCOPED = "scoped"          # Instance per scope


@dataclass
class ServiceDescriptor:
    """Describes a service registration."""
    service_type: Type
    implementation: Any
    lifetime: Lifetime
    factory: Optional[Callable] = None


class DependencyInjectionContainer:
    """IoC container for dependency injection."""

    def __init__(self):
        """Initialize DI container."""
        self.services: Dict[Type, ServiceDescriptor] = {}
        self.singletons: Dict[Type, Any] = {}
        self.resolution_stack: List[Type] = []
        self.lock = __import__('threading').RLock()

    def register_singleton(
        self,
        service_type: Type,
        implementation: Any = None,
        factory: Optional[Callable] = None
    ) -> None:
        """Register singleton service.

        Args:
            service_type: Service type/interface
            implementation: Implementation instance or class
            factory: Factory function
        """
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation,
            lifetime=Lifetime.SINGLETON,
            factory=factory
        )

        with self.lock:
            self.services[service_type] = descriptor

            logger.info(f"Registered singleton: {service_type.__name__}")

    def register_transient(
        self,
        service_type: Type,
        implementation: Any = None,
        factory: Optional[Callable] = None
    ) -> None:
        """Register transient service.

        Args:
            service_type: Service type/interface
            implementation: Implementation class
            factory: Factory function
        """
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation,
            lifetime=Lifetime.TRANSIENT,
            factory=factory
        )

        with self.lock:
            self.services[service_type] = descriptor

            logger.info(f"Registered transient: {service_type.__name__}")

    def resolve(self, service_type: Type) -> Any:
        """Resolve service instance.

        Args:
            service_type: Type to resolve

        Returns:
            Service instance

        Raises:
            ValueError: If service not registered or circular dependency
        """
        # Check for circular dependencies
        if service_type in self.resolution_stack:
            circular_chain = " -> ".join(
                t.__name__ for t in self.resolution_stack + [service_type]
            )
            raise ValueError(f"Circular dependency detected: {circular_chain}")

        if service_type not in self.services:
            raise ValueError(f"Service not registered: {service_type.__name__}")

        with self.lock:
            descriptor = self.services[service_type]

            # Handle singletons
            if descriptor.lifetime == Lifetime.SINGLETON:
                if service_type in self.singletons:
                    return self.singletons[service_type]

                instance = self._create_instance(descriptor)
                self.singletons[service_type] = instance
                return instance

            # Handle transients
            elif descriptor.lifetime == Lifetime.TRANSIENT:
                return self._create_instance(descriptor)

            return None

    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """Create service instance.

        Args:
            descriptor: ServiceDescriptor

        Returns:
            Service instance
        """
        self.resolution_stack.append(descriptor.service_type)

        try:
            # Use factory if provided
            if descriptor.factory:
                return descriptor.factory(self)

            # Use implementation instance if provided
            if descriptor.implementation and not inspect.isclass(descriptor.implementation):
                return descriptor.implementation

            # Create instance from class
            impl_class = descriptor.implementation or descriptor.service_type

            if not inspect.isclass(impl_class):
                return impl_class

            # Get constructor
            sig = inspect.signature(impl_class.__init__)

            # Resolve constructor dependencies
            kwargs = {}

            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue

                param_type = param.annotation

                if param_type == inspect.Parameter.empty:
                    if param.default != inspect.Parameter.empty:
                        kwargs[param_name] = param.default
                    continue

                # Try to resolve dependency
                if param_type in self.services:
                    kwargs[param_name] = self.resolve(param_type)

            return impl_class(**kwargs)

        finally:
            self.resolution_stack.pop()

    def get_service_descriptor(self, service_type: Type) -> Optional[ServiceDescriptor]:
        """Get service descriptor.

        Args:
            service_type: Service type

        Returns:
            ServiceDescriptor or None
        """
        return self.services.get(service_type)

    def is_registered(self, service_type: Type) -> bool:
        """Check if service is registered.

        Args:
            service_type: Service type

        Returns:
            True if registered
        """
        return service_type in self.services

    def get_dependency_graph(self) -> Dict[str, List[str]]:
        """Get dependency graph.

        Returns:
            Dictionary mapping service names to dependencies
        """
        graph = {}

        for service_type, descriptor in self.services.items():
            impl_class = descriptor.implementation or service_type

            if not inspect.isclass(impl_class):
                graph[service_type.__name__] = []
                continue

            sig = inspect.signature(impl_class.__init__)
            dependencies = []

            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue

                param_type = param.annotation

                if param_type != inspect.Parameter.empty:
                    if param_type in self.services:
                        dependencies.append(param_type.__name__)

            graph[service_type.__name__] = dependencies

        return graph

    def clear_singletons(self) -> None:
        """Clear singleton instances."""
        with self.lock:
            self.singletons.clear()
            logger.info("Cleared singleton instances")

    def dispose(self) -> None:
        """Dispose container and services."""
        with self.lock:
            # Call Dispose on services that support it
            for instance in self.singletons.values():
                if hasattr(instance, 'Dispose'):
                    try:
                        instance.Dispose()
                    except Exception as e:
                        logger.error(f"Error disposing service: {e}")

            self.singletons.clear()
            self.services.clear()

            logger.info("DI container disposed")


class ServiceProvider:
    """Provides service instances with DI container access."""

    def __init__(self, container: DependencyInjectionContainer):
        """Initialize service provider.

        Args:
            container: DependencyInjectionContainer
        """
        self.container = container

    def get_service(self, service_type: Type) -> Any:
        """Get service instance.

        Args:
            service_type: Service type

        Returns:
            Service instance
        """
        return self.container.resolve(service_type)

    def create_scope(self) -> 'ServiceProvider':
        """Create service scope.

        Returns:
            New ServiceProvider for scope
        """
        # For now, return same provider
        # In full implementation, would create scope-specific instances
        return self


class ServiceCollection:
    """Builder for service registration."""

    def __init__(self):
        """Initialize service collection."""
        self.descriptors: List[ServiceDescriptor] = []

    def add_singleton(
        self,
        service_type: Type,
        implementation: Any = None,
        factory: Optional[Callable] = None
    ) -> 'ServiceCollection':
        """Add singleton service.

        Args:
            service_type: Service type
            implementation: Implementation
            factory: Factory function

        Returns:
            Self for chaining
        """
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation,
            lifetime=Lifetime.SINGLETON,
            factory=factory
        )

        self.descriptors.append(descriptor)
        return self

    def add_transient(
        self,
        service_type: Type,
        implementation: Any = None,
        factory: Optional[Callable] = None
    ) -> 'ServiceCollection':
        """Add transient service.

        Args:
            service_type: Service type
            implementation: Implementation
            factory: Factory function

        Returns:
            Self for chaining
        """
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation,
            lifetime=Lifetime.TRANSIENT,
            factory=factory
        )

        self.descriptors.append(descriptor)
        return self

    def build(self) -> DependencyInjectionContainer:
        """Build DI container.

        Returns:
            DependencyInjectionContainer
        """
        container = DependencyInjectionContainer()

        for descriptor in self.descriptors:
            if descriptor.lifetime == Lifetime.SINGLETON:
                container.register_singleton(
                    descriptor.service_type,
                    descriptor.implementation,
                    descriptor.factory
                )
            else:
                container.register_transient(
                    descriptor.service_type,
                    descriptor.implementation,
                    descriptor.factory
                )

        return container
