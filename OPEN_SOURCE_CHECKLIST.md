# Open Source Repository Checklist (Tailored)

This checklist is applied to `Filecraft` as of 2026-03-03.

## 🔥 Minimum Required

- [x] `README.md`
- [x] `LICENSE`
- [x] `.gitignore`
- [x] `CONTRIBUTING.md`

## ✅ Community & Collaboration

- [x] `CODE_OF_CONDUCT.md`
- [x] `.github/PULL_REQUEST_TEMPLATE.md`
- [x] `.github/ISSUE_TEMPLATE/bug_report.yml`
- [x] `.github/ISSUE_TEMPLATE/feature_request.yml`
- [x] `SECURITY.md`
- [x] `CODEOWNERS`

## 🚀 Project Management & Maintenance

- [x] `CHANGELOG.md`
- [x] `ROADMAP.md`
- [x] `Makefile`
- [x] CI workflow (`.github/workflows/ci.yml`)
- [x] Dependabot config (`.github/dependabot.yml`)

## 🧪 Testing & Quality

- [x] Tests directories (`filecraft-python/tests`, Go tests in `filecraft-go`) for `Filecraft-python` and `Filecraft-go`
- [x] Coverage config (`.coveragerc`)
- [x] Lint config (`.golangci.yml`, Black config usage in `pyproject.toml`)
- [x] Pre-commit config (`.pre-commit-config.yaml`)

## 📦 Packaging (CLI)

- [x] Versioning strategy documented (`docs/RELEASES.md`)
- [x] Installation instructions (`README.md` + implementation READMEs)
- [x] Example usage commands (`README.md` + implementation READMEs)
- [x] Binary release workflow (`.github/workflows/release.yml`)

## 🌟 Nice to Have

- [x] Architecture diagram (`docs/ARCHITECTURE.md`)
- [x] FAQ section (`README.md`)
- [ ] Good First Issues label *(GitHub repo setting/labels, not a file)*
- [ ] Discussions enabled *(GitHub repo setting, not a file)*

## Remaining Manual GitHub Setup

1. Create label: `good first issue`
2. Enable GitHub Discussions in repository settings
