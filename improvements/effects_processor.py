# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Effects Chain & DSP Processing

Provides professional audio effects processing including:
- Effect chain management
- Parametric EQ
- Compression
- Reverb (algorithmic simulation)
- Delay/Echo
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod
from threading import Lock

logger = logging.getLogger(__name__)


class EffectType(Enum):
    """Available audio effects."""
    EQ = "eq"
    COMPRESSOR = "compressor"
    REVERB = "reverb"
    DELAY = "delay"
    FILTER = "filter"
    SATURATION = "saturation"


@dataclass
class EffectParameters:
    """Parameters for audio effects."""
    enabled: bool = True
    mix: float = 0.5  # Dry/wet mix (0.0-1.0)
    bypass: bool = False

    def validate(self) -> bool:
        """Validate parameters."""
        return 0.0 <= self.mix <= 1.0


class AudioEffect(ABC):
    """Base class for audio effects."""

    def __init__(self, sr: int = 44100):
        """
        Initialize effect.

        Args:
            sr: Sample rate in Hz
        """
        self.sr = sr
        self.params = EffectParameters()
        self.lock = Lock()

    @abstractmethod
    def process(self, audio: np.ndarray) -> np.ndarray:
        """
        Process audio.

        Args:
            audio: Audio samples

        Returns:
            Processed audio
        """
        pass

    def apply_mix(self, dry: np.ndarray, wet: np.ndarray) -> np.ndarray:
        """Apply dry/wet mix."""
        mix_factor = self.params.mix
        return (1 - mix_factor) * dry + mix_factor * wet


class ParametricEQ(AudioEffect):
    """
    3-band parametric equalizer.
    """

    def __init__(self, sr: int = 44100):
        """Initialize EQ with low/mid/high bands."""
        super().__init__(sr)

        # Band gains in dB (-12 to +12)
        self.low_gain = 0.0     # 100 Hz
        self.mid_gain = 0.0     # 1 kHz
        self.high_gain = 0.0    # 10 kHz

        # Simple filter coefficients (precomputed)
        self.low_coef = self._compute_filter_coef(100)
        self.mid_coef = self._compute_filter_coef(1000)
        self.high_coef = self._compute_filter_coef(10000)

    def _compute_filter_coef(self, center_freq: float) -> float:
        """Compute simple filter coefficient."""
        # Simplified Butterworth-style coefficient
        omega = 2 * np.pi * center_freq / self.sr
        return omega / (1 + omega)

    def process(self, audio: np.ndarray) -> np.ndarray:
        """Apply parametric EQ."""
        if self.params.bypass or not self.params.enabled:
            return audio

        output = audio.copy()

        # Apply low band boost/cut
        if self.low_gain != 0:
            low_gain_lin = 10.0 ** (self.low_gain / 20.0)
            output = self._apply_band_filter(output, self.low_coef, low_gain_lin)

        # Apply mid band
        if self.mid_gain != 0:
            mid_gain_lin = 10.0 ** (self.mid_gain / 20.0)
            output = self._apply_band_filter(output, self.mid_coef, mid_gain_lin)

        # Apply high band
        if self.high_gain != 0:
            high_gain_lin = 10.0 ** (self.high_gain / 20.0)
            output = self._apply_band_filter(output, self.high_coef, high_gain_lin)

        # Mix with original
        return self.apply_mix(audio, output)

    def _apply_band_filter(self, signal: np.ndarray, coef: float,
                          gain: float) -> np.ndarray:
        """Apply single band filter."""
        output = np.zeros_like(signal)
        state = 0.0

        for i, sample in enumerate(signal):
            state = state * (1 - coef) + sample * coef
            output[i] = sample + (state - sample) * gain

        return output

    def set_band_gain(self, band: str, gain_db: float) -> None:
        """
        Set band gain in dB.

        Args:
            band: 'low', 'mid', or 'high'
            gain_db: Gain in dB (-12 to +12)
        """
        gain_db = np.clip(gain_db, -12, 12)

        with self.lock:
            if band == 'low':
                self.low_gain = gain_db
            elif band == 'mid':
                self.mid_gain = gain_db
            elif band == 'high':
                self.high_gain = gain_db


