# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Advanced Cueing System

Provides professional DJ cueing capabilities including:
- Cue point management (main cue and hot cues)
- Auto-cue (automatic first beat detection)
- Loop points
- Memory banks for cue storage
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
import numpy as np

logger = logging.getLogger(__name__)


class CueType(Enum):
    """Types of cue points."""
    MAIN = "main"          # Primary cue point
    HOT_CUE = "hot_cue"    # Performance pad cue (8 available)
    LOOP_START = "loop_start"
    LOOP_END = "loop_end"


@dataclass
class CuePoint:
    """Represents a single cue point."""

    time_seconds: float  # Position in seconds
    cue_type: CueType
    name: str = ""
    color: str = "#ffffff"  # Color for visualization
    hot_cue_index: int = -1  # 0-7 for hot cues

    def __post_init__(self):
        """Validate cue point."""
        if self.time_seconds < 0:
            raise ValueError("Cue time cannot be negative")

        if self.cue_type == CueType.HOT_CUE:
            if not (0 <= self.hot_cue_index <= 7):
                raise ValueError("Hot cue index must be 0-7")


@dataclass
class LoopInfo:
    """Information about a loop region."""

    start_time: float  # Loop start in seconds
    end_time: float    # Loop end in seconds
    name: str = "Loop"
    is_active: bool = False

    @property
    def duration(self) -> float:
        """Get loop duration in seconds."""
        return self.end_time - self.start_time

    def is_valid(self) -> bool:
        """Check if loop is valid."""
        return (
            self.start_time >= 0 and
            self.end_time > self.start_time
        )


