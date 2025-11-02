# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Tests for Advanced Plugin Systems (Lifecycle, Sandbox, Testing)

Tests cover:
- Plugin lifecycle management
- Sandbox security and restrictions
- Plugin testing framework
- Marketplace CLI
"""

import pytest
import tempfile
from pathlib import Path

from plugins.plugin_lifecycle import (
    PluginLifecycleManager,
    PluginState,
    PluginStartupConfig,
)
from plugins.plugin_sandbox import (
    PluginSandbox,
    PluginCapability,
    PermissionLevel,
    SandboxPolicy,
)
from plugins.plugin_testing import (
    MockPlugin,
    MockAudioBuffer,
    PluginTestCase,
    PluginPerformanceTest,
    PluginIntegrationTest,
)
from plugins.plugin_marketplace_cli import PluginMarketplaceCLI


class TestPluginLifecycle:
    """Test plugin lifecycle management."""

    @pytest.fixture
    def lifecycle_manager(self):
        """Create lifecycle manager."""
        return PluginLifecycleManager()

    def test_register_plugin(self, lifecycle_manager):
        """Test registering plugin."""
        class TestPluginModule:
            PLUGIN_METADATA = {
                'plugin_id': 'test',
                'name': 'Test',
                'version': '1.0.0',
                'author': 'Dev'
            }

            def create_plugin():
                return MockPlugin()

        success, msg = lifecycle_manager.register_plugin(TestPluginModule)

        assert success

    def test_load_plugin(self, lifecycle_manager):
        """Test loading plugin."""
        class TestPluginModule:
            PLUGIN_METADATA = {
                'plugin_id': 'test',
                'name': 'Test',
                'version': '1.0.0',
                'author': 'Dev'
            }

            def create_plugin():
                return MockPlugin()

        lifecycle_manager.register_plugin(TestPluginModule)
        success, msg = lifecycle_manager.load_plugin('test')

        assert success

    def test_plugin_state_transitions(self, lifecycle_manager):
        """Test plugin state transitions."""
        class TestPluginModule:
            PLUGIN_METADATA = {
                'plugin_id': 'test',
                'name': 'Test',
                'version': '1.0.0',
                'author': 'Dev'
            }

            def create_plugin():
                return MockPlugin()

        lifecycle_manager.register_plugin(TestPluginModule)

        info = lifecycle_manager.get_plugin_info('test')
        assert info.state == PluginState.NOT_LOADED

        lifecycle_manager.load_plugin('test', PluginStartupConfig(auto_initialize=False))

        info = lifecycle_manager.get_plugin_info('test')
        assert info.state == PluginState.LOADED

    def test_unload_plugin(self, lifecycle_manager):
        """Test unloading plugin."""
        class TestPluginModule:
            PLUGIN_METADATA = {
                'plugin_id': 'test',
                'name': 'Test',
                'version': '1.0.0',
                'author': 'Dev'
            }

            def create_plugin():
                return MockPlugin()

        lifecycle_manager.register_plugin(TestPluginModule)
        lifecycle_manager.load_plugin('test', PluginStartupConfig(auto_initialize=False))

        success, msg = lifecycle_manager.unload_plugin('test')

        assert success

    def test_pause_and_resume(self, lifecycle_manager):
        """Test pausing and resuming plugin."""
        class TestPluginModule:
            PLUGIN_METADATA = {
                'plugin_id': 'test',
                'name': 'Test',
                'version': '1.0.0',
                'author': 'Dev'
            }

            def create_plugin():
                return MockPlugin()

        lifecycle_manager.register_plugin(TestPluginModule)
        lifecycle_manager.load_plugin('test', PluginStartupConfig(auto_initialize=False))

        success, msg = lifecycle_manager.pause_plugin('test')
        assert success

        info = lifecycle_manager.get_plugin_info('test')
        assert info.state == PluginState.PAUSED

        success, msg = lifecycle_manager.resume_plugin('test')
        assert success

    def test_lifecycle_callbacks(self, lifecycle_manager):
        """Test lifecycle callbacks."""
        called = {'load': False, 'init': False}

        def on_load(plugin_id, instance):
            called['load'] = True

        def on_init(plugin_id, instance):
            called['init'] = True

        lifecycle_manager.on_load(on_load)
        lifecycle_manager.on_initialize(on_init)

        class TestPluginModule:
            PLUGIN_METADATA = {
                'plugin_id': 'test',
                'name': 'Test',
                'version': '1.0.0',
                'author': 'Dev'
            }

            def create_plugin():
                return MockPlugin()

        lifecycle_manager.register_plugin(TestPluginModule)
        lifecycle_manager.load_plugin('test', PluginStartupConfig(auto_initialize=True))

        assert called['load']
        assert called['init']

    def test_lifecycle_stats(self, lifecycle_manager):
        """Test lifecycle statistics."""
        class TestPluginModule:
            PLUGIN_METADATA = {
                'plugin_id': 'test',
                'name': 'Test',
                'version': '1.0.0',
                'author': 'Dev'
            }

            def create_plugin():
                return MockPlugin()

        lifecycle_manager.register_plugin(TestPluginModule)
        lifecycle_manager.load_plugin('test', PluginStartupConfig(auto_initialize=True))

        stats = lifecycle_manager.get_lifecycle_stats()

        assert stats['total_registered'] == 1
        assert stats['total_loaded'] == 1


class TestPluginSandbox:
    """Test plugin sandbox."""

    def test_sandbox_creation(self):
        """Test creating sandbox."""
        sandbox = PluginSandbox()

        policy = sandbox.create_policy(
            'test_plugin',
            PermissionLevel.SANDBOXED
        )

        assert policy.plugin_id == 'test_plugin'

    def test_capability_check(self):
        """Test capability checking."""
        sandbox = PluginSandbox()

        sandbox.create_policy(
            'test_plugin',
            PermissionLevel.RESTRICTED,
            capabilities={
                PluginCapability.AUDIO_PROCESSING,
                PluginCapability.CONFIGURATION
            }
        )

        assert sandbox.check_capability('test_plugin', PluginCapability.AUDIO_PROCESSING)
        assert not sandbox.check_capability('test_plugin', PluginCapability.FILE_READ)

    def test_api_access_check(self):
        """Test API access checking."""
        sandbox = PluginSandbox()

        sandbox.create_policy(
            'test_plugin',
            PermissionLevel.SANDBOXED
        )

        assert not sandbox.check_api_access('test_plugin', 'os.system')
        assert not sandbox.check_api_access('test_plugin', 'eval')

    def test_resource_limits(self):
        """Test resource limit checking."""
        sandbox = PluginSandbox()

        sandbox.create_policy(
            'test_plugin',
            PermissionLevel.RESTRICTED,
            max_memory_mb=512.0,
            max_cpu_percent=50.0
        )

        assert sandbox.check_resource_limit('test_plugin', 'memory', 256.0)
        assert not sandbox.check_resource_limit('test_plugin', 'memory', 600.0)
        assert sandbox.check_resource_limit('test_plugin', 'cpu', 40.0)
        assert not sandbox.check_resource_limit('test_plugin', 'cpu', 60.0)

    def test_file_access_control(self):
        """Test file access control."""
        sandbox = PluginSandbox()

        sandbox.create_policy(
            'test_plugin',
            PermissionLevel.RESTRICTED,
            allow_file_access=True
        )

        assert sandbox.check_file_access('test_plugin', '/path/file.txt', 'read')

    def test_audit_logging(self):
        """Test audit logging."""
        sandbox = PluginSandbox()

        sandbox.create_policy(
            'test_plugin',
            PermissionLevel.SANDBOXED,
            audit_enabled=True
        )

        # Trigger violation
        sandbox.check_api_access('test_plugin', 'os.system')

        logs = sandbox.get_audit_logs(violations_only=True)

        assert len(logs) > 0

    def test_sandbox_stats(self):
        """Test sandbox statistics."""
        sandbox = PluginSandbox()

        sandbox.create_policy('plugin1', PermissionLevel.UNRESTRICTED)
        sandbox.create_policy('plugin2', PermissionLevel.SANDBOXED)

        stats = sandbox.get_sandbox_stats()

        assert stats['total_policies'] == 2


class TestPluginTesting:
    """Test plugin testing framework."""

    def test_mock_plugin(self):
        """Test mock plugin."""
        plugin = MockPlugin('test_plugin')

        assert plugin.plugin_id == 'test_plugin'
        assert not plugin.initialized

        plugin.initialize({})

        assert plugin.initialized

    def test_mock_audio_buffer(self):
        """Test mock audio buffer."""
        buffer = MockAudioBuffer(sample_rate=44100, duration_seconds=1.0)

        silence = buffer.generate_silence()
        assert silence.shape[0] == 44100

        sine = buffer.generate_sine(1000.0)
        assert sine.shape[0] == 44100

        noise = buffer.generate_white_noise()
        assert noise.shape[0] == 44100

    def test_plugin_test_case(self):
        """Test plugin test case."""
        class TestExample(PluginTestCase):
            def test_audio_shape(self):
                audio = self.create_test_audio()
                self.assert_audio_shape(audio, (44100, 2))

            def test_audio_validity(self):
                audio = self.create_test_audio()
                self.assert_audio_valid(audio)

        suite = TestExample()
        suite.setUp()

        suite.test_audio_shape()
        suite.test_audio_validity()

        suite.tearDown()

    def test_performance_measurement(self):
        """Test performance measurement."""
        plugin = MockPlugin()
        plugin.initialize({})

        perf_test = PluginPerformanceTest(plugin, warmup_iterations=5)

        def process_operation():
            audio = MockAudioBuffer().generate_silence()
            plugin.process_audio(audio)

        latency = perf_test.measure_latency(process_operation, iterations=10)

        assert 'mean' in latency
        assert 'p95' in latency

    def test_integration_testing(self):
        """Test integration testing."""
        plugin = MockPlugin()

        results = PluginIntegrationTest.test_plugin_lifecycle(plugin)

        assert len(results) > 0
        assert all(hasattr(r, 'test_name') for r in results)


class TestPluginMarketplaceCLI:
    """Test marketplace CLI."""

    def test_cli_creation(self):
        """Test CLI creation."""
        cli = PluginMarketplaceCLI()

        assert cli.parser is not None

    def test_cli_search(self):
        """Test search command."""
        cli = PluginMarketplaceCLI()

        exit_code = cli.run(['search', 'effect'])

        assert exit_code == 0

    def test_cli_info(self):
        """Test info command."""
        cli = PluginMarketplaceCLI()

        exit_code = cli.run(['info', 'test_plugin'])

        assert exit_code == 0

    def test_cli_list(self):
        """Test list command."""
        cli = PluginMarketplaceCLI()

        exit_code = cli.run(['list'])

        assert exit_code == 0

    def test_cli_help(self):
        """Test help output."""
        cli = PluginMarketplaceCLI()

        # Should not raise
        cli.run(['--help'])


class TestEdgeCases:
    """Test edge cases."""

    def test_lifecycle_with_missing_methods(self):
        """Test lifecycle with plugin missing methods."""
        class MinimalPlugin:
            pass

        lifecycle = PluginLifecycleManager()

        class TestModule:
            PLUGIN_METADATA = {
                'plugin_id': 'minimal',
                'name': 'Minimal',
                'version': '1.0.0',
                'author': 'Dev'
            }

            def create_plugin():
                return MinimalPlugin()

        lifecycle.register_plugin(TestModule)

        # Should handle gracefully
        lifecycle.load_plugin('minimal', PluginStartupConfig(auto_initialize=False))

    def test_sandbox_with_all_capabilities(self):
        """Test sandbox with all capabilities."""
        sandbox = PluginSandbox()

        sandbox.create_policy(
            'unrestricted',
            PermissionLevel.UNRESTRICTED
        )

        # Should allow everything
        assert sandbox.check_capability('unrestricted', PluginCapability.AUDIO_PROCESSING)
        assert sandbox.check_capability('unrestricted', PluginCapability.NETWORK)
        assert sandbox.check_api_access('unrestricted', 'os.system')

    def test_sandbox_with_no_capabilities(self):
        """Test sandbox with no capabilities."""
        sandbox = PluginSandbox()

        sandbox.create_policy(
            'blocked',
            PermissionLevel.BLOCKED
        )

        # Should deny everything
        assert not sandbox.check_capability('blocked', PluginCapability.AUDIO_PROCESSING)