class Compressor(AudioEffect):
    """
    Dynamic range compressor.
    """

    def __init__(self, sr: int = 44100):
        """Initialize compressor."""
        super().__init__(sr)

        # Compressor parameters
        self.threshold = -20.0  # dB
        self.ratio = 4.0        # Compression ratio
        self.attack = 0.005     # seconds
        self.release = 0.1      # seconds
        self.makeup_gain = 0.0  # dB

        # State
        self.envelope = 0.0

    def process(self, audio: np.ndarray) -> np.ndarray:
        """Apply compression."""
        if self.params.bypass or not self.params.enabled:
            return audio

        output = np.zeros_like(audio)

        # Attack/release coefficients
        attack_coef = np.exp(-1.0 / (self.attack * self.sr))
        release_coef = np.exp(-1.0 / (self.release * self.sr))

        for i, sample in enumerate(audio):
            # Level detection
            level = abs(sample)
            level_db = 20 * np.log10(level + 1e-10)

            # Envelope follower
            if level_db > self.envelope:
                self.envelope = attack_coef * self.envelope + (1 - attack_coef) * level_db
            else:
                self.envelope = release_coef * self.envelope + (1 - release_coef) * level_db

            # Gain reduction calculation
            if self.envelope > self.threshold:
                gain_reduction = (self.envelope - self.threshold) * (1 - 1/self.ratio)
            else:
                gain_reduction = 0.0

            # Apply gain reduction
            gain_lin = 10.0 ** (-gain_reduction / 20.0)
            makeup_lin = 10.0 ** (self.makeup_gain / 20.0)

            output[i] = sample * gain_lin * makeup_lin

        return self.apply_mix(audio, output)


class SimpleReverb(AudioEffect):
    """
    Simple algorithmic reverb using delay line.
    """

    def __init__(self, sr: int = 44100):
        """Initialize reverb."""
        super().__init__(sr)

        # Reverb parameters
        self.room_size = 0.5    # 0.0-1.0
        self.damp = 0.5        # 0.0-1.0
        self.width = 1.0       # Stereo width

        # Delay buffers (different lengths for diffusion)
        self.delays = [
            np.zeros(int(0.02 * sr)),  # 20ms
            np.zeros(int(0.03 * sr)),  # 30ms
            np.zeros(int(0.04 * sr)),  # 40ms
            np.zeros(int(0.05 * sr)),  # 50ms
        ]
        self.write_indices = [0] * len(self.delays)

    def process(self, audio: np.ndarray) -> np.ndarray:
        """Apply reverb."""
        if self.params.bypass or not self.params.enabled:
            return audio

        output = np.zeros_like(audio)

        for i, sample in enumerate(audio):
            # Process through delay lines
            reverb_signal = 0.0

            for delay_idx, delay_buf in enumerate(self.delays):
                # Write to buffer
                self.write_indices[delay_idx] %= len(delay_buf)
                delay_buf[self.write_indices[delay_idx]] = sample

                # Read with feedback
                read_idx = (self.write_indices[delay_idx] - 1) % len(delay_buf)
                reverb_signal += delay_buf[read_idx] * self.room_size

                self.write_indices[delay_idx] += 1

            # Average delay outputs
            reverb_signal /= len(self.delays)

            output[i] = sample + reverb_signal * self.room_size

        return self.apply_mix(audio, output)


