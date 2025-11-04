# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Music Mood & Energy Classification

Provides AI-powered automatic track characterization:
- Energy level detection (1-10 scale)
- Mood classification (happy, dark, groovy, chill, etc.)
- Danceability analysis
- Sentiment analysis from audio features
- Spotify API integration option
- Real-time metadata enrichment
"""

import logging
import numpy as np
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
from threading import Lock
import json

logger = logging.getLogger(__name__)

# Optional dependencies
try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    logger.warning("librosa not installed. Limited feature extraction. "
                  "Install with: pip install librosa")

try:
    import spotipy
    SPOTIFY_AVAILABLE = True
except ImportError:
    SPOTIFY_AVAILABLE = False
    logger.warning("spotipy not installed. Spotify API unavailable. "
                  "Install with: pip install spotipy")


class MoodType(Enum):
    """Music mood classification."""
    HAPPY = "happy"          # Uplifting, positive, major key
    DARK = "dark"            # Minor key, low energy, mysterious
    GROOVY = "groovy"        # Rhythmic, funky, groove-oriented
    CHILL = "chill"          # Relaxed, smooth, easy listening
    ENERGETIC = "energetic"  # High BPM, intense, aggressive
    MELODIC = "melodic"      # Focus on melody, harmonic
    ATMOSPHERIC = "atmospheric"  # Ambient, sparse, reverb-heavy
    PERCUSSIVE = "percussive"    # Drum-heavy, rhythm-focused
    VOCAL_FOCUSED = "vocal"  # Strong vocal content
    INSTRUMENTAL = "instrumental"  # No or minimal vocals


@dataclass
class MoodAnalysis:
    """Complete mood analysis result."""
    energy_level: int  # 1-10
    primary_mood: MoodType
    mood_confidence: float  # 0.0-1.0
    mood_probabilities: Dict[MoodType, float]  # All mood scores
    danceability: float  # 0.0-1.0
    valence: float      # 0.0-1.0 (positive/negative sentiment)
    arousal: float      # 0.0-1.0 (calm to intense)
    has_vocals: bool
    is_instrumental: bool
    genre_tags: List[str]
    processing_time_ms: float


class AudioFeatureExtractor:
    """
    Extracts audio features for mood classification.
    """

    def __init__(self, sr: int = 44100):
        """
        Initialize feature extractor.

        Args:
            sr: Sample rate
        """
        self.sr = sr
        self.lock = Lock()

    def extract_features(self, audio: np.ndarray) -> Dict[str, float]:
        """
        Extract mood-relevant audio features.

        Args:
            audio: Audio samples

        Returns:
            Dictionary of features
        """
        if audio.ndim == 2:
            audio = np.mean(audio, axis=0)

        features = {}

        # Basic time-domain features
        features['rms_energy'] = float(np.sqrt(np.mean(audio ** 2)))
        features['peak_amplitude'] = float(np.max(np.abs(audio)))
        features['zero_crossing_rate'] = float(self._compute_zcr(audio))

        if not LIBROSA_AVAILABLE:
            return features

        try:
            # Frequency-domain features
            spec = np.abs(librosa.stft(audio))
            spec_db = librosa.power_to_db(spec ** 2, ref=np.max)

            # Spectral features
            features['spectral_centroid'] = float(np.mean(
                librosa.feature.spectral_centroid(S=spec_db, sr=self.sr)
            ))
            features['spectral_rolloff'] = float(np.mean(
                librosa.feature.spectral_rolloff(S=spec_db, sr=self.sr)
            ))

            # Temporal features
            onset_env = librosa.onset.onset_strength(y=audio, sr=self.sr)
            features['onset_strength'] = float(np.mean(onset_env))
            features['onset_variance'] = float(np.var(onset_env))

            # Chroma features (key/harmonic content)
            chroma = librosa.feature.chroma_stft(y=audio, sr=self.sr)
            features['chroma_variance'] = float(np.var(chroma))

            # MFCC (Mel-Frequency Cepstral Coefficients)
            mfcc = librosa.feature.mfcc(y=audio, sr=self.sr, n_mfcc=13)
            features['mfcc_mean'] = float(np.mean(mfcc))
            features['mfcc_std'] = float(np.std(mfcc))

            # Tempogram for rhythm
            tempogram = librosa.feature.tempogram(y=audio, sr=self.sr)
            features['rhythm_regularity'] = float(np.mean(np.max(tempogram, axis=0)))

        except Exception as e:
            logger.warning(f"Librosa feature extraction partial: {e}")

        return features

    def _compute_zcr(self, audio: np.ndarray) -> float:
        """Compute zero-crossing rate."""
        zcr = np.mean(librosa.feature.zero_crossing_rate(audio))
        return float(zcr)


class SimpleRuleBasedMoodClassifier:
    """
    Simple rule-based mood classifier using audio features.

    Determines mood using heuristic rules on extracted features.
    """

    def __init__(self):
        """Initialize classifier."""
        self.extractor = AudioFeatureExtractor()
        self.lock = Lock()

    def classify(self, audio: np.ndarray, sr: int = 44100) -> MoodAnalysis:
        """
        Classify mood from audio.

        Args:
            audio: Audio samples
            sr: Sample rate

        Returns:
            MoodAnalysis with classification
        """
        import time
        start_time = time.time()

        # Extract features
        features = self.extractor.extract_features(audio)

        # Classify based on features
        energy = self._classify_energy(features)
        mood, mood_confidence = self._classify_mood(features)
        danceability = self._estimate_danceability(features)
        valence = self._estimate_valence(features)
        arousal = self._estimate_arousal(features)
        has_vocals = self._detect_vocals(features)

        # Get mood probabilities
        mood_probs = self._get_mood_probabilities(features)

        processing_time = (time.time() - start_time) * 1000

        return MoodAnalysis(
            energy_level=energy,
            primary_mood=mood,
            mood_confidence=mood_confidence,
            mood_probabilities=mood_probs,
            danceability=danceability,
            valence=valence,
            arousal=arousal,
            has_vocals=has_vocals,
            is_instrumental=not has_vocals,
            genre_tags=self._estimate_genre_tags(features),
            processing_time_ms=processing_time
        )

    def _classify_energy(self, features: Dict) -> int:
        """Classify energy level 1-10."""
        rms = features.get('rms_energy', 0.0)
        peak = features.get('peak_amplitude', 0.0)
        zcr = features.get('zero_crossing_rate', 0.0)

        # Weighted combination
        energy_score = (rms * 0.4 + peak * 0.3 + zcr * 0.3)

        # Map to 1-10 scale
        energy = int(np.clip(energy_score * 10, 1, 10))
        return energy

    def _classify_mood(self, features: Dict) -> Tuple[MoodType, float]:
        """Classify primary mood."""
        mood_probs = self._get_mood_probabilities(features)

        if mood_probs:
            primary_mood = max(mood_probs, key=mood_probs.get)
            confidence = mood_probs[primary_mood]
            return primary_mood, confidence

        return MoodType.GROOVY, 0.5

    def _get_mood_probabilities(self, features: Dict) -> Dict[MoodType, float]:
        """Calculate mood probabilities."""
        probs = {}

        centroid = features.get('spectral_centroid', 0.0)
        rolloff = features.get('spectral_rolloff', 0.0)
        rhythm = features.get('rhythm_regularity', 0.0)
        onset = features.get('onset_strength', 0.0)
        zcr = features.get('zero_crossing_rate', 0.0)

        # High frequency = happy, presence
        if centroid > 3000:
            probs[MoodType.HAPPY] = 0.7
            probs[MoodType.ENERGETIC] = 0.6
        else:
            probs[MoodType.DARK] = 0.6
            probs[MoodType.CHILL] = 0.5

        # Strong rhythm = groovy
        if rhythm > 0.5 and onset > 0.3:
            probs[MoodType.GROOVY] = 0.8

        # High ZCR = percussive
        if zcr > 0.1:
            probs[MoodType.PERCUSSIVE] = 0.7

        # Low spectral centroid + low rhythm = atmospheric
        if centroid < 2000 and rhythm < 0.3:
            probs[MoodType.ATMOSPHERIC] = 0.7
            probs[MoodType.CHILL] = 0.6

        # Default
        if not probs:
            probs[MoodType.GROOVY] = 0.5

        # Normalize
        total = sum(probs.values())
        if total > 0:
            probs = {k: v / total for k, v in probs.items()}

        return probs

    def _estimate_danceability(self, features: Dict) -> float:
        """Estimate danceability 0.0-1.0."""
        rhythm = features.get('rhythm_regularity', 0.0)
        onset = features.get('onset_strength', 0.0)

        danceability = (rhythm * 0.6 + onset * 0.4)
        return float(np.clip(danceability, 0.0, 1.0))

    def _estimate_valence(self, features: Dict) -> float:
        """Estimate valence (positive sentiment) 0.0-1.0."""
        centroid = features.get('spectral_centroid', 0.0)
        zcr = features.get('zero_crossing_rate', 0.0)

        # Higher centroid and ZCR = more positive
        valence = ((centroid / 8000.0) * 0.5 + (zcr / 0.3) * 0.5)
        return float(np.clip(valence, 0.0, 1.0))

    def _estimate_arousal(self, features: Dict) -> float:
        """Estimate arousal (calm to intense) 0.0-1.0."""
        rms = features.get('rms_energy', 0.0)
        onset = features.get('onset_strength', 0.0)

        arousal = (rms * 0.5 + onset * 0.5)
        return float(np.clip(arousal, 0.0, 1.0))

    def _detect_vocals(self, features: Dict) -> bool:
        """Detect if vocals present."""
        # Simplified: high ZCR suggests vocals/noise
        zcr = features.get('zero_crossing_rate', 0.0)
        return zcr > 0.08

    def _estimate_genre_tags(self, features: Dict) -> List[str]:
        """Estimate genre tags."""
        tags = []

        rhythm = features.get('rhythm_regularity', 0.0)
        if rhythm > 0.6:
            tags.append("rhythmic")

        centroid = features.get('spectral_centroid', 0.0)
        if centroid > 4000:
            tags.append("bright")
        elif centroid < 2000:
            tags.append("dark")

        return tags


class MoodClassifier:
    """
    High-level mood classifier interface.

    Provides mood classification with optional Spotify API enrichment.
    """

    def __init__(self, use_spotify: bool = False,
                 spotify_client_id: Optional[str] = None,
                 spotify_client_secret: Optional[str] = None):
        """
        Initialize mood classifier.

        Args:
            use_spotify: Use Spotify API for metadata
            spotify_client_id: Spotify API credentials
            spotify_client_secret: Spotify API credentials
        """
        self.classifier = SimpleRuleBasedMoodClassifier()
        self.spotify_client = None
        self.lock = Lock()

        # Try to initialize Spotify if requested
        if use_spotify and SPOTIFY_AVAILABLE and spotify_client_id:
            try:
                from spotipy.oauth2 import SpotifyClientCredentials

                auth = SpotifyClientCredentials(
                    client_id=spotify_client_id,
                    client_secret=spotify_client_secret
                )
                self.spotify_client = spotipy.Spotify(auth_manager=auth)
                logger.info("Spotify API initialized")
            except Exception as e:
                logger.warning(f"Spotify initialization failed: {e}")

        logger.info("MoodClassifier initialized")

    def analyze_track(self, audio: np.ndarray, sr: int = 44100,
                     track_title: Optional[str] = None,
                     artist: Optional[str] = None) -> MoodAnalysis:
        """
        Analyze track mood and characteristics.

        Args:
            audio: Audio samples
            sr: Sample rate
            track_title: Track title for Spotify lookup
            artist: Artist name for Spotify lookup

        Returns:
            MoodAnalysis with complete characterization
        """
        # Classify from audio
        analysis = self.classifier.classify(audio, sr)

        # Enhance with Spotify metadata if available
        if self.spotify_client and track_title and artist:
            analysis = self._enrich_with_spotify(analysis, track_title, artist)

        return analysis

    def _enrich_with_spotify(self, analysis: MoodAnalysis,
                            track_title: str, artist: str) -> MoodAnalysis:
        """
        Enrich mood analysis with Spotify API data.

        Args:
            analysis: Original analysis
            track_title: Track title
            artist: Artist name

        Returns:
            Enriched analysis
        """
        try:
            # Search on Spotify
            query = f"track:{track_title} artist:{artist}"
            results = self.spotify_client.search(q=query, type='track', limit=1)

            if results['tracks']['items']:
                track = results['tracks']['items'][0]
                features = self.spotify_client.audio_features(track['id'])[0]

                # Use Spotify's audio analysis
                # Spotify provides: energy, danceability, valence, acousticness, etc.
                if features:
                    analysis.energy_level = int(features.get('energy', analysis.energy_level / 10) * 10)
                    analysis.danceability = features.get('danceability', analysis.danceability)
                    analysis.valence = features.get('valence', analysis.valence)
                    analysis.arousal = features.get('energy', analysis.arousal)

                    logger.info(f"Spotify enrichment: {track_title}")

        except Exception as e:
            logger.warning(f"Spotify enrichment failed: {e}")

        return analysis

    def batch_analyze(self, audio_files: List[Tuple[str, np.ndarray, int]]) -> Dict:
        """
        Analyze multiple tracks.

        Args:
            audio_files: List of (filename, audio, sr) tuples

        Returns:
            Dictionary mapping filenames to MoodAnalysis
        """
        results = {}

        for filename, audio, sr in audio_files:
            try:
                analysis = self.analyze_track(audio, sr, track_title=filename)
                results[filename] = analysis
                logger.info(f"Analyzed: {filename} → {analysis.primary_mood.value}")
            except Exception as e:
                logger.warning(f"Failed to analyze {filename}: {e}")

        return results
