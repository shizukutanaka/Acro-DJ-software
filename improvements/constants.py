# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Application Constants

Centralizes all hardcoded values and magic numbers.
Makes configuration and tuning easier.
"""

# Audio Configuration
AUDIO_SAMPLE_RATE = 44100
AUDIO_CHANNELS = 2
AUDIO_BUFFER_SIZE = 1024
AUDIO_DTYPE = "float32"

# Supported audio formats
SUPPORTED_AUDIO_FORMATS = [".wav", ".flac", ".mp3", ".ogg"]
DEFAULT_AUDIO_FORMAT = ".wav"

# UI Configuration
UI_WINDOW_WIDTH = 1200
UI_WINDOW_HEIGHT = 700
UI_FONT_FAMILY = "Arial"
UI_FONT_SIZE_SMALL = 9
UI_FONT_SIZE_NORMAL = 10
UI_FONT_SIZE_LARGE = 12
UI_FONT_SIZE_TITLE = 14

# Waveform Display
WAVEFORM_WIDTH = 400
WAVEFORM_HEIGHT = 100
WAVEFORM_RESOLUTION = 512
WAVEFORM_UPDATE_INTERVAL_MS = 100

# Colors
COLOR_BG_DARK = "#2b2b2b"
COLOR_FG_LIGHT = "#ffffff"
COLOR_ACCENT_BLUE = "#007acc"
COLOR_DECK_BG = "#1e1e1e"
COLOR_WAVEFORM_FG = "#00ff00"
COLOR_WAVEFORM_BG = "#0a0a0a"

THEME_DARK = {
    "bg": COLOR_BG_DARK,
    "fg": COLOR_FG_LIGHT,
    "accent": COLOR_ACCENT_BLUE,
    "deck_bg": COLOR_DECK_BG,
    "waveform_fg": COLOR_WAVEFORM_FG,
    "waveform_bg": COLOR_WAVEFORM_BG
}

# Audio Processing
EQ_LOW_FREQ = 100
EQ_MID_FREQ = 1000
EQ_HIGH_FREQ = 10000
EQ_MIN_GAIN_DB = -12.0
EQ_MAX_GAIN_DB = 12.0
EQ_DEFAULT_GAIN_DB = 0.0

# Crossfader
CROSSFADER_MIN = 0.0
CROSSFADER_MAX = 1.0
CROSSFADER_DEFAULT = 0.5

# Volume
VOLUME_MIN_PERCENT = 0.0
VOLUME_MAX_PERCENT = 100.0
VOLUME_DEFAULT_PERCENT = 100.0
MASTER_VOLUME_MIN_PERCENT = 0.0
MASTER_VOLUME_MAX_PERCENT = 150.0
MASTER_VOLUME_DEFAULT_PERCENT = 100.0

# Playback
BPM_MIN = 60
BPM_MAX = 200
BPM_DEFAULT = 120
TEMPO_MIN_RATIO = 0.5
TEMPO_MAX_RATIO = 2.0

# Threading
AUDIO_CALLBACK_TIMEOUT_MS = 50
THREAD_SHUTDOWN_TIMEOUT_S = 5
QUEUE_MAX_SIZE = 100

# Performance thresholds
AUDIO_UNDERRUN_THRESHOLD_MS = 10
CALLBACK_MAX_TIME_MS = 20
MEMORY_WARNING_MB = 500
CPU_WARNING_PERCENT = 80

# Logging
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = "dj_mixer.log"

# Development/Testing
DEBUG_MODE = False
PROFILE_AUDIO_CALLBACK = False
LOG_BUFFER_STATS = False

# Configuration file paths
CONFIG_FILE = "config.yaml"
THEME_FILE = "theme.yaml"
STATE_FILE = "state.json"

# Plugin system
PLUGIN_DIRECTORY = "plugins"
PLUGIN_CACHE_DIR = ".plugin_cache"
PLUGIN_TIMEOUT_S = 30
PLUGIN_MAX_INSTANCES = 100

# Resource limits
MAX_CONCURRENT_DECKS = 8
MAX_WAVEFORM_CACHE_SIZE_MB = 200
MAX_UNDO_HISTORY = 50

# Version info
APP_VERSION = "3.2.0"
APP_NAME = "Acro DJ Mixer"
APP_AUTHOR = "Acro DJ Mixer Contributors"
