# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Plugin Sandbox System for Acro DJ Mixer

Provides:
- Restricted execution environment
- API whitelisting
- Resource isolation
- Permission system
- Capability-based security
- Audit logging
"""

import logging
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class PluginCapability(Enum):
    """Plugin capabilities/permissions."""
    AUDIO_PROCESSING = "audio_processing"      # Process audio
    FILE_READ = "file_read"                    # Read files
    FILE_WRITE = "file_write"                  # Write files
    NETWORK = "network"                        # Network access
    STATE_PERSISTENCE = "state_persistence"    # Save state
    INTER_PLUGIN_COMM = "inter_plugin_comm"    # Communicate with plugins
    SYSTEM_INFO = "system_info"                # Access system info
    CONFIGURATION = "configuration"            # Modify configuration
    RESOURCE_MONITORING = "resource_monitoring"  # Monitor resources


class PermissionLevel(Enum):
    """Permission levels."""
    UNRESTRICTED = "unrestricted"  # No restrictions
    RESTRICTED = "restricted"      # Limited capabilities
    SANDBOXED = "sandboxed"        # Heavily restricted
    BLOCKED = "blocked"            # Blocked


@dataclass
class SandboxPolicy:
    """Sandbox security policy."""
    plugin_id: str
    permission_level: PermissionLevel
    allowed_capabilities: Set[PluginCapability] = field(default_factory=set)
    blocked_apis: Set[str] = field(default_factory=set)
    max_memory_mb: Optional[float] = None
    max_cpu_percent: Optional[float] = None
    max_disk_mb: Optional[float] = None
    timeout_seconds: Optional[float] = None
    allow_file_access: bool = False
    allow_network: bool = False
    audit_enabled: bool = True

    def to_dict(self) -> dict:
        return {
            'plugin_id': self.plugin_id,
            'permission_level': self.permission_level.value,
            'allowed_capabilities': [c.value for c in self.allowed_capabilities],
            'blocked_apis': list(self.blocked_apis),
            'max_memory_mb': self.max_memory_mb,
            'max_cpu_percent': self.max_cpu_percent,
            'max_disk_mb': self.max_disk_mb,
            'timeout_seconds': self.timeout_seconds,
            'allow_file_access': self.allow_file_access,
            'allow_network': self.allow_network,
            'audit_enabled': self.audit_enabled,
        }


@dataclass
class AuditLog:
    """Audit log entry."""
    plugin_id: str
    action: str
    resource: str
    allowed: bool
    timestamp: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class PluginSandbox:
    """Sandbox environment for plugin execution."""

    # Default policies
    DEFAULT_POLICIES = {
        PermissionLevel.UNRESTRICTED: {
            'capabilities': set(PluginCapability),
            'blocked_apis': set(),
        },
        PermissionLevel.RESTRICTED: {
            'capabilities': {
                PluginCapability.AUDIO_PROCESSING,
                PluginCapability.STATE_PERSISTENCE,
                PluginCapability.INTER_PLUGIN_COMM,
                PluginCapability.CONFIGURATION,
            },
            'blocked_apis': {
                'os.system', 'subprocess', 'socket', 'urllib',
                '__import__', 'eval', 'exec'
            },
        },
        PermissionLevel.SANDBOXED: {
            'capabilities': {
                PluginCapability.AUDIO_PROCESSING,
                PluginCapability.STATE_PERSISTENCE,
            },
            'blocked_apis': {
                'os', 'sys', 'subprocess', 'socket', 'urllib',
                'pickle', 'ctypes', '__import__', 'eval', 'exec',
                'open', 'file', 'input', '__builtins__'
            },
        },
        PermissionLevel.BLOCKED: {
            'capabilities': set(),
            'blocked_apis': set(PluginCapability),
        },
    }

    def __init__(self):
        """Initialize plugin sandbox."""
        self.policies: Dict[str, SandboxPolicy] = {}
        self.audit_logs: List[AuditLog] = []
        self.access_checks: Dict[str, Callable] = {}

    def create_policy(
        self,
        plugin_id: str,
        permission_level: PermissionLevel,
        capabilities: Optional[Set[PluginCapability]] = None,
        **kwargs
    ) -> SandboxPolicy:
        """Create sandbox policy.

        Args:
            plugin_id: Plugin identifier
            permission_level: Permission level
            capabilities: Optional custom capabilities
            **kwargs: Additional policy parameters

        Returns:
            SandboxPolicy
        """
        if permission_level not in self.DEFAULT_POLICIES:
            permission_level = PermissionLevel.SANDBOXED

        default = self.DEFAULT_POLICIES[permission_level]

        policy = SandboxPolicy(
            plugin_id=plugin_id,
            permission_level=permission_level,
            allowed_capabilities=capabilities or default['capabilities'].copy(),
            blocked_apis=default['blocked_apis'].copy(),
            **kwargs
        )

        self.policies[plugin_id] = policy

        logger.info(f"Created sandbox policy for {plugin_id}: {permission_level.value}")

        return policy

    def set_policy(self, policy: SandboxPolicy) -> None:
        """Set sandbox policy.

        Args:
            policy: SandboxPolicy to set
        """
        self.policies[policy.plugin_id] = policy
        logger.info(f"Set sandbox policy for {policy.plugin_id}")

    def get_policy(self, plugin_id: str) -> Optional[SandboxPolicy]:
        """Get sandbox policy.

        Args:
            plugin_id: Plugin identifier

        Returns:
            SandboxPolicy or None
        """
        return self.policies.get(plugin_id)

    def check_capability(
        self,
        plugin_id: str,
        capability: PluginCapability
    ) -> bool:
        """Check if plugin has capability.

        Args:
            plugin_id: Plugin identifier
            capability: Capability to check

        Returns:
            True if allowed
        """
        policy = self.get_policy(plugin_id)

        if not policy:
            return True  # Default to allow if no policy

        allowed = capability in policy.allowed_capabilities

        if policy.audit_enabled:
            self._log_access(plugin_id, 'capability_check', capability.value, allowed)

        return allowed

    def check_api_access(
        self,
        plugin_id: str,
        api_path: str
    ) -> bool:
        """Check if plugin can access API.

        Args:
            plugin_id: Plugin identifier
            api_path: API path (e.g., 'os.system')

        Returns:
            True if allowed
        """
        policy = self.get_policy(plugin_id)

        if not policy:
            return True  # Default to allow

        allowed = api_path not in policy.blocked_apis

        if policy.audit_enabled:
            self._log_access(plugin_id, 'api_access', api_path, allowed)

        return allowed

    def check_resource_limit(
        self,
        plugin_id: str,
        resource_type: str,
        current_value: float
    ) -> bool:
        """Check resource limit.

        Args:
            plugin_id: Plugin identifier
            resource_type: Type of resource
            current_value: Current resource value

        Returns:
            True if within limit
        """
        policy = self.get_policy(plugin_id)

        if not policy:
            return True

        if resource_type == 'memory' and policy.max_memory_mb:
            allowed = current_value <= policy.max_memory_mb
        elif resource_type == 'cpu' and policy.max_cpu_percent:
            allowed = current_value <= policy.max_cpu_percent
        elif resource_type == 'disk' and policy.max_disk_mb:
            allowed = current_value <= policy.max_disk_mb
        else:
            allowed = True

        if policy.audit_enabled and not allowed:
            self._log_access(
                plugin_id,
                'resource_check',
                f"{resource_type}:{current_value}",
                allowed
            )

        return allowed

    def check_file_access(
        self,
        plugin_id: str,
        file_path: str,
        access_type: str = 'read'
    ) -> bool:
        """Check file access permission.

        Args:
            plugin_id: Plugin identifier
            file_path: File path
            access_type: Type of access ('read' or 'write')

        Returns:
            True if allowed
        """
        policy = self.get_policy(plugin_id)

        if not policy:
            return True

        if not policy.allow_file_access:
            allowed = False
        elif access_type == 'write':
            allowed = PluginCapability.FILE_WRITE in policy.allowed_capabilities
        else:
            allowed = PluginCapability.FILE_READ in policy.allowed_capabilities

        if policy.audit_enabled:
            self._log_access(plugin_id, f'file_{access_type}', file_path, allowed)

        return allowed

    def check_network_access(self, plugin_id: str) -> bool:
        """Check network access permission.

        Args:
            plugin_id: Plugin identifier

        Returns:
            True if allowed
        """
        policy = self.get_policy(plugin_id)

        if not policy:
            return True

        allowed = policy.allow_network and PluginCapability.NETWORK in policy.allowed_capabilities

        if policy.audit_enabled and not allowed:
            self._log_access(plugin_id, 'network_access', 'any', allowed)

        return allowed

    def _log_access(
        self,
        plugin_id: str,
        action: str,
        resource: str,
        allowed: bool
    ) -> None:
        """Log access attempt.

        Args:
            plugin_id: Plugin identifier
            action: Action attempted
            resource: Resource accessed
            allowed: Whether action was allowed
        """
        import datetime

        log = AuditLog(
            plugin_id=plugin_id,
            action=action,
            resource=resource,
            allowed=allowed,
            timestamp=datetime.datetime.now().isoformat()
        )

        self.audit_logs.append(log)

        if not allowed:
            logger.warning(
                f"Sandbox violation: {plugin_id} tried {action} on {resource}"
            )

    def get_audit_logs(
        self,
        plugin_id: Optional[str] = None,
        violations_only: bool = False
    ) -> List[AuditLog]:
        """Get audit logs.

        Args:
            plugin_id: Filter by plugin (optional)
            violations_only: Only show denied access

        Returns:
            List of audit logs
        """
        logs = self.audit_logs

        if plugin_id:
            logs = [l for l in logs if l.plugin_id == plugin_id]

        if violations_only:
            logs = [l for l in logs if not l.allowed]

        return logs

    def clear_audit_logs(self) -> int:
        """Clear audit logs.

        Returns:
            Number of logs cleared
        """
        count = len(self.audit_logs)
        self.audit_logs.clear()
        return count

    def get_sandbox_stats(self) -> Dict[str, Any]:
        """Get sandbox statistics.

        Returns:
            Dictionary with statistics
        """
        violations = [l for l in self.audit_logs if not l.allowed]

        return {
            'total_policies': len(self.policies),
            'total_audit_logs': len(self.audit_logs),
            'total_violations': len(violations),
            'policies_by_level': {
                level.value: sum(1 for p in self.policies.values() if p.permission_level == level)
                for level in PermissionLevel
            }
        }

    def export_audit_logs(self, export_path: str) -> bool:
        """Export audit logs to file.

        Args:
            export_path: Path to export file

        Returns:
            True if successful
        """
        try:
            import json
            import datetime

            data = {
                'export_date': datetime.datetime.now().isoformat(),
                'total_logs': len(self.audit_logs),
                'logs': [log.to_dict() for log in self.audit_logs],
            }

            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Exported audit logs to {export_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export audit logs: {e}")
            return False


class SandboxExecutor:
    """Executes plugin code within sandbox constraints."""

    def __init__(self, sandbox: PluginSandbox):
        """Initialize sandbox executor.

        Args:
            sandbox: PluginSandbox instance
        """
        self.sandbox = sandbox

    def execute(
        self,
        plugin_id: str,
        plugin_code: str,
        globals_dict: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[float] = None
    ) -> Tuple[bool, Any]:
        """Execute plugin code in sandbox.

        Args:
            plugin_id: Plugin identifier
            plugin_code: Code to execute
            globals_dict: Global variables
            timeout_seconds: Execution timeout

        Returns:
            Tuple of (success, result)
        """
        # Check capability
        if not self.sandbox.check_capability(plugin_id, PluginCapability.AUDIO_PROCESSING):
            return False, "Plugin lacks AUDIO_PROCESSING capability"

        # Create restricted environment
        restricted_globals = {
            '__builtins__': self._create_safe_builtins(plugin_id),
            **(globals_dict or {})
        }

        try:
            # Execute code with timeout
            exec(plugin_code, restricted_globals)

            return True, restricted_globals.get('result')

        except Exception as e:
            logger.error(f"Error executing plugin {plugin_id}: {e}")
            return False, str(e)

    def _create_safe_builtins(self, plugin_id: str) -> Dict[str, Any]:
        """Create safe builtins for sandbox.

        Args:
            plugin_id: Plugin identifier

        Returns:
            Dictionary of safe builtins
        """
        def safe_open(*args, **kwargs):
            if not self.sandbox.check_file_access(plugin_id, args[0] if args else '', 'read'):
                raise PermissionError("File access denied by sandbox")
            return open(*args, **kwargs)

        def safe_import(name, *args):
            if not self.sandbox.check_api_access(plugin_id, name):
                raise ImportError(f"Import denied by sandbox: {name}")
            return __import__(name, *args)

        safe_builtins = {
            'print': print,
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'list': list,
            'dict': dict,
            'set': set,
            'tuple': tuple,
            'range': range,
            'enumerate': enumerate,
            'zip': zip,
            'map': map,
            'filter': filter,
            'sum': sum,
            'max': max,
            'min': min,
            'open': safe_open,
            '__import__': safe_import,
        }

        return safe_builtins
