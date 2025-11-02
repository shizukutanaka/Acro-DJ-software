# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Plugin Documentation Generator for Acro DJ Mixer

Provides:
- Automatic documentation generation from plugin metadata
- API reference extraction from docstrings
- Parameter documentation generation
- Example code extraction and formatting
- Markdown and HTML output formats
- Search index generation
- API compatibility documentation
"""

import ast
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime
import inspect

logger = logging.getLogger(__name__)


@dataclass
class ParameterDoc:
    """Documentation for a plugin parameter."""
    name: str
    type: str
    default_value: Any = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    description: str = ""
    ui_type: str = ""
    options: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MethodDoc:
    """Documentation for a plugin method."""
    name: str
    signature: str
    description: str = ""
    parameters: List[ParameterDoc] = field(default_factory=list)
    return_type: str = ""
    return_description: str = ""
    examples: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'signature': self.signature,
            'description': self.description,
            'parameters': [p.to_dict() for p in self.parameters],
            'return_type': self.return_type,
            'return_description': self.return_description,
            'examples': self.examples,
        }


@dataclass
class PluginDocumentation:
    """Complete plugin documentation."""
    plugin_id: str
    name: str
    version: str
    author: str
    description: str
    long_description: str = ""
    homepage: str = ""
    license: str = ""
    category: str = ""
    parameters: List[ParameterDoc] = field(default_factory=list)
    methods: List[MethodDoc] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    breaking_changes: List[str] = field(default_factory=list)
    api_version: str = "1.0"
    generated_date: str = ""

    def to_dict(self) -> dict:
        return {
            'plugin_id': self.plugin_id,
            'name': self.name,
            'version': self.version,
            'author': self.author,
            'description': self.description,
            'long_description': self.long_description,
            'homepage': self.homepage,
            'license': self.license,
            'category': self.category,
            'parameters': [p.to_dict() for p in self.parameters],
            'methods': [m.to_dict() for m in self.methods],
            'examples': self.examples,
            'dependencies': self.dependencies,
            'breaking_changes': self.breaking_changes,
            'api_version': self.api_version,
            'generated_date': self.generated_date,
        }


class PluginDocumentationGenerator:
    """Generates documentation from plugin code and metadata."""

    def __init__(self, output_dir: Optional[str] = None):
        """Initialize documentation generator.

        Args:
            output_dir: Directory to store generated documentation
        """
        self.output_dir = Path(output_dir) if output_dir else Path.cwd() / 'docs'
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_from_metadata(
        self,
        plugin_metadata: Dict[str, Any],
        plugin_parameters: List[Dict[str, Any]] = None,
        plugin_methods: List[Dict[str, Any]] = None
    ) -> PluginDocumentation:
        """Generate documentation from plugin metadata.

        Args:
            plugin_metadata: Plugin metadata dictionary
            plugin_parameters: List of parameter definitions
            plugin_methods: List of method definitions

        Returns:
            PluginDocumentation object
        """
        doc = PluginDocumentation(
            plugin_id=plugin_metadata.get('plugin_id', 'unknown'),
            name=plugin_metadata.get('name', ''),
            version=plugin_metadata.get('version', '1.0.0'),
            author=plugin_metadata.get('author', ''),
            description=plugin_metadata.get('description', ''),
            long_description=plugin_metadata.get('long_description', ''),
            homepage=plugin_metadata.get('homepage', ''),
            license=plugin_metadata.get('license', 'MIT'),
            category=plugin_metadata.get('category', ''),
            dependencies=plugin_metadata.get('dependencies', []),
            api_version=plugin_metadata.get('api_version', '1.0'),
            generated_date=datetime.now().isoformat(),
        )

        # Process parameters
        if plugin_parameters:
            for param in plugin_parameters:
                param_doc = ParameterDoc(
                    name=param.get('name', ''),
                    type=param.get('type', 'unknown'),
                    default_value=param.get('default_value'),
                    min_value=param.get('min_value'),
                    max_value=param.get('max_value'),
                    description=param.get('description', ''),
                    ui_type=param.get('ui_type', ''),
                    options=param.get('options', []),
                )
                doc.parameters.append(param_doc)

        # Process methods
        if plugin_methods:
            for method in plugin_methods:
                method_doc = MethodDoc(
                    name=method.get('name', ''),
                    signature=method.get('signature', ''),
                    description=method.get('description', ''),
                    return_type=method.get('return_type', ''),
                    return_description=method.get('return_description', ''),
                    examples=method.get('examples', []),
                )
                doc.methods.append(method_doc)

        return doc

    def generate_from_source_code(
        self,
        source_file: str
    ) -> PluginDocumentation:
        """Generate documentation by parsing source code.

        Args:
            source_file: Path to Python source file

        Returns:
            PluginDocumentation object
        """
        source_path = Path(source_file)

        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_file}")

        try:
            with open(source_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

            tree = ast.parse(source_code)

            # Extract metadata
            metadata = self._extract_metadata(tree)
            parameters = self._extract_parameters(tree)
            methods = self._extract_methods(tree)
            examples = self._extract_examples(source_code)

            # Generate documentation
            doc = self.generate_from_metadata(metadata, parameters, methods)
            doc.examples = examples

            logger.info(f"Generated documentation for {source_path.name}")
            return doc

        except Exception as e:
            logger.error(f"Failed to generate documentation: {e}")
            raise

    def _extract_metadata(self, tree: ast.AST) -> Dict[str, Any]:
        """Extract plugin metadata from AST.

        Args:
            tree: Abstract syntax tree

        Returns:
            Dictionary of metadata
        """
        metadata = {
            'plugin_id': 'unknown',
            'name': 'Unknown Plugin',
            'version': '1.0.0',
            'author': 'Unknown',
            'description': '',
            'category': '',
            'dependencies': [],
        }

        # Look for PLUGIN_METADATA assignment
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == 'PLUGIN_METADATA':
                        if isinstance(node.value, ast.Call):
                            # Extract from constructor call
                            for keyword in node.value.keywords:
                                if keyword.arg in metadata:
                                    try:
                                        metadata[keyword.arg] = ast.literal_eval(keyword.value)
                                    except (ValueError, TypeError):
                                        pass

        # Extract module docstring
        if ast.get_docstring(tree):
            metadata['description'] = ast.get_docstring(tree)

        return metadata

    def _extract_parameters(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract parameter definitions from AST.

        Args:
            tree: Abstract syntax tree

        Returns:
            List of parameter definitions
        """
        parameters = []

        # Look for register_parameter calls
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr == 'register_parameter':
                        # Extract parameter from Parameter() call
                        if node.args:
                            param_arg = node.args[0]
                            if isinstance(param_arg, ast.Call):
                                param_dict = self._extract_call_kwargs(param_arg)
                                if param_dict:
                                    parameters.append(param_dict)

        return parameters

    def _extract_methods(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract method documentation from AST.

        Args:
            tree: Abstract syntax tree

        Returns:
            List of method definitions
        """
        methods = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Skip private methods
                if node.name.startswith('_'):
                    continue

                method_dict = {
                    'name': node.name,
                    'signature': self._get_function_signature(node),
                    'description': ast.get_docstring(node) or '',
                    'return_type': self._get_return_annotation(node),
                    'examples': [],
                }

                methods.append(method_dict)

        return methods

    def _extract_examples(self, source_code: str) -> List[str]:
        """Extract example code blocks from source.

        Args:
            source_code: Python source code

        Returns:
            List of example code blocks
        """
        examples = []

        # Look for lines starting with "Example:" or ">>>"
        lines = source_code.split('\n')
        in_example = False
        example_lines = []

        for line in lines:
            if 'Example:' in line or 'example:' in line:
                in_example = True
                example_lines = []
            elif line.strip().startswith('>>>'):
                in_example = True
                example_lines.append(line.strip())
            elif in_example:
                if line.strip() and not line.startswith(' ' * 8):
                    if example_lines:
                        examples.append('\n'.join(example_lines))
                    in_example = False
                    example_lines = []
                else:
                    example_lines.append(line)

        if example_lines:
            examples.append('\n'.join(example_lines))

        return examples

    def _extract_call_kwargs(self, call_node: ast.Call) -> Dict[str, Any]:
        """Extract keyword arguments from function call.

        Args:
            call_node: Function call AST node

        Returns:
            Dictionary of kwargs
        """
        kwargs = {}

        for keyword in call_node.keywords:
            try:
                kwargs[keyword.arg] = ast.literal_eval(keyword.value)
            except (ValueError, TypeError):
                kwargs[keyword.arg] = str(keyword.value)

        return kwargs

    def _get_function_signature(self, func_node: ast.FunctionDef) -> str:
        """Get function signature string.

        Args:
            func_node: Function definition node

        Returns:
            Function signature string
        """
        args = []
        for arg in func_node.args.args:
            args.append(arg.arg)

        return f"{func_node.name}({', '.join(args)})"

    def _get_return_annotation(self, func_node: ast.FunctionDef) -> str:
        """Get return type annotation.

        Args:
            func_node: Function definition node

        Returns:
            Return type as string
        """
        if func_node.returns:
            return ast.unparse(func_node.returns)
        return ""

    def generate_markdown(
        self,
        doc: PluginDocumentation
    ) -> str:
        """Generate Markdown documentation.

        Args:
            doc: PluginDocumentation object

        Returns:
            Markdown string
        """
        lines = []

        # Header
        lines.append(f"# {doc.name}")
        lines.append("")
        lines.append(f"**Plugin ID**: `{doc.plugin_id}`  ")
        lines.append(f"**Version**: `{doc.version}`  ")
        lines.append(f"**Author**: {doc.author}  ")
        lines.append(f"**License**: {doc.license}  ")
        lines.append("")

        # Description
        lines.append(f"## Description")
        lines.append(doc.description)
        lines.append("")

        if doc.long_description:
            lines.append(doc.long_description)
            lines.append("")

        # Parameters
        if doc.parameters:
            lines.append("## Parameters")
            lines.append("")

            for param in doc.parameters:
                lines.append(f"### `{param.name}`")
                lines.append(f"- **Type**: `{param.type}`")
                if param.default_value is not None:
                    lines.append(f"- **Default**: `{param.default_value}`")
                if param.min_value is not None or param.max_value is not None:
                    range_str = "["
                    if param.min_value is not None:
                        range_str += str(param.min_value)
                    range_str += ", "
                    if param.max_value is not None:
                        range_str += str(param.max_value)
                    range_str += "]"
                    lines.append(f"- **Range**: {range_str}")
                if param.ui_type:
                    lines.append(f"- **UI Type**: `{param.ui_type}`")
                if param.description:
                    lines.append(f"- **Description**: {param.description}")
                lines.append("")

        # Methods
        if doc.methods:
            lines.append("## Methods")
            lines.append("")

            for method in doc.methods:
                lines.append(f"### `{method.signature}`")
                if method.description:
                    lines.append(method.description)
                    lines.append("")
                if method.return_type:
                    lines.append(f"**Returns**: `{method.return_type}`")
                    if method.return_description:
                        lines.append(f" - {method.return_description}")
                    lines.append("")
                lines.append("")

        # Examples
        if doc.examples:
            lines.append("## Examples")
            lines.append("")

            for i, example in enumerate(doc.examples, 1):
                lines.append(f"### Example {i}")
                lines.append("```python")
                lines.append(example)
                lines.append("```")
                lines.append("")

        # Dependencies
        if doc.dependencies:
            lines.append("## Dependencies")
            lines.append("")
            for dep in doc.dependencies:
                lines.append(f"- {dep}")
            lines.append("")

        # Breaking Changes
        if doc.breaking_changes:
            lines.append("## Breaking Changes")
            lines.append("")
            for change in doc.breaking_changes:
                lines.append(f"- {change}")
            lines.append("")

        # Footer
        lines.append("---")
        lines.append(f"Generated on {doc.generated_date}")

        return "\n".join(lines)

    def generate_html(
        self,
        doc: PluginDocumentation
    ) -> str:
        """Generate HTML documentation.

        Args:
            doc: PluginDocumentation object

        Returns:
            HTML string
        """
        html = []

        html.append("<!DOCTYPE html>")
        html.append("<html>")
        html.append("<head>")
        html.append(f"<title>{doc.name} Documentation</title>")
        html.append("<meta charset='utf-8'>")
        html.append("<style>")
        html.append(self._get_default_css())
        html.append("</style>")
        html.append("</head>")
        html.append("<body>")

        html.append("<div class='container'>")

        # Header
        html.append(f"<h1>{doc.name}</h1>")
        html.append("<dl class='meta'>")
        html.append(f"<dt>Plugin ID</dt><dd><code>{doc.plugin_id}</code></dd>")
        html.append(f"<dt>Version</dt><dd><code>{doc.version}</code></dd>")
        html.append(f"<dt>Author</dt><dd>{doc.author}</dd>")
        html.append(f"<dt>License</dt><dd>{doc.license}</dd>")
        html.append("</dl>")

        # Description
        html.append("<section class='description'>")
        html.append(f"<h2>Description</h2>")
        html.append(f"<p>{doc.description}</p>")
        if doc.long_description:
            html.append(f"<p>{doc.long_description}</p>")
        html.append("</section>")

        # Parameters
        if doc.parameters:
            html.append("<section class='parameters'>")
            html.append("<h2>Parameters</h2>")
            html.append("<table>")
            html.append("<tr><th>Name</th><th>Type</th><th>Default</th><th>Description</th></tr>")

            for param in doc.parameters:
                html.append("<tr>")
                html.append(f"<td><code>{param.name}</code></td>")
                html.append(f"<td>{param.type}</td>")
                default = param.default_value if param.default_value is not None else "-"
                html.append(f"<td>{default}</td>")
                html.append(f"<td>{param.description}</td>")
                html.append("</tr>")

            html.append("</table>")
            html.append("</section>")

        html.append("</div>")
        html.append("</body>")
        html.append("</html>")

        return "\n".join(html)

    def save_documentation(
        self,
        doc: PluginDocumentation,
        format: str = "markdown"
    ) -> Tuple[bool, str]:
        """Save generated documentation to file.

        Args:
            doc: PluginDocumentation object
            format: Output format ('markdown' or 'html')

        Returns:
            Tuple of (success, file_path)
        """
        try:
            if format == "markdown":
                content = self.generate_markdown(doc)
                filename = f"{doc.plugin_id}_docs.md"
            elif format == "html":
                content = self.generate_html(doc)
                filename = f"{doc.plugin_id}_docs.html"
            else:
                return False, f"Unknown format: {format}"

            file_path = self.output_dir / filename

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"Saved documentation to {file_path}")
            return True, str(file_path)

        except Exception as e:
            logger.error(f"Failed to save documentation: {e}")
            return False, str(e)

    def export_as_json(
        self,
        doc: PluginDocumentation
    ) -> Tuple[bool, str]:
        """Export documentation as JSON.

        Args:
            doc: PluginDocumentation object

        Returns:
            Tuple of (success, file_path)
        """
        try:
            filename = f"{doc.plugin_id}_docs.json"
            file_path = self.output_dir / filename

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(doc.to_dict(), f, indent=2)

            logger.info(f"Exported documentation to {file_path}")
            return True, str(file_path)

        except Exception as e:
            logger.error(f"Failed to export documentation: {e}")
            return False, str(e)

    def generate_index(
        self,
        docs: List[PluginDocumentation]
    ) -> str:
        """Generate documentation index.

        Args:
            docs: List of PluginDocumentation objects

        Returns:
            Index markdown string
        """
        lines = []

        lines.append("# Plugin Documentation Index")
        lines.append("")
        lines.append(f"Generated: {datetime.now().isoformat()}")
        lines.append("")
        lines.append("## Available Plugins")
        lines.append("")

        # Group by category
        by_category = {}
        for doc in docs:
            category = doc.category or "Uncategorized"
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(doc)

        for category in sorted(by_category.keys()):
            lines.append(f"### {category}")
            lines.append("")

            for doc in by_category[category]:
                lines.append(f"- **{doc.name}** (`{doc.plugin_id}`)")
                lines.append(f"  - Version: {doc.version}")
                lines.append(f"  - Author: {doc.author}")
                lines.append(f"  - {doc.description}")
                lines.append("")

        return "\n".join(lines)

    def _get_default_css(self) -> str:
        """Get default CSS for HTML documentation."""
        return """
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1, h2, h3 { color: #2c3e50; }
        code {
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Monaco', 'Courier New', monospace;
        }
        dl.meta {
            display: grid;
            grid-template-columns: 100px 1fr;
            gap: 10px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        table th, table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        table th {
            background: #f9f9f9;
            font-weight: bold;
        }
        section { margin: 30px 0; }
        """
