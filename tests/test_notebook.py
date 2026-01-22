"""Tests for the notebook module."""

import json
import pytest

from gitsource.notebook import (
    CellInfo,
    NotebookDict,
    extract_cells,
    load_notebook,
    loads_notebook,
    loads_notebook_to_markdown,
    notebook_to_markdown,
    notebook_to_text,
)


# Sample notebook JSON for testing
SAMPLE_NOTEBOOK_JSON = json.dumps({
    "cells": [
        {
            "cell_type": "markdown",
            "source": ["# Test Notebook\n", "\n", "This is a test."],
            "metadata": {},
        },
        {
            "cell_type": "code",
            "source": ["print('hello world')"],
            "metadata": {},
            "outputs": [{"output_type": "stream", "name": "stdout", "text": ["hello world\n"]}],
            "execution_count": 1,
        },
        {
            "cell_type": "markdown",
            "source": ["## Section 2"],
            "metadata": {},
        },
    ],
    "metadata": {
        "kernelspec": {
            "name": "python3",
            "display_name": "Python 3",
        },
        "language_info": {"name": "python"},
    },
    "nbformat": 4,
    "nbformat_minor": 2,
})


class TestNotebookDict:
    """Tests for NotebookDict class."""

    def test_attribute_access(self):
        nb = NotebookDict({"cells": [{"cell_type": "code"}]})
        assert nb.cells == [{"cell_type": "code"}]
        assert nb["cells"] == [{"cell_type": "code"}]

    def test_nested_wrapping(self):
        nb = NotebookDict({
            "cells": [{"cell_type": "code", "metadata": {}}],
            "metadata": {"key": "value"},
        })
        assert isinstance(nb.cells[0], NotebookDict)
        assert isinstance(nb.metadata, NotebookDict)

    def test_missing_attribute_raises(self):
        nb = NotebookDict({"cells": []})
        with pytest.raises(AttributeError):
            _ = nb.missing_key


class TestLoadsNotebook:
    """Tests for loads_notebook function."""

    def test_load_valid_notebook(self):
        nb = loads_notebook(SAMPLE_NOTEBOOK_JSON)
        assert isinstance(nb, NotebookDict)
        assert len(nb.cells) == 3
        assert nb.cells[0]["cell_type"] == "markdown"
        assert nb.cells[1]["cell_type"] == "code"

    def test_load_invalid_json(self):
        with pytest.raises(ValueError, match="Invalid notebook JSON"):
            loads_notebook("not valid json")


class TestExtractCells:
    """Tests for extract_cells function."""

    def test_extract_all_cells(self):
        nb = loads_notebook(SAMPLE_NOTEBOOK_JSON)
        cells = extract_cells(nb)
        assert len(cells) == 3
        assert cells[0].cell_type == "markdown"
        assert cells[1].cell_type == "code"
        assert cells[2].cell_type == "markdown"

    def test_extract_only_code_cells(self):
        nb = loads_notebook(SAMPLE_NOTEBOOK_JSON)
        cells = extract_cells(nb, cell_type="code")
        assert len(cells) == 1
        assert cells[0].cell_type == "code"

    def test_extract_only_markdown_cells(self):
        nb = loads_notebook(SAMPLE_NOTEBOOK_JSON)
        cells = extract_cells(nb, cell_type="markdown")
        assert len(cells) == 2
        assert all(c.cell_type == "markdown" for c in cells)

    def test_cell_has_output(self):
        nb = loads_notebook(SAMPLE_NOTEBOOK_JSON)
        cells = extract_cells(nb)
        assert cells[0].has_output is False  # markdown
        assert cells[1].has_output is True  # code with output
        assert cells[2].has_output is False  # markdown

    def test_source_concatenation(self):
        nb = loads_notebook(SAMPLE_NOTEBOOK_JSON)
        cells = extract_cells(nb)
        assert cells[0].source == "# Test Notebook\n\nThis is a test."
        assert cells[1].source == "print('hello world')"


class TestNotebookToText:
    """Tests for notebook_to_text function."""

    def test_convert_to_text(self):
        nb = loads_notebook(SAMPLE_NOTEBOOK_JSON)
        text = notebook_to_text(nb)
        assert "# Test Notebook" in text
        assert "print('hello world')" in text
        assert "## Section 2" in text

    def test_convert_only_code_cells(self):
        nb = loads_notebook(SAMPLE_NOTEBOOK_JSON)
        text = notebook_to_text(nb, cell_type="code")
        assert "print('hello world')" in text
        assert "# Test Notebook" not in text

    def test_custom_separator(self):
        nb = loads_notebook(SAMPLE_NOTEBOOK_JSON)
        text = notebook_to_text(nb, separator="|||")
        assert "|||" in text


class TestNotebookToMarkdown:
    """Tests for notebook_to_markdown function."""

    def test_convert_notebook_dict_to_markdown(self):
        nb = loads_notebook(SAMPLE_NOTEBOOK_JSON)
        md = notebook_to_markdown(nb)
        assert "Test Notebook" in md
        assert "print" in md or "hello world" in md

    def test_loads_notebook_to_markdown(self):
        md = loads_notebook_to_markdown(SAMPLE_NOTEBOOK_JSON)
        assert "Test Notebook" in md
        assert isinstance(md, str)

    def test_clear_output_false(self):
        # With output preserved
        md = loads_notebook_to_markdown(SAMPLE_NOTEBOOK_JSON, clear_output=False)
        assert isinstance(md, str)


class TestLoadNotebook:
    """Tests for load_notebook function."""

    def test_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="Notebook not found"):
            load_notebook(tmp_path / "nonexistent.ipynb")

    def test_invalid_json(self, tmp_path):
        nb_file = tmp_path / "invalid.ipynb"
        nb_file.write_text("not valid json")
        with pytest.raises(ValueError, match="Invalid notebook JSON"):
            load_notebook(nb_file)

    def test_load_valid_notebook(self, tmp_path):
        nb_file = tmp_path / "test.ipynb"
        nb_file.write_text(SAMPLE_NOTEBOOK_JSON)
        nb = load_notebook(nb_file)
        assert isinstance(nb, NotebookDict)
        assert len(nb.cells) == 3
