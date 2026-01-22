# gitsource

GitHub repository reader with document chunking for RAG/LLM applications.

## Features

- Download repositories directly from GitHub using `codeload.github.com` (no git required)
- Filter files by extension and path patterns
- Parse frontmatter from markdown files
- Chunk documents using sliding windows (preserves metadata)
- Lightweight Jupyter notebook parser

## Installation

```bash
pip install gitsource
```

## Usage

### Read GitHub Repository

```python
from gitsource import GithubRepositoryDataReader

reader = GithubRepositoryDataReader(
    repo_owner="evidentlyai",
    repo_name="docs",
    allowed_extensions={"md", "mdx"},
)

files = reader.read()
```

### Chunk Documents

```python
from gitsource import chunk_documents

documents = [
    {"content": "Long text here...", "filename": "doc.txt"}
]

chunks = chunk_documents(
    documents,
    size=2000,
    step=1000
)
```

### Parse Jupyter Notebooks

```python
from gitsource import load_notebook

notebook = load_notebook("notebook.ipynb")
cells = notebook.cells  # List of cell dictionaries
```

## License

WTFPL
