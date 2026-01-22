"""
GitHub repository data fetching module.

This module provides functionality to download and extract files from GitHub
repositories without requiring git to be installed.

Features:
- Processor registry for per-extension content transformation
- Callback hooks for before/after file processing (e.g., caching)
- Built-in notebook processor for .ipynb files
"""

import io
import zipfile
import traceback
from dataclasses import dataclass
from typing import Callable, Iterable

import requests


@dataclass
class RawRepositoryFile:
    """Dataclass representing a file from a GitHub repository.

    Attributes:
        filename: The path/filename of the file within the repository
        content: The text content of the file
    """
    filename: str
    content: str


# Type aliases for clarity
Processor = Callable[[str, str], str]  # (content, filename) -> processed_content
BeforeProcessCallback = Callable[[str, str], bool | None]  # (filename, filepath) -> skip?
AfterProcessCallback = Callable[[RawRepositoryFile], None]  # (file) -> None


def notebook_processor(content: str, filename: str) -> str:
    """Convert Jupyter notebook JSON to markdown.

    Uses the built-in notebook parser - no external dependencies required.

    Args:
        content: Raw notebook JSON string
        filename: The notebook filename

    Returns:
        Markdown representation of the notebook with code and markdown cells
    """
    try:
        from .notebook import loads_notebook, notebook_to_text

        nb = loads_notebook(content)
        # Convert to plain text with markdown and code cells
        return notebook_to_text(nb, cell_type=None, separator="\n\n")
    except Exception:
        # If parsing fails, return raw content
        return content


class GithubRepositoryDataReader:
    """Downloads and parses files from a GitHub repository.

    Uses codeload.github.com to fetch repository archives without requiring git.

    Example:
        from gitsource import GithubRepositoryDataReader, notebook_processor

        reader = GithubRepositoryDataReader(
            repo_owner="alexeygrigorev",
            repo_name="gitsource",
            allowed_extensions={"md", "ipynb"},
            processors={"ipynb": notebook_processor},
        )
        files = reader.read()
    """

    def __init__(
        self,
        repo_owner: str,
        repo_name: str,
        allowed_extensions: Iterable[str] | None = None,
        filename_filter: Callable[[str], bool] | None = None,
        branch: str = "main",
        processors: dict[str, Processor] | None = None,
        before_process: BeforeProcessCallback | None = None,
        after_process: AfterProcessCallback | None = None,
    ) -> None:
        """Initialize the GitHub repository data reader.

        Args:
            repo_owner: The owner/organization of the GitHub repository
            repo_name: The name of the GitHub repository
            allowed_extensions: Optional set of file extensions to include
                (e.g., {"md", "py"}). If not provided, all file types are included
            filename_filter: Optional callable to filter files by their path
            branch: The git branch to fetch (default: "main")
            processors: Optional dict mapping file extensions to processor functions.
                Processors take (content, filename) and return processed content.
                Available processors: notebook_processor (for .ipynb files)
            before_process: Optional callback called before processing each file.
                Receives (filename, filepath). Return False to skip the file.
            after_process: Optional callback called after processing each file.
                Receives the RawRepositoryFile. Useful for caching, logging, etc.
        """
        prefix = "https://codeload.github.com"
        self.url = f"{prefix}/{repo_owner}/{repo_name}/zip/refs/heads/{branch}"

        if allowed_extensions is not None:
            self.allowed_extensions = {ext.lower() for ext in allowed_extensions}
        else:
            self.allowed_extensions = None

        self.filename_filter = filename_filter or (lambda filepath: True)

        self.processors = processors or {}
        self.before_process = before_process
        self.after_process = after_process

    def read(self) -> list[RawRepositoryFile]:
        """Download and extract files from the GitHub repository.

        Returns:
            List of RawRepositoryFile objects for each processed file

        Raises:
            Exception: If the repository download fails
        """
        resp = requests.get(self.url)
        if resp.status_code != 200:
            raise Exception(f"Failed to download repository: {resp.status_code}")

        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        repository_data = self._extract_files(zf)
        zf.close()

        return repository_data

    def _extract_files(self, zf: zipfile.ZipFile) -> list[RawRepositoryFile]:
        """Extract and process files from the zip archive.

        Args:
            zf: ZipFile object containing the repository data

        Returns:
            List of RawRepositoryFile objects for each processed file
        """
        data = []

        for file_info in zf.infolist():
            filepath = self._normalize_filepath(file_info.filename)

            if self._should_skip_file(filepath):
                continue

            # Call before_process callback - return False to skip
            if self.before_process:
                try:
                    result = self.before_process(file_info.filename, filepath)
                    if result is False:
                        continue
                except Exception as e:
                    print(f"Error in before_process for {filepath}: {e}")
                    traceback.print_exc()
                    continue

            try:
                with zf.open(file_info) as f_in:
                    content = f_in.read().decode("utf-8", errors="ignore")
                    content = content.strip() if content else None

                    if content is not None:
                        # Apply processor if registered for this extension
                        ext = self._get_extension(filepath)
                        if ext in self.processors:
                            processor = self.processors[ext]
                            try:
                                content = processor(content, filepath)
                            except Exception as e:
                                print(f"Error processing {filepath} with {processor.__name__}: {e}")
                                traceback.print_exc()
                                continue

                        file = RawRepositoryFile(
                            filename=filepath,
                            content=content,
                        )
                        data.append(file)

                        # Call after_process callback
                        if self.after_process:
                            try:
                                self.after_process(file)
                            except Exception as e:
                                print(f"Error in after_process for {filepath}: {e}")
                                traceback.print_exc()

            except Exception as e:
                print(f"Error processing {file_info.filename}: {e}")
                traceback.print_exc()
                continue

        return data

    def _should_skip_file(self, filepath: str) -> bool:
        """Determine whether a file should be skipped during processing.

        Args:
            filepath: The file path to check

        Returns:
            True if the file should be skipped, False otherwise
        """
        filepath = filepath.lower()

        # Skip directories
        if filepath.endswith("/"):
            return True

        # Skip hidden files
        filename = filepath.split("/")[-1]
        if filename.startswith("."):
            return True

        # Filter by extension
        if self.allowed_extensions:
            ext = self._get_extension(filepath)
            if ext not in self.allowed_extensions:
                return True

        # Apply custom filter
        if not self.filename_filter(filepath):
            return True

        return False

    def _get_extension(self, filepath: str) -> str:
        """Extract the file extension from a filepath.

        Args:
            filepath: The file path to extract extension from

        Returns:
            The file extension (without dot) or empty string if no extension
        """
        filename = filepath.lower().split("/")[-1]
        if "." in filename:
            return filename.rsplit(".", maxsplit=1)[-1]
        return ""

    def _normalize_filepath(self, filepath: str) -> str:
        """Removes the top-level directory from the file path inside the zip archive.

        'repo-main/path/to/file.py' -> 'path/to/file.py'

        Args:
            filepath: The original filepath from the zip archive

        Returns:
            The normalized filepath with top-level directory removed
        """
        parts = filepath.split("/", maxsplit=1)
        return parts[1] if len(parts) > 1 else parts[0]
