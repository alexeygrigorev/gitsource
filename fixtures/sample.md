---
title: "Sample Document"
author: "Test Author"
tags: ["test", "sample"]
---

# Sample Document

This is a sample markdown file for testing the gitsource library.

## Features

- Fetch files from GitHub
- Parse frontmatter
- Chunk documents

## Code Example

```python
from gitsource import GithubRepositoryDataReader, notebook_processor

reader = GithubRepositoryDataReader(
    repo_owner="alexeygrigorev",
    repo_name="gitsource",
    allowed_extensions={"md", "ipynb"},
    processors={"ipynb": notebook_processor},
)

files = reader.read()
```
