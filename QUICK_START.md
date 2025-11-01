# DJ Mixer - Quick Start Guide

Get up and running with DJ Mixer in 5 minutes!

## 1. Installation (2 minutes)

### Windows
```cmd
git clone https://github.com/yourusername/tkinter-dj-app.git
cd tkinter-dj-app
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### macOS/Linux
```bash
git clone https://github.com/yourusername/tkinter-dj-app.git
cd tkinter-dj-app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

## 2. First Run (1 minute)

When the application starts:
1. You'll see two empty decks (A and B)
2. Check your audio is working (you should hear nothing yet)
3. Ready to load tracks!

## 3. Load Your First Track (1 minute)

1. **Click "Load"** on Deck A
2. **Select** an audio file (WAV, FLAC, or MP3)
3. Wait for BPM analysis to complete
4. You'll see the track name and detected BPM

## 4. Play Music (30 seconds)

1. **Click "Play"** on Deck A
2. **Adjust volume** with the "Vol" slider if needed
3. **Adjust master volume** at the bottom if needed
4. You should hear music!

## 5. Load and Mix Second Track (1 minute)

1. **Click "Load"** on Deck B
2. Select another audio file
3. **Click "Play"** on Deck B
4. **Use the crossfader** at the bottom to mix between decks
   - Left = More Deck A
   - Right = More Deck B
   - Center = Equal mix

## That's It!

You're now mixing! Here's what to try next:

### Optional Features

**Sync Decks**
- Click "Sync" on Deck B to match Deck A's tempo
- The pitch will automatically adjust

**Set Cue Points**
- Click "Set Cue" to mark a position
- Click "Cue→" to jump back to it

**Loop Section**
- Check "Loop" to loop a 2-second section
- Great for dropping beats!

**Adjust Gain**
- Use "Gain" slider for volume control before mixing
- Range: 0-200% (100% = normal)

**Adjust EQ**
- Use Low/Mid/High sliders for tone control
- Range: 0-200% (100% = neutral)

**Adjust Pitch**
- Slide the "Pitch" control up/down
- Range: ±10%

## Controls Overview

```
┌─────────────────────────────────┐
│         DECK A | DECK B         │
├──────────────┬──────────────────┤
│              │                  │
│ Waveform     │ Waveform         │
│              │                  │
├──────────────┼──────────────────┤
│ Play Stop    │ Play Stop        │
│ Set Cue Cue→ │ Set Cue Cue→     │
│ Sync Loop    │ Sync Loop        │
│ Pitch: ±10%  │ Pitch: ±10%      │
│ Vol: 0-100%  │ Vol: 0-100%      │
│ Gain: 0-200% │ Gain: 0-200%     │
│ Low Mid High │ Low Mid High     │
│ BPM: XXX     │ BPM: XXX         │
└──────────────┴──────────────────┘

A ◄──────X───────► B  ← Crossfader
Master: 0-100%
Cue Mix: 0-100%
Cue Vol: 0-100%
```

## Keyboard Shortcuts (Future)

Currently in development:
- Space: Play/Stop
- Ctrl+L: Load track
- S: Sync deck

## Tips for Better Mixing

1. **Listen to Both Decks**:
   - Use cue mix to preview the next track
   - Set cue mix to 50% to hear both

2. **Match Tempos First**:
   - Click "Sync" to match BPM automatically
   - Fine-tune with pitch slider if needed

3. **Use Gain Wisely**:
   - Boost gain before mixing (within -0dB)
   - Preserve headroom for master volume

4. **EQ for Blending**:
   - Cut lows on incoming track
   - Boost high on outgoing track
   - Create smooth transitions

5. **Practice Beatmatching**:
   - Use loop to practice sync points
   - Match drop points for clean transitions

## Common Issues

### No Sound?
- Check master volume > 0%
- Check deck volume > 0%
- Check system audio isn't muted
- Make sure a track is loaded

### BPM Won't Detect?
- Try converting to WAV format
- Try a different track
- BPM detection works best with clear beats

### Audio Crackling?
- Lower master volume
- Lower individual deck gains
- Close other applications

### Can't Find Audio Files?
- Make sure file is in a supported format
- WAV and FLAC work best
- MP3 may require conversion

## File Formats

**Recommended**:
- WAV (best quality, larger files)
- FLAC (compressed, lossless)

**Supported**:
- MP3 (may require ffmpeg)

**Not Supported**:
- AAC, M4A
- OGG (needs decoder)

## Next Steps

1. **Read README.md** for full feature list
2. **Check SETUP_GUIDE.md** for advanced setup
3. **See CONTRIBUTING.md** if you want to help improve

## Getting Help

1. Check the troubleshooting in README.md
2. Review SETUP_GUIDE.md
3. Create an issue on GitHub

## Have Fun!

You're now a DJ Mixer user! Enjoy mixing, and don't forget to have fun!

---

**More Questions?** Check the full documentation:
- **Features & Advanced**: README.md
- **Installation Help**: SETUP_GUIDE.md
- **Want to Contribute**: CONTRIBUTING.md
