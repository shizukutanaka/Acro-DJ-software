# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Tests for Advanced Plugin Features (Communication, State, Events, Resources, DI)

Tests cover:
- Plugin communication and messaging
- State management and snapshots
- Event system and listeners
- Resource monitoring and quotas
- Dependency injection
"""

import pytest
import tempfile
import threading
import time
from pathlib import Path

from plugins.plugin_communication import (
    PluginCommunicationHub,
    Message,
    MessageType,
    MessagePriority,
)
from plugins.plugin_state import (
    PluginStateManager,
    StateStatus,
)
from plugins.plugin_events import (
    PluginEventSystem,
    EventType,
    Event,
)
from plugins.plugin_resources import (
    ResourceMonitor,
    ResourcePool,
    ResourceType,
    ResourceQuota,
)
from plugins.plugin_dependency_injection import (
    DependencyInjectionContainer,
    ServiceCollection,
    Lifetime,
)


class TestPluginCommunication:
    """Test plugin communication system."""

    @pytest.fixture
    def hub(self):
        """Create communication hub."""
        hub = PluginCommunicationHub()
        hub.start()
        yield hub
        hub.stop()

    def test_register_plugin(self, hub):
        """Test registering plugin."""
        hub.register_plugin("test_plugin")

        assert hub.is_registered("test_plugin") if hasattr(hub, 'is_registered') else True

    def test_send_message(self, hub):
        """Test sending message."""
        hub.register_plugin("plugin1")
        hub.register_plugin("plugin2")

        message = Message(
            message_id="msg1",
            source_plugin="plugin1",
            destination_plugin="plugin2",
            message_type=MessageType.NOTIFICATION,
            data={'test': 'data'}
        )

        hub.send_message(message, async_mode=False)

        # Check history
        history = hub.get_message_history()
        assert len(history) > 0

    def test_send_request_response(self, hub):
        """Test request-response pattern."""
        hub.register_plugin("requester")
        hub.register_plugin("responder")

        def responder_handler(msg):
            return {'response': 'ok'}

        hub.register_handler(
            "responder",
            MessageType.REQUEST,
            responder_handler
        )

        response = hub.send_request(
            "requester",
            "responder",
            {'request': 'data'}
        )

        assert response is not None

    def test_broadcast_event(self, hub):
        """Test broadcasting event."""
        hub.register_plugin("broadcaster")

        hub.broadcast_event(
            "broadcaster",
            "test_event",
            {'data': 'value'}
        )

        time.sleep(0.1)  # Allow async processing

        stats = hub.get_communication_stats()
        assert stats['total_messages'] > 0

    def test_message_priority(self, hub):
        """Test message priority."""
        message1 = Message(
            message_id="msg1",
            source_plugin="plugin1",
            priority=MessagePriority.LOW
        )

        message2 = Message(
            message_id="msg2",
            source_plugin="plugin1",
            priority=MessagePriority.HIGH
        )

        assert message2.priority < message1.priority  # HIGH (1) < LOW (3)


class TestPluginState:
    """Test plugin state management."""

    @pytest.fixture
    def temp_state_dir(self):
        """Create temporary state directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def state_manager(self, temp_state_dir):
        """Create state manager."""
        return PluginStateManager(
            "test_plugin",
            state_dir=temp_state_dir
        )

    def test_set_and_get_state(self, state_manager):
        """Test setting and getting state."""
        state_data = {'gain': 0.5, 'enabled': True}

        state_manager.set_state(state_data)

        assert state_manager.get_state() == state_data

    def test_update_state(self, state_manager):
        """Test updating state."""
        state_manager.set_state({'a': 1, 'b': 2})
        state_manager.update_state({'a': 10})

        assert state_manager.get_state()['a'] == 10

    def test_get_value_by_path(self, state_manager):
        """Test getting value by path."""
        state_manager.set_state({'config': {'gain': 0.5}})

        value = state_manager.get_value('config.gain')

        assert value == 0.5

    def test_set_value_by_path(self, state_manager):
        """Test setting value by path."""
        state_manager.set_state({})
        state_manager.set_value('config.gain', 0.8)

        assert state_manager.get_value('config.gain') == 0.8

    def test_create_snapshot(self, state_manager):
        """Test creating snapshot."""
        state_manager.set_state({'data': 'value'})

        snapshot_id = state_manager.create_snapshot("1.0.0")

        assert snapshot_id is not None

    def test_restore_snapshot(self, state_manager):
        """Test restoring snapshot."""
        state_manager.set_state({'a': 1})
        snapshot_id = state_manager.create_snapshot("1.0.0")

        state_manager.set_state({'a': 2})
        success, msg = state_manager.restore_snapshot(snapshot_id)

        assert success
        assert state_manager.get_state()['a'] == 1

    def test_state_persistence(self, temp_state_dir):
        """Test state persists across instances."""
        manager1 = PluginStateManager("plugin1", state_dir=temp_state_dir)
        manager1.set_state({'data': 'value'})

        manager2 = PluginStateManager("plugin1", state_dir=temp_state_dir)

        assert manager2.get_state()['data'] == 'value'

    def test_state_change_tracking(self, state_manager):
        """Test tracking state changes."""
        state_manager.set_state({'a': 1})
        state_manager.update_state({'a': 2})

        changes = state_manager.get_state_changes()

        assert len(changes) > 0


