# DJ Mixer - Professional Tkinter DJ Application

A lightweight, feature-rich DJ mixing application built with Python and Tkinter. Designed for fast startup times and smooth audio mixing with professional-grade controls.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.8+-blue)

## Features

### Core DJ Functionality
- **Two-Deck Mixer**: Seamless mixing between Deck A and Deck B
- **Crossfader**: Smooth transitioning between decks
- **Master Volume Control**: Overall output volume management
- **Headphone Cue**: Monitor cue signal with mix/volume controls

### Audio Playback
- **Multiple Format Support**: WAV, FLAC, and MP3 audio files
- **Low-Latency Output**: Uses `sounddevice` for responsive audio
- **Real-Time Waveform Display**: Visual feedback for track position

### DJ Controls
- **BPM Detection**: Automatic tempo analysis using librosa
- **Sync Function**: Automatically match slave deck tempo to master
- **Gain Control**: Pre-fader gain adjustment (0-200%)
- **EQ Controls**: Low and High frequency adjustment
- **Pitch Control**: ±10% playback speed adjustment

### Playback Features
- **Cueing System**: Set and jump to cue points
- **Looping**: Fixed-duration 2-second loops
- **Play/Stop**: Standard playback controls
- **Position Memory**: Maintains cue and loop positions

### User Interface
- **Dark Theme**: Professional dark interface reducing eye strain
- **Responsive Design**: Scales with window resizing
- **Real-time Status**: Live feedback on audio engine and mixer state
- **Intuitive Controls**: Familiar DJ mixer layout

## System Requirements

### Minimum
- **OS**: Windows, macOS, or Linux
- **Python**: 3.8 or later
- **RAM**: 512 MB
- **Audio**: Working audio output device

### Recommended
- **Python**: 3.9 or later
- **RAM**: 2 GB
- **Storage**: 500 MB for dependencies

## Installation

### Quick Start (Windows)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/tkinter-dj-app.git
   cd tkinter-dj-app
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**:
   ```bash
   python main.py
   ```

### macOS Installation

```bash
git clone https://github.com/yourusername/tkinter-dj-app.git
cd tkinter-dj-app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Linux Installation

```bash
# Install audio dependencies (Ubuntu/Debian)
sudo apt-get install python3-pip libportaudio2 libsndfile1

# Clone and setup
git clone https://github.com/yourusername/tkinter-dj-app.git
cd tkinter-dj-app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Usage Guide

### Basic Workflow

1. **Load Tracks**:
   - Click the "Load" button on each deck
   - Select an audio file (WAV, FLAC, or MP3)
   - The app will automatically analyze the BPM

2. **Play and Mix**:
   - Click "Play" on a deck to start playback
   - Use the crossfader to blend between decks
   - Adjust deck volumes with the "Vol" slider

3. **Synchronize Tempo**:
   - Click "Sync" on the slave deck to match the master deck's BPM
   - The pitch will adjust automatically

4. **Cueing**:
   - Click "Set Cue" to mark a position
   - Click "Cue→" to jump to the cue point
   - Check "CUE" for headphone preview

5. **Looping**:
   - Check "Loop" to enable a 2-second loop at the current position
   - Uncheck to disable

### Advanced Controls

#### Gain Control
- Range: 0-200%
- 100% = unity gain (no change)
- Boost up to 200% or cut down to 0%
- Apply before master volume for better headroom

#### EQ Controls
- **Low**: Low-frequency adjustment
- **Mid**: Mid-frequency adjustment (UI preview)
- **High**: High-frequency adjustment
- Range: 0-200% (100% = neutral)

#### Pitch Control
- Range: ±10%
- Adjust playback speed
- Sync will automatically set pitch if toggled manually

#### Crossfader
- Left (A): 0% - Full Deck A
- Right (B): 100% - Full Deck B
- Center: 50% - Blend both decks

### Keyboard Shortcuts
- **Ctrl+L**: Load track to focused deck
- **Space**: Play/Stop focused deck
- **S**: Sync focused deck

## Architecture

### File Structure
```
tkinter-dj-app/
├── main.py                 # Main application
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── LICENSE                # MIT License
└── .gitignore            # Git ignore rules
```

### Core Classes

