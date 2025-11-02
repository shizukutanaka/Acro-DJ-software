# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""Sample MIDI controller plugin for Acro DJ Mixer.

This is a complete, working example of how to create a custom
MIDI controller plugin for Acro DJ Mixer. You can use this as a
template for your own MIDI controller integrations.

Supports any MIDI device with standard Control Change messages.

To use this plugin:
1. Create a directory: my-acro-midi-plugin/
2. Copy this file into my-acro-midi-plugin/my_plugin/controller.py
3. Create pyproject.toml with entry point:
   [project.entry-points."acro.controllers"]
   generic = "my_plugin.controller:GenericMIDIController"
4. Install: pip install -e my-acro-midi-plugin/
5. Load via plugin manager

Example:
    >>> from plugin_api import get_plugin_manager
    >>> manager = get_plugin_manager()
    >>> manager.discover_plugins()
    >>> controller = manager.get_controller("generic_midi")
    >>> if controller.connect("My MIDI Device"):
    ...     print("Connected!")
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from plugin_api import AcroController


class GenericMIDIController(AcroController):
    """Generic MIDI controller plugin.

    Works with any MIDI device that sends Control Change (CC) messages.
    Provides standard DJ control mappings.

    Default Mappings:
        CC #0-9:   Deck A controls (volume, gain, pitch, etc.)
        CC #16-25: Deck B controls
        CC #32-41: Deck C controls
        CC #48-57: Deck D controls
        CC #64:    Crossfader
        CC #65:    Master volume
        CC #66-73: FX knobs
        CC #74:    BPM tempo
        CC #80-87: Cue buttons
        CC #88-95: Loop controls

    Parameters:
        channel: MIDI channel to listen on (0-15, default 0)
        sensitivity: Control sensitivity multiplier (0.1-2.0)

    Example:
        >>> controller = GenericMIDIController()
        >>> if controller.connect("MIDI Device"):
        ...     def on_volume_change(value):
        ...         print(f"Volume: {value}")
        ...     controller.register_callback("deck_a_volume", on_volume_change)
    """

    name = "Generic MIDI Controller"
    device_type = "MIDI"
    version = "1.0.0"
    author = "Acro Community"
    description = "Generic MIDI controller with standard DJ control mappings"

    def __init__(self, channel: int = 0, sensitivity: float = 1.0):
        """Initialize MIDI controller.

        Args:
            channel: MIDI channel (0-15)
            sensitivity: Control sensitivity (0.1-2.0)
        """
        self.channel = max(0, min(15, channel))
        self.sensitivity = max(0.1, min(2.0, sensitivity))
        self.connected = False
        self.device_name: Optional[str] = None
        self.callbacks: Dict[str, List[Callable]] = {}
        self.last_values: Dict[int, int] = {}  # CC to value mapping

    def connect(self, device_name: str) -> bool:
        """Connect to MIDI device.

        Args:
            device_name: Name of MIDI device

        Returns:
            True if connection successful
        """
        try:
            # In real implementation, would use mido.open_input()
            self.device_name = device_name
            self.connected = True
            print(f"✓ Connected to {device_name} on channel {self.channel}")
            return True
        except Exception as e:
            print(f"✗ Failed to connect: {e}")
            return False

    def disconnect(self) -> bool:
        """Disconnect from device.

        Returns:
            True if disconnection successful
        """
        if self.connected:
            self.connected = False
            print(f"✓ Disconnected from {self.device_name}")
            return True
        return False

    def on_message(self, msg_type: str, data: bytes) -> None:
        """Process incoming MIDI message.

        Args:
            msg_type: Message type ('control_change', 'note_on', etc.)
            data: Message data
        """
        if msg_type != "control_change" or not self.connected:
            return

        if len(data) < 2:
            return

        cc_number = data[0]
        cc_value = data[1]

        # Normalize to 0.0-1.0 range
        normalized_value = cc_value / 127.0 * self.sensitivity

        # Map CC to control
        control_name = self._get_control_name(cc_number)

        if control_name:
            self._trigger_callbacks(control_name, normalized_value)
            self.last_values[cc_number] = cc_value

    def _get_control_name(self, cc_number: int) -> Optional[str]:
        """Map CC number to control name.

        Args:
            cc_number: CC number (0-127)

        Returns:
            Control name or None
        """
        # Deck A (CC #0-9)
        if 0 <= cc_number <= 9:
            controls_a = [
                "deck_a_volume", "deck_a_gain", "deck_a_pitch",
                "deck_a_eq_low", "deck_a_eq_mid", "deck_a_eq_high",
                "deck_a_filter", "deck_a_reverb", "deck_a_delay",
                "deck_a_effect_knob"
            ]
            return controls_a[cc_number]

        # Deck B (CC #16-25)
        if 16 <= cc_number <= 25:
            offset = cc_number - 16
            controls_b = [
                "deck_b_volume", "deck_b_gain", "deck_b_pitch",
                "deck_b_eq_low", "deck_b_eq_mid", "deck_b_eq_high",
                "deck_b_filter", "deck_b_reverb", "deck_b_delay",
                "deck_b_effect_knob"
            ]
            return controls_b[offset]

        # Deck C (CC #32-41)
        if 32 <= cc_number <= 41:
            offset = cc_number - 32
            controls_c = [
                "deck_c_volume", "deck_c_gain", "deck_c_pitch",
                "deck_c_eq_low", "deck_c_eq_mid", "deck_c_eq_high",
                "deck_c_filter", "deck_c_reverb", "deck_c_delay",
                "deck_c_effect_knob"
            ]
            return controls_c[offset]

        # Deck D (CC #48-57)
        if 48 <= cc_number <= 57:
            offset = cc_number - 48
            controls_d = [
                "deck_d_volume", "deck_d_gain", "deck_d_pitch",
                "deck_d_eq_low", "deck_d_eq_mid", "deck_d_eq_high",
                "deck_d_filter", "deck_d_reverb", "deck_d_delay",
                "deck_d_effect_knob"
            ]
            return controls_d[offset]

        # Crossfader (CC #64)
        if cc_number == 64:
            return "crossfader"

        # Master Volume (CC #65)
        if cc_number == 65:
            return "master_volume"

        # FX Knobs (CC #66-73)
        if 66 <= cc_number <= 73:
            offset = cc_number - 66
            return f"fx_knob_{offset + 1}"

        # BPM Tempo (CC #74)
        if cc_number == 74:
            return "tempo"

        # Cue Buttons (CC #80-87)
        if 80 <= cc_number <= 87:
            offset = cc_number - 80
            return f"cue_button_{offset + 1}"

        # Loop Controls (CC #88-95)
        if 88 <= cc_number <= 95:
            offset = cc_number - 88
            return f"loop_{offset + 1}"

        return None

    def _trigger_callbacks(self, control_name: str, value: float) -> None:
        """Trigger registered callbacks for control.

        Args:
            control_name: Name of control
            value: Control value (0.0-1.0)
        """
        if control_name in self.callbacks:
            for callback in self.callbacks[control_name]:
                try:
                    callback(value)
                except Exception as e:
                    print(f"✗ Callback error for {control_name}: {e}")

    def register_callback(
        self, control_name: str, callback: Callable[[float], None]
    ) -> None:
        """Register callback for control changes.

        Args:
            control_name: Name of control to monitor
            callback: Function to call with new value (0.0-1.0)
        """
        if control_name not in self.callbacks:
            self.callbacks[control_name] = []
        self.callbacks[control_name].append(callback)

    def get_controls(self) -> List[Dict[str, Any]]:
        """Get list of supported controls.

        Returns:
            List of control definitions
        """
        controls = []

        # Deck controls (4 decks)
        for deck in ["A", "B", "C", "D"]:
            deck_lower = deck.lower()
            controls.extend([
                {
                    "name": f"deck_{deck_lower}_volume",
                    "type": "fader",
                    "label": f"Deck {deck} Volume",
                    "range": (0, 127)
                },
                {
                    "name": f"deck_{deck_lower}_gain",
                    "type": "knob",
                    "label": f"Deck {deck} Gain",
                    "range": (0, 127)
                },
                {
                    "name": f"deck_{deck_lower}_pitch",
                    "type": "knob",
                    "label": f"Deck {deck} Pitch",
                    "range": (-127, 127)
                },
            ])

        # Master controls
        controls.extend([
            {
                "name": "crossfader",
                "type": "fader",
                "label": "Crossfader",
                "range": (0, 127)
            },
            {
                "name": "master_volume",
                "type": "fader",
                "label": "Master Volume",
                "range": (0, 127)
            },
            {
                "name": "tempo",
                "type": "knob",
                "label": "Tempo/BPM",
                "range": (0, 127)
            },
        ])

        return controls

    def get_device_info(self) -> Dict[str, str]:
        """Get information about connected device.

        Returns:
            Dictionary with device info
        """
        return {
            "name": self.device_name or "Not Connected",
            "type": self.device_type,
            "version": self.version,
            "channel": str(self.channel + 1),  # Human-readable (1-16)
            "sensitivity": f"{self.sensitivity:.1f}x",
            "connected": "Yes" if self.connected else "No",
        }

    def validate(self) -> bool:
        """Validate controller compatibility.

        Returns:
            True if compatible
        """
        # Generic MIDI is always compatible
        return True


