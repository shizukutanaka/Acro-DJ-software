# Acro DJ Mixer - Project Structure

This document describes the project organization and component relationships.

## Directory Layout

```
acro-dj-mixer/
├── plugins/                    # Plugin system framework
│   ├── __init__.py
│   ├── plugin_api.py          # Base plugin classes (AudioEffect, Tool, Visualizer, etc.)
│   ├── plugin_config.py       # Configuration and parameter management
│   ├── plugin_versioning.py   # Semantic versioning and dependency resolution
│   ├── plugin_validator.py    # Security validation and AST analysis
│   ├── plugin_documentation.py # Auto-documentation generation
│   ├── plugin_profiling.py    # Performance monitoring
│   ├── plugin_communication.py # Inter-plugin messaging
│   ├── plugin_state.py        # State persistence and snapshots
│   ├── plugin_events.py       # Pub/sub event system
│   ├── plugin_resources.py    # Resource quota management
│   ├── plugin_dependency_injection.py # IoC container
│   ├── plugin_lifecycle.py    # Plugin lifecycle management
│   ├── plugin_sandbox.py      # Security sandbox
│   ├── plugin_marketplace_cli.py # Command-line interface
│   ├── plugin_testing.py      # Testing utilities
│   ├── plugin_installer.py    # Plugin installation
│   ├── marketplace_registry.py # Plugin registry
│   ├── library_management.py  # Music library tools
│   ├── professional_eq.py     # Example EQ effect plugin
│   ├── multi_effect_processor.py # Example multi-effect plugin
│   └── template_effect_plugin.py # Developer template
│
├── tests/                      # Test suite
│   ├── conftest.py           # Pytest configuration
│   ├── test_plugin_api.py
│   ├── test_plugin_config.py
│   ├── test_plugin_versioning.py
│   ├── test_plugin_documentation.py
│   ├── test_plugin_profiling.py
│   ├── test_plugin_advanced_features.py
│   ├── test_plugin_advanced_systems.py
│   ├── test_plugins.py
│   ├── test_audio_processing.py
│   └── ... (other test files)
│
├── examples/                   # Example plugins
│   └── sample_midi_controller_plugin.py
│
├── main.py                     # Application entry point
├── config.py                   # Configuration management
├── logging_config.py          # Logging setup
├── audio_processing.py        # Audio processing utilities
├── translations.py            # Multilingual support
│
├── setup.py                    # Legacy setup file (uses pyproject.toml)
├── pyproject.toml             # Modern package configuration
├── MANIFEST.in                # Package manifest
├── LICENSE                    # MIT License
├── README.md                  # Project overview
├── CONTRIBUTING.md            # Contribution guidelines
├── STRUCTURE.md              # This file
└── .gitignore                # Git ignore rules
```

## Core Components

### Application (`main.py`)
- Tkinter-based GUI
- Two-deck DJ mixing interface
- Audio playback and synchronization
- BPM detection and tempo matching
- EQ and gain controls
- Looping and cueing

### Plugin System (`plugins/`)
Complete plugin framework with:
- **15+ module files** providing comprehensive functionality
- **50+ classes** for plugin development
- **200+ public APIs**
- **400+ test cases** for reliability
- **Production-ready** security, performance, and stability

### Configuration (`config.py`)
- Settings management with Pydantic
- Multi-language support
- User preferences
- Audio device configuration

### Audio Processing (`audio_processing.py`)
- Audio file loading and processing
- Beat detection
- Tempo synchronization
- Audio effects

### Testing (`tests/`)
- Unit tests for all plugin systems
- Integration tests
- Performance benchmarks
- Mock objects and fixtures

## Design Principles

This project follows clean code principles from industry leaders:

### Simplicity (John Carmack)
- Minimal dependencies
- Clear, focused responsibilities
- Fast compilation and execution

### Clean Code (Robert C. Martin)
- Meaningful names
- Small, focused functions
- Comprehensive error handling
- Well-documented APIs

### Practical Design (Rob Pike)
- Minimal but complete APIs
- Orthogonal design
- Practical over theoretical
- Single version management

## Version Management

- **Single Version**: Project uses one current version branch
- **Semantic Versioning**: MAJOR.MINOR.PATCH format
- **Changelog**: Track changes in pyproject.toml
- **No branching**: Maintain single production codebase

## Plugin Development

See [README.md](README.md) for quick start. Full documentation available in `plugins/` docstrings.

### Example Plugin
```python
from plugins.plugin_api import AudioEffectPlugin, PluginMetadata

class MyEffect(AudioEffectPlugin):
    def __init__(self):
        super().__init__(PluginMetadata(
            name="My Effect",
            version="1.0.0",
            author="Your Name"
        ))

    def process_audio(self, audio):
        return audio * 1.2  # Simple gain
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_plugin_api.py -v

# With coverage
pytest tests/ --cov=plugins --cov-report=html
```

## Building and Distribution

```bash
# Install in development mode
pip install -e ".[dev]"

# Build package
python -m build

# Upload to PyPI (requires credentials)
python -m twine upload dist/*
```

## Dependencies

### Core
- Python 3.8+
- psutil (resource monitoring)

### Audio (optional, for full features)
- numpy
- sounddevice
- soundfile
- librosa
- scipy

### Development
- pytest
- pytest-cov
- black
- flake8
- mypy

## Support

- **Issues**: GitHub Issues for bugs and feature requests
- **Documentation**: See `plugins/` docstrings and README.md
- **Examples**: See `examples/` directory
- **Tests**: See `tests/` for usage examples

## License

MIT License - see [LICENSE](LICENSE) file
