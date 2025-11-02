# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Plugin Communication System for Acro DJ Mixer

Provides:
- Inter-plugin communication (message passing)
- RPC (Remote Procedure Call) between plugins
- Event broadcasting system
- Asynchronous message handling
- Message queuing and routing
- Request-response patterns
- Publish-subscribe communication
"""

import json
import logging
import threading
import queue
import uuid
from pathlib import Path
from typing import List, Dict, Optional, Callable, Any, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of messages between plugins."""
    REQUEST = "request"           # Request response from plugin
    RESPONSE = "response"         # Response to request
    EVENT = "event"               # Broadcast event
    NOTIFICATION = "notification" # One-way notification
    COMMAND = "command"           # Execute command
    QUERY = "query"               # Query data


class MessagePriority(Enum):
    """Message priority levels."""
    CRITICAL = 0   # Highest priority
    HIGH = 1
    NORMAL = 2     # Default
    LOW = 3
    DEFERRED = 4   # Lowest priority


@dataclass
class Message:
    """Communication message between plugins."""
    message_id: str
    source_plugin: str
    destination_plugin: Optional[str] = None  # None for broadcast
    message_type: MessageType = MessageType.NOTIFICATION
    priority: MessagePriority = MessagePriority.NORMAL
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    response_expected: bool = False
    timeout_ms: int = 5000

    def __post_init__(self):
        """Initialize defaults."""
        if not self.message_id:
            self.message_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            'message_id': self.message_id,
            'source_plugin': self.source_plugin,
            'destination_plugin': self.destination_plugin,
            'message_type': self.message_type.value,
            'priority': self.priority.value,
            'data': self.data,
            'timestamp': self.timestamp,
            'response_expected': self.response_expected,
            'timeout_ms': self.timeout_ms,
        }


@dataclass
class MessageResponse:
    """Response to a message."""
    message_id: str
    source_plugin: str
    response_data: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error_message: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MessageHandler:
    """Handler for incoming messages."""
    plugin_id: str
    message_type: MessageType
    callback: Callable
    priority: int = 0

    def handle(self, message: Message) -> Optional[MessageResponse]:
        """Execute message handler.

        Args:
            message: Message to handle

        Returns:
            MessageResponse if handler returns data
        """
        try:
            result = self.callback(message)

            if result is not None:
                return MessageResponse(
                    message_id=message.message_id,
                    source_plugin=message.source_plugin,
                    response_data=result if isinstance(result, dict) else {'result': result},
                    success=True
                )
            return None
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            return MessageResponse(
                message_id=message.message_id,
                source_plugin=message.source_plugin,
                success=False,
                error_message=str(e)
            )


