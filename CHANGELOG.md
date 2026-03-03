# Changelog

All notable changes to this project are documented in this file.

The format is based on Keep a Changelog and this project uses Semantic Versioning.

## [Unreleased]

### Added

- Open source community and governance baseline (`CONTRIBUTING`, `CODE_OF_CONDUCT`, issue/PR templates, `SECURITY`, `CODEOWNERS`)
- Repository maintenance and quality automation configs (`Makefile`, Dependabot, pre-commit, coverage/lint configs)
- Repo-level architecture and FAQ documentation

## [0.1.0]

### Added

- Initial dual implementation structure:
  - `file-organiser-python` (Typer)
  - `file-organiser-go` (Cobra)
- Core commands: `rename`, `separate`, `merge`, `revert`
- CI and release workflows
