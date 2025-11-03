# Research Integration Guide

Integration of research-based enhancements into Acro DJ Mixer based on web research findings.

---

## Overview

This guide provides step-by-step instructions for integrating 4 new advanced modules:

1. **beat_analyzer.py** - Music information retrieval for tempo/beat/key detection
2. **spectrum_analyzer.py** - Real-time FFT-based frequency analysis
3. **thread_pool_manager.py** - Centralized task scheduling and resource management
4. **memory_pool.py** - Pre-allocated buffer pooling for low GC pressure

---

## Phase 1: Beat Analysis Integration

### 1.1 Install Dependencies

```bash
pip install librosa numpy
```

### 1.2 Import in main.py

```python
from improvements.beat_analyzer import BeatAnalyzer, analyze_track
from improvements.thread_pool_manager import ThreadPoolManager, TaskPriority
```

### 1.3 Initialize Beat Analyzer

In your main DJ application class:

```python
class DJMixer:
    def __init__(self):
        # ... existing initialization ...
        self.beat_analyzer = BeatAnalyzer(sr=44100)
        self.thread_pool = ThreadPoolManager(max_workers=4)
```

### 1.4 Analyze Track on Load

Replace file loading with analysis:

```python
def load_track(self, filepath):
    """Load track with beat analysis."""
    # Existing file loading code...

    # Schedule background analysis
    def on_analysis_complete(result):
        if result and result.is_valid():
            self.current_deck.tempo = result.tempo
            self.current_deck.beats = result.beats
            self.current_deck.beat_times = result.beat_times
            print(f"Detected BPM: {result.tempo:.1f}")

    self.thread_pool.submit(
        analyze_track,
        filepath,
        task_id=f"analyze_{filepath}",
        priority=TaskPriority.HIGH,
        callback=on_analysis_complete
    )
```

### 1.5 Synchronize Decks Using Beat Info

```python
def sync_to_master(self):
    """Sync slave deck to master deck BPM."""
    if not self.master_deck.beat_times or not self.slave_deck.beat_times:
        return

    master_tempo = self.master_deck.tempo
    slave_tempo = self.slave_deck.tempo

    # Calculate tempo ratio for resampling
    tempo_ratio = slave_tempo / master_tempo

    # Apply to audio playback (implementation specific)
    self.slave_deck.set_playback_speed(tempo_ratio)
```

---

## Phase 2: Spectrum Analyzer Integration

### 2.1 Install Dependencies

```bash
pip install numpy scipy
```

### 2.2 Import in main.py

```python
from improvements.spectrum_analyzer import (
    SpectrumAnalyzer, EQAnalyzer, MultiChannelAnalyzer
)
```

### 2.3 Initialize Analyzers

```python
class DJMixer:
    def __init__(self):
        # ... existing code ...
        self.spectrum_analyzer = SpectrumAnalyzer(
            sr=44100,
            n_fft=1024,
            smoothing_frames=4
        )
        self.eq_analyzer = EQAnalyzer(self.spectrum_analyzer)
```

### 2.4 Update Visualization Loop

In your main event loop (every 30-50ms):

```python
def update_visualizations(self):
    """Update spectrum display."""
    # Get current audio chunk from playback
    audio_chunk = self.get_current_audio_chunk(1024)

    if audio_chunk is not None:
        # Analyze spectrum
        spectrum = self.spectrum_analyzer.analyze_frame(audio_chunk)

        # Get EQ band levels for visualization
        eq_levels = self.eq_analyzer.get_eq_bands(spectrum)

        # Update Tkinter canvas
        self.update_spectrum_display(
            spectrum.magnitudes_db,
            spectrum.frequencies
        )
```

### 2.5 Add Real-Time EQ Display

```python
def draw_eq_bars(self, canvas, eq_levels):
    """Draw EQ bar graph."""
    x_pos = 50
    for band_name, level_db in eq_levels.items():
        # Convert dB to visual height
        height = max(0, (level_db + 80) / 80 * 200)  # 0 to 200 pixels

        canvas.create_rectangle(
            x_pos, 300 - height,
            x_pos + 20, 300,
            fill='#00ff00'
        )

        canvas.create_text(
            x_pos + 10, 320,
            text=band_name,
            fill='white'
        )

        x_pos += 30
```

---

## Phase 3: Thread Pool Manager Integration

### 3.1 Replace Synchronous File Operations

**Before:**
```python
def load_track(self, filepath):
    # Blocks UI while loading
    audio_data = load_audio_file(filepath)
    metadata = parse_metadata(filepath)
```

