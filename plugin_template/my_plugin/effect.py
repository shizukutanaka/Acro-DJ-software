# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""Example audio effect plugin for Acro DJ Mixer.

This is a template file for implementing your own audio effects.
Replace the implementation with your custom effect logic.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from plugin_api import AcroEffect


class MyCustomEffect(AcroEffect):
    """Template audio effect plugin.

    This is a basic template showing the structure of an audio effect plugin.
    Replace this with your custom effect implementation.

    Parameters:
        intensity: Effect intensity from 0.0 to 1.0
        dry_wet: Dry/wet mix ratio from 0.0 (dry) to 1.0 (wet)

    Example:
        >>> effect = MyCustomEffect()
        >>> audio = np.random.randn(44100).astype(np.float32)
        >>> processed = effect.process(audio, 44100, intensity=0.5, dry_wet=0.7)
    """

    name = "My Custom Effect"
    category = "Utility"
    version = "1.0.0"
    author = "Your Name"
    description = "Template effect - customize this with your own implementation"

    def process(
        self,
        audio: np.ndarray,
        sample_rate: int,
        **params: Any,
    ) -> np.ndarray:
        """Apply the effect to audio.

        Args:
            audio: Input audio array (float32, mono or stereo)
            sample_rate: Sample rate in Hz
            **params: Effect parameters defined in get_parameters()

        Returns:
            Processed audio array (float32)

        Example:
            >>> audio = np.ones(1000, dtype=np.float32)
            >>> effect = MyCustomEffect()
            >>> result = effect.process(audio, 44100, intensity=0.5)
            >>> assert result.shape == audio.shape
            >>> assert result.dtype == np.float32
        """
        intensity = params.get("intensity", 0.5)
        dry_wet = params.get("dry_wet", 0.5)

        # TODO: Implement your effect logic here
        # This is a template that just applies gain

        # Apply gain based on intensity
        gain = 1.0 + intensity  # 1.0 to 2.0
        processed = audio * gain

        # Simple dry/wet mixing
        output = audio * (1.0 - dry_wet) + processed * dry_wet

        # Soft clipping to prevent distortion
        output = np.tanh(output)

        return output.astype(np.float32)

    def get_parameters(self) -> dict[str, Any]:
        """Define adjustable effect parameters.

        Returns a dictionary where each key is a parameter name,
        and each value is a dictionary defining the parameter properties:
        - type: parameter type (float, int, bool, etc.)
        - min: minimum value
        - max: maximum value
        - default: default value
        - label: human-readable label
        - unit: unit of measurement (optional)
        - step: step size for UI sliders (optional)

        Returns:
            Dictionary of parameter definitions

        Example:
            >>> effect = MyCustomEffect()
            >>> params = effect.get_parameters()
            >>> assert "intensity" in params
            >>> assert params["intensity"]["min"] == 0.0
            >>> assert params["intensity"]["max"] == 1.0
        """
        return {
            "intensity": {
                "type": "float",
                "min": 0.0,
                "max": 1.0,
                "default": 0.5,
                "label": "Effect Intensity",
                "unit": "%",
                "step": 0.01,
            },
            "dry_wet": {
                "type": "float",
                "min": 0.0,
                "max": 1.0,
                "default": 0.5,
                "label": "Dry/Wet Mix",
                "unit": "%",
                "step": 0.01,
            },
        }

    def validate(self) -> bool:
        """Validate plugin compatibility.

        Check if this plugin is compatible with the current system.
        Override this method to add validation logic.

        Returns:
            True if plugin is valid and can be used, False otherwise

        Example:
            >>> effect = MyCustomEffect()
            >>> assert effect.validate() is True
        """
        # Add your validation logic here
        # For example, check for required libraries or system features

        return True

    def on_enable(self) -> None:
        """Called when effect is enabled.

        Override this method to perform initialization:
        - Allocate buffers
        - Initialize state variables
        - Start background threads
        - Load resources

        Example:
            class MyEffect(AcroEffect):
                def on_enable(self):
                    self.buffer = np.zeros(44100)
                    self.enabled = True
        """
        # TODO: Add initialization code here
        pass

    def on_disable(self) -> None:
        """Called when effect is disabled.

        Override this method to perform cleanup:
        - Free buffers
        - Reset state variables
        - Stop background threads
        - Release resources

        Example:
            class MyEffect(AcroEffect):
                def on_disable(self):
                    if hasattr(self, 'buffer'):
                        del self.buffer
                    self.enabled = False
        """
        # TODO: Add cleanup code here
        pass

    def reset_state(self) -> None:
        """Reset internal state variables.

        Called when effect chain is reset or before processing
        a new audio segment. Override to reset any state that
        affects processing continuity.

        This is important for effects like reverb or delay
        that maintain internal buffers.

        Example:
            class ReverbEffect(AcroEffect):
                def reset_state(self):
                    self.buffer.fill(0)
                    self.index = 0
        """
        # TODO: Reset effect state here
        pass


