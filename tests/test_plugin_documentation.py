# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Tests for Plugin Documentation Generator

Tests cover:
- Documentation generation from metadata
- Source code parsing and extraction
- Parameter and method documentation
- Markdown and HTML output
- JSON export
- Documentation index generation
"""

import pytest
import tempfile
from pathlib import Path

from plugins.plugin_documentation import (
    PluginDocumentation,
    ParameterDoc,
    MethodDoc,
    PluginDocumentationGenerator,
)


@pytest.fixture
def temp_output_dir():
    """Create temporary output directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def doc_generator(temp_output_dir):
    """Create documentation generator instance."""
    return PluginDocumentationGenerator(output_dir=temp_output_dir)


@pytest.fixture
def sample_documentation():
    """Create sample PluginDocumentation."""
    doc = PluginDocumentation(
        plugin_id="test_reverb",
        name="Test Reverb",
        version="1.0.0",
        author="Test Developer",
        description="A test reverb plugin",
        long_description="Detailed description of the reverb plugin",
        homepage="https://example.com",
        license="MIT",
        category="Audio Effect",
        api_version="1.0",
    )

    doc.parameters = [
        ParameterDoc(
            name="room_size",
            type="float",
            default_value=0.5,
            min_value=0.0,
            max_value=1.0,
            description="Size of virtual room",
            ui_type="slider"
        ),
        ParameterDoc(
            name="wet_dry",
            type="float",
            default_value=0.5,
            min_value=0.0,
            max_value=1.0,
            description="Mix between wet and dry signal",
            ui_type="slider"
        ),
    ]

    doc.methods = [
        MethodDoc(
            name="initialize",
            signature="initialize(config: dict)",
            description="Initialize the effect with configuration",
            return_type="None"
        ),
        MethodDoc(
            name="process_audio",
            signature="process_audio(audio: ndarray)",
            description="Process audio through the reverb",
            return_type="ndarray"
        ),
    ]

    doc.examples = [
        "effect = TestReverb()\neffect.initialize({'sample_rate': 44100})",
        "output = effect.process_audio(audio_data)",
    ]

    doc.dependencies = ["numpy>=1.20", "scipy>=1.7"]

    return doc


class TestParameterDocumentation:
    """Test parameter documentation."""

    def test_parameter_doc_creation(self):
        """Test creating parameter documentation."""
        param = ParameterDoc(
            name="intensity",
            type="float",
            default_value=0.5,
            min_value=0.0,
            max_value=1.0,
            description="Effect intensity"
        )

        assert param.name == "intensity"
        assert param.type == "float"
        assert param.default_value == 0.5

    def test_parameter_doc_to_dict(self):
        """Test converting parameter doc to dictionary."""
        param = ParameterDoc(
            name="gain",
            type="float",
            description="Gain in dB"
        )

        param_dict = param.to_dict()

        assert param_dict['name'] == "gain"
        assert param_dict['type'] == "float"
        assert param_dict['description'] == "Gain in dB"


class TestMethodDocumentation:
    """Test method documentation."""

    def test_method_doc_creation(self):
        """Test creating method documentation."""
        method = MethodDoc(
            name="process_audio",
            signature="process_audio(audio)",
            description="Process audio"
        )

        assert method.name == "process_audio"
        assert method.signature == "process_audio(audio)"

    def test_method_doc_to_dict(self):
        """Test converting method doc to dictionary."""
        method = MethodDoc(
            name="initialize",
            signature="initialize(config)",
            return_type="None"
        )

        method_dict = method.to_dict()

        assert method_dict['name'] == "initialize"
        assert method_dict['return_type'] == "None"


class TestPluginDocumentation:
    """Test plugin documentation."""

    def test_plugin_doc_creation(self):
        """Test creating plugin documentation."""
        doc = PluginDocumentation(
            plugin_id="my_effect",
            name="My Effect",
            version="1.0.0",
            author="Developer",
            description="A test effect"
        )

        assert doc.plugin_id == "my_effect"
        assert doc.name == "My Effect"

    def test_plugin_doc_to_dict(self):
        """Test converting plugin doc to dictionary."""
        doc = PluginDocumentation(
            plugin_id="test",
            name="Test",
            version="1.0.0",
            author="Dev",
            description="Description"
        )

        doc_dict = doc.to_dict()

        assert doc_dict['plugin_id'] == "test"
        assert doc_dict['name'] == "Test"
        assert 'parameters' in doc_dict


