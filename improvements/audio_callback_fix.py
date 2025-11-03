# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Audio Callback Thread Safety Improvements

This module demonstrates improved thread-safe audio callback implementation.
Uses snapshot pattern to minimize lock contention and prevent race conditions.
"""

import logging
import queue
import numpy as np
from typing import Dict

logger = logging.getLogger(__name__)


def improved_audio_callback(
    indata, outdata, frames: int, time_info, status,
    stream_lock, playback_decks: Dict, audio_queue: queue.Queue,
    crossfader_value, master_volume_percent
) -> None:
    """
    Improved thread-safe audio callback using snapshot pattern.

    Minimizes lock contention by:
    1. Taking snapshot of active decks under lock
    2. Processing snapshot outside the lock
    3. Cleaning up decks in separate atomic operation
    """
    if status:
        logger.warning(f"Audio callback status: {status}")

    try:
        frames = len(outdata)
        mix = np.zeros((frames, 2), dtype=np.float32)

        # Get control values (atomic reads)
        xf = crossfader_value.get()
        master_vol = master_volume_percent.get() / 100.0

        # CRITICAL SECTION: Only take snapshot, minimize lock time
        with stream_lock:
            active_decks = list(playback_decks.items())

        remove_decks = []
        active_count = 0

        # PROCESS OUTSIDE LOCK: All mixing happens here
        for i, (deck_id, deck) in enumerate(active_decks):
            try:
                if deck.is_playing:
                    chunk = deck.get_chunk(frames)
                    if chunk is not None and len(chunk) == frames:
                        level = (1.0 - xf) if i == 0 else xf
                        stereo_chunk = np.column_stack((chunk, chunk)) * level
                        mix += stereo_chunk
                        active_count += 1
                    else:
                        remove_decks.append(deck_id)
                else:
                    remove_decks.append(deck_id)
            except Exception as e:
                logger.error(f"Error processing deck {deck_id}: {e}")
                remove_decks.append(deck_id)

        # CLEANUP: Remove dead decks atomically
        if remove_decks:
            with stream_lock:
                for deck_id in remove_decks:
                    playback_decks.pop(deck_id, None)

        # Apply master volume with clipping
        mix *= master_vol
        np.clip(mix, -1.0, 1.0, out=mix)
        outdata[:] = mix

        # Signal that audio is active (non-blocking)
        if active_count > 0:
            try:
                audio_queue.put_nowait(True)
            except queue.Full:
                pass  # Queue full is OK, we just signal periodically

    except Exception as e:
        logger.critical(f"Fatal error in audio callback: {e}")
        outdata[:] = np.zeros_like(outdata)


class AtomicDeckRegistry:
    """Lock-free deck registry using copy-on-write semantics."""

    def __init__(self):
        """Initialize atomic deck registry."""
        self._decks = {}

    def get_snapshot(self) -> Dict:
        """Get atomic snapshot of current decks (lock-free)."""
        return dict(self._decks)

    def add_deck(self, deck_id: str, deck) -> None:
        """Add a deck (atomic operation)."""
        new_decks = self._decks.copy()
        new_decks[deck_id] = deck
        self._decks = new_decks

    def remove_deck(self, deck_id: str) -> bool:
        """Remove a deck (atomic operation)."""
        if deck_id in self._decks:
            new_decks = self._decks.copy()
            del new_decks[deck_id]
            self._decks = new_decks
            return True
        return False

    def remove_many(self, deck_ids: list) -> None:
        """Remove multiple decks atomically."""
        new_decks = self._decks.copy()
        for deck_id in deck_ids:
            new_decks.pop(deck_id, None)
        self._decks = new_decks


class AudioBufferPool:
    """Pre-allocated buffer pool to reduce GC pressure."""

    def __init__(self, frame_size: int = 1024, num_buffers: int = 4):
        """Initialize audio buffer pool."""
        self.frame_size = frame_size
        self._available = [
            np.zeros((frame_size, 2), dtype=np.float32)
            for _ in range(num_buffers)
        ]
        self._in_use = set()

    def acquire(self) -> np.ndarray:
        """Acquire a buffer from the pool."""
        if self._available:
            buf = self._available.pop()
            buf[:] = 0
            self._in_use.add(id(buf))
            return buf
        else:
            buf = np.zeros((self.frame_size, 2), dtype=np.float32)
            self._in_use.add(id(buf))
            return buf

    def release(self, buf: np.ndarray) -> None:
        """Release a buffer back to the pool."""
        buf_id = id(buf)
        if buf_id in self._in_use:
            self._in_use.remove(buf_id)
            if len(self._available) < 4:
                self._available.append(buf)


class ThreadSafetyMetrics:
    """Monitor audio callback performance and thread safety."""

    def __init__(self):
        """Initialize metrics."""
        self.callback_count = 0
        self.underrun_count = 0
        self.max_processing_time = 0
        self.avg_processing_time = 0

    def record_callback(self, processing_time: float) -> None:
        """Record callback execution."""
        self.callback_count += 1
        self.max_processing_time = max(self.max_processing_time, processing_time)
        self.avg_processing_time = (
            (self.avg_processing_time * (self.callback_count - 1) + processing_time)
            / self.callback_count
        )

    def record_underrun(self) -> None:
        """Record audio underrun."""
        self.underrun_count += 1

    def get_summary(self) -> str:
        """Get metrics summary."""
        return (
            f"Callbacks: {self.callback_count}, "
            f"Underruns: {self.underrun_count}, "
            f"Avg Time: {self.avg_processing_time*1000:.2f}ms, "
            f"Max Time: {self.max_processing_time*1000:.2f}ms"
        )