**After:**
```python
def load_track(self, filepath):
    """Non-blocking track loading."""

    def load_and_parse():
        audio_data = load_audio_file(filepath)
        metadata = parse_metadata(filepath)
        return {'audio': audio_data, 'metadata': metadata}

    def on_loaded(result):
        self.current_deck.set_audio(result['audio'])
        self.current_deck.set_metadata(result['metadata'])
        self.status_bar.config(text="Ready")

    self.status_bar.config(text="Loading...")

    self.thread_pool.submit(
        load_and_parse,
        task_id=f"load_{os.path.basename(filepath)}",
        priority=TaskPriority.HIGH,
        callback=on_loaded
    )
```

### 3.2 Batch Loading (for library)

```python
from improvements.thread_pool_manager import BatchTaskProcessor

def load_library(self, file_list):
    """Load multiple files in parallel."""
    processor = BatchTaskProcessor(
        self.thread_pool,
        on_progress=self.on_load_progress,
        on_complete=self.on_library_loaded
    )

    processor.process_batch(
        file_list,
        load_and_analyze_track,
        priority=TaskPriority.NORMAL
    )

def on_load_progress(self, completed, total):
    """Update progress bar."""
    pct = int(100 * completed / total)
    self.progress_var.set(pct)
    print(f"Loading: {pct}%")

def on_library_loaded(self, results):
    """Update library with loaded tracks."""
    self.library.extend(results)
    print(f"Library loaded: {len(results)} tracks")
```

### 3.3 Monitor Thread Pool Health

```python
def show_pool_statistics(self):
    """Display thread pool statistics."""
    stats = self.thread_pool.get_statistics()

    print(f"Thread Pool Stats:")
    print(f"  Total tasks: {stats['total']}")
    print(f"  Completed: {stats['completed']}")
    print(f"  Failed: {stats['failed']}")
    print(f"  Success rate: {stats['success_rate']:.1%}")
    print(f"  Avg time: {stats['average_time']:.3f}s")
    print(f"  Active tasks: {self.thread_pool.get_active_task_count()}")
```

---

## Phase 4: Memory Pool Integration

### 4.1 Replace Manual Buffer Allocation

**Before:**
```python
def audio_callback(self, indata, outdata, frames, time_info, status):
    # Allocates new buffer every callback (high GC pressure)
    mix_buffer = np.zeros((2, frames), dtype='float32')
    # ... processing ...
```

**After:**
```python
from improvements.memory_pool import get_memory_pool_manager

def __init__(self):
    self.memory_pool = get_memory_pool_manager()

def audio_callback(self, indata, outdata, frames, time_info, status):
    # Acquire from pool (zero-allocation)
    mix_buffer = self.memory_pool.acquire_audio_buffer()

    try:
        # ... processing ...
        outdata[:] = mix_buffer
    finally:
        # Return to pool (important!)
        self.memory_pool.release_audio_buffer(mix_buffer)
```

### 4.2 Visualization Buffer Pooling

```python
def update_waveform_display(self):
    """Update waveform with pooled buffers."""
    # Acquire visualization buffer
    viz_data = self.memory_pool.acquire_viz_buffer()

    try:
        # Compute or fetch waveform data
        waveform_decimated = decimate_waveform(self.audio_data, len(viz_data))
        viz_data[:] = waveform_decimated

        # Draw on canvas
        self.draw_waveform(viz_data)
    finally:
        # Return to pool
        self.memory_pool.release_viz_buffer(viz_data)
```

### 4.3 Metadata Caching

```python
def load_track_with_cache(self, filepath):
    """Load track with metadata caching."""
    # Check cache first
    cached = self.memory_pool.get_cached_metadata(filepath)
    if cached:
        print(f"Using cached metadata for {filepath}")
        return cached

    # Load and cache
    metadata = self.thread_pool.submit(
        parse_full_metadata,
        filepath,
        callback=lambda m: self.memory_pool.cache_metadata(filepath, m)
    )

    return metadata
```

### 4.4 Monitor Memory Usage

```python
def show_memory_statistics(self):
    """Display memory pool statistics."""
    stats = self.memory_pool.get_statistics()

    print(f"Memory Pool Stats:")
    print(f"  Audio pool: {stats['audio_pool'].total_memory_mb:.2f} MB")
    print(f"  Cache size: {stats['metadata_cache_size']} items")
    print(f"  Audio acquired: {stats['audio_pool'].acquired}")
    print(f"  Audio released: {stats['audio_pool'].released}")
```

---

## Integration Checklist

### Immediate (This Session)
- [ ] Create beat_analyzer.py
- [ ] Create spectrum_analyzer.py
- [ ] Create thread_pool_manager.py
- [ ] Create memory_pool.py
- [ ] Commit to GitHub

### Week 1
- [ ] Install librosa and scipy dependencies
- [ ] Initialize ThreadPoolManager in main.py
- [ ] Add BeatAnalyzer for track analysis
- [ ] Test beat detection on sample library

