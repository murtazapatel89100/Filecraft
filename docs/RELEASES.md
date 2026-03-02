# Releases Guide

This repository has two CLI implementations:

- `file-organiser-python` (Typer)
- `file-organiser-go` (Cobra)

Releases are automated with GitHub Actions and are triggered by either:

- pushing a semantic version tag
- manually dispatching the workflow with a version input

## Release Trigger Rules

Release workflow: `.github/workflows/release.yml`

A release runs only when:

1. Trigger source is one of:
  - push tag matching `v*` (for example `v1.2.3`), or
  - manual dispatch input `version` (for example `1.2.3` or `v1.2.3`)
2. The resolved release version is valid semver (`vMAJOR.MINOR.PATCH`, optional pre-release/build suffix)
3. The resolved version (without `v`) matches both:
   - root `VERSION` file
   - `file-organiser-python/pyproject.toml` `version`

If any check fails, release is stopped.

## What the Release Workflow Produces

For each valid version:

- Builds Python CLI executable using `PyInstaller`
- Builds Go CLI binaries for:
  - Linux amd64
  - macOS amd64
  - Windows amd64 (`.exe`)
- Uploads artifacts
- Publishes a GitHub Release
- Auto-generates release notes (`generate_release_notes: true`)

## Standard Release Process (Do This Every Time)

### 1) Update versions

Update both files to the same version number (without `v`):

- `VERSION`
- `file-organiser-python/pyproject.toml` → `version = "x.y.z"`

Example (`1.2.0`):

```bash
printf "1.2.0\n" > VERSION
sed -i 's/^version = ".*"/version = "1.2.0"/' file-organiser-python/pyproject.toml
```

### 2) Run checks locally

```bash
# Python
cd file-organiser-python
poetry install --with dev
poetry run black --check src tests
poetry run python -m unittest discover -s tests -p "test_*.py"
cd ..

# Go
cd file-organiser-go
gofmt -w .
go vet ./...
go test ./...
cd ..
```

### 3) Commit version change

```bash
git add VERSION file-organiser-python/pyproject.toml
git commit -m "chore(release): bump version to v1.2.0"
git push origin main
```

### 4) Trigger the release

Option A (recommended): create and push release tag

```bash
git tag v1.2.0
git push origin v1.2.0
```

Option B: run workflow manually from GitHub Actions UI

- Workflow: `Release`
- Input `version`: `1.2.0` or `v1.2.0`

Either option triggers the release workflow.

## How Not to Break the Pattern

- Do not push release tags without first updating `VERSION` and Python `pyproject.toml` version.
- Keep semver format strict (`vX.Y.Z` preferred for normal releases).
- Never edit workflow artifact names in one job without updating downstream download/publish steps.
- Keep release artifacts deterministic:
  - Python binary name includes version and platform
  - Go binaries include version and target platform
- If release fails at validation, fix versions and push a new correct tag.

## CI vs Release

- `ci.yml` runs on push/PR to `main`: lint, tests, build for both Python and Go.
- `release.yml` runs on valid version tag push or manual workflow dispatch: builds release artifacts and publishes GitHub Release.