- **MinimalDJApp**: Main application window and event handling
- **DeckData**: Audio data management and playback control
- **AudioMetrics**: Track metadata and analysis results

### Audio Processing Pipeline

```
Audio File → Load → BPM Analysis
    ↓
Chunk Retrieval → Gain Applied → EQ Filtering → Volume Control → Mix
    ↓
Crossfader → Master Volume → Audio Output
```

## Performance Optimization

- **Deferred Loading**: Heavy libraries loaded only when needed
- **Threaded Operations**: File loading and BPM analysis run in background
- **Efficient Buffering**: 1024-sample buffer for responsive playback
- **Memory Management**: Minimal memory footprint (~100MB with audio loaded)

## Troubleshooting

### No Sound Output
1. Check system audio settings
2. Verify audio device is connected and working
3. Check master volume is above 0%
4. Ensure deck volume is not muted

### BPM Detection Fails
- Librosa may struggle with certain audio formats
- Try converting the track to WAV
- Check if the track has discernible beats

### Audio Crackling/Pops
- Reduce buffer overload by closing other applications
- Increase system audio buffer if possible
- Check for CPU-intensive processes

### Library Import Errors
```bash
# Clear pip cache and reinstall
pip install --no-cache-dir -r requirements.txt
```

### Audio Device Not Found
```bash
# List available audio devices
python -c "import sounddevice as sd; print(sd.query_devices())"
```

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| numpy | >=1.21.0 | Numerical operations |
| sounddevice | >=0.4.5 | Audio I/O |
| soundfile | >=0.11.0 | Audio file reading |
| librosa | >=0.10.0 | Audio analysis & BPM |
| scipy | >=1.7.0 | Signal processing (EQ) |

## Configuration

### Audio Settings
Edit constants in `main.py`:
```python
DEFAULT_SAMPLERATE = 44100  # 44.1 kHz
BUFFER_SIZE = 1024          # 1024 samples (~23ms)
LOOP_DURATION_SEC = 2.0     # 2-second loops
PITCH_RANGE_PERCENT = 10.0  # ±10% pitch range
```

### EQ Frequencies
```python
EQ_LOW_CUTOFF = 250         # Low-pass threshold (Hz)
EQ_HIGH_CUTOFF = 2000       # High-pass threshold (Hz)
EQ_FILTER_ORDER = 3         # Filter steepness
```

## Advanced Topics

### Real-Time Audio Processing
The application uses a callback-based audio engine:
- Audio callback runs at high priority
- Deck chunks are generated on demand
- Gain and EQ are applied per-sample

### BPM Synchronization
- Uses librosa's beat tracking algorithm
- Calculates tempo ratio between decks
- Automatically adjusts pitch within ±10% range

### Thread Safety
- Stream lock protects shared audio state
- Queue-based communication between threads
- Callback trigger thread maintains audio flow

## Known Limitations

1. **Pitch Shifting**: Pitch adjustment changes playback speed but doesn't use time-stretching
2. **Mid EQ**: Mid-band EQ requires complex filter design (not implemented)
3. **Multiple Formats**: Some MP3 files may require ffmpeg conversion
4. **Latency**: ~100ms typical latency depending on system

## Future Enhancements

- [ ] Time-stretch based pitch shifting
- [ ] Advanced 3-band parametric EQ
- [ ] Playlist management
- [ ] Effects (reverb, delay, filter sweep)
- [ ] MIDI controller support
- [ ] Recording and export
- [ ] Cue points with hot cues
- [ ] Automation recording

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Reporting Issues

Found a bug? Please create an issue with:
- Steps to reproduce
- Expected behavior
- Actual behavior
- System information (OS, Python version, audio device)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **numpy**: Numerical computing
- **sounddevice**: Audio I/O library
- **soundfile**: Audio file format support
- **librosa**: Music information retrieval
- **scipy**: Scientific computing and signal processing

## Support

For questions and support:
- Create an issue on GitHub
- Check existing issues for solutions
- Review the troubleshooting section

## Changelog

### Version 1.0.0 (Initial Release)
- Two-deck mixing functionality
- BPM detection and sync
- Gain and basic EQ controls
- Cue and loop features
- Professional dark UI theme
- Full logging and error handling

---

**DJ Mixer** - Mix like a Pro, Code like a Professional
