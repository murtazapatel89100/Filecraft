# Contributing

Thanks for helping improve `Filecraft`.

This repository contains the Python implementation (`filecraft-python`, Typer) of the Filecraft CLI.

## Ground Rules

- Keep changes focused and small.
- Add or update tests for behavior changes.
- Do not add ad-hoc CI dependency installs outside the package managers already used (`poetry`).

## Development Setup

### Python

```bash
cd filecraft-python
poetry install --with dev --sync
poetry run black --check src tests
poetry run python -m unittest discover -s tests -p "test_*.py"
poetry build
```



## Pull Request Expectations

- Include a clear description of the problem and fix.
- Ensure CI passes before requesting review.

## Versioning and Releases

- Release tags must be semantic (`vX.Y.Z`).
- Version must match across:
  - git tag (without `v`)
  - `VERSION`
  - `filecraft-python/pyproject.toml`
- See `docs/RELEASES.md` for the exact process.

## Reporting Issues

Please use GitHub Issues with:

- steps to reproduce
- expected vs actual behavior
- OS and shell
- command used
- relevant logs or error output
