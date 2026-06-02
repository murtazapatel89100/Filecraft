# Filecraft

![Filecraft Banner](https://raw.githubusercontent.com/murtazapatel89100/Filecraft/main/assets/Filecraft-banner.png)

Filecraft is a cross-language CLI suite for automating file management tasks such as sequential renaming, separation by rule, merging from multiple directories, and safe revert via history.

## Implementations

- [filecraft-python](filecraft-python): Python implementation (PyPI target).

Both implementations support:

- `rename`: sequential renaming with collision-safe file names
- `separate`: organize files by extension, date, extension+date, or file type
- `merge`: merge from multiple source directories with the same modes
- `revert`: restore moved files from saved history

Each implementation has its own README with install, usage examples, and command options.

## Distribution

- `filecraft-cli` (Python): published on PyPI.

## Quick Start

### Python CLI

```bash
cd filecraft-python
poetry install --with dev --sync
poetry run filecraft --help
```

## Example Commands

Python:

```bash
poetry run filecraft rename --working-dir ./downloads --target-dir ./renamed --rename-with invoice
poetry run filecraft separate --mode extension --extension pdf --working-dir ./in --target-dir ./out --history
poetry run filecraft merge --mode file --working-dir ./downloads --working-dir ./desktop --target-dir ./merged
poetry run filecraft revert --directory ./out
```

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the detailed architecture diagram.

```mermaid
flowchart LR
  CLI_PY["Filecraft (Python / Typer)"] --> CORE["Organizer logic"]
  CORE --> FS["Filesystem operations"]
  CORE --> HIST["History files (.organizer_history_*.json)"]
  CI["CI workflow"] --> CLI_PY
  REL["Release workflow"] --> BIN["Versioned Filecraft artifacts"]
```

## Release Process

- See [docs/RELEASES.md](docs/RELEASES.md) for versioning, release commands, and workflow rules.

## Open Source Project Files

- Governance and community docs: `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `CODEOWNERS`
- Collaboration templates: `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/*`
- Maintenance and quality: `CHANGELOG.md`, `ROADMAP.md`, `Makefile`, `.github/dependabot.yml`, `.pre-commit-config.yaml`
- Full checklist status: [OPEN_SOURCE_CHECKLIST.md](OPEN_SOURCE_CHECKLIST.md)

### Where are releases published?

- `filecraft-cli` package: PyPI

### Which version value is canonical for releases?

The release version must match across git tag (without `v`), `VERSION`, and `filecraft-python/pyproject.toml`.
