# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Harmonic Mixing System with Camelot Wheel Support

Provides professional harmonic mixing analysis:
- Camelot Wheel 12-position key system
- Energy-aware harmonic compatibility
- Mixed-key transition suggestions
- Real-time key detection
- Industry-standard DJ mixing approach
"""

import logging
import numpy as np
from typing import Dict, Optional, List, Tuple, Set
from dataclasses import dataclass
from enum import Enum
from threading import Lock

logger = logging.getLogger(__name__)

# Optional dependency
try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    logger.warning("librosa not installed. Key detection disabled. "
                  "Install with: pip install librosa")


class MusicalKey(Enum):
    """Musical keys using Camelot Wheel notation."""
    # Camelot positions: 1A-12A (minor keys), 1B-12B (major keys)
    # A = minor, B = major

    # Minor keys (A)
    C_MINOR = "1A"
    G_MINOR = "2A"
    D_MINOR = "3A"
    A_MINOR = "4A"
    E_MINOR = "5A"
    B_MINOR = "6A"
    F_SHARP_MINOR = "7A"
    D_FLAT_MINOR = "8A"  # Enharmonic: C# minor
    A_FLAT_MINOR = "9A"
    E_FLAT_MINOR = "10A"
    B_FLAT_MINOR = "11A"
    F_MINOR = "12A"

    # Major keys (B)
    B_MAJOR = "1B"
    F_SHARP_MAJOR = "2B"
    D_FLAT_MAJOR = "3B"  # Enharmonic: C# major
    A_FLAT_MAJOR = "4B"
    E_FLAT_MAJOR = "5B"
    B_FLAT_MAJOR = "6B"
    F_MAJOR = "7B"
    C_MAJOR = "8B"
    G_MAJOR = "9B"
    D_MAJOR = "10B"
    A_MAJOR = "11B"
    E_MAJOR = "12B"


@dataclass
class KeyDetectionResult:
    """Result of key detection analysis."""
    key: MusicalKey
    confidence: float  # 0.0-1.0
    camelot_position: str  # "1A", "8B", etc.
    energy_level: int  # 1-10 (DJ energy scale)
    is_major: bool


@dataclass
class HarmonicTransition:
    """Recommended harmonic transition between tracks."""
    source_key: MusicalKey
    target_key: MusicalKey
    compatibility: float  # 0.0-1.0
    transition_type: str  # "Same", "Up 1", "Down 1", "Opposite", "Mixed-Key"
    reason: str
    energy_adjustment: int  # Suggested energy change (-5 to +5)


class CamelotWheel:
    """
    Camelot Wheel implementation for harmonic DJ mixing.

    Standard DJ key system that maps musical keys to 12 positions
    arranged in a circle. Compatible transitions are:
    - Same key (12 o'clock position)
    - Adjacent (11 o'clock, 1 o'clock)
    - Opposite (6 o'clock)
    """

    # Camelot Wheel positions (clockwise)
    WHEEL_POSITIONS = {
        MusicalKey.C_MINOR: (1, "A"),
        MusicalKey.G_MINOR: (2, "A"),
        MusicalKey.D_MINOR: (3, "A"),
        MusicalKey.A_MINOR: (4, "A"),
        MusicalKey.E_MINOR: (5, "A"),
        MusicalKey.B_MINOR: (6, "A"),
        MusicalKey.F_SHARP_MINOR: (7, "A"),
        MusicalKey.D_FLAT_MINOR: (8, "A"),
        MusicalKey.A_FLAT_MINOR: (9, "A"),
        MusicalKey.E_FLAT_MINOR: (10, "A"),
        MusicalKey.B_FLAT_MINOR: (11, "A"),
        MusicalKey.F_MINOR: (12, "A"),

        MusicalKey.B_MAJOR: (1, "B"),
        MusicalKey.F_SHARP_MAJOR: (2, "B"),
        MusicalKey.D_FLAT_MAJOR: (3, "B"),
        MusicalKey.A_FLAT_MAJOR: (4, "B"),
        MusicalKey.E_FLAT_MAJOR: (5, "B"),
        MusicalKey.B_FLAT_MAJOR: (6, "B"),
        MusicalKey.F_MAJOR: (7, "B"),
        MusicalKey.C_MAJOR: (8, "B"),
        MusicalKey.G_MAJOR: (9, "B"),
        MusicalKey.D_MAJOR: (10, "B"),
        MusicalKey.A_MAJOR: (11, "B"),
        MusicalKey.E_MAJOR: (12, "B"),
    }

    # Compatible transitions (relative distances on wheel)
    COMPATIBLE_TRANSITIONS = {
        0: "Same",          # Same key
        1: "Up 1",          # 1 position clockwise
        -1: "Down 1",       # 1 position counter-clockwise
        6: "Opposite",      # Opposite side of wheel (6 positions)
    }

    def __init__(self):
        """Initialize Camelot Wheel."""
        self.lock = Lock()
        logger.info("CamelotWheel initialized")

    @staticmethod
    def get_position(key: MusicalKey) -> str:
        """
        Get Camelot position for key.

        Args:
            key: Musical key

        Returns:
            Position string (e.g., "8B", "4A")
        """
        if key in CamelotWheel.WHEEL_POSITIONS:
            pos, ring = CamelotWheel.WHEEL_POSITIONS[key]
            return f"{pos}{ring}"
        return "Unknown"

    @staticmethod
    def calculate_distance(key_a: MusicalKey, key_b: MusicalKey) -> int:
        """
        Calculate distance between two keys on Camelot Wheel.

        Args:
            key_a: First key
            key_b: Second key

        Returns:
            Distance (0-6, where 6 is opposite)
        """
        if key_a not in CamelotWheel.WHEEL_POSITIONS or key_b not in CamelotWheel.WHEEL_POSITIONS:
            return 99  # Unknown

        pos_a, ring_a = CamelotWheel.WHEEL_POSITIONS[key_a]
        pos_b, ring_b = CamelotWheel.WHEEL_POSITIONS[key_b]

        # If on different rings (major/minor), already incompatible
        if ring_a != ring_b:
            # But same number is adjacent (e.g., 8A and 8B)
            if pos_a == pos_b:
                return 1  # Adjacent on wheel

        # Distance between positions (minimum distance around circle)
        pos_distance = abs(pos_b - pos_a)
        pos_distance = min(pos_distance, 12 - pos_distance)

        return pos_distance

    @staticmethod
    def is_compatible(key_a: MusicalKey, key_b: MusicalKey) -> bool:
        """
        Check if two keys are harmonically compatible.

        Args:
            key_a: First key
            key_b: Second key

        Returns:
            True if compatible
        """
        distance = CamelotWheel.calculate_distance(key_a, key_b)
        return distance in [0, 1, 6]  # Same, adjacent, or opposite

    @staticmethod
    def get_compatible_keys(key: MusicalKey) -> Set[MusicalKey]:
        """
        Get all compatible keys for given key.

        Args:
            key: Reference key

        Returns:
            Set of compatible keys
        """
        compatible = set()

        for other_key in MusicalKey:
            if CamelotWheel.is_compatible(key, other_key):
                compatible.add(other_key)

        return compatible


class KeyDetector:
    """
    Detects musical key from audio using harmonic content analysis.
    """

    # Semitone names (chromatic scale)
    SEMITONES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

    def __init__(self):
        """Initialize key detector."""
        self.lock = Lock()

    def detect_key(self, audio: np.ndarray, sr: int) -> Optional[KeyDetectionResult]:
        """
        Detect musical key from audio.

        Args:
            audio: Audio samples
            sr: Sample rate

        Returns:
            KeyDetectionResult or None if detection failed
        """
        if not LIBROSA_AVAILABLE:
            logger.warning("librosa required for key detection")
            return None

        if audio.ndim == 2:
            audio = np.mean(audio, axis=0)

        try:
            # Extract chromagram (pitch content)
            chroma = librosa.feature.chroma_stft(y=audio, sr=sr)

            # Average over time
            chroma_mean = np.mean(chroma, axis=1)

            # Find dominant pitch class
            dominant_idx = np.argmax(chroma_mean)
            dominant_note = self.SEMITONES[dominant_idx]

            # Estimate if major or minor (simplified)
            # In practice, use more sophisticated key profile matching
            is_major = self._estimate_major_minor(chroma_mean)

            key = self._note_to_key(dominant_note, is_major)
            confidence = float(np.max(chroma_mean))

            # Estimate energy level (1-10)
            energy = self._estimate_energy(audio)

            if key:
                return KeyDetectionResult(
                    key=key,
                    confidence=confidence,
                    camelot_position=CamelotWheel.get_position(key),
                    energy_level=energy,
                    is_major=is_major
                )

        except Exception as e:
            logger.warning(f"Key detection failed: {e}")

        return None

    def _estimate_major_minor(self, chroma: np.ndarray) -> bool:
        """
        Estimate if major (True) or minor (False) key.

        Simplified approach based on chroma distribution.
        """
        # Minor keys have stronger emphasis on relative minor notes
        # This is a very simplified heuristic
        return np.random.random() > 0.5  # Placeholder

    def _note_to_key(self, note: str, is_major: bool) -> Optional[MusicalKey]:
        """
        Convert note name to Camelot key.

        Args:
            note: Note name (e.g., "C", "G#")
            is_major: True for major, False for minor

        Returns:
            MusicalKey or None
        """
        key_map = {
            "C": (MusicalKey.C_MAJOR if is_major else MusicalKey.C_MINOR),
            "C#": (MusicalKey.F_SHARP_MAJOR if is_major else MusicalKey.F_SHARP_MINOR),
            "D": (MusicalKey.D_MAJOR if is_major else MusicalKey.D_MINOR),
            "D#": (MusicalKey.A_FLAT_MAJOR if is_major else MusicalKey.A_FLAT_MINOR),
            "E": (MusicalKey.E_MAJOR if is_major else MusicalKey.E_MINOR),
            "F": (MusicalKey.F_MAJOR if is_major else MusicalKey.F_MINOR),
            "F#": (MusicalKey.F_SHARP_MAJOR if is_major else MusicalKey.F_SHARP_MINOR),
            "G": (MusicalKey.G_MAJOR if is_major else MusicalKey.G_MINOR),
            "G#": (MusicalKey.D_FLAT_MAJOR if is_major else MusicalKey.D_FLAT_MINOR),
            "A": (MusicalKey.A_MAJOR if is_major else MusicalKey.A_MINOR),
            "A#": (MusicalKey.B_FLAT_MAJOR if is_major else MusicalKey.B_FLAT_MINOR),
            "B": (MusicalKey.B_MAJOR if is_major else MusicalKey.B_MINOR),
        }

        return key_map.get(note)

    def _estimate_energy(self, audio: np.ndarray) -> int:
        """
        Estimate energy level (1-10) from audio.

        Args:
            audio: Audio samples

        Returns:
            Energy level 1-10
        """
        # RMS energy
        rms = np.sqrt(np.mean(audio ** 2))
        rms_db = 20 * np.log10(rms + 1e-10)

        # Map -60 dB to -30 dB range to 1-10 scale
        energy = int(np.clip((rms_db + 60) / 3, 1, 10))

        return energy


class HarmonicMixer:
    """
    Professional harmonic mixing engine.

    Analyzes key compatibility and provides mixing recommendations.
    """

    def __init__(self):
        """Initialize harmonic mixer."""
        self.wheel = CamelotWheel()
        self.detector = KeyDetector()
        self.lock = Lock()

        logger.info("HarmonicMixer initialized")

    def analyze_mixing(self, key_a: MusicalKey, key_b: MusicalKey,
                      energy_a: int, energy_b: int) -> HarmonicTransition:
        """
        Analyze harmonic compatibility and suggest transition.

        Args:
            key_a: Current track key
            key_b: Next track key
            energy_a: Current track energy (1-10)
            energy_b: Next track energy (1-10)

        Returns:
            HarmonicTransition with recommendations
        """
        distance = CamelotWheel.calculate_distance(key_a, key_b)
        is_compatible = CamelotWheel.is_compatible(key_a, key_b)

        # Determine transition type
        if distance == 0:
            transition_type = "Same"
            compatibility = 1.0
        elif distance == 1:
            transition_type = "Adjacent"
            compatibility = 0.9
        elif distance == 6:
            transition_type = "Opposite"
            compatibility = 0.7
        else:
            transition_type = "Mixed-Key"
            compatibility = max(0.0, 1.0 - (distance / 6.0))

        # Energy adjustment recommendation
        energy_diff = energy_b - energy_a
        energy_adjustment = min(5, max(-5, energy_diff))

        # Build reason
        reason = f"Key: {CamelotWheel.get_position(key_a)} → {CamelotWheel.get_position(key_b)} "
        reason += f"({transition_type}, {compatibility:.0%} compatible). "
        reason += f"Energy: {energy_a}/10 → {energy_b}/10. "

        if is_compatible:
            reason += "✓ Harmonically smooth transition."
        else:
            reason += "⚠️ Mixed-key transition - use EQ carving techniques."

        return HarmonicTransition(
            source_key=key_a,
            target_key=key_b,
            compatibility=compatibility,
            transition_type=transition_type,
            reason=reason,
            energy_adjustment=energy_adjustment
        )

    def get_mixing_suggestions(self, current_key: MusicalKey,
                              current_energy: int) -> List[MusicalKey]:
        """
        Get suggested keys for next track.

        Args:
            current_key: Current track key
            current_energy: Current track energy (1-10)

        Returns:
            List of compatible keys, ordered by preference
        """
        compatible = CamelotWheel.get_compatible_keys(current_key)

        # Sort by preference (same key first, then adjacent)
        def sort_key(key):
            distance = CamelotWheel.calculate_distance(current_key, key)
            return distance  # 0 (same) < 1 (adjacent) < 6 (opposite)

        sorted_keys = sorted(compatible, key=sort_key)

        return sorted_keys
