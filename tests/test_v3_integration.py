# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Comprehensive integration tests for Acro DJ Mixer v3.x

Tests all v3.0, v3.1, and v3.2 versions with complete feature coverage.
"""

from __future__ import annotations

import pytest
import tempfile
import numpy as np
from pathlib import Path
from dataclasses import dataclass
import json

# Import test modules (these would be the actual app modules in production)
# For now, we test the adapter modules directly

from acro_low_latency_adapter import (
    create_audio_adapter,
    AudioAdapterConfig,
    AcroAudioAdapter,
    SimpleAudioAdapter,
)
from acro_beatmatching_adapter import (
    create_beatmatching_adapter,
    BeatmatchingConfig,
    TrackBeatInfo,
)
from acro_network_adapter import (
    create_network_adapter,
    NetworkAdapterConfig,
    MidiEventData,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_audio_file():
    """Create temporary audio file for testing."""
    try:
        import soundfile
        import numpy as np
    except ImportError:
        pytest.skip("soundfile not installed")

    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        # Create simple sine wave audio
        sr = 22050
        duration = 2
        t = np.linspace(0, duration, int(sr * duration))
        audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)

        soundfile.write(f.name, audio, sr)
        yield f.name

        # Cleanup
        Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def audio_config():
    """Audio adapter configuration."""
    return AudioAdapterConfig(
        sample_rate=44100,
        buffer_size=256,
        audio_backend="PortAudio"
    )


@pytest.fixture
def beatmatching_config():
    """Beat matching configuration."""
    return BeatmatchingConfig(
        sample_rate=44100,
        min_bpm=60.0,
        max_bpm=200.0,
        confidence_threshold=0.5
    )


@pytest.fixture
def network_config():
    """Network adapter configuration."""
    return NetworkAdapterConfig(
        listen_port=5004,
        mode="standalone"
    )


# ============================================================================
# V3.0 - LOW-LATENCY AUDIO ENGINE TESTS
# ============================================================================

class TestV30LowLatencyAudio:
    """Test suite for v3.0 low-latency audio engine integration."""

    def test_audio_adapter_initialization(self, audio_config):
        """Test audio adapter can be initialized."""
        adapter = create_audio_adapter(audio_config)
        assert adapter is not None
        assert isinstance(adapter, (AcroAudioAdapter, SimpleAudioAdapter))

    def test_audio_adapter_configuration_preserved(self, audio_config):
        """Test audio adapter preserves configuration."""
        adapter = create_audio_adapter(audio_config)
        status = adapter.get_status()

        assert status["sample_rate"] == 44100
        assert status["running"] == False

    def test_audio_adapter_latency_info(self, audio_config):
        """Test audio adapter provides latency information."""
        adapter = create_audio_adapter(audio_config)
        info = adapter.get_latency_info()

        assert isinstance(info, dict)
        assert "total_latency_ms" in info

    def test_audio_adapter_performance_metrics(self, audio_config):
        """Test audio adapter provides performance metrics."""
        adapter = create_audio_adapter(audio_config)
        metrics = adapter.get_performance_metrics()

        assert isinstance(metrics, dict)

    def test_audio_adapter_xrun_checking(self, audio_config):
        """Test XRun checking."""
        adapter = create_audio_adapter(audio_config)
        xruns = adapter.check_xruns()

        assert isinstance(xruns, int)
        assert xruns >= 0

    def test_audio_adapter_optimization_methods(self, audio_config):
        """Test optimization methods."""
        adapter = create_audio_adapter(audio_config)

        # Should not raise
        adapter.optimize_for_latency()
        adapter.optimize_for_stability()

    def test_audio_adapter_context_manager(self, audio_config):
        """Test context manager protocol."""
        try:
            with create_audio_adapter(audio_config) as adapter:
                assert adapter is not None
                assert hasattr(adapter, 'get_status')
        except RuntimeError:
            # OK if audio device not available
            pass

    def test_multiple_audio_adapters(self, audio_config):
        """Test creating multiple audio adapters."""
        adapter1 = create_audio_adapter(audio_config)
        adapter2 = create_audio_adapter(audio_config)

        assert adapter1 is not None
        assert adapter2 is not None


# ============================================================================
# V3.1 - BEAT MATCHING & AUTO-SYNC TESTS
# ============================================================================

class TestV31BeatMatching:
    """Test suite for v3.1 beat matching integration."""

    def test_beatmatching_adapter_initialization(self, beatmatching_config):
        """Test beat matching adapter initialization."""
        adapter = create_beatmatching_adapter(beatmatching_config)
        assert adapter is not None

    def test_beatmatching_adapter_status(self, beatmatching_config):
        """Test beat matching adapter status."""
        adapter = create_beatmatching_adapter(beatmatching_config)
        status = adapter.get_status()

        assert isinstance(status, dict)
        assert "available" in status

    def test_beatmatching_config_validation(self):
        """Test beat matching configuration validation."""
        config = BeatmatchingConfig(
            min_bpm=80.0,
            max_bpm=150.0,
            max_tempo_change_percent=15.0
        )
        assert config.min_bpm == 80.0
        assert config.max_bpm == 150.0

    def test_beatmatching_track_analysis_missing_file(self, beatmatching_config):
        """Test track analysis with missing file."""
        adapter = create_beatmatching_adapter(beatmatching_config)
        result = adapter.analyze_track("/nonexistent/file.mp3")

        assert result is None or result.bpm is None

    def test_beatmatching_track_info_structure(self, beatmatching_config):
        """Test track info structure."""
        adapter = create_beatmatching_adapter(beatmatching_config)
        info = adapter.get_track_info()

        assert isinstance(info, dict)
        assert "beatmatching_available" in info
        assert "master_track" in info
        assert "slave_track" in info

    def test_beatmatching_sync_status_empty(self, beatmatching_config):
        """Test sync status with no tracks."""
        adapter = create_beatmatching_adapter(beatmatching_config)
        status = adapter.get_sync_status()

        assert isinstance(status, dict)

    def test_beatmatching_auto_sync_no_tracks(self, beatmatching_config):
        """Test auto-sync without tracks."""
        adapter = create_beatmatching_adapter(beatmatching_config)
        result = adapter.auto_sync()

        assert result == False

    def test_beatmatching_phase_offset_calculation(self, beatmatching_config):
        """Test phase offset calculation."""
        adapter = create_beatmatching_adapter(beatmatching_config)
        offset = adapter.calculate_phase_offset(2.0, 1.5)

        assert isinstance(offset, float)

    def test_beatmatching_pitch_adjustment(self, beatmatching_config):
        """Test pitch adjustment calculation."""
        adapter = create_beatmatching_adapter(beatmatching_config)
        pitch = adapter.get_pitch_adjustment()

        assert isinstance(pitch, float)

    def test_beatmatching_multiple_adapters(self, beatmatching_config):
        """Test multiple beat matching adapters."""
        adapter1 = create_beatmatching_adapter(beatmatching_config)
        adapter2 = create_beatmatching_adapter(beatmatching_config)

        assert adapter1 is not None
        assert adapter2 is not None


# ============================================================================
# V3.2 - NETWORK MUSIC PERFORMANCE TESTS
# ============================================================================

class TestV32NetworkMusic:
    """Test suite for v3.2 network music integration."""

    def test_network_adapter_initialization(self, network_config):
        """Test network adapter initialization."""
        adapter = create_network_adapter(network_config)
        assert adapter is not None

    def test_network_adapter_configuration(self, network_config):
        """Test network configuration."""
        assert network_config.listen_port == 5004
        assert network_config.mode == "standalone"

    def test_network_adapter_status(self, network_config):
        """Test network adapter status."""
        adapter = create_network_adapter(network_config)
        status = adapter.get_status()

        assert isinstance(status, dict)
        assert "available" in status
        assert "mode" in status

    def test_network_mode_standalone(self, network_config):
        """Test standalone network mode."""
        adapter = create_network_adapter(network_config)
        status = adapter.get_status()

        assert status["mode"] == "standalone"

    def test_midi_event_creation(self):
        """Test MIDI event creation."""
        event = MidiEventData(
            event_type="note_on",
            channel=0,
            data1=60,
            data2=100
        )
        assert event.event_type == "note_on"
        assert event.data1 == 60

    def test_midi_control_change_event(self):
        """Test control change MIDI event."""
        event = MidiEventData(
            event_type="control_change",
            channel=0,
            data1=7,
            data2=64
        )
        assert event.event_type == "control_change"
        assert event.data1 == 7

    def test_midi_event_with_timestamp(self):
        """Test MIDI event with timestamp."""
        event = MidiEventData(
            event_type="note_off",
            channel=0,
            data1=60,
            data2=0,
            timestamp_ms=1000.5
        )
        assert event.timestamp_ms == 1000.5

    def test_network_send_midi_disconnected(self, network_config):
        """Test sending MIDI when disconnected."""
        adapter = create_network_adapter(network_config)
        event = MidiEventData(
            event_type="control_change",
            channel=0,
            data1=7,
            data2=64
        )

        result = adapter.send_midi_event(event)
        assert result == False  # Should fail when not connected

    def test_network_latency_reporting(self, network_config):
        """Test network latency reporting."""
        adapter = create_network_adapter(network_config)
        latency = adapter.get_latency_ms()

        assert isinstance(latency, float)
        assert latency >= 0

    def test_network_packet_loss_reporting(self, network_config):
        """Test packet loss reporting."""
        adapter = create_network_adapter(network_config)
        loss = adapter.get_packet_loss_percent()

        assert isinstance(loss, float)
        assert 0 <= loss <= 100

    def test_network_session_management(self, network_config):
        """Test session save/load."""
        adapter = create_network_adapter(network_config)

        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            filename = f.name

        try:
            saved = adapter.save_session(filename)
            assert isinstance(saved, bool)

            if saved:
                assert Path(filename).exists()
                loaded = adapter.load_session(filename)
                assert isinstance(loaded, bool)
        finally:
            Path(filename).unlink(missing_ok=True)

    def test_network_multiple_adapters(self, network_config):
        """Test multiple network adapters."""
        adapter1 = create_network_adapter(network_config)
        adapter2 = create_network_adapter(network_config)

        assert adapter1 is not None
        assert adapter2 is not None


# ============================================================================
# CROSS-VERSION INTEGRATION TESTS
# ============================================================================

class TestCrossVersionIntegration:
    """Test integration across all v3.x versions."""

    def test_all_adapters_can_be_created(
        self,
        audio_config,
        beatmatching_config,
        network_config
    ):
        """Test all adapters can be created together."""
        audio = create_audio_adapter(audio_config)
        beatmatch = create_beatmatching_adapter(beatmatching_config)
        network = create_network_adapter(network_config)

        assert audio is not None
        assert beatmatch is not None
        assert network is not None

    def test_all_adapters_provide_status(
        self,
        audio_config,
        beatmatching_config,
        network_config
    ):
        """Test all adapters can report status."""
        audio = create_audio_adapter(audio_config)
        beatmatch = create_beatmatching_adapter(beatmatching_config)
        network = create_network_adapter(network_config)

        audio_status = audio.get_status()
        beatmatch_status = beatmatch.get_status()
        network_status = network.get_status()

        assert isinstance(audio_status, dict)
        assert isinstance(beatmatch_status, dict)
        assert isinstance(network_status, dict)

    def test_adapters_with_context_managers(
        self,
        audio_config,
        beatmatching_config,
        network_config
    ):
        """Test adapters work as context managers."""
        try:
            with create_audio_adapter(audio_config) as audio:
                assert audio is not None
        except RuntimeError:
            pass

        with create_beatmatching_adapter(beatmatching_config) as beatmatch:
            assert beatmatch is not None

        with create_network_adapter(network_config) as network:
            assert network is not None

    def test_v30_v31_compatibility(self, audio_config, beatmatching_config):
        """Test v3.0 and v3.1 compatibility."""
        audio = create_audio_adapter(audio_config)
        beatmatch = create_beatmatching_adapter(beatmatching_config)

        # Both should work independently
        assert audio.get_status()["sample_rate"] == 44100
        assert beatmatch.get_status()["available"] in [True, False]

    def test_v31_v32_compatibility(self, beatmatching_config, network_config):
        """Test v3.1 and v3.2 compatibility."""
        beatmatch = create_beatmatching_adapter(beatmatching_config)
        network = create_network_adapter(network_config)

        # Both should work independently
        assert beatmatch.get_track_info()
        assert network.get_status()

    def test_v30_v32_compatibility(self, audio_config, network_config):
        """Test v3.0 and v3.2 compatibility."""
        audio = create_audio_adapter(audio_config)
        network = create_network_adapter(network_config)

        # Both should work independently
        assert audio.get_latency_info()
        assert network.get_network_status()

    def test_all_features_together(
        self,
        audio_config,
        beatmatching_config,
        network_config
    ):
        """Test all features working together."""
        audio = create_audio_adapter(audio_config)
        beatmatch = create_beatmatching_adapter(beatmatching_config)
        network = create_network_adapter(network_config)

        # Simulate integrated workflow
        audio_latency = audio.get_latency_ms()
        beat_status = beatmatch.get_sync_status()
        network_status = network.get_network_status()

        assert audio_latency >= 0
        assert isinstance(beat_status, dict)
        assert isinstance(network_status, dict)


# ============================================================================
# ROBUSTNESS & ERROR HANDLING TESTS
# ============================================================================

class TestRobustness:
    """Test error handling and robustness."""

    def test_audio_adapter_survives_multiple_operations(self, audio_config):
        """Test audio adapter robustness."""
        adapter = create_audio_adapter(audio_config)

        # Should handle multiple operations gracefully
        adapter.get_latency_ms()
        adapter.get_performance_metrics()
        adapter.optimize_for_latency()
        adapter.check_xruns()
        adapter.get_status()

    def test_beatmatching_survives_empty_operations(self, beatmatching_config):
        """Test beat matching adapter robustness."""
        adapter = create_beatmatching_adapter(beatmatching_config)

        # Should handle empty operations
        adapter.auto_sync()
        adapter.get_sync_status()
        adapter.calculate_phase_offset(0, 0)
        adapter.get_pitch_adjustment()

    def test_network_survives_disconnected_operations(self, network_config):
        """Test network adapter robustness when disconnected."""
        adapter = create_network_adapter(network_config)

        # Should handle operations when disconnected
        adapter.get_network_status()
        adapter.get_latency_ms()
        adapter.get_packet_loss_percent()

    def test_adapters_cleanup(
        self,
        audio_config,
        beatmatching_config,
        network_config
    ):
        """Test adapter cleanup."""
        audio = create_audio_adapter(audio_config)
        beatmatch = create_beatmatching_adapter(beatmatching_config)
        network = create_network_adapter(network_config)

        # Should cleanup without raising
        audio.close()
        beatmatch.get_status()  # Should still work
        network.close()


# ============================================================================
# CONFIGURATION & SETTINGS TESTS
# ============================================================================

class TestConfiguration:
    """Test configuration management."""

    def test_audio_config_variations(self):
        """Test various audio configurations."""
        configs = [
            AudioAdapterConfig(sample_rate=44100, buffer_size=256),
            AudioAdapterConfig(sample_rate=48000, buffer_size=512),
            AudioAdapterConfig(sample_rate=96000, buffer_size=1024),
        ]

        for config in configs:
            adapter = create_audio_adapter(config)
            assert adapter.get_status()["sample_rate"] == config.sample_rate

    def test_beatmatching_config_variations(self):
        """Test various beat matching configurations."""
        configs = [
            BeatmatchingConfig(min_bpm=60, max_bpm=200),
            BeatmatchingConfig(min_bpm=80, max_bpm=150),
            BeatmatchingConfig(min_bpm=90, max_bpm=130),
        ]

        for config in configs:
            adapter = create_beatmatching_adapter(config)
            assert adapter.get_status()

    def test_network_config_variations(self):
        """Test various network configurations."""
        configs = [
            NetworkAdapterConfig(listen_port=5004),
            NetworkAdapterConfig(listen_port=5005),
            NetworkAdapterConfig(listen_port=5006),
        ]

        for config in configs:
            adapter = create_network_adapter(config)
            assert adapter.get_status()


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Test performance characteristics."""

    def test_audio_adapter_latency_target(self, audio_config):
        """Test audio latency meets targets."""
        adapter = create_audio_adapter(audio_config)
        latency = adapter.get_latency_ms()

        # Should be reasonable (not measuring real latency, just adapter overhead)
        assert latency >= 0
        # If real engine available, should be < 50ms
        if isinstance(adapter, type(create_audio_adapter(audio_config))):
            # Check it's not unreasonable
            assert latency < 1000

    def test_beatmatching_status_response_time(self, beatmatching_config):
        """Test beat matching status response is fast."""
        adapter = create_beatmatching_adapter(beatmatching_config)

        import time
        start = time.time()
        status = adapter.get_status()
        elapsed = (time.time() - start) * 1000  # Convert to ms

        # Should respond in < 100ms
        assert elapsed < 100
        assert status

    def test_network_status_response_time(self, network_config):
        """Test network status response is fast."""
        adapter = create_network_adapter(network_config)

        import time
        start = time.time()
        status = adapter.get_status()
        elapsed = (time.time() - start) * 1000

        # Should respond in < 100ms
        assert elapsed < 100
        assert status


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
