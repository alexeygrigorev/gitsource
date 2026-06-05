.PHONY: test setup shell coverage publish-build release publish-clean

test:
	uv run pytest

coverage:
	uv run pytest --cov=gitsource --cov-report=term-missing --cov-report=html

setup:
	uv sync --dev

shell:
	uv shell

publish-build:
	uv run hatch build

# Release: tag the current version and push to trigger CI publish.
# CI workflow: .github/workflows/publish.yml (on tag push v*)
release:
	@VERSION=$$(grep -E "^__version__" gitsource/__version__.py | sed -E "s/.*['\"]([^'\"]+)['\"].*/\1/"); \
	echo "Releasing v$$VERSION"; \
	git tag "v$$VERSION"; \
	git push origin "v$$VERSION"

publish-clean:
	rm -r dist/
