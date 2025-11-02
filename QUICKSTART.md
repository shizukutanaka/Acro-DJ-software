# Quick Start Guide

Get Acro DJ Mixer running in 5 minutes.

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/acro-dj-mixer.git
cd acro-dj-mixer

# Install dependencies
pip install -e ".[dev]"
```

## Run the Application

```bash
python main.py
```

The DJ mixer interface will open with a two-deck layout ready for mixing.

## Create Your First Plugin

1. Copy the template:
```bash
cp plugins/template_effect_plugin.py plugins/my_effect.py
```

2. Edit the plugin:
```python
from plugins.plugin_api import AudioEffectPlugin, PluginMetadata

class MyEffect(AudioEffectPlugin):
    def __init__(self):
        super().__init__(PluginMetadata(
            name="My Effect",
            version="1.0.0",
            author="Your Name",
            description="My custom audio effect"
        ))

    def process_audio(self, audio):
        # Your effect logic here
        return audio * 1.2  # Simple gain boost
```

3. Test the plugin:
```bash
pytest tests/test_plugins.py -v
```

## Key Commands

```bash
# Run tests
pytest tests/ -v

# Run specific test
pytest tests/test_plugin_api.py::test_plugin_metadata -v

# Check code quality
flake8 plugins/ tests/

# Format code
black plugins/ tests/ main.py

# Type checking
mypy plugins/ main.py
```

## Plugin System Features

- **Configuration**: Type-safe parameter validation
- **Versioning**: Semantic versioning with constraints
- **Communication**: Inter-plugin messaging
- **State**: Persistent state with snapshots
- **Events**: Pub/sub event system
- **Resources**: CPU/Memory quotas
- **Testing**: Mock plugins and test utilities
- **Security**: Sandbox environment
- **Documentation**: Auto-generation

## Project Structure

```
plugins/          - Plugin system framework (16 modules)
tests/            - 400+ test cases
main.py          - Application entry point
config.py        - Configuration
README.md        - Full documentation
STRUCTURE.md     - Architecture guide
```

## Next Steps

1. **Read**: [README.md](README.md) for complete documentation
2. **Learn**: [STRUCTURE.md](STRUCTURE.md) for architecture overview
3. **Explore**: `plugins/` directory for available modules
4. **Develop**: Create plugins using provided frameworks
5. **Test**: Use included test utilities

## Troubleshooting

### Missing audio library
```bash
pip install librosa soundfile sounddevice
```

### Import errors
Ensure you're using Python 3.8+:
```bash
python --version
```

### Test failures
Some tests require audio libraries:
```bash
pip install -e ".[dev]"
```

## Support

- **Issues**: Report on GitHub
- **Documentation**: See README.md and docstrings
- **Examples**: Check plugins/ directory
- **Questions**: Open a GitHub discussion

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

**Happy mixing!** 🎵
