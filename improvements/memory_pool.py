# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Memory Pool Management

Pre-allocates memory buffers to reduce garbage collection pressure
during real-time audio processing.
"""

import logging
import numpy as np
from typing import Optional, List
from dataclasses import dataclass
from threading import Lock, Event
from collections import deque
import gc

logger = logging.getLogger(__name__)


@dataclass
class BufferInfo:
    """Information about a buffer pool."""

    buffer_size: int
    dtype: str
    pool_size: int
    acquired: int = 0
    released: int = 0
    total_memory_mb: float = 0.0


class AudioBufferPool:
    """
    Pool of pre-allocated audio buffers.

    Reduces GC pressure by reusing buffers instead of allocating new ones.
    """

    def __init__(self, buffer_size: int = 1024,
                 pool_size: int = 32,
                 dtype: str = 'float32',
                 channels: int = 2):
        """
        Initialize buffer pool.

        Args:
            buffer_size: Size of each buffer in samples
            pool_size: Number of buffers in pool
            dtype: NumPy data type
            channels: Number of audio channels per buffer
        """
        self.buffer_size = buffer_size
        self.pool_size = pool_size
        self.dtype = dtype
        self.channels = channels

        # Create buffers
        self.available_buffers: deque = deque(maxlen=pool_size)
        self.lock = Lock()
        self.stats_lock = Lock()

        # Statistics
        self.acquired_count = 0
        self.released_count = 0
        self.max_concurrent = 0

        # Pre-allocate buffers
        self._initialize_buffers()

        # Logging
        buffer_shape = (channels, buffer_size) if channels > 1 else (buffer_size,)
        size_mb = (
            np.prod(buffer_shape) *
            np.dtype(dtype).itemsize / (1024 * 1024)
        )
        total_mb = size_mb * pool_size

        logger.info(f"AudioBufferPool initialized: "
                   f"{pool_size} buffers of {buffer_shape}, "
                   f"{total_mb:.2f} MB total")

    def _initialize_buffers(self) -> None:
        """Pre-allocate all buffers."""
        for _ in range(self.pool_size):
            if self.channels > 1:
                buffer = np.zeros((self.channels, self.buffer_size),
                                 dtype=self.dtype)
            else:
                buffer = np.zeros(self.buffer_size, dtype=self.dtype)

            self.available_buffers.append(buffer)

    def acquire(self) -> np.ndarray:
        """
        Acquire a buffer from the pool.

        Returns:
            Zeroed buffer array ready for use
        """
        with self.lock:
            if len(self.available_buffers) > 0:
                buffer = self.available_buffers.popleft()
            else:
                # Allocate new buffer if pool exhausted
                logger.warning("Buffer pool exhausted, allocating new buffer")
                if self.channels > 1:
                    buffer = np.zeros((self.channels, self.buffer_size),
                                     dtype=self.dtype)
                else:
                    buffer = np.zeros(self.buffer_size, dtype=self.dtype)

            # Record stats
            with self.stats_lock:
                self.acquired_count += 1
                current_acquired = self.pool_size - len(self.available_buffers)
                self.max_concurrent = max(self.max_concurrent, current_acquired)

        return buffer

    def release(self, buffer: np.ndarray) -> None:
        """
        Release a buffer back to the pool.

        Args:
            buffer: Buffer to return
        """
        # Clear buffer (important for audio - avoid noise)
        buffer.fill(0)

        with self.lock:
            if len(self.available_buffers) < self.pool_size:
                self.available_buffers.append(buffer)

        # Record stats
        with self.stats_lock:
            self.released_count += 1

    def get_stats(self) -> BufferInfo:
        """Get pool statistics."""
        with self.stats_lock:
            size_mb = (
                np.prod(buffer.shape) *
                np.dtype(self.dtype).itemsize / (1024 * 1024)
            ) if self.channels > 1 else (
                self.buffer_size *
                np.dtype(self.dtype).itemsize / (1024 * 1024)
            )

            return BufferInfo(
                buffer_size=self.buffer_size,
                dtype=self.dtype,
                pool_size=self.pool_size,
                acquired=self.acquired_count,
                released=self.released_count,
                total_memory_mb=size_mb * self.pool_size
            )

    def __enter__(self):
        """Context manager entry."""
        return self.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if exc_val is not None:
            logger.error(f"Exception in buffer context: {exc_val}")


class VisualizationBufferPool:
    """
    Pool of buffers for visualization data.

    Used for waveform display, spectrum, etc.
    """

    def __init__(self, buffer_size: int = 512,
                 pool_size: int = 16):
        """
        Initialize visualization buffer pool.

        Args:
            buffer_size: Size of visualization buffer
            pool_size: Number of buffers
        """
        self.buffer_size = buffer_size
        self.pool_size = pool_size

        self.available_buffers: deque = deque(maxlen=pool_size)
        self.lock = Lock()

        # Pre-allocate
        for _ in range(pool_size):
            buffer = np.zeros(buffer_size, dtype='float32')
            self.available_buffers.append(buffer)

        logger.info(f"VisualizationBufferPool initialized: "
                   f"{pool_size} buffers of {buffer_size} samples")

    def acquire(self) -> np.ndarray:
        """Acquire a visualization buffer."""
        with self.lock:
            if len(self.available_buffers) > 0:
                return self.available_buffers.popleft()
            else:
                return np.zeros(self.buffer_size, dtype='float32')

    def release(self, buffer: np.ndarray) -> None:
        """Release a visualization buffer."""
        buffer.fill(0)

        with self.lock:
            if len(self.available_buffers) < self.pool_size:
                self.available_buffers.append(buffer)


class MetadataCache:
    """
    Cache for track metadata to avoid re-computing.

    Stores: BPM, key, waveform, onsets, etc.
    """

    def __init__(self, max_cache_size: int = 100):
        """
        Initialize metadata cache.

        Args:
            max_cache_size: Maximum number of tracks to cache
        """
        self.max_cache_size = max_cache_size
        self.cache: dict = {}
        self.lock = Lock()

    def get(self, key: str) -> Optional[dict]:
        """Get cached metadata."""
        with self.lock:
            return self.cache.get(key)

    def set(self, key: str, metadata: dict) -> None:
        """Cache metadata for a track."""
        with self.lock:
            # Evict oldest if cache full
            if len(self.cache) >= self.max_cache_size:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]

            self.cache[key] = metadata

    def clear(self) -> None:
        """Clear cache."""
        with self.lock:
            self.cache.clear()

    def get_size(self) -> int:
        """Get current cache size."""
        with self.lock:
            return len(self.cache)


class MemoryPoolManager:
    """
    Manages all memory pools for the application.

    Coordinates: audio buffers, visualization buffers, metadata cache.
    """

    def __init__(self, audio_buffer_size: int = 1024,
                 audio_pool_size: int = 32,
                 viz_buffer_size: int = 512,
                 viz_pool_size: int = 16,
                 cache_size: int = 100):
        """
        Initialize memory pool manager.

        Args:
            audio_buffer_size: Audio buffer size in samples
            audio_pool_size: Number of audio buffers
            viz_buffer_size: Visualization buffer size
            viz_pool_size: Number of visualization buffers
            cache_size: Metadata cache size
        """
        self.audio_pool = AudioBufferPool(
            buffer_size=audio_buffer_size,
            pool_size=audio_pool_size
        )

        self.viz_pool = VisualizationBufferPool(
            buffer_size=viz_buffer_size,
            pool_size=viz_pool_size
        )

        self.metadata_cache = MetadataCache(max_cache_size=cache_size)

        # GC control
        self.gc_interval = 100  # Collect garbage every N operations
        self.operations_count = 0
        self.lock = Lock()

        logger.info("MemoryPoolManager initialized")

    def acquire_audio_buffer(self) -> np.ndarray:
        """Acquire audio buffer."""
        return self.audio_pool.acquire()

    def release_audio_buffer(self, buffer: np.ndarray) -> None:
        """Release audio buffer."""
        self.audio_pool.release(buffer)

    def acquire_viz_buffer(self) -> np.ndarray:
        """Acquire visualization buffer."""
        return self.viz_pool.acquire()

    def release_viz_buffer(self, buffer: np.ndarray) -> None:
        """Release visualization buffer."""
        self.viz_pool.release(buffer)

    def cache_metadata(self, key: str, metadata: dict) -> None:
        """Cache track metadata."""
        self.metadata_cache.set(key, metadata)

    def get_cached_metadata(self, key: str) -> Optional[dict]:
        """Get cached metadata."""
        return self.metadata_cache.get(key)

    def trigger_gc_if_needed(self) -> bool:
        """
        Trigger garbage collection if needed.

        Call periodically to prevent GC pause in audio callback.

        Returns:
            True if GC was triggered
        """
        with self.lock:
            self.operations_count += 1

            if self.operations_count >= self.gc_interval:
                self.operations_count = 0

                # Schedule GC for next opportunity
                gc.collect(generation=0)  # Only collect young generation
                return True

        return False

    def get_statistics(self) -> dict:
        """Get statistics about all pools."""
        return {
            'audio_pool': self.audio_pool.get_stats(),
            'metadata_cache_size': self.metadata_cache.get_size(),
            'gc_operations': self.operations_count
        }

    def clear_all(self) -> None:
        """Clear all caches and pools."""
        self.metadata_cache.clear()
        logger.info("MemoryPoolManager cleared")


# Global instance
_manager: Optional[MemoryPoolManager] = None


def get_memory_pool_manager() -> MemoryPoolManager:
    """
    Get global memory pool manager instance.

    Returns:
        MemoryPoolManager singleton
    """
    global _manager

    if _manager is None:
        _manager = MemoryPoolManager()

    return _manager
