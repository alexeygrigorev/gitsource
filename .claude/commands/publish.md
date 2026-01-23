# Publishing gitsource

## Prerequisites

- Hatch installed (`uv sync --dev` includes it)
- PyPI account configured
- TestPyPI account configured (optional)

## Steps

1. **Run tests**
   ```bash
   uv run pytest
   ```

2. **Update version** in `gitsource/__version__.py`

3. **Build and publish**
   ```bash
   make publish-build    # or: uv run hatch build
   make publish-test     # or: uv run hatch publish --repo test
   make publish          # or: uv run hatch publish
   ```

4. **Commit and push** to GitHub
   ```bash
   git add -A
   git commit -m "Bump version to X.Y.Z"
   git push
   ```

## Makefile

```makefile
publish-build:   # Build with hatch
publish-test:   # Publish to TestPyPI
publish:        # Publish to PyPI
publish-clean:  # Remove dist/
```

## After Publishing

- Verify on PyPI: https://pypi.org/project/gitsource/
- Verify on TestPyPI: https://test.pypi.org/project/gitsource/
