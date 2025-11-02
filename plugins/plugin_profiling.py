# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Plugin Performance Monitoring and Profiling System for Acro DJ Mixer

Provides:
- Real-time performance monitoring
- CPU usage profiling
- Memory usage tracking
- Latency measurement
- Performance bottleneck identification
- Historical performance data storage
- Performance alerts and reporting
"""

import time
import psutil
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Callable, Any
from dataclasses import dataclass, asdict, field
from enum import Enum
from datetime import datetime
import json
from collections import deque
import threading

logger = logging.getLogger(__name__)


class PerformanceMetric(Enum):
    """Performance metrics to track."""
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    EXECUTION_TIME = "execution_time"
    LATENCY = "latency"
    THROUGHPUT = "throughput"


@dataclass
class PerformanceData:
    """Single performance measurement."""
    timestamp: str
    metric: PerformanceMetric
    value: float
    unit: str = ""
    plugin_id: str = ""
    method_name: str = ""
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'timestamp': self.timestamp,
            'metric': self.metric.value,
            'value': self.value,
            'unit': self.unit,
            'plugin_id': self.plugin_id,
            'method_name': self.method_name,
            'context': self.context,
        }


@dataclass
class PerformanceStats:
    """Statistics for a performance metric."""
    metric: PerformanceMetric
    count: int = 0
    min_value: float = float('inf')
    max_value: float = float('-inf')
    average: float = 0.0
    total: float = 0.0
    std_dev: float = 0.0
    p95: float = 0.0
    p99: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PerformanceAlert:
    """Performance threshold alert."""
    alert_id: str
    plugin_id: str
    metric: PerformanceMetric
    threshold: float
    operator: str  # '>', '<', '==', '!=', '>=', '<='
    triggered: bool = False
    trigger_count: int = 0
    last_triggered: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class MethodProfiler:
    """Profiles execution of a specific method."""

    def __init__(
        self,
        plugin_id: str,
        method_name: str,
        max_samples: int = 1000
    ):
        """Initialize method profiler.

        Args:
            plugin_id: Plugin identifier
            method_name: Method name to profile
            max_samples: Maximum samples to keep
        """
        self.plugin_id = plugin_id
        self.method_name = method_name
        self.max_samples = max_samples

        # Execution time samples
        self.execution_times: deque = deque(maxlen=max_samples)

        # Call statistics
        self.total_calls = 0
        self.total_execution_time = 0.0
        self.start_time = None

    def start(self) -> None:
        """Start timing method execution."""
        self.start_time = time.perf_counter()

    def stop(self) -> float:
        """Stop timing and record execution time.

        Returns:
            Execution time in milliseconds
        """
        if self.start_time is None:
            return 0.0

        elapsed = (time.perf_counter() - self.start_time) * 1000  # Convert to ms

        self.execution_times.append(elapsed)
        self.total_calls += 1
        self.total_execution_time += elapsed

        return elapsed

    def get_stats(self) -> Dict[str, float]:
        """Get execution statistics.

        Returns:
            Dictionary with statistical measures
        """
        if not self.execution_times:
            return {}

        times = list(self.execution_times)
        times_sorted = sorted(times)

        min_time = min(times)
        max_time = max(times)
        avg_time = sum(times) / len(times)

        # Calculate percentiles
        p95_idx = int(len(times_sorted) * 0.95)
        p99_idx = int(len(times_sorted) * 0.99)

        p95 = times_sorted[p95_idx] if p95_idx < len(times_sorted) else times_sorted[-1]
        p99 = times_sorted[p99_idx] if p99_idx < len(times_sorted) else times_sorted[-1]

        # Calculate standard deviation
        variance = sum((t - avg_time) ** 2 for t in times) / len(times)
        std_dev = variance ** 0.5

        return {
            'min': min_time,
            'max': max_time,
            'average': avg_time,
            'std_dev': std_dev,
            'p95': p95,
            'p99': p99,
            'count': len(times),
            'total_calls': self.total_calls,
            'total_time': self.total_execution_time,
        }

    def reset(self) -> None:
        """Reset profiler data."""
        self.execution_times.clear()
        self.total_calls = 0
        self.total_execution_time = 0.0


class PluginPerformanceMonitor:
    """Monitors plugin performance metrics."""

    def __init__(
        self,
        plugin_id: str,
        history_size: int = 10000,
        profile_methods: bool = True
    ):
        """Initialize performance monitor.

        Args:
            plugin_id: Plugin identifier
            history_size: Size of rolling history buffer
            profile_methods: Enable method-level profiling
        """
        self.plugin_id = plugin_id
        self.history_size = history_size
        self.profile_methods = profile_methods

        # Performance history
        self.performance_history: deque = deque(maxlen=history_size)

        # Method profilers
        self.method_profilers: Dict[str, MethodProfiler] = {}

        # Performance alerts
        self.alerts: Dict[str, PerformanceAlert] = {}

        # Thread safety
        self.lock = threading.Lock()

        # Process info
        try:
            self.process = psutil.Process()
        except Exception:
            self.process = None

    def record_metric(
        self,
        metric: PerformanceMetric,
        value: float,
        unit: str = "",
        method_name: str = "",
        context: Dict[str, Any] = None
    ) -> None:
        """Record a performance metric.

        Args:
            metric: Performance metric type
            value: Metric value
            unit: Unit of measurement
            method_name: Method name (if applicable)
            context: Additional context information
        """
        with self.lock:
            data = PerformanceData(
                timestamp=datetime.now().isoformat(),
                metric=metric,
                value=value,
                unit=unit,
                plugin_id=self.plugin_id,
                method_name=method_name,
                context=context or {}
            )

            self.performance_history.append(data)

            # Check alerts
            self._check_alerts(metric, value)

    def create_method_profiler(self, method_name: str) -> MethodProfiler:
        """Create a profiler for a specific method.

        Args:
            method_name: Method name to profile

        Returns:
            MethodProfiler instance
        """
        if method_name not in self.method_profilers:
            self.method_profilers[method_name] = MethodProfiler(
                self.plugin_id,
                method_name
            )

        return self.method_profilers[method_name]

    def profile_method(self, method_name: str) -> Callable:
        """Decorator to profile method execution.

        Args:
            method_name: Method name to profile

        Returns:
            Decorator function
        """
        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs) -> Any:
                profiler = self.create_method_profiler(method_name)

                profiler.start()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    elapsed = profiler.stop()
                    self.record_metric(
                        PerformanceMetric.EXECUTION_TIME,
                        elapsed,
                        unit="ms",
                        method_name=method_name
                    )

            return wrapper

        return decorator

    def get_method_stats(self, method_name: str) -> Optional[Dict[str, float]]:
        """Get profiling statistics for a method.

        Args:
            method_name: Method name

        Returns:
            Dictionary of statistics or None
        """
        if method_name not in self.method_profilers:
            return None

        return self.method_profilers[method_name].get_stats()

    def get_all_method_stats(self) -> Dict[str, Dict[str, float]]:
        """Get profiling statistics for all profiled methods.

        Returns:
            Dictionary of method stats
        """
        stats = {}

        for method_name, profiler in self.method_profilers.items():
            method_stats = profiler.get_stats()
            if method_stats:
                stats[method_name] = method_stats

        return stats

    def measure_cpu_usage(self) -> float:
        """Measure current CPU usage percentage.

        Returns:
            CPU usage percentage
        """
        if not self.process:
            return 0.0

        try:
            cpu_percent = self.process.cpu_percent(interval=0.1)
            self.record_metric(
                PerformanceMetric.CPU_USAGE,
                cpu_percent,
                unit="%"
            )
            return cpu_percent
        except Exception as e:
            logger.warning(f"Failed to measure CPU usage: {e}")
            return 0.0

    def measure_memory_usage(self) -> float:
        """Measure current memory usage in MB.

        Returns:
            Memory usage in MB
        """
        if not self.process:
            return 0.0

        try:
            mem_info = self.process.memory_info()
            memory_mb = mem_info.rss / (1024 * 1024)
            self.record_metric(
                PerformanceMetric.MEMORY_USAGE,
                memory_mb,
                unit="MB"
            )
            return memory_mb
        except Exception as e:
            logger.warning(f"Failed to measure memory usage: {e}")
            return 0.0

    def measure_latency(
        self,
        operation: Callable,
        *args,
        **kwargs
    ) -> Tuple[Any, float]:
        """Measure operation latency.

        Args:
            operation: Callable to measure
            *args: Operation arguments
            **kwargs: Operation keyword arguments

        Returns:
            Tuple of (result, latency_ms)
        """
        start = time.perf_counter()

        try:
            result = operation(*args, **kwargs)
            return result, 0.0
        finally:
            latency = (time.perf_counter() - start) * 1000  # Convert to ms
            self.record_metric(
                PerformanceMetric.LATENCY,
                latency,
                unit="ms"
            )

    def add_alert(
        self,
        metric: PerformanceMetric,
        threshold: float,
        operator: str = ">",
        alert_id: Optional[str] = None
    ) -> str:
        """Add a performance alert.

        Args:
            metric: Metric to monitor
            threshold: Threshold value
            operator: Comparison operator ('>', '<', '==', etc.)
            alert_id: Optional custom alert ID

        Returns:
            Alert ID
        """
        if not alert_id:
            alert_id = f"{self.plugin_id}_{metric.value}_{threshold}"

        alert = PerformanceAlert(
            alert_id=alert_id,
            plugin_id=self.plugin_id,
            metric=metric,
            threshold=threshold,
            operator=operator
        )

        self.alerts[alert_id] = alert

        logger.info(f"Added alert {alert_id}: {metric.value} {operator} {threshold}")

        return alert_id

    def _check_alerts(self, metric: PerformanceMetric, value: float) -> None:
        """Check if any alerts should be triggered.

        Args:
            metric: Performance metric
            value: Metric value
        """
        for alert_id, alert in self.alerts.items():
            if alert.metric != metric:
                continue

            triggered = self._evaluate_condition(value, alert.operator, alert.threshold)

            if triggered and not alert.triggered:
                alert.triggered = True
                alert.trigger_count += 1
                alert.last_triggered = datetime.now().isoformat()

                logger.warning(
                    f"Alert triggered: {alert_id} "
                    f"({value} {alert.operator} {alert.threshold})"
                )
            elif not triggered:
                alert.triggered = False

    @staticmethod
    def _evaluate_condition(value: float, operator: str, threshold: float) -> bool:
        """Evaluate condition.

        Args:
            value: Actual value
            operator: Operator string
            threshold: Threshold value

        Returns:
            True if condition is met
        """
        if operator == '>':
            return value > threshold
        elif operator == '<':
            return value < threshold
        elif operator == '>=':
            return value >= threshold
        elif operator == '<=':
            return value <= threshold
        elif operator == '==':
            return value == threshold
        elif operator == '!=':
            return value != threshold
        return False

    def get_performance_history(
        self,
        metric: Optional[PerformanceMetric] = None,
        limit: Optional[int] = None
    ) -> List[PerformanceData]:
        """Get performance history.

        Args:
            metric: Filter by metric type (optional)
            limit: Limit results (optional)

        Returns:
            List of performance data
        """
        with self.lock:
            history = list(self.performance_history)

        if metric:
            history = [d for d in history if d.metric == metric]

        if limit:
            history = history[-limit:]

        return history

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary.

        Returns:
            Dictionary with summary statistics
        """
        with self.lock:
            history = list(self.performance_history)

        if not history:
            return {}

        # Group by metric
        by_metric = {}

        for data in history:
            if data.metric not in by_metric:
                by_metric[data.metric] = []

            by_metric[data.metric].append(data.value)

        # Calculate stats for each metric
        summary = {}

        for metric, values in by_metric.items():
            if not values:
                continue

            summary[metric.value] = {
                'count': len(values),
                'min': min(values),
                'max': max(values),
                'average': sum(values) / len(values),
            }

        return summary

    def export_performance_data(self, export_path: str) -> Tuple[bool, str]:
        """Export performance data to file.

        Args:
            export_path: Path to export file

        Returns:
            Tuple of (success, message)
        """
        try:
            with self.lock:
                history = list(self.performance_history)

            data = {
                'plugin_id': self.plugin_id,
                'export_date': datetime.now().isoformat(),
                'data_points': [d.to_dict() for d in history],
                'method_stats': self.get_all_method_stats(),
                'summary': self.get_performance_summary(),
            }

            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Exported performance data to {export_path}")
            return True, f"Exported {len(history)} data points"

        except Exception as e:
            logger.error(f"Failed to export performance data: {e}")
            return False, str(e)

    def reset_performance_data(self) -> None:
        """Reset all performance data."""
        with self.lock:
            self.performance_history.clear()

        for profiler in self.method_profilers.values():
            profiler.reset()

        logger.info(f"Reset performance data for {self.plugin_id}")

    def get_alert_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all alerts.

        Returns:
            Dictionary of alert statuses
        """
        status = {}

        for alert_id, alert in self.alerts.items():
            status[alert_id] = {
                'triggered': alert.triggered,
                'trigger_count': alert.trigger_count,
                'last_triggered': alert.last_triggered,
                'metric': alert.metric.value,
                'threshold': alert.threshold,
                'operator': alert.operator,
            }

        return status


class PerformanceAnalyzer:
    """Analyzes performance data to identify issues."""

    @staticmethod
    def detect_memory_leak(
        monitor: PluginPerformanceMonitor,
        window_size: int = 100
    ) -> Tuple[bool, float]:
        """Detect potential memory leak.

        Args:
            monitor: Performance monitor instance
            window_size: Window size for trend analysis

        Returns:
            Tuple of (leak_detected, trend_slope)
        """
        history = monitor.get_performance_history(
            metric=PerformanceMetric.MEMORY_USAGE
        )

        if len(history) < window_size:
            return False, 0.0

        # Get recent data
        recent = [d.value for d in history[-window_size:]]

        # Simple linear regression to detect trend
        n = len(recent)
        x = list(range(n))
        y = recent

        mean_x = sum(x) / n
        mean_y = sum(y) / n

        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        denominator = sum((x[i] - mean_x) ** 2 for i in range(n))

        if denominator == 0:
            return False, 0.0

        slope = numerator / denominator

        # Trend is concerning if memory consistently increases
        leak_detected = slope > 0.5  # Threshold in MB per sample

        return leak_detected, slope

    @staticmethod
    def identify_bottlenecks(
        monitor: PluginPerformanceMonitor,
        percentile: float = 0.95
    ) -> List[Tuple[str, float]]:
        """Identify performance bottlenecks.

        Args:
            monitor: Performance monitor instance
            percentile: Percentile threshold (0-1)

        Returns:
            List of (method_name, execution_time) sorted by time
        """
        bottlenecks = []

        for method_name, stats in monitor.get_all_method_stats().items():
            if 'p95' in stats:
                bottlenecks.append((method_name, stats['p95']))

        # Sort by execution time descending
        bottlenecks.sort(key=lambda x: x[1], reverse=True)

        return bottlenecks

    @staticmethod
    def calculate_throughput(
        monitor: PluginPerformanceMonitor,
        duration_seconds: int = 60
    ) -> float:
        """Calculate operation throughput.

        Args:
            monitor: Performance monitor instance
            duration_seconds: Time window in seconds

        Returns:
            Operations per second
        """
        history = monitor.get_performance_history()

        if not history:
            return 0.0

        # Count operations in recent window
        cutoff_time = (datetime.fromisoformat(history[-1].timestamp) -
                      __import__('datetime').timedelta(seconds=duration_seconds))

        recent_ops = [d for d in history
                     if datetime.fromisoformat(d.timestamp) > cutoff_time]

        if not recent_ops:
            return 0.0

        throughput = len(recent_ops) / duration_seconds

        return throughput


# Compatibility for datetime import
import datetime as dt
