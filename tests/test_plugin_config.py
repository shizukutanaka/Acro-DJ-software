# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Tests for Plugin Configuration and Preferences Management System

Tests cover:
- Configuration parameter management
- Profile creation and loading
- Configuration validation and constraints
- Profile import/export
- User preferences
- Batch operations
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime

from plugins.plugin_config import (
    PluginConfigManager,
    ConfigSchema,
    ConfigProfile,
    PresetLibrary,
    ConfigStorageFormat,
)


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory for config files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def config_manager(temp_config_dir):
    """Create a PluginConfigManager instance."""
    return PluginConfigManager(config_dir=temp_config_dir)


@pytest.fixture
def sample_schema():
    """Create a sample configuration schema."""
    return ConfigSchema(
        plugin_id="test_plugin",
        version="1.0.0",
        parameters={
            'gain': {'type': 'float', 'unit': 'dB'},
            'frequency': {'type': 'float', 'unit': 'Hz'},
            'enabled': {'type': 'bool'},
        },
        defaults={
            'gain': 0.0,
            'frequency': 1000.0,
            'enabled': True,
        },
        descriptions={
            'gain': 'Output gain in decibels',
            'frequency': 'Center frequency in Hz',
            'enabled': 'Enable the effect',
        },
        constraints={
            'gain': {'type': float, 'min': -12.0, 'max': 12.0},
            'frequency': {'type': float, 'min': 20.0, 'max': 20000.0},
            'enabled': {'type': bool},
        }
    )


class TestParameterManagement:
    """Test parameter setting and getting."""

    def test_set_and_get_parameter(self, config_manager, sample_schema):
        """Test setting and retrieving a parameter."""
        config_manager.register_schema(sample_schema)

        success, msg = config_manager.set_parameter("test_plugin", "gain", 6.0)
        assert success
        assert config_manager.get_parameter("test_plugin", "gain") == 6.0

    def test_get_default_parameter(self, config_manager, sample_schema):
        """Test retrieving default parameter value."""
        config_manager.register_schema(sample_schema)

        value = config_manager.get_parameter("test_plugin", "gain")
        assert value == 0.0  # default value

    def test_get_nonexistent_parameter(self, config_manager):
        """Test getting non-existent parameter returns default."""
        value = config_manager.get_parameter("nonexistent", "param", default=42)
        assert value == 42

    def test_parameter_validation_type_error(self, config_manager, sample_schema):
        """Test parameter validation for type errors."""
        config_manager.register_schema(sample_schema)

        success, msg = config_manager.set_parameter("test_plugin", "gain", "invalid")
        assert not success
        assert "Invalid type" in msg

    def test_parameter_validation_range_min(self, config_manager, sample_schema):
        """Test parameter validation for minimum constraint."""
        config_manager.register_schema(sample_schema)

        success, msg = config_manager.set_parameter("test_plugin", "gain", -20.0)
        assert not success
        assert "below minimum" in msg

    def test_parameter_validation_range_max(self, config_manager, sample_schema):
        """Test parameter validation for maximum constraint."""
        config_manager.register_schema(sample_schema)

        success, msg = config_manager.set_parameter("test_plugin", "gain", 20.0)
        assert not success
        assert "above maximum" in msg

    def test_set_unknown_parameter(self, config_manager, sample_schema):
        """Test setting an unknown parameter."""
        config_manager.register_schema(sample_schema)

        success, msg = config_manager.set_parameter("test_plugin", "unknown_param", 5.0)
        assert not success
        assert "Unknown parameter" in msg

    def test_get_all_parameters(self, config_manager, sample_schema):
        """Test retrieving all parameters at once."""
        config_manager.register_schema(sample_schema)
        config_manager.set_parameter("test_plugin", "gain", 3.0)
        config_manager.set_parameter("test_plugin", "frequency", 2000.0)

        params = config_manager.get_all_parameters("test_plugin")
        assert params['gain'] == 3.0
        assert params['frequency'] == 2000.0

    def test_batch_set_parameters(self, config_manager, sample_schema):
        """Test setting multiple parameters at once."""
        config_manager.register_schema(sample_schema)

        params = {'gain': 5.0, 'frequency': 1500.0}
        success, errors = config_manager.set_parameters_batch("test_plugin", params)

        assert success
        assert len(errors) == 0
        assert config_manager.get_parameter("test_plugin", "gain") == 5.0

    def test_batch_set_with_errors(self, config_manager, sample_schema):
        """Test batch parameter setting with some invalid values."""
        config_manager.register_schema(sample_schema)

        params = {'gain': 5.0, 'frequency': 50000.0}  # frequency out of range
        success, errors = config_manager.set_parameters_batch("test_plugin", params)

        assert not success
        assert len(errors) == 1
        assert config_manager.get_parameter("test_plugin", "gain") == 5.0


