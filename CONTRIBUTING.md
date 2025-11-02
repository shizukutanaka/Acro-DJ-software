# Contributing to Acro DJ Mixer

Thank you for your interest in contributing to Acro DJ Mixer! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please be respectful and constructive in all interactions with other contributors and maintainers.

## Getting Started

1. Fork the repository
2. Clone your fork locally
3. Create a new branch for your changes
4. Install dependencies: `pip install -e ".[dev]"`
5. Make your changes
6. Run tests: `pytest tests/ -v`
7. Commit and push your changes
8. Submit a pull request

## Development Setup

### Prerequisites

- Python 3.8+
- git

### Installation

```bash
git clone https://github.com/yourusername/acro-dj-mixer.git
cd acro-dj-mixer
pip install -e ".[dev]"
```

## Plugin Development

To create a plugin:

1. Extend one of the base plugin classes from `plugins.plugin_api`
2. Implement the required methods
3. Add configuration schema if your plugin has parameters
4. Write tests for your plugin
5. Add documentation in your plugin's docstring

## Code Style

- Follow PEP 8
- Use type hints on public APIs
- Write comprehensive docstrings
- Keep functions small and focused

## Testing

All contributions should include tests:

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_plugins.py -v

# Run with coverage
pytest tests/ --cov=plugins --cov-report=html
```

Target coverage: > 90%

## Commit Messages

Use clear, descriptive commit messages:

```
feat: Add feature description
fix: Fix bug description
docs: Update documentation
test: Add tests
refactor: Refactor code
```

## Pull Request Process

1. Update README.md if needed
2. Add tests for new functionality
3. Ensure all tests pass
4. Update documentation/docstrings
5. Submit PR with clear description of changes

## Reporting Issues

When reporting issues, please include:

- Python version
- OS and version
- Steps to reproduce
- Expected behavior
- Actual behavior
- Error messages or logs

## Plugin Contribution Guidelines

Plugins can be contributed to extend Acro DJ Mixer:

1. Create your plugin following plugin development guidelines
2. Add comprehensive documentation
3. Include example usage
4. Write tests
5. Submit as a PR or separate plugin repository

## Questions?

- Open an issue on GitHub
- Start a discussion on GitHub Discussions
- Check existing documentation in the docs/ directory

Thank you for contributing!
