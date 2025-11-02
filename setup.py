#!/usr/bin/env python
# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""Legacy setup.py for backward compatibility with older build tools.

This file exists for compatibility with setuptools. The main build
configuration is in pyproject.toml which is the modern approach.

For new projects, use pyproject.toml. This file is only for legacy
systems that do not support PEP 517/518.
"""

from setuptools import setup

setup()
