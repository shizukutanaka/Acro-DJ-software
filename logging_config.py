# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""Logging configuration for Acro DJ Mixer.

This module provides comprehensive logging setup with:
- Loguru integration for flexible logging
- Color-coded console output
- Structured JSON logging support
- Performance tracking
- File rotation and retention

Example:
    Basic logging setup::

        from logging_config import setup_logging
        from loguru import logger

        setup_logging(level="INFO", log_file="logs/acro.log")
        logger.info("Application started")

    Performance monitoring::

        from logging_config import PerformanceMonitor

        monitor = PerformanceMonitor()
        with monitor.measure("audio_callback"):
            process_audio()
        monitor.log_summary()
"""

from __future__ import annotations

import sys
import time
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean, stdev
from typing import Any, Deque, Optional

from loguru import logger


def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    rotation: str = "10 MB",
    retention: str = "1 week",
    json_logs: bool = False,
    colorize: bool = True,
) -> None:
    """Configure application logging.

    Sets up Loguru for console and file logging with optional JSON
    structured logging support.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (None for console only)
        rotation: When to rotate log files ("10 MB", "1 day", etc.)
        retention: How long to keep old log files ("1 week", "1 month", etc.)
        json_logs: Enable structured JSON logging
        colorize: Enable colored console output

    Example:
        >>> setup_logging(
        ...     level="INFO",
        ...     log_file=Path("logs/acro.log"),
        ...     rotation="10 MB"
        ... )
        >>> from loguru import logger
        >>> logger.info("Logging configured")
    """
    # Remove default handler
    logger.remove()

    # Console handler with colors
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    logger.add(
        sys.stderr,
        level=level,
        format=console_format,
        colorize=colorize,
        backtrace=True,
        diagnose=True,
    )

    # File handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)

        if json_logs:
            # Structured JSON logs for log aggregation systems
            logger.add(
                log_file,
                level=level,
                format="{message}",
                rotation=rotation,
                retention=retention,
                compression="zip",
                serialize=True,  # JSON format
                backtrace=True,
                diagnose=True,
            )
        else:
            # Human-readable logs
            file_format = (
                "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
                "{name}:{function}:{line} - {message}"
            )

            logger.add(
                log_file,
                level=level,
                format=file_format,
                rotation=rotation,
                retention=retention,
                compression="zip",
                backtrace=True,
                diagnose=True,
            )

    logger.info(
        "Logging configured",
        level=level,
        file=log_file,
        json_logs=json_logs,
    )


@dataclass
class PerformanceMetrics:
    """Track performance metrics for operations.

    Stores timing measurements and computes statistics:
    - Count: Number of measurements
    - Total time: Sum of all measurements
    - Min/Max: Minimum and maximum times
    - Average: Mean duration
    - Recent average: Mean of recent measurements
    - Stdev: Standard deviation of recent measurements

    Attributes:
        operation: Name of operation being measured
        count: Number of measurements
        total_time: Total time in seconds
        min_time: Minimum time in seconds
        max_time: Maximum time in seconds
        recent_times: Deque of recent measurements
    """

    operation: str
    count: int = 0
    total_time: float = 0.0
    min_time: float = float("inf")
    max_time: float = 0.0
    recent_times: Deque[float] = field(default_factory=lambda: deque(maxlen=100))

    def record(self, duration: float) -> None:
        """Record a new measurement.

        Args:
            duration: Operation duration in seconds
        """
        self.count += 1
        self.total_time += duration
        self.min_time = min(self.min_time, duration)
        self.max_time = max(self.max_time, duration)
        self.recent_times.append(duration)

    @property
    def avg_time(self) -> float:
        """Average time in seconds."""
        return self.total_time / self.count if self.count > 0 else 0.0

    @property
    def recent_avg(self) -> float:
        """Average of recent measurements in seconds."""
        return mean(self.recent_times) if self.recent_times else 0.0

    @property
    def recent_stdev(self) -> float:
        """Standard deviation of recent measurements."""
        return stdev(self.recent_times) if len(self.recent_times) > 1 else 0.0

    def __str__(self) -> str:
        """Format metrics as string."""
        return (
            f"{self.operation}: "
            f"count={self.count}, "
            f"avg={self.avg_time*1000:.2f}ms, "
            f"min={self.min_time*1000:.2f}ms, "
            f"max={self.max_time*1000:.2f}ms, "
            f"recent_avg={self.recent_avg*1000:.2f}ms, "
            f"stdev={self.recent_stdev*1000:.2f}ms"
        )


class PerformanceMonitor:
    """Monitor application performance.

    Tracks timing metrics for operations and provides logging
    and statistics.

    Example:
        >>> monitor = PerformanceMonitor()
        >>> with monitor.measure("audio_processing"):
        ...     process_audio_buffer()
        >>> monitor.log_summary()
    """

    def __init__(self, slow_threshold: float = 0.1) -> None:
        """Initialize performance monitor.

        Args:
            slow_threshold: Duration threshold for logging slow operations
                           (default 0.1 seconds / 100ms)
        """
        self.metrics: dict[str, PerformanceMetrics] = {}
        self.slow_threshold = slow_threshold

    @contextmanager
    def measure(self, operation: str) -> Any:
        """Measure operation performance.

        Context manager that automatically measures execution time
        and logs warnings if operation exceeds slow_threshold.

        Args:
            operation: Name of operation being measured

        Yields:
            None (use as context manager)

        Example:
            >>> monitor = PerformanceMonitor()
            >>> with monitor.measure("bpm_detection"):
            ...     bpm = detect_bpm(audio_data)
        """
        start = time.perf_counter()

        try:
            yield
        finally:
            duration = time.perf_counter() - start

            # Create or update metrics
            if operation not in self.metrics:
                self.metrics[operation] = PerformanceMetrics(operation)

            self.metrics[operation].record(duration)

            # Log warning if slow
            if duration > self.slow_threshold:
                logger.warning(
                    f"Slow operation: {operation}",
                    duration_ms=duration * 1000,
                    threshold_ms=self.slow_threshold * 1000,
                )

    def get_metrics(self, operation: str) -> Optional[PerformanceMetrics]:
        """Get metrics for a specific operation.

        Args:
            operation: Operation name

        Returns:
            PerformanceMetrics if operation exists, None otherwise
        """
        return self.metrics.get(operation)

    def log_summary(self) -> None:
        """Log performance summary for all operations.

        Outputs metrics to logger at INFO level.

        Example:
            >>> monitor.log_summary()
            [INFO] Performance metrics summary:
            [INFO] audio_callback: count=1000, avg=2.34ms, min=1.23ms, max=5.67ms, ...
        """
        if not self.metrics:
            logger.info("No performance metrics collected")
            return

        logger.info("Performance metrics summary:")
        for op, metrics in sorted(self.metrics.items()):
            logger.info(
                f"  {metrics.operation}",
                count=metrics.count,
                avg_ms=metrics.avg_time * 1000,
                min_ms=metrics.min_time * 1000,
                max_ms=metrics.max_time * 1000,
                recent_avg_ms=metrics.recent_avg * 1000,
                recent_stdev_ms=metrics.recent_stdev * 1000,
            )

    def reset(self) -> None:
        """Reset all metrics.

        Example:
            >>> monitor.reset()
        """
        self.metrics.clear()


# Global performance monitor instance
_perf_monitor: Optional[PerformanceMonitor] = None


def get_perf_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance.

    Creates singleton instance on first call.

    Returns:
        Global PerformanceMonitor instance

    Example:
        >>> monitor = get_perf_monitor()
        >>> with monitor.measure("operation"):
        ...     do_work()
    """
    global _perf_monitor

    if _perf_monitor is None:
        _perf_monitor = PerformanceMonitor()

    return _perf_monitor


def contextualize(**kwargs: Any) -> Any:
    """Add context to logging (keyword arguments passed to logger).

    Useful for adding request IDs, user IDs, session info, etc.

    Args:
        **kwargs: Context key-value pairs

    Returns:
        Context manager

    Example:
        >>> from loguru import logger
        >>> with contextualize(deck="A", track="song.wav"):
        ...     logger.info("Loading track")
    """
    return logger.contextualize(**kwargs)


# Configure structured logging helpers
def log_exception(msg: str, exc: Exception) -> None:
    """Log exception with full traceback.

    Args:
        msg: Log message
        exc: Exception instance

    Example:
        >>> try:
        ...     risky_operation()
        ... except Exception as e:
        ...     log_exception("Operation failed", e)
    """
    logger.exception(msg, exc_info=exc)


def log_performance(operation: str, duration_ms: float) -> None:
    """Log performance metric.

    Args:
        operation: Operation name
        duration_ms: Duration in milliseconds

    Example:
        >>> log_performance("audio_processing", 2.5)
    """
    logger.info(f"Performance: {operation}", duration_ms=duration_ms)
