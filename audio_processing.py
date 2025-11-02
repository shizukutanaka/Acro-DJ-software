# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""Advanced audio processing and DSP functions.

Provides professional audio processing capabilities including:
- Basic audio manipulation (gain, normalization, clipping)
- EQ filtering (bass, mid, treble)
- Dynamic range compression
- Reverb effects
- Time stretching
- Frequency analysis (FFT, MFCC, spectral features)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from enum import Enum

import numpy as np
from scipy import signal
from scipy.fftpack import fft, fftfreq


class FadeType(Enum):
    """Fade types."""
    IN = "in"
    OUT = "out"
    IN_OUT = "in_out"


@dataclass
class AudioProcessor:
    """Basic audio processing utilities.

    Provides fundamental audio operations like gain, normalization,
    clipping, and mixing.
    """
    sample_rate: int = 44100

    def apply_gain(self, audio: np.ndarray, gain_db: float) -> np.ndarray:
        """Apply gain to audio.

        Args:
            audio: Input audio array
            gain_db: Gain adjustment in dB

        Returns:
            Audio with gain applied
        """
        linear_gain = 10.0 ** (gain_db / 20.0)
        return (audio * linear_gain).astype(np.float32)

    def normalize(
        self,
        audio: np.ndarray,
        target_level: float = 0.95,
    ) -> np.ndarray:
        """Normalize audio to target level.

        Args:
            audio: Input audio array
            target_level: Target peak level (0.0-1.0)

        Returns:
            Normalized audio array
        """
        max_val = np.max(np.abs(audio))
        if max_val > 0:
            scale_factor = target_level / max_val
            return (audio * scale_factor).astype(np.float32)
        return audio.astype(np.float32)

    def soft_clip(
        self,
        audio: np.ndarray,
        threshold: float = 0.9,
    ) -> np.ndarray:
        """Apply soft clipping to prevent distortion.

        Uses tanh function for smooth saturation.

        Args:
            audio: Input audio array
            threshold: Threshold before clipping

        Returns:
            Clipped audio array
        """
        scaled = audio / threshold
        clipped = np.tanh(scaled)
        return (clipped * threshold).astype(np.float32)

    def apply_fade(
        self,
        audio: np.ndarray,
        fade_type: Literal["in", "out", "in_out"] = "in",
        duration_ms: float = 1000.0,
    ) -> np.ndarray:
        """Apply fade in/out envelope.

        Args:
            audio: Input audio array
            fade_type: Type of fade (in, out, in_out)
            duration_ms: Fade duration in milliseconds

        Returns:
            Audio with fade applied
        """
        fade_samples = int((duration_ms / 1000.0) * self.sample_rate)
        fade_samples = min(fade_samples, len(audio))

        if fade_type == "in" or fade_type == "in_out":
            envelope = np.linspace(0, 1, fade_samples)
            audio[:fade_samples] *= envelope

        if fade_type == "out" or fade_type == "in_out":
            envelope = np.linspace(1, 0, fade_samples)
            audio[-fade_samples:] *= envelope

        return audio.astype(np.float32)

    def mix(
        self,
        audio_signals: list[np.ndarray],
        weights: list[float] | None = None,
    ) -> np.ndarray:
        """Mix multiple audio signals.

        Args:
            audio_signals: List of audio arrays
            weights: Mixing weights for each signal (default: equal)

        Returns:
            Mixed audio array
        """
        if not audio_signals:
            return np.array([], dtype=np.float32)

        if weights is None:
            weights = [1.0 / len(audio_signals)] * len(audio_signals)

        # Pad signals to same length
        max_len = max(len(s) for s in audio_signals)
        padded = []
        for signal_array in audio_signals:
            if len(signal_array) < max_len:
                padded_sig = np.zeros(max_len, dtype=np.float32)
                padded_sig[: len(signal_array)] = signal_array
                padded.append(padded_sig)
            else:
                padded.append(signal_array.astype(np.float32))

        # Mix with weights
        mixed = np.zeros(max_len, dtype=np.float32)
        for signal_array, weight in zip(padded, weights):
            mixed += signal_array * weight

        return mixed.astype(np.float32)


