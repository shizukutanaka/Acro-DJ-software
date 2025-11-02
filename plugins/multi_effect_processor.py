# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Multi-Effect Processor Plugin for Acro DJ Mixer v3.x

Professional effects suite with:
- Reverb (Room, Hall, Plate)
- Delay (with sync to BPM)
- Filter (Lowpass, Highpass, Bandpass)
- Distortion (Soft/Hard clipping, overdrive)
- Modulation (Chorus, Flanger, Phaser)

All effects can be chained with customizable routing.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from enum import Enum
import numpy as np
from scipy.signal import convolve, butter, sosfilt
import logging

logger = logging.getLogger(__name__)


class EffectType(Enum):
    """Available effect types."""
    REVERB = "reverb"
    DELAY = "delay"
    FILTER = "filter"
    DISTORTION = "distortion"
    MODULATION = "modulation"


class ReverbType(Enum):
    """Types of reverb."""
    ROOM = "room"
    HALL = "hall"
    PLATE = "plate"


class FilterMode(Enum):
    """Filter modes."""
    LOWPASS = "lowpass"
    HIGHPASS = "highpass"
    BANDPASS = "bandpass"


class ModulationType(Enum):
    """Modulation types."""
    CHORUS = "chorus"
    FLANGER = "flanger"
    PHASER = "phaser"


@dataclass
class ReverbSettings:
    """Reverb effect settings."""
    reverb_type: ReverbType = ReverbType.HALL
    room_size: float = 0.5      # 0-1
    damping: float = 0.5         # 0-1
    wet_dry_mix: float = 0.5     # 0-1 (0=dry, 1=wet)
    width: float = 1.0           # Stereo width

    def to_dict(self) -> dict:
        return {
            'reverb_type': self.reverb_type.value,
            'room_size': float(self.room_size),
            'damping': float(self.damping),
            'wet_dry_mix': float(self.wet_dry_mix),
            'width': float(self.width),
        }


@dataclass
class DelaySettings:
    """Delay effect settings."""
    delay_time_ms: float = 500.0  # 1-2000 ms
    feedback: float = 0.5          # 0-0.95
    wet_dry_mix: float = 0.5       # 0-1
    sync_to_bpm: bool = False      # If True, sync to host BPM
    num_taps: int = 1              # Number of delay taps (1-4)

    def to_dict(self) -> dict:
        return {
            'delay_time_ms': float(self.delay_time_ms),
            'feedback': float(self.feedback),
            'wet_dry_mix': float(self.wet_dry_mix),
            'sync_to_bpm': self.sync_to_bpm,
            'num_taps': int(self.num_taps),
        }


@dataclass
class FilterSettings:
    """Filter effect settings."""
    mode: FilterMode = FilterMode.LOWPASS
    cutoff_hz: float = 5000.0     # 20-20000 Hz
    resonance: float = 1.0         # 1-10 (Q factor)
    drive: float = 1.0             # 0-2 (gain boost)

    def to_dict(self) -> dict:
        return {
            'mode': self.mode.value,
            'cutoff_hz': float(self.cutoff_hz),
            'resonance': float(self.resonance),
            'drive': float(self.drive),
        }


@dataclass
class DistortionSettings:
    """Distortion effect settings."""
    drive: float = 0.5             # 0-1
    tone: float = 0.5              # 0-1 (brightness)
    output_level: float = 1.0      # 0-2
    soft_clip: bool = True         # Soft vs hard clipping

    def to_dict(self) -> dict:
        return {
            'drive': float(self.drive),
            'tone': float(self.tone),
            'output_level': float(self.output_level),
            'soft_clip': self.soft_clip,
        }


@dataclass
class ModulationSettings:
    """Modulation effect settings."""
    modulation_type: ModulationType = ModulationType.CHORUS
    rate_hz: float = 1.5           # 0.1-20 Hz
    depth: float = 0.5             # 0-1
    feedback: float = 0.0          # 0-0.95
    wet_dry_mix: float = 0.5       # 0-1

    def to_dict(self) -> dict:
        return {
            'modulation_type': self.modulation_type.value,
            'rate_hz': float(self.rate_hz),
            'depth': float(self.depth),
            'feedback': float(self.feedback),
            'wet_dry_mix': float(self.wet_dry_mix),
        }


