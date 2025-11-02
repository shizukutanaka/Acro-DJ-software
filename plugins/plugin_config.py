# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Plugin Configuration and Preferences Management for Acro DJ Mixer

Provides:
- Plugin-specific configuration storage and retrieval
- Parameter persistence across sessions
- User preference management
- Configuration validation and schema definition
- Profile support for different use cases
- Default configuration generation
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


class ConfigStorageFormat(Enum):
    """Supported configuration storage formats."""
    JSON = "json"
    TOML = "toml"


@dataclass
class ConfigSchema:
    """Defines the schema for plugin configuration."""
    plugin_id: str
    version: str
    parameters: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    defaults: Dict[str, Any] = field(default_factory=dict)
    descriptions: Dict[str, str] = field(default_factory=dict)
    constraints: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ConfigProfile:
    """Represents a saved configuration profile."""
    profile_id: str
    plugin_id: str
    name: str
    description: str = ""
    created_date: str = ""
    modified_date: str = ""
    is_default: bool = False
    parameters: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PresetLibrary:
    """Collection of presets for a plugin."""
    plugin_id: str
    presets: Dict[str, ConfigProfile] = field(default_factory=dict)
    current_profile_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            'plugin_id': self.plugin_id,
            'presets': {pid: p.to_dict() for pid, p in self.presets.items()},
            'current_profile_id': self.current_profile_id,
        }


