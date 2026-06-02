SHELL := /bin/bash

.PHONY: help ci python-install python-lint python-test python-build hooks

help:
	@echo "Available targets:"
	@echo "  make ci            - Run Python lint/test/build checks"
	@echo "  make hooks         - Install git pre-commit and pre-push hooks"
	@echo "  make python-install"
	@echo "  make python-lint"
	@echo "  make python-test"
	@echo "  make python-build"

hooks:
	git config core.hooksPath .githooks
	@echo "Git hooks installed (using .githooks/ directory)."

release:
	@command -v git-cliff >/dev/null 2>&1 || { \
		echo "Error: git-cliff is required for make release."; \
		echo "Install with: cargo install git-cliff --locked"; \
		exit 1; \
	}
	echo $(VERSION) > VERSION
	cd filecraft-python && poetry version $(VERSION)
	git cliff -o CHANGELOG.md
	git add VERSION filecraft-python/pyproject.toml CHANGELOG.md
	git commit -m "chore: release v$(VERSION)"
	git tag -a v$(VERSION) -m "Release v$(VERSION)"
	git push origin main
	git push origin v$(VERSION)

ci: python-lint python-test python-build

python-install:
	cd filecraft-python && poetry install --with dev --sync

python-lint:
	cd filecraft-python && poetry run black --check src tests

python-test:
	cd filecraft-python && poetry run python -m unittest discover -s tests -p "test_*.py"

python-build:
	cd filecraft-python && poetry build
	cd filecraft-python && poetry run pyinstaller --onefile --name Filecraft --paths src src/file_organiser_python/main.py


