# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Real-Time Spectrum Analyzer

Provides FFT-based frequency domain analysis for visualization.
Designed for low-latency, real-time audio visualization.
"""

import logging
import numpy as np
from typing import Optional, Tuple
from dataclasses import dataclass
from collections import deque
from threading import Lock
import warnings

try:
    from scipy import signal
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    warnings.warn("scipy not available. Some spectrum analysis features disabled.")

logger = logging.getLogger(__name__)


@dataclass
class SpectrumData:
    """Real-time spectrum data for visualization."""

    frequencies: np.ndarray  # Frequency bins in Hz
    magnitudes: np.ndarray  # Magnitude for each frequency (linear scale)
    magnitudes_db: np.ndarray  # Magnitude in dB scale
    peak_frequencies: np.ndarray  # Frequencies of peaks
    peak_magnitudes: np.ndarray  # Magnitudes at peaks
    rms: float  # RMS energy level


class CircularSpectralBuffer:
    """
    Circular buffer for spectral smoothing.

    Maintains history of FFT frames for temporal smoothing.
    """

    def __init__(self, n_frames: int = 4, n_bins: int = 512):
        """
        Initialize buffer.

        Args:
            n_frames: Number of frames to keep in history
            n_bins: Number of frequency bins
        """
        self.n_frames = n_frames
        self.n_bins = n_bins
        self.buffer = deque(maxlen=n_frames)
        self.lock = Lock()

    def add_frame(self, spectrum: np.ndarray) -> None:
        """Add spectrum frame to buffer."""
        with self.lock:
            self.buffer.append(spectrum.copy())

    def get_smoothed(self, method: str = 'mean') -> np.ndarray:
        """
        Get smoothed spectrum from buffer.

        Args:
            method: 'mean', 'median', or 'max'

        Returns:
            Smoothed spectrum
        """
        with self.lock:
            if len(self.buffer) == 0:
                return np.zeros(self.n_bins)

            stack = np.array(list(self.buffer))

            if method == 'median':
                return np.median(stack, axis=0)
            elif method == 'max':
                return np.max(stack, axis=0)
            else:  # mean
                return np.mean(stack, axis=0)


class SpectrumAnalyzer:
    """
    Real-time FFT-based spectrum analyzer.

    Computes frequency domain representation of audio for visualization.
    """

    def __init__(self, sr: int = 44100, n_fft: int = 1024,
                 window: str = 'hann', smoothing_frames: int = 4):
        """
        Initialize spectrum analyzer.

        Args:
            sr: Sample rate in Hz
            n_fft: FFT size
            window: Window function ('hann', 'hamming', 'blackman')
            smoothing_frames: Number of frames for temporal smoothing
        """
        self.sr = sr
        self.n_fft = n_fft
        self.window_type = window
        self.smoothing_frames = smoothing_frames

        # Create window function
        self.window = self._create_window(window, n_fft)

        # Frequency bins
        self.frequencies = np.fft.rfftfreq(n_fft, 1/sr)

        # Spectral buffer for smoothing
        self.buffer = CircularSpectralBuffer(
            n_frames=smoothing_frames,
            n_bins=len(self.frequencies)
        )

        # Peak detection parameters
        self.peak_detection_height = 0.1  # dB above noise floor

        logger.info(f"Spectrum analyzer initialized: "
                   f"{sr}Hz, FFT={n_fft}, window={window}")

    @staticmethod
    def _create_window(window_type: str, n_fft: int) -> np.ndarray:
        """Create window function."""
        if window_type == 'hann':
            return signal.hann(n_fft, sym=False) if SCIPY_AVAILABLE else \
                   np.hanning(n_fft)
        elif window_type == 'hamming':
            return signal.hamming(n_fft, sym=False) if SCIPY_AVAILABLE else \
                   np.hamming(n_fft)
        elif window_type == 'blackman':
            return signal.blackman(n_fft, sym=False) if SCIPY_AVAILABLE else \
                   np.blackman(n_fft)
        else:
            return signal.windows.get_window(window_type, n_fft) if SCIPY_AVAILABLE else \
                   np.hanning(n_fft)

    def analyze_frame(self, audio_chunk: np.ndarray) -> SpectrumData:
        """
        Analyze single audio frame.

        Args:
            audio_chunk: Audio frame (1D array)

        Returns:
            SpectrumData with frequency domain information
        """
        # Ensure correct length
        if len(audio_chunk) < self.n_fft:
            audio_chunk = np.pad(audio_chunk,
                               (0, self.n_fft - len(audio_chunk)))
        elif len(audio_chunk) > self.n_fft:
            audio_chunk = audio_chunk[:self.n_fft]

        # Apply window function
        windowed = audio_chunk * self.window

        # Compute FFT
        spectrum = np.fft.rfft(windowed)

        # Compute magnitude spectrum (linear)
        magnitudes = np.abs(spectrum)

        # Normalize by FFT size and window energy
        window_energy = np.sum(self.window ** 2)
        magnitudes = 2.0 * magnitudes / (self.sr * window_energy + 1e-10)

        # Convert to dB (20 * log10)
        magnitude_floor = 1e-10
        magnitudes_db = 20.0 * np.log10(magnitudes + magnitude_floor)

        # Add to smoothing buffer
        self.buffer.add_frame(magnitudes_db)

        # Get smoothed spectrum
        smoothed = self.buffer.get_smoothed('mean')

        # Detect peaks
        peak_frequencies, peak_magnitudes = self._detect_peaks(
            smoothed,
            self.frequencies
        )

        # RMS energy
        rms = float(np.sqrt(np.mean(windowed ** 2)))

        return SpectrumData(
            frequencies=self.frequencies,
            magnitudes=magnitudes,
            magnitudes_db=smoothed,
            peak_frequencies=peak_frequencies,
            peak_magnitudes=peak_magnitudes,
            rms=rms
        )

    def _detect_peaks(self, spectrum_db: np.ndarray,
                     frequencies: np.ndarray,
                     min_distance: int = 5) -> Tuple[np.ndarray, np.ndarray]:
        """
        Detect spectral peaks.

        Args:
            spectrum_db: Spectrum in dB
            frequencies: Frequency array
            min_distance: Minimum distance between peaks (bins)

        Returns:
            (peak_frequencies, peak_magnitudes)
        """
        if not SCIPY_AVAILABLE:
            # Fallback: return highest peak
            idx = np.argmax(spectrum_db)
            return np.array([frequencies[idx]]), np.array([spectrum_db[idx]])

        # Find peaks above noise floor
        noise_floor = np.percentile(spectrum_db, 20)
        threshold = noise_floor + self.peak_detection_height

        peaks, _ = signal.find_peaks(spectrum_db, height=threshold,
                                    distance=min_distance)

        if len(peaks) == 0:
            # Return maximum if no peaks found
            idx = np.argmax(spectrum_db)
            peaks = np.array([idx])

        # Limit to top 10 peaks
        magnitudes_at_peaks = spectrum_db[peaks]
        top_indices = np.argsort(-magnitudes_at_peaks)[:10]
        peaks = peaks[top_indices]

        return frequencies[peaks], spectrum_db[peaks]

    def get_display_data(self, n_bands: int = 64,
                        freq_scale: str = 'log') -> np.ndarray:
        """
        Get spectrum data suitable for visualization.

        Args:
            n_bands: Number of frequency bands for display
            freq_scale: 'linear' or 'log' frequency scaling

        Returns:
            Array of magnitudes for each display band
        """
        current = self.buffer.get_smoothed('mean')

        if freq_scale == 'log':
            # Logarithmic frequency spacing (like human hearing)
            return self._resample_log(current, n_bands)
        else:
            # Linear frequency spacing
            indices = np.linspace(0, len(current)-1, n_bands, dtype=int)
            return current[indices]

    def _resample_log(self, spectrum: np.ndarray, n_bands: int) -> np.ndarray:
        """Resample spectrum to logarithmic frequency scale."""
        n_freq = len(spectrum)

        # Create logarithmic frequency indices
        freq_indices = np.logspace(
            np.log10(1),  # Start at bin 1
            np.log10(n_freq),
            n_bands,
            dtype=int
        ) - 1

        # Clamp to valid range
        freq_indices = np.clip(freq_indices, 0, n_freq - 1)

        return spectrum[freq_indices]


class EQAnalyzer:
    """
    Analyzes equalizer-specific bands.

    Focuses on standard EQ bands: sub, bass, low-mid, mid, high-mid, treble.
    """

    # Standard EQ band centers (Hz)
    STANDARD_BANDS = {
        'sub': 60,
        'bass': 250,
        'low_mid': 500,
        'mid': 2000,
        'high_mid': 4000,
        'treble': 10000
    }

    BAND_WIDTHS = {
        'sub': 100,
        'bass': 150,
        'low_mid': 300,
        'mid': 1000,
        'high_mid': 1500,
        'treble': 3000
    }

    def __init__(self, analyzer: SpectrumAnalyzer):
        """
        Initialize EQ analyzer.

        Args:
            analyzer: SpectrumAnalyzer instance to use
        """
        self.analyzer = analyzer

    def get_eq_bands(self, spectrum_data: SpectrumData) -> dict:
        """
        Extract standard EQ band levels.

        Args:
            spectrum_data: SpectrumData from analyzer

        Returns:
            Dictionary mapping band names to dB levels
        """
        eq_levels = {}

        frequencies = spectrum_data.frequencies
        magnitudes_db = spectrum_data.magnitudes_db

        for band_name, center_freq in self.STANDARD_BANDS.items():
            bandwidth = self.BAND_WIDTHS[band_name]

            # Find frequencies in this band
            mask = (frequencies >= center_freq - bandwidth/2) & \
                   (frequencies <= center_freq + bandwidth/2)

            if np.any(mask):
                # Average magnitude in band
                band_level = np.mean(magnitudes_db[mask])
            else:
                band_level = -80.0  # Silent

            eq_levels[band_name] = band_level

        return eq_levels


class MultiChannelAnalyzer:
    """
    Analyzes multiple audio channels simultaneously.
    """

    def __init__(self, n_channels: int = 2, sr: int = 44100,
                 n_fft: int = 1024):
        """Initialize multi-channel analyzer."""
        self.n_channels = n_channels
        self.analyzers = [SpectrumAnalyzer(sr, n_fft) for _ in range(n_channels)]

    def analyze_frame(self, audio_multichannel: np.ndarray) -> list:
        """
        Analyze multi-channel audio.

        Args:
            audio_multichannel: Shape (n_channels, n_samples)

        Returns:
            List of SpectrumData, one per channel
        """
        results = []

        # Handle both (n_channels, n_samples) and (n_samples,) formats
        if audio_multichannel.ndim == 1:
            audio_multichannel = audio_multichannel.reshape(1, -1)

        for i, analyzer in enumerate(self.analyzers):
            if i < audio_multichannel.shape[0]:
                result = analyzer.analyze_frame(audio_multichannel[i])
                results.append(result)
            else:
                # Return empty result for missing channels
                results.append(SpectrumData(
                    frequencies=analyzer.frequencies,
                    magnitudes=np.zeros_like(analyzer.frequencies),
                    magnitudes_db=np.zeros_like(analyzer.frequencies),
                    peak_frequencies=np.array([]),
                    peak_magnitudes=np.array([]),
                    rms=0.0
                ))

        return results
