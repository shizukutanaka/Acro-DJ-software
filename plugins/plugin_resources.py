# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Plugin Resource Management System for Acro DJ Mixer

Provides:
- CPU and memory quota management
- Resource monitoring and enforcement
- Resource pool management
- Resource allocation and deallocation
- Resource warnings and limits
- Multi-plugin resource coordination
"""

import logging
import threading
from typing import Dict, Optional, List, Tuple, Any
from dataclasses import dataclass, asdict, field
from enum import Enum
from datetime import datetime
import psutil

logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """Types of resources to manage."""
    CPU = "cpu"              # CPU percentage
    MEMORY = "memory"        # Memory in MB
    DISK = "disk"            # Disk space in MB
    THREADS = "threads"      # Number of threads
    FILE_HANDLES = "files"   # Open file handles


@dataclass
class ResourceQuota:
    """Resource quota for a plugin."""
    plugin_id: str
    resource_type: ResourceType
    limit: float              # Maximum value
    warning_threshold: float = 0.8  # Warn at 80% usage
    hard_limit: bool = False  # Enforce hard limit

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ResourceUsage:
    """Current resource usage."""
    plugin_id: str
    resource_type: ResourceType
    current_value: float
    timestamp: str = ""
    quota: Optional[ResourceQuota] = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            'plugin_id': self.plugin_id,
            'resource_type': self.resource_type.value,
            'current_value': self.current_value,
            'timestamp': self.timestamp,
        }

    def get_usage_percent(self) -> float:
        """Get usage as percentage of quota.

        Returns:
            Usage percentage (0-100)
        """
        if not self.quota or self.quota.limit == 0:
            return 0.0

        return (self.current_value / self.quota.limit) * 100.0


@dataclass
class ResourceAlert:
    """Alert when resource exceeds threshold."""
    alert_id: str
    plugin_id: str
    resource_type: ResourceType
    alert_type: str  # "warning" or "critical"
    message: str
    current_value: float
    threshold: float
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return asdict(self)


class ResourceMonitor:
    """Monitors resource usage of a plugin."""

    def __init__(self, plugin_id: str):
        """Initialize resource monitor.

        Args:
            plugin_id: Plugin identifier
        """
        self.plugin_id = plugin_id
        self.process = None
        self.quotas: Dict[ResourceType, ResourceQuota] = {}
        self.alerts: Dict[str, ResourceAlert] = {}
        self.alert_callbacks: List[callable] = []
        self.lock = threading.RLock()

        try:
            self.process = psutil.Process()
        except Exception as e:
            logger.warning(f"Could not get process info: {e}")

    def set_quota(self, quota: ResourceQuota) -> None:
        """Set resource quota.

        Args:
            quota: ResourceQuota to set
        """
        with self.lock:
            self.quotas[quota.resource_type] = quota
            logger.info(f"Set quota for {self.plugin_id}: {quota.resource_type.value} = {quota.limit}")

    def get_quota(self, resource_type: ResourceType) -> Optional[ResourceQuota]:
        """Get resource quota.

        Args:
            resource_type: Type of resource

        Returns:
            ResourceQuota or None
        """
        return self.quotas.get(resource_type)

    def get_cpu_usage(self) -> float:
        """Get current CPU usage percentage.

        Returns:
            CPU usage percentage
        """
        if not self.process:
            return 0.0

        try:
            return self.process.cpu_percent(interval=0.1)
        except Exception as e:
            logger.warning(f"Could not measure CPU: {e}")
            return 0.0

    def get_memory_usage(self) -> float:
        """Get current memory usage in MB.

        Returns:
            Memory usage in MB
        """
        if not self.process:
            return 0.0

        try:
            mem_info = self.process.memory_info()
            return mem_info.rss / (1024 * 1024)
        except Exception as e:
            logger.warning(f"Could not measure memory: {e}")
            return 0.0

    def get_thread_count(self) -> int:
        """Get number of threads.

        Returns:
            Thread count
        """
        if not self.process:
            return 0

        try:
            return self.process.num_threads()
        except Exception as e:
            logger.warning(f"Could not count threads: {e}")
            return 0

    def check_quotas(self) -> List[ResourceAlert]:
        """Check if any quotas are exceeded.

        Returns:
            List of ResourceAlert objects
        """
        alerts = []

        for resource_type, quota in self.quotas.items():
            usage = self.measure_resource(resource_type)

            if usage is None:
                continue

            usage_percent = (usage / quota.limit * 100) if quota.limit > 0 else 0

            # Check warning threshold
            warning_threshold = quota.limit * quota.warning_threshold

            if usage >= warning_threshold:
                alert = ResourceAlert(
                    alert_id=f"{self.plugin_id}_{resource_type.value}",
                    plugin_id=self.plugin_id,
                    resource_type=resource_type,
                    alert_type="warning",
                    message=f"{resource_type.value} usage at {usage_percent:.1f}%",
                    current_value=usage,
                    threshold=warning_threshold
                )
                alerts.append(alert)

                # Check hard limit
                if quota.hard_limit and usage > quota.limit:
                    alert.alert_type = "critical"
                    alert.threshold = quota.limit

                # Trigger callbacks
                for callback in self.alert_callbacks:
                    try:
                        callback(alert)
                    except Exception as e:
                        logger.error(f"Error in alert callback: {e}")

        return alerts

    def measure_resource(self, resource_type: ResourceType) -> Optional[float]:
        """Measure a specific resource.

        Args:
            resource_type: Type of resource

        Returns:
            Resource value or None
        """
        if resource_type == ResourceType.CPU:
            return self.get_cpu_usage()
        elif resource_type == ResourceType.MEMORY:
            return self.get_memory_usage()
        elif resource_type == ResourceType.THREADS:
            return float(self.get_thread_count())
        else:
            return None

    def on_resource_alert(self, callback: callable) -> None:
        """Register alert callback.

        Args:
            callback: Callback function
        """
        self.alert_callbacks.append(callback)


class ResourcePool:
    """Manages shared resource pool across plugins."""

    def __init__(
        self,
        total_cpu_percent: float = 100.0,
        total_memory_mb: float = 1000.0
    ):
        """Initialize resource pool.

        Args:
            total_cpu_percent: Total CPU percentage to allocate
            total_memory_mb: Total memory in MB to allocate
        """
        self.total_cpu = total_cpu_percent
        self.total_memory = total_memory_mb

        self.allocated_cpu: Dict[str, float] = {}
        self.allocated_memory: Dict[str, float] = {}

        self.monitors: Dict[str, ResourceMonitor] = {}

        self.lock = threading.RLock()

    def allocate_cpu(self, plugin_id: str, cpu_percent: float) -> bool:
        """Allocate CPU percentage to plugin.

        Args:
            plugin_id: Plugin identifier
            cpu_percent: CPU percentage to allocate

        Returns:
            True if allocation successful
        """
        with self.lock:
            current_total = sum(self.allocated_cpu.values())

            if current_total + cpu_percent > self.total_cpu:
                logger.warning(
                    f"CPU allocation would exceed total "
                    f"({current_total + cpu_percent} > {self.total_cpu})"
                )
                return False

            self.allocated_cpu[plugin_id] = cpu_percent

            # Create quota
            quota = ResourceQuota(
                plugin_id=plugin_id,
                resource_type=ResourceType.CPU,
                limit=cpu_percent
            )

            if plugin_id in self.monitors:
                self.monitors[plugin_id].set_quota(quota)

            logger.info(f"Allocated {cpu_percent}% CPU to {plugin_id}")
            return True

    def allocate_memory(self, plugin_id: str, memory_mb: float) -> bool:
        """Allocate memory to plugin.

        Args:
            plugin_id: Plugin identifier
            memory_mb: Memory in MB to allocate

        Returns:
            True if allocation successful
        """
        with self.lock:
            current_total = sum(self.allocated_memory.values())

            if current_total + memory_mb > self.total_memory:
                logger.warning(
                    f"Memory allocation would exceed total "
                    f"({current_total + memory_mb} > {self.total_memory})"
                )
                return False

            self.allocated_memory[plugin_id] = memory_mb

            # Create quota
            quota = ResourceQuota(
                plugin_id=plugin_id,
                resource_type=ResourceType.MEMORY,
                limit=memory_mb
            )

            if plugin_id in self.monitors:
                self.monitors[plugin_id].set_quota(quota)

            logger.info(f"Allocated {memory_mb}MB memory to {plugin_id}")
            return True

    def register_monitor(self, monitor: ResourceMonitor) -> None:
        """Register resource monitor.

        Args:
            monitor: ResourceMonitor instance
        """
        with self.lock:
            self.monitors[monitor.plugin_id] = monitor

    def get_available_cpu(self) -> float:
        """Get available CPU percentage.

        Returns:
            Available CPU percentage
        """
        with self.lock:
            used = sum(self.allocated_cpu.values())
            return max(0, self.total_cpu - used)

    def get_available_memory(self) -> float:
        """Get available memory in MB.

        Returns:
            Available memory in MB
        """
        with self.lock:
            used = sum(self.allocated_memory.values())
            return max(0, self.total_memory - used)

    def get_resource_summary(self) -> Dict[str, Any]:
        """Get resource pool summary.

        Returns:
            Dictionary with summary
        """
        with self.lock:
            cpu_allocated = sum(self.allocated_cpu.values())
            memory_allocated = sum(self.allocated_memory.values())

            return {
                'total_cpu': self.total_cpu,
                'allocated_cpu': cpu_allocated,
                'available_cpu': self.get_available_cpu(),
                'total_memory': self.total_memory,
                'allocated_memory': memory_allocated,
                'available_memory': self.get_available_memory(),
                'plugins': len(self.monitors),
                'allocations': {
                    'cpu': self.allocated_cpu.copy(),
                    'memory': self.allocated_memory.copy(),
                }
            }
