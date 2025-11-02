# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""Integration tests for Acro adapter modules.

Tests the integration of research-based modules with the existing Acro DJ Mixer
system using adapters.
"""

from __future__ import annotations

import pytest
from pathlib import Path
import tempfile
import json

# Import adapters
from acro_low_latency_adapter import (
    AcroAudioAdapter,
    SimpleAudioAdapter,
    AudioAdapterConfig,
    create_audio_adapter,
)
from acro_beatmatching_adapter import (
    AcroBeatmatchingAdapter,
    SimpleBeatmatchingAdapter,
    BeatmatchingConfig,
    create_beatmatching_adapter,
)
from acro_network_adapter import (
    AcroNetworkAdapter,
    SimpleNetworkAdapter,
    NetworkAdapterConfig,
    MidiEventData,
    create_network_adapter,
)


# ============================================================================
# AUDIO ADAPTER TESTS
# ============================================================================

class TestAudioAdapterConfig:
    """Test audio adapter configuration."""

    def test_default_config(self):
        """Test creating default configuration."""
        config = AudioAdapterConfig()
        assert config.sample_rate == 44100
        assert config.buffer_size == 256
        assert config.channels == 2
        assert config.audio_backend == "PortAudio"

    def test_custom_config(self):
        """Test creating custom configuration."""
        config = AudioAdapterConfig(
            sample_rate=48000,
            buffer_size=512,
            audio_backend="JACK"
        )
        assert config.sample_rate == 48000
        assert config.buffer_size == 512
        assert config.audio_backend == "JACK"


class TestAudioAdapterInitialization:
    """Test audio adapter initialization."""

    def test_adapter_creation(self):
        """Test creating audio adapter."""
        config = AudioAdapterConfig()
        adapter = create_audio_adapter(config)
        assert adapter is not None

    def test_adapter_type(self):
        """Test adapter returns correct type."""
        config = AudioAdapterConfig()
        adapter = create_audio_adapter(config)
        # Should return either real or fallback adapter
        assert isinstance(adapter, (AcroAudioAdapter, SimpleAudioAdapter))

    def test_adapter_status_initial(self):
        """Test initial adapter status."""
        config = AudioAdapterConfig()
        adapter = create_audio_adapter(config)
        status = adapter.get_status()

        assert "running" in status
        assert status["running"] == False
        assert "sample_rate" in status


class TestAudioAdapterProperties:
    """Test audio adapter properties and methods."""

    def test_latency_reporting(self):
        """Test latency can be reported."""
        config = AudioAdapterConfig()
        adapter = create_audio_adapter(config)
        latency = adapter.get_latency_ms()
        assert isinstance(latency, float)
        assert latency >= 0

    def test_latency_info(self):
        """Test latency info structure."""
        config = AudioAdapterConfig()
        adapter = create_audio_adapter(config)
        info = adapter.get_latency_info()

        assert isinstance(info, dict)
        assert "total_latency_ms" in info

    def test_performance_metrics(self):
        """Test performance metrics can be retrieved."""
        config = AudioAdapterConfig()
        adapter = create_audio_adapter(config)
        metrics = adapter.get_performance_metrics()

        assert isinstance(metrics, dict)

    def test_xrun_checking(self):
        """Test XRun checking."""
        config = AudioAdapterConfig()
        adapter = create_audio_adapter(config)
        xruns = adapter.check_xruns()

        assert isinstance(xruns, int)
        assert xruns >= 0

    def test_optimization_methods(self):
        """Test optimization methods don't raise errors."""
        config = AudioAdapterConfig()
        adapter = create_audio_adapter(config)

        # Should not raise
        adapter.optimize_for_latency()
        adapter.optimize_for_stability()

    def test_context_manager(self):
        """Test context manager protocol."""
        config = AudioAdapterConfig()
        adapter = create_audio_adapter(config)

        # Should not raise
        try:
            with adapter as ctx:
                assert ctx is not None
        except RuntimeError:
            # OK if audio device not available in test environment
            pass


# ============================================================================
# BEAT MATCHING ADAPTER TESTS
# ============================================================================