class PluginConfigManager:
    """Manages plugin configuration, preferences, and profiles."""

    def __init__(
        self,
        config_dir: Optional[str] = None,
        storage_format: ConfigStorageFormat = ConfigStorageFormat.JSON
    ):
        """Initialize configuration manager.

        Args:
            config_dir: Directory to store plugin configurations
            storage_format: Format to use for storing configs (JSON or TOML)
        """
        self.config_dir = Path(config_dir) if config_dir else Path.home() / '.acro' / 'plugins'
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.storage_format = storage_format

        # Plugin schemas and configurations
        self.schemas: Dict[str, ConfigSchema] = {}
        self.configs: Dict[str, Dict[str, Any]] = {}
        self.profiles: Dict[str, PresetLibrary] = {}
        self.preferences: Dict[str, Dict[str, Any]] = {}

        self._load_all_configs()

    def _load_all_configs(self) -> None:
        """Load all configuration files from disk."""
        if not self.config_dir.exists():
            return

        for config_file in self.config_dir.glob('*_config.json'):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    plugin_id = data.get('plugin_id')
                    if plugin_id:
                        self.configs[plugin_id] = data.get('parameters', {})
                        logger.info(f"Loaded config for plugin: {plugin_id}")
            except Exception as e:
                logger.error(f"Failed to load config {config_file}: {e}")

        for profile_file in self.config_dir.glob('*_profiles.json'):
            try:
                with open(profile_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    plugin_id = data.get('plugin_id')
                    if plugin_id:
                        presets = {}
                        for pid, pdata in data.get('presets', {}).items():
                            presets[pid] = ConfigProfile(**pdata)
                        self.profiles[plugin_id] = PresetLibrary(
                            plugin_id=plugin_id,
                            presets=presets,
                            current_profile_id=data.get('current_profile_id')
                        )
                        logger.info(f"Loaded {len(presets)} profiles for plugin: {plugin_id}")
            except Exception as e:
                logger.error(f"Failed to load profiles {profile_file}: {e}")

    def register_schema(self, schema: ConfigSchema) -> None:
        """Register a plugin configuration schema.

        Args:
            schema: ConfigSchema defining plugin parameters
        """
        self.schemas[schema.plugin_id] = schema
        logger.info(f"Registered schema for plugin: {schema.plugin_id}")

    def set_parameter(
        self,
        plugin_id: str,
        param_name: str,
        value: Any
    ) -> Tuple[bool, str]:
        """Set a plugin parameter value.

        Args:
            plugin_id: Plugin identifier
            param_name: Parameter name
            value: Parameter value

        Returns:
            Tuple of (success, message)
        """
        # Validate against schema if available
        if plugin_id in self.schemas:
            schema = self.schemas[plugin_id]

            # Check if parameter exists in schema
            if param_name not in schema.parameters:
                return False, f"Unknown parameter: {param_name}"

            # Validate value against constraints
            constraints = schema.constraints.get(param_name, {})
            if 'type' in constraints:
                expected_type = constraints['type']
                if not isinstance(value, expected_type):
                    return False, f"Invalid type for {param_name}: expected {expected_type.__name__}"

            if 'min' in constraints and value < constraints['min']:
                return False, f"Value {value} below minimum {constraints['min']}"

            if 'max' in constraints and value > constraints['max']:
                return False, f"Value {value} above maximum {constraints['max']}"

            if 'options' in constraints and value not in constraints['options']:
                return False, f"Value not in allowed options: {constraints['options']}"

        # Store parameter
        if plugin_id not in self.configs:
            self.configs[plugin_id] = {}

        self.configs[plugin_id][param_name] = value
        self._save_config(plugin_id)

        return True, f"Parameter {param_name} updated"

    def get_parameter(
        self,
        plugin_id: str,
        param_name: str,
        default: Any = None
    ) -> Any:
        """Get a plugin parameter value.

        Args:
            plugin_id: Plugin identifier
            param_name: Parameter name
            default: Default value if not found

        Returns:
            Parameter value or default
        """
        if plugin_id not in self.configs:
            # Try to get default from schema
            if plugin_id in self.schemas:
                return self.schemas[plugin_id].defaults.get(param_name, default)
            return default

        config = self.configs[plugin_id]
        return config.get(param_name, default)

    def get_all_parameters(self, plugin_id: str) -> Dict[str, Any]:
        """Get all parameters for a plugin.

        Args:
            plugin_id: Plugin identifier

        Returns:
            Dictionary of all parameters
        """
        if plugin_id not in self.configs:
            # Return defaults if available
            if plugin_id in self.schemas:
                return self.schemas[plugin_id].defaults.copy()
            return {}

        return self.configs[plugin_id].copy()

    def set_parameters_batch(
        self,
        plugin_id: str,
        parameters: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """Set multiple parameters at once.

        Args:
            plugin_id: Plugin identifier
            parameters: Dictionary of parameter names and values

        Returns:
            Tuple of (all_successful, list_of_error_messages)
        """
        errors = []

        for param_name, value in parameters.items():
            success, message = self.set_parameter(plugin_id, param_name, value)
            if not success:
                errors.append(message)

        return len(errors) == 0, errors

    def create_profile(
        self,
        plugin_id: str,
        profile_name: str,
        parameters: Dict[str, Any],
        description: str = "",
        tags: List[str] = None
    ) -> Tuple[bool, str]:
        """Create a new configuration profile.

        Args:
            plugin_id: Plugin identifier
            profile_name: Human-readable profile name
            parameters: Parameter values for this profile
            description: Optional description
            tags: Optional list of tags

        Returns:
            Tuple of (success, profile_id_or_error_message)
        """
        if plugin_id not in self.profiles:
            self.profiles[plugin_id] = PresetLibrary(plugin_id=plugin_id)

        # Generate profile ID
        profile_id = self._generate_profile_id(plugin_id, profile_name)

        profile = ConfigProfile(
            profile_id=profile_id,
            plugin_id=plugin_id,
            name=profile_name,
            description=description,
            created_date=datetime.now().isoformat(),
            modified_date=datetime.now().isoformat(),
            parameters=parameters.copy(),
            tags=tags or []
        )

        self.profiles[plugin_id].presets[profile_id] = profile
        self._save_profiles(plugin_id)

        logger.info(f"Created profile {profile_id} for plugin {plugin_id}")
        return True, profile_id

    def load_profile(self, plugin_id: str, profile_id: str) -> Tuple[bool, str]:
        """Load a configuration profile.

        Args:
            plugin_id: Plugin identifier
            profile_id: Profile identifier

        Returns:
            Tuple of (success, message)
        """
        if plugin_id not in self.profiles:
            return False, f"No profiles for plugin {plugin_id}"

        library = self.profiles[plugin_id]
        if profile_id not in library.presets:
            return False, f"Profile {profile_id} not found"

        profile = library.presets[profile_id]

        # Apply profile parameters
        success, errors = self.set_parameters_batch(plugin_id, profile.parameters)

        if success:
            library.current_profile_id = profile_id
            self._save_profiles(plugin_id)
            logger.info(f"Loaded profile {profile_id} for plugin {plugin_id}")
            return True, f"Loaded profile: {profile.name}"
        else:
            return False, f"Failed to apply profile: {', '.join(errors)}"

    def delete_profile(self, plugin_id: str, profile_id: str) -> Tuple[bool, str]:
        """Delete a configuration profile.

        Args:
            plugin_id: Plugin identifier
            profile_id: Profile identifier

        Returns:
            Tuple of (success, message)
        """
        if plugin_id not in self.profiles:
            return False, f"No profiles for plugin {plugin_id}"

        library = self.profiles[plugin_id]
        if profile_id not in library.presets:
            return False, f"Profile {profile_id} not found"

        # Don't delete if it's the current profile
        if library.current_profile_id == profile_id:
            return False, "Cannot delete current profile"

        profile_name = library.presets[profile_id].name
        del library.presets[profile_id]
        self._save_profiles(plugin_id)

        logger.info(f"Deleted profile {profile_id} for plugin {plugin_id}")
        return True, f"Deleted profile: {profile_name}"

    def list_profiles(self, plugin_id: str) -> List[ConfigProfile]:
        """List all profiles for a plugin.

        Args:
            plugin_id: Plugin identifier

        Returns:
            List of ConfigProfile objects
        """
        if plugin_id not in self.profiles:
            return []

        return list(self.profiles[plugin_id].presets.values())

    def get_current_profile(self, plugin_id: str) -> Optional[ConfigProfile]:
        """Get the currently loaded profile.

        Args:
            plugin_id: Plugin identifier

        Returns:
            ConfigProfile or None
        """
        if plugin_id not in self.profiles:
            return None

        library = self.profiles[plugin_id]
        if not library.current_profile_id:
            return None

        return library.presets.get(library.current_profile_id)

    def search_profiles(
        self,
        plugin_id: str,
        query: str = ""
    ) -> List[ConfigProfile]:
        """Search profiles by name or tags.

        Args:
            plugin_id: Plugin identifier
            query: Search query (searches name and tags)

        Returns:
            List of matching ConfigProfile objects
        """
        if plugin_id not in self.profiles:
            return []

        query_lower = query.lower()
        library = self.profiles[plugin_id]

        results = []
        for profile in library.presets.values():
            if (query_lower in profile.name.lower() or
                any(query_lower in tag.lower() for tag in profile.tags)):
                results.append(profile)

        return results

    def export_profile(
        self,
        plugin_id: str,
        profile_id: str,
        export_path: str
    ) -> Tuple[bool, str]:
        """Export a profile to a file.

        Args:
            plugin_id: Plugin identifier
            profile_id: Profile identifier
            export_path: Path to export file

        Returns:
            Tuple of (success, message)
        """
        if plugin_id not in self.profiles:
            return False, f"No profiles for plugin {plugin_id}"

        library = self.profiles[plugin_id]
        if profile_id not in library.presets:
            return False, f"Profile {profile_id} not found"

        profile = library.presets[profile_id]

        try:
            export_data = {
                'plugin_id': plugin_id,
                'profile': profile.to_dict(),
                'export_date': datetime.now().isoformat(),
            }

            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2)

            logger.info(f"Exported profile {profile_id} to {export_path}")
            return True, f"Profile exported to {export_path}"
        except Exception as e:
            return False, f"Export failed: {str(e)}"

    def import_profile(
        self,
        import_path: str
    ) -> Tuple[bool, str]:
        """Import a profile from a file.

        Args:
            import_path: Path to import file

        Returns:
            Tuple of (success, profile_id_or_error_message)
        """
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            plugin_id = data.get('plugin_id')
            profile_data = data.get('profile', {})

            if not plugin_id:
                return False, "Invalid import file: missing plugin_id"

            # Create new profile with imported data
            success, result = self.create_profile(
                plugin_id=plugin_id,
                profile_name=profile_data.get('name', 'Imported Profile'),
                parameters=profile_data.get('parameters', {}),
                description=profile_data.get('description', ''),
                tags=profile_data.get('tags', [])
            )

            if success:
                logger.info(f"Imported profile from {import_path}")

            return success, result
        except Exception as e:
            return False, f"Import failed: {str(e)}"

    def set_user_preference(
        self,
        plugin_id: str,
        key: str,
        value: Any
    ) -> None:
        """Set a user preference (non-parameter setting).

        Args:
            plugin_id: Plugin identifier
            key: Preference key
            value: Preference value
        """
        if plugin_id not in self.preferences:
            self.preferences[plugin_id] = {}

        self.preferences[plugin_id][key] = value
        self._save_preferences(plugin_id)

    def get_user_preference(
        self,
        plugin_id: str,
        key: str,
        default: Any = None
    ) -> Any:
        """Get a user preference.

        Args:
            plugin_id: Plugin identifier
            key: Preference key
            default: Default value if not found

        Returns:
            Preference value or default
        """
        if plugin_id not in self.preferences:
            return default

        return self.preferences[plugin_id].get(key, default)

    def _save_config(self, plugin_id: str) -> None:
        """Save plugin configuration to file."""
        try:
            config_file = self.config_dir / f"{plugin_id}_config.json"

            data = {
                'plugin_id': plugin_id,
                'save_date': datetime.now().isoformat(),
                'parameters': self.configs.get(plugin_id, {}),
            }

            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved config for plugin {plugin_id}")
        except Exception as e:
            logger.error(f"Failed to save config for {plugin_id}: {e}")

    def _save_profiles(self, plugin_id: str) -> None:
        """Save plugin profiles to file."""
        try:
            profile_file = self.config_dir / f"{plugin_id}_profiles.json"

            if plugin_id not in self.profiles:
                return

            library = self.profiles[plugin_id]
            data = library.to_dict()
            data['save_date'] = datetime.now().isoformat()

            with open(profile_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved profiles for plugin {plugin_id}")
        except Exception as e:
            logger.error(f"Failed to save profiles for {plugin_id}: {e}")

    def _save_preferences(self, plugin_id: str) -> None:
        """Save user preferences to file."""
        try:
            pref_file = self.config_dir / f"{plugin_id}_preferences.json"

            data = {
                'plugin_id': plugin_id,
                'save_date': datetime.now().isoformat(),
                'preferences': self.preferences.get(plugin_id, {}),
            }

            with open(pref_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved preferences for plugin {plugin_id}")
        except Exception as e:
            logger.error(f"Failed to save preferences for {plugin_id}: {e}")

    def _generate_profile_id(self, plugin_id: str, profile_name: str) -> str:
        """Generate a unique profile ID.

        Args:
            plugin_id: Plugin identifier
            profile_name: Profile name

        Returns:
            Unique profile ID
        """
        base = f"{plugin_id}_{profile_name.lower().replace(' ', '_')}"
        hash_suffix = hashlib.md5(
            f"{plugin_id}_{profile_name}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:8]

        return f"{base}_{hash_suffix}"

    def reset_to_defaults(self, plugin_id: str) -> Tuple[bool, str]:
        """Reset plugin configuration to defaults.

        Args:
            plugin_id: Plugin identifier

        Returns:
            Tuple of (success, message)
        """
        if plugin_id not in self.schemas:
            return False, f"No schema found for plugin {plugin_id}"

        defaults = self.schemas[plugin_id].defaults.copy()
        self.configs[plugin_id] = defaults
        self._save_config(plugin_id)

        logger.info(f"Reset plugin {plugin_id} to defaults")
        return True, f"Plugin {plugin_id} reset to defaults"

    def export_all_configs(self, export_dir: str) -> Tuple[int, List[str]]:
        """Export all plugin configurations and profiles.

        Args:
            export_dir: Directory to export to

        Returns:
            Tuple of (count_exported, errors_list)
        """
        export_path = Path(export_dir)
        export_path.mkdir(parents=True, exist_ok=True)

        count = 0
        errors = []

        # Export configs
        for plugin_id, config in self.configs.items():
            try:
                config_file = export_path / f"{plugin_id}_config.json"
                data = {
                    'plugin_id': plugin_id,
                    'parameters': config,
                    'export_date': datetime.now().isoformat(),
                }
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                count += 1
            except Exception as e:
                errors.append(f"Failed to export {plugin_id}: {str(e)}")

        logger.info(f"Exported {count} plugin configurations")
        return count, errors

    def get_config_stats(self) -> dict:
        """Get statistics about stored configurations.

        Returns:
            Dictionary with statistics
        """
        total_plugins = len(self.configs)
        total_profiles = sum(len(lib.presets) for lib in self.profiles.values())
        total_parameters = sum(len(conf) for conf in self.configs.values())

        return {
            'total_plugins_configured': total_plugins,
            'total_profiles': total_profiles,
            'total_parameters': total_parameters,
            'config_dir': str(self.config_dir),
            'storage_format': self.storage_format.value,
        }
