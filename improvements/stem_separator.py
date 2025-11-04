# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Real-Time Stem Separation & Audio Decomposition

Provides professional-grade stem separation for DJ mixing:
- Demucs v4 neural network for best quality (9.20 dB SDR)
- Pre-analysis mode for performance (recommended for DJ use)
- Real-time mode for capable systems (high-end hardware)
- Fallback to simpler models for lower-end systems
- Caching system to avoid re-processing
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

# Optional dependency
try:
    import torch
    import torchaudio
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    warnings.warn("PyTorch not installed. Stem separation disabled. "
                  "Install with: pip install torch torchaudio")

# Demucs model
try:
    from demucs.pretrained import get_model
    from demucs.apply import apply_model
    DEMUCS_AVAILABLE = True
except ImportError:
    DEMUCS_AVAILABLE = False
    if TORCH_AVAILABLE:
        warnings.warn("Demucs not installed. Install with: pip install demucs")


class StemType(Enum):
    """Audio stem types."""
    VOCALS = "vocals"
    DRUMS = "drums"
    BASS = "bass"
    OTHER = "other"
    PIANO = "piano"


@dataclass
class StemData:
    """Stem audio data."""
    stem_type: StemType
    audio: np.ndarray  # Shape: (samples,) or (channels, samples)
    sample_rate: int


@dataclass
class SeparationResult:
    """Complete stem separation result."""
    stems: Dict[StemType, np.ndarray]  # stem_type -> audio_data
    sample_rate: int
    model_name: str  # Model used for separation
    processing_time: float  # Seconds
    quality_score: float  # 0.0-1.0, based on model SDR
    file_hash: str  # Hash of input file for caching

    def mix_stems(self, mix_levels: Dict[StemType, float]) -> np.ndarray:
        """
        Mix stems with specified levels.

        Args:
            mix_levels: {StemType: gain} mapping

        Returns:
            Mixed audio
        """
        output = np.zeros_like(list(self.stems.values())[0])

        for stem_type, audio in self.stems.items():
            level = mix_levels.get(stem_type, 1.0)
            output += audio * level

        return output


class StemSeparationMode(Enum):
    """Processing mode for stem separation."""
    OFFLINE = "offline"      # Analyze on import, use cached results
    REALTIME = "realtime"    # Separate during playback (high CPU/GPU)
    HYBRID = "hybrid"        # Known tracks use cache, new tracks realtime


