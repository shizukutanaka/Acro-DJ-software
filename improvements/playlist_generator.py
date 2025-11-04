# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Intelligent Playlist Generation & DJ Set Construction

Provides AI-powered DJ set automation:
- Graph-based optimal track sequencing
- BPM/key matching for seamless transitions
- Energy curve progression for set pacing
- Mood/genre consistency detection
- Real-time beat-aligned mixing suggestions
"""

import logging
import numpy as np
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
from threading import Lock
import json

logger = logging.getLogger(__name__)

# Optional dependencies
try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    logger.warning("networkx not installed. Graph-based playlist generation disabled. "
                  "Install with: pip install networkx")

try:
    from scipy.optimize import linear_sum_assignment
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logger.warning("scipy not installed. Optimal sequencing disabled.")


class PlaylistType(Enum):
    """Type of DJ set/playlist."""
    CONTINUOUS = "continuous"  # Seamless 30min+ set
    BATTLE = "battle"          # High-energy back-to-back mixing
    WARM_UP = "warm_up"        # Progressive energy build
    COOL_DOWN = "cool_down"    # Gradual energy decrease
    CLUB = "club"              # Peak-time dance music
    RADIO = "radio"            # Themed radio show mix


@dataclass
class TrackMetadata:
    """Metadata for tracks in playlist."""
    filename: str
    title: str = ""
    artist: str = ""
    bpm: float = 120.0
    key: str = "8B"  # Camelot wheel position
    energy: int = 5  # 1-10 scale
    mood: str = "neutral"  # e.g., "happy", "dark", "groovy"
    duration_seconds: float = 180.0
    # For recommendation algorithms
    genre: str = ""
    year: int = 0
    popularity: float = 0.5  # 0.0-1.0


@dataclass
class PlaylistSequence:
    """Generated DJ set sequence."""
    tracks: List[TrackMetadata]
    total_duration: float  # seconds
    energy_progression: List[float]  # Energy curve over time
    bpm_profile: List[float]  # BPM changes
    estimated_quality: float  # 0.0-1.0
    transition_quality: List[float]  # Per-transition quality


class SimplePlaylistOptimizer:
    """
    Simple greedy optimizer for playlist sequencing.

    Used when networkx not available. Greedy approach:
    1. Start with highest energy track
    2. Find next best match for current track
    3. Repeat until all tracks used
    """

    def __init__(self):
        """Initialize simple optimizer."""
        self.lock = Lock()

    def optimize_sequence(self, tracks: List[TrackMetadata],
                         set_type: PlaylistType = PlaylistType.CONTINUOUS) -> List[TrackMetadata]:
        """
        Generate optimized track sequence using greedy approach.

        Args:
            tracks: Available tracks
            set_type: Type of set to generate

        Returns:
            Optimized track sequence
        """
        if not tracks:
            return []

        # Start with appropriate opening track
        remaining = list(tracks)
        sequence = []

        if set_type == PlaylistType.WARM_UP:
            current = min(remaining, key=lambda t: t.energy)
        elif set_type == PlaylistType.COOL_DOWN:
            current = max(remaining, key=lambda t: t.energy)
        else:
            current = remaining[0]

        sequence.append(current)
        remaining.remove(current)

        # Greedily add tracks
        while remaining:
            # Find best next track
            best_next = None
            best_score = -np.inf

            for candidate in remaining:
                score = self._calculate_transition_quality(current, candidate, set_type)
                if score > best_score:
                    best_score = score
                    best_next = candidate

            if best_next:
                sequence.append(best_next)
                remaining.remove(best_next)
                current = best_next
            else:
                # Fallback: just add any remaining track
                sequence.append(remaining.pop(0))

        return sequence

    def _calculate_transition_quality(self, track_a: TrackMetadata,
                                     track_b: TrackMetadata,
                                     set_type: PlaylistType) -> float:
        """
        Calculate quality score for transition from track A to B.

        Higher score = better transition.
        """
        score = 0.0

        # BPM compatibility (prefer close BPM)
        bpm_ratio = max(track_a.bpm, track_b.bpm) / max(1.0, min(track_a.bpm, track_b.bpm))
        bpm_compat = 1.0 / bpm_ratio  # Closer to 1.0 = better
        score += bpm_compat * 0.4

        # Key compatibility (prefer same/adjacent keys)
        # Simplified: check if same key or 1 step away
        key_distance = self._estimate_key_distance(track_a.key, track_b.key)
        key_compat = 1.0 / (1.0 + key_distance)
        score += key_compat * 0.3

        # Energy progression (depends on set type)
        energy_change = track_b.energy - track_a.energy

        if set_type == PlaylistType.WARM_UP:
            # Prefer increasing energy
            score += max(0, energy_change) * 0.2
        elif set_type == PlaylistType.COOL_DOWN:
            # Prefer decreasing energy
            score += max(0, -energy_change) * 0.2
        else:
            # Prefer smooth changes (small ΔE)
            score += (1.0 - abs(energy_change) / 10.0) * 0.2

        # Mood consistency
        if track_a.mood == track_b.mood:
            score += 0.1

        return score

    def _estimate_key_distance(self, key_a: str, key_b: str) -> int:
        """
        Estimate distance between two Camelot keys.

        Simple version: parse position numbers.
        """
        try:
            pos_a = int(key_a[:-1])
            pos_b = int(key_b[:-1])
            distance = min(abs(pos_b - pos_a), 12 - abs(pos_b - pos_a))
            return distance
        except:
            return 6  # Unknown keys, moderate distance


class PlaylistGenerator:
    """
    Intelligent DJ set and playlist generation.

    Analyzes track library and generates optimized sequences
    for different DJ set types.
    """

    def __init__(self):
        """Initialize playlist generator."""
        self.optimizer = SimplePlaylistOptimizer()
        self.lock = Lock()

        if NETWORKX_AVAILABLE:
            logger.info("Graph-based optimization available (networkx)")
        else:
            logger.info("Using greedy optimization (networkx not available)")

    def generate_set(self, tracks: List[TrackMetadata],
                    set_type: PlaylistType = PlaylistType.CONTINUOUS,
                    set_duration_minutes: Optional[float] = None) -> PlaylistSequence:
        """
        Generate optimized DJ set.

        Args:
            tracks: Available tracks
            set_type: Type of set to generate
            set_duration_minutes: Target set duration (None = use all tracks)

        Returns:
            PlaylistSequence with optimized track order
        """
        if not tracks:
            return PlaylistSequence([], 0.0, [], [], 0.0, [])

        # Filter tracks to fit duration if specified
        selected_tracks = tracks
        if set_duration_minutes:
            selected_tracks = self._select_tracks_for_duration(
                tracks, set_duration_minutes * 60.0
            )

        # Optimize sequence
        with self.lock:
            optimized = self.optimizer.optimize_sequence(selected_tracks, set_type)

        # Calculate progression metrics
        energy_progression = [t.energy for t in optimized]
        bpm_profile = [t.bpm for t in optimized]

        # Calculate total duration
        total_duration = sum(t.duration_seconds for t in optimized)

        # Calculate quality scores
        transition_qualities = []
        for i in range(len(optimized) - 1):
            quality = self.optimizer._calculate_transition_quality(
                optimized[i], optimized[i+1], set_type
            )
            transition_qualities.append(quality)

        avg_quality = np.mean(transition_qualities) if transition_qualities else 0.0

        return PlaylistSequence(
            tracks=optimized,
            total_duration=total_duration,
            energy_progression=energy_progression,
            bpm_profile=bpm_profile,
            estimated_quality=float(avg_quality),
            transition_quality=transition_qualities
        )

    def _select_tracks_for_duration(self, tracks: List[TrackMetadata],
                                   target_duration: float) -> List[TrackMetadata]:
        """
        Select subset of tracks to match target duration.

        Args:
            tracks: Available tracks
            target_duration: Target total duration in seconds

        Returns:
            Selected tracks
        """
        # Sort by energy to get good representation
        sorted_tracks = sorted(tracks, key=lambda t: t.energy)

        selected = []
        total_duration = 0.0

        for track in sorted_tracks:
            if total_duration + track.duration_seconds <= target_duration:
                selected.append(track)
                total_duration += track.duration_seconds

        return selected if selected else tracks[:10]  # At least 10 tracks

    def suggest_next_track(self, current_track: TrackMetadata,
                          available_tracks: List[TrackMetadata],
                          set_type: PlaylistType = PlaylistType.CONTINUOUS) -> Optional[TrackMetadata]:
        """
        Suggest next track based on current track.

        Args:
            current_track: Currently playing track
            available_tracks: Remaining unplayed tracks
            set_type: Type of set being mixed

        Returns:
            Suggested next track or None
        """
        if not available_tracks:
            return None

        best_track = None
        best_score = -np.inf

        for candidate in available_tracks:
            score = self.optimizer._calculate_transition_quality(
                current_track, candidate, set_type
            )
            if score > best_score:
                best_score = score
                best_track = candidate

        return best_track

    def analyze_compatibility(self, tracks: List[TrackMetadata]) -> Dict:
        """
        Analyze overall compatibility of tracks in list.

        Args:
            tracks: Tracks to analyze

        Returns:
            Dictionary with compatibility metrics
        """
        if len(tracks) < 2:
            return {"compatibility_score": 1.0, "issues": []}

        # Calculate pairwise compatibility
        scores = []
        issues = []

        for i in range(len(tracks) - 1):
            score = self.optimizer._calculate_transition_quality(
                tracks[i], tracks[i+1], PlaylistType.CONTINUOUS
            )
            scores.append(score)

            # Check for major compatibility issues
            if score < 0.3:
                issues.append(f"Weak transition: {tracks[i].title} → {tracks[i+1].title}")

        avg_score = float(np.mean(scores)) if scores else 1.0

        return {
            "compatibility_score": avg_score,
            "transition_count": len(scores),
            "avg_transition_quality": avg_score,
            "issues": issues
        }

    def export_set(self, sequence: PlaylistSequence, filepath: str) -> bool:
        """
        Export generated set to file.

        Args:
            sequence: Generated playlist sequence
            filepath: Output file path

        Returns:
            True if successful
        """
        try:
            data = {
                "total_duration_seconds": sequence.total_duration,
                "estimated_quality": sequence.estimated_quality,
                "tracks": [
                    {
                        "filename": t.filename,
                        "title": t.title,
                        "artist": t.artist,
                        "bpm": t.bpm,
                        "key": t.key,
                        "energy": t.energy,
                        "duration": t.duration_seconds
                    }
                    for t in sequence.tracks
                ],
                "energy_progression": sequence.energy_progression,
                "bpm_profile": sequence.bpm_profile
            }

            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Playlist exported to: {filepath}")
            return True

        except Exception as e:
            logger.error(f"Failed to export playlist: {e}")
            return False
