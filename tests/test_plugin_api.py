# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""Tests for plugin architecture and plugin manager.

Tests for plugin discovery, loading, validation, and management.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch, MagicMock

import numpy as np
import pytest

from plugin_api import (
    AcroEffect,
    AcroController,
    AcroVisualizer,
    PluginManager,
    PluginInfo,
    PluginError,
)


class TestVolumeBoostEffect(AcroEffect):
    """Simple test effect."""

    name = "Test Volume"
    category = "Utility"
    version = "1.0.0"
    author = "Test"
    description = "Test effect"

    def process(self, audio: np.ndarray, sample_rate: int, **params: Any) -> np.ndarray:
        """Process audio."""
        gain = params.get("gain", 1.0)
        return (audio * gain).astype(np.float32)

    def get_parameters(self) -> dict[str, Any]:
        """Get parameters."""
        return {
            "gain": {
                "type": "float",
                "min": 0.0,
                "max": 2.0,
                "default": 1.0,
                "label": "Gain",
            }
        }

    def validate(self) -> bool:
        """Validate plugin."""
        return True


class TestEQEffect(AcroEffect):
    """Test EQ effect."""

    name = "Test EQ"
    category = "Filter"
    version = "1.0.0"
    author = "Test"
    description = "Test EQ effect"

    def process(self, audio: np.ndarray, sample_rate: int, **params: Any) -> np.ndarray:
        """Process audio."""
        return audio.astype(np.float32)

    def get_parameters(self) -> dict[str, Any]:
        """Get parameters."""
        return {
            "bass": {
                "type": "float",
                "min": -12.0,
                "max": 12.0,
                "default": 0.0,
                "label": "Bass",
                "unit": "dB",
            },
            "treble": {
                "type": "float",
                "min": -12.0,
                "max": 12.0,
                "default": 0.0,
                "label": "Treble",
                "unit": "dB",
            },
        }

    def validate(self) -> bool:
        """Validate plugin."""
        return True


class TestAcroEffectInterface:
    """Test AcroEffect base class."""

    def test_effect_properties(self):
        """Test effect properties."""
        effect = TestVolumeBoostEffect()

        assert effect.name == "Test Volume"
        assert effect.category == "Utility"
        assert effect.version == "1.0.0"
        assert effect.author == "Test"

    def test_effect_process(self, sample_audio: np.ndarray):
        """Test effect processing."""
        effect = TestVolumeBoostEffect()

        result = effect.process(sample_audio, 44100, gain=2.0)

        assert result.shape == sample_audio.shape
        assert result.dtype == np.float32
        assert np.max(np.abs(result)) > np.max(np.abs(sample_audio))

    def test_effect_get_parameters(self):
        """Test getting parameters."""
        effect = TestVolumeBoostEffect()
        params = effect.get_parameters()

        assert "gain" in params
        assert params["gain"]["type"] == "float"
        assert params["gain"]["min"] == 0.0
        assert params["gain"]["max"] == 2.0

    def test_effect_validate(self):
        """Test effect validation."""
        effect = TestVolumeBoostEffect()
        assert effect.validate() is True

    def test_effect_lifecycle(self):
        """Test effect lifecycle methods."""
        effect = TestVolumeBoostEffect()

        effect.on_enable()  # Should not raise
        effect.on_disable()  # Should not raise
        effect.reset_state()  # Should not raise


class TestAcroControllerInterface:
    """Test AcroController base class."""

    def test_controller_creation(self):
        """Test creating controller."""

        class TestController(AcroController):
            name = "Test"
            category = "MIDI"
            version = "1.0.0"
            author = "Test"
            description = "Test"

            def connect(self) -> bool:
                return True

            def disconnect(self) -> None:
                pass

            def process_input(self) -> dict[str, Any]:
                return {}

            def validate(self) -> bool:
                return True

        controller = TestController()
        assert controller.name == "Test"
        assert controller.validate() is True

    def test_controller_callbacks(self):
        """Test controller callback registration."""

        class TestController(AcroController):
            name = "Test"
            category = "MIDI"
            version = "1.0.0"
            author = "Test"
            description = "Test"

            def connect(self) -> bool:
                return True

            def disconnect(self) -> None:
                pass

            def process_input(self) -> dict[str, Any]:
                return {}

            def validate(self) -> bool:
                return True

        controller = TestController()
        callback_called = False

        def on_input(data):
            nonlocal callback_called
            callback_called = True

        controller.on_input(on_input)
        assert len(controller._callbacks) > 0


class TestAcroVisualizerInterface:
    """Test AcroVisualizer base class."""

    def test_visualizer_creation(self):
        """Test creating visualizer."""

        class TestVisualizer(AcroVisualizer):
            name = "Test"
            category = "Spectrum"
            version = "1.0.0"
            author = "Test"
            description = "Test"

            def update(self, audio: np.ndarray, sample_rate: int) -> None:
                pass

            def render(self) -> Any:
                return None

            def validate(self) -> bool:
                return True

        visualizer = TestVisualizer()
        assert visualizer.name == "Test"


