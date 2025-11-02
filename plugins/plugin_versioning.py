# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Plugin Versioning and Auto-Update System for Acro DJ Mixer

Provides:
- Semantic version comparison and management
- Dependency resolution and version compatibility
- Update checking and installation
- Version migration and compatibility layers
- Rollback and recovery mechanisms
- Update progress tracking and logging
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class UpdateStrategy(Enum):
    """Strategy for handling plugin updates."""
    MANUAL = "manual"          # User must manually approve updates
    MINOR_AUTO = "minor_auto"  # Auto-update minor/patch versions
    AUTO = "auto"              # Auto-update all versions


@dataclass
class SemanticVersion:
    """Semantic version representation (major.minor.patch)."""
    major: int
    minor: int
    patch: int
    prerelease: str = ""        # alpha, beta, rc, etc.
    build: str = ""             # Build metadata

    def __str__(self) -> str:
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build:
            version += f"+{self.build}"
        return version

    def __eq__(self, other: 'SemanticVersion') -> bool:
        return (self.major == other.major and
                self.minor == other.minor and
                self.patch == other.patch and
                self.prerelease == other.prerelease)

    def __lt__(self, other: 'SemanticVersion') -> bool:
        if self.major != other.major:
            return self.major < other.major
        if self.minor != other.minor:
            return self.minor < other.minor
        if self.patch != other.patch:
            return self.patch < other.patch
        # Prerelease versions are lower than release versions
        if self.prerelease and not other.prerelease:
            return True
        if not self.prerelease and other.prerelease:
            return False
        return self.prerelease < other.prerelease

    def __le__(self, other: 'SemanticVersion') -> bool:
        return self == other or self < other

    def __gt__(self, other: 'SemanticVersion') -> bool:
        return not self <= other

    def __ge__(self, other: 'SemanticVersion') -> bool:
        return not self < other

    @staticmethod
    def parse(version_string: str) -> 'SemanticVersion':
        """Parse version string to SemanticVersion.

        Args:
            version_string: Version string (e.g., "1.2.3", "2.0.0-beta.1")

        Returns:
            SemanticVersion object
        """
        # Remove 'v' prefix if present
        version_string = version_string.lstrip('v')

        # Parse build metadata
        build = ""
        if '+' in version_string:
            version_string, build = version_string.split('+', 1)

        # Parse prerelease
        prerelease = ""
        if '-' in version_string:
            version_string, prerelease = version_string.split('-', 1)

        # Parse major.minor.patch
        parts = version_string.split('.')
        try:
            major = int(parts[0]) if len(parts) > 0 else 0
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0
        except (ValueError, IndexError):
            raise ValueError(f"Invalid version format: {version_string}")

        return SemanticVersion(
            major=major,
            minor=minor,
            patch=patch,
            prerelease=prerelease,
            build=build
        )

    @staticmethod
    def from_string(version_string: str) -> 'SemanticVersion':
        """Alias for parse()."""
        return SemanticVersion.parse(version_string)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class VersionConstraint:
    """Version constraint specification (e.g., ">=1.0.0 <2.0.0")."""
    min_version: Optional[SemanticVersion] = None
    max_version: Optional[SemanticVersion] = None
    exclude_versions: List[SemanticVersion] = field(default_factory=list)

    def matches(self, version: SemanticVersion) -> bool:
        """Check if version matches constraint.

        Args:
            version: Version to check

        Returns:
            True if version matches constraint
        """
        if self.min_version and version < self.min_version:
            return False
        if self.max_version and version > self.max_version:
            return False
        if version in self.exclude_versions:
            return False
        return True

    @staticmethod
    def parse(constraint_string: str) -> 'VersionConstraint':
        """Parse constraint string (e.g., ">=1.0.0 <2.0.0").

        Args:
            constraint_string: Constraint specification

        Returns:
            VersionConstraint object
        """
        min_version = None
        max_version = None
        exclude_versions = []

        # Split on whitespace
        parts = constraint_string.split()

        for i in range(0, len(parts), 2):
            if i + 1 >= len(parts):
                break

            operator = parts[i]
            version_str = parts[i + 1]
            version = SemanticVersion.parse(version_str)

            if operator == ">=" or operator == ">=":
                min_version = version
            elif operator == ">" or operator == ">":
                min_version = SemanticVersion(
                    version.major,
                    version.minor,
                    version.patch + 1
                )
            elif operator == "<=" or operator == "<=":
                max_version = version
            elif operator == "<" or operator == "<":
                max_version = SemanticVersion(
                    version.major,
                    version.minor,
                    max(0, version.patch - 1)
                )
            elif operator == "!=" or operator == "!=":
                exclude_versions.append(version)

        return VersionConstraint(
            min_version=min_version,
            max_version=max_version,
            exclude_versions=exclude_versions
        )


