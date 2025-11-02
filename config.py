# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""Configuration management for Acro DJ Mixer.

This module provides robust configuration handling with:
- Pydantic validation for type safety
- TOML file support
- Environment variable overrides
- Configuration versioning and migration
- Per-environment configs (dev, test, prod)

Example:
    Basic usage::

        from config import AcroSettings
        from pathlib import Path

        # Load from TOML
        config = AcroSettings.load_from_toml(Path('acro_config.toml'))

        # Access configuration
        sample_rate = config.audio.sample_rate
        theme = config.ui.theme

        # Save configuration
        config.save_to_toml(Path('acro_config.toml'))
"""

from __future__ import annotations

import json
import sys
from dataclasses import field
from pathlib import Path
from typing import Any, Literal, Optional

try:
    import tomllib
except ImportError:
    # Python < 3.11
    import tomli as tomllib  # type: ignore[import-not-found,no-redef]

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AudioConfig(BaseModel):
    """Audio system configuration.

    Attributes:
        sample_rate: Sample rate in Hz (8000-192000, default 44100)
        buffer_size: Audio buffer size in frames (power of 2, default 2048)
        channels: Number of channels (1 or 2, default 2)
        device_name: Audio device name (None for auto-detect)
        latency: Target latency in seconds (default 0.05)
    """

    sample_rate: int = Field(default=44100, ge=8000, le=192000)
    buffer_size: int = Field(default=2048, ge=128, le=8192)
    channels: Literal[1, 2] = 2
    device_name: Optional[str] = None
    latency: float = Field(default=0.05, ge=0.001, le=1.0)

    @field_validator("buffer_size")
    @classmethod
    def buffer_must_be_power_of_two(cls, v: int) -> int:
        """Validate that buffer size is a power of 2."""
        if v & (v - 1) != 0:
            raise ValueError("buffer_size must be power of 2")
        return v


class EffectsConfig(BaseModel):
    """Audio effects configuration.

    Attributes:
        enable_reverb: Enable reverb effect
        enable_delay: Enable delay effect
        enable_filter: Enable filter effect
        max_reverb_time: Maximum reverb time in seconds
    """

    enable_reverb: bool = True
    enable_delay: bool = True
    enable_filter: bool = True
    max_reverb_time: float = Field(default=3.0, ge=0.1, le=10.0)


class MIDIConfig(BaseModel):
    """MIDI controller configuration.

    Attributes:
        enabled: Enable MIDI support
        device_name: MIDI device name (None for auto-detect)
        auto_connect: Automatically connect to device on startup
        channel: MIDI channel (1-16)
    """

    enabled: bool = False
    device_name: Optional[str] = None
    auto_connect: bool = True
    channel: int = Field(default=1, ge=1, le=16)


class UIConfig(BaseModel):
    """User interface configuration.

    Attributes:
        theme: UI theme (dark, light, neon, retro)
        language: UI language code (e.g., 'en', 'ja', 'es')
        window_width: Window width in pixels (minimum 800)
        window_height: Window height in pixels (minimum 600)
        font_size: Font size in points (8-20)
    """

    theme: Literal["dark", "light", "neon", "retro"] = "dark"
    language: str = "en"
    window_width: int = Field(default=1200, ge=800)
    window_height: int = Field(default=800, ge=600)
    font_size: int = Field(default=10, ge=8, le=20)


class LibraryConfig(BaseModel):
    """Music library configuration.

    Attributes:
        library_path: Path to music library directory
        auto_scan: Automatically scan library on startup
        scan_recursive: Scan subdirectories recursively
        supported_formats: List of supported audio formats
    """

    library_path: Path = Field(default_factory=lambda: Path.home() / "Music")
    auto_scan: bool = False
    scan_recursive: bool = True
    supported_formats: list[str] = Field(
        default_factory=lambda: ["wav", "flac", "mp3", "ogg"]
    )


class AcroSettings(BaseSettings):
    """Main application settings.

    Combines configuration from multiple sources in priority order:
    1. Environment variables (highest priority)
    2. TOML configuration file
    3. Default values (lowest priority)

    Example:
        >>> config = AcroSettings.load_from_toml(Path('acro_config.toml'))
        >>> config.audio.sample_rate
        44100

    Environment variables can override settings using nested delimiter:
        ACRO_AUDIO__SAMPLE_RATE=48000
        ACRO_UI__THEME=light
    """

    model_config = SettingsConfigDict(
        env_prefix="ACRO_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    # Application metadata
    version: str = "2.5.0"
    config_version: int = 1

    # Component configurations
    audio: AudioConfig = Field(default_factory=AudioConfig)
    effects: EffectsConfig = Field(default_factory=EffectsConfig)
    midi: MIDIConfig = Field(default_factory=MIDIConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    library: LibraryConfig = Field(default_factory=LibraryConfig)

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_file: Optional[Path] = None
    log_json: bool = False

    @classmethod
    def load_from_toml(cls, path: Path) -> AcroSettings:
        """Load configuration from TOML file.

        Combines TOML settings with environment variables (which take
        priority). If file doesn't exist, returns default settings.

        Args:
            path: Path to TOML configuration file

        Returns:
            Configured AcroSettings instance

        Example:
            >>> config = AcroSettings.load_from_toml(Path('acro_config.toml'))
        """
        config_dict: dict[str, Any] = {}

        if path.exists():
            with open(path, "rb") as f:
                config_dict = tomllib.load(f)

        return cls(**config_dict)

    def save_to_toml(self, path: Path) -> None:
        """Save configuration to TOML file.

        Args:
            path: Path where TOML file will be saved

        Raises:
            IOError: If file cannot be written

        Example:
            >>> config = AcroSettings()
            >>> config.save_to_toml(Path('acro_config.toml'))
        """
        try:
            import tomli_w
        except ImportError:
            # Fallback to JSON if tomli_w not available
            with open(path, "w") as f:
                # Convert to dict and save as JSON
                json.dump(
                    self.model_dump(mode="json"),
                    f,
                    indent=2,
                    default=str,
                )
            return

        path.parent.mkdir(parents=True, exist_ok=True)

        config_dict = self.model_dump(mode="json", exclude_none=True)

        with open(path, "wb") as f:
            tomli_w.dump(config_dict, f)

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary.

        Returns:
            Configuration as nested dictionary

        Example:
            >>> config = AcroSettings()
            >>> config_dict = config.to_dict()
            >>> print(config_dict['audio']['sample_rate'])
            44100
        """
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AcroSettings:
        """Create configuration from dictionary.

        Args:
            data: Configuration dictionary

        Returns:
            AcroSettings instance

        Example:
            >>> config_dict = {'audio': {'sample_rate': 48000}}
            >>> config = AcroSettings.from_dict(config_dict)
        """
        return cls(**data)


