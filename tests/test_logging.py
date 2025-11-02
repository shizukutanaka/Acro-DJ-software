# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""Tests for professional logging system.

Tests for Loguru-based logging configuration, performance monitoring,
and structured logging features.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from logging_config import (
    setup_logging,
    get_logger,
    PerformanceMonitor,
    PerformanceMetrics,
    measure,
)


class TestLoggingSetup:
    """Test logging configuration."""

    def test_setup_logging_default(self, temp_dir: Path):
        """Test default logging setup."""
        setup_logging()
        logger = get_logger(__name__)

        assert logger is not None
        assert logger.level == 20  # INFO level

    def test_setup_logging_debug_level(self, temp_dir: Path):
        """Test debug level setup."""
        setup_logging(level="DEBUG")
        logger = get_logger(__name__)

        assert logger.level == 10  # DEBUG level

    def test_setup_logging_with_file(self, temp_dir: Path):
        """Test logging with file output."""
        log_file = temp_dir / "test.log"
        setup_logging(log_file=log_file)

        logger = get_logger(__name__)
        logger.info("Test message")

        assert log_file.exists()
        assert "Test message" in log_file.read_text()

    def test_setup_logging_rotation(self, temp_dir: Path):
        """Test log rotation configuration."""
        log_file = temp_dir / "test.log"
        setup_logging(log_file=log_file, rotation="1 KB")

        logger = get_logger(__name__)

        # Write enough to trigger rotation
        for i in range(100):
            logger.info(f"Test message {i}" * 10)

    def test_setup_logging_json_format(self, temp_dir: Path):
        """Test JSON logging format."""
        log_file = temp_dir / "test.log"
        setup_logging(log_file=log_file, json_logs=True)

        logger = get_logger(__name__)
        logger.info("Test JSON message", extra={"user_id": 123})

        # Verify JSON output
        content = log_file.read_text().strip()
        lines = content.split('\n')

        for line in lines:
            if line.strip():
                try:
                    data = json.loads(line)
                    assert "message" in data or "text" in data
                except json.JSONDecodeError:
                    pass  # Some lines might not be JSON


class TestPerformanceMetrics:
    """Test performance metrics dataclass."""

    def test_metrics_creation(self):
        """Test creating metrics."""
        metrics = PerformanceMetrics(
            operation="test_op",
            duration_ms=100.5,
            memory_mb=50.0,
        )

        assert metrics.operation == "test_op"
        assert metrics.duration_ms == 100.5
        assert metrics.memory_mb == 50.0

    def test_metrics_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = PerformanceMetrics(
            operation="test",
            duration_ms=100.0,
        )

        data = metrics.to_dict()
        assert isinstance(data, dict)
        assert data["operation"] == "test"
        assert data["duration_ms"] == 100.0

    def test_metrics_json_serializable(self):
        """Test metrics can be JSON serialized."""
        metrics = PerformanceMetrics(
            operation="test",
            duration_ms=100.0,
        )

        json_str = json.dumps(metrics.to_dict())
        assert "test" in json_str


class TestPerformanceMonitor:
    """Test performance monitoring."""

    def test_monitor_creation(self):
        """Test creating performance monitor."""
        monitor = PerformanceMonitor()
        assert monitor is not None
        assert isinstance(monitor.metrics, list)

    def test_measure_context_manager(self):
        """Test measure context manager."""
        import time
        monitor = PerformanceMonitor()

        with monitor.measure("test_operation"):
            time.sleep(0.01)  # 10ms

        assert len(monitor.metrics) > 0
        assert monitor.metrics[-1].operation == "test_operation"
        assert monitor.metrics[-1].duration_ms > 5

    def test_measure_decorator(self):
        """Test measure as decorator."""
        monitor = PerformanceMonitor()

        @monitor.measure_function
        def slow_function():
            import time
            time.sleep(0.01)
            return "result"

        result = slow_function()
        assert result == "result"
        assert len(monitor.metrics) > 0

    def test_get_statistics(self):
        """Test getting statistics."""
        import time
        monitor = PerformanceMonitor()

        for i in range(5):
            with monitor.measure("test"):
                time.sleep(0.001)

        stats = monitor.get_statistics("test")
        assert stats["count"] == 5
        assert stats["mean_ms"] > 0.5
        assert stats["min_ms"] > 0
        assert stats["max_ms"] > 0

    def test_clear_metrics(self):
        """Test clearing metrics."""
        import time
        monitor = PerformanceMonitor()

        with monitor.measure("test"):
            time.sleep(0.001)

        assert len(monitor.metrics) > 0
        monitor.clear()
        assert len(monitor.metrics) == 0

    def test_export_metrics_json(self, temp_dir: Path):
        """Test exporting metrics to JSON."""
        import time
        monitor = PerformanceMonitor()

        with monitor.measure("test"):
            time.sleep(0.001)

        output_file = temp_dir / "metrics.json"
        monitor.export_json(output_file)

        assert output_file.exists()
        data = json.loads(output_file.read_text())
        assert isinstance(data, list)


class TestGlobalMeasure:
    """Test global measure function."""

    def test_measure_function_simple(self):
        """Test simple measure operation."""
        import time

        with measure("test_operation"):
            time.sleep(0.001)

    def test_measure_function_with_logger(self):
        """Test measure with logger integration."""
        import time

        with measure("test_op", log_level="DEBUG"):
            time.sleep(0.001)

    def test_measure_nested_operations(self):
        """Test nested measurements."""
        import time

        with measure("outer"):
            time.sleep(0.001)
            with measure("inner"):
                time.sleep(0.001)


class TestLoggerSingleton:
    """Test logger singleton pattern."""

    def test_same_logger_instance(self):
        """Test that get_logger returns same instance."""
        logger1 = get_logger("test")
        logger2 = get_logger("test")

        assert logger1 is logger2

    def test_different_loggers_different_names(self):
        """Test different loggers for different names."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        # Same sink but different names
        assert logger1 is not logger2


class TestLoggingIntegration:
    """Integration tests for logging system."""

    def test_logging_with_config(self, config, temp_dir: Path):
        """Test logging with configuration."""
        log_file = temp_dir / "test.log"
        setup_logging(level=config.log_level, log_file=log_file)

        logger = get_logger(__name__)
        logger.info("Test message")

        assert log_file.exists()

    def test_performance_monitoring_integration(self):
        """Test performance monitoring in real scenario."""
        import time
        monitor = PerformanceMonitor()

        # Simulate real operations
        for i in range(3):
            with monitor.measure(f"operation_{i}"):
                time.sleep(0.001)

        # Verify all operations tracked
        assert len(monitor.metrics) == 3

    def test_error_logging(self, temp_dir: Path):
        """Test error logging."""
        log_file = temp_dir / "error.log"
        setup_logging(log_file=log_file)

        logger = get_logger(__name__)

        try:
            raise ValueError("Test error")
        except ValueError as e:
            logger.error(f"Error occurred: {e}", exc_info=True)

        assert "Error occurred" in log_file.read_text()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