class StemSeparator:
    """
    Neural network-based stem separation using Demucs v4.

    Provides professional audio decomposition for DJ mixing.
    """

    # Quality scores for different models
    MODEL_QUALITY = {
        "htdemucs": 0.95,      # State-of-the-art (9.20 dB SDR)
        "htdemucs_ft": 0.92,   # Fine-tuned variant
        "htdemucs_6s": 0.88,   # 6-stem (less accurate per stem)
        "demucs": 0.85,        # Previous version
    }

    def __init__(self, mode: StemSeparationMode = StemSeparationMode.OFFLINE,
                 model_name: str = "htdemucs",
                 cache_dir: Optional[Path] = None,
                 device: Optional[str] = None):
        """
        Initialize stem separator.

        Args:
            mode: Processing mode (offline/realtime/hybrid)
            model_name: Demucs model to use
            cache_dir: Directory for caching separated stems
            device: Device to use ("cpu", "cuda", "mps", None=auto)
        """
        if not TORCH_AVAILABLE or not DEMUCS_AVAILABLE:
            logger.warning("Torch/Demucs not available - stem separation disabled")
            self.available = False
            return

        self.available = True
        self.mode = mode
        self.model_name = model_name
        self.cache_dir = Path(cache_dir or "stem_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Device selection
        if device is None:
            if torch.cuda.is_available():
                device = "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                device = "mps"
            else:
                device = "cpu"

        self.device = device
        self.model = None
        self.lock = Lock()

        logger.info(f"StemSeparator initialized: model={model_name}, "
                   f"device={device}, mode={mode.value}")

    def _ensure_model_loaded(self) -> bool:
        """Lazy load model."""
        if self.model is None:
            try:
                with self.lock:
                    if self.model is None:
                        self.model = get_model(self.model_name).to(self.device)
                        self.model.eval()
                        logger.info(f"Model loaded: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                return False

        return True

    def _get_cache_path(self, file_hash: str) -> Path:
        """Get cache file path for given hash."""
        return self.cache_dir / f"{file_hash}_{self.model_name}.json"

    def _compute_file_hash(self, audio_data: np.ndarray) -> str:
        """Compute hash of audio data."""
        return hashlib.sha256(audio_data.tobytes()).hexdigest()[:16]

    def _load_from_cache(self, file_hash: str) -> Optional[SeparationResult]:
        """Load cached separation result."""
        cache_path = self._get_cache_path(file_hash)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)

            # Load stem audio files
            stems = {}
            for stem_name in ['vocals', 'drums', 'bass', 'other']:
                stem_path = cache_path.parent / f"{file_hash}_{stem_name}.npy"
                if stem_path.exists():
                    stems[StemType(stem_name)] = np.load(stem_path)

            if len(stems) > 0:
                result = SeparationResult(
                    stems=stems,
                    sample_rate=data['sample_rate'],
                    model_name=data['model_name'],
                    processing_time=data['processing_time'],
                    quality_score=data['quality_score'],
                    file_hash=file_hash
                )
                logger.info(f"Loaded cached separation: {file_hash}")
                return result

        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")

        return None

    def _save_to_cache(self, result: SeparationResult) -> bool:
        """Save separation result to cache."""
        try:
            cache_path = self._get_cache_path(result.file_hash)

            # Save metadata
            metadata = {
                'sample_rate': result.sample_rate,
                'model_name': result.model_name,
                'processing_time': result.processing_time,
                'quality_score': result.quality_score
            }

            with open(cache_path, 'w') as f:
                json.dump(metadata, f)

            # Save stem audio
            for stem_type, audio in result.stems.items():
                stem_path = cache_path.parent / f"{result.file_hash}_{stem_type.value}.npy"
                np.save(stem_path, audio)

            logger.info(f"Cached separation: {result.file_hash}")
            return True

        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")
            return False

    def separate_audio(self, audio: np.ndarray, sr: int) -> Optional[SeparationResult]:
        """
        Separate audio into stems.

        Args:
            audio: Audio samples (mono or stereo)
            sr: Sample rate

        Returns:
            SeparationResult with stems, or None if separation failed
        """
        if not self.available:
            logger.error("Stem separation not available")
            return None

        # Check cache first
        file_hash = self._compute_file_hash(audio)
        cached = self._load_from_cache(file_hash)
        if cached:
            return cached

        # Load model if needed
        if not self._ensure_model_loaded():
            return None

        try:
            import time
            start_time = time.time()

            # Prepare audio for Demucs
            # Expected: torch tensor, shape (channels, samples)
            if audio.ndim == 1:
                audio = np.stack([audio, audio])  # Convert mono to stereo
            elif audio.shape[0] > audio.shape[1]:
                audio = audio.T  # Ensure (channels, samples) format

            # Convert to torch tensor
            audio_tensor = torch.from_numpy(audio).float().to(self.device)

            # Perform separation
            with torch.no_grad():
                stems_dict = apply_model(
                    self.model,
                    audio_tensor.unsqueeze(0),  # Add batch dimension
                    device=self.device,
                    progress=False
                )

            processing_time = time.time() - start_time

            # Extract stems (Demucs returns: drums, bass, other, vocals)
            stems = {}
            stem_order = [StemType.DRUMS, StemType.BASS, StemType.OTHER, StemType.VOCALS]

            for stem_type, stem_tensor in zip(stem_order, stems_dict):
                # Convert back to numpy
                stem_audio = stem_tensor.cpu().numpy()

                # Average channels if needed
                if stem_audio.ndim > 1 and stem_audio.shape[0] > 1:
                    stem_audio = np.mean(stem_audio, axis=0)
                elif stem_audio.ndim > 1:
                    stem_audio = stem_audio[0]

                stems[stem_type] = stem_audio

            # Create result
            quality_score = self.MODEL_QUALITY.get(self.model_name, 0.85)

            result = SeparationResult(
                stems=stems,
                sample_rate=sr,
                model_name=self.model_name,
                processing_time=processing_time,
                quality_score=quality_score,
                file_hash=file_hash
            )

            # Cache result
            self._save_to_cache(result)

            logger.info(f"Separated audio: {processing_time:.2f}s, "
                       f"quality={quality_score:.2f}")

            return result

        except Exception as e:
            logger.error(f"Separation failed: {e}")
            return None

    def separate_file(self, audio_file: str) -> Optional[SeparationResult]:
        """
        Load and separate audio file.

        Args:
            audio_file: Path to audio file

        Returns:
            SeparationResult or None
        """
        try:
            # Load audio
            audio, sr = torchaudio.load(audio_file)
            audio = audio.numpy()

            return self.separate_audio(audio, sr)

        except Exception as e:
            logger.error(f"Failed to load file: {e}")
            return None

    def get_cache_size(self) -> int:
        """Get total cache size in bytes."""
        total = 0
        for file in self.cache_dir.glob("*.npy"):
            total += file.stat().st_size
        return total

    def clear_cache(self) -> int:
        """
        Clear all cached separations.

        Returns:
            Number of files deleted
        """
        count = 0
        for file in self.cache_dir.glob("*.npy"):
            file.unlink()
            count += 1
        for file in self.cache_dir.glob("*.json"):
            file.unlink()
            count += 1

        logger.info(f"Cache cleared: {count} files")
        return count


class SimpleStemFallback:
    """
    Fallback stem separator using basic frequency filtering.

    For systems without PyTorch. Quality is lower but enables basic functionality.
    """

    def __init__(self):
        """Initialize fallback separator."""
        self.model_name = "frequency_filter"
        logger.warning("Using fallback stem separator (lower quality)")

    def separate_audio(self, audio: np.ndarray, sr: int) -> Optional[SeparationResult]:
        """
        Separate using simple frequency filtering.

        Args:
            audio: Audio samples
            sr: Sample rate

        Returns:
            SeparationResult with basic stems
        """
        from scipy import signal

        # Design filters
        drums_low = 200
        bass_low = 40
        bass_high = 200

        # Create separation using filters
        # This is very basic and not suitable for production

        # Bass: <200Hz
        bass_sos = signal.butter(4, [bass_low, bass_high], btype='band', fs=sr, output='sos')
        bass = signal.sosfilt(bass_sos, audio)

        # Drums: 200-5000Hz
        drums_sos = signal.butter(4, [drums_low, 5000], btype='band', fs=sr, output='sos')
        drums = signal.sosfilt(drums_sos, audio)

        # Vocals: >2000Hz (simplified)
        vocals_sos = signal.butter(4, 2000, btype='high', fs=sr, output='sos')
        vocals = signal.sosfilt(vocals_sos, audio)

        # Other: everything else
        other = audio - bass - drums - vocals

        return SeparationResult(
            stems={
                StemType.VOCALS: vocals,
                StemType.DRUMS: drums,
                StemType.BASS: bass,
                StemType.OTHER: other
            },
            sample_rate=sr,
            model_name=self.model_name,
            processing_time=0.0,
            quality_score=0.3,  # Very low quality
            file_hash="fallback"
        )


def get_stem_separator(
    mode: StemSeparationMode = StemSeparationMode.OFFLINE,
    use_fallback: bool = True
) -> Optional[StemSeparator]:
    """
    Get appropriate stem separator for system.

    Args:
        mode: Processing mode
        use_fallback: Use SimpleStemFallback if Torch/Demucs unavailable

    Returns:
        StemSeparator or SimpleStemFallback or None
    """
    if TORCH_AVAILABLE and DEMUCS_AVAILABLE:
        return StemSeparator(mode=mode)

    if use_fallback:
        logger.warning("Using fallback stem separator")
        return SimpleStemFallback()

    return None