# Optional: Add more effect classes for different effects

class TemplateModulationEffect(AcroEffect):
    """Template for modulation effects (Chorus, Flanger, etc.)."""

    name = "Template Modulation"
    category = "Modulation"
    version = "1.0.0"
    author = "Your Name"
    description = "Template modulation effect"

    def process(
        self,
        audio: np.ndarray,
        sample_rate: int,
        **params: Any,
    ) -> np.ndarray:
        """Apply modulation effect."""
        # TODO: Implement modulation effect
        return audio.astype(np.float32)

    def get_parameters(self) -> dict[str, Any]:
        """Define modulation parameters."""
        return {
            "rate": {
                "type": "float",
                "min": 0.1,
                "max": 10.0,
                "default": 2.0,
                "label": "Modulation Rate",
                "unit": "Hz",
            },
            "depth": {
                "type": "float",
                "min": 0.0,
                "max": 1.0,
                "default": 0.5,
                "label": "Modulation Depth",
                "unit": "%",
            },
        }

    def validate(self) -> bool:
        """Validate plugin."""
        return True


class TemplateFilterEffect(AcroEffect):
    """Template for filter effects (Low-pass, High-pass, Band-pass)."""

    name = "Template Filter"
    category = "Filter"
    version = "1.0.0"
    author = "Your Name"
    description = "Template filter effect"

    def process(
        self,
        audio: np.ndarray,
        sample_rate: int,
        **params: Any,
    ) -> np.ndarray:
        """Apply filter effect."""
        # TODO: Implement filter effect
        return audio.astype(np.float32)

    def get_parameters(self) -> dict[str, Any]:
        """Define filter parameters."""
        return {
            "cutoff_frequency": {
                "type": "float",
                "min": 20.0,
                "max": 20000.0,
                "default": 10000.0,
                "label": "Cutoff Frequency",
                "unit": "Hz",
            },
            "resonance": {
                "type": "float",
                "min": 0.0,
                "max": 1.0,
                "default": 0.5,
                "label": "Resonance",
                "unit": "%",
            },
        }

    def validate(self) -> bool:
        """Validate plugin."""
        return True


if __name__ == "__main__":
    # Test the effect
    print("Testing template effect...")

    # Create effect instance
    effect = MyCustomEffect()

    print(f"Effect: {effect.name}")
    print(f"Category: {effect.category}")
    print(f"Author: {effect.author}")
    print(f"Version: {effect.version}")

    # Test parameters
    params = effect.get_parameters()
    print(f"\nParameters: {list(params.keys())}")

    # Test processing
    sample_rate = 44100
    duration = 1.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    test_audio = (np.sin(2 * np.pi * 440 * t) * 0.1).astype(np.float32)

    processed = effect.process(test_audio, sample_rate, intensity=0.5)

    print(f"\nInput shape: {test_audio.shape}")
    print(f"Output shape: {processed.shape}")
    print(f"Input max: {np.max(np.abs(test_audio)):.4f}")
    print(f"Output max: {np.max(np.abs(processed)):.4f}")

    print("\n✅ Template effect working correctly!")