class CueingSystem:
    """
    Professional DJ cueing system with memory banks and hot cues.
    """

    # Standard hot cue colors (DJ software convention)
    HOT_CUE_COLORS = [
        "#ff0000",  # Red
        "#00ff00",  # Green
        "#0000ff",  # Blue
        "#ffff00",  # Yellow
        "#ff00ff",  # Magenta
        "#00ffff",  # Cyan
        "#ffa500",  # Orange
        "#800080",  # Purple
    ]

    def __init__(self, track_duration_seconds: float):
        """
        Initialize cueing system.

        Args:
            track_duration_seconds: Total track duration in seconds
        """
        self.track_duration = track_duration_seconds
        self.lock = Lock()

        # Main cue point
        self.main_cue: Optional[CuePoint] = None

        # Hot cues (8 available, indexed 0-7)
        self.hot_cues: Dict[int, CuePoint] = {}

        # Loop points
        self.loops: List[LoopInfo] = []
        self.active_loop: Optional[LoopInfo] = None

        # Memory banks for saving/loading cues
        self.memory_banks: Dict[int, Dict] = {}  # 0-7 banks

        logger.info(f"CueingSystem initialized for {track_duration_seconds}s track")

    def set_main_cue(self, time_seconds: float, name: str = "Main Cue") -> CuePoint:
        """
        Set the main cue point.

        Args:
            time_seconds: Cue position in seconds
            name: Cue name

        Returns:
            CuePoint object
        """
        with self.lock:
            if time_seconds < 0 or time_seconds > self.track_duration:
                raise ValueError(
                    f"Cue time {time_seconds} outside track duration "
                    f"(0-{self.track_duration})"
                )

            self.main_cue = CuePoint(
                time_seconds=time_seconds,
                cue_type=CueType.MAIN,
                name=name
            )

            logger.info(f"Main cue set to {time_seconds:.2f}s")

        return self.main_cue

    def set_hot_cue(self, hot_cue_index: int, time_seconds: float,
                   name: str = "") -> CuePoint:
        """
        Set a hot cue point.

        Args:
            hot_cue_index: Hot cue number (0-7)
            time_seconds: Cue position in seconds
            name: Cue name

        Returns:
            CuePoint object

        Raises:
            ValueError if index out of range
        """
        if not (0 <= hot_cue_index <= 7):
            raise ValueError("Hot cue index must be 0-7")

        with self.lock:
            if time_seconds < 0 or time_seconds > self.track_duration:
                raise ValueError(
                    f"Cue time {time_seconds} outside track duration"
                )

            cue = CuePoint(
                time_seconds=time_seconds,
                cue_type=CueType.HOT_CUE,
                name=name or f"Hot Cue {hot_cue_index + 1}",
                color=self.HOT_CUE_COLORS[hot_cue_index],
                hot_cue_index=hot_cue_index
            )

            self.hot_cues[hot_cue_index] = cue

            logger.info(f"Hot cue {hot_cue_index} set to {time_seconds:.2f}s")

        return cue

    def clear_hot_cue(self, hot_cue_index: int) -> bool:
        """
        Clear a hot cue.

        Args:
            hot_cue_index: Hot cue number (0-7)

        Returns:
            True if cleared, False if didn't exist
        """
        with self.lock:
            if hot_cue_index in self.hot_cues:
                del self.hot_cues[hot_cue_index]
                logger.info(f"Hot cue {hot_cue_index} cleared")
                return True
            return False

    def get_hot_cue(self, hot_cue_index: int) -> Optional[CuePoint]:
        """Get a hot cue point."""
        with self.lock:
            return self.hot_cues.get(hot_cue_index)

    def get_all_hot_cues(self) -> Dict[int, CuePoint]:
        """Get all hot cues."""
        with self.lock:
            return self.hot_cues.copy()

    def create_loop(self, start_time: float, end_time: float,
                   name: str = "Loop") -> LoopInfo:
        """
        Create a loop region.

        Args:
            start_time: Loop start in seconds
            end_time: Loop end in seconds
            name: Loop name

        Returns:
            LoopInfo object
        """
        with self.lock:
            if start_time < 0 or end_time > self.track_duration:
                raise ValueError("Loop times outside track duration")

            if end_time <= start_time:
                raise ValueError("Loop end must be after start")

            loop = LoopInfo(
                start_time=start_time,
                end_time=end_time,
                name=name
            )

            self.loops.append(loop)

            logger.info(f"Loop created: {start_time:.2f}s - {end_time:.2f}s")

        return loop

    def activate_loop(self, loop_index: int) -> bool:
        """
        Activate a loop for playback.

        Args:
            loop_index: Index in loops list

        Returns:
            True if activated
        """
        with self.lock:
            if not (0 <= loop_index < len(self.loops)):
                return False

            # Deactivate others
            for loop in self.loops:
                loop.is_active = False

            # Activate this one
            self.loops[loop_index].is_active = True
            self.active_loop = self.loops[loop_index]

            logger.info(f"Loop {loop_index} activated")

        return True

    def deactivate_loop(self) -> None:
        """Deactivate current loop."""
        with self.lock:
            if self.active_loop:
                self.active_loop.is_active = False
                self.active_loop = None
                logger.info("Loop deactivated")

    def get_active_loop(self) -> Optional[LoopInfo]:
        """Get currently active loop."""
        with self.lock:
            return self.active_loop

    def auto_cue_from_beat(self, beat_times: np.ndarray) -> Optional[CuePoint]:
        """
        Automatically set main cue to first beat.

        Args:
            beat_times: Array of beat times in seconds (from beat_analyzer)

        Returns:
            Set CuePoint or None
        """
        if len(beat_times) == 0:
            logger.warning("No beats available for auto-cue")
            return None

        # Set to first beat
        first_beat_time = float(beat_times[0])

        return self.set_main_cue(first_beat_time, "Auto Cue (First Beat)")

    def save_memory_bank(self, bank_index: int) -> bool:
        """
        Save current cues to memory bank.

        Args:
            bank_index: Bank number (0-7)

        Returns:
            True if saved
        """
        if not (0 <= bank_index <= 7):
            return False

        with self.lock:
            self.memory_banks[bank_index] = {
                'main_cue': self.main_cue,
                'hot_cues': self.hot_cues.copy(),
                'loops': [
                    {
                        'start': loop.start_time,
                        'end': loop.end_time,
                        'name': loop.name
                    }
                    for loop in self.loops
                ]
            }

            logger.info(f"Cues saved to memory bank {bank_index}")

        return True

    def load_memory_bank(self, bank_index: int) -> bool:
        """
        Load cues from memory bank.

        Args:
            bank_index: Bank number (0-7)

        Returns:
            True if loaded
        """
        if bank_index not in self.memory_banks:
            return False

        with self.lock:
            bank_data = self.memory_banks[bank_index]

            self.main_cue = bank_data.get('main_cue')
            self.hot_cues = bank_data.get('hot_cues', {}).copy()

            # Restore loops
            self.loops = []
            for loop_data in bank_data.get('loops', []):
                loop = LoopInfo(
                    start_time=loop_data['start'],
                    end_time=loop_data['end'],
                    name=loop_data['name']
                )
                self.loops.append(loop)

            logger.info(f"Cues loaded from memory bank {bank_index}")

        return True

    def get_cue_points_for_display(self) -> List[Tuple[float, str, str]]:
        """
        Get all cue points for visualization.

        Returns:
            List of (time_seconds, name, color) tuples
        """
        cue_points = []

        with self.lock:
            if self.main_cue:
                cue_points.append((
                    self.main_cue.time_seconds,
                    self.main_cue.name,
                    "#ff0000"  # Red for main
                ))

            for cue in self.hot_cues.values():
                cue_points.append((
                    cue.time_seconds,
                    cue.name,
                    cue.color
                ))

            for loop in self.loops:
                cue_points.append((
                    loop.start_time,
                    f"{loop.name} (start)",
                    "#00ff00"
                ))
                cue_points.append((
                    loop.end_time,
                    f"{loop.name} (end)",
                    "#00ff00"
                ))

        return sorted(cue_points, key=lambda x: x[0])

    def get_cue_statistics(self) -> Dict[str, int]:
        """Get statistics about cues."""
        with self.lock:
            return {
                'main_cue': 1 if self.main_cue else 0,
                'hot_cues': len(self.hot_cues),
                'loops': len(self.loops),
                'active_loops': sum(1 for l in self.loops if l.is_active),
                'memory_banks': len(self.memory_banks)
            }