class PluginCommunicationHub:
    """Central hub for plugin communication."""

    def __init__(self, max_message_history: int = 1000):
        """Initialize communication hub.

        Args:
            max_message_history: Maximum messages to keep in history
        """
        # Message handlers by plugin
        self.handlers: Dict[str, List[MessageHandler]] = {}

        # Message queue for async processing
        self.message_queue: queue.Queue = queue.Queue()

        # Pending responses (message_id -> response)
        self.pending_responses: Dict[str, queue.Queue] = {}

        # Message history
        self.message_history: List[Message] = []
        self.max_message_history = max_message_history

        # Thread for async message processing
        self.processing_thread = None
        self.running = False

        # Thread lock
        self.lock = threading.RLock()

        # Message callbacks
        self.message_callbacks: Dict[str, List[Callable]] = {}

    def start(self) -> None:
        """Start async message processing."""
        if self.running:
            return

        self.running = True
        self.processing_thread = threading.Thread(
            target=self._process_messages,
            daemon=True
        )
        self.processing_thread.start()
        logger.info("Communication hub started")

    def stop(self) -> None:
        """Stop async message processing."""
        self.running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=5.0)
        logger.info("Communication hub stopped")

    def register_plugin(self, plugin_id: str) -> None:
        """Register a plugin for communication.

        Args:
            plugin_id: Plugin identifier
        """
        with self.lock:
            if plugin_id not in self.handlers:
                self.handlers[plugin_id] = []
                logger.info(f"Registered plugin for communication: {plugin_id}")

    def unregister_plugin(self, plugin_id: str) -> None:
        """Unregister a plugin.

        Args:
            plugin_id: Plugin identifier
        """
        with self.lock:
            if plugin_id in self.handlers:
                del self.handlers[plugin_id]
                logger.info(f"Unregistered plugin: {plugin_id}")

    def register_handler(
        self,
        plugin_id: str,
        message_type: MessageType,
        callback: Callable,
        priority: int = 0
    ) -> str:
        """Register message handler for plugin.

        Args:
            plugin_id: Plugin identifier
            message_type: Type of message to handle
            callback: Handler function
            priority: Handler priority (higher = earlier)

        Returns:
            Handler ID
        """
        with self.lock:
            if plugin_id not in self.handlers:
                self.register_plugin(plugin_id)

            handler = MessageHandler(
                plugin_id=plugin_id,
                message_type=message_type,
                callback=callback,
                priority=priority
            )

            self.handlers[plugin_id].append(handler)

            # Sort by priority
            self.handlers[plugin_id].sort(key=lambda h: h.priority, reverse=True)

            logger.debug(f"Registered handler for {plugin_id}")
            return handler.plugin_id

    def send_message(
        self,
        message: Message,
        async_mode: bool = True
    ) -> Optional[MessageResponse]:
        """Send a message to another plugin.

        Args:
            message: Message to send
            async_mode: Process asynchronously

        Returns:
            MessageResponse if not async, None if async
        """
        # Store in history
        with self.lock:
            self.message_history.append(message)
            if len(self.message_history) > self.max_message_history:
                self.message_history.pop(0)

        if async_mode:
            self.message_queue.put(message)
            return None
        else:
            return self._process_message(message)

    def send_request(
        self,
        source_plugin: str,
        destination_plugin: str,
        data: Dict[str, Any],
        timeout_ms: int = 5000
    ) -> Optional[MessageResponse]:
        """Send a request and wait for response.

        Args:
            source_plugin: Source plugin ID
            destination_plugin: Destination plugin ID
            data: Request data
            timeout_ms: Response timeout in milliseconds

        Returns:
            MessageResponse or None if timeout
        """
        message = Message(
            message_id=str(uuid.uuid4()),
            source_plugin=source_plugin,
            destination_plugin=destination_plugin,
            message_type=MessageType.REQUEST,
            data=data,
            response_expected=True,
            timeout_ms=timeout_ms
        )

        # Create response queue
        response_queue: queue.Queue = queue.Queue()
        self.pending_responses[message.message_id] = response_queue

        try:
            # Send message synchronously
            self.send_message(message, async_mode=False)

            # Wait for response
            try:
                response = response_queue.get(timeout=timeout_ms / 1000.0)
                return response
            except queue.Empty:
                logger.warning(f"Request timeout: {message.message_id}")
                return None
        finally:
            if message.message_id in self.pending_responses:
                del self.pending_responses[message.message_id]

    def broadcast_event(
        self,
        source_plugin: str,
        event_name: str,
        data: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> None:
        """Broadcast event to all plugins.

        Args:
            source_plugin: Plugin broadcasting event
            event_name: Event name
            data: Event data
            priority: Message priority
        """
        message = Message(
            message_id=str(uuid.uuid4()),
            source_plugin=source_plugin,
            destination_plugin=None,  # Broadcast
            message_type=MessageType.EVENT,
            priority=priority,
            data={'event_name': event_name, **data}
        )

        self.send_message(message, async_mode=True)

    def _process_messages(self) -> None:
        """Process queued messages (runs in separate thread)."""
        while self.running:
            try:
                message = self.message_queue.get(timeout=0.1)
                self._process_message(message)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}")

    def _process_message(self, message: Message) -> Optional[MessageResponse]:
        """Process a single message.

        Args:
            message: Message to process

        Returns:
            MessageResponse if applicable
        """
        try:
            # Get target plugins
            if message.destination_plugin:
                targets = [message.destination_plugin]
            else:
                targets = list(self.handlers.keys())

            response = None

            for target in targets:
                if target not in self.handlers:
                    continue

                # Find matching handlers
                handlers = [
                    h for h in self.handlers[target]
                    if h.message_type == message.message_type
                ]

                # Execute handlers
                for handler in handlers:
                    response = handler.handle(message)

                    if response and message.message_id in self.pending_responses:
                        self.pending_responses[message.message_id].put(response)

            # Call message callbacks
            if message.message_type.value in self.message_callbacks:
                for callback in self.message_callbacks[message.message_type.value]:
                    try:
                        callback(message)
                    except Exception as e:
                        logger.error(f"Error in message callback: {e}")

            return response

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return None

    def subscribe(
        self,
        event_name: str,
        callback: Callable
    ) -> str:
        """Subscribe to event type.

        Args:
            event_name: Event name to subscribe to
            callback: Callback function

        Returns:
            Subscription ID
        """
        if event_name not in self.message_callbacks:
            self.message_callbacks[event_name] = []

        self.message_callbacks[event_name].append(callback)

        return str(uuid.uuid4())

    def unsubscribe(
        self,
        event_name: str,
        callback: Callable
    ) -> bool:
        """Unsubscribe from event.

        Args:
            event_name: Event name
            callback: Callback function

        Returns:
            True if unsubscribed
        """
        if event_name in self.message_callbacks:
            try:
                self.message_callbacks[event_name].remove(callback)
                return True
            except ValueError:
                return False
        return False

    def get_message_history(
        self,
        source_plugin: Optional[str] = None,
        message_type: Optional[MessageType] = None,
        limit: Optional[int] = None
    ) -> List[Message]:
        """Get message history.

        Args:
            source_plugin: Filter by source plugin
            message_type: Filter by message type
            limit: Limit results

        Returns:
            List of messages
        """
        with self.lock:
            history = list(self.message_history)

        if source_plugin:
            history = [m for m in history if m.source_plugin == source_plugin]

        if message_type:
            history = [m for m in history if m.message_type == message_type]

        if limit:
            history = history[-limit:]

        return history

    def get_communication_stats(self) -> Dict[str, Any]:
        """Get communication statistics.

        Returns:
            Dictionary with statistics
        """
        with self.lock:
            total_messages = len(self.message_history)
            by_type = {}

            for msg in self.message_history:
                msg_type = msg.message_type.value
                by_type[msg_type] = by_type.get(msg_type, 0) + 1

        return {
            'total_messages': total_messages,
            'by_type': by_type,
            'registered_plugins': len(self.handlers),
            'pending_responses': len(self.pending_responses),
            'queue_size': self.message_queue.qsize(),
        }

    def export_message_log(self, export_path: str) -> Tuple[bool, str]:
        """Export message log to file.

        Args:
            export_path: Path to export file

        Returns:
            Tuple of (success, message)
        """
        try:
            with self.lock:
                messages = [m.to_dict() for m in self.message_history]

            data = {
                'export_date': datetime.now().isoformat(),
                'total_messages': len(messages),
                'messages': messages,
                'stats': self.get_communication_stats(),
            }

            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Exported message log to {export_path}")
            return True, f"Exported {len(messages)} messages"

        except Exception as e:
            logger.error(f"Failed to export message log: {e}")
            return False, str(e)