class TestDocumentationGeneration:
    """Test documentation generation from metadata."""

    def test_generate_from_metadata_basic(self, doc_generator):
        """Test generating documentation from basic metadata."""
        metadata = {
            'plugin_id': 'test_plugin',
            'name': 'Test Plugin',
            'version': '1.0.0',
            'author': 'Developer',
            'description': 'A test plugin',
        }

        doc = doc_generator.generate_from_metadata(metadata)

        assert doc.plugin_id == 'test_plugin'
        assert doc.name == 'Test Plugin'
        assert doc.version == '1.0.0'

    def test_generate_from_metadata_with_parameters(self, doc_generator):
        """Test generating with parameters."""
        metadata = {
            'plugin_id': 'test',
            'name': 'Test',
            'version': '1.0.0',
            'author': 'Dev',
            'description': 'Test',
        }

        parameters = [
            {
                'name': 'intensity',
                'type': 'float',
                'default_value': 0.5,
                'description': 'Effect intensity',
            }
        ]

        doc = doc_generator.generate_from_metadata(metadata, parameters)

        assert len(doc.parameters) == 1
        assert doc.parameters[0].name == 'intensity'

    def test_generate_from_metadata_with_methods(self, doc_generator):
        """Test generating with methods."""
        metadata = {
            'plugin_id': 'test',
            'name': 'Test',
            'version': '1.0.0',
            'author': 'Dev',
            'description': 'Test',
        }

        methods = [
            {
                'name': 'process',
                'signature': 'process(audio)',
                'description': 'Process audio',
            }
        ]

        doc = doc_generator.generate_from_metadata(metadata, methods=methods)

        assert len(doc.methods) == 1
        assert doc.methods[0].name == 'process'


class TestMarkdownGeneration:
    """Test Markdown documentation generation."""

    def test_generate_markdown_basic(self, doc_generator, sample_documentation):
        """Test basic Markdown generation."""
        markdown = doc_generator.generate_markdown(sample_documentation)

        assert "# Test Reverb" in markdown
        assert "test_reverb" in markdown
        assert "1.0.0" in markdown
        assert "Test Developer" in markdown

    def test_generate_markdown_includes_description(self, doc_generator, sample_documentation):
        """Test Markdown includes description."""
        markdown = doc_generator.generate_markdown(sample_documentation)

        assert "A test reverb plugin" in markdown
        assert "Detailed description" in markdown

    def test_generate_markdown_includes_parameters(self, doc_generator, sample_documentation):
        """Test Markdown includes parameter documentation."""
        markdown = doc_generator.generate_markdown(sample_documentation)

        assert "## Parameters" in markdown
        assert "room_size" in markdown
        assert "wet_dry" in markdown
        assert "slider" in markdown

    def test_generate_markdown_includes_methods(self, doc_generator, sample_documentation):
        """Test Markdown includes method documentation."""
        markdown = doc_generator.generate_markdown(sample_documentation)

        assert "## Methods" in markdown
        assert "initialize" in markdown
        assert "process_audio" in markdown

    def test_generate_markdown_includes_examples(self, doc_generator, sample_documentation):
        """Test Markdown includes examples."""
        markdown = doc_generator.generate_markdown(sample_documentation)

        assert "## Examples" in markdown
        assert "Example 1" in markdown
        assert "python" in markdown

    def test_generate_markdown_includes_dependencies(self, doc_generator, sample_documentation):
        """Test Markdown includes dependencies."""
        markdown = doc_generator.generate_markdown(sample_documentation)

        assert "## Dependencies" in markdown
        assert "numpy" in markdown
        assert "scipy" in markdown

    def test_markdown_includes_metadata(self, doc_generator, sample_documentation):
        """Test Markdown includes all metadata."""
        markdown = doc_generator.generate_markdown(sample_documentation)

        assert "Plugin ID" in markdown
        assert "Version" in markdown
        assert "Author" in markdown
        assert "License" in markdown


class TestHTMLGeneration:
    """Test HTML documentation generation."""

    def test_generate_html_basic(self, doc_generator, sample_documentation):
        """Test basic HTML generation."""
        html = doc_generator.generate_html(sample_documentation)

        assert "<!DOCTYPE html>" in html
        assert "<html>" in html
        assert "Test Reverb" in html
        assert "</html>" in html

    def test_generate_html_includes_metadata(self, doc_generator, sample_documentation):
        """Test HTML includes metadata."""
        html = doc_generator.generate_html(sample_documentation)

        assert "test_reverb" in html
        assert "1.0.0" in html
        assert "Test Developer" in html

    def test_generate_html_includes_parameters(self, doc_generator, sample_documentation):
        """Test HTML includes parameters."""
        html = doc_generator.generate_html(sample_documentation)

        assert "room_size" in html
        assert "Parameters" in html
        assert "<table>" in html

    def test_generate_html_has_css(self, doc_generator, sample_documentation):
        """Test HTML includes CSS styling."""
        html = doc_generator.generate_html(sample_documentation)

        assert "<style>" in html
        assert "font-family" in html
        assert "</style>" in html


