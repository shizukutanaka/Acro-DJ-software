# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""Pytest configuration and shared fixtures.

This module provides common fixtures for testing Acro DJ Mixer.
Fixtures include audio data, mock devices, and configuration objects.

Usage:
    Fixtures defined here are automatically available to all tests
    without explicit imports. Example:

    def test_something(sample_audio):
        assert sample_audio.shape == (44100,)
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Generator

import numpy as np
import pytest

from config import AcroSettings


@pytest.fixture
def sample_audio() -> np.ndarray:
    """Generate 1-second test audio at 44.1kHz.

    Returns:
        Audio array: 44100 samples, shape (44100,)
    """
    sample_rate = 44100
    duration = 1.0
    frequency = 440.0  # A4 note
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = np.sin(2 * np.pi * frequency * t)
    return audio.astype(np.float32)


@pytest.fixture
def stereo_audio() -> np.ndarray:
    """Generate stereo test audio at 44.1kHz.

    Returns:
        Audio array: shape (44100, 2)
    """
    sample_rate = 44100
    duration = 1.0
    frequency = 440.0
    t = np.linspace(0, duration, int(sample_rate * duration))

    # Left channel: 440 Hz
    left = np.sin(2 * np.pi * frequency * t)

    # Right channel: 880 Hz
    right = np.sin(2 * np.pi * frequency * 2 * t)

    audio = np.column_stack([left, right])
    return audio.astype(np.float32)


@pytest.fixture
def sweep_audio() -> np.ndarray:
    """Generate frequency sweep audio (20Hz to 20kHz).

    Returns:
        Audio array: shape (44100,)
    """
    sample_rate = 44100
    duration = 1.0
    t = np.linspace(0, duration, int(sample_rate * duration))

    # Linear frequency sweep from 20 Hz to 20 kHz
    f0 = 20.0
    f1 = 20000.0
    k = (f1 - f0) / duration

    phase = 2 * np.pi * (f0 * t + k * t**2 / 2)
    audio = np.sin(phase)

    return audio.astype(np.float32)


@pytest.fixture
def silence() -> np.ndarray:
    """Generate silent audio (zeros).

    Returns:
        Silent audio array: shape (44100,)
    """
    return np.zeros(44100, dtype=np.float32)


@pytest.fixture
def white_noise() -> np.ndarray:
    """Generate white noise audio.

    Returns:
        White noise array: shape (44100,)
    """
    return np.random.randn(44100).astype(np.float32)


@pytest.fixture
def impulse() -> np.ndarray:
    """Generate impulse audio (single spike).

    Returns:
        Impulse array: shape (44100,)
    """
    audio = np.zeros(44100, dtype=np.float32)
    audio[0] = 1.0
    return audio


@pytest.fixture
def config() -> AcroSettings:
    """Get default configuration.

    Returns:
        AcroSettings instance with defaults
    """
    return AcroSettings()


@pytest.fixture
def test_config() -> AcroSettings:
    """Get test configuration.

    Returns:
        AcroSettings configured for testing
    """
    settings = AcroSettings()
    settings.audio.sample_rate = 22050  # Lower for faster tests
    settings.audio.buffer_size = 512
    settings.log_level = "DEBUG"
    return settings


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create temporary directory for tests.

    Yields:
        Path to temporary directory (auto-cleaned up)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_audio_file(sample_audio: np.ndarray, temp_dir: Path) -> Path:
    """Create temporary WAV file with test audio.

    Args:
        sample_audio: Audio data to save
        temp_dir: Temporary directory

    Returns:
        Path to created WAV file
    """
    try:
        import soundfile
    except ImportError:
        pytest.skip("soundfile not installed")

    audio_file = temp_dir / "test_audio.wav"
    soundfile.write(audio_file, sample_audio, 44100)
    return audio_file


@pytest.fixture
def temp_config_file(temp_dir: Path) -> Path:
    """Create temporary TOML configuration file.

    Args:
        temp_dir: Temporary directory

    Returns:
        Path to created configuration file
    """
    config_file = temp_dir / "test_config.toml"

    config_content = """
version = "2.5.0"
config_version = 1

[audio]
sample_rate = 22050
buffer_size = 512
channels = 2

[effects]
enable_reverb = true

[ui]
theme = "dark"
language = "en"

[library]
auto_scan = false
"""

    config_file.write_text(config_content)
    return config_file


@pytest.fixture
def mock_audio_device(mocker):
    """Mock sounddevice.OutputStream.

    Args:
        mocker: pytest-mock fixture

    Returns:
        Mocked OutputStream
    """
    return mocker.patch("sounddevice.OutputStream")


@pytest.fixture
def mock_audio_input(mocker):
    """Mock sounddevice.InputStream.

    Args:
        mocker: pytest-mock fixture

    Returns:
        Mocked InputStream
    """
    return mocker.patch("sounddevice.InputStream")


@pytest.fixture
def mock_midi_device(mocker):
    """Mock mido MIDI device.

    Args:
        mocker: pytest-mock fixture

    Returns:
        Mocked MIDI input
    """
    return mocker.patch("mido.open_input")


# Test markers
def pytest_configure(config: pytest.Config) -> None:
    """Register custom pytest markers.

    Args:
        config: Pytest configuration
    """
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "audio: marks tests requiring audio")
    config.addinivalue_line("markers", "midi: marks tests requiring MIDI")
    config.addinivalue_line("markers", "integration: marks integration tests")