class TestProfileManagement:
    """Test configuration profile creation and management."""

    def test_create_profile(self, config_manager):
        """Test creating a configuration profile."""
        params = {'gain': 3.0, 'frequency': 1000.0}
        success, profile_id = config_manager.create_profile(
            "test_plugin",
            "Bright",
            params,
            "A bright profile"
        )

        assert success
        assert profile_id is not None
        assert "test_plugin" in profile_id

    def test_list_profiles(self, config_manager):
        """Test listing all profiles for a plugin."""
        config_manager.create_profile("test_plugin", "Profile1", {})
        config_manager.create_profile("test_plugin", "Profile2", {})

        profiles = config_manager.list_profiles("test_plugin")
        assert len(profiles) == 2

    def test_load_profile(self, config_manager, sample_schema):
        """Test loading a profile."""
        config_manager.register_schema(sample_schema)

        params = {'gain': 6.0, 'frequency': 2000.0}
        success, profile_id = config_manager.create_profile(
            "test_plugin",
            "Treble Boost",
            params
        )

        # Load the profile
        success, msg = config_manager.load_profile("test_plugin", profile_id)
        assert success
        assert config_manager.get_parameter("test_plugin", "gain") == 6.0

    def test_load_nonexistent_profile(self, config_manager):
        """Test loading a non-existent profile."""
        success, msg = config_manager.load_profile("test_plugin", "nonexistent")
        assert not success
        assert "not found" in msg

    def test_delete_profile(self, config_manager):
        """Test deleting a profile."""
        success, profile_id = config_manager.create_profile(
            "test_plugin",
            "To Delete",
            {}
        )

        # Don't load it (so it's not current)
        config_manager.create_profile("test_plugin", "Keep", {})

        success, msg = config_manager.delete_profile("test_plugin", profile_id)
        assert success

        profiles = config_manager.list_profiles("test_plugin")
        assert profile_id not in [p.profile_id for p in profiles]

    def test_delete_current_profile_fails(self, config_manager):
        """Test that deleting current profile fails."""
        success, profile_id = config_manager.create_profile(
            "test_plugin",
            "Current",
            {}
        )

        config_manager.load_profile("test_plugin", profile_id)

        success, msg = config_manager.delete_profile("test_plugin", profile_id)
        assert not success
        assert "current profile" in msg

    def test_get_current_profile(self, config_manager):
        """Test getting the currently loaded profile."""
        success, profile_id = config_manager.create_profile(
            "test_plugin",
            "Current",
            {'gain': 3.0}
        )

        config_manager.load_profile("test_plugin", profile_id)

        current = config_manager.get_current_profile("test_plugin")
        assert current is not None
        assert current.profile_id == profile_id
        assert current.name == "Current"

    def test_search_profiles_by_name(self, config_manager):
        """Test searching profiles by name."""
        config_manager.create_profile("test_plugin", "Bright Warm", {})
        config_manager.create_profile("test_plugin", "Dark Cool", {})

        results = config_manager.search_profiles("test_plugin", "bright")
        assert len(results) == 1
        assert results[0].name == "Bright Warm"

    def test_search_profiles_by_tags(self, config_manager):
        """Test searching profiles by tags."""
        config_manager.create_profile(
            "test_plugin",
            "Profile1",
            {},
            tags=['electronic', 'edm']
        )
        config_manager.create_profile(
            "test_plugin",
            "Profile2",
            {},
            tags=['jazz', 'acoustic']
        )

        results = config_manager.search_profiles("test_plugin", "edm")
        assert len(results) == 1