class TestDocumentationSaving:
    """Test saving generated documentation."""

    def test_save_markdown_documentation(self, doc_generator, sample_documentation):
        """Test saving Markdown documentation."""
        success, path = doc_generator.save_documentation(
            sample_documentation,
            format="markdown"
        )

        assert success
        assert "test_reverb_docs.md" in path
        assert Path(path).exists()

        # Verify content
        with open(path) as f:
            content = f.read()
            assert "# Test Reverb" in content

    def test_save_html_documentation(self, doc_generator, sample_documentation):
        """Test saving HTML documentation."""
        success, path = doc_generator.save_documentation(
            sample_documentation,
            format="html"
        )

        assert success
        assert "test_reverb_docs.html" in path
        assert Path(path).exists()

        # Verify content
        with open(path) as f:
            content = f.read()
            assert "<!DOCTYPE html>" in content

    def test_save_invalid_format(self, doc_generator, sample_documentation):
        """Test saving with invalid format."""
        success, error = doc_generator.save_documentation(
            sample_documentation,
            format="invalid"
        )

        assert not success
        assert "Unknown format" in error

    def test_export_as_json(self, doc_generator, sample_documentation):
        """Test exporting as JSON."""
        success, path = doc_generator.export_as_json(sample_documentation)

        assert success
        assert "test_reverb_docs.json" in path
        assert Path(path).exists()

        # Verify content
        import json
        with open(path) as f:
            data = json.load(f)
            assert data['plugin_id'] == "test_reverb"
            assert data['name'] == "Test Reverb"


class TestDocumentationIndex:
    """Test generating documentation index."""

    def test_generate_index(self, doc_generator):
        """Test generating documentation index."""
        doc1 = PluginDocumentation(
            plugin_id="effect1",
            name="Effect 1",
            version="1.0.0",
            author="Dev",
            description="First effect",
            category="Audio Effect"
        )

        doc2 = PluginDocumentation(
            plugin_id="effect2",
            name="Effect 2",
            version="1.0.0",
            author="Dev",
            description="Second effect",
            category="Audio Effect"
        )

        index = doc_generator.generate_index([doc1, doc2])

        assert "# Plugin Documentation Index" in index
        assert "Audio Effect" in index
        assert "Effect 1" in index
        assert "Effect 2" in index

    def test_index_groups_by_category(self, doc_generator):
        """Test that index groups plugins by category."""
        doc1 = PluginDocumentation(
            plugin_id="effect1",
            name="Effect 1",
            version="1.0.0",
            author="Dev",
            description="Effect",
            category="Audio Effect"
        )

        doc2 = PluginDocumentation(
            plugin_id="analyzer1",
            name="Analyzer 1",
            version="1.0.0",
            author="Dev",
            description="Analyzer",
            category="Analyzer"
        )

        index = doc_generator.generate_index([doc1, doc2])

        assert "### Audio Effect" in index
        assert "### Analyzer" in index


class TestSourceCodeParsing:
    """Test parsing documentation from source code."""

    def test_generate_from_source_code_missing_file(self, doc_generator):
        """Test error handling for missing source file."""
        with pytest.raises(FileNotFoundError):
            doc_generator.generate_from_source_code("/nonexistent/file.py")

    def test_generate_from_valid_source(self, doc_generator, temp_output_dir):
        """Test parsing valid source code."""
        # Create a sample plugin file
        source_code = '''
"""Test plugin module"""

class TestPlugin:
    """A test plugin class."""

    def process(self, data):
        """Process data.

        Args:
            data: Input data

        Returns:
            Processed data
        """
        return data * 2
'''

        source_file = Path(temp_output_dir) / "test_plugin.py"
        with open(source_file, 'w') as f:
            f.write(source_code)

        doc = doc_generator.generate_from_source_code(str(source_file))

        assert doc is not None
        assert "test_plugin" in doc.plugin_id.lower()


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_generate_with_empty_documentation(self, doc_generator):
        """Test generating with minimal documentation."""
        doc = PluginDocumentation(
            plugin_id="minimal",
            name="Minimal",
            version="1.0.0",
            author="Dev",
            description=""
        )

        markdown = doc_generator.generate_markdown(doc)

        assert "Minimal" in markdown
        assert "minimal" in markdown

    def test_documentation_with_special_characters(self, doc_generator):
        """Test handling special characters in documentation."""
        doc = PluginDocumentation(
            plugin_id="test",
            name="Test & Demo",
            version="1.0.0",
            author="Dev <dev@example.com>",
            description="Description with < > & characters"
        )

        html = doc_generator.generate_html(doc)

        # Should not crash
        assert "html" in html.lower()

    def test_very_large_parameter_list(self, doc_generator):
        """Test handling large number of parameters."""
        doc = PluginDocumentation(
            plugin_id="test",
            name="Test",
            version="1.0.0",
            author="Dev",
            description="Test"
        )

        # Add many parameters
        for i in range(100):
            doc.parameters.append(ParameterDoc(
                name=f"param_{i}",
                type="float",
                description=f"Parameter {i}"
            ))

        markdown = doc_generator.generate_markdown(doc)

        # Should handle large output
        assert "param_0" in markdown
        assert "param_99" in markdown
