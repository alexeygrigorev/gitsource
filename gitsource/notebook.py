"""
Lightweight Jupyter notebook parser and converter.

This module provides fast notebook loading using JSON directly and
markdown conversion using nbconvert.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class NotebookDict(dict):
    """A dict subclass that provides attribute access for notebook data.

    This allows code like notebook.cells to work alongside notebook["cells"].
    """

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._wrap_nested()

    def _wrap_nested(self) -> None:
        """Recursively wrap nested dicts and lists."""
        if "cells" in self and isinstance(self["cells"], list):
            self["cells"] = [
                NotebookDict(cell) if isinstance(cell, dict) else cell
                for cell in self["cells"]
            ]

        if "metadata" in self and isinstance(self["metadata"], dict):
            self["metadata"] = NotebookDict(self["metadata"])

    def __getattr__(self, key: str) -> Any:
        try:
            return self[key]
        except KeyError:
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{key}'"
            )

    def __setattr__(self, key: str, value: Any) -> None:
        self[key] = value


@dataclass
class CellInfo:
    """Information about a notebook cell."""

    cell_type: str  # 'code' or 'markdown'
    source: str  # Source code as string
    cell_index: int  # Index in the notebook
    has_output: bool = False  # Whether cell has output (code cells only)


def load_notebook(path: str | Path) -> NotebookDict:
    """Load a Jupyter notebook from a file using JSON.

    Args:
        path: Path to the .ipynb file

    Returns:
        NotebookDict (dict with attribute access) representing the notebook

    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the file is not a valid notebook
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Notebook not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return NotebookDict(data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid notebook JSON: {e}") from e


def loads_notebook(content: str) -> NotebookDict:
    """Load a Jupyter notebook from a JSON string.

    Args:
        content: JSON string representation of a notebook

    Returns:
        NotebookDict (dict with attribute access) representing the notebook

    Raises:
        ValueError: If the content is not a valid notebook
    """
    try:
        data = json.loads(content)
        return NotebookDict(data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid notebook JSON: {e}") from e


def extract_cells(
    notebook: NotebookDict,
    cell_type: str | None = None,
    include_source: bool = True,
) -> list[CellInfo]:
    """Extract cells from a notebook.

    Args:
        notebook: The notebook dictionary
        cell_type: Filter by cell type ('code', 'markdown', or None for all)
        include_source: Whether to include the source content

    Returns:
        List of CellInfo objects
    """
    cells = []

    for idx, cell in enumerate(notebook.get("cells", [])):
        ct = cell.get("cell_type", "")

        if cell_type and ct != cell_type:
            continue

        source_obj = cell.get("source", "")
        if isinstance(source_obj, str):
            source = source_obj
        else:
            source = "".join(source_obj)

        has_output = False
        if ct == "code":
            outputs = cell.get("outputs", [])
            has_output = bool(outputs)

        if not include_source:
            source = ""

        cells.append(
            CellInfo(
                cell_type=ct,
                source=source,
                cell_index=idx,
                has_output=has_output,
            )
        )

    return cells


def notebook_to_text(
    notebook: NotebookDict,
    cell_type: str | None = None,
    separator: str = "\n\n---\n\n",
) -> str:
    """Convert a notebook to plain text.

    Args:
        notebook: The notebook dictionary
        cell_type: Filter by cell type ('code', 'markdown', or None for all)
        separator: String to insert between cells

    Returns:
        String representation of the notebook
    """
    cells = extract_cells(notebook, cell_type=cell_type, include_source=True)
    return separator.join(cell.source for cell in cells)


def _convert_notebook_dict(obj: Any) -> Any:
    """Recursively convert NotebookDict to regular dict.

    This is needed for nbformat.from_dict which doesn't handle dict subclasses.

    Args:
        obj: The object to convert (NotebookDict, dict, list, or other)

    Returns:
        A regular dict/list with all NotebookDict instances converted
    """
    if isinstance(obj, NotebookDict):
        return {k: _convert_notebook_dict(v) for k, v in obj.items()}
    elif isinstance(obj, dict):
        return {k: _convert_notebook_dict(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_notebook_dict(item) for item in obj]
    else:
        return obj


def notebook_to_markdown(
    notebook_path: str | Path | NotebookDict,
    clear_output: bool = True,
) -> str:
    """Convert a Jupyter notebook to markdown using nbconvert.

    This requires nbformat and nbconvert to be installed.

    Args:
        notebook_path: Path to the .ipynb file, or a NotebookDict
        clear_output: If True, remove cell outputs from the markdown

    Returns:
        Markdown string representation of the notebook

    Raises:
        ImportError: If nbformat or nbconvert are not installed
        FileNotFoundError: If the file doesn't exist
    """
    try:
        import nbformat
        from nbconvert import MarkdownExporter
        from nbconvert.preprocessors import ClearOutputPreprocessor
    except ImportError as e:
        raise ImportError(
            "nbconvert and nbformat are required for notebook_to_markdown. "
            "Install them with: pip install nbconvert nbformat"
        ) from e

    if isinstance(notebook_path, NotebookDict):
        # Convert NotebookDict to JSON string and use nbformat.reads
        # This ensures proper handling of source lists
        import json
        json_str = json.dumps(_convert_notebook_dict(notebook_path))
        nb_node = nbformat.reads(json_str, as_version=nbformat.NO_CONVERT)
    elif isinstance(notebook_path, (str, Path)):
        path = Path(notebook_path)
        if not path.exists():
            raise FileNotFoundError(f"Notebook not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        nb_node = nbformat.reads(content, as_version=nbformat.NO_CONVERT)
    else:
        raise TypeError(
            f"notebook_path must be str, Path, or NotebookDict, got {type(notebook_path)}"
        )

    exporter = MarkdownExporter()
    if clear_output:
        exporter.register_preprocessor(ClearOutputPreprocessor(), enabled=True)

    md_body, _ = exporter.from_notebook_node(nb_node)
    return md_body


def loads_notebook_to_markdown(content: str, clear_output: bool = True) -> str:
    """Convert a notebook JSON string to markdown.

    Args:
        content: JSON string representation of a notebook
        clear_output: If True, remove cell outputs from the markdown

    Returns:
        Markdown string representation of the notebook
    """
    notebook = loads_notebook(content)
    return notebook_to_markdown(notebook, clear_output=clear_output)
