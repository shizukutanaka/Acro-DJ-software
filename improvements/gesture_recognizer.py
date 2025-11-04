# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
MIDI Jog Wheel Gesture Recognition

Recognizes DJ techniques from jog wheel MIDI input:
- Scratch detection and classification
- Nudge/tempo adjustment recognition
- Spin/fast forward/rewind detection
- Brake effect recognition
- Rule-based and ML-ready architecture
"""

import logging
import numpy as np
from typing import Dict, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum
from threading import Lock
from collections import deque
import time

logger = logging.getLogger(__name__)


class GestureType(Enum):
    """Recognized jog wheel gestures."""
    SCRATCH = "scratch"          # Back-and-forth scratching
    NUDGE = "nudge"              # Quick tempo adjustment
    SPIN = "spin"                # Fast rotation (forward/rewind)
    BRAKE = "brake"              # Deceleration effect
    STOP = "stop"                # Complete stop
    JOG = "jog"                  # Slow positional jogging
    UNKNOWN = "unknown"


@dataclass
class MIDIMessage:
    """MIDI message data."""
    timestamp: float          # Seconds
    cc_value: int            # 0-127
    channel: int = 0
    control_number: int = 0  # CC number


@dataclass
class GestureEvent:
    """Recognized gesture event."""
    gesture_type: GestureType
    confidence: float  # 0.0-1.0
    start_time: float  # Seconds
    end_time: float    # Seconds
    peak_velocity: float  # Maximum velocity magnitude
    duration: float  # Seconds
    direction: int  # 1 for clockwise, -1 for counter-clockwise
    metadata: Dict = None  # Additional info


class JogWheelFeatureExtractor:
    """
    Extracts features from MIDI jog wheel data.

    Processes raw CC values and computes gesture features.
    """

    def __init__(self, window_size: int = 100, sr: float = 100.0):
        """
        Initialize feature extractor.

        Args:
            window_size: Number of MIDI messages to buffer
            sr: Effective sample rate (messages per second)
        """
        self.window_size = window_size
        self.sr = sr
        self.buffer: deque = deque(maxlen=window_size)
        self.lock = Lock()

    def add_midi_message(self, cc_value: int, timestamp: float) -> None:
        """
        Add MIDI message to buffer.

        Args:
            cc_value: CC value (0-127, 64 = center)
            timestamp: Message timestamp in seconds
        """
        # MIDI jog wheel: 64 = center, >64 = clockwise, <64 = counter-clockwise
        with self.lock:
            self.buffer.append(MIDIMessage(
                timestamp=timestamp,
                cc_value=cc_value
            ))

    def extract_features(self) -> Optional[Dict[str, float]]:
        """
        Extract gesture features from buffer.

        Returns:
            Feature dictionary or None if buffer too small
        """
        with self.lock:
            if len(self.buffer) < 10:  # Need minimum messages
                return None

            messages = list(self.buffer)

        # Extract numeric features
        cc_values = np.array([m.cc_value for m in messages], dtype=float)
        timestamps = np.array([m.timestamp for m in messages], dtype=float)

        # Deviations from center (64)
        deviations = cc_values - 64.0

        # Direction (+1 if moving clockwise, -1 if counter-clockwise)
        directions = np.sign(deviations)

        # Velocity (rate of change)
        if len(cc_values) > 1:
            dt = np.diff(timestamps)
            dt = np.clip(dt, 1e-6, None)  # Avoid division by zero
            velocities = np.diff(cc_values) / dt
        else:
            velocities = np.array([0.0])

        # Acceleration
        if len(velocities) > 1:
            dt_vel = np.diff(timestamps[:-1])
            dt_vel = np.clip(dt_vel, 1e-6, None)
            accelerations = np.diff(velocities) / dt_vel
        else:
            accelerations = np.array([0.0])

        # Feature extraction
        features = {
            'mean_velocity': float(np.mean(np.abs(velocities))),
            'max_velocity': float(np.max(np.abs(velocities))),
            'min_velocity': float(np.min(np.abs(velocities))),
            'velocity_std': float(np.std(np.abs(velocities))),
            'velocity_range': float(np.max(np.abs(velocities)) - np.min(np.abs(velocities))),

            'mean_acceleration': float(np.mean(np.abs(accelerations))),
            'max_acceleration': float(np.max(np.abs(accelerations))),
            'acceleration_std': float(np.std(np.abs(accelerations))),

            'direction_changes': float(np.sum(np.diff(directions) != 0)),
            'dominant_direction': float(np.sign(np.sum(deviations))),
            'direction_consistency': float(np.mean(np.abs(directions))),

            'total_movement': float(np.sum(np.abs(deviations))),
            'duration': float(timestamps[-1] - timestamps[0]),
            'message_count': float(len(messages)),

            'is_moving': float(np.max(np.abs(velocities)) > 5.0),
        }

        return features


class GestureRecognizer:
    """
    Recognizes DJ gestures from jog wheel features.

    Uses rule-based classification with ML-ready architecture.
    """

    def __init__(self):
        """Initialize gesture recognizer."""
        self.feature_extractor = JogWheelFeatureExtractor()
        self.lock = Lock()
        self.last_gesture: Optional[GestureEvent] = None

        logger.info("GestureRecognizer initialized")

    def add_midi_message(self, cc_value: int, timestamp: float) -> Optional[GestureEvent]:
        """
        Process MIDI message and check for gesture.

        Args:
            cc_value: CC value (0-127)
            timestamp: Message timestamp

        Returns:
            GestureEvent if gesture detected, None otherwise
        """
        self.feature_extractor.add_midi_message(cc_value, timestamp)
        features = self.feature_extractor.extract_features()

        if features is None:
            return None

        # Classify gesture
        gesture = self._classify_gesture(features)

        if gesture.gesture_type != GestureType.UNKNOWN:
            with self.lock:
                self.last_gesture = gesture

        return gesture if gesture.confidence > 0.5 else None

    def _classify_gesture(self, features: Dict[str, float]) -> GestureEvent:
        """
        Classify gesture from features.

        Args:
            features: Extracted features

        Returns:
            GestureEvent with detected gesture
        """
        max_vel = features['max_velocity']
        mean_vel = features['mean_velocity']
        dir_changes = features['direction_changes']
        dur = features['duration']
        accel_std = features['acceleration_std']
        dir_consistency = features['direction_consistency']

        # Initialize result
        gesture = GestureType.UNKNOWN
        confidence = 0.0
        metadata = {}

        # SCRATCH: Rapid direction changes with consistent high velocity
        if dir_changes > 3 and max_vel > 50 and mean_vel > 20 and dur < 2.0:
            gesture = GestureType.SCRATCH
            confidence = 0.9
            metadata['scratch_type'] = self._classify_scratch_type(features)

        # NUDGE: Single quick movement, moderate velocity
        elif dir_changes < 2 and max_vel > 30 and max_vel < 80 and dur < 0.5:
            gesture = GestureType.NUDGE
            confidence = 0.85
            metadata['nudge_amount'] = features['total_movement']

        # SPIN: High velocity, consistent direction, medium duration
        elif dir_changes < 2 and max_vel > 80 and dur > 0.3 and dur < 3.0:
            gesture = GestureType.SPIN
            confidence = 0.88
            metadata['spin_velocity'] = mean_vel
            metadata['spin_direction'] = features['dominant_direction']

        # BRAKE: Decelerating motion (high initial velocity, low final)
        elif (max_vel > 60 and features['min_velocity'] < 10 and
              dir_changes < 2 and accel_std < 100):
            gesture = GestureType.BRAKE
            confidence = 0.85
            metadata['brake_strength'] = max_vel

        # STOP: Minimal movement
        elif max_vel < 5 and features['is_moving'] == 0:
            gesture = GestureType.STOP
            confidence = 0.95

        # JOG: Slow deliberate movement
        elif max_vel < 30 and dir_changes < 1:
            gesture = GestureType.JOG
            confidence = 0.8
            metadata['jog_position'] = features['total_movement']

        # Calculate additional metrics
        peak_velocity = max_vel
        direction = int(features['dominant_direction'])
        start_time = 0.0  # Would need tracking
        end_time = features['duration']

        return GestureEvent(
            gesture_type=gesture,
            confidence=confidence,
            start_time=start_time,
            end_time=end_time,
            peak_velocity=peak_velocity,
            duration=features['duration'],
            direction=direction,
            metadata=metadata or {}
        )

    def _classify_scratch_type(self, features: Dict[str, float]) -> str:
        """
        Classify type of scratch.

        Args:
            features: Gesture features

        Returns:
            Scratch type name
        """
        mean_vel = features['mean_velocity']
        dur = features['duration']

        if mean_vel > 100 and dur < 0.5:
            return "fast_cutter"
        elif dur < 1.0:
            return "scribble"
        else:
            return "transformer"  # Slower scratch style


class GestureActionMapper:
    """
    Maps recognized gestures to audio engine actions.
    """

    def __init__(self):
        """Initialize action mapper."""
        self.action_callbacks: Dict[GestureType, Callable] = {}
        self.lock = Lock()

    def register_action(self, gesture_type: GestureType,
                       callback: Callable[[GestureEvent], None]) -> None:
        """
        Register callback for gesture type.

        Args:
            gesture_type: Gesture to handle
            callback: Function to call with GestureEvent
        """
        with self.lock:
            self.action_callbacks[gesture_type] = callback

        logger.info(f"Action registered for: {gesture_type.value}")

    def execute_gesture(self, gesture: GestureEvent) -> bool:
        """
        Execute action for gesture.

        Args:
            gesture: Recognized gesture

        Returns:
            True if action executed
        """
        with self.lock:
            callback = self.action_callbacks.get(gesture.gesture_type)

        if callback is None:
            return False

        try:
            callback(gesture)
            return True
        except Exception as e:
            logger.error(f"Error executing gesture action: {e}")
            return False


class DJGestureActions:
    """
    Standard DJ actions for recognized gestures.
    """

    def __init__(self, audio_engine: Optional[object] = None):
        """
        Initialize with audio engine reference.

        Args:
            audio_engine: Audio processing engine for actual effects
        """
        self.audio_engine = audio_engine
        self.mapper = GestureActionMapper()

        # Register standard actions
        self.mapper.register_action(GestureType.SCRATCH, self.on_scratch)
        self.mapper.register_action(GestureType.NUDGE, self.on_nudge)
        self.mapper.register_action(GestureType.SPIN, self.on_spin)
        self.mapper.register_action(GestureType.BRAKE, self.on_brake)
        self.mapper.register_action(GestureType.STOP, self.on_stop)
        self.mapper.register_action(GestureType.JOG, self.on_jog)

    def on_scratch(self, gesture: GestureEvent) -> None:
        """Handle scratch gesture."""
        if self.audio_engine is None:
            logger.info(f"SCRATCH: {gesture.metadata.get('scratch_type', 'unknown')}")
            return

        scratch_type = gesture.metadata.get('scratch_type', 'scribble')
        velocity = gesture.peak_velocity

        logger.info(f"Applying {scratch_type} scratch, velocity={velocity:.0f}")
        # Would call: self.audio_engine.apply_scratch(scratch_type, velocity)

    def on_nudge(self, gesture: GestureEvent) -> None:
        """Handle nudge gesture."""
        if self.audio_engine is None:
            logger.info(f"NUDGE: amount={gesture.metadata.get('nudge_amount', 0):.0f}")
            return

        nudge_amount = gesture.metadata.get('nudge_amount', 0)
        direction = gesture.direction

        # Convert to tempo adjustment (% change)
        tempo_adjustment = (nudge_amount / 64.0) * 0.05 * direction

        logger.info(f"Tempo nudge: {tempo_adjustment:+.2%}")
        # Would call: self.audio_engine.adjust_tempo(tempo_adjustment)

    def on_spin(self, gesture: GestureEvent) -> None:
        """Handle spin gesture (fast forward/rewind)."""
        if self.audio_engine is None:
            velocity = gesture.metadata.get('spin_velocity', 0)
            direction = gesture.direction
            logger.info(f"SPIN: velocity={velocity:.0f}, direction={direction:+d}")
            return

        velocity = gesture.metadata.get('spin_velocity', 0)
        direction = gesture.direction

        # Fast forward/rewind speed
        seek_rate = (velocity / 100.0) * 2.0 * direction

        logger.info(f"Seeking: {seek_rate:.2f}x speed")
        # Would call: self.audio_engine.seek_relative(seek_rate * gesture.duration)

    def on_brake(self, gesture: GestureEvent) -> None:
        """Handle brake gesture."""
        if self.audio_engine is None:
            strength = gesture.metadata.get('brake_strength', 0)
            logger.info(f"BRAKE: strength={strength:.0f}")
            return

        strength = gesture.metadata.get('brake_strength', 0)

        # Brake duration depends on strength
        brake_duration = (strength / 100.0) * 2.0  # Up to 2 seconds

        logger.info(f"Brake effect: {brake_duration:.2f}s deceleration")
        # Would call: self.audio_engine.apply_brake(brake_duration)

    def on_stop(self, gesture: GestureEvent) -> None:
        """Handle stop gesture."""
        logger.info("STOP: Playback stopped")
        # Would call: self.audio_engine.stop()

    def on_jog(self, gesture: GestureEvent) -> None:
        """Handle jog gesture (positional seeking)."""
        position = gesture.metadata.get('jog_position', 0)
        direction = gesture.direction

        logger.info(f"JOG: position={position:.0f}, direction={direction:+d}")
        # Would call: self.audio_engine.set_position_relative(position * direction)

    def process_gesture(self, gesture: GestureEvent) -> bool:
        """
        Process recognized gesture.

        Args:
            gesture: Recognized gesture

        Returns:
            True if handled
        """
        return self.mapper.execute_gesture(gesture)


class JogWheelGestureInterface:
    """
    Complete jog wheel gesture interface.

    Integrates feature extraction, recognition, and action execution.
    """

    def __init__(self, audio_engine: Optional[object] = None):
        """
        Initialize jog wheel interface.

        Args:
            audio_engine: Audio processing engine
        """
        self.recognizer = GestureRecognizer()
        self.actions = DJGestureActions(audio_engine)
        self.lock = Lock()
        self.last_gesture: Optional[GestureEvent] = None

        logger.info("JogWheelGestureInterface initialized")

    def process_midi_cc(self, cc_value: int, timestamp: float) -> Optional[GestureEvent]:
        """
        Process MIDI CC message from jog wheel.

        Args:
            cc_value: CC value (0-127)
            timestamp: Message timestamp

        Returns:
            GestureEvent if gesture detected and executed
        """
        # Recognize gesture
        gesture = self.recognizer.add_midi_message(cc_value, timestamp)

        if gesture and gesture.confidence > 0.6:
            # Execute action
            if self.actions.process_gesture(gesture):
                with self.lock:
                    self.last_gesture = gesture

                return gesture

        return None

    def get_last_gesture(self) -> Optional[GestureEvent]:
        """Get last recognized gesture."""
        with self.lock:
            return self.last_gesture

    def reset(self) -> None:
        """Reset recognizer state."""
        self.recognizer.feature_extractor.buffer.clear()
        with self.lock:
            self.last_gesture = None
