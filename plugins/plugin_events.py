# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Plugin Event System for Acro DJ Mixer

Provides:
- Event emission and listening
- Event filtering and routing
- Event priorities and ordering
- Event context propagation
- Event aggregation and debouncing
- Event history and logging
"""

import logging
import threading
import uuid
from typing import List, Dict, Optional, Callable, Any, Set
from dataclasses import dataclass, asdict, field
from enum import Enum
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Plugin event types."""
    PLUGIN_LOADED = "plugin_loaded"
    PLUGIN_UNLOADED = "plugin_unloaded"
    PLUGIN_ENABLED = "plugin_enabled"
    PLUGIN_DISABLED = "plugin_disabled"
    STATE_CHANGED = "state_changed"
    PARAMETER_CHANGED = "parameter_changed"
    PROFILE_LOADED = "profile_loaded"
    ERROR_OCCURRED = "error_occurred"
    PERFORMANCE_WARNING = "performance_warning"
    VERSION_UPDATED = "version_updated"
    CUSTOM = "custom"


@dataclass
class Event:
    """An event in the plugin system."""
    event_id: str
    event_type: EventType
    source_plugin: str
    timestamp: str
    data: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # Higher = higher priority
    handled: bool = False

    def __post_init__(self):
        if not self.event_id:
            self.event_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            'event_id': self.event_id,
            'event_type': self.event_type.value,
            'source_plugin': self.source_plugin,
            'timestamp': self.timestamp,
            'data': self.data,
            'priority': self.priority,
            'handled': self.handled,
        }


@dataclass
class EventListener:
    """Listener for events."""
    listener_id: str
    callback: Callable
    event_type: EventType
    filter_fn: Optional[Callable] = None  # Additional filter
    priority: int = 0


class PluginEventSystem:
    """Event system for plugin communication."""

    def __init__(self, max_history: int = 500):
        """Initialize event system.

        Args:
            max_history: Maximum events to keep in history
        """
        # Event listeners by event type
        self.listeners: Dict[EventType, List[EventListener]] = defaultdict(list)

        # Event history
        self.event_history: List[Event] = []
        self.max_history = max_history

        # Listener tracking
        self.listener_count = 0

        # Event filters
        self.global_filters: List[Callable] = []

        # Thread lock
        self.lock = threading.RLock()

    def subscribe(
        self,
        event_type: EventType,
        callback: Callable,
        filter_fn: Optional[Callable] = None,
        priority: int = 0
    ) -> str:
        """Subscribe to event type.

        Args:
            event_type: Type of event to listen for
            callback: Callback function
            filter_fn: Optional filter function
            priority: Listener priority (higher = called first)

        Returns:
            Listener ID
        """
        listener_id = str(uuid.uuid4())

        listener = EventListener(
            listener_id=listener_id,
            callback=callback,
            event_type=event_type,
            filter_fn=filter_fn,
            priority=priority
        )

        with self.lock:
            self.listeners[event_type].append(listener)

            # Sort by priority
            self.listeners[event_type].sort(
                key=lambda l: l.priority,
                reverse=True
            )

            self.listener_count += 1

        logger.debug(f"Subscribed to {event_type.value} with ID {listener_id}")

        return listener_id

    def unsubscribe(
        self,
        event_type: EventType,
        listener_id: str
    ) -> bool:
        """Unsubscribe from event.

        Args:
            event_type: Event type
            listener_id: Listener ID

        Returns:
            True if unsubscribed
        """
        with self.lock:
            listeners = self.listeners[event_type]

            for i, listener in enumerate(listeners):
                if listener.listener_id == listener_id:
                    listeners.pop(i)
                    self.listener_count -= 1
                    return True

        return False

    def emit(
        self,
        event: Event
    ) -> None:
        """Emit an event.

        Args:
            event: Event to emit
        """
        # Check global filters
        for global_filter in self.global_filters:
            if not global_filter(event):
                return

        # Store in history
        with self.lock:
            self.event_history.append(event)

            if len(self.event_history) > self.max_history:
                self.event_history.pop(0)

        # Call listeners
        listeners = self.listeners.get(event.event_type, [])

        for listener in listeners:
            # Check listener filter
            if listener.filter_fn and not listener.filter_fn(event):
                continue

            try:
                listener.callback(event)
                event.handled = True
            except Exception as e:
                logger.error(f"Error in event listener: {e}")

    def emit_event(
        self,
        event_type: EventType,
        source_plugin: str,
        data: Dict[str, Any],
        priority: int = 0
    ) -> None:
        """Emit a simple event.

        Args:
            event_type: Type of event
            source_plugin: Source plugin ID
            data: Event data
            priority: Event priority
        """
        event = Event(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            source_plugin=source_plugin,
            timestamp=datetime.now().isoformat(),
            data=data,
            priority=priority
        )

        self.emit(event)

    def add_global_filter(self, filter_fn: Callable) -> None:
        """Add global event filter.

        Args:
            filter_fn: Filter function (returns True to allow event)
        """
        with self.lock:
            self.global_filters.append(filter_fn)

    def get_event_history(
        self,
        event_type: Optional[EventType] = None,
        source_plugin: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Event]:
        """Get event history.

        Args:
            event_type: Filter by event type
            source_plugin: Filter by source plugin
            limit: Limit results

        Returns:
            List of events
        """
        with self.lock:
            history = list(self.event_history)

        if event_type:
            history = [e for e in history if e.event_type == event_type]

        if source_plugin:
            history = [e for e in history if e.source_plugin == source_plugin]

        if limit:
            history = history[-limit:]

        return history

    def get_recent_events(
        self,
        count: int = 10
    ) -> List[Event]:
        """Get most recent events.

        Args:
            count: Number of events to return

        Returns:
            List of recent events
        """
        with self.lock:
            return list(self.event_history[-count:])

    def get_listener_count(
        self,
        event_type: Optional[EventType] = None
    ) -> int:
        """Get listener count.

        Args:
            event_type: Count for specific event type

        Returns:
            Number of listeners
        """
        if event_type:
            with self.lock:
                return len(self.listeners.get(event_type, []))
        else:
            return self.listener_count

    def clear_history(self) -> None:
        """Clear event history."""
        with self.lock:
            self.event_history.clear()

    def get_event_stats(self) -> Dict[str, Any]:
        """Get event statistics.

        Returns:
            Dictionary with statistics
        """
        with self.lock:
            history = list(self.event_history)
            listeners = {
                et.value: len(ls) for et, ls in self.listeners.items()
            }

        # Count events by type
        by_type = {}
        for event in history:
            et = event.event_type.value
            by_type[et] = by_type.get(et, 0) + 1

        return {
            'total_events': len(history),
            'by_type': by_type,
            'total_listeners': self.listener_count,
            'listeners': listeners,
        }


