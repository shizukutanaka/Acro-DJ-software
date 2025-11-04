# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
MIDI Controller Integration

Provides MIDI input support and parameter mapping for hardware controllers.
Features:
- MIDI device detection and initialization
- Parameter binding (knobs, faders, buttons)
- Preset/controller mapping storage
- Real-time parameter updates
"""

import logging
from typing import Dict, Optional, Callable, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum
from threading import Lock, Thread
import warnings

try:
    import mido
    MIDO_AVAILABLE = True
except ImportError:
    MIDO_AVAILABLE = False
    warnings.warn("mido not installed. MIDI support disabled. "
                  "Install with: pip install python-rtmidi or pip install mido")

logger = logging.getLogger(__name__)


class MIDIEventType(Enum):
    """MIDI event types."""
    NOTE_ON = "note_on"
    NOTE_OFF = "note_off"
    CONTROL_CHANGE = "control_change"
    PITCH_BEND = "pitch_bend"


@dataclass
class MIDIMapping:
    """Maps MIDI control to application parameter."""

    midi_type: MIDIEventType  # Type of MIDI event
    channel: int              # MIDI channel (0-15)
    control_number: int       # CC number or note number
    min_value: float          # Minimum parameter value
    max_value: float          # Maximum parameter value
    parameter_name: str       # Target parameter name
    callback: Optional[Callable] = None  # Callback function

    def normalize_value(self, midi_value: int) -> float:
        """
        Convert MIDI value (0-127) to parameter range.

        Args:
            midi_value: Raw MIDI value (0-127)

        Returns:
            Normalized value in [min_value, max_value]
        """
        # Normalize MIDI value to 0.0-1.0
        normalized = midi_value / 127.0

        # Map to parameter range
        return self.min_value + normalized * (self.max_value - self.min_value)


@dataclass
class ControllerInfo:
    """Information about detected MIDI controller."""

    name: str
    input_port: Optional[str] = None
    output_port: Optional[str] = None
    is_connected: bool = False


class MIDIController:
    """
    Manages MIDI input from hardware controller.
    """

    def __init__(self, auto_detect: bool = True):
        """
        Initialize MIDI controller.

        Args:
            auto_detect: Automatically detect controllers on startup
        """
        if not MIDO_AVAILABLE:
            logger.warning("mido not available - MIDI support disabled")
            self.available = False
            return

        self.available = True
        self.input_port = None
        self.connected_controller: Optional[ControllerInfo] = None

        self.mappings: Dict[Tuple, MIDIMapping] = {}
        self.lock = Lock()

        self.listening = False
        self.listener_thread: Optional[Thread] = None

        if auto_detect:
            self.auto_detect_controller()

        logger.info("MIDIController initialized")

    def get_available_inputs(self) -> List[str]:
        """Get list of available MIDI input ports."""
        if not MIDO_AVAILABLE or not self.available:
            return []

        try:
            return mido.get_input_names()
        except Exception as e:
            logger.error(f"Error getting MIDI inputs: {e}")
            return []

    def auto_detect_controller(self) -> bool:
        """
        Automatically detect and connect to first MIDI controller.

        Returns:
            True if controller found and connected
        """
        if not MIDO_AVAILABLE or not self.available:
            return False

        inputs = self.get_available_inputs()

        if not inputs:
            logger.warning("No MIDI input devices found")
            return False

        logger.info(f"Found MIDI inputs: {inputs}")

        # Try to connect to first input
        for input_name in inputs:
            if self.connect_to_input(input_name):
                return True

        return False

    def connect_to_input(self, port_name: str) -> bool:
        """
        Connect to specific MIDI input.

        Args:
            port_name: Name of MIDI input port

        Returns:
            True if connection successful
        """
        if not MIDO_AVAILABLE or not self.available:
            return False

        try:
            self.input_port = mido.open_input(port_name)
            self.connected_controller = ControllerInfo(
                name=port_name,
                input_port=port_name,
                is_connected=True
            )

            logger.info(f"Connected to MIDI input: {port_name}")

            # Start listening
            self.start_listening()

            return True

        except Exception as e:
            logger.error(f"Failed to connect to {port_name}: {e}")
            return False

    def add_mapping(self, midi_type: MIDIEventType, channel: int,
                   control: int, param_name: str,
                   min_val: float = 0.0, max_val: float = 1.0,
                   callback: Optional[Callable] = None) -> None:
        """
        Add MIDI-to-parameter mapping.

        Args:
            midi_type: Type of MIDI event
            channel: MIDI channel (0-15)
            control: CC number or note number
            param_name: Target parameter name
            min_val: Minimum parameter value
            max_val: Maximum parameter value
            callback: Optional callback function
        """
        key = (midi_type, channel, control)

        with self.lock:
            self.mappings[key] = MIDIMapping(
                midi_type=midi_type,
                channel=channel,
                control_number=control,
                min_value=min_val,
                max_value=max_val,
                parameter_name=param_name,
                callback=callback
            )

            logger.info(f"MIDI mapping added: {midi_type.value} CH{channel} "
                       f"CC{control} → {param_name}")

    def remove_mapping(self, midi_type: MIDIEventType, channel: int,
                      control: int) -> bool:
        """Remove MIDI mapping."""
        key = (midi_type, channel, control)

        with self.lock:
            if key in self.mappings:
                del self.mappings[key]
                return True
            return False

    def start_listening(self) -> None:
        """Start listening for MIDI events."""
        if not self.input_port or self.listening:
            return

        self.listening = True
        self.listener_thread = Thread(target=self._listen_loop, daemon=True)
        self.listener_thread.start()

        logger.info("MIDI listening started")

    def stop_listening(self) -> None:
        """Stop listening for MIDI events."""
        self.listening = False

        if self.listener_thread:
            self.listener_thread.join(timeout=2.0)
            logger.info("MIDI listening stopped")

    def _listen_loop(self) -> None:
        """Main MIDI listening loop."""
        if not self.input_port:
            return

        try:
            for message in self.input_port.iter_pending():
                self._process_message(message)

        except Exception as e:
            logger.error(f"Error in MIDI listen loop: {e}")
            self.listening = False

    def _process_message(self, message: Any) -> None:
        """
        Process MIDI message.

        Args:
            message: mido MidiMessage object
        """
        try:
            # Determine message type
            if message.type == 'control_change':
                midi_type = MIDIEventType.CONTROL_CHANGE
                control = message.control
                value = message.value
                channel = message.channel

            elif message.type == 'note_on':
                midi_type = MIDIEventType.NOTE_ON
                control = message.note
                value = message.velocity
                channel = message.channel

            elif message.type == 'note_off':
                midi_type = MIDIEventType.NOTE_OFF
                control = message.note
                value = 0
                channel = message.channel

            elif message.type == 'pitchwheel':
                midi_type = MIDIEventType.PITCH_BEND
                control = 0
                value = message.pitch
                channel = message.channel

            else:
                return

            # Find mapping
            key = (midi_type, channel, control)

            with self.lock:
                if key in self.mappings:
                    mapping = self.mappings[key]

                    # Normalize value
                    param_value = mapping.normalize_value(value)

                    # Call callback if provided
                    if mapping.callback:
                        mapping.callback(mapping.parameter_name, param_value)

                    logger.debug(f"MIDI mapped: {mapping.parameter_name} = {param_value:.2f}")

        except Exception as e:
            logger.error(f"Error processing MIDI message: {e}")

    def get_controller_info(self) -> Optional[ControllerInfo]:
        """Get connected controller information."""
        with self.lock:
            return self.connected_controller

    def get_mappings(self) -> Dict[Tuple, MIDIMapping]:
        """Get all MIDI mappings."""
        with self.lock:
            return self.mappings.copy()

    def save_mapping_preset(self, filename: str) -> bool:
        """
        Save MIDI mappings to file.

        Args:
            filename: Output file path

        Returns:
            True if saved successfully
        """
        try:
            import json

            with self.lock:
                data = {
                    'mappings': [
                        {
                            'midi_type': k[0].value,
                            'channel': k[1],
                            'control': k[2],
                            'param_name': v.parameter_name,
                            'min_val': v.min_value,
                            'max_val': v.max_value
                        }
                        for k, v in self.mappings.items()
                    ]
                }

            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)

            logger.info(f"MIDI preset saved: {filename}")
            return True

        except Exception as e:
            logger.error(f"Error saving MIDI preset: {e}")
            return False

    def load_mapping_preset(self, filename: str) -> bool:
        """
        Load MIDI mappings from file.

        Args:
            filename: Input file path

        Returns:
            True if loaded successfully
        """
        try:
            import json

            with open(filename, 'r') as f:
                data = json.load(f)

            with self.lock:
                self.mappings.clear()

                for mapping_data in data.get('mappings', []):
                    midi_type = MIDIEventType(mapping_data['midi_type'])

                    self.add_mapping(
                        midi_type=midi_type,
                        channel=mapping_data['channel'],
                        control=mapping_data['control'],
                        param_name=mapping_data['param_name'],
                        min_val=mapping_data.get('min_val', 0.0),
                        max_val=mapping_data.get('max_val', 1.0)
                    )

            logger.info(f"MIDI preset loaded: {filename}")
            return True

        except Exception as e:
            logger.error(f"Error loading MIDI preset: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from MIDI input."""
        self.stop_listening()

        if self.input_port:
            try:
                self.input_port.close()
                self.input_port = None
                self.connected_controller = None

                logger.info("Disconnected from MIDI input")

            except Exception as e:
                logger.error(f"Error disconnecting MIDI: {e}")

    def __del__(self):
        """Cleanup on deletion."""
        self.disconnect()