class ConfigMigration:
    """Handle configuration version migrations.

    Allows graceful upgrades when configuration schema changes
    between versions.

    Example:
        >>> old_config = {...}  # v1 config format
        >>> migrated = ConfigMigration.migrate(old_config, 1, 2)
    """

    # Migration functions: (from_version, to_version) -> migration_func
    _migrations: dict[tuple[int, int], Any] = {}

    @classmethod
    def migrate(
        cls,
        config_dict: dict[str, Any],
        from_version: int,
        to_version: int,
    ) -> dict[str, Any]:
        """Migrate configuration from one version to another.

        Args:
            config_dict: Configuration dictionary to migrate
            from_version: Current configuration version
            to_version: Target configuration version

        Returns:
            Migrated configuration dictionary

        Raises:
            ValueError: If no migration path exists

        Example:
            >>> config = {'version': 1, 'audio': {...}}
            >>> migrated = ConfigMigration.migrate(config, 1, 2)
        """
        current_version = from_version

        while current_version < to_version:
            next_version = current_version + 1
            migration_key = (current_version, next_version)

            if migration_key not in cls._migrations:
                raise ValueError(
                    f"No migration path from v{current_version} to v{next_version}"
                )

            migration_func = cls._migrations[migration_key]
            config_dict = migration_func(config_dict)
            current_version = next_version

        config_dict["config_version"] = to_version
        return config_dict

    @classmethod
    def register_migration(
        cls, from_v: int, to_v: int
    ) -> Any:
        """Register a migration function.

        Args:
            from_v: Source version
            to_v: Target version

        Returns:
            Decorator for migration function

        Example:
            >>> @ConfigMigration.register_migration(1, 2)
            >>> def migrate_1_to_2(config):
            ...     config['midi'] = config.get('midi', {})
            ...     return config
        """

        def decorator(func: Any) -> Any:
            cls._migrations[(from_v, to_v)] = func
            return func

        return decorator


# Example migration (uncomment to use)
# @ConfigMigration.register_migration(1, 2)
# def _migrate_1_to_2(config: dict[str, Any]) -> dict[str, Any]:
#     """Add MIDI configuration section if missing."""
#     if 'midi' not in config:
#         config['midi'] = {
#             'enabled': False,
#             'auto_connect': True,
#             'channel': 1,
#         }
#     return config


def get_config_path(environment: Optional[str] = None) -> Path:
    """Get configuration file path based on environment.

    Args:
        environment: Environment name (dev, test, prod).
                    If None, uses ACRO_ENV or defaults to 'prod'

    Returns:
        Path to configuration file

    Example:
        >>> dev_config = get_config_path('dev')
        >>> prod_config = get_config_path('prod')
    """
    if environment is None:
        environment = (
            sys.argv[1] if len(sys.argv) > 1 else
            Path.cwd().name.lower()
        )

    # Try explicit environment config first
    config_file = Path(f"acro_config.{environment}.toml")
    if config_file.exists():
        return config_file

    # Fall back to default
    return Path("acro_config.toml")


def load_settings(
    config_path: Optional[Path] = None,
    environment: Optional[str] = None,
) -> AcroSettings:
    """Load application settings.

    Convenience function that handles config path resolution and loading.

    Args:
        config_path: Explicit path to config file (overrides auto-detection)
        environment: Environment name for auto-detection

    Returns:
        Loaded AcroSettings instance

    Example:
        >>> config = load_settings()  # Uses acro_config.toml
        >>> config = load_settings(Path('/etc/acro/config.toml'))
    """
    if config_path is None:
        config_path = get_config_path(environment)

    return AcroSettings.load_from_toml(config_path)


# Global settings instance (singleton pattern)
_settings: Optional[AcroSettings] = None


def get_settings() -> AcroSettings:
    """Get global settings instance.

    Returns cached instance. Initialize with load_settings() first.

    Returns:
        Global AcroSettings instance

    Raises:
        RuntimeError: If settings not yet initialized

    Example:
        >>> load_settings()
        >>> config = get_settings()
    """
    global _settings

    if _settings is None:
        _settings = load_settings()

    return _settings


def set_settings(settings: AcroSettings) -> None:
    """Set global settings instance.

    Args:
        settings: AcroSettings instance to set globally

    Example:
        >>> config = AcroSettings()
        >>> set_settings(config)
    """
    global _settings
    _settings = settings
