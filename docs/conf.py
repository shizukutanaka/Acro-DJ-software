# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""Sphinx configuration for Acro DJ Mixer documentation.

Build documentation with:
    cd docs && make html
"""

import os
import sys
from datetime import datetime

# Add source to path
sys.path.insert(0, os.path.abspath(".."))

# Project information
project = "Acro DJ Mixer"
copyright = f"{datetime.now().year}, Acro Community"
author = "Acro Community"
release = "2.5.0"
version = "2.5"

# Extensions
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx_rtd_theme",
    "sphinx.ext.mathjax",
    "myst_parser",
]

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_param = True
napoleon_use_rtype = True

# Autodoc settings
autodoc_typehints = "description"
autodoc_member_order = "bysource"
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": False,
    "show-inheritance": True,
}

# Source suffix
source_suffix = {
    ".rst": None,
    ".md": "myst-nb",
}

# Templates
templates_path = ["_templates"]

# Exclude patterns
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# Pygments style
pygments_style = "monokai"

# HTML theme
html_theme = "sphinx_rtd_theme"
html_theme_options = {
    "canonical_url": "https://acro-dj-mixer.readthedocs.io",
    "analytics_id": "",
    "display_version": True,
    "prev_next_buttons_location": "bottom",
    "style_external_links": False,
    "vcs_pageview_mode": "",
    "style_nav_header_background": "#343131",
    "collapse_navigation": True,
    "sticky_navigation": True,
    "navigation_depth": 4,
    "includehidden": True,
    "titles_only": False,
}

html_static_path = ["_static"]
html_logo = "../logo.png"
html_favicon = "../favicon.ico"

# LaTeX settings
latex_elements = {
    "papersize": "letterpaper",
    "pointsize": "11pt",
    "preamble": r"""
\usepackage{charter}
\usepackage[defaultsans]{lato}
\usepackage{inconsolata}
""",
    "fncychap": r"\usepackage[Bjornstrup]{fncychap}",
    "printindex": r"\footnotesize\raggedcolumns\printindex",
}

latex_documents = [
    (
        "index",
        "AcroDJMixer.tex",
        "Acro DJ Mixer Documentation",
        "Acro Community",
        "manual",
    ),
]

# EPUB settings
epub_title = "Acro DJ Mixer"
epub_author = "Acro Community"
epub_publisher = "Acro"
epub_copyright = f"{datetime.now().year}, Acro Community"

# Intersphinx mapping
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable", None),
    "scipy": ("https://docs.scipy.org/doc/scipy/reference", None),
}

# MyST Parser settings
myst_enable_extensions = [
    "dollarmath",
    "amsmath",
    "deflist",
    "html_image",
]

# API documentation auto-generation
def setup(app):
    """Sphinx setup hook."""
    app.add_config_value("recommonmark_enable_eval_rst", True, "html")
