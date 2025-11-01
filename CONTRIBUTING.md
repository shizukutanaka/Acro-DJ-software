# Contributing to DJ Mixer

Thank you for your interest in contributing to DJ Mixer! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please be respectful and constructive in all interactions. We welcome contributors from all backgrounds and experience levels.

## Getting Started

### Prerequisites
- Python 3.8 or higher
- Git
- A text editor or IDE
- Audio device for testing

### Setting Up Development Environment

1. **Fork the repository** on GitHub

2. **Clone your fork**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/tkinter-dj-app.git
   cd tkinter-dj-app
   ```

3. **Create a virtual environment**:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Guidelines

### Code Style
- Follow PEP 8 guidelines
- Use meaningful variable and function names
- Add type hints where possible
- Keep functions focused and reasonably sized

### Documentation
- Add docstrings to all classes and functions
- Update README.md if adding features
- Include comments for complex logic

### Testing
- Test your changes thoroughly before submitting
- Test on different operating systems if possible
- Include test audio files of various formats

### Commit Messages
Use clear, descriptive commit messages:
```
Fix: Correct audio crackling issue
Add: BPM detection improvement
Update: Documentation for new features
Refactor: Audio callback efficiency
```

## Types of Contributions

### Bug Reports
1. Check if the bug has already been reported
2. Provide detailed steps to reproduce
3. Include system information (OS, Python version)
4. Describe expected vs actual behavior

### Feature Requests
1. Check if the feature has been requested
2. Describe the use case and benefits
3. Provide examples if applicable
4. Consider implementation complexity

### Code Contributions
1. Keep changes focused and minimal
2. Include related test cases
3. Update documentation
4. Submit a pull request with clear description

## Pull Request Process

1. **Ensure code quality**:
   - Run the application and verify functionality
   - Check for any warnings or errors
   - Follow code style guidelines

2. **Create a descriptive PR**:
   ```markdown
   ## Description
   Brief description of changes

   ## Type of Change
   - [ ] Bug fix
   - [ ] New feature
   - [ ] Documentation update
   - [ ] Performance improvement

   ## Testing
   Describe tests performed

   ## Screenshots (if applicable)
   ```

3. **Wait for review**:
   - Address feedback and suggestions
   - Make requested changes
   - Keep the conversation professional

4. **Merge**:
   - Maintainers will merge when approved
   - Your contribution will be attributed

## Coding Standards

### Example Code Structure
```python
def function_name(param1: str, param2: int) -> bool:
    """
    Brief description of function.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value
    """
    # Implementation
    return True
```

### Class Example
```python
class AudioProcessor:
    """Handles audio processing operations."""

    def __init__(self, sample_rate: int) -> None:
        """Initialize the processor."""
        self.sample_rate = sample_rate

    def process(self, data: np.ndarray) -> np.ndarray:
        """Process audio data."""
        return data
```

## Areas for Contribution

### High Priority
- [ ] Time-stretch based pitch shifting
- [ ] Advanced parametric EQ
- [ ] MIDI controller support
- [ ] Performance optimization

### Medium Priority
- [ ] Playlist management
- [ ] Effects (reverb, delay, etc.)
- [ ] Recording functionality
- [ ] Hot cues implementation

### Documentation
- [ ] Improved tutorials
- [ ] Video guides
- [ ] API documentation
- [ ] Plugin development guide

## Reporting Security Issues

Do not create public issues for security vulnerabilities. Instead:
1. Email security concerns to maintainers
2. Include detailed description
3. Allow time for patching before disclosure

## Questions?

- Check the README and documentation
- Review existing issues and discussions
- Create a new issue for clarification

## Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project acknowledgments

Thank you for helping make DJ Mixer better!
