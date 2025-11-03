# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Beat Analysis and Detection Module

Provides music information retrieval capabilities including:
- BPM/Tempo detection
- Beat tracking
- Onset detection
- Key/harmonic analysis

Based on librosa library and industry-standard algorithms.
"""

import logging
import numpy as np
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass
import warnings

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    warnings.warn("librosa not installed. Beat analysis features disabled. "
                  "Install with: pip install librosa")

logger = logging.getLogger(__name__)


@dataclass
class BeatAnalysisResult:
    """Result of beat analysis on a track."""

    tempo: float  # BPM
    beats: np.ndarray  # Beat frames
    beat_times: np.ndarray  # Beat times in seconds
    onsets: np.ndarray  # Onset frames
    onset_times: np.ndarray  # Onset times in seconds
    onset_strength: np.ndarray  # Onset strength envelope
    confidence: float  # Confidence 0.0-1.0

    def is_valid(self) -> bool:
        """Check if analysis result is valid."""
        return (
            self.tempo > 0 and
            len(self.beats) > 0 and
            self.confidence > 0.3
        )


@dataclass
class KeyAnalysisResult:
    """Result of key/harmonic analysis."""

    key: str  # e.g., 'A', 'C#'
    scale: str  # 'major' or 'minor'
    confidence: float  # 0.0-1.0

    def is_valid(self) -> bool:
        """Check if key analysis is valid."""
        return self.confidence > 0.5


class BeatAnalyzer:
    """
    Analyzes beat, tempo, and rhythm information from audio.

    Uses librosa for music information retrieval (MIR).
    """

    def __init__(self, sr: int = 44100, hop_length: int = 512):
        """
        Initialize beat analyzer.

        Args:
            sr: Sample rate
            hop_length: Hop length for STFT
        """
        if not LIBROSA_AVAILABLE:
            raise RuntimeError("librosa is required for beat analysis. "
                             "Install with: pip install librosa")

        self.sr = sr
        self.hop_length = hop_length

    def analyze_file(self, audio_file: str) -> Optional[BeatAnalysisResult]:
        """
        Analyze beat information from audio file.

        Args:
            audio_file: Path to audio file

        Returns:
            BeatAnalysisResult or None on error
        """
        try:
            # Load audio
            logger.info(f"Loading audio file: {audio_file}")
            y, sr = librosa.load(audio_file, sr=self.sr)

            # Perform analysis
            return self.analyze_audio(y, sr)

        except Exception as e:
            logger.error(f"Error analyzing file {audio_file}: {e}")
            return None

    def analyze_audio(self, y: np.ndarray, sr: int) -> BeatAnalysisResult:
        """
        Analyze beat information from audio array.

        Args:
            y: Audio time series
            sr: Sample rate

        Returns:
            BeatAnalysisResult
        """
        logger.info("Analyzing beat structure...")

        # Beat tracking (core algorithm)
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)

        # Convert beats from frames to time
        beat_times = librosa.frames_to_time(beats, sr=sr)

        # Onset detection
        logger.info("Detecting onsets...")
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        onsets = librosa.util.peak_pick(
            onset_env,
            pre_max=3,
            post_max=3,
            pre_avg=3,
            post_avg=3,
            delta=0.1,
            wait=10
        )
        onset_times = librosa.frames_to_time(onsets, sr=sr)

        # Confidence estimation
        # Based on onset strength at beat locations
        if len(beats) > 0:
            beat_strengths = onset_env[np.minimum(beats, len(onset_env)-1)]
            confidence = float(np.mean(beat_strengths))
        else:
            confidence = 0.0

        return BeatAnalysisResult(
            tempo=float(tempo),
            beats=beats,
            beat_times=beat_times,
            onsets=onsets,
            onset_times=onset_times,
            onset_strength=onset_env,
            confidence=confidence
        )

    def get_next_beat(self, beat_times: np.ndarray,
                     current_time: float) -> Optional[float]:
        """
        Get next beat time after current position.

        Args:
            beat_times: Array of beat times
            current_time: Current playback time in seconds

        Returns:
            Time of next beat or None
        """
        future_beats = beat_times[beat_times > current_time]
        if len(future_beats) > 0:
            return float(future_beats[0])
        return None

    def get_sync_offset(self, beat_times: np.ndarray,
                       current_time: float) -> float:
        """
        Get offset from current position to nearest beat.

        Useful for beat-synchronous effects.

        Args:
            beat_times: Array of beat times
            current_time: Current playback time in seconds

        Returns:
            Offset in seconds (-0.5 to +0.5)
        """
        # Find nearest beat
        if len(beat_times) == 0:
            return 0.0

        idx = np.searchsorted(beat_times, current_time)

        # Get surrounding beats
        if idx == 0:
            nearest = beat_times[0]
        elif idx >= len(beat_times):
            nearest = beat_times[-1]
        else:
            # Choose closer of two adjacent beats
            before = beat_times[idx - 1]
            after = beat_times[idx]
            nearest = before if abs(current_time - before) < abs(current_time - after) else after

        offset = current_time - nearest

        # Clamp to -0.5 to +0.5 beat duration
        if len(beat_times) > 1:
            beat_duration = beat_times[1] - beat_times[0]
            offset = np.clip(offset, -beat_duration/2, beat_duration/2)

        return float(offset)


class TempoEstimator:
    """
    Estimates tempo/BPM using various methods.
    """

    @staticmethod
    def estimate_from_onsets(onset_env: np.ndarray,
                           sr: int,
                           hop_length: int = 512,
                           start_bpm: int = 120,
                           tightness: float = 100) -> float:
        """
        Estimate tempo from onset strength envelope.

        More flexible than beat_track for edge cases.

        Args:
            onset_env: Onset strength envelope
            sr: Sample rate
            hop_length: Hop length used to compute onset_env
            start_bpm: Initial BPM guess
            tightness: Tempo preference strength (0-400+)

        Returns:
            Estimated BPM
        """
        # Use dynamic programming for tempo estimation
        ac = librosa.util.autocorrelate(onset_env)

        # Compute lag in frames
        frame_duration = hop_length / sr

        # Search for periodic structure
        max_lag = len(ac) // 2
        ac = ac[:max_lag]

        # Find peaks in autocorrelation
        peaks, _ = librosa.util.peak_pick(ac, pre_max=3, post_max=3,
                                         pre_avg=3, post_avg=3, delta=0.1, wait=10)

        if len(peaks) == 0:
            return float(start_bpm)

        # Convert peaks to BPM
        lag_frames = peaks[0]
        if lag_frames > 0:
            lag_seconds = lag_frames * frame_duration
            bpm = 60.0 / lag_seconds
        else:
            bpm = float(start_bpm)

        return bpm


class HarmonicAnalyzer:
    """
    Analyzes harmonic content and key signature.
    """

    @staticmethod
    def estimate_key(y: np.ndarray, sr: int) -> KeyAnalysisResult:
        """
        Estimate musical key from audio.

        Uses chromagram and template matching.

        Args:
            y: Audio time series
            sr: Sample rate

        Returns:
            KeyAnalysisResult
        """
        # Compute chromagram (12-bin representation of pitch classes)
        chromagram = librosa.feature.chroma_cqt(y=y, sr=sr)

        # Average chromagram over time
        chroma_mean = np.mean(chromagram, axis=1)

        # Template matching for major and minor keys
        major_template = np.array([1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0], dtype=float)
        minor_template = np.array([1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 1], dtype=float)

        # Normalize templates
        major_template /= np.linalg.norm(major_template)
        minor_template /= np.linalg.norm(minor_template)
        chroma_mean /= (np.linalg.norm(chroma_mean) + 1e-10)

        # Compute correlations
        major_corr = np.correlate(chroma_mean, major_template, mode='same')
        minor_corr = np.correlate(chroma_mean, minor_template, mode='same')

        # Find root note (which pitch class is strongest)
        root_idx = np.argmax(chroma_mean)

        # Find scale (major or minor)
        is_major = np.max(major_corr) > np.max(minor_corr)

        # Note names
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F',
                     'F#', 'G', 'G#', 'A', 'A#', 'B']

        key = note_names[root_idx]
        scale = 'major' if is_major else 'minor'
        confidence = float(np.max([np.max(major_corr), np.max(minor_corr)]))

        return KeyAnalysisResult(
            key=key,
            scale=scale,
            confidence=confidence
        )


def analyze_track(audio_file: str, sr: int = 44100) -> Dict[str, Any]:
    """
    Comprehensive track analysis.

    Analyzes beat, tempo, key, and other musical features.

    Args:
        audio_file: Path to audio file
        sr: Sample rate

    Returns:
        Dictionary with analysis results
    """
    if not LIBROSA_AVAILABLE:
        logger.warning("librosa not available - returning empty analysis")
        return {}

    results = {
        'file': audio_file,
        'beat': None,
        'key': None,
        'error': None
    }

    try:
        # Beat analysis
        analyzer = BeatAnalyzer(sr=sr)
        beat_result = analyzer.analyze_file(audio_file)
        results['beat'] = beat_result

        # Key analysis
        if beat_result and beat_result.is_valid():
            y, sr = librosa.load(audio_file, sr=sr)
            key_result = HarmonicAnalyzer.estimate_key(y, sr)
            results['key'] = key_result

    except Exception as e:
        logger.error(f"Error analyzing track {audio_file}: {e}")
        results['error'] = str(e)

    return results