@dataclass
class PluginDependency:
    """Plugin dependency specification."""
    plugin_id: str
    version_constraint: VersionConstraint
    optional: bool = False
    description: str = ""

    def to_dict(self) -> dict:
        return {
            'plugin_id': self.plugin_id,
            'version_constraint': str(self.version_constraint),
            'optional': self.optional,
            'description': self.description,
        }


@dataclass
class PluginReleaseInfo:
    """Information about a plugin release."""
    plugin_id: str
    version: SemanticVersion
    release_date: str
    changelog: str
    download_url: str
    file_hash: str = ""
    file_size: int = 0
    dependencies: List[PluginDependency] = field(default_factory=list)
    breaking_changes: List[str] = field(default_factory=list)
    deprecated_features: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'plugin_id': self.plugin_id,
            'version': str(self.version),
            'release_date': self.release_date,
            'changelog': self.changelog,
            'download_url': self.download_url,
            'file_hash': self.file_hash,
            'file_size': self.file_size,
            'dependencies': [d.to_dict() for d in self.dependencies],
            'breaking_changes': self.breaking_changes,
            'deprecated_features': self.deprecated_features,
        }


@dataclass
class UpdateCheckResult:
    """Result of checking for updates."""
    plugin_id: str
    current_version: SemanticVersion
    latest_version: Optional[SemanticVersion] = None
    has_update: bool = False
    is_major_update: bool = False
    is_breaking_change: bool = False
    release_info: Optional[PluginReleaseInfo] = None
    check_time: str = ""

    def to_dict(self) -> dict:
        return {
            'plugin_id': self.plugin_id,
            'current_version': str(self.current_version),
            'latest_version': str(self.latest_version) if self.latest_version else None,
            'has_update': self.has_update,
            'is_major_update': self.is_major_update,
            'is_breaking_change': self.is_breaking_change,
            'check_time': self.check_time,
        }


