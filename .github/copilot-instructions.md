# Copilot Guide for Filecraft

This repository contains two CLI implementations of the same Filecraft behavior:

- `filecraft-python` (Typer + Poetry)
- `filecraft-go` (Cobra + Go modules)

Use this guide when making changes so behavior stays aligned across both implementations.

## Repository Layout

- `filecraft-python/`
  - `src/file_organiser_python/`: Filecraft Python CLI and core logic
  - `tests/`: Python test suite (`unittest`)
  - `pyproject.toml`: single source of truth for Python dependencies/build metadata
- `filecraft-go/`
  - `cmd/`: Cobra commands
  - `internal/organizer/`: Go organizer logic
  - `go.mod`: Go dependencies and toolchain version
- `.github/workflows/`
  - `ci.yml`: lint/test/build on push and PR
  - `release.yml`: tag-driven release automation
- `VERSION`: canonical repo version (without `v` prefix)
- `docs/RELEASES.md`: release process and guardrails
- `.githooks/`: git hook scripts (pre-commit for lint, pre-push for tests)

## Non-Negotiable Rules

1. Keep Python and Go command behavior compatible.
2. Do not add ad-hoc dependencies in CI workflows.

- Python dependencies must be managed only via `filecraft-python/pyproject.toml`.

3. Release pipeline runs only on semantic version tags (`v*`).
4. Release version must match all three:
   - tag without `v`
   - `VERSION`

- `filecraft-python/pyproject.toml` version

## Local Dev Commands

### Initial Setup

```bash
make hooks
```

### Python

```bash
cd filecraft-python
poetry install --with dev --sync
poetry run black --check src tests
poetry run python -m unittest discover -s tests -p "test_*.py"
poetry build
poetry run pyinstaller --onefile --name Filecraft --paths src src/file_organiser_python/main.py
```

### Go

```bash
cd filecraft-go
gofmt -w .
go vet ./...
go test ./...
go build -o dist/Filecraft .
```

## CI/Release Expectations

### CI (`.github/workflows/ci.yml`)

- Runs on push/PR to `main`.
- Matrix builds on:
  - `ubuntu-latest`
  - `macos-latest`
  - `windows-latest`
- Executes lint, tests, and build for both Python and Go.
- Uploads CI artifacts for each OS.

### Release (`.github/workflows/release.yml`)

- Trigger: pushing a semantic tag like `v1.2.3`.
- Validates tag/version consistency.
- Builds OS-specific binaries on native runner matrices for Python and Go.
- Publishes release artifacts and auto-generated release notes.

## Change Checklist (Before Opening PR)

- [ ] Python + Go logic parity maintained.
- [ ] `pyproject.toml` and `go.mod` updated when dependencies change.
- [ ] `README.md`/`docs/RELEASES.md` updated if workflow or command behavior changed.
- [ ] Local lint/tests/build passed for affected implementation(s).
- [ ] No workflow step installs Python packages outside Poetry.

## Version Bump Workflow

```bash
# Example: release 1.2.0
printf "1.2.0\n" > VERSION
# update filecraft-python/pyproject.toml version = "1.2.0"

git add VERSION file-organiser-python/pyproject.toml
git commit -m "chore(release): bump version to v1.2.0"
git push origin main

git tag v1.2.0
git push origin v1.2.0
```

The tag push triggers the release workflow automatically.