class AutoCueEngine:
    """
    Analyzes track structure for intelligent auto-cue placement.
    """

    @staticmethod
    def detect_intro_length(onset_times: np.ndarray,
                          beat_times: np.ndarray) -> float:
        """
        Detect intro length by finding first regular beat pattern.

        Args:
            onset_times: Onset detection times
            beat_times: Detected beat times

        Returns:
            Estimated intro length in seconds
        """
        if len(beat_times) < 4:
            return 0.0

        # Intro typically ends when regular beat pattern starts
        # Look for first beat with consistent spacing after it
        beat_intervals = np.diff(beat_times)

        if len(beat_intervals) == 0:
            return beat_times[0] if len(beat_times) > 0 else 0.0

        median_interval = np.median(beat_intervals)

        # Find first position with regular beat spacing
        for i, interval in enumerate(beat_intervals):
            if abs(interval - median_interval) < 0.1:  # Within 100ms
                return float(beat_times[i])

        return float(beat_times[0])

    @staticmethod
    def detect_outro_start(beat_times: np.ndarray,
                         track_duration: float) -> float:
        """
        Detect outro start by analyzing beat pattern at end.

        Args:
            beat_times: Detected beat times
            track_duration: Total track duration in seconds

        Returns:
            Estimated outro start in seconds
        """
        if len(beat_times) < 4:
            return track_duration

        # Outro typically starts when beat spacing becomes irregular
        beat_intervals = np.diff(beat_times)
        median_interval = np.median(beat_intervals)

        # Search from end for irregular spacing
        for i in range(len(beat_intervals) - 1, 0, -1):
            if abs(beat_intervals[i] - median_interval) > 0.2:  # >200ms deviation
                return float(beat_times[i])

        # Default: last quarter of track
        return track_duration * 0.75