class PluginVersionManager:
    """Manages plugin versioning, updates, and compatibility."""

    def __init__(self, versions_dir: Optional[str] = None):
        """Initialize version manager.

        Args:
            versions_dir: Directory to store version information
        """
        self.versions_dir = Path(versions_dir) if versions_dir else Path.home() / '.acro' / 'versions'
        self.versions_dir.mkdir(parents=True, exist_ok=True)

        # Installed plugin versions
        self.installed_versions: Dict[str, SemanticVersion] = {}

        # Available releases (from registry/updates)
        self.available_releases: Dict[str, List[PluginReleaseInfo]] = {}

        # Update preferences
        self.update_strategy: Dict[str, UpdateStrategy] = {}

        # Version history (for rollback)
        self.version_history: Dict[str, List[SemanticVersion]] = {}

        self._load_version_info()

    def _load_version_info(self) -> None:
        """Load version information from disk."""
        try:
            versions_file = self.versions_dir / 'versions.json'
            if versions_file.exists():
                with open(versions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for plugin_id, version_str in data.get('installed', {}).items():
                        self.installed_versions[plugin_id] = SemanticVersion.parse(version_str)

                    for plugin_id, history in data.get('history', {}).items():
                        self.version_history[plugin_id] = [
                            SemanticVersion.parse(v) for v in history
                        ]

                logger.info(f"Loaded version info for {len(self.installed_versions)} plugins")
        except Exception as e:
            logger.error(f"Failed to load version info: {e}")

    def _save_version_info(self) -> None:
        """Save version information to disk."""
        try:
            data = {
                'installed': {
                    pid: str(ver) for pid, ver in self.installed_versions.items()
                },
                'history': {
                    pid: [str(v) for v in vers] for pid, vers in self.version_history.items()
                },
                'last_updated': datetime.now().isoformat(),
            }

            versions_file = self.versions_dir / 'versions.json'
            with open(versions_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            logger.debug("Saved version info")
        except Exception as e:
            logger.error(f"Failed to save version info: {e}")

    def register_installed_plugin(
        self,
        plugin_id: str,
        version: str,
        update_strategy: UpdateStrategy = UpdateStrategy.MANUAL
    ) -> None:
        """Register an installed plugin version.

        Args:
            plugin_id: Plugin identifier
            version: Version string
            update_strategy: Strategy for handling updates
        """
        parsed_version = SemanticVersion.parse(version)
        self.installed_versions[plugin_id] = parsed_version
        self.update_strategy[plugin_id] = update_strategy

        # Track version history
        if plugin_id not in self.version_history:
            self.version_history[plugin_id] = []
        self.version_history[plugin_id].append(parsed_version)

        self._save_version_info()
        logger.info(f"Registered {plugin_id} v{version}")

    def get_installed_version(self, plugin_id: str) -> Optional[SemanticVersion]:
        """Get installed version of a plugin.

        Args:
            plugin_id: Plugin identifier

        Returns:
            SemanticVersion or None if not installed
        """
        return self.installed_versions.get(plugin_id)

    def register_available_release(self, release_info: PluginReleaseInfo) -> None:
        """Register an available release.

        Args:
            release_info: PluginReleaseInfo object
        """
        plugin_id = release_info.plugin_id

        if plugin_id not in self.available_releases:
            self.available_releases[plugin_id] = []

        # Check for duplicates
        existing = [r for r in self.available_releases[plugin_id]
                   if r.version == release_info.version]
        if not existing:
            self.available_releases[plugin_id].append(release_info)
            # Keep sorted
            self.available_releases[plugin_id].sort(key=lambda r: r.version)

        logger.info(f"Registered release {plugin_id} v{release_info.version}")

    def check_for_updates(self, plugin_id: str) -> UpdateCheckResult:
        """Check if updates are available for a plugin.

        Args:
            plugin_id: Plugin identifier

        Returns:
            UpdateCheckResult with update information
        """
        current = self.get_installed_version(plugin_id)

        result = UpdateCheckResult(
            plugin_id=plugin_id,
            current_version=current,
            check_time=datetime.now().isoformat()
        )

        if not current:
            logger.warning(f"Plugin {plugin_id} not installed")
            return result

        if plugin_id not in self.available_releases:
            logger.debug(f"No releases available for {plugin_id}")
            return result

        # Find latest compatible release
        releases = self.available_releases[plugin_id]
        latest = releases[-1]

        result.latest_version = latest.version

        if latest.version > current:
            result.has_update = True
            result.release_info = latest

            # Check if major version changed
            if latest.version.major > current.major:
                result.is_major_update = True

            # Check for breaking changes
            if latest.breaking_changes:
                result.is_breaking_change = True

        return result

    def check_dependency_compatibility(
        self,
        plugin_id: str,
        version: SemanticVersion,
        dependencies: List[PluginDependency]
    ) -> Tuple[bool, List[str]]:
        """Check if dependencies are satisfied.

        Args:
            plugin_id: Plugin identifier
            version: Plugin version
            dependencies: List of dependencies

        Returns:
            Tuple of (all_satisfied, list_of_errors)
        """
        errors = []

        for dep in dependencies:
            installed = self.get_installed_version(dep.plugin_id)

            if not installed:
                if dep.optional:
                    logger.info(f"Optional dependency {dep.plugin_id} not found")
                    continue
                errors.append(f"Required dependency {dep.plugin_id} not installed")
                continue

            if not dep.version_constraint.matches(installed):
                msg = f"{dep.plugin_id} version {installed} doesn't match constraint"
                if dep.optional:
                    logger.info(msg)
                else:
                    errors.append(msg)

        return len(errors) == 0, errors

    def get_version_history(self, plugin_id: str) -> List[SemanticVersion]:
        """Get version history for a plugin.

        Args:
            plugin_id: Plugin identifier

        Returns:
            List of SemanticVersion objects in chronological order
        """
        return self.version_history.get(plugin_id, [])

    def can_rollback(self, plugin_id: str) -> bool:
        """Check if plugin can be rolled back.

        Args:
            plugin_id: Plugin identifier

        Returns:
            True if previous versions are available
        """
        history = self.get_version_history(plugin_id)
        return len(history) > 1

    def get_previous_version(self, plugin_id: str) -> Optional[SemanticVersion]:
        """Get previous version for rollback.

        Args:
            plugin_id: Plugin identifier

        Returns:
            Previous SemanticVersion or None
        """
        history = self.get_version_history(plugin_id)
        if len(history) < 2:
            return None
        return history[-2]

    def compare_versions(
        self,
        version1: str,
        version2: str
    ) -> int:
        """Compare two versions.

        Args:
            version1: First version string
            version2: Second version string

        Returns:
            -1 if version1 < version2
             0 if version1 == version2
             1 if version1 > version2
        """
        v1 = SemanticVersion.parse(version1)
        v2 = SemanticVersion.parse(version2)

        if v1 < v2:
            return -1
        elif v1 > v2:
            return 1
        else:
            return 0

    def get_version_difference(
        self,
        version1: str,
        version2: str
    ) -> Dict[str, int]:
        """Get difference between two versions.

        Args:
            version1: First version string
            version2: Second version string

        Returns:
            Dictionary with major, minor, patch differences
        """
        v1 = SemanticVersion.parse(version1)
        v2 = SemanticVersion.parse(version2)

        return {
            'major': v2.major - v1.major,
            'minor': v2.minor - v1.minor,
            'patch': v2.patch - v1.patch,
        }

    def find_compatible_versions(
        self,
        plugin_id: str,
        constraint: str
    ) -> List[SemanticVersion]:
        """Find available versions matching constraint.

        Args:
            plugin_id: Plugin identifier
            constraint: Version constraint string (e.g., ">=1.0.0 <2.0.0")

        Returns:
            List of matching SemanticVersion objects
        """
        vc = VersionConstraint.parse(constraint)

        if plugin_id not in self.available_releases:
            return []

        matching = []
        for release in self.available_releases[plugin_id]:
            if vc.matches(release.version):
                matching.append(release.version)

        return matching

    def get_release_info(
        self,
        plugin_id: str,
        version: str
    ) -> Optional[PluginReleaseInfo]:
        """Get release information.

        Args:
            plugin_id: Plugin identifier
            version: Version string

        Returns:
            PluginReleaseInfo or None
        """
        parsed_version = SemanticVersion.parse(version)

        if plugin_id not in self.available_releases:
            return None

        for release in self.available_releases[plugin_id]:
            if release.version == parsed_version:
                return release

        return None

    def get_changelog_between(
        self,
        plugin_id: str,
        from_version: str,
        to_version: str
    ) -> str:
        """Get consolidated changelog between versions.

        Args:
            plugin_id: Plugin identifier
            from_version: Starting version
            to_version: Ending version

        Returns:
            Consolidated changelog
        """
        from_v = SemanticVersion.parse(from_version)
        to_v = SemanticVersion.parse(to_version)

        if plugin_id not in self.available_releases:
            return ""

        changelog_parts = []

        for release in self.available_releases[plugin_id]:
            if from_v < release.version <= to_v:
                changelog_parts.append(f"## {release.version}")
                changelog_parts.append(release.changelog)
                changelog_parts.append("")

        return "\n".join(changelog_parts)

    def get_breaking_changes_between(
        self,
        plugin_id: str,
        from_version: str,
        to_version: str
    ) -> List[str]:
        """Get breaking changes between versions.

        Args:
            plugin_id: Plugin identifier
            from_version: Starting version
            to_version: Ending version

        Returns:
            List of breaking changes
        """
        from_v = SemanticVersion.parse(from_version)
        to_v = SemanticVersion.parse(to_version)

        if plugin_id not in self.available_releases:
            return []

        breaking_changes = []

        for release in self.available_releases[plugin_id]:
            if from_v < release.version <= to_v:
                breaking_changes.extend(release.breaking_changes)

        return breaking_changes

    def get_version_stats(self) -> dict:
        """Get version management statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            'installed_plugins': len(self.installed_versions),
            'available_releases': sum(
                len(releases) for releases in self.available_releases.values()
            ),
            'total_version_history': sum(
                len(history) for history in self.version_history.values()
            ),
            'plugins_with_updates': sum(
                1 for pid in self.installed_versions
                if self.check_for_updates(pid).has_update
            ),
        }
