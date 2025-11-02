# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Professional EQ Plugin for Acro DJ Mixer v3.x

Features:
- 10-band parametric equalizer
- Real-time frequency spectrum display
- Professional presets (House, Techno, Hip-Hop, etc.)
- Full gain adjustment (-12dB to +12dB per band)
- Frequency sweep and Q factor control
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import numpy as np
from scipy.signal import butter, sosfilt
import logging

logger = logging.getLogger(__name__)


@dataclass
class EQBand:
    """Represents a single EQ band."""
    frequency: float           # Center frequency in Hz
    gain_db: float            # Gain in dB (-12 to +12)
    q_factor: float = 1.0     # Q factor (bandwidth control, 0.1-10)
    active: bool = True       # Whether band is enabled
    name: str = ""            # Optional band name

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'frequency': float(self.frequency),
            'gain_db': float(self.gain_db),
            'q_factor': float(self.q_factor),
            'active': self.active,
            'name': self.name,
        }


@dataclass
class EQPreset:
    """Represents a complete EQ preset."""
    name: str
    description: str
    bands: List[EQBand] = field(default_factory=list)
    master_gain_db: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'description': self.description,
            'bands': [b.to_dict() for b in self.bands],
            'master_gain_db': float(self.master_gain_db),
        }


class ProfessionalEQ:
    """Professional 10-band parametric equalizer."""

    # Standard 10-band EQ frequencies
    STANDARD_FREQUENCIES = [60, 150, 250, 500, 1000, 2000, 4000, 8000, 12000, 16000]

    # Presets for different music genres
    PRESETS = {
        'Flat': EQPreset(
            name='Flat',
            description='No equalization (neutral)',
            bands=[EQBand(f, 0.0) for f in STANDARD_FREQUENCIES],
        ),
        'House': EQPreset(
            name='House',
            description='Boost lows and mids for deep house',
            bands=[
                EQBand(60, 4.0, name='Sub Bass'),
                EQBand(150, 3.0, name='Bass'),
                EQBand(250, 2.0, name='Low Mid'),
                EQBand(500, 1.0, name='Warm'),
                EQBand(1000, 0.0),
                EQBand(2000, 0.0),
                EQBand(4000, 1.0, name='Presence'),
                EQBand(8000, 0.5),
                EQBand(12000, -1.0),
                EQBand(16000, -2.0, name='High Shine'),
            ],
        ),
        'Techno': EQPreset(
            name='Techno',
            description='Aggressive lows, reduced mids',
            bands=[
                EQBand(60, 6.0, name='Sub Bass'),
                EQBand(150, 3.0, name='Kick'),
                EQBand(250, -2.0, name='Mudd'),
                EQBand(500, -1.5, name='Boxiness'),
                EQBand(1000, -1.0),
                EQBand(2000, 0.0),
                EQBand(4000, 2.0, name='Presence'),
                EQBand(8000, 2.5, name='Air'),
                EQBand(12000, 1.0),
                EQBand(16000, 1.5, name='Brilliance'),
            ],
        ),
        'Hip-Hop': EQPreset(
            name='Hip-Hop',
            description='Punchy kicks, prominent vocals',
            bands=[
                EQBand(60, 3.0, name='Sub'),
                EQBand(150, 2.0, name='Kick'),
                EQBand(250, 0.0),
                EQBand(500, 0.5, name='Warmth'),
                EQBand(1000, 1.5, name='Vocal Presence'),
                EQBand(2000, 2.0, name='Intelligibility'),
                EQBand(4000, 1.5, name='Presence'),
                EQBand(8000, 1.0, name='Clarity'),
                EQBand(12000, 0.0),
                EQBand(16000, -1.0),
            ],
        ),
        'Deep House': EQPreset(
            name='Deep House',
            description='Warm, smooth lows',
            bands=[
                EQBand(60, 2.5, name='Sub'),
                EQBand(150, 2.0, name='Bass'),
                EQBand(250, 1.5, name='Full'),
                EQBand(500, 1.0, name='Warmth'),
                EQBand(1000, -0.5),
                EQBand(2000, -1.0, name='Muddiness Cut'),
                EQBand(4000, 0.5),
                EQBand(8000, 0.0),
                EQBand(12000, -0.5),
                EQBand(16000, -1.0),
            ],
        ),
        'Vocal Boost': EQPreset(
            name='Vocal Boost',
            description='Highlight vocals and presence',
            bands=[
                EQBand(60, -1.0),
                EQBand(150, -1.0),
                EQBand(250, -0.5),
                EQBand(500, 0.5),
                EQBand(1000, 2.0, name='Vocal Presence'),
                EQBand(2000, 3.0, name='Clarity'),
                EQBand(4000, 2.5, name='Presence'),
                EQBand(8000, 1.5),
                EQBand(12000, 0.5),
                EQBand(16000, -1.0),
            ],
        ),
        'Bass Boost': EQPreset(
            name='Bass Boost',
            description='Enhance low frequencies',
            bands=[
                EQBand(60, 6.0, name='Sub'),
                EQBand(150, 4.0, name='Bass'),
                EQBand(250, 2.0),
                EQBand(500, 1.0),
                EQBand(1000, 0.0),
                EQBand(2000, -0.5),
                EQBand(4000, -1.0),
                EQBand(8000, -1.5),
                EQBand(12000, -2.0),
                EQBand(16000, -2.0),
            ],
        ),
    }

    def __init__(self, sample_rate: int = 44100, num_bands: int = 10):
        """Initialize professional EQ.

        Args:
            sample_rate: Audio sample rate in Hz
            num_bands: Number of EQ bands
        """
        self.sample_rate = sample_rate
        self.num_bands = num_bands
        self.bands: List[EQBand] = [
            EQBand(f, 0.0) for f in self.STANDARD_FREQUENCIES[:num_bands]
        ]
        self.master_gain_db = 0.0
        self._filter_cache = {}

    def set_band_gain(self, band_index: int, gain_db: float) -> None:
        """Set gain for a specific band.

        Args:
            band_index: Index of the band (0-9)
            gain_db: Gain in dB (-12 to +12)
        """
        if 0 <= band_index < len(self.bands):
            gain_db = np.clip(gain_db, -12.0, 12.0)
            self.bands[band_index].gain_db = gain_db
            self._filter_cache.clear()  # Clear cache

    def set_band_frequency(self, band_index: int, frequency: float) -> None:
        """Set center frequency for a specific band.

        Args:
            band_index: Index of the band (0-9)
            frequency: Frequency in Hz (20-20000)
        """
        if 0 <= band_index < len(self.bands):
            frequency = np.clip(frequency, 20, 20000)
            self.bands[band_index].frequency = frequency
            self._filter_cache.clear()

    def set_band_q(self, band_index: int, q_factor: float) -> None:
        """Set Q factor (bandwidth) for a specific band.

        Args:
            band_index: Index of the band (0-9)
            q_factor: Q factor (0.1-10.0)
        """
        if 0 <= band_index < len(self.bands):
            q_factor = np.clip(q_factor, 0.1, 10.0)
            self.bands[band_index].q_factor = q_factor
            self._filter_cache.clear()

    def set_band_active(self, band_index: int, active: bool) -> None:
        """Enable/disable a specific band.

        Args:
            band_index: Index of the band (0-9)
            active: Whether to enable the band
        """
        if 0 <= band_index < len(self.bands):
            self.bands[band_index].active = active
            self._filter_cache.clear()

    def set_master_gain(self, gain_db: float) -> None:
        """Set master output gain.

        Args:
            gain_db: Gain in dB (-12 to +12)
        """
        self.master_gain_db = np.clip(gain_db, -12.0, 12.0)

    def load_preset(self, preset_name: str) -> None:
        """Load a preset configuration.

        Args:
            preset_name: Name of preset ('Flat', 'House', 'Techno', etc.)
        """
        if preset_name not in self.PRESETS:
            logger.warning(f"Preset '{preset_name}' not found")
            return

        preset = self.PRESETS[preset_name]
        self.bands = [
            EQBand(
                frequency=b.frequency,
                gain_db=b.gain_db,
                q_factor=b.q_factor,
                active=b.active,
                name=b.name,
            )
            for b in preset.bands
        ]
        self.master_gain_db = preset.master_gain_db
        self._filter_cache.clear()

    def get_available_presets(self) -> List[str]:
        """Get list of available preset names."""
        return list(self.PRESETS.keys())

    def process_audio(self, audio: np.ndarray) -> np.ndarray:
        """Apply EQ to audio signal.

        Args:
            audio: Audio samples as numpy array

        Returns:
            Processed audio signal
        """
        if len(audio) == 0:
            return audio

        output = audio.copy().astype(np.float32)

        # Apply each active band
        for i, band in enumerate(self.bands):
            if not band.active or abs(band.gain_db) < 0.01:
                continue

            try:
                # Design filter for this band
                sos = self._design_peaking_filter(
                    frequency=band.frequency,
                    gain_db=band.gain_db,
                    q_factor=band.q_factor
                )

                # Apply filter
                output = sosfilt(sos, output)

            except Exception as e:
                logger.warning(f"Failed to apply band {i}: {e}")

        # Apply master gain
        if abs(self.master_gain_db) > 0.01:
            gain_linear = 10.0 ** (self.master_gain_db / 20.0)
            output = output * gain_linear

        # Soft clipping to prevent distortion
        output = np.tanh(output)

        return output

    def _design_peaking_filter(
        self,
        frequency: float,
        gain_db: float,
        q_factor: float
    ) -> np.ndarray:
        """Design a peaking EQ filter using SOS format.

        Args:
            frequency: Center frequency in Hz
            gain_db: Gain in dB
            q_factor: Q factor (bandwidth)

        Returns:
            Second-order sections array for scipy.signal.sosfilt
        """
        # Normalize frequency to Nyquist
        nyquist = self.sample_rate / 2.0
        w0 = 2.0 * np.pi * frequency / self.sample_rate

        # Calculate filter coefficients
        alpha = np.sin(w0) / (2.0 * q_factor)
        A = 10.0 ** (gain_db / 40.0)

        b0 = 1.0 + alpha * A
        b1 = -2.0 * np.cos(w0)
        b2 = 1.0 - alpha * A
        a0 = 1.0 + alpha / A
        a1 = -2.0 * np.cos(w0)
        a2 = 1.0 - alpha / A

        # Normalize
        b = np.array([b0/a0, b1/a0, b2/a0])
        a = np.array([1.0, a1/a0, a2/a0])

        # Convert to SOS format
        sos = np.array([[b[0], b[1], b[2], 1.0, a[1], a[2]]])

        return sos

    def get_frequency_response(self, frequencies: np.ndarray) -> np.ndarray:
        """Calculate frequency response magnitude at specified frequencies.

        Args:
            frequencies: Array of frequencies in Hz

        Returns:
            Magnitude response in dB
        """
        magnitude_db = np.zeros_like(frequencies, dtype=float)

        for band in self.bands:
            if not band.active:
                continue

            # Simplified peaking filter response
            df = frequencies - band.frequency
            magnitude_db += band.gain_db / (1.0 + (2.0 * df / band.frequency / band.q_factor)**2)

        # Add master gain
        magnitude_db += self.master_gain_db

        return magnitude_db

    def to_dict(self) -> dict:
        """Export EQ state to dictionary."""
        return {
            'bands': [b.to_dict() for b in self.bands],
            'master_gain_db': float(self.master_gain_db),
            'sample_rate': int(self.sample_rate),
        }

    def from_dict(self, data: dict) -> None:
        """Import EQ state from dictionary."""
        self.master_gain_db = data.get('master_gain_db', 0.0)

        bands_data = data.get('bands', [])
        self.bands = []
        for b_data in bands_data:
            self.bands.append(EQBand(
                frequency=b_data['frequency'],
                gain_db=b_data['gain_db'],
                q_factor=b_data.get('q_factor', 1.0),
                active=b_data.get('active', True),
                name=b_data.get('name', ''),
            ))

        self._filter_cache.clear()
