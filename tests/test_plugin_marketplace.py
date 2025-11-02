# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""Tests for plugin marketplace registry.

Tests for plugin discovery, metadata management, and marketplace functionality.
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime

import pytest

from plugin_marketplace_registry import (
    PluginMetadata,
    PluginRegistry,
    PluginRating,
    PluginStatus,
    PluginType,
)


class TestPluginMetadata:
    """Test plugin metadata."""

    def test_create_metadata(self):
        """Test creating plugin metadata."""
        metadata = PluginMetadata(
            name="Test Plugin",
            package_name="test-plugin",
            version="1.0.0",
            plugin_type=PluginType.EFFECT,
            author="Test Author",
            author_email="test@example.com",
            description="Test plugin description",
        )

        assert metadata.name == "Test Plugin"
        assert metadata.package_name == "test-plugin"
        assert metadata.plugin_type == PluginType.EFFECT

    def test_metadata_to_dict(self):
        """Test converting metadata to dict."""
        metadata = PluginMetadata(
            name="Test",
            package_name="test",
            version="1.0.0",
            plugin_type=PluginType.EFFECT,
            author="Author",
            author_email="author@example.com",
            description="Test",
        )

        data = metadata.to_dict()
        assert isinstance(data, dict)
        assert data["name"] == "Test"
        assert data["plugin_type"] == "effect"

    def test_metadata_from_dict(self):
        """Test creating metadata from dict."""
        data = {
            "name": "Test Plugin",
            "package_name": "test-plugin",
            "version": "1.0.0",
            "plugin_type": "effect",
            "author": "Author",
            "author_email": "author@example.com",
            "description": "Test description",
            "status": "active",
        }

        metadata = PluginMetadata.from_dict(data)
        assert metadata.name == "Test Plugin"
        assert metadata.plugin_type == PluginType.EFFECT
        assert metadata.status == PluginStatus.ACTIVE

    def test_validate_metadata_valid(self):
        """Test validating valid metadata."""
        metadata = PluginMetadata(
            name="Valid Plugin",
            package_name="valid-plugin",
            version="1.0.0",
            plugin_type=PluginType.EFFECT,
            author="Author",
            author_email="author@example.com",
            description="Valid description",
        )

        is_valid, errors = metadata.validate()
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_metadata_invalid(self):
        """Test validating invalid metadata."""
        metadata = PluginMetadata(
            name="",
            package_name="",
            version="1.0.0",
            plugin_type=PluginType.EFFECT,
            author="",
            author_email="invalid-email",
            description="",
        )

        is_valid, errors = metadata.validate()
        assert is_valid is False
        assert len(errors) > 0

    def test_metadata_rating_bounds(self):
        """Test rating validation."""
        metadata = PluginMetadata(
            name="Test",
            package_name="test",
            version="1.0.0",
            plugin_type=PluginType.EFFECT,
            author="Author",
            author_email="author@example.com",
            description="Test",
            ratings=6.0,
        )

        is_valid, errors = metadata.validate()
        assert is_valid is False
        assert any("ratings" in error for error in errors)