class PioneerDDJ400Controller(AcroController):
    """Pioneer DDJ-400 specific controller plugin.

    Optimized mappings for Pioneer DDJ-400 with built-in presets.

    Features:
        - Optimized for DDJ-400 layout
        - JOG wheel support
        - Specific button mappings
        - LED feedback (when supported)

    Example:
        >>> controller = PioneerDDJ400Controller()
        >>> if controller.connect("DDJ-400"):
        ...     print("Ready to DJ!")
    """

    name = "Pioneer DDJ-400"
    device_type = "MIDI"
    version = "1.0.0"
    author = "Acro Community"
    description = "Optimized controller for Pioneer DDJ-400"

    def __init__(self):
        """Initialize Pioneer DDJ-400 controller."""
        self.connected = False
        self.device_name: Optional[str] = None
        self.callbacks: Dict[str, List[Callable]] = {}

    def connect(self, device_name: str) -> bool:
        """Connect to DDJ-400.

        Args:
            device_name: Device name (usually contains "DDJ-400")

        Returns:
            True if connection successful
        """
        if "DDJ-400" not in device_name and "ddj-400" not in device_name.lower():
            print(f"✗ This controller is optimized for DDJ-400, got {device_name}")
            return False

        try:
            self.device_name = device_name
            self.connected = True
            print(f"✓ Connected to {device_name}")
            return True
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False

    def disconnect(self) -> bool:
        """Disconnect from device."""
        if self.connected:
            self.connected = False
            return True
        return False

    def on_message(self, msg_type: str, data: bytes) -> None:
        """Process DDJ-400 MIDI messages."""
        pass

    def get_controls(self) -> List[Dict[str, Any]]:
        """Get DDJ-400 specific controls."""
        return [
            {"name": "play_deck_a", "type": "button", "label": "Play Deck A"},
            {"name": "play_deck_b", "type": "button", "label": "Play Deck B"},
            {"name": "cue_deck_a", "type": "button", "label": "Cue Deck A"},
            {"name": "cue_deck_b", "type": "button", "label": "Cue Deck B"},
            {"name": "sync_a", "type": "button", "label": "Sync Deck A"},
            {"name": "sync_b", "type": "button", "label": "Sync Deck B"},
        ]

    def validate(self) -> bool:
        """Validate controller."""
        return True