class TestPluginInfo:
    """Test plugin information dataclass."""

    def test_plugin_info_creation(self):
        """Test creating plugin info."""
        info = PluginInfo(
            name="Test Plugin",
            category="Effect",
            version="1.0.0",
            author="Test Author",
            description="Test description",
            plugin_type="effect",
            entry_point="test:TestEffect",
        )

        assert info.name == "Test Plugin"
        assert info.version == "1.0.0"

    def test_plugin_info_to_dict(self):
        """Test converting to dictionary."""
        info = PluginInfo(
            name="Test",
            category="Effect",
            version="1.0.0",
            author="Test",
            description="Test",
            plugin_type="effect",
            entry_point="test:Test",
        )

        data = info.to_dict()
        assert isinstance(data, dict)
        assert data["name"] == "Test"


class TestPluginManager:
    """Test plugin manager."""

    def test_manager_creation(self):
        """Test creating plugin manager."""
        manager = PluginManager()
        assert manager is not None

    def test_register_effect(self):
        """Test registering effect."""
        manager = PluginManager()
        effect = TestVolumeBoostEffect()

        manager.register_effect("test_volume", effect)
        retrieved = manager.get_effect("test_volume")

        assert retrieved is effect

    def test_list_effects(self):
        """Test listing effects."""
        manager = PluginManager()
        manager.register_effect("volume", TestVolumeBoostEffect())
        manager.register_effect("eq", TestEQEffect())

        effects = manager.list_effects()
        assert "volume" in effects
        assert "eq" in effects

    def test_list_effects_by_category(self):
        """Test listing effects by category."""
        manager = PluginManager()
        manager.register_effect("volume", TestVolumeBoostEffect())
        manager.register_effect("eq", TestEQEffect())

        utility_effects = manager.list_effects(category="Utility")
        filter_effects = manager.list_effects(category="Filter")

        assert "volume" in utility_effects
        assert "eq" in filter_effects

    def test_get_nonexistent_effect(self):
        """Test getting nonexistent effect."""
        manager = PluginManager()
        effect = manager.get_effect("nonexistent")

        assert effect is None

    def test_remove_effect(self):
        """Test removing effect."""
        manager = PluginManager()
        manager.register_effect("volume", TestVolumeBoostEffect())

        effect = manager.get_effect("volume")
        assert effect is not None

        manager.remove_effect("volume")
        effect = manager.get_effect("volume")
        assert effect is None

    def test_enable_disable_effect(self):
        """Test enabling/disabling effect."""
        manager = PluginManager()
        manager.register_effect("volume", TestVolumeBoostEffect())

        manager.enable_effect("volume")
        assert manager.is_enabled("volume") is True

        manager.disable_effect("volume")
        assert manager.is_enabled("volume") is False

    def test_plugin_statistics(self):
        """Test plugin statistics."""
        manager = PluginManager()
        manager.register_effect("volume", TestVolumeBoostEffect())
        manager.register_effect("eq", TestEQEffect())

        stats = manager.get_statistics()

        assert stats["total_effects"] == 2
        assert len(stats["categories"]) > 0


class TestPluginIntegration:
    """Integration tests for plugin system."""

    def test_effect_chain(self, sample_audio: np.ndarray):
        """Test effect chain processing."""
        manager = PluginManager()
        manager.register_effect("volume1", TestVolumeBoostEffect())
        manager.register_effect("volume2", TestVolumeBoostEffect())

        audio = sample_audio
        for effect_name in ["volume1", "volume2"]:
            effect = manager.get_effect(effect_name)
            if effect:
                audio = effect.process(audio, 44100, gain=1.5)

        assert audio.shape == sample_audio.shape

    def test_discover_and_load_plugins(self):
        """Test plugin discovery and loading."""
        manager = PluginManager()

        # Manually register since we can't use entry points in test
        manager.register_effect("test", TestVolumeBoostEffect())

        effects = manager.list_effects()
        assert len(effects) > 0

    def test_plugin_error_handling(self):
        """Test error handling in plugins."""

        class ErrorEffect(AcroEffect):
            name = "Error"
            category = "Test"
            version = "1.0.0"
            author = "Test"
            description = "Test"

            def process(self, audio: np.ndarray, sample_rate: int, **params) -> np.ndarray:
                raise ValueError("Test error")

            def get_parameters(self) -> dict[str, Any]:
                return {}

            def validate(self) -> bool:
                return True

        effect = ErrorEffect()
        manager = PluginManager()
        manager.register_effect("error", effect)

        with pytest.raises(ValueError):
            effect.process(np.array([1, 2, 3], dtype=np.float32), 44100)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
