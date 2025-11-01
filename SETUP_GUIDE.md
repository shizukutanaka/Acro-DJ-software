# DJ Mixer - Complete Setup Guide

This guide provides step-by-step instructions for setting up DJ Mixer on various operating systems.

## Table of Contents
1. [Windows Setup](#windows-setup)
2. [macOS Setup](#macos-setup)
3. [Linux Setup](#linux-setup)
4. [Troubleshooting](#troubleshooting)
5. [Audio Device Configuration](#audio-device-configuration)

## Windows Setup

### Requirements
- Windows 10 or later
- Python 3.8 or higher
- At least 500MB free disk space

### Step-by-Step Installation

1. **Install Python**:
   - Download from https://www.python.org/downloads/
   - Run the installer
   - **Important**: Check "Add Python to PATH"
   - Click "Install Now"

2. **Verify Installation**:
   ```cmd
   python --version
   ```

3. **Clone Repository**:
   ```cmd
   git clone https://github.com/yourusername/tkinter-dj-app.git
   cd tkinter-dj-app
   ```

4. **Create Virtual Environment**:
   ```cmd
   python -m venv venv
   .\venv\Scripts\activate
   ```

5. **Install Dependencies**:
   ```cmd
   pip install -r requirements.txt
   ```

6. **Run Application**:
   ```cmd
   python main.py
   ```

### Audio Device Setup (Windows)

1. **Check Audio Devices**:
   ```cmd
   python -c "import sounddevice as sd; print(sd.query_devices())"
   ```

2. **Select Default Device**:
   - Right-click speaker icon in taskbar
   - Click "Open Sound settings"
   - Set preferred audio device as default

3. **Test Audio**:
   - Load a test audio file
   - Click "Play"
   - Verify sound output

## macOS Setup

### Requirements
- macOS 10.14 or later
- Python 3.8 or higher
- Homebrew (optional but recommended)

### Step-by-Step Installation

1. **Install Python** (using Homebrew):
   ```bash
   brew install python3
   ```

   Or download from https://www.python.org/downloads/

2. **Verify Installation**:
   ```bash
   python3 --version
   ```

3. **Clone Repository**:
   ```bash
   git clone https://github.com/yourusername/tkinter-dj-app.git
   cd tkinter-dj-app
   ```

4. **Create Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

5. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

6. **Install Audio Drivers** (if needed):
   ```bash
   brew install portaudio
   ```

7. **Run Application**:
   ```bash
   python main.py
   ```

### Audio Device Setup (macOS)

1. **Check Audio Devices**:
   ```bash
   python3 -c "import sounddevice as sd; print(sd.query_devices())"
   ```

2. **System Audio Settings**:
   - Apple Menu → System Preferences
   - Click "Sound"
   - Select output device under "Output"

## Linux Setup

### Debian/Ubuntu

1. **Install Python and Dependencies**:
   ```bash
   sudo apt-get update
   sudo apt-get install python3-pip python3-venv libportaudio2 libsndfile1
   ```

2. **Clone Repository**:
   ```bash
   git clone https://github.com/yourusername/tkinter-dj-app.git
   cd tkinter-dj-app
   ```

3. **Create Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

4. **Install Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Run Application**:
   ```bash
   python3 main.py
   ```

### Fedora/RHEL

1. **Install Python and Dependencies**:
   ```bash
   sudo dnf install python3-pip portaudio-devel libsndfile-devel
   ```

2. **Clone and Setup** (same as Debian/Ubuntu above)

### Audio Device Setup (Linux)

1. **Install ALSA (Advanced Linux Sound Architecture)**:
   ```bash
   sudo apt-get install alsa-utils
   ```

2. **List Audio Devices**:
   ```bash
   python3 -c "import sounddevice as sd; print(sd.query_devices())"
   ```

3. **Configure Default Device**:
   ```bash
   alsamixer
   ```
   - Select audio device from list
   - Adjust levels as needed

## Audio Device Configuration

### Selecting a Specific Audio Device

To use a specific audio device, modify `main.py`:

```python
# Find your device ID
import sounddevice as sd
print(sd.query_devices())

# Set device in main.py (around line 400)
audio_stream = sd.OutputStream(
    device=3,  # Replace 3 with your device ID
    samplerate=DEFAULT_SAMPLERATE,
    blocksize=BUFFER_SIZE,
    channels=2,
    callback=self.audio_callback,
    dtype=np.float32
)
```

### Testing Audio Output

1. **Create Test Script**:
   ```python
   import sounddevice as sd
   import numpy as np

   # Generate test tone (440 Hz, 1 second)
   sample_rate = 44100
   duration = 1
   frequency = 440

   t = np.linspace(0, duration, int(sample_rate * duration))
   audio = np.sin(2 * np.pi * frequency * t) * 0.3

   sd.play(audio, sample_rate)
   sd.wait()
   ```

2. **Run Test**:
   ```bash
   python test_audio.py
   ```

## Troubleshooting

### No Audio Output

**Problem**: No sound comes from speakers

**Solutions**:
1. Check system volume is not muted
2. Verify audio device is connected
3. Check device is set as default
4. Try different audio device
5. Restart the application

### Library Installation Fails

**Problem**: `pip install` fails with dependency errors

**Solutions**:
```bash
# Clear pip cache
pip install --no-cache-dir -r requirements.txt

# Update pip
pip install --upgrade pip

# Install specific versions manually
pip install numpy==1.21.0
pip install sounddevice==0.4.5
```

### Python Not Found

**Problem**: `python: command not found`

**Windows**:
- Add Python to PATH
- Reinstall Python and check "Add to PATH"

**macOS/Linux**:
```bash
# Use python3 instead
python3 main.py

# Or create alias
alias python=python3
```

### Audio Device Not Recognized

**Problem**: Device doesn't appear in device list

**Solutions**:
1. Check device is connected properly
2. Update audio drivers
3. Restart computer
4. Try different USB port

### High CPU Usage

**Problem**: Application uses excessive CPU

**Solutions**:
1. Reduce buffer size in constants (try 512)
2. Close other applications
3. Check for malware/background processes
4. Update Python and libraries

### Crackling/Distorted Audio

**Problem**: Audio sounds distorted or has dropouts

**Solutions**:
1. Reduce master volume
2. Reduce individual deck gain
3. Increase system audio buffer
4. Close CPU-intensive applications
5. Update audio drivers

## Performance Tips

1. **Optimize Settings**:
   - Sample rate: 44100 Hz (standard)
   - Buffer size: 1024 samples (good latency/CPU balance)

2. **System Maintenance**:
   - Close unnecessary applications
   - Update OS and drivers
   - Disable visual effects
   - Check system resources

3. **Audio Files**:
   - Use WAV format for best compatibility
   - 44100 Hz, 16-bit or 24-bit preferred
   - Mono or stereo (automatically converted to mono)

## Uninstalling

### Windows
```cmd
rmdir /s venv
rmdir /s __pycache__
```

### macOS/Linux
```bash
rm -rf venv
rm -rf __pycache__
rm -rf .pytest_cache
```

## Getting Help

1. Check this guide first
2. Review README.md troubleshooting section
3. Search GitHub issues
4. Create a new issue with:
   - OS and Python version
   - Steps to reproduce
   - Error messages
   - System information

## Next Steps

After successful installation:
1. Read README.md for features overview
2. Load some audio files to test
3. Try different audio devices
4. Explore all controls and features
5. Check for updates regularly

---

**Happy Mixing!**
