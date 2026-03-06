# Releases Guide

This repository has two CLI implementations under the Filecraft app:

- Python implementation (Typer, PyPI distribution as `filecraft-cli`)
- Go implementation (Cobra, GitHub Releases binary as `Filecraft`)

Releases are automated with GitHub Actions and are triggered by either:

- pushing a semantic version tag
- manually dispatching the workflow with a version input

## Release Trigger Rules

Release workflow: `.github/workflows/release.yml`

A release runs only when:

- Trigger source is one of:
  - push tag matching `v*` (for example `v1.2.3`), or
  - manual dispatch input `version` (for example `1.2.3` or `v1.2.3`)
- The resolved release version is valid semver (`vMAJOR.MINOR.PATCH`, optional pre-release/build suffix)
- The resolved version (without `v`) matches both:
  - root `VERSION` file
  - `filecraft-python/pyproject.toml` `version`

If any check fails, release is stopped.

## What the Release Workflow Produces

For each valid version:

- Builds `Filecraft` Python CLI executable using `PyInstaller`
- Builds Python package artifacts (`sdist` + `wheel`) once for PyPI and GitHub Release assets
- Publishes to PyPI via Trusted Publishing (OIDC)
- Builds `Filecraft` Go binaries for:
  - Linux amd64
  - macOS amd64
  - Windows amd64 (`.exe`)
- Uploads artifacts
- Publishes a GitHub Release
- Auto-generates release notes (`generate_release_notes: true`)

## Standard Release Process (Do This Every Time)

### Prerequisites

- `git-cliff` must be installed before running `make release` (used to generate `CHANGELOG.md`).

Install example:

```bash
cargo install git-cliff --locked
```

### 1) Update versions

Update both files to the same version number (without `v`):

- `VERSION`
- `filecraft-python/pyproject.toml` → `version = "x.y.z"`

Example (`1.2.0`):

```bash
printf "1.2.0\n" > VERSION
sed -i 's/^version = ".*"/version = "1.2.0"/' filecraft-python/pyproject.toml
```

### 2) Run checks locally

```bash
# Python
cd filecraft-python
poetry install --with dev
poetry run black --check src tests
poetry run python -m unittest discover -s tests -p "test_*.py"
cd ..

# Go
cd filecraft-go
gofmt -w .
go vet ./...
go test ./...
cd ..
```

### 3) Commit version change

```bash
git add VERSION filecraft-python/pyproject.toml
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

### 5) Configure PyPI Trusted Publisher (one-time)

For `filecraft-cli`, add a PyPI Trusted Publisher that matches:

- Owner: `murtazapatel89100`
- Repository: `Filecraft`
- Workflow filename: `release.yml`

## How Not to Break the Pattern

- Do not push release tags without first updating `VERSION` and Python `pyproject.toml` version.
- Keep semver format strict (`vX.Y.Z` preferred for normal releases).
- Never edit workflow artifact names in one job without updating downstream download/publish steps.
- Keep release artifacts deterministic:
  - Python binary includes version and platform
  - Go binaries include version and target platform
- If release fails at validation, fix versions and push a new correct tag.

## CI vs Release

- `ci.yml` runs on push/PR to `main`: lint, tests, build for both Python and Go.
- `release.yml` runs on valid version tag push or manual workflow dispatch: builds release artifacts and publishes GitHub Release.