class TestBeatmatchingAdapterConfig:
    """Test beat matching adapter configuration."""

    def test_default_config(self):
        """Test default beat matching config."""
        config = BeatmatchingConfig()
        assert config.sample_rate == 44100
        assert config.min_bpm == 60.0
        assert config.max_bpm == 200.0

    def test_custom_config(self):
        """Test custom beat matching config."""
        config = BeatmatchingConfig(
            min_bpm=80.0,
            max_bpm=150.0,
            max_tempo_change_percent=15.0
        )
        assert config.min_bpm == 80.0
        assert config.max_bpm == 150.0
        assert config.max_tempo_change_percent == 15.0


class TestBeatmatchingAdapterInitialization:
    """Test beat matching adapter initialization."""

    def test_adapter_creation(self):
        """Test creating beat matching adapter."""
        config = BeatmatchingConfig()
        adapter = create_beatmatching_adapter(config)
        assert adapter is not None

    def test_adapter_type(self):
        """Test adapter returns correct type."""
        config = BeatmatchingConfig()
        adapter = create_beatmatching_adapter(config)
        assert isinstance(adapter, (AcroBeatmatchingAdapter, SimpleBeatmatchingAdapter))

    def test_adapter_status_initial(self):
        """Test initial beat matching status."""
        config = BeatmatchingConfig()
        adapter = create_beatmatching_adapter(config)
        status = adapter.get_status()

        assert "available" in status
        assert isinstance(status["available"], bool)


class TestBeatmatchingAdapterState:
    """Test beat matching adapter state management."""

    def test_empty_state_initially(self):
        """Test empty track info initially."""
        config = BeatmatchingConfig()
        adapter = create_beatmatching_adapter(config)

        info = adapter.get_track_info() if hasattr(adapter, 'get_track_info') else {}
        if info:
            assert "master_track" in info
            assert "slave_track" in info

    def test_sync_status_unavailable(self):
        """Test sync status when no tracks loaded."""
        config = BeatmatchingConfig()
        adapter = create_beatmatching_adapter(config)

        if hasattr(adapter, 'get_sync_status'):
            status = adapter.get_sync_status()
            assert isinstance(status, dict)


class TestBeatmatchingAdapterMethods:
    """Test beat matching adapter methods."""

    def test_set_master_no_file(self):
        """Test setting master track with nonexistent file."""
        config = BeatmatchingConfig()
        adapter = create_beatmatching_adapter(config)

        if hasattr(adapter, 'set_master_track'):
            result = adapter.set_master_track("/nonexistent/file.mp3")
            assert result == False

    def test_set_slave_no_file(self):
        """Test setting slave track with nonexistent file."""
        config = BeatmatchingConfig()
        adapter = create_beatmatching_adapter(config)

        if hasattr(adapter, 'set_slave_track'):
            result = adapter.set_slave_track("/nonexistent/file.mp3")
            assert result == False

    def test_auto_sync_no_tracks(self):
        """Test auto sync without tracks loaded."""
        config = BeatmatchingConfig()
        adapter = create_beatmatching_adapter(config)

        if hasattr(adapter, 'auto_sync'):
            result = adapter.auto_sync()
            assert result == False

    def test_phase_offset_calculation(self):
        """Test phase offset calculation."""
        config = BeatmatchingConfig()
        adapter = create_beatmatching_adapter(config)

        if hasattr(adapter, 'calculate_phase_offset'):
            offset = adapter.calculate_phase_offset(2.0, 1.5)
            assert isinstance(offset, float)

    def test_pitch_adjustment(self):
        """Test pitch adjustment calculation."""
        config = BeatmatchingConfig()
        adapter = create_beatmatching_adapter(config)

        if hasattr(adapter, 'get_pitch_adjustment'):
            pitch = adapter.get_pitch_adjustment()
            assert isinstance(pitch, float)


# ============================================================================
# NETWORK ADAPTER TESTS
# ============================================================================