class TestProfileImportExport:
    """Test profile import and export functionality."""

    def test_export_profile(self, config_manager, temp_config_dir):
        """Test exporting a profile to file."""
        success, profile_id = config_manager.create_profile(
            "test_plugin",
            "Export Test",
            {'gain': 3.0}
        )

        export_path = Path(temp_config_dir) / "export.json"
        success, msg = config_manager.export_profile(
            "test_plugin",
            profile_id,
            str(export_path)
        )

        assert success
        assert export_path.exists()

        # Verify export content
        with open(export_path) as f:
            data = json.load(f)
            assert data['plugin_id'] == "test_plugin"
            assert data['profile']['name'] == "Export Test"

    def test_import_profile(self, config_manager, temp_config_dir):
        """Test importing a profile from file."""
        # Create and export a profile
        success, profile_id = config_manager.create_profile(
            "test_plugin",
            "Original",
            {'gain': 5.0}
        )

        export_path = Path(temp_config_dir) / "profile.json"
        config_manager.export_profile("test_plugin", profile_id, str(export_path))

        # Create new manager to test import
        config_manager2 = PluginConfigManager(config_dir=temp_config_dir)

        success, imported_id = config_manager2.import_profile(str(export_path))
        assert success

        # Verify imported profile
        imported_profile = config_manager2.get_current_profile("test_plugin")
        assert imported_profile is not None
        assert imported_profile.name == "Original"
        assert imported_profile.parameters['gain'] == 5.0

    def test_export_nonexistent_profile(self, config_manager, temp_config_dir):
        """Test exporting a non-existent profile."""
        export_path = Path(temp_config_dir) / "export.json"
        success, msg = config_manager.export_profile(
            "test_plugin",
            "nonexistent",
            str(export_path)
        )

        assert not success


class TestUserPreferences:
    """Test user preference storage and retrieval."""

    def test_set_and_get_preference(self, config_manager):
        """Test setting and retrieving a preference."""
        config_manager.set_user_preference("test_plugin", "ui_color", "dark")

        value = config_manager.get_user_preference("test_plugin", "ui_color")
        assert value == "dark"

    def test_get_preference_default(self, config_manager):
        """Test getting non-existent preference returns default."""
        value = config_manager.get_user_preference(
            "test_plugin",
            "nonexistent",
            default="default_value"
        )
        assert value == "default_value"

    def test_preference_persistence(self, config_manager, temp_config_dir):
        """Test that preferences persist across instances."""
        config_manager.set_user_preference("test_plugin", "theme", "dark")

        # Create new manager instance
        config_manager2 = PluginConfigManager(config_dir=temp_config_dir)

        value = config_manager2.get_user_preference("test_plugin", "theme")
        assert value == "dark"


class TestConfigurationPersistence:
    """Test configuration persistence to disk."""

    def test_config_persistence(self, config_manager, temp_config_dir):
        """Test that configurations persist across instances."""
        config_manager.set_parameter("test_plugin", "gain", 5.0)

        # Create new manager instance
        config_manager2 = PluginConfigManager(config_dir=temp_config_dir)

        value = config_manager2.get_parameter("test_plugin", "gain")
        assert value == 5.0

    def test_profile_persistence(self, config_manager, temp_config_dir):
        """Test that profiles persist across instances."""
        success, profile_id = config_manager.create_profile(
            "test_plugin",
            "Test Profile",
            {'gain': 3.0}
        )

        # Create new manager instance
        config_manager2 = PluginConfigManager(config_dir=temp_config_dir)

        profiles = config_manager2.list_profiles("test_plugin")
        assert len(profiles) == 1
        assert profiles[0].name == "Test Profile"


class TestResetAndDefaults:
    """Test reset to defaults functionality."""

    def test_reset_to_defaults(self, config_manager, sample_schema):
        """Test resetting configuration to defaults."""
        config_manager.register_schema(sample_schema)

        config_manager.set_parameter("test_plugin", "gain", 10.0)
        config_manager.set_parameter("test_plugin", "frequency", 5000.0)

        success, msg = config_manager.reset_to_defaults("test_plugin")
        assert success

        assert config_manager.get_parameter("test_plugin", "gain") == 0.0
        assert config_manager.get_parameter("test_plugin", "frequency") == 1000.0

    def test_reset_nonexistent_schema(self, config_manager):
        """Test resetting when no schema exists."""
        success, msg = config_manager.reset_to_defaults("nonexistent")
        assert not success
        assert "No schema" in msg


