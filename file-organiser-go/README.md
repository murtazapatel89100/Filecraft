# File Organiser CLI (Go)

Go implementation of the file organiser CLI using Cobra. It mirrors the Python version's behavior: rename files, separate files by mode, merge from multiple directories, and revert using history.

## Requirements

- Go `>=1.22`

## Install / Run

### Run directly

```bash
go run . --help
```

### Build binary

```bash
go build -o organizer .
./organizer --help
```

## Commands

- `organizer rename`
- `organizer separate`
- `organizer merge`
- `organizer revert`

All commands support `--dry-run` to preview actions without moving files.
Working directory flags are validated before any `--target-dir` creation prompt.

## `rename`

Renames files in `working_dir` to numeric names (`1.ext`, `2.ext`, ...) and moves them to `target_dir`.

### Options

- `--working-dir PATH` (default: current directory)
- `--target-dir PATH` (default: current directory)
- `--dry-run`
- `--history` (save history file for revert)

If `--target-dir` is provided and does not exist, the CLI prompts to create it (`y/n`).
Declining exits with a `--target-dir` error.

### Example

```bash
go run . rename --working-dir ./downloads --target-dir ./renamed --history
```

## `separate`

Separates files according to mode.

### Modes

- `extension`: Move files of a specific extension (e.g. `.pdf`) into `TARGET/PDF`
- `date`: Move files modified on a specific date (or today) into `TARGET/YYYY-MM-DD`
- `extension_and_date`: Combine both filters into `TARGET/YYYY-MM-DD/EXT`
- `file`: Sort all files by file type category (`IMAGES`, `VIDEOS`, `DOCUMENTS`, `ARCHIVES`, etc.)

### Options

- `--mode [extension|date|extension_and_date|file]` (default: `extension`)
- `--extension TEXT` (required for `extension` and `extension_and_date`)
- `--file-type TEXT` (optional for `file`; accepts category like `documents` or extension like `pdf`)
- `--date YYYY-MM-DD` (used by `date` and `extension_and_date`; validated)
- `--working-dir PATH` (default: current directory)
- `--target-dir PATH` (default: current directory)
- `--dry-run`
- `--history`

### Examples

```bash
go run . separate --mode extension --extension pdf --working-dir ./in --target-dir ./out
go run . separate --mode date --date 2026-03-01 --working-dir ./in --target-dir ./out
go run . separate --mode extension_and_date --extension .jpg --date 2026-03-01 --working-dir ./in --target-dir ./out
go run . separate --mode file --working-dir ./in --target-dir ./out
go run . separate --mode file --file-type pdf --working-dir ./in --target-dir ./out
```

## `merge`

Merges files from multiple `working_dir` locations into a single `target_dir`.

### Modes

- `extension`: Merge files of a specific extension into `TARGET/EXT`
- `date`: Merge files modified on a specific date (or today) into `TARGET/YYYY-MM-DD`
- `extension_and_date`: Combine both filters into `TARGET/YYYY-MM-DD/EXT`
- `file`: Merge all files by file type category (`IMAGES`, `VIDEOS`, `DOCUMENTS`, `ARCHIVES`, etc.)

### Options

- `--mode [extension|date|extension_and_date|file]` (default: `extension`)
- `--extension TEXT` (required for `extension` and `extension_and_date`)
- `--date YYYY-MM-DD` (used by `date` and `extension_and_date`; validated)
- `--working-dir PATH` (required, repeat for multiple source directories)
- `--target-dir PATH` (default: current directory)
- `--dry-run`
- `--history`

### Examples

```bash
go run . merge --mode extension --extension pdf --working-dir ./downloads --working-dir ./desktop --target-dir ./merged
go run . merge --mode date --date 2026-03-01 --working-dir ./in1 --working-dir ./in2 --target-dir ./merged
go run . merge --mode extension_and_date --extension .jpg --date 2026-03-01 --working-dir ./camera --working-dir ./phone --target-dir ./merged
go run . merge --mode file --working-dir ./in1 --working-dir ./in2 --target-dir ./merged
```

## `revert`

Reverts moves using a history file.

### Options

- `--directory PATH` (searches latest history in that directory; default: current directory)
- `--history-file PATH` (use a specific history file)
- `--dry-run`
- `--keep-history` (do not delete history file after successful revert)

### Examples

```bash
go run . revert --directory ./out
go run . revert --history-file ./out/.organizer_history_2026-03-01_12-00-00-123456.json
```

## Tests

```bash
go test ./...
```

## Notes

- History files are saved with a timestamped name like `.organizer_history_YYYY-MM-DD_HH-MM-SS-ffffff.json`.
- File collisions are handled safely by appending suffixes like `_1`, `_2`, etc.
- Compound extensions such as `.tar.gz` are recognized when sorting by file type.