# Standard DJ controller mappings
COMMON_DJ_MAPPINGS = {
    'Pioneer DDJ-400': {
        'CROSSFADER': (MIDIEventType.CONTROL_CHANGE, 0, 15, 'crossfader', 0.0, 1.0),
        'MASTER_VOLUME': (MIDIEventType.CONTROL_CHANGE, 0, 14, 'master_volume', 0.0, 150.0),
        'LEFT_DECK_GAIN': (MIDIEventType.CONTROL_CHANGE, 0, 16, 'left_gain', 0.0, 100.0),
        'RIGHT_DECK_GAIN': (MIDIEventType.CONTROL_CHANGE, 0, 17, 'right_gain', 0.0, 100.0),
    },
    'Generic MIDI': {
        'CROSSFADER': (MIDIEventType.CONTROL_CHANGE, 0, 1, 'crossfader', 0.0, 1.0),
        'FADER_LEFT': (MIDIEventType.CONTROL_CHANGE, 0, 2, 'left_volume', 0.0, 1.0),
        'FADER_RIGHT': (MIDIEventType.CONTROL_CHANGE, 0, 3, 'right_volume', 0.0, 1.0),
        'KNOB_1': (MIDIEventType.CONTROL_CHANGE, 0, 20, 'param_1', -1.0, 1.0),
        'KNOB_2': (MIDIEventType.CONTROL_CHANGE, 0, 21, 'param_2', -1.0, 1.0),
    }
}


def get_standard_mapping(controller_type: str) -> Optional[Dict]:
    """Get standard mapping for known controller."""
    return COMMON_DJ_MAPPINGS.get(controller_type)