class TestConfigurationStatistics:
    """Test configuration statistics and reporting."""

    def test_get_config_stats(self, config_manager, sample_schema):
        """Test getting configuration statistics."""
        config_manager.register_schema(sample_schema)
        config_manager.set_parameter("test_plugin", "gain", 5.0)
        config_manager.create_profile("test_plugin", "Profile1", {})

        stats = config_manager.get_config_stats()

        assert stats['total_plugins_configured'] == 1
        assert stats['total_profiles'] == 1
        assert stats['total_parameters'] == 1
        assert 'config_dir' in stats
        assert 'storage_format' in stats

    def test_export_all_configs(self, config_manager, temp_config_dir, sample_schema):
        """Test exporting all configurations."""
        config_manager.register_schema(sample_schema)
        config_manager.set_parameter("test_plugin", "gain", 5.0)

        export_dir = Path(temp_config_dir) / "export"
        count, errors = config_manager.export_all_configs(str(export_dir))

        assert count == 1
        assert len(errors) == 0
        assert (export_dir / "test_plugin_config.json").exists()


class TestSchemaRegistration:
    """Test schema registration and management."""

    def test_register_schema(self, config_manager, sample_schema):
        """Test registering a configuration schema."""
        config_manager.register_schema(sample_schema)

        assert "test_plugin" in config_manager.schemas
        schema = config_manager.schemas["test_plugin"]
        assert schema.version == "1.0.0"

    def test_schema_to_dict(self, sample_schema):
        """Test converting schema to dictionary."""
        schema_dict = sample_schema.to_dict()

        assert schema_dict['plugin_id'] == "test_plugin"
        assert schema_dict['version'] == "1.0.0"
        assert 'parameters' in schema_dict


class TestMultiplePlugins:
    """Test managing multiple plugins simultaneously."""

    def test_manage_multiple_plugins(self, config_manager):
        """Test managing configurations for multiple plugins."""
        config_manager.set_parameter("plugin1", "param1", "value1")
        config_manager.set_parameter("plugin2", "param1", "value2")

        assert config_manager.get_parameter("plugin1", "param1") == "value1"
        assert config_manager.get_parameter("plugin2", "param1") == "value2"

    def test_multiple_plugins_profiles(self, config_manager):
        """Test managing profiles for multiple plugins."""
        config_manager.create_profile("plugin1", "Profile1", {})
        config_manager.create_profile("plugin2", "Profile1", {})

        profiles1 = config_manager.list_profiles("plugin1")
        profiles2 = config_manager.list_profiles("plugin2")

        assert len(profiles1) == 1
        assert len(profiles2) == 1
        assert profiles1[0].plugin_id == "plugin1"
        assert profiles2[0].plugin_id == "plugin2"


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_parameter_name(self, config_manager):
        """Test with empty parameter name."""
        success, msg = config_manager.set_parameter("plugin1", "", "value")
        assert not success or msg  # Should handle gracefully

    def test_none_parameter_value(self, config_manager):
        """Test setting None as parameter value."""
        config_manager.set_parameter("plugin1", "param1", None)
        value = config_manager.get_parameter("plugin1", "param1")
        assert value is None

    def test_special_characters_in_names(self, config_manager):
        """Test handling special characters in profile names."""
        success, profile_id = config_manager.create_profile(
            "plugin1",
            "Profile@#$%",
            {}
        )
        assert success

        profiles = config_manager.list_profiles("plugin1")
        assert profiles[0].name == "Profile@#$%"

    def test_very_large_configuration(self, config_manager):
        """Test handling large configurations."""
        large_params = {f"param_{i}": i for i in range(1000)}

        success, errors = config_manager.set_parameters_batch("plugin1", large_params)
        assert success  # Should handle large batch without schema validation

    def test_concurrent_access_simulation(self, config_manager):
        """Test simulating concurrent access patterns."""
        # Set parameters in quick succession
        for i in range(100):
            config_manager.set_parameter("plugin1", f"param_{i}", i)

        # Verify all were set
        for i in range(100):
            value = config_manager.get_parameter("plugin1", f"param_{i}")
            assert value == i
