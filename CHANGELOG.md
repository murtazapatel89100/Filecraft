## [unreleased]

### ⚙️ Miscellaneous Tasks

- Fix malformed version in makefile
## [0.2.0] - 2026-03-04

### 🚀 Features

- Add --file-type filter for separate mode file in Go and Python
- Add makefile command for releasing new versions

### 📚 Documentation

- Expand README and add project governance/maintenance files

### ⚙️ Miscellaneous Tasks

- *(release)* Add manual workflow_dispatch trigger
- Fix yml formatiing
- Fix architecture diagram error
- Release v0.2.0
## [0.1.0] - 2026-03-02

### 🚀 Features

- Implement file renaming with numeric prefixes and history tracking
- Add file extension constants and separate method placeholder
- Add separation logic and update FileOrganizer
- Add date separation functionality and placeholders for future features
- Implement full CLI functionality for rename, separate, and revert
- Add merge command to organize files from multiple source directories

### 🐛 Bug Fixes

- Adjust Python version and dependencies
- Update Python version constraints for dependency compatibility
- *(python)* Make Windows-safe output and unique history filenames

### 🎨 Styling

- Format Python code with black

### ⚙️ Miscellaneous Tasks

- Remove unused history logic
- Add release automation, copilot guide, and upgrade Cobra to v1.10.2
- Init CI/release workflows and version tracking
- Normalize line endings across platforms
- Remove windows conflicting terminal commads