@dataclass
class SimpleEQ:
    """Simple 3-band EQ filter.

    Provides bass, mid, and treble boost/cut.
    """
    sample_rate: int = 44100
    bass_gain: float = 0.0
    mid_gain: float = 0.0
    treble_gain: float = 0.0

    # Filter coefficients for each band
    _bass_b: np.ndarray = field(default_factory=lambda: np.array([1.0]))
    _bass_a: np.ndarray = field(default_factory=lambda: np.array([1.0]))
    _mid_b: np.ndarray = field(default_factory=lambda: np.array([1.0]))
    _mid_a: np.ndarray = field(default_factory=lambda: np.array([1.0]))
    _treble_b: np.ndarray = field(default_factory=lambda: np.array([1.0]))
    _treble_a: np.ndarray = field(default_factory=lambda: np.array([1.0]))

    def set_band(
        self,
        band: Literal["bass", "mid", "treble"],
        gain_db: float,
    ) -> None:
        """Set EQ band gain.

        Args:
            band: Band to adjust (bass, mid, treble)
            gain_db: Gain adjustment in dB
        """
        if band == "bass":
            self.bass_gain = np.clip(gain_db, -12, 12)
            self._update_bass_filter()
        elif band == "mid":
            self.mid_gain = np.clip(gain_db, -12, 12)
            self._update_mid_filter()
        elif band == "treble":
            self.treble_gain = np.clip(gain_db, -12, 12)
            self._update_treble_filter()

    def _update_bass_filter(self) -> None:
        """Update bass filter coefficients."""
        if self.bass_gain != 0:
            # Simple shelving filter for bass
            freq = 100.0  # Center frequency
            Q = 0.707
            A = 10.0 ** (self.bass_gain / 40.0)
            w0 = 2.0 * np.pi * freq / self.sample_rate
            alpha = np.sin(w0) / (2.0 * Q)

            b0 = A * ((A + 1.0) - (A - 1.0) * np.cos(w0) + 2.0 * np.sqrt(A) * alpha)
            b1 = 2.0 * A * ((A - 1.0) - (A + 1.0) * np.cos(w0))
            b2 = A * ((A + 1.0) - (A - 1.0) * np.cos(w0) - 2.0 * np.sqrt(A) * alpha)
            a0 = (A + 1.0) + (A - 1.0) * np.cos(w0) + 2.0 * np.sqrt(A) * alpha
            a1 = -2.0 * ((A - 1.0) + (A + 1.0) * np.cos(w0))
            a2 = (A + 1.0) + (A - 1.0) * np.cos(w0) - 2.0 * np.sqrt(A) * alpha

            self._bass_b = np.array([b0, b1, b2]) / a0
            self._bass_a = np.array([1.0, a1 / a0, a2 / a0])

    def _update_mid_filter(self) -> None:
        """Update mid filter coefficients."""
        if self.mid_gain != 0:
            freq = 1000.0
            Q = 1.0
            A = 10.0 ** (self.mid_gain / 40.0)
            w0 = 2.0 * np.pi * freq / self.sample_rate
            alpha = np.sin(w0) / (2.0 * Q)

            b0 = 1.0 + alpha * A
            b1 = -2.0 * np.cos(w0)
            b2 = 1.0 - alpha * A
            a0 = 1.0 + alpha / A
            a1 = -2.0 * np.cos(w0)
            a2 = 1.0 - alpha / A

            self._mid_b = np.array([b0, b1, b2]) / a0
            self._mid_a = np.array([1.0, a1 / a0, a2 / a0])

    def _update_treble_filter(self) -> None:
        """Update treble filter coefficients."""
        if self.treble_gain != 0:
            freq = 10000.0
            Q = 0.707
            A = 10.0 ** (self.treble_gain / 40.0)
            w0 = 2.0 * np.pi * freq / self.sample_rate
            alpha = np.sin(w0) / (2.0 * Q)

            b0 = A * ((A + 1.0) + (A - 1.0) * np.cos(w0) + 2.0 * np.sqrt(A) * alpha)
            b1 = -2.0 * A * ((A - 1.0) + (A + 1.0) * np.cos(w0))
            b2 = A * ((A + 1.0) + (A - 1.0) * np.cos(w0) - 2.0 * np.sqrt(A) * alpha)
            a0 = (A + 1.0) - (A - 1.0) * np.cos(w0) + 2.0 * np.sqrt(A) * alpha
            a1 = 2.0 * ((A - 1.0) - (A + 1.0) * np.cos(w0))
            a2 = (A + 1.0) - (A - 1.0) * np.cos(w0) - 2.0 * np.sqrt(A) * alpha

            self._treble_b = np.array([b0, b1, b2]) / a0
            self._treble_a = np.array([1.0, a1 / a0, a2 / a0])

    def process(self, audio: np.ndarray) -> np.ndarray:
        """Process audio with EQ.

        Args:
            audio: Input audio array

        Returns:
            Processed audio
        """
        result = audio.astype(np.float32)

        if self.bass_gain != 0:
            result = signal.filtfilt(self._bass_b, self._bass_a, result)

        if self.mid_gain != 0:
            result = signal.filtfilt(self._mid_b, self._mid_a, result)

        if self.treble_gain != 0:
            result = signal.filtfilt(self._treble_b, self._treble_a, result)

        return result.astype(np.float32)

    def get_band_settings(self) -> dict[str, dict[str, float]]:
        """Get current band settings.

        Returns:
            Dictionary of band settings
        """
        return {
            "bass": {"gain_db": self.bass_gain, "freq_hz": 100.0},
            "mid": {"gain_db": self.mid_gain, "freq_hz": 1000.0},
            "treble": {"gain_db": self.treble_gain, "freq_hz": 10000.0},
        }

    def reset(self) -> None:
        """Reset EQ to flat response."""
        self.bass_gain = 0.0
        self.mid_gain = 0.0
        self.treble_gain = 0.0
        self._bass_b = np.array([1.0])
        self._bass_a = np.array([1.0])
        self._mid_b = np.array([1.0])
        self._mid_a = np.array([1.0])
        self._treble_b = np.array([1.0])
        self._treble_a = np.array([1.0])