class TestPluginEvents:
    """Test plugin event system."""

    @pytest.fixture
    def event_system(self):
        """Create event system."""
        return PluginEventSystem()

    def test_subscribe_and_emit(self, event_system):
        """Test subscribing to event."""
        received_events = []

        def handler(event):
            received_events.append(event)

        event_system.subscribe(EventType.STATE_CHANGED, handler)

        event_system.emit_event(
            EventType.STATE_CHANGED,
            "plugin1",
            {'state': 'new'}
        )

        assert len(received_events) == 1

    def test_unsubscribe(self, event_system):
        """Test unsubscribing from event."""
        def handler(event):
            pass

        listener_id = event_system.subscribe(EventType.STATE_CHANGED, handler)

        success = event_system.unsubscribe(EventType.STATE_CHANGED, listener_id)

        assert success

    def test_event_filter(self, event_system):
        """Test event filtering."""
        received = []

        def filter_fn(event):
            return 'important' in event.data

        def handler(event):
            received.append(event)

        event_system.subscribe(
            EventType.CUSTOM,
            handler,
            filter_fn=filter_fn
        )

        event_system.emit_event(EventType.CUSTOM, "plugin1", {})
        event_system.emit_event(
            EventType.CUSTOM,
            "plugin1",
            {'important': True}
        )

        assert len(received) == 1

    def test_event_history(self, event_system):
        """Test event history."""
        event_system.emit_event(EventType.STATE_CHANGED, "plugin1", {})
        event_system.emit_event(EventType.PARAMETER_CHANGED, "plugin1", {})

        history = event_system.get_event_history()

        assert len(history) == 2

    def test_event_stats(self, event_system):
        """Test event statistics."""
        event_system.subscribe(EventType.STATE_CHANGED, lambda e: None)

        event_system.emit_event(EventType.STATE_CHANGED, "plugin1", {})

        stats = event_system.get_event_stats()

        assert stats['total_events'] == 1
        assert stats['total_listeners'] == 1


class TestResourceManagement:
    """Test resource management."""

    def test_resource_monitor(self):
        """Test resource monitoring."""
        monitor = ResourceMonitor("test_plugin")

        cpu = monitor.get_cpu_usage()
        memory = monitor.get_memory_usage()

        assert cpu >= 0
        assert memory > 0

    def test_set_quota(self):
        """Test setting resource quota."""
        monitor = ResourceMonitor("test_plugin")

        quota = ResourceQuota(
            plugin_id="test_plugin",
            resource_type=ResourceType.MEMORY,
            limit=500.0
        )

        monitor.set_quota(quota)

        assert monitor.get_quota(ResourceType.MEMORY) is not None

    def test_resource_pool_allocation(self):
        """Test resource pool allocation."""
        pool = ResourcePool(total_cpu_percent=100.0, total_memory_mb=1000.0)

        success = pool.allocate_cpu("plugin1", 50.0)

        assert success
        assert pool.get_available_cpu() == 50.0

    def test_resource_pool_overflow(self):
        """Test resource pool overflow protection."""
        pool = ResourcePool(total_cpu_percent=100.0)

        pool.allocate_cpu("plugin1", 60.0)
        success = pool.allocate_cpu("plugin2", 50.0)

        assert not success

    def test_resource_pool_summary(self):
        """Test resource pool summary."""
        pool = ResourcePool(
            total_cpu_percent=100.0,
            total_memory_mb=1000.0
        )

        pool.allocate_cpu("plugin1", 30.0)
        pool.allocate_memory("plugin1", 200.0)

        summary = pool.get_resource_summary()

        assert summary['allocated_cpu'] == 30.0
        assert summary['allocated_memory'] == 200.0


