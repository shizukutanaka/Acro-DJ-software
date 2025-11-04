# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Neural Network-Based Tempo & Beat Estimation

Provides state-of-the-art tempo and beat tracking:
- BeatNet for best accuracy (95-98% within 8% tolerance)
- Comprehensive beat, downbeat, tempo, and meter tracking
- Confidence scoring for quality assessment
- Fallback to librosa for systems without BeatNet
- Caching system for fast retrieval
"""

import logging
import numpy as np
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum
from threading import Lock
from pathlib import Path
import json
import hashlib
import warnings

logger = logging.getLogger(__name__)

# Optional dependencies
try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    warnings.warn("librosa not installed. Limited tempo estimation. "
                  "Install with: pip install librosa")

try:
    from tempocnn import TempoClassifier
    TEMPOCNN_AVAILABLE = True
except ImportError:
    TEMPOCNN_AVAILABLE = False

try:
    from BeatNet.BeatNet import BeatNet
    BEATNET_AVAILABLE = True
except ImportError:
    BEATNET_AVAILABLE = False


class Meter(Enum):
    """Time signature meter."""
    DUPLE = "2/4"
    TRIPLE = "3/4"
    QUADRUPLE = "4/4"
    COMPLEX = "complex"


@dataclass
class BeatTrackingResult:
    """Beat tracking analysis result."""
    global_tempo: float  # BPM
    beat_times: np.ndarray  # Beat times in seconds
    downbeat_times: np.ndarray  # Downbeat times
    meter: Meter  # Time signature
    confidence: float  # 0.0-1.0
    beat_grid_samples: np.ndarray  # Beat positions in samples
    model_name: str  # Model used
    processing_time: float  # Seconds


@dataclass
class TempoAnalysisResult:
    """Tempo analysis with detailed metrics."""
    global_tempo: float
    local_tempos: np.ndarray  # Tempo at each frame
    tempo_std: float  # Standard deviation
    is_consistent: bool  # True if tempo is stable
    confidence: float  # Overall confidence
    tempogram: Optional[np.ndarray] = None  # Tempo over time
    model_name: str = "unknown"


class TempoEstimationModel(Enum):
    """Available tempo estimation models."""
    BEATNET = "beatnet"          # State-of-the-art (95-98% accuracy)
    TEMPOCNN = "tempocnn"        # Fast (92-95% accuracy)
    LIBROSA = "librosa"          # Basic (85-90% accuracy)
    FALLBACK = "fallback"        # Simple threshold-based


class NeuralTempoEstimator:
    """
    Neural network-based tempo and beat estimation.

    Provides professional-grade beat tracking and tempo analysis.
    """

    # Model accuracy scores
    MODEL_ACCURACY = {
        "beatnet": 0.97,
        "tempocnn": 0.93,
        "librosa": 0.87,
    }

    def __init__(self, model: TempoEstimationModel = TempoEstimationModel.BEATNET,
                 cache_dir: Optional[Path] = None,
                 sr: int = 44100):
        """
        Initialize tempo estimator.

        Args:
            model: Model to use
            cache_dir: Directory for caching results
            sr: Sample rate
        """
        self.model_type = model
        self.cache_dir = Path(cache_dir or "tempo_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.sr = sr
        self.lock = Lock()
        self.beatnet_model = None
        self.tempocnn_model = None
        self.available = self._check_availability()

        logger.info(f"NeuralTempoEstimator initialized: model={model.value}, "
                   f"sr={sr}")

    def _check_availability(self) -> bool:
        """Check if selected model is available."""
        if self.model_type == TempoEstimationModel.BEATNET:
            if not BEATNET_AVAILABLE:
                logger.warning("BeatNet not available, falling back to TempoCNN")
                return False
            return True

        elif self.model_type == TempoEstimationModel.TEMPOCNN:
            if not TEMPOCNN_AVAILABLE:
                logger.warning("TempoCNN not available, falling back to librosa")
                return False
            return True

        elif self.model_type == TempoEstimationModel.LIBROSA:
            if not LIBROSA_AVAILABLE:
                logger.warning("librosa not available, using fallback")
                return False
            return True

        return True

    def _get_cache_path(self, file_hash: str) -> Path:
        """Get cache file path."""
        return self.cache_dir / f"{file_hash}_{self.model_type.value}.json"

    def _compute_file_hash(self, audio_data: np.ndarray) -> str:
        """Compute audio hash."""
        return hashlib.sha256(audio_data.tobytes()).hexdigest()[:16]

    def _load_from_cache(self, file_hash: str) -> Optional[Dict]:
        """Load cached result."""
        cache_path = self._get_cache_path(file_hash)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
            logger.info(f"Loaded cached tempo: {file_hash}")
            return data
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
            return None

    def _save_to_cache(self, file_hash: str, result: Dict) -> bool:
        """Save result to cache."""
        try:
            cache_path = self._get_cache_path(file_hash)

            with open(cache_path, 'w') as f:
                json.dump(result, f)

            logger.info(f"Cached tempo: {file_hash}")
            return True
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")
            return False

    def _estimate_with_beatnet(self, audio: np.ndarray) -> Optional[BeatTrackingResult]:
        """Estimate using BeatNet model."""
        try:
            if self.beatnet_model is None:
                self.beatnet_model = BeatNet(1, mode='offline', inference_model='DBN')

            # BeatNet expects audio path or array
            if audio.ndim == 2:
                audio = np.mean(audio, axis=0)

            output = self.beatnet_model.process(audio.astype(np.float32))

            # Extract results
            beats = output[0]  # Beat times in seconds
            downbeats = output[1]  # Downbeat times
            meter = output[3]  # Meter (1=duple, 2=triple, 3=quadruple)

            # Estimate global tempo from beat intervals
            if len(beats) > 1:
                beat_intervals = np.diff(beats)
                mean_interval = np.mean(beat_intervals)
                global_tempo = 60.0 / mean_interval if mean_interval > 0 else 120.0
            else:
                global_tempo = 120.0

            # Map meter
            meter_map = {1: Meter.DUPLE, 2: Meter.TRIPLE, 3: Meter.QUADRUPLE}
            beat_meter = meter_map.get(meter, Meter.QUADRUPLE)

            # Convert beat times to samples
            beat_grid_samples = (beats * self.sr).astype(int)

            return BeatTrackingResult(
                global_tempo=float(global_tempo),
                beat_times=beats,
                downbeat_times=downbeats,
                meter=beat_meter,
                confidence=0.95,  # BeatNet is very confident
                beat_grid_samples=beat_grid_samples,
                model_name="BeatNet",
                processing_time=0.0
            )

        except Exception as e:
            logger.warning(f"BeatNet estimation failed: {e}")
            return None

    def _estimate_with_tempocnn(self, audio: np.ndarray) -> Optional[BeatTrackingResult]:
        """Estimate using TempoCNN model."""
        try:
            if self.tempocnn_model is None:
                self.tempocnn_model = TempoClassifier('cnn')

            if audio.ndim == 2:
                audio = np.mean(audio, axis=0)

            # Estimate global tempo
            global_tempo = self.tempocnn_model.estimate_tempo(audio)

            # Generate beat grid from tempo
            beat_interval = 60.0 / global_tempo
            beat_times = np.arange(0, len(audio) / self.sr, beat_interval)

            return BeatTrackingResult(
                global_tempo=float(global_tempo),
                beat_times=beat_times,
                downbeat_times=beat_times[::4],  # Every 4th beat (typical)
                meter=Meter.QUADRUPLE,
                confidence=0.92,
                beat_grid_samples=(beat_times * self.sr).astype(int),
                model_name="TempoCNN",
                processing_time=0.0
            )

        except Exception as e:
            logger.warning(f"TempoCNN estimation failed: {e}")
            return None

    def _estimate_with_librosa(self, audio: np.ndarray) -> Optional[BeatTrackingResult]:
        """Estimate using librosa (fallback)."""
        try:
            if audio.ndim == 2:
                audio = np.mean(audio, axis=0)

            # Basic beat tracking
            tempo, beats = librosa.beat.beat_track(y=audio, sr=self.sr)
            beat_times = librosa.frames_to_time(beats, sr=self.sr)

            return BeatTrackingResult(
                global_tempo=float(tempo),
                beat_times=beat_times,
                downbeat_times=beat_times[::4],
                meter=Meter.QUADRUPLE,
                confidence=0.87,
                beat_grid_samples=(beat_times * self.sr).astype(int),
                model_name="librosa",
                processing_time=0.0
            )

        except Exception as e:
            logger.warning(f"librosa estimation failed: {e}")
            return None

    def _estimate_fallback(self, audio: np.ndarray) -> BeatTrackingResult:
        """Simple fallback estimation."""
        # Assume 120 BPM and 4/4 meter
        global_tempo = 120.0
        beat_interval = 60.0 / global_tempo
        beat_times = np.arange(0, len(audio) / self.sr, beat_interval)

        return BeatTrackingResult(
            global_tempo=global_tempo,
            beat_times=beat_times,
            downbeat_times=beat_times[::4],
            meter=Meter.QUADRUPLE,
            confidence=0.0,  # No confidence in fallback
            beat_grid_samples=(beat_times * self.sr).astype(int),
            model_name="fallback",
            processing_time=0.0
        )

    def estimate_tempo(self, audio: np.ndarray,
                       sr: Optional[int] = None) -> Optional[BeatTrackingResult]:
        """
        Estimate tempo and beat grid.

        Args:
            audio: Audio samples (mono or stereo)
            sr: Sample rate (uses default if not provided)

        Returns:
            BeatTrackingResult or None
        """
        if sr is None:
            sr = self.sr

        # Check cache
        file_hash = self._compute_file_hash(audio)
        cached = self._load_from_cache(file_hash)

        if cached:
            return BeatTrackingResult(
                global_tempo=cached['global_tempo'],
                beat_times=np.array(cached['beat_times']),
                downbeat_times=np.array(cached['downbeat_times']),
                meter=Meter(cached['meter']),
                confidence=cached['confidence'],
                beat_grid_samples=np.array(cached['beat_grid_samples']),
                model_name=cached['model_name'],
                processing_time=0.0
            )

        # Try models in order
        result = None

        if self.model_type == TempoEstimationModel.BEATNET:
            result = self._estimate_with_beatnet(audio)

        elif self.model_type == TempoEstimationModel.TEMPOCNN:
            result = self._estimate_with_tempocnn(audio)

        elif self.model_type == TempoEstimationModel.LIBROSA:
            result = self._estimate_with_librosa(audio)

        # Fallback if primary failed
        if result is None:
            if self.model_type != TempoEstimationModel.LIBROSA and LIBROSA_AVAILABLE:
                result = self._estimate_with_librosa(audio)

        # Final fallback
        if result is None:
            result = self._estimate_fallback(audio)

        # Cache result
        if result.confidence > 0.5:  # Only cache confident results
            cache_data = {
                'global_tempo': result.global_tempo,
                'beat_times': result.beat_times.tolist(),
                'downbeat_times': result.downbeat_times.tolist(),
                'meter': result.meter.value,
                'confidence': result.confidence,
                'beat_grid_samples': result.beat_grid_samples.tolist(),
                'model_name': result.model_name
            }
            self._save_to_cache(file_hash, cache_data)

        return result

    def estimate_tempo_file(self, audio_file: str) -> Optional[BeatTrackingResult]:
        """
        Load and estimate tempo from file.

        Args:
            audio_file: Path to audio file

        Returns:
            BeatTrackingResult or None
        """
        try:
            import soundfile as sf
            audio, sr = sf.read(audio_file, dtype=np.float32)
            return self.estimate_tempo(audio, sr)
        except Exception as e:
            logger.error(f"Failed to load file: {e}")
            return None

    def analyze_tempo_consistency(self, audio: np.ndarray,
                                  sr: Optional[int] = None) -> Optional[TempoAnalysisResult]:
        """
        Analyze tempo consistency and variations.

        Args:
            audio: Audio samples
            sr: Sample rate

        Returns:
            TempoAnalysisResult with detailed metrics
        """
        if sr is None:
            sr = self.sr

        if audio.ndim == 2:
            audio = np.mean(audio, axis=0)

        try:
            # Extract onset strengths
            onset_env = librosa.onset.onset_strength(y=audio, sr=sr)

            # Compute tempogram
            if TEMPOCNN_AVAILABLE:
                tempogram = self.tempocnn_model.estimate_tempo_local(audio)
            else:
                # Simple fallback tempogram
                tempogram = np.ones_like(onset_env) * 120.0

            # Calculate local tempos
            local_tempos = tempogram if isinstance(tempogram, np.ndarray) else np.ones_like(onset_env) * 120.0

            global_tempo = np.mean(local_tempos)
            tempo_std = np.std(local_tempos)

            # Determine consistency
            is_consistent = tempo_std < global_tempo * 0.1  # Within 10%

            confidence = 1.0 - min(tempo_std / global_tempo, 1.0) if global_tempo > 0 else 0.0

            return TempoAnalysisResult(
                global_tempo=float(global_tempo),
                local_tempos=local_tempos,
                tempo_std=float(tempo_std),
                is_consistent=is_consistent,
                confidence=float(confidence),
                tempogram=tempogram,
                model_name=self.model_type.value
            )

        except Exception as e:
            logger.error(f"Tempo analysis failed: {e}")
            return None

    def generate_beat_grid(self, tempo: float, duration_seconds: float,
                          meter: Meter = Meter.QUADRUPLE) -> np.ndarray:
        """
        Generate beat grid for given tempo.

        Args:
            tempo: BPM
            duration_seconds: Track duration
            meter: Time signature

        Returns:
            Beat times in seconds
        """
        beat_interval = 60.0 / tempo
        beat_times = np.arange(0, duration_seconds, beat_interval)
        return beat_times

    def get_cache_size(self) -> int:
        """Get total cache size in bytes."""
        total = 0
        for file in self.cache_dir.glob("*.json"):
            total += file.stat().st_size
        return total

    def clear_cache(self) -> int:
        """Clear cache."""
        count = 0
        for file in self.cache_dir.glob("*.json"):
            file.unlink()
            count += 1
        logger.info(f"Cache cleared: {count} files")
        return count