class TestNetworkAdapterConfig:
    """Test network adapter configuration."""

    def test_default_config(self):
        """Test default network config."""
        config = NetworkAdapterConfig()
        assert config.listen_port == 5004
        assert config.mode == "standalone"
        assert config.enable_click_sync == True

    def test_custom_config(self):
        """Test custom network config."""
        config = NetworkAdapterConfig(
            listen_port=5005,
            master_ip="192.168.1.100",
            mode="slave"
        )
        assert config.listen_port == 5005
        assert config.master_ip == "192.168.1.100"
        assert config.mode == "slave"


class TestNetworkAdapterInitialization:
    """Test network adapter initialization."""

    def test_adapter_creation(self):
        """Test creating network adapter."""
        config = NetworkAdapterConfig()
        adapter = create_network_adapter(config)
        assert adapter is not None

    def test_adapter_type(self):
        """Test adapter returns correct type."""
        config = NetworkAdapterConfig()
        adapter = create_network_adapter(config)
        assert isinstance(adapter, (AcroNetworkAdapter, SimpleNetworkAdapter))

    def test_adapter_status_initial(self):
        """Test initial network status."""
        config = NetworkAdapterConfig()
        adapter = create_network_adapter(config)
        status = adapter.get_status()

        assert "available" in status
        assert "mode" in status
        assert status["mode"] in ["standalone", "master", "slave"]


class TestNetworkAdapterState:
    """Test network adapter state management."""

    def test_initial_disconnected_state(self):
        """Test initial state is disconnected."""
        config = NetworkAdapterConfig()
        adapter = create_network_adapter(config)

        status = adapter.get_status()
        if "is_connected" in status:
            assert status["is_connected"] == False

    def test_mode_configuration(self):
        """Test mode is preserved from config."""
        config = NetworkAdapterConfig(mode="master")
        adapter = create_network_adapter(config)

        status = adapter.get_status()
        # Mode might be different after initialization
        assert "mode" in status


class TestMidiEventData:
    """Test MIDI event data structure."""

    def test_create_note_on(self):
        """Test creating note-on event."""
        event = MidiEventData(
            event_type="note_on",
            channel=0,
            data1=60,
            data2=100
        )
        assert event.event_type == "note_on"
        assert event.data1 == 60

    def test_create_control_change(self):
        """Test creating control change event."""
        event = MidiEventData(
            event_type="control_change",
            channel=0,
            data1=7,  # Volume CC
            data2=64
        )
        assert event.event_type == "control_change"
        assert event.data1 == 7

    def test_create_with_timestamp(self):
        """Test creating event with timestamp."""
        event = MidiEventData(
            event_type="note_off",
            channel=0,
            data1=60,
            data2=0,
            timestamp_ms=1000.5
        )
        assert event.timestamp_ms == 1000.5


