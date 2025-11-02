# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""Acro DJ Mixer Plugin System - v3.x"""

__version__ = "1.0.0"
__author__ = "Acro Development Team"

from .library_management import LibraryAnalyzer, TrackAnalysis, LibraryManager

__all__ = ['LibraryAnalyzer', 'TrackAnalysis', 'LibraryManager']
