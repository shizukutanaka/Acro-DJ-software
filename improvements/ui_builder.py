# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
UI Builder Module

Separates UI creation logic from business logic.
Provides reusable UI component builders.
"""

import tkinter as tk
from tkinter import ttk
import logging
from typing import Dict, Callable, Optional

logger = logging.getLogger(__name__)

# Theme constants
DEFAULT_THEME_COLORS = {
    "bg": "#2b2b2b",
    "fg": "#ffffff",
    "accent": "#007acc",
    "deck_bg": "#1e1e1e",
    "waveform_fg": "#00ff00",
    "waveform_bg": "#0a0a0a"
}


class UIComponentBuilder:
    """Base class for UI component builders."""

    def __init__(self, theme_colors: Optional[Dict[str, str]] = None):
        """Initialize builder with theme colors."""
        self.colors = theme_colors or DEFAULT_THEME_COLORS


class DeckUIBuilder(UIComponentBuilder):
    """Builder for deck UI components."""

    def build_deck_frame(self, parent: tk.Widget) -> tk.Frame:
        """Build main deck frame."""
        frame = tk.Frame(
            parent,
            bg=self.colors["deck_bg"],
            relief=tk.SUNKEN,
            bd=2
        )
        return frame

    def build_waveform_canvas(
        self, parent: tk.Widget, width: int = 400, height: int = 100
    ) -> tk.Canvas:
        """Build waveform display canvas."""
        canvas = tk.Canvas(
            parent,
            width=width,
            height=height,
            bg=self.colors["waveform_bg"],
            highlightthickness=0,
            relief=tk.SUNKEN,
            bd=1
        )
        return canvas

    def build_transport_controls(
        self, parent: tk.Widget, callbacks: Dict[str, Callable]
    ) -> tk.Frame:
        """Build transport control buttons (Play, Pause, Stop, etc)."""
        frame = tk.Frame(parent, bg=self.colors["deck_bg"])

        button_configs = [
            ("Play", "play", "▶"),
            ("Pause", "pause", "⏸"),
            ("Stop", "stop", "⏹"),
            ("Cue", "cue", "◆")
        ]

        for label, action, symbol in button_configs:
            callback = callbacks.get(action, lambda: None)
            btn = tk.Button(
                frame,
                text=symbol,
                command=callback,
                width=4,
                bg=self.colors["accent"],
                fg=self.colors["fg"],
                activebackground="#1084d7"
            )
            btn.pack(side=tk.LEFT, padx=2, pady=2)

        return frame

    def build_level_slider(
        self, parent: tk.Widget, label: str, callback: Callable
    ) -> tk.Scale:
        """Build audio level slider."""
        frame = tk.Frame(parent, bg=self.colors["deck_bg"])

        lbl = tk.Label(
            frame,
            text=label,
            bg=self.colors["deck_bg"],
            fg=self.colors["fg"],
            font=("Arial", 9)
        )
        lbl.pack()

        slider = tk.Scale(
            frame,
            from_=0,
            to=100,
            orient=tk.VERTICAL,
            command=callback,
            bg=self.colors["deck_bg"],
            fg=self.colors["fg"],
            troughcolor=self.colors["waveform_bg"],
            activebackground=self.colors["accent"],
            highlightthickness=0
        )
        slider.pack()

        return slider


class ControlPanelBuilder(UIComponentBuilder):
    """Builder for main control panel components."""

    def build_crossfader(
        self, parent: tk.Widget, callback: Callable
    ) -> tk.Scale:
        """Build crossfader slider."""
        frame = tk.Frame(parent, bg=self.colors["bg"])

        label = tk.Label(
            frame,
            text="Crossfader",
            bg=self.colors["bg"],
            fg=self.colors["fg"],
            font=("Arial", 10, "bold")
        )
        label.pack()

        slider = tk.Scale(
            frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            command=callback,
            length=200,
            bg=self.colors["bg"],
            fg=self.colors["fg"],
            troughcolor=self.colors["waveform_bg"],
            activebackground=self.colors["accent"],
            highlightthickness=0
        )
        slider.set(50)
        slider.pack(fill=tk.X, padx=10, pady=5)

        return slider

    def build_master_volume(
        self, parent: tk.Widget, callback: Callable
    ) -> tk.Scale:
        """Build master volume control."""
        frame = tk.Frame(parent, bg=self.colors["bg"])

        label = tk.Label(
            frame,
            text="Master Volume",
            bg=self.colors["bg"],
            fg=self.colors["fg"],
            font=("Arial", 10, "bold")
        )
        label.pack()

        slider = tk.Scale(
            frame,
            from_=0,
            to=100,
            orient=tk.VERTICAL,
            command=callback,
            height=150,
            bg=self.colors["bg"],
            fg=self.colors["fg"],
            troughcolor=self.colors["waveform_bg"],
            activebackground=self.colors["accent"],
            highlightthickness=0
        )
        slider.set(100)
        slider.pack(padx=10, pady=5)

        return slider

    def build_menu_bar(
        self, parent: tk.Widget, menu_items: Dict[str, Dict[str, Callable]]
    ) -> tk.Menu:
        """Build menu bar."""
        menubar = tk.Menu(parent, bg=self.colors["bg"], fg=self.colors["fg"])

        for menu_name, items in menu_items.items():
            menu = tk.Menu(
                menubar,
                bg=self.colors["bg"],
                fg=self.colors["fg"],
                activebackground=self.colors["accent"]
            )

            for item_name, callback in items.items():
                menu.add_command(label=item_name, command=callback)

            menubar.add_cascade(label=menu_name, menu=menu)

        return menubar

    def build_status_bar(self, parent: tk.Widget) -> tk.Label:
        """Build status bar."""
        status = tk.Label(
            parent,
            text="Ready",
            bg=self.colors["accent"],
            fg=self.colors["fg"],
            relief=tk.SUNKEN,
            bd=1,
            anchor=tk.W,
            padx=10
        )
        return status


class MainUIBuilder:
    """Main application UI builder."""

    def __init__(self, theme_colors: Optional[Dict[str, str]] = None):
        """Initialize main UI builder."""
        self.colors = theme_colors or DEFAULT_THEME_COLORS
        self.deck_builder = DeckUIBuilder(self.colors)
        self.control_builder = ControlPanelBuilder(self.colors)

    def build_application(
        self, root: tk.Tk, callbacks: Dict[str, Callable]
    ) -> Dict[str, tk.Widget]:
        """Build complete application UI."""
        widgets = {}

        # Configure root window
        root.configure(bg=self.colors["bg"])
        root.title("DJ Mixer")

        # Build menu
        menubar = self.control_builder.build_menu_bar(
            root,
            {
                "File": {
                    "Open Track": callbacks.get("open_track", lambda: None),
                    "Exit": callbacks.get("exit_app", lambda: None)
                },
                "View": {
                    "Theme": callbacks.get("change_theme", lambda: None)
                }
            }
        )
        root.config(menu=menubar)
        widgets["menubar"] = menubar

        # Main content frame
        main_frame = tk.Frame(root, bg=self.colors["bg"])
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Decks frame
        decks_frame = tk.Frame(main_frame, bg=self.colors["bg"])
        decks_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left deck
        left_frame = self.deck_builder.build_deck_frame(decks_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        widgets["left_deck"] = left_frame

        # Right deck
        right_frame = self.deck_builder.build_deck_frame(decks_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        widgets["right_deck"] = right_frame

        # Control panel
        control_frame = tk.Frame(main_frame, bg=self.colors["bg"])
        control_frame.pack(fill=tk.X, padx=10, pady=10)

        # Crossfader
        xf = self.control_builder.build_crossfader(
            control_frame,
            callbacks.get("crossfader_changed", lambda v: None)
        )
        widgets["crossfader"] = xf

        # Master volume
        master_vol = self.control_builder.build_master_volume(
            control_frame,
            callbacks.get("master_volume_changed", lambda v: None)
        )
        widgets["master_volume"] = master_vol

        # Status bar
        status = self.control_builder.build_status_bar(main_frame)
        status.pack(fill=tk.X)
        widgets["status_bar"] = status

        return widgets

    def update_theme(self, root: tk.Tk, new_colors: Dict[str, str]) -> None:
        """Update theme colors."""
        self.colors = new_colors
        self.deck_builder.colors = new_colors
        self.control_builder.colors = new_colors

        # Re-render with new colors (simplified - in practice need to rebuild)
        root.configure(bg=new_colors["bg"])
        logger.info("Theme updated")
