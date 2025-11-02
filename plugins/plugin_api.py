# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Plugin API for Acro DJ Mixer v3.x

Allows third-party developers to create custom plugins for:
- Audio effects
- Library tools
- Visualization
- MIDI controllers
- Analysis tools

This module provides the base classes and interfaces for plugin development.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import numpy as np
import logging

logger = logging.getLogger(__name__)


class PluginCategory(Enum):
    """Plugin categories."""
    AUDIO_EFFECT = "audio_effect"
    LIBRARY_TOOL = "library_tool"
    VISUALIZER = "visualizer"
    MIDI_CONTROLLER = "midi_controller"
    ANALYZER = "analyzer"
    UTILITY = "utility"


@dataclass
class PluginMetadata:
    """Metadata for a plugin."""
    name: str                      # Plugin name
    version: str                   # Version (e.g., "1.0.0")
    author: str                    # Author name
    description: str               # Short description
    category: PluginCategory       # Plugin category
    homepage: Optional[str] = None # Website/documentation URL
    license: str = "MIT"           # License type
    requirements: List[str] = None # Dependencies (e.g., ["numpy>=1.20"])

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'version': self.version,
            'author': self.author,
            'description': self.description,
            'category': self.category.value,
            'homepage': self.homepage,
            'license': self.license,
            'requirements': self.requirements or [],
        }


@dataclass
class Parameter:
    """Represents a plugin parameter."""
    name: str
    value_type: type  # int, float, bool, str
    default_value: Any
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    description: str = ""
    ui_type: str = "slider"  # slider, knob, toggle, choice, text
    options: Optional[List[str]] = None  # For choice type

    def validate(self, value: Any) -> bool:
        """Check if value is valid."""
        if not isinstance(value, self.value_type):
            return False

        if self.min_value is not None and value < self.min_value:
            return False

        if self.max_value is not None and value > self.max_value:
            return False

        if self.options and value not in self.options:
            return False

        return True

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'value_type': self.value_type.__name__,
            'default_value': self.default_value,
            'min_value': self.min_value,
            'max_value': self.max_value,
            'description': self.description,
            'ui_type': self.ui_type,
            'options': self.options,
        }


