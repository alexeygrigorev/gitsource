"""Tests for RawRepositoryFile.parse() method."""

import pytest

from gitsource.github import RawRepositoryFile


class TestRawRepositoryFileParse:
    """Tests for RawRepositoryFile.parse() method."""

    def test_parse_frontmatter(self):
        """Test parsing YAML frontmatter from markdown files."""
        file1 = RawRepositoryFile(
            filename="doc1.md",
            content='---\ntitle: "Test"\nauthor: "John"\n---\n\nContent here',
        )
        file2 = RawRepositoryFile(
            filename="doc2.md",
            content='---\ntags: [python, test]\n---\n\nAnother document',
        )

        result1 = file1.parse()
        result2 = file2.parse()

        assert result1["filename"] == "doc1.md"
        assert result1["title"] == "Test"
        assert result1["author"] == "John"
        assert result1["content"] == "Content here"

        assert result2["filename"] == "doc2.md"
        assert result2["tags"] == ["python", "test"]
        assert result2["content"] == "Another document"

    def test_parse_no_frontmatter(self):
        """Test parsing files without frontmatter."""
        file = RawRepositoryFile(
            filename="doc.md",
            content="Just plain content without frontmatter",
        )

        result = file.parse()

        assert result["filename"] == "doc.md"
        assert result["content"] == "Just plain content without frontmatter"

    def test_parse_multiline_frontmatter(self):
        """Test parsing multiline frontmatter values."""
        file = RawRepositoryFile(
            filename="doc.md",
            content='---\ndescription: >\n  This is a\n  multiline description\n---\n\nContent',
        )

        result = file.parse()

        assert result["filename"] == "doc.md"
        assert "multiline description" in result["description"]

    def test_parse_list_comprehension(self):
        """Test parsing multiple files using list comprehension."""
        files = [
            RawRepositoryFile(
                filename="doc1.md",
                content='---\ntitle: "First"\n---\n\nContent 1',
            ),
            RawRepositoryFile(
                filename="doc2.md",
                content='---\ntitle: "Second"\n---\n\nContent 2',
            ),
        ]

        parsed = [f.parse() for f in files]

        assert len(parsed) == 2
        assert parsed[0]["title"] == "First"
        assert parsed[1]["title"] == "Second"
