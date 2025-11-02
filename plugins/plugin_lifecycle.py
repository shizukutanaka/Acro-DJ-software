# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Plugin Lifecycle Manager for Acro DJ Mixer

Provides:
- Complete plugin lifecycle management
- Plugin loading, initialization, execution, unloading
- Plugin dependency resolution
- Plugin health monitoring
- Plugin crash recovery
- Plugin hot reload support
"""

import logging
import threading
import traceback
from pathlib import Path
from typing import Dict, Optional, List, Callable, Tuple, Any
from dataclasses import dataclass, asdict, field
from enum import Enum
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class PluginState(Enum):
    """Plugin execution state."""
    NOT_LOADED = "not_loaded"
    LOADING = "loading"
    LOADED = "loaded"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    UNLOADING = "unloading"
    UNLOADED = "unloaded"


@dataclass
class PluginInfo:
    """Information about a loaded plugin."""
    plugin_id: str
    name: str
    version: str
    author: str
    state: PluginState
    loaded_at: str = ""
    initialized_at: str = ""
    last_error: Optional[str] = None
    error_count: int = 0
    execution_count: int = 0
    uptime_seconds: float = 0.0

    def to_dict(self) -> dict:
        return {
            'plugin_id': self.plugin_id,
            'name': self.name,
            'version': self.version,
            'author': self.author,
            'state': self.state.value,
            'loaded_at': self.loaded_at,
            'initialized_at': self.initialized_at,
            'last_error': self.last_error,
            'error_count': self.error_count,
            'execution_count': self.execution_count,
            'uptime_seconds': self.uptime_seconds,
        }


@dataclass
class PluginStartupConfig:
    """Configuration for plugin startup."""
    auto_initialize: bool = True
    auto_recover: bool = True
    max_restart_attempts: int = 3
    restart_delay_ms: int = 1000
    enable_monitoring: bool = True
    sandbox: bool = False


class PluginLifecycleManager:
    """Manages complete plugin lifecycle."""

    def __init__(
        self,
        plugin_dir: Optional[str] = None,
        default_config: Optional[PluginStartupConfig] = None
    ):
        """Initialize lifecycle manager.

        Args:
            plugin_dir: Directory containing plugins
            default_config: Default startup configuration
        """
        self.plugin_dir = Path(plugin_dir) if plugin_dir else Path.cwd() / 'plugins'
        self.default_config = default_config or PluginStartupConfig()

        # Plugin registry
        self.plugins: Dict[str, Any] = {}
        self.plugin_info: Dict[str, PluginInfo] = {}
        self.plugin_instances: Dict[str, Any] = {}

        # Lifecycle hooks
        self.on_load_callbacks: List[Callable] = []
        self.on_init_callbacks: List[Callable] = []
        self.on_error_callbacks: List[Callable] = []
        self.on_unload_callbacks: List[Callable] = []

        # Restart tracking
        self.restart_counts: Dict[str, int] = {}
        self.restart_timers: Dict[str, threading.Timer] = {}

        # Thread lock
        self.lock = threading.RLock()

        # Monitoring
        self.performance_data: Dict[str, List[float]] = {}

    def register_plugin(self, plugin_module: Any) -> Tuple[bool, str]:
        """Register a plugin module.

        Args:
            plugin_module: Plugin module with metadata

        Returns:
            Tuple of (success, message)
        """
        try:
            # Extract metadata
            if not hasattr(plugin_module, 'PLUGIN_METADATA'):
                return False, "Missing PLUGIN_METADATA"

            metadata = plugin_module.PLUGIN_METADATA

            plugin_id = metadata.get('plugin_id', metadata.get('name', 'unknown'))

            with self.lock:
                if plugin_id in self.plugins:
                    return False, f"Plugin already registered: {plugin_id}"

                self.plugins[plugin_id] = plugin_module
                self.plugin_info[plugin_id] = PluginInfo(
                    plugin_id=plugin_id,
                    name=metadata.get('name', plugin_id),
                    version=metadata.get('version', '1.0.0'),
                    author=metadata.get('author', 'Unknown'),
                    state=PluginState.NOT_LOADED
                )
                self.restart_counts[plugin_id] = 0

            logger.info(f"Registered plugin: {plugin_id}")
            return True, f"Registered {plugin_id}"

        except Exception as e:
            logger.error(f"Failed to register plugin: {e}")
            return False, str(e)

    def load_plugin(
        self,
        plugin_id: str,
        config: Optional[PluginStartupConfig] = None
    ) -> Tuple[bool, str]:
        """Load and initialize a plugin.

        Args:
            plugin_id: Plugin identifier
            config: Startup configuration

        Returns:
            Tuple of (success, message)
        """
        config = config or self.default_config

        with self.lock:
            if plugin_id not in self.plugins:
                return False, f"Plugin not registered: {plugin_id}"

            if self.plugin_info[plugin_id].state != PluginState.NOT_LOADED:
                return False, f"Plugin already loaded: {plugin_id}"

            self.plugin_info[plugin_id].state = PluginState.LOADING

        try:
            # Get plugin module
            plugin_module = self.plugins[plugin_id]

            # Create instance
            if hasattr(plugin_module, 'create_plugin'):
                instance = plugin_module.create_plugin()
            else:
                return False, "Plugin missing create_plugin() function"

            with self.lock:
                self.plugin_instances[plugin_id] = instance
                self.plugin_info[plugin_id].state = PluginState.LOADED
                self.plugin_info[plugin_id].loaded_at = datetime.now().isoformat()

            # Call load callbacks
            for callback in self.on_load_callbacks:
                try:
                    callback(plugin_id, instance)
                except Exception as e:
                    logger.error(f"Error in load callback: {e}")

            # Auto-initialize if configured
            if config.auto_initialize:
                return self.initialize_plugin(plugin_id, config)

            logger.info(f"Loaded plugin: {plugin_id}")
            return True, f"Loaded {plugin_id}"

        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_id}: {e}")
            with self.lock:
                self.plugin_info[plugin_id].state = PluginState.ERROR
                self.plugin_info[plugin_id].last_error = str(e)
                self.plugin_info[plugin_id].error_count += 1

            return False, str(e)

    def initialize_plugin(
        self,
        plugin_id: str,
        config: Optional[PluginStartupConfig] = None
    ) -> Tuple[bool, str]:
        """Initialize a loaded plugin.

        Args:
            plugin_id: Plugin identifier
            config: Startup configuration

        Returns:
            Tuple of (success, message)
        """
        config = config or self.default_config

        with self.lock:
            if plugin_id not in self.plugin_instances:
                return False, f"Plugin not loaded: {plugin_id}"

            self.plugin_info[plugin_id].state = PluginState.INITIALIZING

        try:
            instance = self.plugin_instances[plugin_id]

            # Call initialize if exists
            if hasattr(instance, 'initialize'):
                instance.initialize({})

            with self.lock:
                self.plugin_info[plugin_id].state = PluginState.READY
                self.plugin_info[plugin_id].initialized_at = datetime.now().isoformat()

            # Call init callbacks
            for callback in self.on_init_callbacks:
                try:
                    callback(plugin_id, instance)
                except Exception as e:
                    logger.error(f"Error in init callback: {e}")

            logger.info(f"Initialized plugin: {plugin_id}")
            return True, f"Initialized {plugin_id}"

        except Exception as e:
            logger.error(f"Failed to initialize plugin {plugin_id}: {e}")
            with self.lock:
                self.plugin_info[plugin_id].state = PluginState.ERROR
                self.plugin_info[plugin_id].last_error = str(e)
                self.plugin_info[plugin_id].error_count += 1

            # Auto-recovery
            if config.auto_recover and self.restart_counts.get(plugin_id, 0) < config.max_restart_attempts:
                self._schedule_restart(plugin_id, config)

            return False, str(e)

    def unload_plugin(self, plugin_id: str) -> Tuple[bool, str]:
        """Unload a plugin.

        Args:
            plugin_id: Plugin identifier

        Returns:
            Tuple of (success, message)
        """
        with self.lock:
            if plugin_id not in self.plugin_instances:
                return False, f"Plugin not loaded: {plugin_id}"

            self.plugin_info[plugin_id].state = PluginState.UNLOADING

        try:
            instance = self.plugin_instances[plugin_id]

            # Call shutdown if exists
            if hasattr(instance, 'shutdown'):
                instance.shutdown()

            with self.lock:
                del self.plugin_instances[plugin_id]
                self.plugin_info[plugin_id].state = PluginState.UNLOADED

            # Call unload callbacks
            for callback in self.on_unload_callbacks:
                try:
                    callback(plugin_id)
                except Exception as e:
                    logger.error(f"Error in unload callback: {e}")

            logger.info(f"Unloaded plugin: {plugin_id}")
            return True, f"Unloaded {plugin_id}"

        except Exception as e:
            logger.error(f"Failed to unload plugin {plugin_id}: {e}")
            return False, str(e)

    def execute_plugin_method(
        self,
        plugin_id: str,
        method_name: str,
        *args,
        **kwargs
    ) -> Tuple[bool, Any]:
        """Execute a plugin method.

        Args:
            plugin_id: Plugin identifier
            method_name: Method name
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Tuple of (success, result)
        """
        with self.lock:
            if plugin_id not in self.plugin_instances:
                return False, "Plugin not loaded"

            instance = self.plugin_instances[plugin_id]
            self.plugin_info[plugin_id].execution_count += 1

        try:
            if not hasattr(instance, method_name):
                return False, f"Method not found: {method_name}"

            method = getattr(instance, method_name)

            # Execute method
            result = method(*args, **kwargs)

            return True, result

        except Exception as e:
            logger.error(f"Error executing {method_name} in {plugin_id}: {e}")
            with self.lock:
                self.plugin_info[plugin_id].last_error = str(e)
                self.plugin_info[plugin_id].error_count += 1

            return False, str(e)

    def pause_plugin(self, plugin_id: str) -> Tuple[bool, str]:
        """Pause a plugin.

        Args:
            plugin_id: Plugin identifier

        Returns:
            Tuple of (success, message)
        """
        with self.lock:
            if plugin_id not in self.plugin_instances:
                return False, "Plugin not loaded"

            self.plugin_info[plugin_id].state = PluginState.PAUSED

        logger.info(f"Paused plugin: {plugin_id}")
        return True, f"Paused {plugin_id}"

    def resume_plugin(self, plugin_id: str) -> Tuple[bool, str]:
        """Resume a paused plugin.

        Args:
            plugin_id: Plugin identifier

        Returns:
            Tuple of (success, message)
        """
        with self.lock:
            if plugin_id not in self.plugin_instances:
                return False, "Plugin not loaded"

            self.plugin_info[plugin_id].state = PluginState.READY

        logger.info(f"Resumed plugin: {plugin_id}")
        return True, f"Resumed {plugin_id}"

    def get_plugin_info(self, plugin_id: str) -> Optional[PluginInfo]:
        """Get plugin information.

        Args:
            plugin_id: Plugin identifier

        Returns:
            PluginInfo or None
        """
        with self.lock:
            return self.plugin_info.get(plugin_id)

    def get_all_plugin_info(self) -> Dict[str, PluginInfo]:
        """Get information for all plugins.

        Returns:
            Dictionary of PluginInfo objects
        """
        with self.lock:
            return {pid: info.to_dict() for pid, info in self.plugin_info.items()}

    def get_loaded_plugins(self) -> List[str]:
        """Get list of loaded plugins.

        Returns:
            List of plugin IDs
        """
        with self.lock:
            return [pid for pid, info in self.plugin_info.items()
                   if info.state in [PluginState.READY, PluginState.RUNNING]]

    def get_failed_plugins(self) -> List[str]:
        """Get list of failed plugins.

        Returns:
            List of plugin IDs
        """
        with self.lock:
            return [pid for pid, info in self.plugin_info.items()
                   if info.state == PluginState.ERROR]

    def shutdown_all(self) -> Tuple[int, int]:
        """Shutdown all plugins.

        Returns:
            Tuple of (unloaded_count, failed_count)
        """
        unloaded = 0
        failed = 0

        plugin_ids = list(self.plugin_instances.keys())

        for plugin_id in plugin_ids:
            success, msg = self.unload_plugin(plugin_id)

            if success:
                unloaded += 1
            else:
                failed += 1

        logger.info(f"Shutdown all plugins: {unloaded} unloaded, {failed} failed")
        return unloaded, failed

    def _schedule_restart(
        self,
        plugin_id: str,
        config: PluginStartupConfig
    ) -> None:
        """Schedule plugin restart.

        Args:
            plugin_id: Plugin identifier
            config: Startup configuration
        """
        with self.lock:
            self.restart_counts[plugin_id] = self.restart_counts.get(plugin_id, 0) + 1
            count = self.restart_counts[plugin_id]

        logger.warning(
            f"Scheduling restart for {plugin_id} "
            f"(attempt {count}/{config.max_restart_attempts})"
        )

        def do_restart():
            self.unload_plugin(plugin_id)
            self.load_plugin(plugin_id, config)

        timer = threading.Timer(config.restart_delay_ms / 1000.0, do_restart)
        timer.daemon = True
        timer.start()

        with self.lock:
            self.restart_timers[plugin_id] = timer

    def on_load(self, callback: Callable) -> None:
        """Register load callback.

        Args:
            callback: Callback function
        """
        self.on_load_callbacks.append(callback)

    def on_initialize(self, callback: Callable) -> None:
        """Register initialization callback.

        Args:
            callback: Callback function
        """
        self.on_init_callbacks.append(callback)

    def on_error(self, callback: Callable) -> None:
        """Register error callback.

        Args:
            callback: Callback function
        """
        self.on_error_callbacks.append(callback)

    def on_unload(self, callback: Callable) -> None:
        """Register unload callback.

        Args:
            callback: Callback function
        """
        self.on_unload_callbacks.append(callback)

    def get_lifecycle_stats(self) -> Dict[str, Any]:
        """Get lifecycle statistics.

        Returns:
            Dictionary with statistics
        """
        with self.lock:
            total = len(self.plugins)
            loaded = len(self.plugin_instances)
            ready = len([p for p in self.plugin_info.values()
                        if p.state == PluginState.READY])
            error = len([p for p in self.plugin_info.values()
                        if p.state == PluginState.ERROR])

        return {
            'total_registered': total,
            'total_loaded': loaded,
            'total_ready': ready,
            'total_error': error,
            'restart_attempts': sum(self.restart_counts.values()),
        }

    def export_lifecycle_data(self, export_path: str) -> Tuple[bool, str]:
        """Export lifecycle data to file.

        Args:
            export_path: Path to export file

        Returns:
            Tuple of (success, message)
        """
        try:
            with self.lock:
                data = {
                    'export_date': datetime.now().isoformat(),
                    'plugins': self.get_all_plugin_info(),
                    'stats': self.get_lifecycle_stats(),
                }

            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Exported lifecycle data to {export_path}")
            return True, f"Exported lifecycle data"

        except Exception as e:
            logger.error(f"Failed to export lifecycle data: {e}")
            return False, str(e)