class Delay(AudioEffect):
    """
    Delay/Echo effect with feedback.
    """

    def __init__(self, sr: int = 44100, max_delay_seconds: float = 2.0):
        """Initialize delay."""
        super().__init__(sr)

        self.max_delay_samples = int(max_delay_seconds * sr)
        self.buffer = np.zeros(self.max_delay_samples)
        self.write_index = 0

        self.delay_time = 0.5  # seconds
        self.feedback = 0.5    # 0.0-1.0

    def process(self, audio: np.ndarray) -> np.ndarray:
        """Apply delay."""
        if self.params.bypass or not self.params.enabled:
            return audio

        output = np.zeros_like(audio)
        delay_samples = int(self.delay_time * self.sr)
        delay_samples = min(delay_samples, self.max_delay_samples)

        for i, sample in enumerate(audio):
            # Read delayed sample
            read_index = (self.write_index - delay_samples) % self.max_delay_samples
            delayed = self.buffer[read_index]

            # Write to buffer with feedback
            self.buffer[self.write_index] = sample + delayed * self.feedback
            self.write_index = (self.write_index + 1) % self.max_delay_samples

            # Output
            output[i] = sample + delayed

        return self.apply_mix(audio, output)


class EffectsChain:
    """
    Manages a chain of audio effects.
    """

    def __init__(self):
        """Initialize effects chain."""
        self.effects: Dict[str, AudioEffect] = {}
        self.order: List[str] = []
        self.lock = Lock()

        # Create standard effects
        self.add_effect("eq", ParametricEQ())
        self.add_effect("compressor", Compressor())
        self.add_effect("delay", Delay())
        self.add_effect("reverb", SimpleReverb())

        logger.info("EffectsChain initialized with 4 effects")

    def add_effect(self, name: str, effect: AudioEffect) -> None:
        """
        Add effect to chain.

        Args:
            name: Effect name/identifier
            effect: AudioEffect instance
        """
        with self.lock:
            self.effects[name] = effect
            if name not in self.order:
                self.order.append(name)

            logger.info(f"Effect '{name}' added to chain")

    def remove_effect(self, name: str) -> bool:
        """Remove effect from chain."""
        with self.lock:
            if name in self.effects:
                del self.effects[name]
                self.order.remove(name)
                logger.info(f"Effect '{name}' removed from chain")
                return True
            return False

    def reorder_effects(self, new_order: List[str]) -> bool:
        """
        Reorder effects in chain.

        Args:
            new_order: New effect order

        Returns:
            True if reordered
        """
        with self.lock:
            if set(new_order) != set(self.effects.keys()):
                logger.error("New order doesn't match existing effects")
                return False

            self.order = new_order
            logger.info(f"Effects reordered: {new_order}")

        return True

    def process(self, audio: np.ndarray) -> np.ndarray:
        """
        Process audio through entire chain.

        Args:
            audio: Input audio samples

        Returns:
            Processed audio
        """
        output = audio.copy()

        with self.lock:
            for effect_name in self.order:
                effect = self.effects[effect_name]
                if effect.params.enabled:
                    output = effect.process(output)

        return output

    def enable_effect(self, name: str, enabled: bool = True) -> bool:
        """Enable/disable specific effect."""
        with self.lock:
            if name in self.effects:
                self.effects[name].params.enabled = enabled
                logger.info(f"Effect '{name}' {'enabled' if enabled else 'disabled'}")
                return True
            return False

    def bypass_effect(self, name: str, bypass: bool = True) -> bool:
        """Bypass specific effect."""
        with self.lock:
            if name in self.effects:
                self.effects[name].params.bypass = bypass
                return True
            return False

    def get_effect(self, name: str) -> Optional[AudioEffect]:
        """Get effect by name."""
        with self.lock:
            return self.effects.get(name)

    def get_chain_order(self) -> List[str]:
        """Get current effect chain order."""
        with self.lock:
            return self.order.copy()

    def get_statistics(self) -> Dict[str, any]:
        """Get chain statistics."""
        with self.lock:
            return {
                'total_effects': len(self.effects),
                'enabled_effects': sum(
                    1 for e in self.effects.values() if e.params.enabled
                ),
                'chain_order': self.order.copy(),
                'effects': list(self.effects.keys())
            }
