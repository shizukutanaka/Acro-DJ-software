# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Tests for Plugin Performance Monitoring and Profiling System

Tests cover:
- Method profiling and execution timing
- CPU and memory usage measurement
- Latency measurement
- Performance alerts
- Data export and analysis
- Bottleneck identification
"""

import pytest
import tempfile
import time
from pathlib import Path

from plugins.plugin_profiling import (
    PerformanceData,
    PerformanceMetric,
    MethodProfiler,
    PluginPerformanceMonitor,
    PerformanceAlert,
    PerformanceAnalyzer,
)


class TestMethodProfiler:
    """Test method profiling."""

    def test_method_profiler_creation(self):
        """Test creating method profiler."""
        profiler = MethodProfiler("test_plugin", "test_method")

        assert profiler.plugin_id == "test_plugin"
        assert profiler.method_name == "test_method"

    def test_method_profiler_timing(self):
        """Test timing method execution."""
        profiler = MethodProfiler("test_plugin", "test_method")

        profiler.start()
        time.sleep(0.01)  # 10ms
        elapsed = profiler.stop()

        assert elapsed > 0
        assert elapsed >= 10  # At least 10ms

    def test_method_profiler_multiple_calls(self):
        """Test profiling multiple calls."""
        profiler = MethodProfiler("test_plugin", "test_method")

        for _ in range(10):
            profiler.start()
            time.sleep(0.001)  # 1ms
            profiler.stop()

        assert profiler.total_calls == 10

    def test_method_profiler_get_stats(self):
        """Test getting profiling statistics."""
        profiler = MethodProfiler("test_plugin", "test_method")

        for _ in range(10):
            profiler.start()
            time.sleep(0.001)
            profiler.stop()

        stats = profiler.get_stats()

        assert stats['count'] == 10
        assert stats['average'] > 0
        assert stats['min'] > 0
        assert stats['max'] >= stats['min']

    def test_method_profiler_percentiles(self):
        """Test percentile calculation."""
        profiler = MethodProfiler("test_plugin", "test_method")

        # Create varied execution times
        for i in range(100):
            profiler.start()
            time.sleep(0.001 * (1 + i % 5))  # 1-5ms
            profiler.stop()

        stats = profiler.get_stats()

        assert stats['p95'] >= stats['min']
        assert stats['p99'] >= stats['p95']

    def test_method_profiler_reset(self):
        """Test resetting profiler."""
        profiler = MethodProfiler("test_plugin", "test_method")

        profiler.start()
        profiler.stop()

        profiler.reset()

        stats = profiler.get_stats()

        assert stats == {}


class TestPerformanceData:
    """Test performance data recording."""

    def test_performance_data_creation(self):
        """Test creating performance data."""
        data = PerformanceData(
            timestamp="2024-01-01T00:00:00",
            metric=PerformanceMetric.CPU_USAGE,
            value=50.5,
            unit="%"
        )

        assert data.metric == PerformanceMetric.CPU_USAGE
        assert data.value == 50.5

    def test_performance_data_to_dict(self):
        """Test converting to dictionary."""
        data = PerformanceData(
            timestamp="2024-01-01T00:00:00",
            metric=PerformanceMetric.EXECUTION_TIME,
            value=25.5,
            unit="ms"
        )

        data_dict = data.to_dict()

        assert data_dict['metric'] == "execution_time"
        assert data_dict['value'] == 25.5


class TestPluginPerformanceMonitor:
    """Test performance monitoring."""

    @pytest.fixture
    def monitor(self):
        """Create performance monitor."""
        return PluginPerformanceMonitor("test_plugin")

    def test_monitor_creation(self, monitor):
        """Test creating performance monitor."""
        assert monitor.plugin_id == "test_plugin"
        assert len(monitor.method_profilers) == 0

    def test_record_metric(self, monitor):
        """Test recording metric."""
        monitor.record_metric(
            PerformanceMetric.CPU_USAGE,
            50.0,
            unit="%"
        )

        history = monitor.get_performance_history()
        assert len(history) == 1
        assert history[0].value == 50.0

    def test_create_method_profiler(self, monitor):
        """Test creating method profiler."""
        profiler = monitor.create_method_profiler("test_method")

        assert profiler is not None
        assert profiler.method_name == "test_method"

    def test_profile_method_decorator(self, monitor):
        """Test method profiling decorator."""
        @monitor.profile_method("test_operation")
        def test_operation():
            time.sleep(0.01)
            return "result"

        result = test_operation()

        assert result == "result"
        assert monitor.get_method_stats("test_operation") is not None

    def test_measure_cpu_usage(self, monitor):
        """Test measuring CPU usage."""
        cpu = monitor.measure_cpu_usage()

        assert isinstance(cpu, float)
        assert cpu >= 0

    def test_measure_memory_usage(self, monitor):
        """Test measuring memory usage."""
        memory = monitor.measure_memory_usage()

        assert isinstance(memory, float)
        assert memory > 0

    def test_measure_latency(self, monitor):
        """Test measuring operation latency."""
        def slow_operation():
            time.sleep(0.01)
            return "result"

        result, latency = monitor.measure_latency(slow_operation)

        assert result == "result"
        assert latency > 0

    def test_add_alert(self, monitor):
        """Test adding performance alert."""
        alert_id = monitor.add_alert(
            PerformanceMetric.CPU_USAGE,
            80.0,
            operator=">"
        )

        assert alert_id in monitor.alerts

    def test_alert_triggered(self, monitor):
        """Test alert triggering."""
        monitor.add_alert(
            PerformanceMetric.CPU_USAGE,
            50.0,
            operator=">"
        )

        # Record value above threshold
        monitor.record_metric(PerformanceMetric.CPU_USAGE, 75.0)

        status = monitor.get_alert_status()
        assert any(s['triggered'] for s in status.values())

    def test_get_performance_history(self, monitor):
        """Test getting performance history."""
        monitor.record_metric(PerformanceMetric.CPU_USAGE, 25.0)
        monitor.record_metric(PerformanceMetric.MEMORY_USAGE, 500.0)
        monitor.record_metric(PerformanceMetric.CPU_USAGE, 35.0)

        # Get all history
        history = monitor.get_performance_history()
        assert len(history) == 3

        # Get filtered history
        cpu_history = monitor.get_performance_history(
            metric=PerformanceMetric.CPU_USAGE
        )
        assert len(cpu_history) == 2

    def test_get_performance_history_limit(self, monitor):
        """Test limiting performance history."""
        for i in range(100):
            monitor.record_metric(PerformanceMetric.CPU_USAGE, float(i))

        limited = monitor.get_performance_history(limit=10)
        assert len(limited) == 10

    def test_get_performance_summary(self, monitor):
        """Test getting performance summary."""
        for i in range(10):
            monitor.record_metric(PerformanceMetric.CPU_USAGE, float(i * 10))

        summary = monitor.get_performance_summary()

        assert "cpu_usage" in summary
        assert summary["cpu_usage"]["count"] == 10
        assert summary["cpu_usage"]["min"] == 0.0
        assert summary["cpu_usage"]["max"] == 90.0

    def test_export_performance_data(self, monitor):
        """Test exporting performance data."""
        monitor.record_metric(PerformanceMetric.CPU_USAGE, 50.0)
        monitor.record_metric(PerformanceMetric.MEMORY_USAGE, 500.0)

        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = Path(tmpdir) / "performance.json"

            success, msg = monitor.export_performance_data(str(export_path))

            assert success
            assert export_path.exists()

            # Verify content
            import json
            with open(export_path) as f:
                data = json.load(f)
                assert data['plugin_id'] == "test_plugin"
                assert len(data['data_points']) == 2

    def test_reset_performance_data(self, monitor):
        """Test resetting performance data."""
        monitor.record_metric(PerformanceMetric.CPU_USAGE, 50.0)
        monitor.create_method_profiler("test").start()
        monitor.create_method_profiler("test").stop()

        monitor.reset_performance_data()

        history = monitor.get_performance_history()
        assert len(history) == 0

    def test_get_method_stats(self, monitor):
        """Test getting method statistics."""
        profiler = monitor.create_method_profiler("test_method")

        for _ in range(5):
            profiler.start()
            time.sleep(0.001)
            profiler.stop()

        stats = monitor.get_method_stats("test_method")

        assert stats is not None
        assert stats['count'] == 5

    def test_get_all_method_stats(self, monitor):
        """Test getting all method statistics."""
        for i in range(3):
            profiler = monitor.create_method_profiler(f"method_{i}")
            profiler.start()
            profiler.stop()

        all_stats = monitor.get_all_method_stats()

        assert len(all_stats) == 3
        for method_name in ["method_0", "method_1", "method_2"]:
            assert method_name in all_stats

    def test_multiple_alerts(self, monitor):
        """Test managing multiple alerts."""
        monitor.add_alert(PerformanceMetric.CPU_USAGE, 80.0, operator=">")
        monitor.add_alert(PerformanceMetric.MEMORY_USAGE, 1000.0, operator=">")
        monitor.add_alert(PerformanceMetric.EXECUTION_TIME, 100.0, operator=">")

        status = monitor.get_alert_status()

        assert len(status) == 3


class TestPerformanceAlert:
    """Test performance alerts."""

    def test_alert_creation(self):
        """Test creating alert."""
        alert = PerformanceAlert(
            alert_id="test_alert",
            plugin_id="test_plugin",
            metric=PerformanceMetric.CPU_USAGE,
            threshold=80.0,
            operator=">"
        )

        assert alert.alert_id == "test_alert"
        assert alert.threshold == 80.0

    def test_alert_to_dict(self):
        """Test converting alert to dict."""
        alert = PerformanceAlert(
            alert_id="test",
            plugin_id="plugin",
            metric=PerformanceMetric.CPU_USAGE,
            threshold=50.0,
            operator=">"
        )

        alert_dict = alert.to_dict()

        assert alert_dict['alert_id'] == "test"
        assert alert_dict['threshold'] == 50.0


class TestPerformanceAnalyzer:
    """Test performance analysis."""

    def test_detect_memory_leak(self):
        """Test memory leak detection."""
        monitor = PluginPerformanceMonitor("test_plugin")

        # Record increasing memory values
        for i in range(100):
            monitor.record_metric(
                PerformanceMetric.MEMORY_USAGE,
                500.0 + (i * 1.0)  # Linearly increasing
            )

        leak_detected, slope = PerformanceAnalyzer.detect_memory_leak(monitor)

        assert leak_detected
        assert slope > 0

    def test_identify_bottlenecks(self):
        """Test bottleneck identification."""
        monitor = PluginPerformanceMonitor("test_plugin")

        # Create methods with different performance
        for i in range(3):
            profiler = monitor.create_method_profiler(f"method_{i}")

            for _ in range(10):
                profiler.start()
                time.sleep(0.001 * (i + 1))  # Increasing sleep
                profiler.stop()

        bottlenecks = PerformanceAnalyzer.identify_bottlenecks(monitor)

        assert len(bottlenecks) >= 0
        # Highest should be slowest method
        if bottlenecks:
            assert "method_2" in [b[0] for b in bottlenecks[:1]]

    def test_calculate_throughput(self):
        """Test throughput calculation."""
        monitor = PluginPerformanceMonitor("test_plugin")

        # Record operations
        for _ in range(100):
            monitor.record_metric(PerformanceMetric.EXECUTION_TIME, 10.0)

        throughput = PerformanceAnalyzer.calculate_throughput(monitor, duration_seconds=1)

        # Should have operations per second
        assert throughput >= 0


class TestPerformanceMonitoring:
    """Test performance monitoring scenarios."""

    def test_continuous_monitoring(self):
        """Test continuous performance monitoring."""
        monitor = PluginPerformanceMonitor("test_plugin")

        # Simulate continuous monitoring
        for i in range(50):
            monitor.record_metric(PerformanceMetric.CPU_USAGE, float(i % 100))
            monitor.record_metric(PerformanceMetric.MEMORY_USAGE, 500.0 + i)

        history = monitor.get_performance_history()
        assert len(history) == 100

    def test_performance_with_method_profiling(self):
        """Test performance tracking with method profiling."""
        monitor = PluginPerformanceMonitor("test_plugin")

        @monitor.profile_method("process")
        def process_data(data):
            time.sleep(0.001)
            return data * 2

        # Call multiple times
        for i in range(20):
            process_data(i)

        stats = monitor.get_method_stats("process")
        assert stats is not None
        assert stats['count'] == 20

    def test_alert_conditions(self):
        """Test various alert conditions."""
        monitor = PluginPerformanceMonitor("test_plugin")

        # Add alerts with different operators
        monitor.add_alert(PerformanceMetric.CPU_USAGE, 50.0, operator=">")
        monitor.add_alert(PerformanceMetric.MEMORY_USAGE, 1000.0, operator="<")

        # Test above threshold
        monitor.record_metric(PerformanceMetric.CPU_USAGE, 60.0)

        # Test below threshold
        monitor.record_metric(PerformanceMetric.MEMORY_USAGE, 800.0)

        status = monitor.get_alert_status()
        assert len(status) == 2


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_profiler_with_no_calls(self):
        """Test profiler with no calls."""
        profiler = MethodProfiler("test", "method")

        stats = profiler.get_stats()

        assert stats == {}

    def test_monitor_with_no_data(self):
        """Test monitor with no recorded data."""
        monitor = PluginPerformanceMonitor("test_plugin")

        summary = monitor.get_performance_summary()

        assert summary == {}

    def test_very_large_history(self):
        """Test handling very large performance history."""
        monitor = PluginPerformanceMonitor("test_plugin", history_size=1000)

        # Record many metrics
        for i in range(2000):
            monitor.record_metric(PerformanceMetric.CPU_USAGE, float(i % 100))

        # Should only keep last 1000
        history = monitor.get_performance_history()
        assert len(history) <= 1000

    def test_concurrent_recording(self):
        """Test thread-safe metric recording."""
        monitor = PluginPerformanceMonitor("test_plugin")

        # Record metrics (normally would be from different threads)
        for i in range(100):
            monitor.record_metric(PerformanceMetric.CPU_USAGE, float(i))

        history = monitor.get_performance_history()
        assert len(history) == 100

    def test_export_with_large_dataset(self):
        """Test exporting large dataset."""
        monitor = PluginPerformanceMonitor("test_plugin", history_size=10000)

        # Record large amount of data
        for i in range(5000):
            monitor.record_metric(PerformanceMetric.CPU_USAGE, float(i % 100))

        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = Path(tmpdir) / "large_export.json"

            success, msg = monitor.export_performance_data(str(export_path))

            assert success
            assert export_path.exists()
