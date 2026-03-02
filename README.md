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

## Release Process

- See [docs/RELEASES.md](docs/RELEASES.md) for versioning, release commands, and workflow rules.