class TestPluginRegistry:
    """Test plugin registry."""

    def test_registry_creation(self, temp_dir: Path):
        """Test creating registry."""
        registry_file = temp_dir / "registry.json"
        registry = PluginRegistry(registry_file)

        assert isinstance(registry.plugins, dict)
        assert len(registry.plugins) == 0

    def test_register_plugin(self, temp_dir: Path):
        """Test registering plugin."""
        registry = PluginRegistry(temp_dir / "registry.json")

        metadata = PluginMetadata(
            name="Test Plugin",
            package_name="test-plugin",
            version="1.0.0",
            plugin_type=PluginType.EFFECT,
            author="Author",
            author_email="author@example.com",
            description="Test description",
        )

        result = registry.register_plugin(metadata)
        assert result is True
        assert "test-plugin" in registry.plugins

    def test_unregister_plugin(self, temp_dir: Path):
        """Test unregistering plugin."""
        registry = PluginRegistry(temp_dir / "registry.json")

        metadata = PluginMetadata(
            name="Test",
            package_name="test",
            version="1.0.0",
            plugin_type=PluginType.EFFECT,
            author="Author",
            author_email="author@example.com",
            description="Test",
        )

        registry.register_plugin(metadata)
        assert "test" in registry.plugins

        registry.unregister_plugin("test")
        assert "test" not in registry.plugins

    def test_get_plugin(self, temp_dir: Path):
        """Test getting plugin."""
        registry = PluginRegistry(temp_dir / "registry.json")

        metadata = PluginMetadata(
            name="Test",
            package_name="test",
            version="1.0.0",
            plugin_type=PluginType.EFFECT,
            author="Author",
            author_email="author@example.com",
            description="Test",
        )

        registry.register_plugin(metadata)
        retrieved = registry.get_plugin("test")

        assert retrieved is not None
        assert retrieved.name == "Test"

    def test_get_nonexistent_plugin(self, temp_dir: Path):
        """Test getting nonexistent plugin."""
        registry = PluginRegistry(temp_dir / "registry.json")
        plugin = registry.get_plugin("nonexistent")

        assert plugin is None

    def test_search_plugins_by_query(self, temp_dir: Path):
        """Test searching plugins by query."""
        registry = PluginRegistry(temp_dir / "registry.json")

        plugin1 = PluginMetadata(
            name="Echo Effect",
            package_name="echo-effect",
            version="1.0.0",
            plugin_type=PluginType.EFFECT,
            author="Author",
            author_email="author@example.com",
            description="Echo audio processing",
        )

        plugin2 = PluginMetadata(
            name="Reverb Effect",
            package_name="reverb-effect",
            version="1.0.0",
            plugin_type=PluginType.EFFECT,
            author="Author",
            author_email="author@example.com",
            description="Reverb audio processing",
        )

        registry.register_plugin(plugin1)
        registry.register_plugin(plugin2)

        results = registry.search_plugins(query="echo")
        assert len(results) == 1
        assert results[0].name == "Echo Effect"

    def test_search_plugins_by_type(self, temp_dir: Path):
        """Test searching plugins by type."""
        registry = PluginRegistry(temp_dir / "registry.json")

        effect = PluginMetadata(
            name="Test Effect",
            package_name="test-effect",
            version="1.0.0",
            plugin_type=PluginType.EFFECT,
            author="Author",
            author_email="author@example.com",
            description="Test effect",
        )

        controller = PluginMetadata(
            name="Test Controller",
            package_name="test-controller",
            version="1.0.0",
            plugin_type=PluginType.CONTROLLER,
            author="Author",
            author_email="author@example.com",
            description="Test controller",
        )

        registry.register_plugin(effect)
        registry.register_plugin(controller)

        effects = registry.search_plugins(plugin_type=PluginType.EFFECT)
        assert len(effects) == 1
        assert effects[0].plugin_type == PluginType.EFFECT

    def test_search_plugins_by_category(self, temp_dir: Path):
        """Test searching plugins by category."""
        registry = PluginRegistry(temp_dir / "registry.json")

        metadata = PluginMetadata(
            name="Test",
            package_name="test",
            version="1.0.0",
            plugin_type=PluginType.EFFECT,
            author="Author",
            author_email="author@example.com",
            description="Test",
            categories=["Utility", "Filter"],
        )

        registry.register_plugin(metadata)

        results = registry.search_plugins(category="Utility")
        assert len(results) == 1

    def test_search_plugins_by_rating(self, temp_dir: Path):
        """Test searching plugins by minimum rating."""
        registry = PluginRegistry(temp_dir / "registry.json")

        metadata1 = PluginMetadata(
            name="High Rated",
            package_name="high-rated",
            version="1.0.0",
            plugin_type=PluginType.EFFECT,
            author="Author",
            author_email="author@example.com",
            description="High rated plugin",
            ratings=4.5,
        )

        metadata2 = PluginMetadata(
            name="Low Rated",
            package_name="low-rated",
            version="1.0.0",
            plugin_type=PluginType.EFFECT,
            author="Author",
            author_email="author@example.com",
            description="Low rated plugin",
            ratings=2.0,
        )

        registry.register_plugin(metadata1)
        registry.register_plugin(metadata2)

        results = registry.search_plugins(min_rating=3.0)
        assert len(results) == 1
        assert results[0].ratings >= 3.0

    def test_add_rating(self, temp_dir: Path):
        """Test adding user rating."""
        registry = PluginRegistry(temp_dir / "registry.json")

        metadata = PluginMetadata(
            name="Test",
            package_name="test",
            version="1.0.0",
            plugin_type=PluginType.EFFECT,
            author="Author",
            author_email="author@example.com",
            description="Test",
        )

        registry.register_plugin(metadata)

        rating = PluginRating(
            plugin_name="test",
            username="user1",
            rating=5.0,
            review_text="Great plugin!",
        )

        result = registry.add_rating("test", rating)
        assert result is True
        assert len(registry.get_ratings("test")) == 1
        assert registry.plugins["test"].reviews_count == 1

    def test_get_statistics(self, temp_dir: Path):
        """Test getting marketplace statistics."""
        registry = PluginRegistry(temp_dir / "registry.json")

        for i in range(3):
            metadata = PluginMetadata(
                name=f"Plugin {i}",
                package_name=f"plugin-{i}",
                version="1.0.0",
                plugin_type=PluginType.EFFECT if i % 2 == 0 else PluginType.CONTROLLER,
                author="Author",
                author_email="author@example.com",
                description="Test plugin",
                downloads=100 * (i + 1),
            )
            registry.register_plugin(metadata)

        stats = registry.get_statistics()
        assert stats["total_plugins"] == 3
        assert stats["total_downloads"] > 0
        assert "plugins_by_type" in stats

    def test_get_trending_plugins(self, temp_dir: Path):
        """Test getting trending plugins."""
        registry = PluginRegistry(temp_dir / "registry.json")

        for i in range(5):
            metadata = PluginMetadata(
                name=f"Plugin {i}",
                package_name=f"plugin-{i}",
                version="1.0.0",
                plugin_type=PluginType.EFFECT,
                author="Author",
                author_email="author@example.com",
                description="Test plugin",
                downloads=100 * (i + 1),
                ratings=4.0 + (0.2 * i),
            )
            registry.register_plugin(metadata)

        trending = registry.get_trending_plugins(limit=3)
        assert len(trending) == 3
        # Should be sorted by downloads and rating
        assert trending[0].downloads >= trending[1].downloads


class TestPluginRating:
    """Test plugin rating."""

    def test_create_rating(self):
        """Test creating rating."""
        rating = PluginRating(
            plugin_name="test-plugin",
            username="user1",
            rating=4.5,
            review_text="Great plugin!",
        )

        assert rating.plugin_name == "test-plugin"
        assert rating.rating == 4.5
        assert rating.username == "user1"

    def test_rating_to_dict(self):
        """Test converting rating to dict."""
        rating = PluginRating(
            plugin_name="test",
            username="user",
            rating=5.0,
            review_text="Great!",
        )

        data = rating.to_dict()
        assert isinstance(data, dict)
        assert data["rating"] == 5.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