class AcroPlugin(ABC):
    """Base class for all Acro plugins."""

    def __init__(self, metadata: PluginMetadata):
        """Initialize plugin.

        Args:
            metadata: Plugin metadata
        """
        self.metadata = metadata
        self.parameters: Dict[str, Parameter] = {}
        self._parameter_values: Dict[str, Any] = {}
        self.enabled = True

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the plugin with configuration.

        Args:
            config: Configuration dictionary
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Shutdown and cleanup the plugin."""
        pass

    def register_parameter(self, parameter: Parameter) -> None:
        """Register a plugin parameter.

        Args:
            parameter: Parameter object
        """
        self.parameters[parameter.name] = parameter
        self._parameter_values[parameter.name] = parameter.default_value

    def set_parameter(self, name: str, value: Any) -> bool:
        """Set a parameter value.

        Args:
            name: Parameter name
            value: New value

        Returns:
            True if successful, False if invalid
        """
        if name not in self.parameters:
            logger.warning(f"Parameter '{name}' not found")
            return False

        param = self.parameters[name]
        if not param.validate(value):
            logger.warning(f"Invalid value for parameter '{name}': {value}")
            return False

        self._parameter_values[name] = value
        return True

    def get_parameter(self, name: str) -> Any:
        """Get a parameter value.

        Args:
            name: Parameter name

        Returns:
            Parameter value, or None if not found
        """
        return self._parameter_values.get(name)

    def get_all_parameters(self) -> Dict[str, Any]:
        """Get all parameter values."""
        return self._parameter_values.copy()

    def export_state(self) -> Dict[str, Any]:
        """Export plugin state for saving.

        Returns:
            Dictionary with plugin state
        """
        return {
            'metadata': self.metadata.to_dict(),
            'parameters': self._parameter_values.copy(),
            'enabled': self.enabled,
        }

    def import_state(self, state: Dict[str, Any]) -> None:
        """Import plugin state from saved file.

        Args:
            state: Dictionary with plugin state
        """
        if 'parameters' in state:
            for name, value in state['parameters'].items():
                self.set_parameter(name, value)

        if 'enabled' in state:
            self.enabled = state['enabled']


class AudioEffectPlugin(AcroPlugin):
    """Base class for audio effect plugins."""

    def __init__(self, metadata: PluginMetadata, sample_rate: int = 44100):
        """Initialize audio effect plugin.

        Args:
            metadata: Plugin metadata
            sample_rate: Audio sample rate in Hz
        """
        super().__init__(metadata)
        self.sample_rate = sample_rate

    @abstractmethod
    def process_audio(self, audio: np.ndarray) -> np.ndarray:
        """Process audio through the effect.

        Args:
            audio: Input audio signal (numpy array)

        Returns:
            Processed audio signal
        """
        pass

    def process(self, audio: np.ndarray) -> np.ndarray:
        """Process audio (called by host).

        Args:
            audio: Input audio signal

        Returns:
            Processed audio signal
        """
        if not self.enabled or len(audio) == 0:
            return audio

        return self.process_audio(audio)


class LibraryToolPlugin(AcroPlugin):
    """Base class for library management plugins."""

    @abstractmethod
    def analyze_track(self, file_path: str) -> Dict[str, Any]:
        """Analyze a single track.

        Args:
            file_path: Path to audio file

        Returns:
            Dictionary with analysis results
        """
        pass

    @abstractmethod
    def analyze_library(self, folder_path: str) -> Dict[str, Dict[str, Any]]:
        """Analyze entire library.

        Args:
            folder_path: Path to library folder

        Returns:
            Dictionary mapping filenames to analysis results
        """
        pass


class VisualizerPlugin(AcroPlugin):
    """Base class for visualization plugins."""

    @abstractmethod
    def get_visualization_data(
        self,
        audio: np.ndarray,
        sample_rate: int
    ) -> Dict[str, Any]:
        """Generate visualization data from audio.

        Args:
            audio: Input audio signal
            sample_rate: Sample rate in Hz

        Returns:
            Dictionary with visualization data
        """
        pass


class MidiControllerPlugin(AcroPlugin):
    """Base class for MIDI controller plugins."""

    def __init__(self, metadata: PluginMetadata):
        """Initialize MIDI controller plugin.

        Args:
            metadata: Plugin metadata
        """
        super().__init__(metadata)
        self._on_control_change: Optional[Callable] = None
        self._on_note: Optional[Callable] = None

    def set_on_control_change(self, callback: Callable) -> None:
        """Set callback for MIDI CC events.

        Args:
            callback: Function(channel, cc_number, value)
        """
        self._on_control_change = callback

    def set_on_note(self, callback: Callable) -> None:
        """Set callback for MIDI note events.

        Args:
            callback: Function(channel, note_number, velocity, is_note_on)
        """
        self._on_note = callback

    @abstractmethod
    def get_controllers(self) -> List[Dict[str, Any]]:
        """Get list of available controllers.

        Returns:
            List of controller descriptions
        """
        pass

    def on_control_change(
        self,
        channel: int,
        cc_number: int,
        value: int
    ) -> None:
        """Handle MIDI CC event.

        Args:
            channel: MIDI channel (0-15)
            cc_number: CC number (0-127)
            value: CC value (0-127)
        """
        if self._on_control_change:
            self._on_control_change(channel, cc_number, value)

    def on_note(
        self,
        channel: int,
        note_number: int,
        velocity: int,
        is_note_on: bool
    ) -> None:
        """Handle MIDI note event.

        Args:
            channel: MIDI channel (0-15)
            note_number: Note number (0-127)
            velocity: Velocity (0-127)
            is_note_on: True for note on, False for note off
        """
        if self._on_note:
            self._on_note(channel, note_number, velocity, is_note_on)


class AnalyzerPlugin(AcroPlugin):
    """Base class for audio analysis plugins."""

    @abstractmethod
    def analyze(self, audio: np.ndarray, sample_rate: int) -> Dict[str, Any]:
        """Analyze audio signal.

        Args:
            audio: Input audio signal
            sample_rate: Sample rate in Hz

        Returns:
            Dictionary with analysis results
        """
        pass


class PluginManager:
    """Manages plugin loading and lifecycle."""

    def __init__(self):
        """Initialize plugin manager."""
        self.plugins: Dict[str, AcroPlugin] = {}
        self._plugin_categories: Dict[PluginCategory, List[str]] = {}

    def register_plugin(self, plugin: AcroPlugin) -> None:
        """Register a plugin.

        Args:
            plugin: Plugin instance
        """
        plugin_name = plugin.metadata.name
        self.plugins[plugin_name] = plugin

        # Register by category
        category = plugin.metadata.category
        if category not in self._plugin_categories:
            self._plugin_categories[category] = []

        self._plugin_categories[category].append(plugin_name)

        logger.info(f"Registered plugin: {plugin_name} v{plugin.metadata.version}")

    def unregister_plugin(self, plugin_name: str) -> None:
        """Unregister a plugin.

        Args:
            plugin_name: Name of plugin to unregister
        """
        if plugin_name in self.plugins:
            plugin = self.plugins[plugin_name]
            plugin.shutdown()
            del self.plugins[plugin_name]

            # Remove from categories
            for plugins_list in self._plugin_categories.values():
                if plugin_name in plugins_list:
                    plugins_list.remove(plugin_name)

            logger.info(f"Unregistered plugin: {plugin_name}")

    def get_plugin(self, plugin_name: str) -> Optional[AcroPlugin]:
        """Get a plugin by name.

        Args:
            plugin_name: Name of plugin

        Returns:
            Plugin instance, or None if not found
        """
        return self.plugins.get(plugin_name)

    def get_plugins_by_category(self, category: PluginCategory) -> List[AcroPlugin]:
        """Get all plugins in a category.

        Args:
            category: Plugin category

        Returns:
            List of plugin instances
        """
        plugin_names = self._plugin_categories.get(category, [])
        return [self.plugins[name] for name in plugin_names if name in self.plugins]

    def list_plugins(self) -> Dict[str, Dict[str, Any]]:
        """List all registered plugins.

        Returns:
            Dictionary mapping plugin names to metadata
        """
        return {
            name: plugin.metadata.to_dict()
            for name, plugin in self.plugins.items()
        }

    def shutdown_all(self) -> None:
        """Shutdown all plugins."""
        for plugin in self.plugins.values():
            try:
                plugin.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down plugin: {e}")


# Plugin discovery and loading utilities

def discover_plugins(plugin_folder: str) -> List[PluginMetadata]:
    """Discover plugins in a folder.

    Args:
        plugin_folder: Path to folder containing plugins

    Returns:
        List of discovered plugin metadata
    """
    from pathlib import Path
    import importlib.util

    plugins = []
    plugin_path = Path(plugin_folder)

    if not plugin_path.is_dir():
        logger.warning(f"Plugin folder not found: {plugin_folder}")
        return plugins

    # Find all Python files
    for py_file in plugin_path.glob("*.py"):
        if py_file.name.startswith("_"):
            continue

        try:
            # Load module
            spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Look for plugin metadata
            if hasattr(module, 'PLUGIN_METADATA'):
                plugins.append(module.PLUGIN_METADATA)

        except Exception as e:
            logger.warning(f"Failed to load plugin from {py_file}: {e}")

    return plugins


def load_plugin(plugin_path: str) -> Optional[AcroPlugin]:
    """Load a plugin from a file.

    Args:
        plugin_path: Path to plugin file

    Returns:
        Plugin instance, or None if failed
    """
    import importlib.util
    from pathlib import Path

    try:
        path = Path(plugin_path)
        spec = importlib.util.spec_from_file_location(path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if hasattr(module, 'create_plugin'):
            return module.create_plugin()

        logger.warning(f"Plugin {path} does not have create_plugin() function")
        return None

    except Exception as e:
        logger.error(f"Failed to load plugin from {plugin_path}: {e}")
        return None
