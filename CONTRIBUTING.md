# Contributing

Thanks for helping improve `organizer-cli`.

This repository contains two implementations of the same CLI behavior:

- `file-organiser-python` (Typer)
- `file-organiser-go` (Cobra)

## Ground Rules

- Keep command behavior compatible across both implementations.
- Keep changes focused and small.
- Add or update tests for behavior changes.
- Do not add ad-hoc CI dependency installs outside the package managers already used (`poetry`, `go mod`).

## Development Setup

### Python

```bash
cd file-organiser-python
poetry install --with dev --sync
poetry run black --check src tests
poetry run python -m unittest discover -s tests -p "test_*.py"
poetry build
```

### Go

```bash
cd file-organiser-go
gofmt -w .
go vet ./...
go test ./...
go build -o dist/organizer-go .
```

## Pull Request Expectations

- Include a clear description of the problem and fix.
- Mention whether behavior changed in Python, Go, or both.
- If behavior changes in one implementation, either:
  - implement parity in the other implementation, or
  - explain why parity is intentionally deferred.
- Ensure CI passes before requesting review.

## Versioning and Releases

- Release tags must be semantic (`vX.Y.Z`).
- Version must match across:
  - git tag (without `v`)
  - `VERSION`
  - `file-organiser-python/pyproject.toml`
- See `docs/RELEASES.md` for the exact process.

## Reporting Issues

Please use GitHub Issues with:

- steps to reproduce
- expected vs actual behavior
- OS and shell
- command used
- relevant logs or error output
