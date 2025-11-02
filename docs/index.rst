.. Acro DJ Mixer documentation master file

====================================
Acro DJ Mixer - Professional DJ Software
====================================

Welcome to the Acro DJ Mixer documentation!

Acro DJ Mixer is a free, open-source, professional DJ mixing application
featuring modern plugin architecture, comprehensive effects, MIDI control,
and preset management.

.. image:: https://img.shields.io/badge/License-MIT-yellow.svg
   :target: https://opensource.org/licenses/MIT

.. image:: https://img.shields.io/badge/Python-3.8+-blue.svg
   :target: https://www.python.org/

.. image:: https://img.shields.io/badge/Status-Production-brightgreen.svg


Quick Start
===========

Installation
~~~~~~~~~~~~

.. code-block:: bash

    pip install acro-dj-mixer

Running the Application
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # GUI mode
    acro-gui

    # CLI mode
    acro-cli


Table of Contents
=================

.. toctree::
   :maxdepth: 2
   :numbered:
   :caption: Getting Started

   getting_started/installation
   getting_started/quickstart
   getting_started/configuration

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   user_guide/interface
   user_guide/mixing
   user_guide/effects
   user_guide/midi_control
   user_guide/presets

.. toctree::
   :maxdepth: 2
   :caption: Developer Guide

   developer/architecture
   developer/plugin_development
   developer/audio_processing
   developer/api_reference

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/effects
   api/controllers
   api/config
   api/logging

.. toctree::
   :maxdepth: 2
   :caption: Advanced Topics

   advanced/performance
   advanced/custom_effects
   advanced/integration

.. toctree::
   :maxdepth: 1
   :caption: Community

   community/contributing
   community/changelog
   community/faq


Features
========

Core Features
~~~~~~~~~~~~~

* **Professional Audio Engine**
  - Multi-channel audio processing
  - Real-time effects
  - High-quality sample rate support (up to 192kHz)

* **Effects Suite**
  - EQ (Bass, Mid, Treble)
  - Compression
  - Reverb
  - Delay
  - Time stretching
  - Pitch shifting

* **MIDI Support**
  - Full MIDI controller support
  - Assignable controls
  - Multiple device support

* **Preset Management**
  - Save/load effect chains
  - Preset library
  - Metadata tagging

* **Advanced Features**
  - Plugin architecture
  - Frequency analysis
  - Performance monitoring
  - Docker support

Architecture
============

Acro DJ Mixer follows modern Python best practices:

* **Type Safety**: Full type hints with MyPy strict mode
* **Code Quality**: Automated linting with Ruff
* **Testing**: Comprehensive test suite (15-platform CI/CD)
* **Configuration**: Pydantic-based type-safe configuration
* **Logging**: Professional Loguru-based logging
* **Extensibility**: Entry point-based plugin system


Installation & Setup
====================

See :doc:`/getting_started/installation` for detailed setup instructions.


Contributing
============

We welcome contributions! See :doc:`/community/contributing` for guidelines.

Development
~~~~~~~~~~~

.. code-block:: bash

    # Clone repository
    git clone https://github.com/yourusername/acro-dj-mixer.git

    # Create virtual environment
    python -m venv venv
    source venv/bin/activate  # Linux/Mac
    # or
    venv\Scripts\activate  # Windows

    # Install in development mode
    pip install -e ".[dev]"

    # Run tests
    pytest

    # Build documentation
    cd docs && make html


Support
=======

* **Documentation**: https://acro-dj-mixer.readthedocs.io
* **GitHub Issues**: Report bugs and request features
* **GitHub Discussions**: Ask questions and discuss
* **Email**: support@acro-dj-mixer.dev


License
=======

Acro DJ Mixer is licensed under the MIT License.
See LICENSE file for details.


Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