@dataclass
class CompressorEffect:
    """Dynamic range compressor.

    Reduces dynamic range of audio signal with configurable
    threshold, ratio, attack, release, and makeup gain.
    """
    sample_rate: int = 44100
    threshold: float = -20.0  # dB
    ratio: float = 4.0
    attack_ms: float = 10.0
    release_ms: float = 100.0
    makeup_gain_db: float = 0.0

    attack_samples: int = field(init=False)
    release_samples: int = field(init=False)
    envelope: float = 0.0

    def __post_init__(self) -> None:
        """Calculate sample counts for attack/release."""
        self.attack_samples = int((self.attack_ms / 1000.0) * self.sample_rate)
        self.release_samples = int((self.release_ms / 1000.0) * self.sample_rate)

    def set_threshold(self, threshold_db: float) -> None:
        """Set compression threshold.

        Args:
            threshold_db: Threshold in dB
        """
        self.threshold = np.clip(threshold_db, -80, 0)

    def set_ratio(self, ratio: float) -> None:
        """Set compression ratio.

        Args:
            ratio: Compression ratio (1 = no compression, >1 = compression)
        """
        self.ratio = max(1.0, ratio)

    def set_attack_ms(self, attack_ms: float) -> None:
        """Set attack time.

        Args:
            attack_ms: Attack time in milliseconds
        """
        self.attack_ms = max(0.1, attack_ms)
        self.attack_samples = int((self.attack_ms / 1000.0) * self.sample_rate)

    def set_release_ms(self, release_ms: float) -> None:
        """Set release time.

        Args:
            release_ms: Release time in milliseconds
        """
        self.release_ms = max(0.1, release_ms)
        self.release_samples = int((self.release_ms / 1000.0) * self.sample_rate)

    def process(self, audio: np.ndarray) -> np.ndarray:
        """Apply compression.

        Args:
            audio: Input audio array

        Returns:
            Compressed audio
        """
        output = np.zeros_like(audio, dtype=np.float32)
        makeup_gain_lin = 10.0 ** (self.makeup_gain_db / 20.0)

        for i in range(len(audio)):
            # Calculate input level in dB
            input_level_db = 20.0 * np.log10(np.abs(audio[i]) + 1e-10)

            # Calculate gain reduction
            if input_level_db > self.threshold:
                gain_reduction_db = (input_level_db - self.threshold) * (1 - 1 / self.ratio)
            else:
                gain_reduction_db = 0.0

            # Smooth gain change with attack/release
            target_envelope = 10.0 ** (-gain_reduction_db / 20.0)

            if target_envelope < self.envelope:
                # Attack phase
                attack_coeff = 1.0 - np.exp(-1.0 / self.attack_samples) if self.attack_samples > 0 else 1.0
                self.envelope += attack_coeff * (target_envelope - self.envelope)
            else:
                # Release phase
                release_coeff = 1.0 - np.exp(-1.0 / self.release_samples) if self.release_samples > 0 else 1.0
                self.envelope += release_coeff * (target_envelope - self.envelope)

            # Apply gain reduction and makeup gain
            output[i] = audio[i] * self.envelope * makeup_gain_lin

        return output.astype(np.float32)


