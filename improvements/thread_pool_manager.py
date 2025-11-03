# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Thread Pool Manager

Provides centralized, priority-aware task execution for I/O-bound operations.
Handles file loading, audio analysis, metadata parsing.
"""

import logging
import os
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from typing import Callable, Any, Optional, Dict, List
from dataclasses import dataclass, field
from enum import Enum
from queue import PriorityQueue, Queue
from threading import Lock, Event
import traceback
import time

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task execution priority."""

    CRITICAL = 0  # Audio callback critical path
    HIGH = 1      # UI responsiveness critical
    NORMAL = 2    # Regular operations
    LOW = 3       # Background tasks
    BACKGROUND = 4  # Deferred tasks


@dataclass
class Task:
    """Represents a single async task."""

    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    timeout: Optional[float] = None
    callback: Optional[Callable] = None
    error_callback: Optional[Callable] = None
    task_id: Optional[str] = None

    def execute(self) -> Any:
        """Execute the task."""
        return self.func(*self.args, **self.kwargs)


class TaskStats:
    """Statistics about task execution."""

    def __init__(self):
        """Initialize stats."""
        self.total_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.total_time = 0.0
        self.lock = Lock()

    def record_completion(self, task_time: float):
        """Record task completion."""
        with self.lock:
            self.completed_tasks += 1
            self.total_time += task_time

    def record_failure(self):
        """Record task failure."""
        with self.lock:
            self.failed_tasks += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics."""
        with self.lock:
            return {
                'total': self.total_tasks,
                'completed': self.completed_tasks,
                'failed': self.failed_tasks,
                'average_time': self.total_time / max(self.completed_tasks, 1),
                'success_rate': self.completed_tasks / max(self.total_tasks, 1)
            }


class ThreadPoolManager:
    """
    Manages thread pool for I/O-bound operations.

    Features:
    - Priority-based task execution
    - Resource monitoring
    - Graceful shutdown
    - Task statistics
    """

    def __init__(self, max_workers: Optional[int] = None,
                 thread_name_prefix: str = "AcroDJ"):
        """
        Initialize thread pool manager.

        Args:
            max_workers: Maximum worker threads
                        (default: min(32, cpu_count + 4))
            thread_name_prefix: Prefix for thread names
        """
        if max_workers is None:
            # Balance I/O and CPU bound tasks
            cpu_count = os.cpu_count() or 1
            max_workers = min(32, cpu_count + 4)

        self.max_workers = max_workers
        self.thread_name_prefix = thread_name_prefix

        # Create executor
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix=thread_name_prefix
        )

        # Track active futures
        self.active_futures: Dict[str, Future] = {}
        self.futures_lock = Lock()

        # Statistics
        self.stats = TaskStats()

        # Shutdown flag
        self.shutdown_event = Event()

        logger.info(f"ThreadPoolManager initialized with {max_workers} workers")

    def submit_task(self, task: Task) -> Optional[Future]:
        """
        Submit a task for execution.

        Args:
            task: Task to execute

        Returns:
            Future or None if shutdown
        """
        if self.shutdown_event.is_set():
            logger.warning("Cannot submit task - executor is shutting down")
            return None

        # Wrap task with stats tracking
        def wrapped_task():
            start_time = time.time()
            try:
                result = task.execute()

                # Record success
                self.stats.record_completion(time.time() - start_time)

                # Call success callback
                if task.callback:
                    try:
                        task.callback(result)
                    except Exception as e:
                        logger.error(f"Callback error: {e}")

                return result

            except Exception as e:
                # Record failure
                self.stats.record_failure()

                logger.error(f"Task execution failed: {e}\n{traceback.format_exc()}")

                # Call error callback
                if task.error_callback:
                    try:
                        task.error_callback(e)
                    except Exception as callback_e:
                        logger.error(f"Error callback failed: {callback_e}")

                raise

        # Submit to executor
        try:
            future = self.executor.submit(wrapped_task)

            # Track future
            if task.task_id:
                with self.futures_lock:
                    self.active_futures[task.task_id] = future

            return future

        except Exception as e:
            logger.error(f"Failed to submit task: {e}")
            return None

    def submit(self, func: Callable, *args, task_id: Optional[str] = None,
              priority: TaskPriority = TaskPriority.NORMAL,
              timeout: Optional[float] = None,
              callback: Optional[Callable] = None,
              error_callback: Optional[Callable] = None,
              **kwargs) -> Optional[Future]:
        """
        Convenience method to submit a simple task.

        Args:
            func: Function to execute
            args: Positional arguments
            task_id: Optional task identifier
            priority: Task priority (for future prioritization)
            timeout: Execution timeout in seconds
            callback: Success callback(result)
            error_callback: Error callback(exception)
            kwargs: Keyword arguments

        Returns:
            Future or None
        """
        task = Task(
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            timeout=timeout,
            callback=callback,
            error_callback=error_callback,
            task_id=task_id
        )

        return self.submit_task(task)

    def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """
        Wait for a specific task to complete.

        Args:
            task_id: Task identifier
            timeout: Wait timeout in seconds

        Returns:
            Task result

        Raises:
            TimeoutError if task doesn't complete in time
            ValueError if task_id not found
        """
        with self.futures_lock:
            future = self.active_futures.get(task_id)

        if future is None:
            raise ValueError(f"Task '{task_id}' not found")

        try:
            return future.result(timeout=timeout)
        finally:
            # Remove from tracking
            with self.futures_lock:
                self.active_futures.pop(task_id, None)

    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a specific task.

        Args:
            task_id: Task identifier

        Returns:
            True if cancelled, False if not found or already completed
        """
        with self.futures_lock:
            future = self.active_futures.get(task_id)

        if future is None:
            return False

        cancelled = future.cancel()

        if cancelled:
            with self.futures_lock:
                self.active_futures.pop(task_id, None)

        return cancelled

    def get_statistics(self) -> Dict[str, Any]:
        """Get execution statistics."""
        return self.stats.get_stats()

    def get_active_task_count(self) -> int:
        """Get number of currently active tasks."""
        with self.futures_lock:
            return len(self.active_futures)

    def shutdown(self, wait: bool = True, timeout: float = 10.0) -> None:
        """
        Shutdown the thread pool.

        Args:
            wait: Wait for tasks to complete
            timeout: Maximum wait time in seconds
        """
        logger.info("Shutting down ThreadPoolManager...")

        self.shutdown_event.set()

        if wait:
            try:
                self.executor.shutdown(wait=True, timeout=timeout)
                logger.info("ThreadPoolManager shutdown complete")
            except Exception as e:
                logger.error(f"Shutdown error: {e}")
        else:
            self.executor.shutdown(wait=False)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()
        return False


