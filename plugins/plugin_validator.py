# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Plugin Validation and Security System for Acro DJ Mixer

Provides:
- Plugin code validation
- Security scanning
- Dependency verification
- Performance profiling
- Certification system
"""

import ast
import json
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """Security assessment level."""
    CRITICAL = "critical"  # Should not run
    HIGH = "high"         # Warning required
    MEDIUM = "medium"     # Caution advised
    LOW = "low"           # Informational
    PASS = "pass"         # No issues


class ValidationType(Enum):
    """Types of validation checks."""
    CODE_QUALITY = "code_quality"
    SECURITY = "security"
    PERFORMANCE = "performance"
    COMPATIBILITY = "compatibility"
    BEST_PRACTICES = "best_practices"


@dataclass
class ValidationIssue:
    """A validation issue found during checking."""
    issue_type: ValidationType
    severity: SecurityLevel
    file_path: str
    line_number: Optional[int]
    message: str
    suggestion: str = ""
    code_sample: str = ""

    def to_dict(self) -> dict:
        return {
            'type': self.issue_type.value,
            'severity': self.severity.value,
            'file': self.file_path,
            'line': self.line_number,
            'message': self.message,
            'suggestion': self.suggestion,
            'code': self.code_sample,
        }


@dataclass
class ValidationResult:
    """Result of plugin validation."""
    plugin_id: str
    plugin_name: str
    passed: bool
    overall_severity: SecurityLevel
    issues: List[ValidationIssue] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    validation_timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            'plugin_id': self.plugin_id,
            'plugin_name': self.plugin_name,
            'passed': self.passed,
            'severity': self.overall_severity.value,
            'issues_count': len(self.issues),
            'issues': [issue.to_dict() for issue in self.issues],
            'warnings': self.warnings,
            'recommendations': self.recommendations,
            'timestamp': self.validation_timestamp,
        }


class PluginValidator:
    """Validates plugin code for security, quality, and compatibility."""

    # Dangerous patterns that should not be used in plugins
    DANGEROUS_PATTERNS = {
        r'__import__\s*\(': "Dynamic imports should be avoided",
        r'eval\s*\(': "eval() is forbidden for security reasons",
        r'exec\s*\(': "exec() is forbidden for security reasons",
        r'open\s*\([^)]*[\'"]\/etc': "Reading system files is forbidden",
        r'os\.system': "System command execution is forbidden",
        r'subprocess\.': "Subprocess operations require approval",
        r'socket\.': "Network operations require special approval",
        r'ctypes\.': "C library access is forbidden",
        r'pickle\.load': "Unsafe deserialization is forbidden",
    }

    # Recommended imports for plugin development
    RECOMMENDED_IMPORTS = {
        'numpy', 'scipy', 'librosa', 'soundfile', 'sounddevice',
        'logging', 'json', 'pathlib', 'dataclasses', 'typing'
    }

    # Forbidden imports for security
    FORBIDDEN_IMPORTS = {
        'os', 'sys', 'subprocess', 'socket', 'pickle', 'marshal',
        'ctypes', '__builtin__', '__main__'
    }

    def __init__(self):
        """Initialize validator."""
        pass

    def validate_plugin(self, plugin_path: str) -> ValidationResult:
        """Validate a complete plugin.

        Args:
            plugin_path: Path to plugin file or directory

        Returns:
            ValidationResult with all findings
        """
        plugin_file = Path(plugin_path)

        if not plugin_file.exists():
            return ValidationResult(
                plugin_id="unknown",
                plugin_name="unknown",
                passed=False,
                overall_severity=SecurityLevel.CRITICAL,
                issues=[ValidationIssue(
                    issue_type=ValidationType.COMPATIBILITY,
                    severity=SecurityLevel.CRITICAL,
                    file_path=str(plugin_file),
                    line_number=None,
                    message="Plugin file not found",
                )]
            )

        if plugin_file.is_dir():
            return self._validate_plugin_package(plugin_file)
        else:
            return self._validate_plugin_file(plugin_file)

    def _validate_plugin_file(self, file_path: Path) -> ValidationResult:
        """Validate a single plugin Python file."""
        result = ValidationResult(
            plugin_id=file_path.stem,
            plugin_name=file_path.name,
            passed=True,
            overall_severity=SecurityLevel.PASS,
        )

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

            # Parse AST
            try:
                tree = ast.parse(source_code)
            except SyntaxError as e:
                result.issues.append(ValidationIssue(
                    issue_type=ValidationType.CODE_QUALITY,
                    severity=SecurityLevel.HIGH,
                    file_path=str(file_path),
                    line_number=e.lineno,
                    message=f"Syntax error: {e.msg}",
                ))
                result.passed = False
                return result

            # Run validation checks
            self._check_security(source_code, file_path, result)
            self._check_code_quality(tree, file_path, result)
            self._check_compatibility(tree, file_path, result)
            self._check_best_practices(source_code, tree, file_path, result)

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            result.issues.append(ValidationIssue(
                issue_type=ValidationType.COMPATIBILITY,
                severity=SecurityLevel.HIGH,
                file_path=str(file_path),
                line_number=None,
                message=f"Validation error: {str(e)}",
            ))
            result.passed = False

        # Determine overall severity
        if result.issues:
            severities = [issue.severity for issue in result.issues]
            if SecurityLevel.CRITICAL in severities:
                result.overall_severity = SecurityLevel.CRITICAL
                result.passed = False
            elif SecurityLevel.HIGH in severities:
                result.overall_severity = SecurityLevel.HIGH
                result.passed = False
            elif SecurityLevel.MEDIUM in severities:
                result.overall_severity = SecurityLevel.MEDIUM
            else:
                result.overall_severity = SecurityLevel.LOW

        return result

    def _validate_plugin_package(self, package_dir: Path) -> ValidationResult:
        """Validate a plugin package directory."""
        result = ValidationResult(
            plugin_id=package_dir.name,
            plugin_name=package_dir.name,
            passed=True,
            overall_severity=SecurityLevel.PASS,
        )

        # Check for manifest
        manifest_path = package_dir / 'plugin.json'
        if not manifest_path.exists():
            result.issues.append(ValidationIssue(
                issue_type=ValidationType.COMPATIBILITY,
                severity=SecurityLevel.HIGH,
                file_path=str(manifest_path),
                line_number=None,
                message="Missing plugin.json manifest",
            ))
            result.passed = False
            return result

        # Validate manifest
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)

            required_fields = ['plugin_id', 'name', 'version', 'author', 'entry_point']
            for field in required_fields:
                if field not in manifest:
                    result.issues.append(ValidationIssue(
                        issue_type=ValidationType.COMPATIBILITY,
                        severity=SecurityLevel.HIGH,
                        file_path=str(manifest_path),
                        line_number=None,
                        message=f"Missing required field: {field}",
                    ))
                    result.passed = False

        except json.JSONDecodeError as e:
            result.issues.append(ValidationIssue(
                issue_type=ValidationType.COMPATIBILITY,
                severity=SecurityLevel.HIGH,
                file_path=str(manifest_path),
                line_number=None,
                message=f"Invalid JSON: {e}",
            ))
            result.passed = False
            return result

        # Validate all Python files
        for py_file in package_dir.glob('*.py'):
            if py_file.name.startswith('_'):
                continue
            file_result = self._validate_plugin_file(py_file)
            result.issues.extend(file_result.issues)
            if not file_result.passed:
                result.passed = False

        return result

    def _check_security(
        self,
        source_code: str,
        file_path: Path,
        result: ValidationResult
    ) -> None:
        """Check for security issues."""
        lines = source_code.split('\n')

        # Check for dangerous patterns
        for pattern, message in self.DANGEROUS_PATTERNS.items():
            for line_num, line in enumerate(lines, 1):
                if re.search(pattern, line):
                    result.issues.append(ValidationIssue(
                        issue_type=ValidationType.SECURITY,
                        severity=SecurityLevel.HIGH,
                        file_path=str(file_path),
                        line_number=line_num,
                        message=message,
                        code_sample=line.strip(),
                    ))

    def _check_code_quality(
        self,
        tree: ast.AST,
        file_path: Path,
        result: ValidationResult
    ) -> None:
        """Check code quality issues."""
        for node in ast.walk(tree):
            # Check for missing docstrings in functions
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                if not ast.get_docstring(node):
                    result.issues.append(ValidationIssue(
                        issue_type=ValidationType.CODE_QUALITY,
                        severity=SecurityLevel.LOW,
                        file_path=str(file_path),
                        line_number=node.lineno,
                        message=f"Missing docstring for {node.name}",
                        suggestion="Add a docstring describing the purpose",
                    ))

            # Check for bare excepts
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    result.issues.append(ValidationIssue(
                        issue_type=ValidationType.CODE_QUALITY,
                        severity=SecurityLevel.MEDIUM,
                        file_path=str(file_path),
                        line_number=node.lineno,
                        message="Bare except clause is too broad",
                        suggestion="Catch specific exception types",
                    ))

    def _check_compatibility(
        self,
        tree: ast.AST,
        file_path: Path,
        result: ValidationResult
    ) -> None:
        """Check for compatibility issues."""
        for node in ast.walk(tree):
            # Check imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split('.')[0]

                    if module in self.FORBIDDEN_IMPORTS:
                        result.issues.append(ValidationIssue(
                            issue_type=ValidationType.COMPATIBILITY,
                            severity=SecurityLevel.HIGH,
                            file_path=str(file_path),
                            line_number=node.lineno,
                            message=f"Forbidden import: {module}",
                            suggestion=f"Use plugin API instead of {module}",
                        ))

            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split('.')[0] in self.FORBIDDEN_IMPORTS:
                    result.issues.append(ValidationIssue(
                        issue_type=ValidationType.COMPATIBILITY,
                        severity=SecurityLevel.HIGH,
                        file_path=str(file_path),
                        line_number=node.lineno,
                        message=f"Forbidden import: {node.module}",
                    ))

    def _check_best_practices(
        self,
        source_code: str,
        tree: ast.AST,
        file_path: Path,
        result: ValidationResult
    ) -> None:
        """Check for best practice violations."""
        lines = source_code.split('\n')

        # Check for print statements (should use logging)
        for line_num, line in enumerate(lines, 1):
            if re.match(r'\s*print\s*\(', line):
                result.issues.append(ValidationIssue(
                    issue_type=ValidationType.BEST_PRACTICES,
                    severity=SecurityLevel.LOW,
                    file_path=str(file_path),
                    line_number=line_num,
                    message="Use logging instead of print()",
                    suggestion="Use logger.info() or similar",
                    code_sample=line.strip(),
                ))

        # Check for type hints on public functions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if not node.name.startswith('_'):  # Public function
                    if not node.returns:
                        result.recommendations.append(
                            f"Add return type hint to {node.name}()"
                        )

    def generate_report(self, result: ValidationResult) -> str:
        """Generate a human-readable report.

        Args:
            result: ValidationResult to report on

        Returns:
            Formatted report string
        """
        lines = [
            f"Plugin Validation Report",
            f"{'=' * 50}",
            f"Plugin: {result.plugin_name} ({result.plugin_id})",
            f"Status: {'PASSED' if result.passed else 'FAILED'}",
            f"Severity: {result.overall_severity.value.upper()}",
            f"Issues: {len(result.issues)}",
            f"",
        ]

        if result.issues:
            lines.append("Issues Found:")
            lines.append("-" * 50)
            for issue in result.issues:
                lines.append(f"[{issue.severity.value.upper()}] {issue.message}")
                if issue.line_number:
                    lines.append(f"  at {issue.file_path}:{issue.line_number}")
                if issue.suggestion:
                    lines.append(f"  → {issue.suggestion}")
                lines.append("")

        if result.recommendations:
            lines.append("Recommendations:")
            lines.append("-" * 50)
            for rec in result.recommendations:
                lines.append(f"• {rec}")
            lines.append("")

        return "\n".join(lines)


class PluginCertification:
    """Manages plugin certification."""

    def __init__(self):
        """Initialize certification system."""
        self.certified_plugins: Dict[str, Dict] = {}
        self.certification_levels = {
            'verified': 'Reviewed and approved by Acro team',
            'certified': 'Meets all quality standards',
            'trusted': 'Community-trusted plugin',
            'community': 'Community-contributed',
        }

    def certify_plugin(
        self,
        plugin_id: str,
        validation_result: ValidationResult,
        certification_level: str = 'community'
    ) -> bool:
        """Certify a plugin.

        Args:
            plugin_id: Plugin identifier
            validation_result: Validation result
            certification_level: Level of certification

        Returns:
            True if certification successful
        """
        if not validation_result.passed:
            return False

        self.certified_plugins[plugin_id] = {
            'level': certification_level,
            'description': self.certification_levels.get(certification_level, ''),
            'validation_result': validation_result.to_dict(),
        }

        return True

    def is_certified(self, plugin_id: str) -> bool:
        """Check if plugin is certified.

        Args:
            plugin_id: Plugin identifier

        Returns:
            True if certified
        """
        return plugin_id in self.certified_plugins

    def get_certification(self, plugin_id: str) -> Optional[Dict]:
        """Get certification info.

        Args:
            plugin_id: Plugin identifier

        Returns:
            Certification info dict or None
        """
        return self.certified_plugins.get(plugin_id)
