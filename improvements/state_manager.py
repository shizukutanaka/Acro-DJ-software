# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Global State Manager

Encapsulates global state to eliminate scattered global variables.
Provides centralized, thread-safe state management.
"""

import logging
import threading
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class AudioState:
    """Audio stream state."""
    sample_rate: int = 44100
    buffer_size: int = 1024
    channels: int = 2
    audio_stream: Optional[Any] = None
    is_streaming: bool = False


@dataclass
class PlaybackState:
    """Playback decks state."""
    decks: Dict[str, Any] = field(default_factory=dict)
    crossfader_value: float = 0.5
    master_volume_percent: float = 100.0


@dataclass
class UIState:
    """UI state."""
    waveform_cache: Dict[str, Any] = field(default_factory=dict)
    selected_file: Optional[str] = None
    theme_colors: Dict[str, str] = field(default_factory=dict)


class GlobalStateManager:
    """
    Centralized global state manager.

    Replaces scattered global variables with organized state containers.
    Provides thread-safe access to application state.
    """

    def __init__(self):
        """Initialize state manager."""
        self._lock = threading.RLock()
        self.audio = AudioState()
        self.playback = PlaybackState()
        self.ui = UIState()
        self._observers = []

    def register_observer(self, callback) -> None:
        """Register state change observer."""
        with self._lock:
            self._observers.append(callback)

    def notify_observers(self, state_name: str, value: Any) -> None:
        """Notify all observers of state change."""
        with self._lock:
            for callback in self._observers:
                try:
                    callback(state_name, value)
                except Exception as e:
                    logger.error(f"Observer callback error: {e}")

    def get_audio_state(self) -> AudioState:
        """Get audio state (thread-safe copy)."""
        with self._lock:
            return AudioState(
                sample_rate=self.audio.sample_rate,
                buffer_size=self.audio.buffer_size,
                channels=self.audio.channels,
                audio_stream=self.audio.audio_stream,
                is_streaming=self.audio.is_streaming
            )

    def set_audio_stream(self, stream: Any) -> None:
        """Set audio stream."""
        with self._lock:
            self.audio.audio_stream = stream
            self.audio.is_streaming = True
        self.notify_observers("audio_stream", stream)

    def stop_audio_stream(self) -> None:
        """Stop audio stream."""
        with self._lock:
            if self.audio.audio_stream:
                self.audio.audio_stream = None
            self.audio.is_streaming = False
        self.notify_observers("audio_stream_stopped", None)

    def get_playback_state(self) -> PlaybackState:
        """Get playback state."""
        with self._lock:
            return PlaybackState(
                decks=dict(self.playback.decks),
                crossfader_value=self.playback.crossfader_value,
                master_volume_percent=self.playback.master_volume_percent
            )

    def add_deck(self, deck_id: str, deck: Any) -> None:
        """Add playback deck."""
        with self._lock:
            self.playback.decks[deck_id] = deck
        self.notify_observers("deck_added", deck_id)

    def remove_deck(self, deck_id: str) -> None:
        """Remove playback deck."""
        with self._lock:
            self.playback.decks.pop(deck_id, None)
        self.notify_observers("deck_removed", deck_id)

    def get_decks(self) -> Dict[str, Any]:
        """Get all decks (thread-safe snapshot)."""
        with self._lock:
            return dict(self.playback.decks)

    def set_crossfader(self, value: float) -> None:
        """Set crossfader position."""
        value = max(0.0, min(1.0, value))
        with self._lock:
            self.playback.crossfader_value = value
        self.notify_observers("crossfader_changed", value)

    def set_master_volume(self, percent: float) -> None:
        """Set master volume percentage."""
        percent = max(0.0, min(100.0, percent))
        with self._lock:
            self.playback.master_volume_percent = percent
        self.notify_observers("master_volume_changed", percent)

    def get_ui_state(self) -> UIState:
        """Get UI state."""
        with self._lock:
            return UIState(
                waveform_cache=dict(self.ui.waveform_cache),
                selected_file=self.ui.selected_file,
                theme_colors=dict(self.ui.theme_colors)
            )

    def set_selected_file(self, filepath: Optional[str]) -> None:
        """Set selected file."""
        with self._lock:
            self.ui.selected_file = filepath
        self.notify_observers("file_selected", filepath)

    def cache_waveform(self, filepath: str, waveform_data: Any) -> None:
        """Cache waveform data."""
        with self._lock:
            self.ui.waveform_cache[filepath] = waveform_data
        self.notify_observers("waveform_cached", filepath)

    def get_waveform(self, filepath: str) -> Optional[Any]:
        """Get cached waveform."""
        with self._lock:
            return self.ui.waveform_cache.get(filepath)

    def clear_waveform_cache(self) -> None:
        """Clear waveform cache."""
        with self._lock:
            self.ui.waveform_cache.clear()
        self.notify_observers("waveform_cache_cleared", None)

    def set_theme_colors(self, colors: Dict[str, str]) -> None:
        """Set theme colors."""
        with self._lock:
            self.ui.theme_colors = dict(colors)
        self.notify_observers("theme_changed", colors)


# Global instance
_state_manager: Optional[GlobalStateManager] = None


def get_state_manager() -> GlobalStateManager:
    """Get or create global state manager."""
    global _state_manager
    if _state_manager is None:
        _state_manager = GlobalStateManager()
    return _state_manager


def reset_state_manager() -> None:
    """Reset global state manager (for testing)."""
    global _state_manager
    _state_manager = None
