SHELL := /bin/bash

.PHONY: help ci python-install python-lint python-test python-build go-lint go-test go-build

help:
	@echo "Available targets:"
	@echo "  make ci            - Run Python + Go lint/test/build checks"
	@echo "  make python-install"
	@echo "  make python-lint"
	@echo "  make python-test"
	@echo "  make python-build"
	@echo "  make go-lint"
	@echo "  make go-test"
	@echo "  make go-build"

release:
	echo $(VERSION) > VERSION
	cd file-organiser-python && poetry version $(VERSION)
	git add VERSION file-organiser-python/pyproject.toml
	git commit -m "chore: release v$(VERSION)"
	git tag -a v$(VERSION) -m "Release v$(VERSION)"
	git push origin main
	git push origin v$(VERSION)

ci: python-lint python-test python-build go-lint go-test go-build

python-install:
	cd file-organiser-python && poetry install --with dev --sync

python-lint:
	cd file-organiser-python && poetry run black --check src tests

python-test:
	cd file-organiser-python && poetry run python -m unittest discover -s tests -p "test_*.py"

python-build:
	cd file-organiser-python && poetry build
	cd file-organiser-python && poetry run pyinstaller --onefile --name organizer-python --paths src src/file_organiser_python/main.py

go-lint:
	cd file-organiser-go && gofmt -w .
	cd file-organiser-go && go vet ./...

go-test:
	cd file-organiser-go && go test ./...

go-build:
	mkdir -p file-organiser-go/dist
	cd file-organiser-go && go build -o dist/organizer-go .