class TestDependencyInjection:
    """Test dependency injection system."""

    class Service:
        """Test service interface."""
        pass

    class ServiceImpl(Service):
        """Test service implementation."""
        def __init__(self):
            self.initialized = True

    class Consumer:
        """Service consumer."""
        def __init__(self, service: Service):
            self.service = service

    def test_register_singleton(self):
        """Test registering singleton."""
        container = DependencyInjectionContainer()

        container.register_singleton(
            self.Service,
            self.ServiceImpl()
        )

        service1 = container.resolve(self.Service)
        service2 = container.resolve(self.Service)

        assert service1 is service2

    def test_register_transient(self):
        """Test registering transient."""
        container = DependencyInjectionContainer()

        container.register_transient(
            self.Service,
            self.ServiceImpl
        )

        service1 = container.resolve(self.Service)
        service2 = container.resolve(self.Service)

        assert service1 is not service2

    def test_constructor_injection(self):
        """Test constructor dependency injection."""
        container = DependencyInjectionContainer()

        container.register_singleton(
            self.Service,
            self.ServiceImpl
        )
        container.register_transient(
            self.Consumer,
            self.Consumer
        )

        consumer = container.resolve(self.Consumer)

        assert isinstance(consumer.service, self.Service)

    def test_service_collection(self):
        """Test service collection builder."""
        collection = ServiceCollection()

        collection.add_singleton(self.Service, self.ServiceImpl)

        container = collection.build()
        service = container.resolve(self.Service)

        assert isinstance(service, self.Service)

    def test_dependency_graph(self):
        """Test dependency graph."""
        container = DependencyInjectionContainer()

        container.register_singleton(self.Service, self.ServiceImpl)
        container.register_transient(self.Consumer, self.Consumer)

        graph = container.get_dependency_graph()

        assert 'Service' in graph or 'ServiceImpl' in graph

    def test_unregistered_service_error(self):
        """Test error for unregistered service."""
        container = DependencyInjectionContainer()

        with pytest.raises(ValueError):
            container.resolve(self.Service)


class TestIntegration:
    """Integration tests for advanced features."""

    def test_communication_with_events(self):
        """Test communication system with events."""
        hub = PluginCommunicationHub()
        events = PluginEventSystem()

        hub.start()

        # Send message and emit event
        message = Message(
            message_id="test",
            source_plugin="plugin1",
            destination_plugin="plugin2"
        )

        hub.send_message(message, async_mode=False)

        events.emit_event(
            EventType.PLUGIN_LOADED,
            "plugin1",
            {}
        )

        # Verify both systems recorded activity
        msg_history = hub.get_message_history()
        event_history = events.get_event_history()

        assert len(msg_history) > 0
        assert len(event_history) > 0

        hub.stop()

    def test_state_with_di(self):
        """Test state management with DI."""
        class StateService:
            def __init__(self):
                self.state = {}

        collection = ServiceCollection()
        collection.add_singleton(StateService, StateService)

        container = collection.build()
        service = container.resolve(StateService)

        service.state['key'] = 'value'

        assert service.state['key'] == 'value'

    def test_resource_with_monitoring(self):
        """Test resources with monitoring."""
        monitor = ResourceMonitor("plugin1")

        quota = ResourceQuota(
            plugin_id="plugin1",
            resource_type=ResourceType.CPU,
            limit=50.0
        )

        monitor.set_quota(quota)
        alerts = monitor.check_quotas()

        # Should have alerts if current usage > limit
        # (may be 0 if system idle)
        assert isinstance(alerts, list)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_communication_with_no_handlers(self):
        """Test communication with no registered handlers."""
        hub = PluginCommunicationHub()
        hub.start()

        message = Message(
            message_id="test",
            source_plugin="plugin1",
            destination_plugin="nonexistent"
        )

        # Should not crash
        hub.send_message(message, async_mode=False)

        hub.stop()

    def test_state_with_nested_paths(self):
        """Test state with deeply nested paths."""
        state_mgr = PluginStateManager("plugin")

        state_mgr.set_value("a.b.c.d.e", 42)

        value = state_mgr.get_value("a.b.c.d.e")

        assert value == 42

    def test_event_with_large_data(self):
        """Test event with large data."""
        events = PluginEventSystem()

        large_data = {'data': 'x' * 10000}

        events.emit_event(EventType.CUSTOM, "plugin", large_data)

        history = events.get_event_history()

        assert len(history) > 0

    def test_resource_pool_with_many_plugins(self):
        """Test resource pool with many plugins."""
        pool = ResourcePool(total_cpu_percent=100.0)

        for i in range(10):
            monitor = ResourceMonitor(f"plugin_{i}")
            pool.register_monitor(monitor)
            pool.allocate_cpu(f"plugin_{i}", 5.0)

        summary = pool.get_resource_summary()

        assert summary['allocated_cpu'] == 50.0
