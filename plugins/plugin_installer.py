# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Plugin Installer and Package Manager for Acro DJ Mixer

Handles:
- Plugin installation and updates
- Dependency resolution
- Version management
- Plugin validation
- Installation verification
"""

import json
import shutil
import hashlib
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from packaging import version
import logging

logger = logging.getLogger(__name__)


class PluginDependency:
    """Represents a plugin dependency."""

    def __init__(self, name: str, version_spec: str = ""):
        """Initialize dependency.

        Args:
            name: Package name
            version_spec: Version specifier (e.g., ">=1.0,<2.0")
        """
        self.name = name
        self.version_spec = version_spec or "*"

    def __str__(self) -> str:
        """String representation."""
        if self.version_spec and self.version_spec != "*":
            return f"{self.name}{self.version_spec}"
        return self.name

    def is_satisfied(self, installed_version: str) -> bool:
        """Check if dependency is satisfied.

        Args:
            installed_version: Installed version string

        Returns:
            True if requirement is met
        """
        if self.version_spec == "*":
            return True

        # Simple version comparison
        try:
            inst_ver = version.parse(installed_version)

            if ">=" in self.version_spec:
                min_ver = version.parse(self.version_spec.split(">=")[1])
                return inst_ver >= min_ver

            if "<=" in self.version_spec:
                max_ver = version.parse(self.version_spec.split("<=")[1])
                return inst_ver <= max_ver

            if "==" in self.version_spec:
                req_ver = version.parse(self.version_spec.split("==")[1])
                return inst_ver == req_ver

            return True

        except Exception as e:
            logger.warning(f"Failed to parse version: {e}")
            return True


class PluginPackage:
    """Represents a packaged plugin."""

    def __init__(
        self,
        plugin_id: str,
        name: str,
        version: str,
        author: str,
        entry_point: str,
        dependencies: List[str] = None,
    ):
        """Initialize plugin package.

        Args:
            plugin_id: Unique plugin identifier
            name: Human-readable plugin name
            version: Semantic version
            author: Plugin author
            entry_point: Module path to create_plugin function
            dependencies: List of dependencies
        """
        self.plugin_id = plugin_id
        self.name = name
        self.version = version
        self.author = author
        self.entry_point = entry_point
        self.dependencies = dependencies or []

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'plugin_id': self.plugin_id,
            'name': self.name,
            'version': self.version,
            'author': self.author,
            'entry_point': self.entry_point,
            'dependencies': self.dependencies,
        }


class PluginInstaller:
    """Manages plugin installation and updates."""

    def __init__(self, plugins_dir: str, cache_dir: str = None):
        """Initialize installer.

        Args:
            plugins_dir: Directory where plugins are installed
            cache_dir: Optional cache directory for downloads
        """
        self.plugins_dir = Path(plugins_dir)
        self.cache_dir = Path(cache_dir) if cache_dir else self.plugins_dir / ".cache"
        self.installed_plugins: Dict[str, PluginPackage] = {}

        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._load_installed_plugins()

    def _load_installed_plugins(self) -> None:
        """Load list of installed plugins."""
        manifest_path = self.plugins_dir / "manifest.json"

        if not manifest_path.exists():
            return

        try:
            with open(manifest_path, 'r') as f:
                data = json.load(f)

            for plugin_data in data.get('plugins', []):
                plugin = PluginPackage(**plugin_data)
                self.installed_plugins[plugin.plugin_id] = plugin

            logger.info(f"Loaded {len(self.installed_plugins)} installed plugins")

        except Exception as e:
            logger.warning(f"Failed to load manifest: {e}")

    def _save_manifest(self) -> None:
        """Save installed plugins manifest."""
        manifest_path = self.plugins_dir / "manifest.json"

        data = {
            'version': '1.0',
            'plugins': [
                p.to_dict() for p in self.installed_plugins.values()
            ]
        }

        try:
            with open(manifest_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save manifest: {e}")

    def check_dependencies(self, plugin: PluginPackage) -> Tuple[bool, List[str]]:
        """Check if plugin dependencies are satisfied.

        Args:
            plugin: Plugin package to check

        Returns:
            (all_satisfied, list_of_missing_packages)
        """
        missing = []

        for dep_str in plugin.dependencies:
            # Parse dependency string
            if ">=" in dep_str:
                name, version_spec = dep_str.split(">=", 1)
                dep = PluginDependency(name.strip(), f">={version_spec.strip()}")
            elif "<=" in dep_str:
                name, version_spec = dep_str.split("<=", 1)
                dep = PluginDependency(name.strip(), f"<={version_spec.strip()}")
            elif "==" in dep_str:
                name, version_spec = dep_str.split("==", 1)
                dep = PluginDependency(name.strip(), f"=={version_spec.strip()}")
            else:
                dep = PluginDependency(dep_str.strip())

            # Check if installed
            try:
                import importlib
                installed = importlib.import_module(dep.name)
                installed_version = getattr(installed, '__version__', '0.0.0')

                if not dep.is_satisfied(installed_version):
                    missing.append(str(dep))
            except ImportError:
                missing.append(str(dep))

        return len(missing) == 0, missing

    def validate_package(self, package_path: str) -> Tuple[bool, str]:
        """Validate a plugin package file.

        Args:
            package_path: Path to plugin package file

        Returns:
            (is_valid, error_message)
        """
        package_file = Path(package_path)

        if not package_file.exists():
            return False, f"Package file not found: {package_path}"

        if not package_file.suffix == '.zip':
            return False, "Package must be a .zip file"

        try:
            import zipfile
            with zipfile.ZipFile(package_file, 'r') as z:
                # Check for manifest
                if 'plugin.json' not in z.namelist():
                    return False, "Missing plugin.json manifest"

                # Check for entry point module
                manifest_text = z.read('plugin.json').decode('utf-8')
                manifest = json.loads(manifest_text)

                entry_point = manifest.get('entry_point', '')
                if not entry_point:
                    return False, "Missing entry_point in manifest"

            return True, ""

        except Exception as e:
            return False, f"Invalid package: {str(e)}"

    def install_plugin(
        self,
        package_path: str,
        force: bool = False,
    ) -> Tuple[bool, str]:
        """Install a plugin package.

        Args:
            package_path: Path to plugin package file
            force: Force installation even if already installed

        Returns:
            (success, message)
        """
        package_file = Path(package_path)

        # Validate package
        is_valid, error = self.validate_package(package_path)
        if not is_valid:
            return False, error

        try:
            import zipfile

            with zipfile.ZipFile(package_file, 'r') as z:
                manifest_text = z.read('plugin.json').decode('utf-8')
                manifest = json.loads(manifest_text)

                plugin = PluginPackage(**manifest)

                # Check if already installed
                if plugin.plugin_id in self.installed_plugins and not force:
                    installed = self.installed_plugins[plugin.plugin_id]
                    if version.parse(plugin.version) <= version.parse(installed.version):
                        return False, f"Plugin already installed (v{installed.version})"

                # Check dependencies
                satisfied, missing = self.check_dependencies(plugin)
                if not satisfied:
                    return False, f"Missing dependencies: {', '.join(missing)}"

                # Extract plugin
                plugin_dir = self.plugins_dir / plugin.plugin_id
                plugin_dir.mkdir(parents=True, exist_ok=True)

                z.extractall(plugin_dir)

                # Register installation
                self.installed_plugins[plugin.plugin_id] = plugin
                self._save_manifest()

                logger.info(f"Installed plugin: {plugin.name} v{plugin.version}")

                return True, f"Installed {plugin.name} v{plugin.version}"

        except Exception as e:
            logger.error(f"Installation failed: {e}")
            return False, f"Installation failed: {str(e)}"

    def uninstall_plugin(self, plugin_id: str) -> Tuple[bool, str]:
        """Uninstall a plugin.

        Args:
            plugin_id: Plugin identifier

        Returns:
            (success, message)
        """
        if plugin_id not in self.installed_plugins:
            return False, f"Plugin not installed: {plugin_id}"

        try:
            plugin_dir = self.plugins_dir / plugin_id
            if plugin_dir.exists():
                shutil.rmtree(plugin_dir)

            del self.installed_plugins[plugin_id]
            self._save_manifest()

            logger.info(f"Uninstalled plugin: {plugin_id}")

            return True, f"Uninstalled {plugin_id}"

        except Exception as e:
            logger.error(f"Uninstall failed: {e}")
            return False, f"Uninstall failed: {str(e)}"

    def update_plugin(self, plugin_id: str, new_package_path: str) -> Tuple[bool, str]:
        """Update an installed plugin.

        Args:
            plugin_id: Plugin identifier
            new_package_path: Path to new plugin package

        Returns:
            (success, message)
        """
        if plugin_id not in self.installed_plugins:
            return False, f"Plugin not installed: {plugin_id}"

        # Install new version with force
        return self.install_plugin(new_package_path, force=True)

    def list_installed_plugins(self) -> List[PluginPackage]:
        """Get list of installed plugins.

        Returns:
            List of PluginPackage objects
        """
        return list(self.installed_plugins.values())

    def get_plugin_info(self, plugin_id: str) -> Optional[PluginPackage]:
        """Get info about an installed plugin.

        Args:
            plugin_id: Plugin identifier

        Returns:
            PluginPackage or None
        """
        return self.installed_plugins.get(plugin_id)

    def calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of a file.

        Args:
            file_path: Path to file

        Returns:
            Hex digest of file hash
        """
        sha256_hash = hashlib.sha256()

        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

        return sha256_hash.hexdigest()

    def verify_plugin_integrity(
        self,
        package_path: str,
        expected_hash: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Verify plugin package integrity.

        Args:
            package_path: Path to plugin package
            expected_hash: Optional expected SHA256 hash

        Returns:
            (is_valid, message)
        """
        try:
            import zipfile

            # Check ZIP integrity
            with zipfile.ZipFile(package_path, 'r') as z:
                bad_file = z.testzip()
                if bad_file:
                    return False, f"Corrupted file in package: {bad_file}"

            # Check hash if provided
            if expected_hash:
                actual_hash = self.calculate_file_hash(package_path)
                if actual_hash.lower() != expected_hash.lower():
                    return False, "Hash mismatch - package may be corrupted"

            return True, "Package integrity verified"

        except Exception as e:
            return False, f"Verification failed: {str(e)}"

    def get_plugin_stats(self) -> dict:
        """Get installation statistics.

        Returns:
            Dictionary with installation stats
        """
        total_size = 0
        for plugin_dir in self.plugins_dir.glob("*"):
            if plugin_dir.is_dir():
                for file in plugin_dir.rglob("*"):
                    if file.is_file():
                        total_size += file.stat().st_size

        return {
            'installed_plugins': len(self.installed_plugins),
            'total_size_mb': total_size / (1024 * 1024),
            'cache_size_mb': sum(f.stat().st_size for f in self.cache_dir.rglob("*") if f.is_file()) / (1024 * 1024),
        }
