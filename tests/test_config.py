# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""Tests for configuration management.

Tests for Pydantic-based configuration system.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from config import AcroSettings, ConfigMigration, load_settings


class TestAudioConfig:
    """Test audio configuration."""

    def test_default_sample_rate(self):
        """Test default sample rate."""
        config = AcroSettings()
        assert config.audio.sample_rate == 44100

    def test_sample_rate_range(self):
        """Test sample rate validation."""
        config = AcroSettings()

        # Valid rates
        config.audio.sample_rate = 48000
        assert config.audio.sample_rate == 48000

        # Invalid rates
        with pytest.raises(ValueError):
            config.audio.sample_rate = 1000  # Too low

        with pytest.raises(ValueError):
            config.audio.sample_rate = 500000  # Too high

    def test_buffer_size_power_of_two(self):
        """Test buffer size must be power of 2."""
        config = AcroSettings()

        # Valid buffer sizes
        for size in [128, 256, 512, 1024, 2048, 4096, 8192]:
            config.audio.buffer_size = size
            assert config.audio.buffer_size == size

        # Invalid buffer sizes
        with pytest.raises(ValueError):
            config.audio.buffer_size = 1000  # Not power of 2

        with pytest.raises(ValueError):
            config.audio.buffer_size = 512 + 1  # Not power of 2

    def test_channels_validation(self):
        """Test channel validation."""
        config = AcroSettings()

        config.audio.channels = 1
        assert config.audio.channels == 1

        config.audio.channels = 2
        assert config.audio.channels == 2

        with pytest.raises(ValueError):
            config.audio.channels = 3  # Invalid

    def test_latency_range(self):
        """Test latency validation."""
        config = AcroSettings()

        config.audio.latency = 0.05
        assert config.audio.latency == 0.05

        with pytest.raises(ValueError):
            config.audio.latency = 0.0  # Too low

        with pytest.raises(ValueError):
            config.audio.latency = 2.0  # Too high


class TestEffectsConfig:
    """Test effects configuration."""

    def test_default_effects(self):
        """Test default effect settings."""
        config = AcroSettings()
        assert config.effects.enable_reverb is True
        assert config.effects.enable_delay is True
        assert config.effects.enable_filter is True

    def test_max_reverb_time(self):
        """Test reverb time validation."""
        config = AcroSettings()

        config.effects.max_reverb_time = 5.0
        assert config.effects.max_reverb_time == 5.0

        with pytest.raises(ValueError):
            config.effects.max_reverb_time = 0.0  # Too low

        with pytest.raises(ValueError):
            config.effects.max_reverb_time = 20.0  # Too high


class TestMIDIConfig:
    """Test MIDI configuration."""

    def test_default_midi_disabled(self):
        """Test MIDI is disabled by default."""
        config = AcroSettings()
        assert config.midi.enabled is False

    def test_midi_channel_range(self):
        """Test MIDI channel validation."""
        config = AcroSettings()

        # Valid channels
        for ch in range(1, 17):
            config.midi.channel = ch
            assert config.midi.channel == ch

        # Invalid channels
        with pytest.raises(ValueError):
            config.midi.channel = 0  # Too low

        with pytest.raises(ValueError):
            config.midi.channel = 17  # Too high


class TestUIConfig:
    """Test UI configuration."""

    def test_theme_options(self):
        """Test available themes."""
        config = AcroSettings()

        for theme in ["dark", "light", "neon", "retro"]:
            config.ui.theme = theme
            assert config.ui.theme == theme

        with pytest.raises(ValueError):
            config.ui.theme = "invalid"  # type: ignore

    def test_window_size_minimum(self):
        """Test window size minimums."""
        config = AcroSettings()

        # Valid sizes
        config.ui.window_width = 800
        config.ui.window_height = 600
        assert config.ui.window_width == 800
        assert config.ui.window_height == 600

        # Invalid sizes
        with pytest.raises(ValueError):
            config.ui.window_width = 700  # Too small

        with pytest.raises(ValueError):
            config.ui.window_height = 500  # Too small

    def test_font_size_range(self):
        """Test font size validation."""
        config = AcroSettings()

        config.ui.font_size = 12
        assert config.ui.font_size == 12

        with pytest.raises(ValueError):
            config.ui.font_size = 5  # Too small

        with pytest.raises(ValueError):
            config.ui.font_size = 25  # Too large


class TestConfigLoading:
    """Test configuration file loading."""

    def test_load_from_toml(self, temp_config_file: Path):
        """Test loading configuration from TOML file."""
        config = AcroSettings.load_from_toml(temp_config_file)

        assert config.audio.sample_rate == 22050
        assert config.audio.buffer_size == 512
        assert config.ui.theme == "dark"

    def test_load_missing_file(self, temp_dir: Path):
        """Test loading missing file returns defaults."""
        config = AcroSettings.load_from_toml(
            temp_dir / "nonexistent.toml"
        )

        assert config.audio.sample_rate == 44100  # Default
        assert config.ui.theme == "dark"  # Default

    def test_save_to_toml(self, config: AcroSettings, temp_dir: Path):
        """Test saving configuration to TOML."""
        config.audio.sample_rate = 48000
        config.ui.theme = "neon"

        file_path = temp_dir / "saved_config.toml"
        config.save_to_toml(file_path)

        assert file_path.exists()

        # Load and verify
        loaded = AcroSettings.load_from_toml(file_path)
        assert loaded.audio.sample_rate == 48000
        assert loaded.ui.theme == "neon"

    def test_config_to_dict(self, config: AcroSettings):
        """Test converting config to dictionary."""
        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert "audio" in config_dict
        assert "effects" in config_dict
        assert config_dict["audio"]["sample_rate"] == 44100

    def test_config_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            "audio": {"sample_rate": 48000, "buffer_size": 1024},
            "ui": {"theme": "neon"},
        }

        config = AcroSettings.from_dict(data)
        assert config.audio.sample_rate == 48000
        assert config.ui.theme == "neon"


class TestEnvironmentVariables:
    """Test environment variable overrides."""

    def test_env_override_simple(self, monkeypatch):
        """Test environment variable override."""
        monkeypatch.setenv("ACRO_AUDIO__SAMPLE_RATE", "48000")

        config = AcroSettings()
        assert config.audio.sample_rate == 48000

    def test_env_override_ui(self, monkeypatch):
        """Test environment variable override for UI."""
        monkeypatch.setenv("ACRO_UI__THEME", "neon")
        monkeypatch.setenv("ACRO_LOG_LEVEL", "DEBUG")

        config = AcroSettings()
        assert config.ui.theme == "neon"
        assert config.log_level == "DEBUG"


class TestConfigMigration:
    """Test configuration migration."""

    def test_migration_registration(self):
        """Test migration function registration."""

        @ConfigMigration.register_migration(1, 2)
        def migrate_1_to_2(config):
            config["version"] = 2
            return config

        config = {"version": 1}
        migrated = ConfigMigration.migrate(config, 1, 2)

        assert migrated["version"] == 2

    def test_migration_missing(self):
        """Test error on missing migration path."""
        config = {"version": 1}

        with pytest.raises(ValueError):
            ConfigMigration.migrate(config, 1, 3)  # No path


class TestLoadSettings:
    """Test settings loading functions."""

    def test_load_settings_default(self):
        """Test loading default settings."""
        settings = load_settings()

        assert settings.audio.sample_rate == 44100
        assert settings.ui.theme == "dark"

    def test_load_settings_custom_path(self, temp_config_file: Path):
        """Test loading custom configuration file."""
        settings = load_settings(config_path=temp_config_file)

        assert settings.audio.sample_rate == 22050


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
