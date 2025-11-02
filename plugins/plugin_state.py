# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Plugin State Management System for Acro DJ Mixer

Provides:
- Plugin state persistence and restoration
- State snapshots and versioning
- State validation and integrity checking
- State migration between versions
- State rollback capability
- Dirty state tracking
- State change notifications
"""

import json
import logging
import threading
from pathlib import Path
from typing import List, Dict, Optional, Any, Callable, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


class StateStatus(Enum):
    """Status of plugin state."""
    CLEAN = "clean"        # No unsaved changes
    DIRTY = "dirty"        # Has unsaved changes
    CORRUPTED = "corrupted"  # State data corrupted
    MIGRATING = "migrating"  # State being migrated


@dataclass
class StateSnapshot:
    """A snapshot of plugin state at a point in time."""
    snapshot_id: str
    plugin_id: str
    plugin_version: str
    state_data: Dict[str, Any]
    timestamp: str
    description: str = ""
    checksum: str = ""
    user_created: bool = False

    def __post_init__(self):
        """Calculate checksum."""
        if not self.checksum:
            data_str = json.dumps(self.state_data, sort_keys=True)
            self.checksum = hashlib.sha256(data_str.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        return asdict(self)

    def validate(self) -> bool:
        """Validate snapshot integrity.

        Returns:
            True if valid
        """
        data_str = json.dumps(self.state_data, sort_keys=True)
        calculated = hashlib.sha256(data_str.encode()).hexdigest()[:16]
        return calculated == self.checksum


@dataclass
class StateChange:
    """A change to plugin state."""
    change_id: str
    timestamp: str
    path: str                # State path (e.g., "config.gain")
    old_value: Any
    new_value: Any
    changed_by: str = "system"  # What triggered the change

    def to_dict(self) -> dict:
        return asdict(self)


class PluginStateManager:
    """Manages plugin state persistence and restoration."""

    def __init__(
        self,
        plugin_id: str,
        state_dir: Optional[str] = None,
        auto_save: bool = True
    ):
        """Initialize state manager.

        Args:
            plugin_id: Plugin identifier
            state_dir: Directory for state files
            auto_save: Automatically save state changes
        """
        self.plugin_id = plugin_id
        self.state_dir = Path(state_dir) if state_dir else Path.home() / '.acro' / 'plugin_states'
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Current state
        self.state: Dict[str, Any] = {}
        self.status = StateStatus.CLEAN

        # State history
        self.snapshots: Dict[str, StateSnapshot] = {}
        self.changes: List[StateChange] = []

        # Change tracking
        self.dirty_paths: set = set()
        self.auto_save = auto_save

        # Change callbacks
        self.change_callbacks: List[Callable] = []

        # Thread lock
        self.lock = threading.RLock()

        # Load existing state
        self._load_state()

    def set_state(self, state_data: Dict[str, Any]) -> None:
        """Set complete plugin state.

        Args:
            state_data: New state dictionary
        """
        with self.lock:
            old_state = self.state.copy()
            self.state = state_data.copy()
            self.status = StateStatus.DIRTY
            self.dirty_paths = set(self.state.keys())

            # Track changes
            for key in set(list(old_state.keys()) + list(state_data.keys())):
                old_val = old_state.get(key)
                new_val = state_data.get(key)

                if old_val != new_val:
                    self._record_change(key, old_val, new_val)

            # Notify callbacks
            self._notify_callbacks()

            if self.auto_save:
                self.save_state()

    def get_state(self) -> Dict[str, Any]:
        """Get current plugin state.

        Returns:
            State dictionary
        """
        with self.lock:
            return self.state.copy()

    def update_state(
        self,
        updates: Dict[str, Any],
        changed_by: str = "system"
    ) -> None:
        """Update specific state values.

        Args:
            updates: Dictionary of updates
            changed_by: What triggered the change
        """
        with self.lock:
            for key, value in updates.items():
                old_value = self.state.get(key)

                if old_value != value:
                    self.state[key] = value
                    self.dirty_paths.add(key)
                    self._record_change(key, old_value, value, changed_by)

            if updates:
                self.status = StateStatus.DIRTY
                self._notify_callbacks()

            if self.auto_save:
                self.save_state()

    def get_value(self, path: str, default: Any = None) -> Any:
        """Get state value by path.

        Args:
            path: State path (e.g., "config.gain")
            default: Default value if not found

        Returns:
            State value or default
        """
        with self.lock:
            keys = path.split('.')
            value = self.state

            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key)
                    if value is None:
                        return default
                else:
                    return default

            return value

    def set_value(self, path: str, value: Any) -> None:
        """Set state value by path.

        Args:
            path: State path (e.g., "config.gain")
            value: New value
        """
        with self.lock:
            keys = path.split('.')
            current = self.state

            # Navigate to parent
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]

            # Set value
            old_value = current.get(keys[-1])
            current[keys[-1]] = value

            if old_value != value:
                self.dirty_paths.add(path)
                self.status = StateStatus.DIRTY
                self._record_change(path, old_value, value)
                self._notify_callbacks()

                if self.auto_save:
                    self.save_state()

    def save_state(self) -> Tuple[bool, str]:
        """Save current state to disk.

        Returns:
            Tuple of (success, message)
        """
        try:
            with self.lock:
                state_file = self.state_dir / f"{self.plugin_id}_state.json"

                data = {
                    'plugin_id': self.plugin_id,
                    'state': self.state,
                    'save_date': datetime.now().isoformat(),
                }

                with open(state_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)

                self.status = StateStatus.CLEAN
                self.dirty_paths.clear()

                logger.info(f"Saved state for {self.plugin_id}")
                return True, "State saved successfully"

        except Exception as e:
            logger.error(f"Failed to save state: {e}")
            self.status = StateStatus.CORRUPTED
            return False, str(e)

    def _load_state(self) -> None:
        """Load state from disk."""
        try:
            state_file = self.state_dir / f"{self.plugin_id}_state.json"

            if state_file.exists():
                with open(state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.state = data.get('state', {})
                    self.status = StateStatus.CLEAN

                logger.info(f"Loaded state for {self.plugin_id}")
            else:
                self.state = {}
                self.status = StateStatus.CLEAN

        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            self.state = {}
            self.status = StateStatus.CORRUPTED

    def create_snapshot(
        self,
        plugin_version: str,
        description: str = "",
        user_created: bool = False
    ) -> str:
        """Create state snapshot.

        Args:
            plugin_version: Plugin version
            description: Optional description
            user_created: Whether user manually created snapshot

        Returns:
            Snapshot ID
        """
        snapshot_id = f"{self.plugin_id}_{datetime.now().timestamp()}"

        with self.lock:
            snapshot = StateSnapshot(
                snapshot_id=snapshot_id,
                plugin_id=self.plugin_id,
                plugin_version=plugin_version,
                state_data=self.state.copy(),
                timestamp=datetime.now().isoformat(),
                description=description,
                user_created=user_created
            )

            self.snapshots[snapshot_id] = snapshot

            # Save snapshot to disk
            self._save_snapshot(snapshot)

            logger.info(f"Created snapshot {snapshot_id}")
            return snapshot_id

    def restore_snapshot(self, snapshot_id: str) -> Tuple[bool, str]:
        """Restore state from snapshot.

        Args:
            snapshot_id: Snapshot ID to restore

        Returns:
            Tuple of (success, message)
        """
        if snapshot_id not in self.snapshots:
            return False, f"Snapshot not found: {snapshot_id}"

        snapshot = self.snapshots[snapshot_id]

        # Validate snapshot
        if not snapshot.validate():
            return False, "Snapshot validation failed (corrupted)"

        # Restore state
        self.set_state(snapshot.state_data)

        logger.info(f"Restored snapshot {snapshot_id}")
        return True, f"Restored to {snapshot.timestamp}"

    def list_snapshots(self) -> List[StateSnapshot]:
        """List all snapshots.

        Returns:
            List of snapshots
        """
        with self.lock:
            return list(self.snapshots.values())

    def get_state_changes(self, limit: Optional[int] = None) -> List[StateChange]:
        """Get state change history.

        Args:
            limit: Limit results

        Returns:
            List of state changes
        """
        with self.lock:
            changes = list(self.changes)

        if limit:
            changes = changes[-limit:]

        return changes

    def _record_change(
        self,
        path: str,
        old_value: Any,
        new_value: Any,
        changed_by: str = "system"
    ) -> None:
        """Record state change.

        Args:
            path: State path
            old_value: Previous value
            new_value: New value
            changed_by: What triggered change
        """
        change = StateChange(
            change_id=f"{self.plugin_id}_{datetime.now().timestamp()}",
            timestamp=datetime.now().isoformat(),
            path=path,
            old_value=old_value,
            new_value=new_value,
            changed_by=changed_by
        )

        self.changes.append(change)

        # Keep only recent changes
        if len(self.changes) > 1000:
            self.changes = self.changes[-1000:]

    def _save_snapshot(self, snapshot: StateSnapshot) -> None:
        """Save snapshot to disk.

        Args:
            snapshot: StateSnapshot to save
        """
        try:
            snapshot_file = self.state_dir / f"{snapshot.snapshot_id}.json"

            with open(snapshot_file, 'w', encoding='utf-8') as f:
                json.dump(snapshot.to_dict(), f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save snapshot: {e}")

    def _notify_callbacks(self) -> None:
        """Notify state change callbacks."""
        for callback in self.change_callbacks:
            try:
                callback(self.state)
            except Exception as e:
                logger.error(f"Error in state callback: {e}")

    def on_state_change(self, callback: Callable) -> str:
        """Register state change callback.

        Args:
            callback: Callback function (receives state dict)

        Returns:
            Callback ID
        """
        self.change_callbacks.append(callback)
        return str(len(self.change_callbacks) - 1)

    def reset_to_defaults(self, defaults: Dict[str, Any]) -> None:
        """Reset state to defaults.

        Args:
            defaults: Default state dictionary
        """
        with self.lock:
            self.state = defaults.copy()
            self.dirty_paths = set(defaults.keys())
            self.status = StateStatus.DIRTY
            self.changes.clear()
            self._notify_callbacks()

            if self.auto_save:
                self.save_state()

    def clear_state(self) -> None:
        """Clear all state."""
        with self.lock:
            self.state.clear()
            self.dirty_paths.clear()
            self.status = StateStatus.CLEAN
            self.changes.clear()

            if self.auto_save:
                self.save_state()

    def export_state(self, export_path: str) -> Tuple[bool, str]:
        """Export state to file.

        Args:
            export_path: Path to export file

        Returns:
            Tuple of (success, message)
        """
        try:
            with self.lock:
                data = {
                    'plugin_id': self.plugin_id,
                    'state': self.state,
                    'export_date': datetime.now().isoformat(),
                    'snapshots': [s.to_dict() for s in self.snapshots.values()],
                    'changes': [c.to_dict() for c in self.changes],
                }

            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Exported state to {export_path}")
            return True, f"State exported"

        except Exception as e:
            logger.error(f"Failed to export state: {e}")
            return False, str(e)

    def get_state_stats(self) -> Dict[str, Any]:
        """Get state statistics.

        Returns:
            Dictionary with statistics
        """
        with self.lock:
            return {
                'plugin_id': self.plugin_id,
                'status': self.status.value,
                'state_size': len(json.dumps(self.state)),
                'dirty_paths': len(self.dirty_paths),
                'total_snapshots': len(self.snapshots),
                'total_changes': len(self.changes),
            }
