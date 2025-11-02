# Acro DJ Mixer v3.x

A professional-grade DJ mixing application with a comprehensive plugin system for extensibility.

## Features

- **Professional DJ Mixing**: Full-featured mixing engine for DJs
- **Plugin System**: Extensible architecture for creating custom audio effects, tools, and visualizers
- **Multiple Plugin Types**: AudioEffect, LibraryTool, Visualizer, and more
- **Configuration Management**: Parameter validation, profiles, and preferences
- **State Management**: Persistent state with snapshots and restoration
- **Event System**: Pub/sub event-driven architecture
- **Dependency Injection**: Clean architecture with IoC container
- **Communication Hub**: Inter-plugin messaging and RPC
- **Resource Management**: CPU/Memory quotas and monitoring
- **Sandbox Security**: Permission-based security for plugins
- **Performance Monitoring**: Profiling and performance analysis

## Quick Start

### Installation

```bash
git clone https://github.com/yourusername/acro-dj-mixer.git
cd acro-dj-mixer
pip install -e .
```

### Running the Application

```bash
python -m acro_dj_mixer
```

## Plugin Development

Create a new plugin by extending the base plugin classes:

```python
from plugins.plugin_api import AudioEffectPlugin, PluginMetadata, Parameter

class MyEffect(AudioEffectPlugin):
    def __init__(self):
        super().__init__(PluginMetadata(
            name="My Effect",
            version="1.0.0",
            author="Your Name"
        ))

    def process_audio(self, audio):
        # Implement your effect here
        return audio
```

See [Plugin Development Guide](#plugin-development) for more details.

## System Requirements

- Python 3.8+
- tkinter (usually included with Python)
- psutil (for resource monitoring)

## Architecture

### Core Components

- **Plugin Framework**: Base classes and plugin lifecycle management
- **Configuration System**: Parameter validation and profile storage
- **Event System**: Pub/sub messaging
- **State Management**: Persistence and snapshots
- **Communication Hub**: Inter-plugin messaging
- **Dependency Injection**: IoC container for clean architecture
- **Resource Management**: CPU/Memory quota management
- **Sandbox**: Security and permission system

### File Structure

```
acro-dj-mixer/
├── plugins/                  # Plugin system modules
│   ├── plugin_api.py        # Core plugin framework
│   ├── plugin_config.py     # Configuration management
│   ├── plugin_versioning.py # Semantic versioning
│   ├── plugin_communication.py # Message passing
│   ├── plugin_state.py      # State persistence
│   ├── plugin_events.py     # Event system
│   ├── plugin_resources.py  # Resource management
│   ├── plugin_dependency_injection.py # IoC container
│   └── ...                  # Other plugin modules
├── tests/                   # Test suite
├── setup.py                 # Package configuration
└── README.md               # This file
```

## Testing

Run the test suite:

```bash
pytest tests/ -v
```

Run with coverage:

```bash
pytest tests/ --cov=plugins --cov=acro_dj_mixer
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## Support

- **Issues**: Report bugs on [GitHub Issues](https://github.com/yourusername/acro-dj-mixer/issues)
- **Discussions**: Ask questions on [GitHub Discussions](https://github.com/yourusername/acro-dj-mixer/discussions)
- **Documentation**: See the docs/ directory for comprehensive guides

## Acknowledgments

Built with Python and tkinter, with inspiration from professional DJ software like Serato, Pioneer, and Virtual DJ.
