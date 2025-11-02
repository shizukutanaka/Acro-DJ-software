# Acro DJ Mixer Plugin Template

This is a template for creating plugins for Acro DJ Mixer.

## Quick Start

### 1. Create Plugin Directory

```bash
mkdir my-acro-plugin
cd my-acro-plugin
```

### 2. Project Structure

```
my-acro-plugin/
├── README.md
├── LICENSE
├── pyproject.toml
├── my_plugin/
│   ├── __init__.py
│   ├── effect.py          # For AcroEffect plugins
│   ├── controller.py      # For AcroController plugins
│   └── visualizer.py      # For AcroVisualizer plugins
└── tests/
    └── test_my_plugin.py
```

### 3. Create pyproject.toml

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-acro-plugin"
version = "1.0.0"
description = "My custom Acro DJ Mixer plugin"
authors = [{name = "Your Name", email = "you@example.com"}]
license = {text = "MIT"}
requires-python = ">=3.8"
dependencies = [
    "acro-dj-mixer>=2.5.0",
    "numpy>=1.20.0",
]

[project.entry-points."acro.effects"]
my_effect = "my_plugin.effect:MyCustomEffect"

[project.entry-points."acro.controllers"]
my_controller = "my_plugin.controller:MyCustomController"

[project.entry-points."acro.visualizers"]
my_visualizer = "my_plugin.visualizer:MyCustomVisualizer"
```

### 4. Create Plugin Class

For Audio Effect:

```python
from plugin_api import AcroEffect
import numpy as np
from typing import Any

class MyCustomEffect(AcroEffect):
    name = "My Custom Effect"
    category = "Utility"
    version = "1.0.0"
    author = "Your Name"
    description = "Description of my effect"

    def process(
        self,
        audio: np.ndarray,
        sample_rate: int,
        **params: Any,
    ) -> np.ndarray:
        """Process audio with the effect."""
        # Your effect code here
        return audio.astype(np.float32)

    def get_parameters(self) -> dict[str, Any]:
        """Define effect parameters."""
        return {
            "intensity": {
                "type": "float",
                "min": 0.0,
                "max": 1.0,
                "default": 0.5,
                "label": "Intensity",
            }
        }

    def validate(self) -> bool:
        """Validate plugin compatibility."""
        return True
```

For MIDI Controller:

```python
from plugin_api import AcroController
from typing import Any

class MyCustomController(AcroController):
    name = "My MIDI Controller"
    category = "MIDI"
    version = "1.0.0"
    author = "Your Name"
    description = "Support for my MIDI controller"

    def connect(self) -> bool:
        """Connect to controller."""
        return True

    def disconnect(self) -> None:
        """Disconnect from controller."""
        pass

    def process_input(self) -> dict[str, Any]:
        """Process controller input."""
        return {}

    def validate(self) -> bool:
        """Validate controller compatibility."""
        return True
```

### 5. Install Plugin

Development mode:

```bash
pip install -e .
```

Production:

```bash
pip install my-acro-plugin
```

### 6. Test Plugin

```bash
pytest tests/
```

### 7. Publish to PyPI

```bash
pip install build twine

python -m build

twine upload dist/*
```

## Plugin Types

### Audio Effects (AcroEffect)

Process audio signals with custom effects.

**Example**: EQ, Compressor, Reverb, Delay, Distortion

### MIDI Controllers (AcroController)

Handle input from MIDI controllers.

**Example**: Generic MIDI, Pioneer DDJ, Numark, etc.

### Visualizers (AcroVisualizer)

Provide real-time visual feedback.

**Example**: Spectrum Analyzer, Waveform Display, 3D Visualization

## Best Practices

### Code Quality

```bash
# Install development dependencies
pip install ruff mypy

# Lint code
ruff check .

# Type checking
mypy my_plugin/
```

### Testing

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run tests
pytest

# Check coverage
pytest --cov=my_plugin
```

### Documentation

- Write docstrings for all public methods
- Include usage examples
- Document parameters and return types
- Add installation and usage instructions to README

### Performance

- Use NumPy for audio processing
- Avoid unnecessary copies
- Profile code to identify bottlenecks
- Consider memory usage for long-running effects

## Example Plugins

See official examples in the `examples/` directory of Acro DJ Mixer:

- `sample_effect_plugin.py` - Audio effects (Volume, Distortion, Phaser)
- `sample_midi_controller_plugin.py` - MIDI controllers
- `sample_visualizer_plugin.py` - Visualizers

## API Reference

### AcroEffect

```python
class AcroEffect(ABC):
    """Base class for audio effect plugins."""

    name: str  # Effect name
    category: str  # Category (Utility, Filter, Saturation, etc.)
    version: str  # Plugin version
    author: str  # Plugin author
    description: str  # Plugin description

    def process(
        self,
        audio: np.ndarray,
        sample_rate: int,
        **params: Any,
    ) -> np.ndarray:
        """Process audio with the effect."""
        ...

    def get_parameters(self) -> dict[str, Any]:
        """Get effect parameters."""
        ...

    def validate(self) -> bool:
        """Validate plugin compatibility."""
        ...
```

### AcroController

```python
class AcroController(ABC):
    """Base class for controller plugins."""

    name: str
    category: str
    version: str
    author: str
    description: str

    def connect(self) -> bool:
        """Connect to controller."""
        ...

    def disconnect(self) -> None:
        """Disconnect from controller."""
        ...

    def process_input(self) -> dict[str, Any]:
        """Process controller input."""
        ...

    def validate(self) -> bool:
        """Validate controller compatibility."""
        ...
```

## Troubleshooting

### Plugin not loading

1. Check entry point name in `pyproject.toml`
2. Verify package is installed: `pip list`
3. Check plugin manager logs: `acro-gui --log-level DEBUG`

### Plugin crashes

1. Add error handling to process methods
2. Validate input parameters
3. Test with different audio formats
4. Check memory usage

### Performance issues

1. Use NumPy for vectorized operations
2. Avoid loops over audio samples
3. Pre-compute filters and coefficients
4. Profile code: `python -m cProfile`

## Resources

- [Acro DJ Mixer Documentation](https://acro-dj-mixer.readthedocs.io)
- [Plugin API Reference](https://acro-dj-mixer.readthedocs.io/api/)
- [Plugin Development Guide](https://acro-dj-mixer.readthedocs.io/developer/plugin_development/)
- [GitHub Discussions](https://github.com/acro-dj-mixer/acro-dj-mixer/discussions)

## License

Plugins should be licensed under a compatible open-source license (MIT, GPL, etc.).

## Support

For help with plugin development:

1. Check the [FAQ](https://acro-dj-mixer.readthedocs.io/community/faq/)
2. Search [GitHub Issues](https://github.com/acro-dj-mixer/acro-dj-mixer/issues)
3. Ask in [GitHub Discussions](https://github.com/acro-dj-mixer/acro-dj-mixer/discussions)
4. Email: plugins@acro-dj-mixer.dev

Happy plugin development!
