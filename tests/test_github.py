"""Tests for the github module."""

import json
import pytest
from contextlib import contextmanager

from gitsource.github import (
    GithubRepositoryDataReader,
    notebook_processor,
)


def _create_mock_zip(files: dict[str, str]) -> bytes:
    """Helper to create a mock zip file for testing.

    Note: Adds "test-repo/" prefix to all paths to simulate GitHub's
    codeload.zip structure which includes the repo name as top-level directory.
    """
    import zipfile
    import io

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        for path, content in files.items():
            zf.writestr(f"test-repo/{path}", content)
    zip_buffer.seek(0)
    return zip_buffer.getvalue()


@contextmanager
def _mock_github_zip(files: dict[str, str]):
    """Context manager to mock GitHub zip download.

    Usage:
        files = {"file.txt": "content"}
        with _mock_github_zip(files):
            reader = GithubRepositoryDataReader(...)
            files = reader.read()
    """
    import requests

    original_get = requests.get
    zip_content = _create_mock_zip(files)

    class MockResponse:
        status_code = 200
        content = zip_content

    requests.get = lambda *args, **kwargs: MockResponse()
    try:
        yield
    finally:
        requests.get = original_get


# Sample notebook JSON for testing
SAMPLE_NOTEBOOK_JSON = json.dumps({
    "cells": [
        {
            "cell_type": "markdown",
            "source": ["# Test Notebook\n"],
            "metadata": {},
        },
        {
            "cell_type": "code",
            "source": ["print('hello')"],
            "metadata": {},
            "outputs": [],
            "execution_count": None,
        },
    ],
    "metadata": {"language_info": {"name": "python"}},
    "nbformat": 4,
    "nbformat_minor": 2,
})


class TestNotebookProcessor:
    """Tests for notebook_processor function."""

    def test_converts_notebook_to_text(self):
        result = notebook_processor(SAMPLE_NOTEBOOK_JSON, "test.ipynb")
        assert "# Test Notebook" in result
        assert "print('hello')" in result

    def test_invalid_json_returns_raw(self):
        invalid = "not a json"
        result = notebook_processor(invalid, "test.ipynb")
        assert result == invalid


class TestProcessor:
    """Tests for processor functionality."""

    def test_custom_processor(self):
        """Test that custom processors are applied."""
        files = {"test.txt": "hello world"}
        with _mock_github_zip(files):
            reader = GithubRepositoryDataReader(
                repo_owner="test",
                repo_name="repo",
                processors={"txt": lambda content, filename: content.upper()},
            )
            files = reader.read()
            assert len(files) == 1
            assert files[0].content == "HELLO WORLD"


class TestNotebookProcessorIntegration:
    """Integration tests for notebook processing with GithubRepositoryDataReader."""

    def test_ipynb_files_processed_when_registered(self):
        """Test that .ipynb files are processed when notebook_processor is registered."""
        files = {"notebook.ipynb": SAMPLE_NOTEBOOK_JSON}
        with _mock_github_zip(files):
            reader = GithubRepositoryDataReader(
                repo_owner="test",
                repo_name="repo",
                allowed_extensions={"ipynb"},
                processors={"ipynb": notebook_processor},
            )
            files = reader.read()
            assert len(files) == 1
            # Content should be converted from notebook JSON to text
            assert "# Test Notebook" in files[0].content
            assert "print('hello')" in files[0].content


class TestUrlConstruction:
    """Tests for how the download URL is built."""

    def test_branch_default(self):
        """Without commit_id, the URL points at the branch ref."""
        reader = GithubRepositoryDataReader(repo_owner="test", repo_name="repo")
        assert reader.url == (
            "https://codeload.github.com/test/repo/zip/refs/heads/main"
        )

    def test_custom_branch(self):
        """A custom branch is reflected in the URL."""
        reader = GithubRepositoryDataReader(
            repo_owner="test", repo_name="repo", branch="master"
        )
        assert reader.url == (
            "https://codeload.github.com/test/repo/zip/refs/heads/master"
        )

    def test_commit_id_pins_revision(self):
        """commit_id builds a commit archive URL and ignores branch."""
        reader = GithubRepositoryDataReader(
            repo_owner="test",
            repo_name="repo",
            commit_id="8c1834d",
            branch="master",
        )
        assert reader.url == "https://codeload.github.com/test/repo/zip/8c1834d"


class TestFileFilters:
    """Tests for file filtering features."""

    def test_skip_hidden_default_includes_hidden(self):
        """Test that hidden files are included by default."""
        files = {"visible.txt": "visible", ".hidden.txt": "hidden"}
        with _mock_github_zip(files):
            reader = GithubRepositoryDataReader(repo_owner="test", repo_name="repo")
            files = reader.read()
            assert len(files) == 2
            filenames = {f.filename for f in files}
            assert "visible.txt" in filenames
            assert ".hidden.txt" in filenames

    def test_skip_hidden_true_excludes_hidden(self):
        """Test that skip_hidden=True excludes hidden files."""
        files = {"visible.txt": "visible", ".hidden.txt": "hidden"}
        with _mock_github_zip(files):
            reader = GithubRepositoryDataReader(
                repo_owner="test",
                repo_name="repo",
                skip_hidden=True,
            )
            files = reader.read()
            assert len(files) == 1
            assert files[0].filename == "visible.txt"

    def test_allowed_extensions_filters(self):
        """Test that allowed_extensions filters by extension."""
        files = {
            "file.txt": "text",
            "file.md": "markdown",
            "file.py": "python",
        }
        with _mock_github_zip(files):
            reader = GithubRepositoryDataReader(
                repo_owner="test",
                repo_name="repo",
                allowed_extensions={"txt", "md"},
            )
            files = reader.read()
            assert len(files) == 2
            filenames = {f.filename for f in files}
            assert "file.txt" in filenames
            assert "file.md" in filenames
            assert "file.py" not in filenames

    def test_filename_filter(self):
        """Test that filename_filter is applied."""
        files = {
            "dir1/file.txt": "file1",
            "dir2/file.txt": "file2",
            "dir3/file.txt": "file3",
        }
        with _mock_github_zip(files):
            reader = GithubRepositoryDataReader(
                repo_owner="test",
                repo_name="repo",
                filename_filter=lambda fp: fp.startswith("dir1/") or fp.startswith("dir2/"),
            )
            files = reader.read()
            assert len(files) == 2
            filenames = {f.filename for f in files}
            assert "dir1/file.txt" in filenames
            assert "dir2/file.txt" in filenames
            assert "dir3/file.txt" not in filenames

    def test_path_normalization(self):
        """Test that top-level repo directory is removed from paths."""
        files = {"some/nested/path/file.txt": "content"}
        with _mock_github_zip(files):
            reader = GithubRepositoryDataReader(repo_owner="test", repo_name="repo")
            files = reader.read()
            assert len(files) == 1
            # Top-level "test-repo/" should be removed, keeping the rest
            assert files[0].filename == "some/nested/path/file.txt"
