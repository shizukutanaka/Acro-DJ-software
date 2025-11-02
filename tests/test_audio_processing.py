# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""Tests for audio processing and DSP functions.

Tests for audio effects, filtering, and signal processing.
"""

from __future__ import annotations

import numpy as np
import pytest

from audio_processing import (
    AudioProcessor,
    SimpleEQ,
    CompressorEffect,
    ReverbEffect,
    TimeStretchProcessor,
    FrequencyAnalyzer,
)


class TestAudioProcessor:
    """Test basic audio processor."""

    def test_processor_creation(self):
        """Test creating processor."""
        processor = AudioProcessor(sample_rate=44100)
        assert processor.sample_rate == 44100

    def test_normalize_audio(self, sample_audio: np.ndarray):
        """Test audio normalization."""
        processor = AudioProcessor()

        # Scale audio
        scaled = sample_audio * 0.5
        normalized = processor.normalize(scaled, target_level=0.9)

        assert np.max(np.abs(normalized)) <= 0.95
        assert normalized.dtype == np.float32

    def test_apply_gain(self, sample_audio: np.ndarray):
        """Test applying gain."""
        processor = AudioProcessor()

        # Apply 6dB gain
        result = processor.apply_gain(sample_audio, gain_db=6)

        assert result.shape == sample_audio.shape
        # Should be ~2x louder (6dB)
        ratio = np.max(np.abs(result)) / np.max(np.abs(sample_audio))
        assert ratio > 1.9 and ratio < 2.1

    def test_fade_in_out(self, sample_audio: np.ndarray):
        """Test fade in/out."""
        processor = AudioProcessor()

        result = processor.apply_fade(sample_audio, fade_type="in", duration_ms=100)

        # First sample should be near 0
        assert result[0] < 0.1 * np.max(np.abs(sample_audio))
        # Last sample should be full
        assert result[-1] > 0.9 * np.max(np.abs(sample_audio))

    def test_clip_audio(self, sample_audio: np.ndarray):
        """Test soft clipping."""
        processor = AudioProcessor()

        scaled = sample_audio * 5  # Clip heavily
        clipped = processor.soft_clip(scaled, threshold=1.0)

        assert np.max(np.abs(clipped)) <= 1.1
        assert clipped.dtype == np.float32

    def test_mix_audio(self, sample_audio: np.ndarray, stereo_audio: np.ndarray):
        """Test mixing audio."""
        processor = AudioProcessor()

        # Mix two signals
        mixed = processor.mix([sample_audio, sample_audio], weights=[0.5, 0.5])

        assert mixed.shape == sample_audio.shape
        # Should be similar to original since we mixed same signal at 50%
        assert np.allclose(mixed, sample_audio, atol=0.01)


class TestSimpleEQ:
    """Test simple EQ filter."""

    def test_eq_creation(self):
        """Test creating EQ."""
        eq = SimpleEQ(sample_rate=44100)
        assert eq.sample_rate == 44100

    def test_set_bass_boost(self, sample_audio: np.ndarray):
        """Test bass boost."""
        eq = SimpleEQ(sample_rate=44100)

        result = eq.set_band(band="bass", gain_db=6)
        assert result is not None

        processed = eq.process(sample_audio)
        assert processed.dtype == np.float32

    def test_set_mid_cut(self, sample_audio: np.ndarray):
        """Test mid cut."""
        eq = SimpleEQ(sample_rate=44100)

        eq.set_band(band="mid", gain_db=-3)
        processed = eq.process(sample_audio)

        assert processed.shape == sample_audio.shape

    def test_set_treble_boost(self, sample_audio: np.ndarray):
        """Test treble boost."""
        eq = SimpleEQ(sample_rate=44100)

        eq.set_band(band="treble", gain_db=6)
        processed = eq.process(sample_audio)

        assert processed.dtype == np.float32

    def test_get_band_settings(self):
        """Test getting band settings."""
        eq = SimpleEQ(sample_rate=44100)

        eq.set_band(band="bass", gain_db=6)
        settings = eq.get_band_settings()

        assert "bass" in settings
        assert settings["bass"]["gain_db"] == 6

    def test_reset_eq(self, sample_audio: np.ndarray):
        """Test resetting EQ."""
        eq = SimpleEQ(sample_rate=44100)

        eq.set_band(band="bass", gain_db=12)
        eq.reset()

        result = eq.process(sample_audio)
        # Should be similar to input when reset
        assert np.allclose(result, sample_audio, atol=0.1)


class TestCompressorEffect:
    """Test compressor effect."""

    def test_compressor_creation(self):
        """Test creating compressor."""
        comp = CompressorEffect(sample_rate=44100)
        assert comp.threshold == -20.0
        assert comp.ratio == 4.0

    def test_compress_audio(self, sample_audio: np.ndarray):
        """Test audio compression."""
        comp = CompressorEffect(
            sample_rate=44100,
            threshold=-20,
            ratio=4,
            attack_ms=10,
            release_ms=100,
        )

        result = comp.process(sample_audio * 0.5)  # Scale to trigger compression

        assert result.shape == sample_audio.shape
        assert result.dtype == np.float32

    def test_set_threshold(self):
        """Test setting threshold."""
        comp = CompressorEffect(sample_rate=44100)

        comp.set_threshold(-15)
        assert comp.threshold == -15

    def test_set_ratio(self):
        """Test setting compression ratio."""
        comp = CompressorEffect(sample_rate=44100)

        comp.set_ratio(8)
        assert comp.ratio == 8

    def test_set_attack_release(self):
        """Test setting attack and release."""
        comp = CompressorEffect(sample_rate=44100)

        comp.set_attack_ms(5)
        comp.set_release_ms(200)

        assert comp.attack_samples > 0
        assert comp.release_samples > 0

    def test_makeup_gain(self, sample_audio: np.ndarray):
        """Test makeup gain."""
        comp = CompressorEffect(
            sample_rate=44100,
            threshold=-20,
            makeup_gain_db=10,
        )

        result = comp.process(sample_audio)
        # With makeup gain, output should be boosted
        assert np.max(np.abs(result)) > np.max(np.abs(sample_audio))


class TestReverbEffect:
    """Test reverb effect."""

    def test_reverb_creation(self):
        """Test creating reverb."""
        reverb = ReverbEffect(sample_rate=44100)
        assert reverb.sample_rate == 44100

    def test_set_room_size(self):
        """Test setting room size."""
        reverb = ReverbEffect(sample_rate=44100)

        reverb.set_room_size(0.8)
        assert reverb.room_size == 0.8

    def test_set_damping(self):
        """Test setting damping."""
        reverb = ReverbEffect(sample_rate=44100)

        reverb.set_damping(0.5)
        assert reverb.damping == 0.5

    def test_set_wet_dry_mix(self):
        """Test setting wet/dry mix."""
        reverb = ReverbEffect(sample_rate=44100)

        reverb.set_wet_dry(wet=0.3, dry=0.7)
        assert reverb.wet_level == 0.3
        assert reverb.dry_level == 0.7

    def test_process_with_reverb(self, sample_audio: np.ndarray):
        """Test processing with reverb."""
        reverb = ReverbEffect(
            sample_rate=44100,
            room_size=0.7,
            damping=0.5,
        )

        result = reverb.process(sample_audio)

        assert result.shape[0] >= sample_audio.shape[0]  # May be longer due to tail
        assert result.dtype == np.float32


class TestTimeStretchProcessor:
    """Test time stretching."""

    def test_time_stretch_creation(self):
        """Test creating time stretch processor."""
        ts = TimeStretchProcessor(sample_rate=44100)
        assert ts.sample_rate == 44100

    def test_stretch_tempo(self, sample_audio: np.ndarray):
        """Test stretching tempo."""
        ts = TimeStretchProcessor(sample_rate=44100)

        # Slow down by 20%
        result = ts.stretch(sample_audio, tempo_ratio=0.8)

        assert len(result) > len(sample_audio)
        assert result.dtype == np.float32

    def test_time_stretch_pitch_shift(self, sample_audio: np.ndarray):
        """Test time stretch with pitch shift."""
        ts = TimeStretchProcessor(sample_rate=44100)

        # Speed up by 50% without changing pitch
        result = ts.stretch(sample_audio, tempo_ratio=1.5, preserve_pitch=True)

        assert len(result) < len(sample_audio)

    def test_large_stretch_ratio(self, sample_audio: np.ndarray):
        """Test large stretch ratio."""
        ts = TimeStretchProcessor(sample_rate=44100)

        # 2x slower
        result = ts.stretch(sample_audio, tempo_ratio=0.5)

        assert len(result) > len(sample_audio) * 1.8


class TestFrequencyAnalyzer:
    """Test frequency analysis."""

    def test_analyzer_creation(self):
        """Test creating analyzer."""
        analyzer = FrequencyAnalyzer(sample_rate=44100)
        assert analyzer.sample_rate == 44100

    def test_compute_spectrum(self, sample_audio: np.ndarray):
        """Test computing spectrum."""
        analyzer = FrequencyAnalyzer(sample_rate=44100)

        spectrum = analyzer.compute_spectrum(sample_audio)

        assert len(spectrum) > 0
        assert np.all(spectrum >= 0)  # Magnitude should be positive

    def test_get_peak_frequency(self, sample_audio: np.ndarray):
        """Test getting peak frequency."""
        analyzer = FrequencyAnalyzer(sample_rate=44100)

        peak_freq = analyzer.get_peak_frequency(sample_audio)

        # For 440Hz sine wave, peak should be around 440Hz
        assert 400 < peak_freq < 480

    def test_compute_mfcc(self, sample_audio: np.ndarray):
        """Test MFCC computation."""
        analyzer = FrequencyAnalyzer(sample_rate=44100)

        mfcc = analyzer.compute_mfcc(sample_audio, n_mfcc=13)

        assert mfcc.shape[0] == 13
        assert mfcc.shape[1] > 0

    def test_detect_silence(self, silence: np.ndarray, sample_audio: np.ndarray):
        """Test silence detection."""
        analyzer = FrequencyAnalyzer(sample_rate=44100)

        # Should detect silence
        assert analyzer.is_silent(silence, threshold_db=-40)

        # Should not detect signal as silence
        assert not analyzer.is_silent(sample_audio, threshold_db=-40)

    def test_get_energy_by_band(self, sample_audio: np.ndarray):
        """Test energy by frequency band."""
        analyzer = FrequencyAnalyzer(sample_rate=44100)

        energy = analyzer.get_energy_by_band(sample_audio, n_bands=10)

        assert len(energy) == 10
        assert np.all(energy >= 0)

    def test_spectral_centroid(self, sample_audio: np.ndarray):
        """Test spectral centroid."""
        analyzer = FrequencyAnalyzer(sample_rate=44100)

        centroid = analyzer.spectral_centroid(sample_audio)

        assert 0 < centroid < 22050  # Nyquist frequency


class TestAudioProcessingIntegration:
    """Integration tests for audio processing."""

    def test_multi_effect_chain(self, sample_audio: np.ndarray):
        """Test applying multiple effects."""
        # Apply EQ -> Compressor -> Reverb chain
        eq = SimpleEQ(sample_rate=44100)
        comp = CompressorEffect(sample_rate=44100)
        reverb = ReverbEffect(sample_rate=44100)

        audio = sample_audio
        audio = eq.process(audio)
        audio = comp.process(audio)
        audio = reverb.process(audio)

        assert audio.dtype == np.float32

    def test_time_stretch_and_pitch_shift(self, sample_audio: np.ndarray):
        """Test time stretching with pitch preservation."""
        ts = TimeStretchProcessor(sample_rate=44100)

        # Stretch tempo without changing pitch
        result = ts.stretch(sample_audio, tempo_ratio=1.2, preserve_pitch=True)

        assert result.dtype == np.float32

    def test_frequency_analysis_on_processed_audio(self, sample_audio: np.ndarray):
        """Test frequency analysis after processing."""
        eq = SimpleEQ(sample_rate=44100)
        eq.set_band(band="bass", gain_db=6)
        processed = eq.process(sample_audio)

        analyzer = FrequencyAnalyzer(sample_rate=44100)
        spectrum = analyzer.compute_spectrum(processed)

        assert len(spectrum) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