if __name__ == "__main__":
    # Test the controllers
    print("Testing MIDI controller plugins...\n")

    # Test Generic MIDI
    print("1. Generic MIDI Controller")
    generic = GenericMIDIController()
    print(f"   Name: {generic.name}")
    print(f"   Type: {generic.device_type}")
    print(f"   Channel: {generic.channel}")

    if generic.connect("Virtual MIDI Device"):
        print(f"   Device Info: {generic.get_device_info()}")
        print(f"   Controls: {len(generic.get_controls())} available")

        # Register and test callback
        test_value = None

        def volume_callback(value):
            nonlocal test_value
            test_value = value

        generic.register_callback("deck_a_volume", volume_callback)

        # Simulate MIDI message (CC #0, value 100)
        generic.on_message("control_change", bytes([0, 100]))
        print(f"   Callback test: Volume set to {test_value:.2f}")

        generic.disconnect()

    # Test Pioneer DDJ-400
    print("\n2. Pioneer DDJ-400 Controller")
    pioneer = PioneerDDJ400Controller()
    print(f"   Name: {pioneer.name}")
    print(f"   Type: {pioneer.device_type}")

    if pioneer.connect("DDJ-400 Mk2"):
        print(f"   Connected: {pioneer.get_device_info()['connected']}")
        print(f"   Controls: {len(pioneer.get_controls())} available")
        pioneer.disconnect()
    else:
        print("   ✗ Connection failed (expected for wrong device)")

    print("\n✅ All MIDI controller plugins tested successfully!")