class SimpleReverb:
    """Simple reverb effect based on Schroeder reverberator."""

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.settings = ReverbSettings()

        # Reverb buffer lengths (in samples)
        self.comb_sizes = [int(s * sample_rate / 1000) for s in [25, 27, 29, 31]]
        self.allpass_sizes = [int(s * sample_rate / 1000) for s in [5, 7]]

        # Initialize buffers
        self.comb_buffers = [np.zeros(size) for size in self.comb_sizes]
        self.comb_indices = [0] * len(self.comb_sizes)
        self.comb_filter_states = [0.0] * len(self.comb_sizes)

        self.allpass_buffers = [np.zeros(size) for size in self.allpass_sizes]
        self.allpass_indices = [0] * len(self.allpass_sizes)

    def process(self, audio: np.ndarray) -> np.ndarray:
        """Process audio through reverb."""
        output = np.zeros_like(audio)
        room_size = 0.28 + 0.7 * self.settings.room_size
        damping = 0.4 + 0.6 * self.settings.damping

        for n, sample in enumerate(audio):
            # Process through comb filters
            comb_out = 0.0
            for i in range(len(self.comb_buffers)):
                idx = self.comb_indices[i]
                buf_sample = self.comb_buffers[i][idx]

                # Damping filter
                self.comb_filter_states[i] = buf_sample * (1 - damping) + self.comb_filter_states[i] * damping

                # Feedback
                new_sample = sample + self.comb_filter_states[i] * room_size
                self.comb_buffers[i][idx] = new_sample

                comb_out += buf_sample
                self.comb_indices[i] = (idx + 1) % len(self.comb_buffers[i])

            # Process through allpass filters
            allpass_out = comb_out
            for i in range(len(self.allpass_buffers)):
                idx = self.allpass_indices[i]
                buf_sample = self.allpass_buffers[i][idx]

                new_sample = allpass_out + buf_sample * 0.5
                self.allpass_buffers[i][idx] = allpass_out - buf_sample * 0.5

                allpass_out = new_sample
                self.allpass_indices[i] = (idx + 1) % len(self.allpass_buffers[i])

            # Mix wet/dry
            wet = allpass_out
            dry = audio[n]
            mix = self.settings.wet_dry_mix
            output[n] = dry * (1 - mix) + wet * mix

        return output


class SimpleDelay:
    """Simple delay effect with feedback."""

    def __init__(self, sample_rate: int = 44100, max_delay_ms: float = 2000):
        self.sample_rate = sample_rate
        self.settings = DelaySettings()
        self.max_delay_samples = int(max_delay_ms * sample_rate / 1000)
        self.buffer = np.zeros(self.max_delay_samples)
        self.write_index = 0

    def process(self, audio: np.ndarray) -> np.ndarray:
        """Process audio through delay."""
        output = np.zeros_like(audio)
        delay_samples = int(self.settings.delay_time_ms * self.sample_rate / 1000)
        delay_samples = min(delay_samples, self.max_delay_samples - 1)

        for n, sample in enumerate(audio):
            # Read from delay buffer
            read_index = (self.write_index - delay_samples) % self.max_delay_samples
            delayed = self.buffer[read_index]

            # Write with feedback
            new_sample = sample + delayed * self.settings.feedback
            self.buffer[self.write_index] = new_sample
            self.write_index = (self.write_index + 1) % self.max_delay_samples

            # Mix wet/dry
            mix = self.settings.wet_dry_mix
            output[n] = sample * (1 - mix) + delayed * mix

        return output


class SimpleFilter:
    """Simple filter effect using butterworth filters."""

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.settings = FilterSettings()
        self._last_sos = None

    def process(self, audio: np.ndarray) -> np.ndarray:
        """Process audio through filter."""
        try:
            # Design filter
            nyquist = self.sample_rate / 2
            normalized_freq = self.settings.cutoff_hz / nyquist
            normalized_freq = np.clip(normalized_freq, 0.001, 0.999)

            if self.settings.mode == FilterMode.LOWPASS:
                sos = butter(4, normalized_freq, btype='low', output='sos')
            elif self.settings.mode == FilterMode.HIGHPASS:
                sos = butter(4, normalized_freq, btype='high', output='sos')
            else:  # BANDPASS
                sos = butter(4, normalized_freq, btype='bandpass', output='sos')

            # Apply filter
            output = sosfilt(sos, audio)

            # Apply drive (gain boost)
            output = output * self.settings.drive

            return output

        except Exception as e:
            logger.warning(f"Filter processing failed: {e}")
            return audio


