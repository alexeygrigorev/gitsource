"""Integration test to verify fixtures can be fetched from the actual repo."""

import pytest

from gitsource import GithubRepositoryDataReader, notebook_processor


def only_fixtures(filepath):
    """Filter to only get fixtures folder."""
    return filepath.startswith("fixtures/")


@pytest.mark.integration
class TestLiveRepo:
    """Tests against the live gitsource repository."""

    def test_fetch_fixtures_from_gitsource_repo(self):
        """Test that we can fetch actual fixtures from the gitsource repo."""
        reader = GithubRepositoryDataReader(
            repo_owner="alexeygrigorev",
            repo_name="gitsource",
            branch="master",
            allowed_extensions={"md", "ipynb"},
            filename_filter=only_fixtures,
            processors={"ipynb": notebook_processor},
        )

        files = reader.read()

        # Verify we got the fixtures we expect
        filenames = {f.filename for f in files}
        assert "fixtures/sample.md" in filenames
        assert "fixtures/sample.ipynb" in filenames

        # Check markdown content
        md_file = next(f for f in files if f.filename == "fixtures/sample.md")
        assert "Sample Document" in md_file.content
        assert "---" in md_file.content  # frontmatter

        # Check notebook was processed (not JSON, but text)
        nb_file = next(f for f in files if f.filename == "fixtures/sample.ipynb")
        assert "# Sample Notebook" in nb_file.content
        assert "print(" in nb_file.content  # code cell
        assert "{\n" not in nb_file.content  # Not JSON anymore
        assert '"cells"' not in nb_file.content  # Not JSON anymore
