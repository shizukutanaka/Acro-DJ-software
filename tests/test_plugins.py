# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Comprehensive tests for Acro DJ Mixer plugin system.

Tests cover:
- Plugin loading and registration
- Audio effect processing
- Library analysis
- Parameter validation
- Plugin manager lifecycle
- Integration between plugins
"""

import pytest
import numpy as np
from pathlib import Path
import sys

# Add plugins to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from plugins.plugin_api import (
    PluginManager, PluginMetadata, PluginCategory, Parameter,
    AudioEffectPlugin, LibraryToolPlugin, AnalyzerPlugin
)
from plugins.library_management import LibraryAnalyzer, CuePoint, DetectionType
from plugins.professional_eq import ProfessionalEQ, EQPreset, EQBand
from plugins.multi_effect_processor import (
    MultiEffectProcessor, EffectType, ReverbSettings, DelaySettings,
    FilterSettings, FilterMode, DistortionSettings
)


class TestPluginMetadata:
    """Test plugin metadata."""

    def test_metadata_creation(self):
        """Test creating plugin metadata."""
        metadata = PluginMetadata(
            name="Test Plugin",
            version="1.0.0",
            author="Test Author",
            description="Test description",
            category=PluginCategory.AUDIO_EFFECT,
        )

        assert metadata.name == "Test Plugin"
        assert metadata.version == "1.0.0"
        assert metadata.category == PluginCategory.AUDIO_EFFECT

    def test_metadata_to_dict(self):
        """Test converting metadata to dict."""
        metadata = PluginMetadata(
            name="Test",
            version="1.0.0",
            author="Author",
            description="Desc",
            category=PluginCategory.AUDIO_EFFECT,
        )

        data = metadata.to_dict()
        assert data['name'] == "Test"
        assert data['version'] == "1.0.0"
        assert data['category'] == "audio_effect"


class TestPluginParameter:
    """Test plugin parameter system."""

    def test_parameter_creation(self):
        """Test creating a parameter."""
        param = Parameter(
            name='gain',
            value_type=float,
            default_value=0.0,
            min_value=-12.0,
            max_value=12.0,
            description='Gain in dB',
        )

        assert param.name == 'gain'
        assert param.default_value == 0.0

    def test_parameter_validation(self):
        """Test parameter validation."""
        param = Parameter(
            name='gain',
            value_type=float,
            default_value=0.0,
            min_value=-12.0,
            max_value=12.0,
        )

        assert param.validate(0.0) is True
        assert param.validate(6.0) is True
        assert param.validate(-12.0) is True
        assert param.validate(15.0) is False  # Out of range
        assert param.validate("invalid") is False  # Wrong type

    def test_parameter_to_dict(self):
        """Test converting parameter to dict."""
        param = Parameter(
            name='gain',
            value_type=float,
            default_value=0.0,
            min_value=-12.0,
            max_value=12.0,
            description='Gain',
        )

        data = param.to_dict()
        assert data['name'] == 'gain'
        assert data['default_value'] == 0.0
        assert data['value_type'] == 'float'


class TestLibraryAnalyzer:
    """Test library analysis plugin."""

    def test_analyzer_initialization(self):
        """Test initializing library analyzer."""
        analyzer = LibraryAnalyzer()
        assert analyzer.max_workers == 4

    def test_bpm_detection(self):
        """Test BPM detection on synthetic audio."""
        analyzer = LibraryAnalyzer()

        # Generate synthetic audio at known BPM (120 BPM = 2 beats per second)
        sample_rate = 44100
        duration = 10  # seconds
        bpm = 120.0
        beat_interval = sample_rate / (bpm / 60.0)

        # Create audio with impulses at beat times
        audio = np.zeros(duration * sample_rate)
        for i in range(int(duration * bpm / 60)):
            idx = int(i * beat_interval)
            if idx < len(audio):
                audio[idx] = 1.0

        # Detect BPM
        detected_bpm, confidence = analyzer._detect_bpm(audio, sample_rate)

        # Should be close to 120 BPM (allow ±20 BPM tolerance)
        assert 100 <= detected_bpm <= 140
        assert confidence > 0.0

    def test_key_detection(self):
        """Test musical key detection."""
        analyzer = LibraryAnalyzer()

        # Generate synthetic audio
        sample_rate = 44100
        duration = 5
        frequency = 440  # A4

        # Generate sine wave
        t = np.linspace(0, duration, int(duration * sample_rate))
        audio = np.sin(2 * np.pi * frequency * t).astype(np.float32)

        # Detect key
        key, confidence = analyzer._detect_key(audio, sample_rate)

        assert key is not None
        assert 0.0 <= confidence <= 1.0

    def test_cue_point_detection(self):
        """Test cue point detection."""
        analyzer = LibraryAnalyzer()

        # Generate synthetic audio with energy changes
        sample_rate = 44100
        duration = 20
        audio = np.zeros(duration * sample_rate, dtype=np.float32)

        # Add energy peaks to simulate drops
        for drop_time in [5, 10, 15]:
            start_idx = int(drop_time * sample_rate)
            end_idx = min(int((drop_time + 1) * sample_rate), len(audio))
            audio[start_idx:end_idx] = np.random.randn(end_idx - start_idx) * 0.5

        # Detect cue points
        cue_points = analyzer._detect_cue_points(audio, sample_rate, 120.0)

        # Should detect intro, drops, and outro
        assert len(cue_points) > 0
        assert any(cp.detection_type == DetectionType.INTRO for cp in cue_points)
        assert any(cp.detection_type == DetectionType.OUTRO for cp in cue_points)


class TestProfessionalEQ:
    """Test professional EQ plugin."""

    def test_eq_initialization(self):
        """Test EQ initialization."""
        eq = ProfessionalEQ(sample_rate=44100, num_bands=10)

        assert eq.sample_rate == 44100
        assert len(eq.bands) == 10

    def test_eq_preset_loading(self):
        """Test loading EQ presets."""
        eq = ProfessionalEQ()

        for preset_name in ['Flat', 'House', 'Techno', 'Hip-Hop']:
            eq.load_preset(preset_name)
            assert len(eq.bands) > 0
            assert eq.bands[0].frequency > 0

    def test_eq_gain_setting(self):
        """Test setting EQ gain."""
        eq = ProfessionalEQ()

        eq.set_band_gain(0, 6.0)
        assert eq.bands[0].gain_db == 6.0

        # Test clamping
        eq.set_band_gain(0, 20.0)  # Out of range
        assert eq.bands[0].gain_db == 12.0  # Should be clamped

    def test_eq_processing(self):
        """Test EQ audio processing."""
        eq = ProfessionalEQ(sample_rate=44100)

        # Generate test audio
        audio = np.random.randn(44100).astype(np.float32) * 0.1

        # Process through EQ
        output = eq.process_audio(audio)

        assert output.shape == audio.shape
        assert np.isfinite(output).all()  # No NaN/Inf

    def test_eq_frequency_response(self):
        """Test EQ frequency response calculation."""
        eq = ProfessionalEQ()
        eq.set_band_gain(0, 6.0)  # Boost first band

        frequencies = np.array([60, 1000, 5000, 10000])
        response = eq.get_frequency_response(frequencies)

        assert response.shape == frequencies.shape
        assert np.isfinite(response).all()

    def test_eq_state_export(self):
        """Test EQ state export/import."""
        eq1 = ProfessionalEQ()
        eq1.set_band_gain(0, 6.0)
        eq1.set_master_gain(3.0)

        # Export state
        state = eq1.to_dict()

        # Import to new EQ
        eq2 = ProfessionalEQ()
        eq2.from_dict(state)

        assert eq2.bands[0].gain_db == 6.0
        assert eq2.master_gain_db == 3.0


class TestMultiEffectProcessor:
    """Test multi-effect processor plugin."""

    def test_processor_initialization(self):
        """Test processor initialization."""
        processor = MultiEffectProcessor(sample_rate=44100)

        assert processor.sample_rate == 44100
        assert processor.reverb is not None
        assert processor.delay is not None
        assert processor.filter is not None
        assert processor.distortion is not None

    def test_effect_enable_disable(self):
        """Test enabling/disabling effects."""
        processor = MultiEffectProcessor()

        processor.set_effect_enabled(EffectType.REVERB, True)
        assert processor.enabled_effects[EffectType.REVERB] is True

        processor.set_effect_enabled(EffectType.REVERB, False)
        assert processor.enabled_effects[EffectType.REVERB] is False

    def test_effect_chain_ordering(self):
        """Test effect chain ordering."""
        processor = MultiEffectProcessor()

        chain = [EffectType.DISTORTION, EffectType.REVERB, EffectType.DELAY]
        processor.set_effect_chain(chain)

        assert processor.effect_chain == chain

    def test_reverb_settings(self):
        """Test reverb settings."""
        processor = MultiEffectProcessor()

        settings = ReverbSettings(room_size=0.7, damping=0.6, wet_dry_mix=0.4)
        processor.set_reverb_settings(settings)

        retrieved = processor.get_reverb_settings()
        assert retrieved.room_size == 0.7
        assert retrieved.damping == 0.6

    def test_delay_settings(self):
        """Test delay settings."""
        processor = MultiEffectProcessor()

        settings = DelaySettings(delay_time_ms=500, feedback=0.5, wet_dry_mix=0.3)
        processor.set_delay_settings(settings)

        retrieved = processor.get_delay_settings()
        assert retrieved.delay_time_ms == 500
        assert retrieved.feedback == 0.5

    def test_filter_settings(self):
        """Test filter settings."""
        processor = MultiEffectProcessor()

        settings = FilterSettings(mode=FilterMode.LOWPASS, cutoff_hz=5000)
        processor.set_filter_settings(settings)

        retrieved = processor.get_filter_settings()
        assert retrieved.mode == FilterMode.LOWPASS
        assert retrieved.cutoff_hz == 5000

    def test_distortion_settings(self):
        """Test distortion settings."""
        processor = MultiEffectProcessor()

        settings = DistortionSettings(drive=0.7, tone=0.5, soft_clip=True)
        processor.set_distortion_settings(settings)

        retrieved = processor.get_distortion_settings()
        assert retrieved.drive == 0.7
        assert retrieved.soft_clip is True

    def test_effect_processing(self):
        """Test effect chain processing."""
        processor = MultiEffectProcessor()

        # Enable and configure effects
        processor.set_effect_enabled(EffectType.REVERB, True)
        processor.set_effect_enabled(EffectType.DELAY, True)

        processor.set_effect_chain([EffectType.DELAY, EffectType.REVERB])

        # Generate test audio
        audio = np.random.randn(44100).astype(np.float32) * 0.1

        # Process
        output = processor.process(audio)

        assert output.shape == audio.shape
        assert np.isfinite(output).all()

    def test_individual_effects(self):
        """Test individual effects processing."""
        audio = np.random.randn(44100).astype(np.float32) * 0.1

        # Test reverb
        processor = MultiEffectProcessor()
        processor.set_effect_enabled(EffectType.REVERB, True)
        output = processor.process(audio)
        assert output.shape == audio.shape

        # Test delay
        processor.set_effect_enabled(EffectType.REVERB, False)
        processor.set_effect_enabled(EffectType.DELAY, True)
        output = processor.process(audio)
        assert output.shape == audio.shape

        # Test filter
        processor.set_effect_enabled(EffectType.DELAY, False)
        processor.set_effect_enabled(EffectType.FILTER, True)
        output = processor.process(audio)
        assert output.shape == audio.shape

        # Test distortion
        processor.set_effect_enabled(EffectType.FILTER, False)
        processor.set_effect_enabled(EffectType.DISTORTION, True)
        output = processor.process(audio)
        assert output.shape == audio.shape


class TestPluginManager:
    """Test plugin manager."""

    def test_manager_initialization(self):
        """Test plugin manager initialization."""
        manager = PluginManager()

        assert len(manager.plugins) == 0
        assert len(manager.list_plugins()) == 0

    def test_plugin_registration(self):
        """Test registering plugins."""
        manager = PluginManager()

        # Create mock plugin
        metadata = PluginMetadata(
            name="Test Plugin",
            version="1.0.0",
            author="Test",
            description="Test",
            category=PluginCategory.AUDIO_EFFECT,
        )

        plugin = type('TestPlugin', (AudioEffectPlugin,), {
            'process_audio': lambda self, audio: audio,
            'initialize': lambda self, config: None,
            'shutdown': lambda self: None,
        })(metadata)

        manager.register_plugin(plugin)

        assert "Test Plugin" in manager.plugins
        assert len(manager.list_plugins()) == 1

    def test_plugin_retrieval(self):
        """Test retrieving plugins."""
        manager = PluginManager()

        metadata = PluginMetadata(
            name="Test",
            version="1.0.0",
            author="Test",
            description="Test",
            category=PluginCategory.AUDIO_EFFECT,
        )

        plugin = type('TestPlugin', (AudioEffectPlugin,), {
            'process_audio': lambda self, audio: audio,
            'initialize': lambda self, config: None,
            'shutdown': lambda self: None,
        })(metadata)

        manager.register_plugin(plugin)

        retrieved = manager.get_plugin("Test")
        assert retrieved is not None
        assert retrieved.metadata.name == "Test"

    def test_plugin_by_category(self):
        """Test retrieving plugins by category."""
        manager = PluginManager()

        metadata = PluginMetadata(
            name="Test Effect",
            version="1.0.0",
            author="Test",
            description="Test",
            category=PluginCategory.AUDIO_EFFECT,
        )

        plugin = type('TestPlugin', (AudioEffectPlugin,), {
            'process_audio': lambda self, audio: audio,
            'initialize': lambda self, config: None,
            'shutdown': lambda self: None,
        })(metadata)

        manager.register_plugin(plugin)

        effects = manager.get_plugins_by_category(PluginCategory.AUDIO_EFFECT)
        assert len(effects) == 1
        assert effects[0].metadata.name == "Test Effect"


class TestPluginIntegration:
    """Integration tests for plugins working together."""

    def test_library_and_eq_integration(self):
        """Test library analyzer with EQ."""
        # This would test using library analysis results to set EQ

        analyzer = LibraryAnalyzer()
        eq = ProfessionalEQ()

        # Simulate having analyzed a track
        # and using that info to set EQ presets
        eq.load_preset('House')  # Based on track genre

        # Generate test audio
        audio = np.random.randn(44100).astype(np.float32) * 0.1

        # Process
        output = eq.process_audio(audio)

        assert output.shape == audio.shape
        assert np.isfinite(output).all()

    def test_eq_and_effects_integration(self):
        """Test EQ with multi-effect processor."""
        eq = ProfessionalEQ()
        processor = MultiEffectProcessor()

        # Configure both
        eq.load_preset('Techno')
        processor.set_effect_enabled(EffectType.REVERB, True)

        # Generate test audio
        audio = np.random.randn(44100).astype(np.float32) * 0.1

        # Process through EQ then effects
        eq_output = eq.process_audio(audio)
        final_output = processor.process(eq_output)

        assert final_output.shape == audio.shape
        assert np.isfinite(final_output).all()

    def test_all_plugins_together(self):
        """Test all three plugins working together."""
        analyzer = LibraryAnalyzer()
        eq = ProfessionalEQ()
        processor = MultiEffectProcessor()

        # Configure plugins
        eq.load_preset('Hip-Hop')
        processor.set_effect_enabled(EffectType.DISTORTION, True)
        processor.set_effect_enabled(EffectType.DELAY, True)

        # Generate test audio
        audio = np.random.randn(44100).astype(np.float32) * 0.1

        # Process pipeline
        eq_output = eq.process_audio(audio)
        final_output = processor.process(eq_output)

        assert final_output.shape == audio.shape
        assert np.isfinite(final_output).all()


class TestPluginPerformance:
    """Performance tests for plugins."""

    def test_eq_processing_speed(self):
        """Test EQ processing speed."""
        import time

        eq = ProfessionalEQ()
        audio = np.random.randn(44100).astype(np.float32) * 0.1

        start = time.time()
        output = eq.process_audio(audio)
        duration = time.time() - start

        # Should process 1 second of audio in < 100ms
        assert duration < 0.1, f"EQ processing too slow: {duration}s"

    def test_processor_processing_speed(self):
        """Test processor speed."""
        import time

        processor = MultiEffectProcessor()
        processor.set_effect_enabled(EffectType.REVERB, True)
        processor.set_effect_enabled(EffectType.DELAY, True)

        audio = np.random.randn(44100).astype(np.float32) * 0.1

        start = time.time()
        output = processor.process(audio)
        duration = time.time() - start

        # Should process 1 second of audio in < 200ms
        assert duration < 0.2, f"Effect processing too slow: {duration}s"

    def test_analyzer_performance(self):
        """Test analyzer performance."""
        import time

        analyzer = LibraryAnalyzer()

        # Generate test audio
        audio = np.random.randn(int(44100 * 10)).astype(np.float32) * 0.1

        start = time.time()
        bpm, confidence = analyzer._detect_bpm(audio, 44100)
        duration = time.time() - start

        # Should analyze in reasonable time
        assert duration < 5.0, f"BPM detection too slow: {duration}s"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