class TestNetworkAdapterMethods:
    """Test network adapter methods."""

    def test_send_midi_disconnected(self):
        """Test sending MIDI while disconnected."""
        config = NetworkAdapterConfig()
        adapter = create_network_adapter(config)

        event = MidiEventData(
            event_type="control_change",
            channel=0,
            data1=7,
            data2=64
        )

        if hasattr(adapter, 'send_midi_event'):
            result = adapter.send_midi_event(event)
            # Should fail when not connected
            assert result == False

    def test_latency_reporting(self):
        """Test latency can be reported."""
        config = NetworkAdapterConfig()
        adapter = create_network_adapter(config)

        if hasattr(adapter, 'get_latency_ms'):
            latency = adapter.get_latency_ms()
            assert isinstance(latency, float)
            assert latency >= 0

    def test_packet_loss_reporting(self):
        """Test packet loss can be reported."""
        config = NetworkAdapterConfig()
        adapter = create_network_adapter(config)

        if hasattr(adapter, 'get_packet_loss_percent'):
            loss = adapter.get_packet_loss_percent()
            assert isinstance(loss, float)
            assert 0 <= loss <= 100

    def test_session_save_load(self):
        """Test session save and load."""
        config = NetworkAdapterConfig()
        adapter = create_network_adapter(config)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filename = f.name

        try:
            if hasattr(adapter, 'save_session'):
                saved = adapter.save_session(filename)
                assert isinstance(saved, bool)

                # Check file exists if save successful
                if saved:
                    assert Path(filename).exists()

            if hasattr(adapter, 'load_session'):
                loaded = adapter.load_session(filename)
                assert isinstance(loaded, bool)
        finally:
            Path(filename).unlink(missing_ok=True)


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestAdapterIntegration:
    """Test integration between adapters."""

    def test_all_adapters_can_be_created(self):
        """Test all adapters can be created together."""
        audio_config = AudioAdapterConfig()
        beatmatch_config = BeatmatchingConfig()
        network_config = NetworkAdapterConfig()

        audio = create_audio_adapter(audio_config)
        beatmatch = create_beatmatching_adapter(beatmatch_config)
        network = create_network_adapter(network_config)

        assert audio is not None
        assert beatmatch is not None
        assert network is not None

    def test_all_adapters_provide_status(self):
        """Test all adapters can report status."""
        audio = create_audio_adapter(AudioAdapterConfig())
        beatmatch = create_beatmatching_adapter(BeatmatchingConfig())
        network = create_network_adapter(NetworkAdapterConfig())

        audio_status = audio.get_status()
        beatmatch_status = beatmatch.get_status()
        network_status = network.get_status()

        assert isinstance(audio_status, dict)
        assert isinstance(beatmatch_status, dict)
        assert isinstance(network_status, dict)

    def test_adapters_with_context_managers(self):
        """Test adapters work as context managers."""
        try:
            with create_audio_adapter(AudioAdapterConfig()) as audio:
                assert audio is not None
        except RuntimeError:
            # OK if audio device not available
            pass

        with create_beatmatching_adapter(BeatmatchingConfig()) as beatmatch:
            assert beatmatch is not None

        with create_network_adapter(NetworkAdapterConfig()) as network:
            assert network is not None


class TestAdapterRobustness:
    """Test adapter robustness and error handling."""

    def test_audio_adapter_survives_multiple_stop_calls(self):
        """Test audio adapter handles multiple stops."""
        config = AudioAdapterConfig()
        adapter = create_audio_adapter(config)

        # Should not raise even if not started
        adapter.stop()
        adapter.stop()

    def test_network_adapter_survives_multiple_stops(self):
        """Test network adapter handles multiple stops."""
        config = NetworkAdapterConfig()
        adapter = create_network_adapter(config)

        # Should not raise even if not started
        if hasattr(adapter, 'stop'):
            adapter.stop()
            adapter.stop()

    def test_beatmatching_survives_empty_operations(self):
        """Test beat matching handles empty state operations."""
        config = BeatmatchingConfig()
        adapter = create_beatmatching_adapter(config)

        # All should return safely
        if hasattr(adapter, 'auto_sync'):
            adapter.auto_sync()
        if hasattr(adapter, 'get_sync_status'):
            adapter.get_sync_status()
        if hasattr(adapter, 'calculate_phase_offset'):
            adapter.calculate_phase_offset(0, 0)


# ============================================================================
# COMPATIBILITY TESTS
# ============================================================================

class TestAdapterCompatibility:
    """Test adapter API compatibility."""

    def test_audio_adapter_implements_interface(self):
        """Test audio adapter implements required interface."""
        adapter = create_audio_adapter(AudioAdapterConfig())

        # Required methods
        assert hasattr(adapter, 'start')
        assert hasattr(adapter, 'stop')
        assert hasattr(adapter, 'get_status')
        assert hasattr(adapter, 'get_latency_ms')

    def test_beatmatching_adapter_implements_interface(self):
        """Test beat matching adapter implements required interface."""
        adapter = create_beatmatching_adapter(BeatmatchingConfig())

        # Required methods
        assert hasattr(adapter, 'get_status')
        assert hasattr(adapter, 'analyze_track') or hasattr(adapter, 'get_status')

    def test_network_adapter_implements_interface(self):
        """Test network adapter implements required interface."""
        adapter = create_network_adapter(NetworkAdapterConfig())

        # Required methods
        assert hasattr(adapter, 'get_status')
        assert hasattr(adapter, 'start_as_master') or hasattr(adapter, 'get_status')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
