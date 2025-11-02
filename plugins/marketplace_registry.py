# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Plugin Marketplace Registry for Acro DJ Mixer v3.x

Provides:
- Central registry of available plugins
- Plugin discovery and search
- Version management
- Rating and review system
- Dependency resolution
- Installation management
"""

import json
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PluginStatus(Enum):
    """Plugin status in marketplace."""
    VERIFIED = "verified"      # Official, tested by Acro team
    COMMUNITY = "community"    # Community-contributed
    BETA = "beta"             # Beta/experimental
    DEPRECATED = "deprecated" # No longer recommended


@dataclass
class PluginReview:
    """A user review of a plugin."""
    reviewer_name: str
    rating: float              # 1-5 stars
    comment: str
    date: str
    helpful_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PluginVersion:
    """A version of a plugin."""
    version: str               # Semantic version (e.g., "1.0.0")
    release_date: str
    changelog: str
    download_url: str
    file_hash: str             # SHA256 hash
    file_size_bytes: int
    python_version_min: str = "3.8"
    python_version_max: str = "3.12"
    dependencies: List[str] = field(default_factory=list)
    downloads: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PluginListing:
    """Complete plugin listing in marketplace."""
    plugin_id: str
    name: str
    author: str
    description: str
    long_description: str
    category: str
    status: PluginStatus
    icon_url: Optional[str] = None
    homepage_url: Optional[str] = None
    repository_url: Optional[str] = None
    license: str = "MIT"
    version: str = "1.0.0"       # Current version
    rating: float = 0.0          # 0-5 stars (average)
    rating_count: int = 0        # Number of ratings
    download_count: int = 0      # Total downloads
    last_updated: str = ""
    verified_by: Optional[str] = None  # Acro team member if verified
    versions: List[PluginVersion] = field(default_factory=list)
    reviews: List[PluginReview] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        data = {k: v for k, v in asdict(self).items() if k != 'status'}
        data['status'] = self.status.value
        data['versions'] = [v.to_dict() for v in self.versions]
        data['reviews'] = [r.to_dict() for r in self.reviews]
        return data

    def get_current_version(self) -> Optional[PluginVersion]:
        """Get current version object."""
        for v in self.versions:
            if v.version == self.version:
                return v
        return None if not self.versions else self.versions[-1]

    def get_average_rating(self) -> float:
        """Calculate average rating."""
        if not self.reviews:
            return 0.0
        total = sum(r.rating for r in self.reviews)
        return total / len(self.reviews)

    def add_review(self, review: PluginReview) -> None:
        """Add a user review."""
        self.reviews.append(review)
        self.rating = self.get_average_rating()
        self.rating_count = len(self.reviews)


class PluginMarketplaceRegistry:
    """Central registry for plugins in marketplace."""

    def __init__(self, registry_path: Optional[str] = None):
        """Initialize registry.

        Args:
            registry_path: Path to registry JSON file
        """
        self.registry_path = Path(registry_path) if registry_path else Path('plugin_registry.json')
        self.plugins: Dict[str, PluginListing] = {}
        self._load_registry()

    def _load_registry(self) -> None:
        """Load registry from file."""
        if not self.registry_path.exists():
            logger.info("Creating new plugin registry")
            return

        try:
            with open(self.registry_path, 'r') as f:
                data = json.load(f)

            for plugin_data in data.get('plugins', []):
                plugin = self._dict_to_listing(plugin_data)
                self.plugins[plugin.plugin_id] = plugin

            logger.info(f"Loaded {len(self.plugins)} plugins from registry")

        except Exception as e:
            logger.error(f"Failed to load registry: {e}")

    def _dict_to_listing(self, data: dict) -> PluginListing:
        """Convert dict to PluginListing."""
        versions = [
            PluginVersion(**v) for v in data.get('versions', [])
        ]
        reviews = [
            PluginReview(**r) for r in data.get('reviews', [])
        ]

        return PluginListing(
            plugin_id=data['plugin_id'],
            name=data['name'],
            author=data['author'],
            description=data['description'],
            long_description=data.get('long_description', ''),
            category=data['category'],
            status=PluginStatus(data.get('status', 'community')),
            icon_url=data.get('icon_url'),
            homepage_url=data.get('homepage_url'),
            repository_url=data.get('repository_url'),
            license=data.get('license', 'MIT'),
            version=data.get('version', '1.0.0'),
            rating=data.get('rating', 0.0),
            rating_count=data.get('rating_count', 0),
            download_count=data.get('download_count', 0),
            last_updated=data.get('last_updated', ''),
            verified_by=data.get('verified_by'),
            versions=versions,
            reviews=reviews,
            tags=data.get('tags', []),
        )

    def save_registry(self) -> None:
        """Save registry to file."""
        try:
            data = {
                'version': '1.0',
                'last_updated': datetime.now().isoformat(),
                'plugin_count': len(self.plugins),
                'plugins': [
                    plugin.to_dict() for plugin in self.plugins.values()
                ]
            }

            with open(self.registry_path, 'w') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Saved registry with {len(self.plugins)} plugins")

        except Exception as e:
            logger.error(f"Failed to save registry: {e}")

    def register_plugin(self, listing: PluginListing) -> None:
        """Register a plugin in marketplace.

        Args:
            listing: PluginListing object
        """
        if listing.plugin_id in self.plugins:
            logger.warning(f"Plugin '{listing.plugin_id}' already registered")
            return

        listing.last_updated = datetime.now().isoformat()
        self.plugins[listing.plugin_id] = listing
        self.save_registry()

        logger.info(f"Registered plugin: {listing.name} v{listing.version}")

    def update_plugin(self, plugin_id: str, listing: PluginListing) -> None:
        """Update plugin listing.

        Args:
            plugin_id: Plugin ID
            listing: Updated PluginListing
        """
        if plugin_id not in self.plugins:
            logger.warning(f"Plugin '{plugin_id}' not found")
            return

        listing.last_updated = datetime.now().isoformat()
        self.plugins[plugin_id] = listing
        self.save_registry()

    def unregister_plugin(self, plugin_id: str) -> None:
        """Remove plugin from registry.

        Args:
            plugin_id: Plugin ID
        """
        if plugin_id in self.plugins:
            del self.plugins[plugin_id]
            self.save_registry()
            logger.info(f"Unregistered plugin: {plugin_id}")

    def get_plugin(self, plugin_id: str) -> Optional[PluginListing]:
        """Get plugin listing by ID.

        Args:
            plugin_id: Plugin ID

        Returns:
            PluginListing or None
        """
        return self.plugins.get(plugin_id)

    def search_plugins(
        self,
        query: str = "",
        category: Optional[str] = None,
        status: Optional[PluginStatus] = None,
        min_rating: float = 0.0
    ) -> List[PluginListing]:
        """Search plugins by criteria.

        Args:
            query: Search query (name, description, tags)
            category: Filter by category
            status: Filter by status
            min_rating: Minimum rating (0-5)

        Returns:
            List of matching PluginListings
        """
        query_lower = query.lower()
        results = []

        for plugin in self.plugins.values():
            # Category filter
            if category and plugin.category != category:
                continue

            # Status filter
            if status and plugin.status != status:
                continue

            # Rating filter
            if plugin.rating < min_rating:
                continue

            # Text search
            if query:
                if not (query_lower in plugin.name.lower() or
                        query_lower in plugin.description.lower() or
                        any(query_lower in tag.lower() for tag in plugin.tags)):
                    continue

            results.append(plugin)

        # Sort by rating (descending)
        results.sort(key=lambda p: p.rating, reverse=True)

        return results

    def get_plugins_by_category(self, category: str) -> List[PluginListing]:
        """Get all plugins in a category.

        Args:
            category: Plugin category

        Returns:
            List of PluginListings
        """
        return self.search_plugins(category=category)

    def get_verified_plugins(self) -> List[PluginListing]:
        """Get all verified plugins.

        Returns:
            List of verified PluginListings
        """
        return self.search_plugins(status=PluginStatus.VERIFIED)

    def get_community_plugins(self) -> List[PluginListing]:
        """Get all community plugins.

        Returns:
            List of community PluginListings
        """
        return self.search_plugins(status=PluginStatus.COMMUNITY)

    def get_trending_plugins(self, limit: int = 10) -> List[PluginListing]:
        """Get trending plugins (most downloaded recently).

        Args:
            limit: Number of plugins to return

        Returns:
            List of trending PluginListings
        """
        sorted_plugins = sorted(
            self.plugins.values(),
            key=lambda p: p.download_count,
            reverse=True
        )
        return sorted_plugins[:limit]

    def get_top_rated_plugins(self, limit: int = 10) -> List[PluginListing]:
        """Get top-rated plugins.

        Args:
            limit: Number of plugins to return

        Returns:
            List of top-rated PluginListings
        """
        sorted_plugins = sorted(
            self.plugins.values(),
            key=lambda p: (p.rating, p.rating_count),
            reverse=True
        )
        return sorted_plugins[:limit]

    def add_review(
        self,
        plugin_id: str,
        reviewer_name: str,
        rating: float,
        comment: str
    ) -> bool:
        """Add a review to a plugin.

        Args:
            plugin_id: Plugin ID
            reviewer_name: Name of reviewer
            rating: Rating (1-5)
            comment: Review comment

        Returns:
            True if successful, False otherwise
        """
        if plugin_id not in self.plugins:
            return False

        rating = max(1.0, min(5.0, rating))  # Clamp 1-5

        review = PluginReview(
            reviewer_name=reviewer_name,
            rating=rating,
            comment=comment,
            date=datetime.now().isoformat(),
        )

        self.plugins[plugin_id].add_review(review)
        self.save_registry()

        return True

    def increment_download_count(self, plugin_id: str) -> None:
        """Increment download count for a plugin.

        Args:
            plugin_id: Plugin ID
        """
        if plugin_id in self.plugins:
            self.plugins[plugin_id].download_count += 1
            if self.plugins[plugin_id].versions:
                self.plugins[plugin_id].versions[-1].downloads += 1
            self.save_registry()

    def get_plugin_stats(self) -> dict:
        """Get marketplace statistics.

        Returns:
            Dictionary with statistics
        """
        total_plugins = len(self.plugins)
        verified = sum(1 for p in self.plugins.values() if p.status == PluginStatus.VERIFIED)
        community = sum(1 for p in self.plugins.values() if p.status == PluginStatus.COMMUNITY)
        beta = sum(1 for p in self.plugins.values() if p.status == PluginStatus.BETA)
        total_downloads = sum(p.download_count for p in self.plugins.values())
        avg_rating = (sum(p.rating for p in self.plugins.values()) / total_plugins
                     if total_plugins > 0 else 0.0)

        return {
            'total_plugins': total_plugins,
            'verified_plugins': verified,
            'community_plugins': community,
            'beta_plugins': beta,
            'total_downloads': total_downloads,
            'average_rating': avg_rating,
        }

    def export_catalog(self, export_path: str) -> None:
        """Export plugin catalog to file.

        Args:
            export_path: Path to export file
        """
        data = {
            'catalog_version': '1.0',
            'generated_date': datetime.now().isoformat(),
            'plugins': [
                {
                    'id': pid,
                    'name': p.name,
                    'author': p.author,
                    'category': p.category,
                    'rating': p.rating,
                    'downloads': p.download_count,
                    'url': p.homepage_url,
                    'repository': p.repository_url,
                }
                for pid, p in self.plugins.items()
            ]
        }

        with open(export_path, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Exported catalog to {export_path}")