@dataclass
class ReverbEffect:
    """Reverb effect using Schroeder reverberator.

    Creates spacious reverb ambience using parallel comb and
    allpass filters.
    """
    sample_rate: int = 44100
    room_size: float = 0.5
    damping: float = 0.5
    width: float = 1.0
    wet_level: float = 0.3
    dry_level: float = 0.7

    # Comb filter delays (in samples)
    comb_tunings: list[int] = field(default_factory=lambda: [
        1116, 1188, 1277, 1356
    ])
    allpass_tunings: list[int] = field(default_factory=lambda: [
        556, 441, 341, 225
    ])

    # Filter states
    comb_buffers: list[np.ndarray] = field(default_factory=list)
    comb_filter_states: list[float] = field(default_factory=list)
    comb_indexes: list[int] = field(default_factory=list)

    allpass_buffers: list[np.ndarray] = field(default_factory=list)
    allpass_indexes: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Initialize reverb buffers."""
        # Initialize comb filters
        self.comb_buffers = [np.zeros(delay) for delay in self.comb_tunings]
        self.comb_filter_states = [0.0] * len(self.comb_tunings)
        self.comb_indexes = [0] * len(self.comb_tunings)

        # Initialize allpass filters
        self.allpass_buffers = [np.zeros(delay) for delay in self.allpass_tunings]
        self.allpass_indexes = [0] * len(self.allpass_tunings)

    def set_room_size(self, room_size: float) -> None:
        """Set room size (0.0-1.0)."""
        self.room_size = np.clip(room_size, 0.0, 1.0)

    def set_damping(self, damping: float) -> None:
        """Set damping (0.0-1.0)."""
        self.damping = np.clip(damping, 0.0, 1.0)

    def set_wet_dry(self, wet: float, dry: float) -> None:
        """Set wet/dry mix.

        Args:
            wet: Wet level (0.0-1.0)
            dry: Dry level (0.0-1.0)
        """
        self.wet_level = np.clip(wet, 0.0, 1.0)
        self.dry_level = np.clip(dry, 0.0, 1.0)

    def process(self, audio: np.ndarray) -> np.ndarray:
        """Apply reverb.

        Args:
            audio: Input audio array

        Returns:
            Reverb-processed audio
        """
        output = np.zeros(len(audio) + 44100, dtype=np.float32)  # Add tail

        for i in range(len(audio)):
            # Process comb filters in parallel
            comb_out = 0.0
            for j in range(len(self.comb_buffers)):
                buffer = self.comb_buffers[j]
                idx = self.comb_indexes[j]

                # Read from buffer
                comb_out += buffer[idx]

                # Update filter state
                filter_input = audio[i] + buffer[idx] * self.damping
                self.comb_filter_states[j] = filter_input * (1.0 - self.damping) + \
                                             self.comb_filter_states[j] * self.damping

                # Write to buffer with room size factor
                buffer[idx] = self.comb_filter_states[j] * self.room_size

                # Update index
                self.comb_indexes[j] = (idx + 1) % len(buffer)

            # Process allpass filters in series
            allpass_out = comb_out
            for j in range(len(self.allpass_buffers)):
                buffer = self.allpass_buffers[j]
                idx = self.allpass_indexes[j]

                # Allpass filter processing
                buffer_val = buffer[idx]
                buffer[idx] = allpass_out + buffer_val * 0.5
                allpass_out = buffer_val - allpass_out * 0.5

                self.allpass_indexes[j] = (idx + 1) % len(buffer)

            # Mix wet and dry
            output[i] = audio[i] * self.dry_level + allpass_out * self.wet_level

        # Trim to reasonable length
        return output[:len(audio) + 22050].astype(np.float32)


@dataclass
class TimeStretchProcessor:
    """Time stretching processor.

    Stretches or compresses audio duration while optionally
    preserving pitch using phase vocoder techniques.
    """
    sample_rate: int = 44100
    hop_length: int = 512
    n_fft: int = 2048

    def stretch(
        self,
        audio: np.ndarray,
        tempo_ratio: float,
        preserve_pitch: bool = False,
    ) -> np.ndarray:
        """Stretch audio duration.

        Args:
            audio: Input audio array
            tempo_ratio: Stretch ratio (< 1.0 = slower, > 1.0 = faster)
            preserve_pitch: Whether to preserve pitch while stretching

        Returns:
            Time-stretched audio
        """
        if tempo_ratio == 1.0:
            return audio.astype(np.float32)

        if preserve_pitch:
            # Use phase vocoder approach
            return self._phase_vocoder(audio, tempo_ratio)
        else:
            # Simple resampling
            new_length = int(len(audio) / tempo_ratio)
            indices = np.linspace(0, len(audio) - 1, new_length)
            return np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)

    def _phase_vocoder(
        self,
        audio: np.ndarray,
        tempo_ratio: float,
    ) -> np.ndarray:
        """Phase vocoder for pitch-preserving time stretch.

        Args:
            audio: Input audio
            tempo_ratio: Stretch ratio

        Returns:
            Stretched audio
        """
        # STFT with hop length
        D = np.abs(self._stft(audio))

        # Time-stretch magnitude
        stretched_length = int(D.shape[1] / tempo_ratio)
        D_stretched = np.zeros((D.shape[0], stretched_length), dtype=D.dtype)

        for i in range(D.shape[0]):
            D_stretched[i] = np.interp(
                np.arange(stretched_length) * tempo_ratio,
                np.arange(D.shape[1]),
                D[i],
            )

        # Simple reconstruction
        n_frames = D_stretched.shape[1]
        output_length = n_frames * self.hop_length + self.n_fft
        output = np.zeros(output_length, dtype=np.float32)

        # Add frames with overlap
        for i in range(n_frames):
            frame = D_stretched[:, i]
            # Inverse FFT with random phase
            phase = np.random.randn(len(frame)) * np.pi * 2
            stft_frame = frame * np.exp(1j * phase)
            time_frame = np.fft.irfft(stft_frame, n=self.n_fft)

            start_idx = i * self.hop_length
            output[start_idx : start_idx + self.n_fft] += time_frame

        return output[:int(len(audio) / tempo_ratio)].astype(np.float32)

    def _stft(self, audio: np.ndarray) -> np.ndarray:
        """Compute STFT."""
        n_frames = 1 + (len(audio) - self.n_fft) // self.hop_length
        D = np.zeros((self.n_fft // 2 + 1, n_frames), dtype=np.complex128)

        for i in range(n_frames):
            frame = audio[i * self.hop_length : i * self.hop_length + self.n_fft]
            if len(frame) < self.n_fft:
                frame = np.pad(frame, (0, self.n_fft - len(frame)))
            D[:, i] = np.fft.rfft(frame)

        return D


@dataclass
class FrequencyAnalyzer:
    """Frequency analysis and spectral feature extraction."""
    sample_rate: int = 44100
    n_fft: int = 2048

    def compute_spectrum(self, audio: np.ndarray) -> np.ndarray:
        """Compute frequency spectrum.

        Args:
            audio: Input audio array

        Returns:
            Magnitude spectrum
        """
        spectrum = np.abs(fft(audio, n=self.n_fft))
        return spectrum[: len(spectrum) // 2]

    def get_peak_frequency(self, audio: np.ndarray) -> float:
        """Get peak frequency in Hz.

        Args:
            audio: Input audio array

        Returns:
            Peak frequency in Hz
        """
        spectrum = self.compute_spectrum(audio)
        peak_idx = np.argmax(spectrum)
        frequencies = fftfreq(self.n_fft, 1 / self.sample_rate)
        return abs(frequencies[peak_idx])

    def compute_mfcc(self, audio: np.ndarray, n_mfcc: int = 13) -> np.ndarray:
        """Compute Mel-frequency cepstral coefficients.

        Args:
            audio: Input audio array
            n_mfcc: Number of MFCCs to compute

        Returns:
            MFCC array of shape (n_mfcc, n_frames)
        """
        spectrum = np.abs(fft(audio, n=self.n_fft)) ** 2

        # Mel-scale filterbank
        mel_freqs = self._mel_freqs(0, self.sample_rate / 2, n_mfcc + 2)

        # Apply filterbank
        mfcc_array = []
        for i in range(n_mfcc):
            f1, f2, f3 = mel_freqs[i : i + 3]

            # Triangular filter
            f1_idx = int(f1 * self.n_fft / self.sample_rate)
            f2_idx = int(f2 * self.n_fft / self.sample_rate)
            f3_idx = int(f3 * self.n_fft / self.sample_rate)

            if f3_idx - f1_idx > 0:
                val = np.sum(spectrum[f1_idx:f3_idx])
                mfcc_array.append(np.log(max(val, 1e-10)))

        return np.array(mfcc_array).reshape(-1, 1)

    def is_silent(self, audio: np.ndarray, threshold_db: float = -40.0) -> bool:
        """Detect silence.

        Args:
            audio: Input audio array
            threshold_db: Silence threshold in dB

        Returns:
            True if audio is silent
        """
        rms = np.sqrt(np.mean(audio ** 2))
        db = 20.0 * np.log10(max(rms, 1e-10))
        return db < threshold_db

    def get_energy_by_band(
        self,
        audio: np.ndarray,
        n_bands: int = 10,
    ) -> np.ndarray:
        """Get energy in frequency bands.

        Args:
            audio: Input audio array
            n_bands: Number of bands

        Returns:
            Energy in each band
        """
        spectrum = np.abs(fft(audio, n=self.n_fft)) ** 2
        energy_per_band = []

        band_width = len(spectrum) // n_bands
        for i in range(n_bands):
            start = i * band_width
            end = start + band_width if i < n_bands - 1 else len(spectrum)
            energy = np.sum(spectrum[start:end])
            energy_per_band.append(np.log10(max(energy, 1e-10)))

        return np.array(energy_per_band)

    def spectral_centroid(self, audio: np.ndarray) -> float:
        """Calculate spectral centroid.

        Args:
            audio: Input audio array

        Returns:
            Spectral centroid in Hz
        """
        spectrum = np.abs(fft(audio, n=self.n_fft)) ** 2
        freqs = fftfreq(self.n_fft, 1 / self.sample_rate)[: len(spectrum)]

        centroid = np.sum(freqs * spectrum) / (np.sum(spectrum) + 1e-10)
        return abs(centroid)

    def _mel_freqs(self, f_min: float, f_max: float, n: int) -> np.ndarray:
        """Convert Hz to mel scale."""
        mel_min = 2595 * np.log10(1 + f_min / 700)
        mel_max = 2595 * np.log10(1 + f_max / 700)
        mel_points = np.linspace(mel_min, mel_max, n)
        return 700 * (10 ** (mel_points / 2595) - 1)
