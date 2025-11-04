# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Parallel Effects Processing with Latency Compensation

Provides professional parallel compression, parallel EQ, and convolution reverb:
- Latency-compensated mixing
- Parallel compression with configurable parameters
- Parallel EQ for frequency-specific processing
- Convolution reverb with FFT-based fast convolution
- Real-time capable with optimization
"""

import logging
import numpy as np
from typing import Dict, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum
from threading import Lock
from scipy import signal
from scipy.signal import fftconvolve

logger = logging.getLogger(__name__)

# Optional dependencies
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


@dataclass
class EffectLatency:
    """Latency information for effect."""
    input_latency_samples: int  # Samples from input to effect processing
    output_latency_samples: int  # Samples from effect processing to output
    total_latency_samples: int  # Total effect latency

    def get_latency_ms(self, sample_rate: int) -> float:
        """Get total latency in milliseconds."""
        return (self.total_latency_samples / sample_rate) * 1000.0


class ParallelCompressionProfile(Enum):
    """Parallel compression intensity profiles."""
    SUBTLE = "subtle"      # Light parallel compression (30% mix)
    BALANCED = "balanced"  # Standard parallel compression (50% mix)
    HEAVY = "heavy"        # Aggressive parallel compression (70% mix)


@dataclass
class ParallelCompressionSettings:
    """Parallel compression configuration."""
    ratio: float = 4.0              # Compression ratio (1:1 to 8:1)
    threshold_db: float = -20.0     # Threshold in dB
    attack_ms: float = 5.0          # Attack time in ms
    release_ms: float = 100.0       # Release time in ms
    makeup_gain_db: float = 0.0     # Makeup gain in dB
    mix: float = 0.5                # Dry/wet mix (0.0-1.0)


class ParallelCompressor:
    """
    Parallel compression with latency compensation.

    Provides transparent parallel compression by measuring and compensating
    for the latency introduced by the compression circuit.
    """

    def __init__(self, sr: int = 44100, buffer_size: int = 2048):
        """
        Initialize parallel compressor.

        Args:
            sr: Sample rate
            buffer_size: Processing buffer size
        """
        self.sr = sr
        self.buffer_size = buffer_size
        self.settings = ParallelCompressionSettings()
        self.lock = Lock()

        # Delay line for latency compensation
        self.max_delay_samples = sr  # 1 second max delay
        self.delay_line = np.zeros(self.max_delay_samples)
        self.write_index = 0

        # Compressor state
        self.envelope = 0.0

        logger.info(f"ParallelCompressor initialized: sr={sr}, buffer_size={buffer_size}")

    def _compute_latency(self) -> int:
        """Compute compression circuit latency."""
        # Approximate: attack time is primary component
        latency_samples = int(self.settings.attack_ms * self.sr / 1000.0)
        return latency_samples

    def set_profile(self, profile: ParallelCompressionProfile) -> None:
        """
        Set compression profile.

        Args:
            profile: Preset profile
        """
        profiles = {
            ParallelCompressionProfile.SUBTLE: ParallelCompressionSettings(
                ratio=2.0, threshold_db=-10.0, attack_ms=1.0, release_ms=50.0, mix=0.3
            ),
            ParallelCompressionProfile.BALANCED: ParallelCompressionSettings(
                ratio=4.0, threshold_db=-20.0, attack_ms=5.0, release_ms=100.0, mix=0.5
            ),
            ParallelCompressionProfile.HEAVY: ParallelCompressionSettings(
                ratio=8.0, threshold_db=-30.0, attack_ms=10.0, release_ms=200.0, mix=0.7
            ),
        }

        with self.lock:
            self.settings = profiles[profile]

        logger.info(f"Compression profile set: {profile.value}")

    def process(self, audio: np.ndarray) -> np.ndarray:
        """
        Apply parallel compression.

        Args:
            audio: Input audio samples

        Returns:
            Compressed audio mixed with dry signal
        """
        if self.settings.mix <= 0.0:
            return audio

        dry = audio.copy()

        # Compress audio
        wet = self._compress_audio(audio)

        # Compute latency and compensate
        latency_samples = self._compute_latency()
        dry_delayed = self._apply_delay(dry, latency_samples)

        # Mix dry and wet
        output = (dry_delayed * (1 - self.settings.mix)) + (wet * self.settings.mix)

        return output

    def _compress_audio(self, audio: np.ndarray) -> np.ndarray:
        """Apply compression to audio."""
        output = np.zeros_like(audio)

        # Convert times to coefficients
        attack_coef = np.exp(-1.0 / (self.settings.attack_ms * self.sr / 1000.0))
        release_coef = np.exp(-1.0 / (self.settings.release_ms * self.sr / 1000.0))

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
            if self.envelope > self.settings.threshold_db:
                gain_reduction = (self.envelope - self.settings.threshold_db) * (
                    1 - 1 / self.settings.ratio
                )
            else:
                gain_reduction = 0.0

            # Apply gain reduction and makeup gain
            gain_lin = 10.0 ** (-gain_reduction / 20.0)
            makeup_lin = 10.0 ** (self.settings.makeup_gain_db / 20.0)

            output[i] = sample * gain_lin * makeup_lin

        return output

    def _apply_delay(self, audio: np.ndarray, delay_samples: int) -> np.ndarray:
        """Apply delay to audio for latency compensation."""
        if delay_samples <= 0:
            return audio

        output = np.zeros_like(audio)
        delay_samples = min(delay_samples, self.max_delay_samples)

        for i, sample in enumerate(audio):
            # Write to delay line
            self.write_index %= self.max_delay_samples
            self.delay_line[self.write_index] = sample

            # Read from delay line
            read_index = (self.write_index - delay_samples) % self.max_delay_samples
            output[i] = self.delay_line[read_index]

            self.write_index += 1

        return output


class ParallelEQ:
    """
    Parallel equalization with frequency-specific processing.

    Allows selective EQ on specific frequency ranges while maintaining
    overall signal transparency through parallel mixing.
    """

    def __init__(self, sr: int = 44100):
        """
        Initialize parallel EQ.

        Args:
            sr: Sample rate
        """
        self.sr = sr
        self.lock = Lock()

        # Filter frequencies
        self.low_freq = 100  # Hz
        self.mid_freq = 1000  # Hz
        self.high_freq = 10000  # Hz

        # Gains in dB
        self.low_gain = 0.0
        self.mid_gain = 0.0
        self.high_gain = 0.0

        # Dry/wet mix
        self.mix = 0.5

        logger.info(f"ParallelEQ initialized: sr={sr}")

    def set_band_gain(self, band: str, gain_db: float, apply_to_wet: bool = True) -> None:
        """
        Set gain for frequency band.

        Args:
            band: "low", "mid", or "high"
            gain_db: Gain in dB
            apply_to_wet: Apply to wet signal (True) or dry (False)
        """
        gain_db = np.clip(gain_db, -12, 12)

        with self.lock:
            if band == "low":
                self.low_gain = gain_db
            elif band == "mid":
                self.mid_gain = gain_db
            elif band == "high":
                self.high_gain = gain_db

    def process(self, audio: np.ndarray) -> np.ndarray:
        """
        Apply parallel EQ.

        Args:
            audio: Input audio

        Returns:
            EQ-processed audio
        """
        if self.mix <= 0.0:
            return audio

        dry = audio.copy()

        # Apply EQ to wet signal
        wet = self._apply_eq(audio)

        # Mix
        output = (dry * (1 - self.mix)) + (wet * self.mix)

        return output

    def _apply_eq(self, audio: np.ndarray) -> np.ndarray:
        """Apply 3-band EQ using butterworth filters."""
        output = audio.copy()

        # Low band
        if self.low_gain != 0:
            low_gain_lin = 10.0 ** (self.low_gain / 20.0)
            low_sos = signal.butter(2, self.low_freq, btype='low', fs=self.sr, output='sos')
            low_filtered = signal.sosfilt(low_sos, audio)
            low_component = audio - signal.sosfilt(low_sos, audio - low_filtered)
            output += (low_filtered - audio) * (low_gain_lin - 1.0)

        # Mid band
        if self.mid_gain != 0:
            mid_gain_lin = 10.0 ** (self.mid_gain / 20.0)
            mid_sos = signal.butter(2, [self.low_freq, self.high_freq], btype='band',
                                   fs=self.sr, output='sos')
            mid_filtered = signal.sosfilt(mid_sos, audio)
            output += (mid_filtered - audio) * (mid_gain_lin - 1.0)

        # High band
        if self.high_gain != 0:
            high_gain_lin = 10.0 ** (self.high_gain / 20.0)
            high_sos = signal.butter(2, self.high_freq, btype='high', fs=self.sr, output='sos')
            high_filtered = signal.sosfilt(high_sos, audio)
            output += (high_filtered - audio) * (high_gain_lin - 1.0)

        return output


class ConvolutionReverb:
    """
    Convolution reverb with FFT-based fast convolution.

    Provides realistic room modeling using impulse responses.
    Optimized for real-time performance.
    """

    def __init__(self, impulse_response: np.ndarray, sr: int = 44100,
                 partition_size: int = 512):
        """
        Initialize convolution reverb.

        Args:
            impulse_response: IR audio samples
            sr: Sample rate
            partition_size: FFT partition size (higher = more latency but faster)
        """
        self.sr = sr
        self.partition_size = partition_size
        self.lock = Lock()

        # Normalize IR
        max_val = np.max(np.abs(impulse_response))
        if max_val > 0:
            self.ir = impulse_response / max_val
        else:
            self.ir = impulse_response

        # Parameters
        self.mix = 0.3  # Dry/wet mix
        self.pre_delay_ms = 0.0
        self.room_size = 1.0  # 0.0-1.0 (scales IR length)
        self.damping = 0.5  # 0.0-1.0 (affects high frequencies)

        # State
        self.delay_line = np.zeros(int(self.sr))  # 1 second max delay
        self.write_index = 0

        logger.info(f"ConvolutionReverb initialized: IR length={len(self.ir)}, "
                   f"partition_size={partition_size}")

    def set_room_size(self, size: float) -> None:
        """
        Set room size (scales IR length).

        Args:
            size: 0.0-1.0
        """
        with self.lock:
            self.room_size = np.clip(size, 0.0, 1.0)

    def set_mix(self, mix: float) -> None:
        """
        Set dry/wet mix.

        Args:
            mix: 0.0 (all dry) to 1.0 (all wet)
        """
        with self.lock:
            self.mix = np.clip(mix, 0.0, 1.0)

    def process(self, audio: np.ndarray) -> np.ndarray:
        """
        Apply convolution reverb.

        Args:
            audio: Input audio

        Returns:
            Reverbed audio
        """
        if self.mix <= 0.0:
            return audio

        dry = audio.copy()

        # Apply pre-delay
        audio_delayed = self._apply_pre_delay(audio)

        # Convolve with IR using FFT (fast convolution)
        try:
            wet = fftconvolve(audio_delayed, self.ir, mode='same')
        except Exception:
            # Fallback to direct convolution if FFT fails
            wet = np.convolve(audio_delayed, self.ir, mode='same')

        # Normalize to prevent clipping
        max_val = np.max(np.abs(wet))
        if max_val > 1.0:
            wet = wet / max_val

        # Mix
        output = (dry * (1 - self.mix)) + (wet * self.mix)

        return output

    def _apply_pre_delay(self, audio: np.ndarray) -> np.ndarray:
        """Apply pre-delay to reverb."""
        if self.pre_delay_ms <= 0:
            return audio

        delay_samples = int(self.pre_delay_ms * self.sr / 1000.0)
        delay_samples = min(delay_samples, len(self.delay_line) - 1)

        output = np.zeros_like(audio)

        for i, sample in enumerate(audio):
            self.write_index %= len(self.delay_line)
            self.delay_line[self.write_index] = sample

            read_index = (self.write_index - delay_samples) % len(self.delay_line)
            output[i] = self.delay_line[read_index]

            self.write_index += 1

        return output


class ParallelEffectChain:
    """
    Complete parallel effect chain with multiple processors.

    Combines parallel compression, EQ, and convolution reverb
    with proper latency compensation.
    """

    def __init__(self, sr: int = 44100):
        """
        Initialize parallel effect chain.

        Args:
            sr: Sample rate
        """
        self.sr = sr
        self.lock = Lock()

        # Effect processors
        self.parallel_compressor = ParallelCompressor(sr=sr)
        self.parallel_eq = ParallelEQ(sr=sr)
        self.convolution_reverb: Optional[ConvolutionReverb] = None

        # Enable/disable flags
        self.enable_compression = True
        self.enable_eq = True
        self.enable_reverb = False

        logger.info(f"ParallelEffectChain initialized: sr={sr}")

    def load_impulse_response(self, ir_audio: np.ndarray) -> bool:
        """
        Load impulse response for convolution reverb.

        Args:
            ir_audio: IR audio samples

        Returns:
            True if loaded successfully
        """
        try:
            with self.lock:
                self.convolution_reverb = ConvolutionReverb(ir_audio, sr=self.sr)
            logger.info(f"IR loaded: {len(ir_audio)} samples")
            return True
        except Exception as e:
            logger.error(f"Failed to load IR: {e}")
            return False

    def process(self, audio: np.ndarray) -> np.ndarray:
        """
        Process audio through all enabled effects.

        Args:
            audio: Input audio

        Returns:
            Processed audio
        """
        output = audio.copy()

        # Apply effects in order
        if self.enable_compression:
            output = self.parallel_compressor.process(output)

        if self.enable_eq:
            output = self.parallel_eq.process(output)

        if self.enable_reverb and self.convolution_reverb:
            output = self.convolution_reverb.process(output)

        return output

    def set_compression_profile(self, profile: ParallelCompressionProfile) -> None:
        """Set compression profile."""
        self.parallel_compressor.set_profile(profile)

    def set_eq_band(self, band: str, gain_db: float) -> None:
        """Set EQ band gain."""
        self.parallel_eq.set_band_gain(band, gain_db)

    def set_reverb_mix(self, mix: float) -> None:
        """Set reverb wet/dry mix."""
        if self.convolution_reverb:
            self.convolution_reverb.set_mix(mix)

    def get_total_latency_samples(self) -> int:
        """Get total chain latency."""
        total = 0

        if self.enable_compression:
            total += self.parallel_compressor._compute_latency()

        return total

    def get_total_latency_ms(self) -> float:
        """Get total latency in milliseconds."""
        return (self.get_total_latency_samples() / self.sr) * 1000.0