### Week 2
- [ ] Initialize SpectrumAnalyzer in main.py
- [ ] Add spectrum visualization to waveform display
- [ ] Replace synchronous file loading with thread pool
- [ ] Add progress indicators for async operations

### Week 3
- [ ] Implement memory pool for audio callbacks
- [ ] Test for GC pause reduction (profiling)
- [ ] Add EQ analyzer display
- [ ] Implement metadata caching

### Week 4
- [ ] Optimize thread pool worker count
- [ ] Add thread pool statistics display
- [ ] Test batch operations (library loading)
- [ ] Profile memory usage and performance

---

## Performance Targets

After integration, verify these improvements:

### Beat Detection
- Track analysis time: <5s per track (background)
- BPM detection accuracy: >95% on professional DJ tracks
- Sync lock stability: Zero dropouts

### Spectrum Analyzer
- FFT computation: <5ms per frame
- Display update: 30 Hz (33ms intervals)
- Memory: <50MB for spectrum history

### Thread Pool
- Non-blocking file load: <100ms UI latency
- Batch load of 100 tracks: <2 minutes
- Active task tracking: Accurate within 1 task

### Memory Pool
- GC pause reduction: >70%
- Buffer acquisition time: <1μs
- Memory stability: No growth during 1hr playback

---

## Troubleshooting

### librosa Not Installed

```python
# Graceful fallback if librosa unavailable
try:
    beat_result = analyzer.analyze_file(filepath)
except RuntimeError:
    print("librosa not available - beat detection disabled")
    beat_result = None
```

### Thread Pool Deadlock

```python
# Check for deadlock patterns
if thread_pool.get_active_task_count() > 10:
    logger.warning("High task count - possible deadlock")

# Always use timeout for blocking waits
try:
    result = thread_pool.wait_for_task(task_id, timeout=10.0)
except TimeoutError:
    logger.error("Task timeout - possible deadlock")
```

### Memory Pool Exhaustion

```python
# Monitor and warn if approaching limit
with memory_pool:
    buffer = memory_pool.acquire_audio_buffer()
    # Use buffer...
    # Auto-release when exiting context

# Check stats
if stats['audio_pool'].acquired > pool_size:
    logger.warning("Audio pool exhausted!")
```

---

## Migration Path (Optional)

If existing code needs compatibility:

```python
# Wrapper for gradual migration
class CompatibilityLayer:
    def __init__(self, thread_pool):
        self.thread_pool = thread_pool

    def load_track_sync(self, filepath):
        """Synchronous interface for compatibility."""
        future = self.thread_pool.submit(load_track, filepath)
        return future.result()  # Blocking - for compatibility

# Usage
compat = CompatibilityLayer(thread_pool)
track = compat.load_track_sync(filepath)  # Old-style blocking
```

---

## Testing Strategy

### Unit Tests

```python
# test_beat_analyzer.py
def test_beat_detection():
    analyzer = BeatAnalyzer()
    result = analyzer.analyze_file('test_audio.wav')
    assert result.is_valid()
    assert result.tempo > 80 and result.tempo < 160

# test_spectrum_analyzer.py
def test_spectrum_computation():
    analyzer = SpectrumAnalyzer()
    chunk = np.random.randn(1024).astype('float32')
    spectrum = analyzer.analyze_frame(chunk)
    assert len(spectrum.frequencies) > 0
    assert len(spectrum.magnitudes_db) > 0

# test_thread_pool_manager.py
def test_task_execution():
    manager = ThreadPoolManager()
    result = manager.submit(lambda x: x*2, 5).result()
    assert result == 10

# test_memory_pool.py
def test_buffer_pooling():
    pool = AudioBufferPool(pool_size=4)
    buf1 = pool.acquire()
    buf2 = pool.acquire()
    pool.release(buf1)
    buf3 = pool.acquire()  # Should get buf1
    assert buf1 is buf3
```

### Integration Tests

```python
def test_full_pipeline():
    """Test all modules working together."""
    with ThreadPoolManager() as thread_pool:
        memory_pool = get_memory_pool_manager()
        beat_analyzer = BeatAnalyzer()

        # Load and analyze
        future = thread_pool.submit(
            analyze_track,
            'test.wav'
        )
        result = future.result()

        # Verify results
        assert result['beat'].is_valid()
        assert memory_pool.get_statistics() is not None
```

---

## References

- **Research Document**: RESEARCH_FINDINGS_AND_RECOMMENDATIONS.md
- **Librosa Docs**: https://librosa.org/
- **Python Concurrency**: https://docs.python.org/3/library/concurrent.futures.html
- **NumPy/SciPy FFT**: https://docs.scipy.org/doc/scipy/reference/fftpack.html

---

**Document Status**: Ready for Implementation
**Version**: 1.0
**Updated**: November 4, 2025