class EventAggregator:
    """Aggregates events for batch processing."""

    def __init__(
        self,
        event_system: PluginEventSystem,
        event_type: EventType,
        window_size: int = 10
    ):
        """Initialize event aggregator.

        Args:
            event_system: Event system to monitor
            event_type: Event type to aggregate
            window_size: Number of events to aggregate
        """
        self.event_system = event_system
        self.event_type = event_type
        self.window_size = window_size

        self.aggregated_events: List[Event] = []
        self.lock = threading.RLock()

        # Subscribe to events
        self.listener_id = event_system.subscribe(
            event_type,
            self._on_event
        )

    def _on_event(self, event: Event) -> None:
        """Internal event handler.

        Args:
            event: Event received
        """
        with self.lock:
            self.aggregated_events.append(event)

            if len(self.aggregated_events) >= self.window_size:
                self.on_aggregated_events(self.aggregated_events.copy())
                self.aggregated_events.clear()

    def on_aggregated_events(self, events: List[Event]) -> None:
        """Called when events are aggregated.

        Override this method to handle aggregated events.

        Args:
            events: List of aggregated events
        """
        pass

    def unsubscribe(self) -> None:
        """Stop aggregating events."""
        self.event_system.unsubscribe(self.event_type, self.listener_id)


class EventDebouncer:
    """Debounces events to prevent rapid firing."""

    def __init__(
        self,
        event_system: PluginEventSystem,
        event_type: EventType,
        callback: Callable,
        debounce_ms: int = 100
    ):
        """Initialize event debouncer.

        Args:
            event_system: Event system
            event_type: Event type to debounce
            callback: Callback for debounced event
            debounce_ms: Debounce delay in milliseconds
        """
        self.event_system = event_system
        self.event_type = event_type
        self.callback = callback
        self.debounce_ms = debounce_ms

        self.pending_timer = None
        self.last_event = None
        self.lock = threading.RLock()

        # Subscribe to events
        self.listener_id = event_system.subscribe(
            event_type,
            self._on_event
        )

    def _on_event(self, event: Event) -> None:
        """Internal event handler.

        Args:
            event: Event received
        """
        with self.lock:
            self.last_event = event

            # Cancel pending timer
            if self.pending_timer:
                self.pending_timer.cancel()

            # Schedule debounced callback
            self.pending_timer = threading.Timer(
                self.debounce_ms / 1000.0,
                self._execute_callback
            )
            self.pending_timer.daemon = True
            self.pending_timer.start()

    def _execute_callback(self) -> None:
        """Execute the debounced callback."""
        with self.lock:
            if self.last_event:
                try:
                    self.callback(self.last_event)
                except Exception as e:
                    logger.error(f"Error in debounced callback: {e}")

            self.pending_timer = None

    def unsubscribe(self) -> None:
        """Stop debouncing events."""
        with self.lock:
            if self.pending_timer:
                self.pending_timer.cancel()

        self.event_system.unsubscribe(self.event_type, self.listener_id)
