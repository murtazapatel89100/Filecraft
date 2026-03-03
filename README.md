# organizer-cli
File Organiser is a structured command-line tool for automating file management tasks such as separating files by extension, sequential renaming, and safely reverting file moves.

## Implementations

- [file-organiser-python](file-organiser-python): Python implementation using Typer.
- [file-organiser-go](file-organiser-go): Go implementation using Cobra.

Both implementations support:

- `rename`: sequential renaming with collision-safe file names
- `separate`: organize files by extension, date, extension+date, or file type
- `merge`: merge from multiple source directories with the same modes
- `revert`: restore moved files from saved history

Each implementation has its own README with install, usage examples, and command options.

## Quick Start

### Python CLI

```bash
cd file-organiser-python
poetry install --with dev --sync
poetry run organizer --help
```

### Go CLI

```bash
cd file-organiser-go
go run . --help
```

## Example Commands

Python:

```bash
poetry run organizer separate --mode extension --extension pdf --working-dir ./in --target-dir ./out --history
poetry run organizer merge --mode file --working-dir ./downloads --working-dir ./desktop --target-dir ./merged
poetry run organizer revert --directory ./out
```

Go:

```bash
go run . separate --mode extension --extension pdf --working-dir ./in --target-dir ./out --history
go run . merge --mode file --working-dir ./downloads --working-dir ./desktop --target-dir ./merged
go run . revert --directory ./out
```

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the detailed architecture diagram.

```mermaid
flowchart LR
	CLI_PY[Python CLI (Typer)] --> CORE[Organizer logic]
	CLI_GO[Go CLI (Cobra)] --> CORE
	CORE --> FS[Filesystem operations]
	CORE --> HIST[History files (.organizer_history_*.json)]
	CI[CI workflow] --> CLI_PY
	CI --> CLI_GO
	REL[Release workflow] --> BIN[Versioned release binaries]
```

## Release Process

- See [docs/RELEASES.md](docs/RELEASES.md) for versioning, release commands, and workflow rules.

## Open Source Project Files

- Governance and community docs: `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `CODEOWNERS`
- Collaboration templates: `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/*`
- Maintenance and quality: `CHANGELOG.md`, `ROADMAP.md`, `Makefile`, `.github/dependabot.yml`, `.pre-commit-config.yaml`
- Full checklist status: [OPEN_SOURCE_CHECKLIST.md](OPEN_SOURCE_CHECKLIST.md)

## FAQ

### Why keep both Python and Go implementations?

To provide the same CLI behavior across two ecosystems while comparing developer and runtime tradeoffs.

### Which version value is canonical for releases?

The release version must match across git tag (without `v`), `VERSION`, and `file-organiser-python/pyproject.toml`.

### Where should command behavior changes be implemented?

In both implementations unless explicitly scoped otherwise.