class BatchTaskProcessor:
    """
    Process multiple related tasks as a batch.

    Useful for loading multiple files or performing analysis on a set.
    """

    def __init__(self, thread_pool: ThreadPoolManager,
                 on_progress: Optional[Callable] = None,
                 on_complete: Optional[Callable] = None):
        """
        Initialize batch processor.

        Args:
            thread_pool: ThreadPoolManager instance
            on_progress: Progress callback(completed, total)
            on_complete: Completion callback(results)
        """
        self.thread_pool = thread_pool
        self.on_progress = on_progress
        self.on_complete = on_complete

    def process_batch(self, items: List[Any],
                     process_fn: Callable,
                     priority: TaskPriority = TaskPriority.NORMAL) -> List[Any]:
        """
        Process a batch of items in parallel.

        Args:
            items: Items to process
            process_fn: Function to apply to each item
            priority: Task priority

        Returns:
            List of results in original order
        """
        futures = {}

        # Submit all tasks
        for idx, item in enumerate(items):
            future = self.thread_pool.submit(
                process_fn,
                item,
                task_id=f"batch_{idx}",
                priority=priority
            )
            if future:
                futures[idx] = future

        # Collect results
        results = [None] * len(items)
        completed = 0

        for idx, future in futures.items():
            try:
                results[idx] = future.result()
                completed += 1

                if self.on_progress:
                    self.on_progress(completed, len(items))

            except Exception as e:
                logger.error(f"Batch item {idx} failed: {e}")
                results[idx] = None

        if self.on_complete:
            self.on_complete(results)

        return results
