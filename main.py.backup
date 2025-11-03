#!/usr/bin/env python3
# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

# -*- coding: utf-8 -*-
"""
Minimal DJ Application - A lightweight, professional DJ mixer built with Tkinter.

This application provides core DJ functionality including:
- Two-deck mixing with crossfader
- Audio file playback (WAV, FLAC)
- BPM detection and tempo sync
- Gain, EQ, and master volume controls
- Looping and cueing capabilities

Author: Your Name
License: MIT
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sys
import os
import threading
import queue
import time
import math
import logging
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Heavy imports deferred until needed
np = None
sd = None
sf = None
librosa = None
scipy_signal = None

# Constants
APP_NAME = "DJ Mixer v1.0"
APP_VERSION = "1.0.0"
DEFAULT_SAMPLERATE = 44100
BUFFER_SIZE = 1024
LOOP_DURATION_SEC = 2.0
PITCH_RANGE_PERCENT = 10.0
EQ_LOW_CUTOFF = 250
EQ_HIGH_CUTOFF = 2000
EQ_FILTER_ORDER = 3
WAVEFORM_WIDTH = 350
WAVEFORM_HEIGHT = 80
WAVEFORM_COLOR = "#4a9eff"

# Global state
audio_stream = None
stream_lock = threading.Lock()
audio_queue = queue.Queue(maxsize=1)
playback_decks = {}


class DeckMode(Enum):
    """Deck operational modes."""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"


@dataclass
class AudioMetrics:
    """Audio metrics for a deck."""
    duration_samples: int = 0
    samplerate: int = DEFAULT_SAMPLERATE
    bpm: Optional[float] = None
    channels: int = 1
    file_path: Optional[str] = None

    @property
    def duration_seconds(self) -> float:
        """Calculate duration in seconds."""
        return self.duration_samples / max(self.samplerate, 1)


class DeckData:
    """Manages audio data and playback state for a single deck."""

    def __init__(self, deck_id: str, parent_app: 'MinimalDJApp') -> None:
        """Initialize deck data."""
        self.deck_id = deck_id
        self.parent_app = parent_app
        self.logger = logging.getLogger(f"DeckData.{deck_id}")

        # Audio data
        self.audio_data = None
        self.metrics = AudioMetrics()

        # Playback state
        self.position = 0
        self.mode = DeckMode.STOPPED
        self.volume = 1.0
        self.gain_percent = 100.0

        # EQ state
        self.eq_low_percent = 100.0
        self.eq_mid_percent = 100.0
        self.eq_high_percent = 100.0
        self.b_low, self.a_low = None, None
        self.b_high, self.a_high = None, None

        # Pitch and sync
        self.pitch_percent = 0.0
        self.is_synced = False

        # Cueing
        self.cue_point = None
        self.cue_active = False

        # Looping
        self.looping = False
        self.loop_start_pos = 0
        self.loop_duration_samples = int(LOOP_DURATION_SEC * DEFAULT_SAMPLERATE)

        self.logger.info(f"Initialized {deck_id}")

    @property
    def is_playing(self) -> bool:
        """Check if deck is currently playing."""
        return self.mode == DeckMode.PLAYING

    @is_playing.setter
    def is_playing(self, value: bool) -> None:
        """Set playing state (for backward compatibility)."""
        self.mode = DeckMode.PLAYING if value else DeckMode.STOPPED

    def load_file_threaded(self, file_path: str, callback_on_load) -> None:
        """Load audio file in a background thread."""
        def _load():
            global sf, np
            if sf is None or np is None:
                self.logger.error("Required libraries not loaded")
                self.parent_app.root.after(0, callback_on_load, self.deck_id, False, "Libraries not loaded")
                return

            self.logger.info(f"Loading: {os.path.basename(file_path)}")

            try:
                with sf.SoundFile(file_path, 'r') as f:
                    sr = f.samplerate
                    data = f.read(dtype='float32')

                    # Convert to mono if stereo
                    if data.ndim > 1:
                        data = np.mean(data, axis=1)

                    self.audio_data = data
                    self.metrics = AudioMetrics(
                        duration_samples=len(data),
                        samplerate=sr,
                        file_path=file_path,
                        channels=1
                    )

                    # Reset playback state
                    self.position = 0
                    self.mode = DeckMode.STOPPED
                    self.cue_point = None
                    self.looping = False
                    self.pitch_percent = 0.0

                    # Reset EQ
                    self.eq_low_percent = 100.0
                    self.eq_mid_percent = 100.0
                    self.eq_high_percent = 100.0
                    self.b_low, self.a_low = None, None
                    self.b_high, self.a_high = None, None

                    self.logger.info(f"Loaded: {os.path.basename(file_path)} "
                                   f"({sr}Hz, {self.metrics.duration_seconds:.1f}s)")
                    self.parent_app.root.after(0, callback_on_load, self.deck_id, True, "")

            except Exception as e:
                error_msg = f"Failed to load audio: {str(e)}"
                self.logger.error(error_msg)
                self.audio_data = None
                self.parent_app.root.after(0, callback_on_load, self.deck_id, False, error_msg)

        threading.Thread(target=_load, daemon=True).start()

    def analyze_bpm_threaded(self, callback_on_complete) -> None:
        """Analyze BPM in a background thread."""
        if self.audio_data is None:
            self.logger.warning("No audio data to analyze")
            self.parent_app.root.after(0, callback_on_complete, self.deck_id, None, "No audio data")
            return

        def _analyze():
            global librosa, np
            if librosa is None or np is None:
                self.logger.error("Librosa not loaded")
                self.parent_app.root.after(0, callback_on_complete, self.deck_id, None, "Libraries not loaded")
                return

            self.logger.info("Analyzing BPM...")

            try:
                tempo, _ = librosa.beat.beat_track(
                    y=self.audio_data,
                    sr=self.metrics.samplerate
                )
                bpm = round(tempo)
                self.metrics.bpm = bpm
                self.logger.info(f"BPM detected: {bpm}")
                self.parent_app.root.after(0, callback_on_complete, self.deck_id, bpm, "")

            except Exception as e:
                error_msg = f"BPM analysis failed: {str(e)}"
                self.logger.error(error_msg)
                self.parent_app.root.after(0, callback_on_complete, self.deck_id, None, error_msg)

        threading.Thread(target=_analyze, daemon=True).start()

    def get_chunk(self, num_samples: int) -> 'np.ndarray':
        """Get audio chunk with gain and EQ applied."""
        if not self.is_playing or self.audio_data is None or len(self.audio_data) == 0:
            return np.zeros(num_samples, dtype=np.float32)

        chunk = self._get_raw_chunk(num_samples)
        processed = self._apply_gain_eq(chunk)
        return processed * self.volume

    def _get_raw_chunk(self, num_samples: int) -> 'np.ndarray':
        """Get raw audio chunk, handling looping and bounds."""
        if self.looping:
            return self._get_looped_chunk(num_samples)
        else:
            return self._get_linear_chunk(num_samples)

    def _get_linear_chunk(self, num_samples: int) -> 'np.ndarray':
        """Get chunk for linear (non-looping) playback."""
        start = self.position
        end = start + num_samples
        data_len = len(self.audio_data)

        if end <= data_len:
            chunk = self.audio_data[start:end]
            self.position = end
        else:
            remainder = data_len - start
            chunk = np.pad(self.audio_data[start:], (0, num_samples - remainder))
            self.position = data_len
            self.mode = DeckMode.STOPPED

        return chunk

    def _get_looped_chunk(self, num_samples: int) -> 'np.ndarray':
        """Get chunk for looped playback."""
        loop_end = min(self.loop_start_pos + self.loop_duration_samples, len(self.audio_data))
        loop_duration = loop_end - self.loop_start_pos

        if loop_duration <= 0:
            self.looping = False
            return self._get_linear_chunk(num_samples)

        pos_in_loop = (self.position - self.loop_start_pos) % loop_duration
        to_read = num_samples
        parts = []

        while to_read > 0:
            read_start = self.loop_start_pos + pos_in_loop
            available = loop_end - read_start
            read_now = min(to_read, available)

            if read_now > 0:
                parts.append(self.audio_data[read_start:read_start + read_now])
                to_read -= read_now
                pos_in_loop = (pos_in_loop + read_now) % loop_duration
            else:
                break

        chunk = np.concatenate(parts) if parts else np.zeros(num_samples, dtype=np.float32)

        if len(chunk) < num_samples:
            chunk = np.pad(chunk, (0, num_samples - len(chunk)))

        self.position = self.loop_start_pos + pos_in_loop
        return chunk[:num_samples]

    def _apply_gain_eq(self, chunk: 'np.ndarray') -> 'np.ndarray':
        """Apply gain and EQ processing to chunk."""
        global scipy_signal

        # Apply gain
        gain_factor = self.gain_percent / 100.0
        chunk_out = chunk * gain_factor

        # Apply EQ (if scipy available)
        if self.eq_low_percent != 100.0 or self.eq_high_percent != 100.0:
            if scipy_signal is None:
                try:
                    import scipy.signal as scipy_signal_module
                    scipy_signal = scipy_signal_module
                except ImportError:
                    self.logger.warning("scipy.signal not available for EQ")
                    return chunk_out

            if scipy_signal:
                chunk_out = self._apply_eq_filters(chunk_out)

        return chunk_out

    def _apply_eq_filters(self, chunk: 'np.ndarray') -> 'np.ndarray':
        """Apply low and high pass EQ filters."""
        try:
            nyquist = 0.5 * self.metrics.samplerate

            # Low EQ filter
            if self.eq_low_percent != 100.0:
                if self.b_low is None or self.a_low is None:
                    normal_cutoff = EQ_LOW_CUTOFF / nyquist
                    if 0 < normal_cutoff < 1:
                        self.b_low, self.a_low = scipy_signal.butter(
                            EQ_FILTER_ORDER, normal_cutoff, btype='low', analog=False
                        )

                if self.b_low is not None:
                    try:
                        chunk = scipy_signal.lfilter(self.b_low, self.a_low, chunk)
                    except Exception as e:
                        self.logger.warning(f"Low EQ filter failed: {e}")

            # High EQ filter
            if self.eq_high_percent != 100.0:
                if self.b_high is None or self.a_high is None:
                    normal_cutoff = EQ_HIGH_CUTOFF / nyquist
                    if 0 < normal_cutoff < 1:
                        self.b_high, self.a_high = scipy_signal.butter(
                            EQ_FILTER_ORDER, normal_cutoff, btype='high', analog=False
                        )

                if self.b_high is not None:
                    try:
                        chunk = scipy_signal.lfilter(self.b_high, self.a_high, chunk)
                    except Exception as e:
                        self.logger.warning(f"High EQ filter failed: {e}")

        except Exception as e:
            self.logger.error(f"EQ filtering error: {e}")

        return chunk

    def set_cue(self) -> None:
        """Set cue point at current position."""
        self.cue_point = self.position
        self.logger.info(f"Cue set at {self.position / self.metrics.samplerate:.2f}s")

    def jump_to_cue(self) -> None:
        """Jump to cue point."""
        if self.cue_point is None or self.audio_data is None:
            self.logger.warning("No cue point set")
            return

        self.cue_point = max(0, min(len(self.audio_data) - 1, self.cue_point))
        self.position = self.cue_point
        self.logger.info(f"Jumped to cue at {self.position / self.metrics.samplerate:.2f}s")

        if self.is_playing:
            try:
                audio_queue.put_nowait(True)
            except queue.Full:
                pass

    def toggle_loop(self, enabled: bool) -> bool:
        """Toggle looping on/off."""
        if not self.audio_data:
            self.looping = False
            return False

        if enabled == self.looping:
            return enabled

        if enabled:
            self.looping = True
            self.loop_start_pos = self.position
            self.loop_duration_samples = int(LOOP_DURATION_SEC * self.metrics.samplerate)
            self.loop_start_pos = min(self.loop_start_pos, len(self.audio_data) - 1)
            self.logger.info(f"Loop enabled at {self.loop_start_pos / self.metrics.samplerate:.1f}s")
        else:
            self.looping = False
            self.logger.info("Loop disabled")

        return self.looping

    def set_pitch_value(self, percent: float, from_sync: bool = False) -> None:
        """Set pitch value."""
        self.pitch_percent = max(-PITCH_RANGE_PERCENT, min(PITCH_RANGE_PERCENT, percent))
        if not from_sync and self.is_synced:
            self.is_synced = False
            self.logger.info("Sync broken by manual pitch adjustment")

    def set_gain(self, percent: float) -> None:
        """Set gain percentage (0-200)."""
        self.gain_percent = max(0.0, min(200.0, percent))

    def set_eq_low(self, percent: float) -> None:
        """Set low EQ percentage (0-200)."""
        self.eq_low_percent = max(0.0, min(200.0, percent))

    def set_eq_mid(self, percent: float) -> None:
        """Set mid EQ percentage (0-200)."""
        self.eq_mid_percent = max(0.0, min(200.0, percent))

    def set_eq_high(self, percent: float) -> None:
        """Set high EQ percentage (0-200)."""
        self.eq_high_percent = max(0.0, min(200.0, percent))

    def set_cue_active(self, active: bool) -> None:
        """Set cue active state."""
        self.cue_active = active
        self.logger.debug(f"Cue active: {active}")


class MinimalDJApp:
    """Main DJ application class."""

    def __init__(self, root: tk.Tk) -> None:
        """Initialize the DJ application."""
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("900x700")
        self.root.minsize(800, 600)

        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Initializing {APP_NAME}")

        # Set up dark theme
        self._setup_theme()

        # Initialize UI
        self._create_ui()

        # State flags
        self.heavy_libs_loaded = False
        self.audio_engine_initialized = False
        self.keep_callback_alive_flag = False
        self.callback_trigger_thread = None

        # Deck data
        self.deck_data = {}
        for i in range(2):
            deck_id = f"Deck_{chr(ord('A') + i)}"
            self.deck_data[deck_id] = DeckData(deck_id, self)

        self.logger.info("UI initialization complete")
        self.root.after(100, self.check_initialization)

    def _setup_theme(self) -> None:
        """Configure application theme."""
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except tk.TclError:
            pass

        # Colors
        bg_dark = "#1e1e1e"
        bg_medium = "#2e2e2e"
        bg_light = "#3e3e3e"
        fg_text = "#e0e0e0"
        fg_muted = "#999999"
        accent = "#4a9eff"

        # Configure styles
        style.configure("TFrame", background=bg_medium)
        style.configure("TLabel", background=bg_medium, foreground=fg_text)
        style.configure("Title.TLabel", background=bg_medium, foreground=fg_text,
                       font=('Segoe UI', 12, 'bold'))
        style.configure("TButton", padding=6, relief=tk.FLAT, background=bg_light,
                       foreground=fg_text, font=('Segoe UI', 9))
        style.map("TButton",
                 background=[('active', '#4a4a4a'), ('pressed', '#5a5a5a')],
                 foreground=[('disabled', fg_muted)])

        style.configure("Vertical.TScale", background=bg_medium, troughcolor="#444",
                       sliderlength=20)
        style.configure("Horizontal.TScale", background=bg_medium, troughcolor="#444",
                       sliderlength=20)
        style.configure("TCheckbutton", background=bg_medium, foreground=fg_text,
                       padding=5)
        style.map("TCheckbutton",
                 background=[('active', bg_light)],
                 foreground=[('disabled', fg_muted)])

        self.root.configure(bg=bg_medium)

    def _create_ui(self) -> None:
        """Create the user interface."""
        # Main container
        main_frame = ttk.Frame(self.root, padding="5")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title bar
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))

        title_label = ttk.Label(title_frame, text=APP_NAME, style="Title.TLabel")
        title_label.pack(side=tk.LEFT)

        version_label = ttk.Label(title_frame, text=f"v{APP_VERSION}", foreground="#999999")
        version_label.pack(side=tk.LEFT, padx=(10, 0))

        # Decks container
        decks_frame = ttk.Frame(main_frame)
        decks_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.deck_frames = {}
        self.deck_controls = {}

        for i in range(2):
            deck_id = f"Deck_{chr(ord('A') + i)}"
            deck_frame = ttk.Frame(decks_frame, relief=tk.GROOVE, borderwidth=1, padding=10)
            deck_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

            self.deck_frames[deck_id] = deck_frame

            # Deck title and load button
            title_subframe = ttk.Frame(deck_frame)
            title_subframe.pack(fill=tk.X)

            deck_label = ttk.Label(title_subframe, text=f"Deck {chr(ord('A') + i)}",
                                  font=('Segoe UI', 11, 'bold'))
            deck_label.pack(side=tk.LEFT)

            load_btn = ttk.Button(title_subframe, text="Load",
                                 command=lambda d=deck_id: self.deferred_load_track(d))
            load_btn.pack(side=tk.RIGHT)

            # Waveform display
            waveform_canvas = tk.Canvas(deck_frame, width=WAVEFORM_WIDTH,
                                       height=WAVEFORM_HEIGHT, bg="#1e1e1e",
                                       highlightthickness=0)
            waveform_canvas.pack(fill=tk.X, pady=5)

            # Controls placeholder
            controls_frame = ttk.Frame(deck_frame, height=250)
            controls_frame.pack(fill=tk.X, pady=5)

            self.deck_controls[deck_id] = {
                'placeholder': controls_frame,
                'waveform_canvas': waveform_canvas
            }

        # Bottom controls
        self._create_bottom_controls(main_frame)

        # Status bar
        self.status_label = ttk.Label(main_frame, text="Status: Ready | Audio: Inactive")
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

    def _create_bottom_controls(self, parent: ttk.Frame) -> None:
        """Create bottom control section."""
        bottom_frame = ttk.Frame(parent, padding=(0, 10, 0, 5))
        bottom_frame.pack(fill=tk.X)

        # Crossfader section
        xfader_frame = ttk.Frame(bottom_frame)
        xfader_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Label(xfader_frame, text="A").pack(side=tk.LEFT)
        self.crossfader_value = tk.DoubleVar(value=0.5)
        self.xfader_scale = ttk.Scale(xfader_frame, from_=0.0, to=1.0,
                                     orient=tk.HORIZONTAL,
                                     variable=self.crossfader_value,
                                     command=self.update_status_label)
        self.xfader_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        ttk.Label(xfader_frame, text="B").pack(side=tk.LEFT)

        # Master volume section
        master_frame = ttk.Frame(bottom_frame, padding=(20, 0, 0, 0))
        master_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Label(master_frame, text="Master:").pack(side=tk.LEFT)
        self.master_volume_percent = tk.DoubleVar(value=100.0)
        master_scale = ttk.Scale(master_frame, from_=0.0, to=100.0,
                                orient=tk.HORIZONTAL,
                                variable=self.master_volume_percent,
                                command=self.update_status_label)
        master_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Cue section
        cue_frame = ttk.Frame(bottom_frame, padding=(20, 0, 0, 0))
        cue_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Label(cue_frame, text="Cue Mix:").pack(side=tk.LEFT)
        self.cue_mix_percent = tk.DoubleVar(value=50.0)
        cue_mix_scale = ttk.Scale(cue_frame, from_=0.0, to=100.0,
                                 orient=tk.HORIZONTAL,
                                 variable=self.cue_mix_percent)
        cue_mix_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        ttk.Label(cue_frame, text="Vol:").pack(side=tk.LEFT, padx=(20, 0))
        self.cue_volume_percent = tk.DoubleVar(value=80.0)
        cue_vol_scale = ttk.Scale(cue_frame, from_=0.0, to=100.0,
                                 orient=tk.HORIZONTAL,
                                 variable=self.cue_volume_percent)
        cue_vol_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

    def check_initialization(self) -> None:
        """Check and perform necessary initializations."""
        pass

    def initialize_heavy_components(self) -> bool:
        """Initialize heavy libraries."""
        global np, sd, sf, librosa, scipy_signal

        if not self.heavy_libs_loaded:
            self.logger.info("Loading heavy libraries...")
            try:
                import numpy as np_module
                import sounddevice as sd_module
                import soundfile as sf_module
                import librosa as librosa_module

                np = np_module
                sd = sd_module
                sf = sf_module
                librosa = librosa_module

                self.heavy_libs_loaded = True
                self.logger.info("Libraries loaded successfully")
            except ImportError as e:
                error_msg = f"Failed to import required libraries: {e}"
                self.logger.error(error_msg)
                messagebox.showerror("Library Error", error_msg)
                return False

        if not self.audio_engine_initialized and self.heavy_libs_loaded:
            self.logger.info("Initializing audio engine...")
            self.init_audio_stream()

            if self.audio_stream is not None:
                self.audio_engine_initialized = True
                self.logger.info("Audio engine initialized")
            else:
                self.logger.error("Failed to initialize audio stream")
                messagebox.showerror("Audio Error", "Failed to initialize audio stream")
                return False

        return True

    def init_audio_stream(self) -> None:
        """Initialize audio output stream."""
        global audio_stream

        with stream_lock:
            if audio_stream is not None:
                return

            try:
                self.logger.info(f"Starting audio stream: {DEFAULT_SAMPLERATE}Hz, {BUFFER_SIZE} buffer")
                audio_stream = sd.OutputStream(
                    samplerate=DEFAULT_SAMPLERATE,
                    blocksize=BUFFER_SIZE,
                    channels=2,
                    callback=self.audio_callback,
                    finished_callback=self.stream_finished_callback,
                    dtype=np.float32
                )
                audio_stream.start()

                self.keep_callback_alive_flag = True
                self.callback_trigger_thread = threading.Thread(
                    target=self._keep_callback_alive, daemon=True
                )
                self.callback_trigger_thread.start()

                self.logger.info("Audio stream started successfully")
                self.update_status_label()

            except Exception as e:
                self.logger.error(f"Failed to initialize audio stream: {e}")
                audio_stream = None

    def audio_callback(self, outdata, frames: int, time_info, status) -> None:
        """Audio output callback."""
        if status:
            self.logger.warning(f"Audio status: {status}")

        try:
            _ = audio_queue.get_nowait()
        except queue.Empty:
            outdata.fill(0)
            return

        # Initialize mix buffer
        mix = np.zeros((frames, 2), dtype=np.float32)
        active_decks = 0
        remove_decks = []
        xf = self.crossfader_value.get()
        master_vol = self.master_volume_percent.get() / 100.0

        with stream_lock:
            for i, (deck_id, deck) in enumerate(list(playback_decks.items())):
                if deck.is_playing:
                    chunk = deck.get_chunk(frames)
                    level = (1.0 - xf) if i == 0 else xf
                    stereo_chunk = np.column_stack((chunk, chunk)) * level
                    mix += stereo_chunk

                    if deck.is_playing:
                        active_decks += 1
                    else:
                        remove_decks.append(deck_id)
                else:
                    remove_decks.append(deck_id)

            # Clean up inactive decks
            for deck_id in remove_decks:
                if deck_id in playback_decks:
                    del playback_decks[deck_id]

        # Apply master volume and clip
        mix *= master_vol
        np.clip(mix, -1.0, 1.0, out=mix)
        outdata[:] = mix

        # Keep callback alive if there's active playback
        if active_decks > 0:
            try:
                audio_queue.put_nowait(True)
            except queue.Full:
                pass

    def _keep_callback_alive(self) -> None:
        """Keep the audio callback active during playback."""
        self.logger.info("Callback keeper thread started")

        while self.keep_callback_alive_flag:
            active = False

            with stream_lock:
                for deck in playback_decks.values():
                    if deck.is_playing:
                        active = True
                        break

            if active:
                try:
                    audio_queue.put_nowait(True)
                except queue.Full:
                    pass

            time.sleep(BUFFER_SIZE / DEFAULT_SAMPLERATE / 2.0)

        self.logger.info("Callback keeper thread stopped")

    def stream_finished_callback(self) -> None:
        """Handle stream finished event."""
        global audio_stream
        self.logger.info("Audio stream finished")
        self.update_status_label()

        with stream_lock:
            audio_stream = None

    def deferred_load_track(self, deck_id: str) -> None:
        """Load track with deferred library initialization."""
        self.logger.info(f"Load clicked for {deck_id}")

        if not self.initialize_heavy_components():
            return

        try:
            file_path = filedialog.askopenfilename(
                title=f"Load {deck_id}",
                filetypes=[
                    ("Audio Files", "*.wav *.flac *.mp3"),
                    ("WAV", "*.wav"),
                    ("FLAC", "*.flac"),
                    ("All Files", "*.*")
                ]
            )

            if file_path:
                self.logger.info(f"Loading: {file_path}")
                self.update_deck_ui(deck_id, loading=True)
                self.deck_data[deck_id].load_file_threaded(file_path, self.on_track_load_complete)

        except Exception as e:
            self.logger.error(f"File dialog error: {e}")
            messagebox.showerror("Error", f"Failed to open file dialog:\n{e}")

    def on_track_load_complete(self, deck_id: str, success: bool, error_msg: str) -> None:
        """Handle track load completion."""
        self.logger.info(f"Load complete for {deck_id}: success={success}")

        if success:
            self.update_deck_ui(deck_id, loading=False, loaded=True)
            deck = self.deck_data.get(deck_id)

            if deck:
                self.logger.info(f"Starting BPM analysis for {deck_id}")
                deck.analyze_bpm_threaded(self.on_bpm_analysis_complete)

                # Update BPM label
                controls = self.deck_controls.get(deck_id)
                if controls and 'placeholder' in controls:
                    if 'bpm_label' not in controls:
                        controls['bpm_label'] = ttk.Label(
                            controls['placeholder'], text="BPM: Analyzing..."
                        )
                        controls['bpm_label'].pack(side=tk.BOTTOM, anchor=tk.W)
                    else:
                        controls['bpm_label'].config(text="BPM: Analyzing...")
        else:
            self.update_deck_ui(deck_id, loading=False, loaded=False)
            messagebox.showerror("Load Error", f"Failed to load track:\n{error_msg}")

    def on_bpm_analysis_complete(self, deck_id: str, bpm: Optional[float], error_msg: str) -> None:
        """Handle BPM analysis completion."""
        self.logger.info(f"BPM analysis complete for {deck_id}: bpm={bpm}")

        deck = self.deck_data.get(deck_id)
        controls = self.deck_controls.get(deck_id)

        if not deck or not controls:
            return

        if bpm is not None:
            if 'bpm_label' in controls:
                controls['bpm_label'].config(text=f"BPM: {int(bpm)}")
        else:
            if 'bpm_label' in controls:
                controls['bpm_label'].config(text="BPM: N/A")
            if error_msg:
                self.logger.warning(f"BPM error for {deck_id}: {error_msg}")

    def on_waveform_data_ready(self, deck_id: str, coords: Optional[list], error_msg: str) -> None:
        """Handle waveform data ready."""
        controls = self.deck_controls.get(deck_id)

        if not controls:
            return

        canvas = controls.get('waveform_canvas')
        if canvas:
            canvas.delete("waveform_line")

            if coords and len(coords) > 3:
                try:
                    canvas.create_line(coords, fill=WAVEFORM_COLOR, width=1.0, tags="waveform_line")
                except tk.TclError as e:
                    self.logger.warning(f"Canvas draw error for {deck_id}: {e}")
            elif error_msg:
                self.logger.error(f"Waveform error for {deck_id}: {error_msg}")

    def update_deck_ui(self, deck_id: str, loading: bool = False, loaded: bool = False) -> None:
        """Update deck UI based on load state."""
        deck_frame = self.deck_frames.get(deck_id)
        controls = self.deck_controls.get(deck_id)
        deck = self.deck_data.get(deck_id)

        if not all([deck_frame, controls, deck]):
            return

        # Clear existing controls (except waveform and placeholder)
        for widget in list(controls.values()):
            if widget not in ['placeholder', 'waveform_canvas']:
                if isinstance(widget, tk.Widget):
                    widget.destroy()

        # Reset controls dict
        self.deck_controls[deck_id] = {
            'placeholder': controls['placeholder'],
            'waveform_canvas': controls.get('waveform_canvas')
        }
        controls = self.deck_controls[deck_id]
        parent = controls['placeholder']

        # Clear waveform
        canvas = controls.get('waveform_canvas')
        if canvas:
            canvas.delete("waveform_line")

        if loading:
            controls['status'] = ttk.Label(parent, text="Loading...")
            controls['status'].pack(pady=5)

        elif loaded and deck.metrics.file_path:
            self._create_deck_loaded_ui(deck_id, deck, parent, controls)

        else:
            controls['status'] = ttk.Label(
                parent, text="Click 'Load' to select an audio file"
            )
            controls['status'].pack(pady=5)

    def _create_deck_loaded_ui(self, deck_id: str, deck: DeckData, parent: ttk.Frame,
                               controls: Dict[str, Any]) -> None:
        """Create UI for a loaded deck."""
        # Filename label
        controls['filename'] = ttk.Label(
            parent,
            text=os.path.basename(deck.metrics.file_path),
            wraplength=200
        )
        controls['filename'].pack(pady=2)

        # Playback controls
        playback_frame = ttk.Frame(parent)
        playback_frame.pack(fill=tk.X, pady=2)

        controls['play'] = ttk.Button(
            playback_frame, text="Play",
            command=lambda: self.play_deck(deck_id)
        )
        controls['play'].pack(side=tk.LEFT, padx=1)

        controls['stop'] = ttk.Button(
            playback_frame, text="Stop",
            command=lambda: self.stop_deck(deck_id)
        )
        controls['stop'].pack(side=tk.LEFT, padx=1)

        # Cue controls
        controls['set_cue'] = ttk.Button(
            playback_frame, text="Set Cue",
            command=lambda: deck.set_cue()
        )
        controls['set_cue'].pack(side=tk.LEFT, padx=1)

        controls['cue_jump'] = ttk.Button(
            playback_frame, text="Cue→",
            command=lambda: deck.jump_to_cue()
        )
        controls['cue_jump'].pack(side=tk.LEFT, padx=1)
        controls['cue_jump'].config(state=tk.NORMAL if deck.cue_point is not None else tk.DISABLED)

        # Sync and loop controls
        controls['sync_button'] = ttk.Button(
            playback_frame, text="Sync",
            command=lambda: self.sync_deck(deck_id)
        )
        controls['sync_button'].pack(side=tk.LEFT, padx=1)

        controls['loop_var'] = tk.BooleanVar(value=deck.looping)
        controls['loop_button'] = ttk.Checkbutton(
            playback_frame, text="Loop",
            variable=controls['loop_var'],
            command=lambda: self.toggle_deck_loop(deck_id)
        )
        controls['loop_button'].pack(side=tk.LEFT, padx=3)

        # Cue button
        controls['deck_cue_var'] = tk.BooleanVar(value=deck.cue_active)
        controls['deck_cue_button'] = ttk.Checkbutton(
            playback_frame, text="CUE",
            variable=controls['deck_cue_var'],
            command=lambda: self.toggle_deck_cue(deck_id)
        )
        controls['deck_cue_button'].pack(side=tk.LEFT, padx=(5, 2))

        # Pitch control
        pitch_frame = ttk.Frame(parent)
        pitch_frame.pack(fill=tk.X, pady=3)

        controls['pitch_label'] = ttk.Label(
            pitch_frame, text=f"Pitch: {deck.pitch_percent:.1f}%", width=12, anchor=tk.W
        )
        controls['pitch_label'].pack(side=tk.LEFT, padx=(0, 5))

        controls['pitch_var'] = tk.DoubleVar(value=deck.pitch_percent)
        controls['pitch_slider'] = ttk.Scale(
            pitch_frame, from_=-PITCH_RANGE_PERCENT, to=PITCH_RANGE_PERCENT,
            orient=tk.HORIZONTAL, variable=controls['pitch_var'],
            command=lambda val: self.set_deck_pitch(deck_id, float(val))
        )
        controls['pitch_slider'].pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Volume and gain
        vol_gain_frame = ttk.Frame(parent)
        vol_gain_frame.pack(fill=tk.X, pady=3)

        # Volume
        vol_frame = ttk.Frame(vol_gain_frame)
        ttk.Label(vol_frame, text="Vol:").pack(side=tk.LEFT)
        controls['volume'] = ttk.Scale(
            vol_frame, from_=0.0, to=1.0, orient=tk.HORIZONTAL,
            command=lambda val: self.set_deck_volume(deck_id, float(val))
        )
        controls['volume'].set(deck.volume)
        controls['volume'].pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        vol_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        # Gain
        gain_frame = ttk.Frame(vol_gain_frame)
        ttk.Label(gain_frame, text="Gain:").pack(side=tk.LEFT)
        controls['gain_var'] = tk.DoubleVar(value=deck.gain_percent)
        controls['gain_slider'] = ttk.Scale(
            gain_frame, from_=0.0, to=200.0, orient=tk.HORIZONTAL,
            variable=controls['gain_var'],
            command=lambda val: self.set_deck_gain(deck_id, float(val))
        )
        controls['gain_slider'].pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        gain_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        # EQ section
        eq_frame = ttk.Frame(parent)
        eq_frame.pack(side=tk.LEFT, padx=5, pady=3)

        ttk.Label(eq_frame, text="EQ:", font=('Segoe UI', 9, 'bold')).pack(side=tk.TOP, anchor=tk.W)

        eq_sliders_frame = ttk.Frame(eq_frame)
        eq_sliders_frame.pack()

        eq_bands = [
            ("Low", "eq_low_percent", deck.set_eq_low),
            ("Mid", "eq_mid_percent", deck.set_eq_mid),
            ("High", "eq_high_percent", deck.set_eq_high)
        ]

        for name, attr, setter in eq_bands:
            eq_slider_frame = ttk.Frame(eq_sliders_frame)

            controls[f'eq_{name.lower()}_var'] = tk.DoubleVar(value=getattr(deck, attr))
            controls[f'eq_{name.lower()}_slider'] = ttk.Scale(
                eq_slider_frame, from_=200.0, to=0.0, orient=tk.VERTICAL, length=60,
                variable=controls[f'eq_{name.lower()}_var'],
                command=lambda val, s=setter: s(float(val))
            )
            controls[f'eq_{name.lower()}_slider'].pack(side=tk.TOP, pady=(0, 2))

            ttk.Label(eq_slider_frame, text=name, font=('Segoe UI', 7)).pack(side=tk.TOP)
            eq_slider_frame.pack(side=tk.LEFT, padx=2)

        # BPM label
        bpm_text = f"BPM: {int(deck.metrics.bpm)}" if deck.metrics.bpm else "BPM: Analyzing..."
        controls['bpm_label'] = ttk.Label(parent, text=bpm_text)
        controls['bpm_label'].pack(side=tk.BOTTOM, anchor=tk.W, pady=(5, 0))

    def play_deck(self, deck_id: str) -> None:
        """Start playback on a deck."""
        if not self.audio_engine_initialized:
            self.logger.warning("Audio engine not initialized")
            return

        deck = self.deck_data.get(deck_id)

        if deck and deck.audio_data is not None and not deck.is_playing:
            self.logger.info(f"Playing {deck_id}")
            deck.is_playing = True

            with stream_lock:
                playback_decks[deck_id] = deck

            try:
                audio_queue.put_nowait(True)
            except queue.Full:
                pass

    def stop_deck(self, deck_id: str) -> None:
        """Stop playback on a deck."""
        deck = self.deck_data.get(deck_id)

        if deck and deck.is_playing:
            self.logger.info(f"Stopping {deck_id}")
            deck.is_playing = False
            deck.position = 0
            deck.looping = False

            # Update UI
            controls = self.deck_controls.get(deck_id, {})
            if 'loop_var' in controls:
                controls['loop_var'].set(False)
            if 'deck_cue_var' in controls:
                controls['deck_cue_var'].set(False)

            deck.cue_active = False

    def set_deck_volume(self, deck_id: str, volume: float) -> None:
        """Set deck volume."""
        deck = self.deck_data.get(deck_id)
        if deck:
            deck.volume = max(0.0, min(1.0, volume))

    def set_deck_gain(self, deck_id: str, gain: float) -> None:
        """Set deck gain."""
        deck = self.deck_data.get(deck_id)
        if deck:
            deck.set_gain(gain)

    def set_deck_pitch(self, deck_id: str, pitch: float) -> None:
        """Set deck pitch."""
        deck = self.deck_data.get(deck_id)
        controls = self.deck_controls.get(deck_id)

        if deck and controls:
            deck.set_pitch_value(pitch, from_sync=False)
            if 'pitch_label' in controls:
                controls['pitch_label'].config(text=f"Pitch: {deck.pitch_percent:.1f}%")

    def toggle_deck_loop(self, deck_id: str) -> None:
        """Toggle loop on/off."""
        deck = self.deck_data.get(deck_id)
        controls = self.deck_controls.get(deck_id)

        if deck and controls and 'loop_var' in controls:
            new_state = controls['loop_var'].get()
            actual_state = deck.toggle_loop(new_state)

            if actual_state != new_state:
                controls['loop_var'].set(actual_state)

    def toggle_deck_cue(self, deck_id: str) -> None:
        """Toggle cue on/off."""
        deck = self.deck_data.get(deck_id)
        controls = self.deck_controls.get(deck_id)

        if deck and controls and 'deck_cue_var' in controls:
            new_state = controls['deck_cue_var'].get()
            deck.set_cue_active(new_state)

    def sync_deck(self, slave_deck_id: str) -> None:
        """Sync slave deck to master deck."""
        self.logger.info(f"Sync pressed for {slave_deck_id}")

        slave_deck = self.deck_data.get(slave_deck_id)

        if not slave_deck or not slave_deck.metrics.bpm:
            self.logger.warning(f"Slave deck {slave_deck_id} has no BPM")
            return

        # Find master deck
        other_id = "Deck_B" if slave_deck_id == "Deck_A" else "Deck_A"
        master_deck = self.deck_data.get(other_id)

        if not master_deck or not master_deck.is_playing or not master_deck.metrics.bpm:
            self.logger.warning(f"Master deck {other_id} is not playing or has no BPM")
            return

        try:
            ratio = master_deck.metrics.bpm / slave_deck.metrics.bpm

            if ratio <= 0 or not math.isfinite(ratio):
                raise ValueError("Invalid BPM ratio")

            target_pitch = (ratio - 1.0) * 100.0
            target_pitch = max(-PITCH_RANGE_PERCENT, min(PITCH_RANGE_PERCENT, target_pitch))

            self.logger.info(f"Syncing {slave_deck_id} to {other_id}: "
                           f"ratio={ratio:.2f}, pitch={target_pitch:.1f}%")

            slave_deck.set_pitch_value(target_pitch, from_sync=True)
            slave_deck.is_synced = True

            # Update UI
            controls = self.deck_controls.get(slave_deck_id)
            if controls:
                if 'pitch_var' in controls:
                    controls['pitch_var'].set(target_pitch)
                if 'pitch_label' in controls:
                    controls['pitch_label'].config(text=f"Pitch: {slave_deck.pitch_percent:.1f}%")

        except Exception as e:
            self.logger.error(f"Sync calculation error: {e}")
            slave_deck.is_synced = False

    def update_status_label(self, *args) -> None:
        """Update status label."""
        global audio_stream

        audio_status = "Inactive"
        if audio_stream and audio_stream.active:
            audio_status = "Active"
        elif self.audio_engine_initialized and not audio_stream:
            audio_status = "Stopped"

        xf_pct = int(self.crossfader_value.get() * 100)
        master_vol_pct = int(self.master_volume_percent.get())

        status_text = (
            f"Status: Ready | Audio: {audio_status} | "
            f"Master: {master_vol_pct}% | XFader: {xf_pct}%"
        )
        self.status_label.config(text=status_text)

    def closeEvent(self) -> None:
        """Handle window close event."""
        global audio_stream

        self.logger.info("Closing application...")

        self.keep_callback_alive_flag = False

        with stream_lock:
            if audio_stream is not None:
                try:
                    self.logger.info("Stopping audio stream...")
                    audio_stream.stop()
                    audio_stream.close()
                    self.logger.info("Audio stream stopped")
                except Exception as e:
                    self.logger.error(f"Error stopping audio stream: {e}")
                finally:
                    audio_stream = None

        if hasattr(self, 'callback_trigger_thread') and self.callback_trigger_thread:
            if self.callback_trigger_thread.is_alive():
                self.logger.info("Waiting for callback thread...")
                self.callback_trigger_thread.join(timeout=0.5)

        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

        self.logger.info("Cleanup complete, closing application")
        self.root.destroy()


def main() -> None:
    """Main entry point."""
    root = tk.Tk()
    app = MinimalDJApp(root)
    root.protocol("WM_DELETE_WINDOW", app.closeEvent)

    logger.info("Starting main event loop")
    root.mainloop()
    logger.info("Application exited")


if __name__ == '__main__':
    main()
