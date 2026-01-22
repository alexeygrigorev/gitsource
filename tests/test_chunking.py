"""Tests for the chunking module."""

import pytest

from gitsource.chunking import chunk_documents, sliding_window


class TestSlidingWindow:
    """Tests for sliding_window function."""

    def test_basic_chunking(self):
        result = sliding_window("hello world", size=5, step=3)
        assert len(result) == 4
        assert result[0] == {"start": 0, "content": "hello"}
        assert result[1] == {"start": 3, "content": "lo wo"}
        assert result[2] == {"start": 6, "content": "world"}
        assert result[3] == {"start": 9, "content": "ld"}

    def test_size_equals_length(self):
        result = sliding_window("hello", size=5, step=5)
        assert len(result) == 1
        assert result[0] == {"start": 0, "content": "hello"}

    def test_step_larger_than_size(self):
        result = sliding_window("hello world", size=3, step=10)
        assert len(result) == 2
        assert result[0] == {"start": 0, "content": "hel"}
        assert result[1] == {"start": 10, "content": "d"}

    def test_invalid_size(self):
        with pytest.raises(ValueError, match="size and step must be positive"):
            sliding_window("hello", size=0, step=2)

    def test_invalid_step(self):
        with pytest.raises(ValueError, match="size and step must be positive"):
            sliding_window("hello", size=2, step=0)

    def test_list_input(self):
        result = sliding_window([1, 2, 3, 4, 5], size=2, step=2)
        assert len(result) == 3
        assert result[0] == {"start": 0, "content": [1, 2]}
        assert result[1] == {"start": 2, "content": [3, 4]}
        assert result[2] == {"start": 4, "content": [5]}


class TestChunkDocuments:
    """Tests for chunk_documents function."""

    def test_basic_chunking(self):
        documents = [{"content": "a" * 100, "filename": "test.txt"}]
        result = chunk_documents(documents, size=30, step=20)
        assert len(result) == 5
        # Check metadata is preserved
        assert all(chunk["filename"] == "test.txt" for chunk in result)
        # Check start positions
        assert result[0]["start"] == 0
        assert result[1]["start"] == 20
        assert result[2]["start"] == 40

    def test_multiple_documents(self):
        documents = [
            {"content": "abc" * 10, "filename": "file1.txt"},
            {"content": "xyz" * 10, "filename": "file2.txt"},
        ]
        result = chunk_documents(documents, size=15, step=10)
        assert len(result) == 6
        # First 3 chunks from file1
        assert result[0]["filename"] == "file1.txt"
        assert result[2]["filename"] == "file1.txt"
        # Next 3 chunks from file2
        assert result[3]["filename"] == "file2.txt"
        assert result[5]["filename"] == "file2.txt"

    def test_custom_content_field(self):
        documents = [{"text": "a" * 50, "filename": "test.txt"}]
        result = chunk_documents(documents, size=20, step=10, content_field_name="text")
        assert len(result) == 5
        # 'text' should be removed, 'content' added
        assert "text" not in result[0]
        assert "content" in result[0]

    def test_preserves_metadata(self):
        documents = [
            {
                "content": "a" * 50,
                "filename": "test.txt",
                "title": "Test",
                "date": "2024-01-01",
            }
        ]
        result = chunk_documents(documents, size=20, step=10)
        assert len(result) == 5
        for chunk in result:
            assert chunk["filename"] == "test.txt"
            assert chunk["title"] == "Test"
            assert chunk["date"] == "2024-01-01"

    def test_empty_documents(self):
        result = chunk_documents([], size=20, step=10)
        assert result == []