class SimpleDistortion:
    """Simple distortion effect with soft/hard clipping."""

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.settings = DistortionSettings()

    def process(self, audio: np.ndarray) -> np.ndarray:
        """Process audio through distortion."""
        # Apply drive (amplification)
        driven = audio * (1.0 + self.settings.drive * 10)

        # Apply clipping
        if self.settings.soft_clip:
            # Soft clip using tanh
            clipped = np.tanh(driven)
        else:
            # Hard clip
            clipped = np.clip(driven, -1.0, 1.0)

        # Tone control (simple high-pass)
        tone_factor = self.settings.tone
        # Simple moving average for tone
        if tone_factor < 1.0:
            kernel = np.array([tone_factor, 1.0 - tone_factor])
            clipped = np.convolve(clipped, kernel, mode='same')

        # Output level
        output = clipped * self.settings.output_level

        return output


class MultiEffectProcessor:
    """Combines multiple effects in a chain."""

    def __init__(self, sample_rate: int = 44100):
        """Initialize multi-effect processor.

        Args:
            sample_rate: Audio sample rate in Hz
        """
        self.sample_rate = sample_rate

        # Initialize all effects
        self.reverb = SimpleReverb(sample_rate)
        self.delay = SimpleDelay(sample_rate)
        self.filter = SimpleFilter(sample_rate)
        self.distortion = SimpleDistortion(sample_rate)

        # Effect chain ordering
        self.effect_chain: List[EffectType] = []
        self.enabled_effects: Dict[EffectType, bool] = {
            EffectType.REVERB: False,
            EffectType.DELAY: False,
            EffectType.FILTER: False,
            EffectType.DISTORTION: False,
            EffectType.MODULATION: False,
        }

    def set_effect_enabled(self, effect_type: EffectType, enabled: bool) -> None:
        """Enable/disable an effect.

        Args:
            effect_type: Type of effect
            enabled: Whether to enable
        """
        self.enabled_effects[effect_type] = enabled

    def set_effect_chain(self, chain: List[EffectType]) -> None:
        """Set the order of effects in the chain.

        Args:
            chain: List of effect types in desired order
        """
        self.effect_chain = chain

    def process(self, audio: np.ndarray) -> np.ndarray:
        """Process audio through effects chain.

        Args:
            audio: Input audio signal

        Returns:
            Processed audio signal
        """
        output = audio.copy()

        # Process through effect chain
        for effect_type in self.effect_chain:
            if not self.enabled_effects[effect_type]:
                continue

            if effect_type == EffectType.REVERB:
                output = self.reverb.process(output)
            elif effect_type == EffectType.DELAY:
                output = self.delay.process(output)
            elif effect_type == EffectType.FILTER:
                output = self.filter.process(output)
            elif effect_type == EffectType.DISTORTION:
                output = self.distortion.process(output)

        # Soft clipping to prevent distortion
        output = np.tanh(output * 0.5) / np.tanh(0.5)

        return output

    def get_reverb_settings(self) -> ReverbSettings:
        """Get reverb settings."""
        return self.reverb.settings

    def set_reverb_settings(self, settings: ReverbSettings) -> None:
        """Set reverb settings."""
        self.reverb.settings = settings

    def get_delay_settings(self) -> DelaySettings:
        """Get delay settings."""
        return self.delay.settings

    def set_delay_settings(self, settings: DelaySettings) -> None:
        """Set delay settings."""
        self.delay.settings = settings

    def get_filter_settings(self) -> FilterSettings:
        """Get filter settings."""
        return self.filter.settings

    def set_filter_settings(self, settings: FilterSettings) -> None:
        """Set filter settings."""
        self.filter.settings = settings

    def get_distortion_settings(self) -> DistortionSettings:
        """Get distortion settings."""
        return self.distortion.settings

    def set_distortion_settings(self, settings: DistortionSettings) -> None:
        """Set distortion settings."""
        self.distortion.settings = settings
