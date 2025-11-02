# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Tests for Plugin Versioning and Auto-Update System

Tests cover:
- Semantic version parsing and comparison
- Version constraints and compatibility
- Update checking and availability
- Dependency resolution
- Version history and rollback
- Changelog and breaking changes
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from plugins.plugin_versioning import (
    SemanticVersion,
    VersionConstraint,
    PluginDependency,
    PluginReleaseInfo,
    PluginVersionManager,
    UpdateCheckResult,
    UpdateStrategy,
)


class TestSemanticVersion:
    """Test semantic version parsing and comparison."""

    def test_parse_simple_version(self):
        """Test parsing simple version string."""
        v = SemanticVersion.parse("1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3

    def test_parse_version_with_prerelease(self):
        """Test parsing version with prerelease."""
        v = SemanticVersion.parse("1.2.3-beta.1")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3
        assert v.prerelease == "beta.1"

    def test_parse_version_with_build(self):
        """Test parsing version with build metadata."""
        v = SemanticVersion.parse("1.2.3+build.123")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3
        assert v.build == "build.123"

    def test_parse_version_with_v_prefix(self):
        """Test parsing version with v prefix."""
        v = SemanticVersion.parse("v1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3

    def test_version_string_conversion(self):
        """Test converting version back to string."""
        v = SemanticVersion.parse("1.2.3-beta.1+build.123")
        assert str(v) == "1.2.3-beta.1+build.123"

    def test_version_equality(self):
        """Test version equality comparison."""
        v1 = SemanticVersion.parse("1.2.3")
        v2 = SemanticVersion.parse("1.2.3")
        assert v1 == v2

    def test_version_less_than_major(self):
        """Test version less than comparison (major)."""
        v1 = SemanticVersion.parse("1.0.0")
        v2 = SemanticVersion.parse("2.0.0")
        assert v1 < v2

    def test_version_less_than_minor(self):
        """Test version less than comparison (minor)."""
        v1 = SemanticVersion.parse("1.1.0")
        v2 = SemanticVersion.parse("1.2.0")
        assert v1 < v2

    def test_version_less_than_patch(self):
        """Test version less than comparison (patch)."""
        v1 = SemanticVersion.parse("1.0.1")
        v2 = SemanticVersion.parse("1.0.2")
        assert v1 < v2

    def test_version_prerelease_comparison(self):
        """Test prerelease versions are lower than release."""
        v1 = SemanticVersion.parse("1.0.0-beta")
        v2 = SemanticVersion.parse("1.0.0")
        assert v1 < v2

    def test_version_greater_than(self):
        """Test version greater than comparison."""
        v1 = SemanticVersion.parse("2.0.0")
        v2 = SemanticVersion.parse("1.0.0")
        assert v1 > v2

    def test_version_sorting(self):
        """Test sorting multiple versions."""
        versions = [
            SemanticVersion.parse("2.0.0"),
            SemanticVersion.parse("1.0.0-beta"),
            SemanticVersion.parse("1.0.0"),
            SemanticVersion.parse("1.1.0"),
            SemanticVersion.parse("1.0.1"),
        ]

        sorted_versions = sorted(versions)

        assert str(sorted_versions[0]) == "1.0.0-beta"
        assert str(sorted_versions[1]) == "1.0.0"
        assert str(sorted_versions[2]) == "1.0.1"
        assert str(sorted_versions[3]) == "1.1.0"
        assert str(sorted_versions[4]) == "2.0.0"

    def test_version_from_string_alias(self):
        """Test from_string alias method."""
        v = SemanticVersion.from_string("1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3


class TestVersionConstraint:
    """Test version constraint parsing and matching."""

    def test_constraint_greater_than_or_equal(self):
        """Test >= constraint."""
        c = VersionConstraint.parse(">=1.0.0")
        assert c.matches(SemanticVersion.parse("1.0.0"))
        assert c.matches(SemanticVersion.parse("2.0.0"))
        assert not c.matches(SemanticVersion.parse("0.9.0"))

    def test_constraint_less_than_or_equal(self):
        """Test <= constraint."""
        c = VersionConstraint.parse("<=2.0.0")
        assert c.matches(SemanticVersion.parse("2.0.0"))
        assert c.matches(SemanticVersion.parse("1.0.0"))
        assert not c.matches(SemanticVersion.parse("2.1.0"))

    def test_constraint_range(self):
        """Test range constraint."""
        c = VersionConstraint.parse(">=1.0.0 <2.0.0")
        assert c.matches(SemanticVersion.parse("1.0.0"))
        assert c.matches(SemanticVersion.parse("1.5.0"))
        assert not c.matches(SemanticVersion.parse("2.0.0"))
        assert not c.matches(SemanticVersion.parse("0.9.0"))

    def test_constraint_excluded_version(self):
        """Test excluding specific version."""
        c = VersionConstraint.parse(">=1.0.0 !=1.5.0")
        assert c.matches(SemanticVersion.parse("1.0.0"))
        assert c.matches(SemanticVersion.parse("1.6.0"))
        assert not c.matches(SemanticVersion.parse("1.5.0"))

    def test_constraint_multiple_ranges(self):
        """Test multiple range constraints."""
        c = VersionConstraint.parse(">=1.0.0 <2.0.0 !=1.5.0")
        assert c.matches(SemanticVersion.parse("1.0.0"))
        assert c.matches(SemanticVersion.parse("1.4.0"))
        assert not c.matches(SemanticVersion.parse("1.5.0"))
        assert not c.matches(SemanticVersion.parse("2.0.0"))


class TestPluginVersionManager:
    """Test plugin version management."""

    @pytest.fixture
    def temp_versions_dir(self):
        """Create temporary versions directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def version_manager(self, temp_versions_dir):
        """Create version manager instance."""
        return PluginVersionManager(versions_dir=temp_versions_dir)

    def test_register_installed_plugin(self, version_manager):
        """Test registering installed plugin version."""
        version_manager.register_installed_plugin(
            "test_plugin",
            "1.0.0"
        )

        installed = version_manager.get_installed_version("test_plugin")
        assert installed is not None
        assert str(installed) == "1.0.0"

    def test_get_installed_version_not_found(self, version_manager):
        """Test getting version for non-installed plugin."""
        version = version_manager.get_installed_version("nonexistent")
        assert version is None

    def test_register_available_release(self, version_manager):
        """Test registering available release."""
        release = PluginReleaseInfo(
            plugin_id="test_plugin",
            version=SemanticVersion.parse("2.0.0"),
            release_date=datetime.now().isoformat(),
            changelog="New features",
            download_url="http://example.com/download"
        )

        version_manager.register_available_release(release)

        assert "test_plugin" in version_manager.available_releases
        assert len(version_manager.available_releases["test_plugin"]) == 1

    def test_check_for_updates_available(self, version_manager):
        """Test checking for available updates."""
        # Register installed version
        version_manager.register_installed_plugin("test_plugin", "1.0.0")

        # Register new release
        release = PluginReleaseInfo(
            plugin_id="test_plugin",
            version=SemanticVersion.parse("1.1.0"),
            release_date=datetime.now().isoformat(),
            changelog="Bug fixes",
            download_url="http://example.com/download"
        )
        version_manager.register_available_release(release)

        # Check for updates
        result = version_manager.check_for_updates("test_plugin")

        assert result.has_update
        assert result.latest_version == SemanticVersion.parse("1.1.0")
        assert not result.is_major_update

    def test_check_for_updates_major(self, version_manager):
        """Test detecting major version updates."""
        version_manager.register_installed_plugin("test_plugin", "1.0.0")

        release = PluginReleaseInfo(
            plugin_id="test_plugin",
            version=SemanticVersion.parse("2.0.0"),
            release_date=datetime.now().isoformat(),
            changelog="Major rewrite",
            download_url="http://example.com/download"
        )
        version_manager.register_available_release(release)

        result = version_manager.check_for_updates("test_plugin")

        assert result.has_update
        assert result.is_major_update

    def test_check_for_updates_breaking_changes(self, version_manager):
        """Test detecting breaking changes."""
        version_manager.register_installed_plugin("test_plugin", "1.0.0")

        release = PluginReleaseInfo(
            plugin_id="test_plugin",
            version=SemanticVersion.parse("1.1.0"),
            release_date=datetime.now().isoformat(),
            changelog="API changes",
            download_url="http://example.com/download",
            breaking_changes=["Removed old API method"]
        )
        version_manager.register_available_release(release)

        result = version_manager.check_for_updates("test_plugin")

        assert result.has_update
        assert result.is_breaking_change

    def test_check_for_updates_none_available(self, version_manager):
        """Test when no updates are available."""
        version_manager.register_installed_plugin("test_plugin", "2.0.0")

        release = PluginReleaseInfo(
            plugin_id="test_plugin",
            version=SemanticVersion.parse("1.9.0"),
            release_date=datetime.now().isoformat(),
            changelog="Old version",
            download_url="http://example.com/download"
        )
        version_manager.register_available_release(release)

        result = version_manager.check_for_updates("test_plugin")

        assert not result.has_update

    def test_dependency_compatibility_check_satisfied(self, version_manager):
        """Test dependency compatibility check - all satisfied."""
        version_manager.register_installed_plugin("plugin_a", "1.0.0")
        version_manager.register_installed_plugin("plugin_b", "2.0.0")

        deps = [
            PluginDependency(
                plugin_id="plugin_a",
                version_constraint=VersionConstraint.parse(">=1.0.0")
            ),
            PluginDependency(
                plugin_id="plugin_b",
                version_constraint=VersionConstraint.parse(">=2.0.0")
            ),
        ]

        satisfied, errors = version_manager.check_dependency_compatibility(
            "test_plugin",
            SemanticVersion.parse("1.0.0"),
            deps
        )

        assert satisfied
        assert len(errors) == 0

    def test_dependency_compatibility_check_missing(self, version_manager):
        """Test dependency compatibility check - missing dependency."""
        deps = [
            PluginDependency(
                plugin_id="missing_plugin",
                version_constraint=VersionConstraint.parse(">=1.0.0"),
                optional=False
            ),
        ]

        satisfied, errors = version_manager.check_dependency_compatibility(
            "test_plugin",
            SemanticVersion.parse("1.0.0"),
            deps
        )

        assert not satisfied
        assert len(errors) == 1
        assert "not installed" in errors[0]

    def test_dependency_compatibility_check_optional_missing(self, version_manager):
        """Test optional dependency can be missing."""
        deps = [
            PluginDependency(
                plugin_id="missing_plugin",
                version_constraint=VersionConstraint.parse(">=1.0.0"),
                optional=True
            ),
        ]

        satisfied, errors = version_manager.check_dependency_compatibility(
            "test_plugin",
            SemanticVersion.parse("1.0.0"),
            deps
        )

        assert satisfied
        assert len(errors) == 0

    def test_version_history_tracking(self, version_manager):
        """Test version history is tracked."""
        version_manager.register_installed_plugin("test_plugin", "1.0.0")
        version_manager.register_installed_plugin("test_plugin", "1.1.0")
        version_manager.register_installed_plugin("test_plugin", "1.2.0")

        history = version_manager.get_version_history("test_plugin")

        assert len(history) == 3
        assert str(history[0]) == "1.0.0"
        assert str(history[2]) == "1.2.0"

    def test_can_rollback(self, version_manager):
        """Test checking if rollback is possible."""
        version_manager.register_installed_plugin("test_plugin", "1.0.0")

        assert not version_manager.can_rollback("test_plugin")

        version_manager.register_installed_plugin("test_plugin", "1.1.0")

        assert version_manager.can_rollback("test_plugin")

    def test_get_previous_version(self, version_manager):
        """Test getting previous version for rollback."""
        version_manager.register_installed_plugin("test_plugin", "1.0.0")
        version_manager.register_installed_plugin("test_plugin", "1.1.0")

        previous = version_manager.get_previous_version("test_plugin")

        assert previous is not None
        assert str(previous) == "1.0.0"

    def test_compare_versions(self, version_manager):
        """Test version comparison."""
        assert version_manager.compare_versions("1.0.0", "2.0.0") == -1
        assert version_manager.compare_versions("2.0.0", "1.0.0") == 1
        assert version_manager.compare_versions("1.0.0", "1.0.0") == 0

    def test_get_version_difference(self, version_manager):
        """Test calculating version difference."""
        diff = version_manager.get_version_difference("1.2.3", "2.3.5")

        assert diff['major'] == 1
        assert diff['minor'] == 1
        assert diff['patch'] == 2

    def test_find_compatible_versions(self, version_manager):
        """Test finding compatible versions."""
        version_manager.register_available_release(PluginReleaseInfo(
            plugin_id="test_plugin",
            version=SemanticVersion.parse("1.0.0"),
            release_date=datetime.now().isoformat(),
            changelog="",
            download_url=""
        ))
        version_manager.register_available_release(PluginReleaseInfo(
            plugin_id="test_plugin",
            version=SemanticVersion.parse("1.5.0"),
            release_date=datetime.now().isoformat(),
            changelog="",
            download_url=""
        ))
        version_manager.register_available_release(PluginReleaseInfo(
            plugin_id="test_plugin",
            version=SemanticVersion.parse("2.0.0"),
            release_date=datetime.now().isoformat(),
            changelog="",
            download_url=""
        ))

        compatible = version_manager.find_compatible_versions(
            "test_plugin",
            ">=1.0.0 <2.0.0"
        )

        assert len(compatible) == 2
        assert SemanticVersion.parse("1.0.0") in compatible
        assert SemanticVersion.parse("1.5.0") in compatible

    def test_get_release_info(self, version_manager):
        """Test getting release information."""
        release = PluginReleaseInfo(
            plugin_id="test_plugin",
            version=SemanticVersion.parse("1.0.0"),
            release_date=datetime.now().isoformat(),
            changelog="Initial release",
            download_url="http://example.com/download"
        )

        version_manager.register_available_release(release)

        info = version_manager.get_release_info("test_plugin", "1.0.0")

        assert info is not None
        assert info.changelog == "Initial release"

    def test_get_changelog_between(self, version_manager):
        """Test getting changelog between versions."""
        version_manager.register_available_release(PluginReleaseInfo(
            plugin_id="test_plugin",
            version=SemanticVersion.parse("1.0.0"),
            release_date=datetime.now().isoformat(),
            changelog="Initial release",
            download_url=""
        ))
        version_manager.register_available_release(PluginReleaseInfo(
            plugin_id="test_plugin",
            version=SemanticVersion.parse("1.1.0"),
            release_date=datetime.now().isoformat(),
            changelog="Bug fixes",
            download_url=""
        ))

        changelog = version_manager.get_changelog_between(
            "test_plugin",
            "1.0.0",
            "1.1.0"
        )

        assert "Bug fixes" in changelog
        assert "1.1.0" in changelog

    def test_get_breaking_changes_between(self, version_manager):
        """Test getting breaking changes between versions."""
        version_manager.register_available_release(PluginReleaseInfo(
            plugin_id="test_plugin",
            version=SemanticVersion.parse("1.0.0"),
            release_date=datetime.now().isoformat(),
            changelog="",
            download_url="",
            breaking_changes=[]
        ))
        version_manager.register_available_release(PluginReleaseInfo(
            plugin_id="test_plugin",
            version=SemanticVersion.parse("2.0.0"),
            release_date=datetime.now().isoformat(),
            changelog="",
            download_url="",
            breaking_changes=["Removed API v1", "Changed configuration format"]
        ))

        changes = version_manager.get_breaking_changes_between(
            "test_plugin",
            "1.0.0",
            "2.0.0"
        )

        assert len(changes) == 2
        assert "Removed API v1" in changes

    def test_version_persistence(self, temp_versions_dir):
        """Test version information persists across instances."""
        manager1 = PluginVersionManager(versions_dir=temp_versions_dir)
        manager1.register_installed_plugin("test_plugin", "1.0.0")

        # Create new instance
        manager2 = PluginVersionManager(versions_dir=temp_versions_dir)

        installed = manager2.get_installed_version("test_plugin")
        assert installed is not None
        assert str(installed) == "1.0.0"

    def test_get_version_stats(self, version_manager):
        """Test getting version statistics."""
        version_manager.register_installed_plugin("plugin1", "1.0.0")
        version_manager.register_installed_plugin("plugin2", "2.0.0")

        version_manager.register_available_release(PluginReleaseInfo(
            plugin_id="plugin1",
            version=SemanticVersion.parse("1.1.0"),
            release_date=datetime.now().isoformat(),
            changelog="",
            download_url=""
        ))

        stats = version_manager.get_version_stats()

        assert stats['installed_plugins'] == 2
        assert stats['available_releases'] == 1
