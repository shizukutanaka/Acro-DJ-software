# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""My Acro DJ Mixer Plugin.

A template for creating custom Acro DJ Mixer plugins.

This package provides example implementations of:
- Audio effect plugins
- MIDI controller plugins
- Visualizer plugins
"""

from __future__ import annotations

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "you@example.com"
__license__ = "MIT"

from my_plugin.effect import MyCustomEffect, TemplateModulationEffect, TemplateFilterEffect

__all__ = [
    "MyCustomEffect",
    "TemplateModulationEffect",
    "TemplateFilterEffect",
]
