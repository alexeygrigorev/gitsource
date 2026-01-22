"""Tests for the github module."""

import json
import pytest

from gitsource.github import (
    GithubRepositoryDataReader,
    notebook_processor,
    Processor,
    RawRepositoryFile,
)


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


class TestProcessorCallback:
    """Tests for processor and callback functionality."""

    def test_custom_processor(self, tmp_path):
        """Test that custom processors are applied."""
        # Create a mock zip file
        import zipfile
        import io

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("test-repo/test.txt", "hello world")
        zip_buffer.seek(0)

        reader = GithubRepositoryDataReader(
            repo_owner="test",
            repo_name="repo",
            processors={
                "txt": lambda content, filename: content.upper(),
            },
        )

        # Manually inject our test zip
        import requests
        original_get = requests.get

        class MockResponse:
            status_code = 200
            content = zip_buffer.getvalue()

        requests.get = lambda *args, **kwargs: MockResponse()

        try:
            files = reader.read()
            assert len(files) == 1
            assert files[0].content == "HELLO WORLD"
        finally:
            requests.get = original_get

    def test_before_process_skip(self, tmp_path):
        """Test that before_process can skip files."""
        import zipfile
        import io

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("test-repo/file1.txt", "content1")
            zf.writestr("test-repo/file2.txt", "content2")
        zip_buffer.seek(0)

        skip_files = set()

        def before_process(filename, filepath):
            if "file1" in filepath:
                skip_files.add(filepath)
                return False  # Skip this file
            return None

        reader = GithubRepositoryDataReader(
            repo_owner="test",
            repo_name="repo",
            before_process=before_process,
        )

        import requests
        original_get = requests.get

        class MockResponse:
            status_code = 200
            content = zip_buffer.getvalue()

        requests.get = lambda *args, **kwargs: MockResponse()

        try:
            files = reader.read()
            assert len(files) == 1
            assert files[0].filename == "file2.txt"
            assert "file1.txt" in skip_files
        finally:
            requests.get = original_get

    def test_after_process_callback(self, tmp_path):
        """Test that after_process is called for each file."""
        import zipfile
        import io

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("test-repo/file1.txt", "content1")
        zip_buffer.seek(0)

        processed_files = []

        def after_process(file: RawRepositoryFile):
            processed_files.append(file.filename)

        reader = GithubRepositoryDataReader(
            repo_owner="test",
            repo_name="repo",
            after_process=after_process,
        )

        import requests
        original_get = requests.get

        class MockResponse:
            status_code = 200
            content = zip_buffer.getvalue()

        requests.get = lambda *args, **kwargs: MockResponse()

        try:
            files = reader.read()
            assert len(processed_files) == 1
            assert "file1.txt" in processed_files[0]
        finally:
            requests.get = original_get


class TestNotebookProcessorIntegration:
    """Integration tests for notebook processing with GithubRepositoryDataReader."""

    def test_ipynb_files_processed_when_registered(self, tmp_path):
        """Test that .ipynb files are processed when notebook_processor is registered."""
        import zipfile
        import io

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("test-repo/notebook.ipynb", SAMPLE_NOTEBOOK_JSON)
        zip_buffer.seek(0)

        reader = GithubRepositoryDataReader(
            repo_owner="test",
            repo_name="repo",
            allowed_extensions={"ipynb"},
            processors={"ipynb": notebook_processor},
        )

        import requests
        original_get = requests.get

        class MockResponse:
            status_code = 200
            content = zip_buffer.getvalue()

        requests.get = lambda *args, **kwargs: MockResponse()

        try:
            files = reader.read()
            assert len(files) == 1
            # Content should be converted from notebook JSON to text
            assert "# Test Notebook" in files[0].content
            assert "print('hello')" in files[0].content
        finally:
            requests.get = original_get
