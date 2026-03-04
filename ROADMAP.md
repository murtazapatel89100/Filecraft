# Organizer CLI – Future Feature Roadmap

## File Discovery
- Recursive directory traversal
- Include pattern filtering (`--include`)
- Ignore pattern filtering (`--ignore`)
- File size filtering (`--min-size`, `--max-size`)
- Time filters (`--before`, `--after`, `--older-than`)
- Hidden file handling
- Depth limiting (`--max-depth`)

## Conflict Handling
- `--conflict rename` (current default)
- `--conflict overwrite`
- `--conflict skip`
- `--conflict fail`
- `--conflict prompt`

## File Type Detection
- MIME-type detection
- Smart file categorization
- Extension normalization
- File signature detection

## Sorting Enhancements
- Sort by file size
- Sort by creation time
- Sort by modification time
- Sort by filename patterns
- Sort by multiple conditions
- Custom folder naming templates

## Automation
- Watch mode (`organizer watch`)
- Scheduled execution support
- Continuous folder monitoring
- Rule-based automation

## Config System
- YAML config file support
- JSON config support
- Config validation
- Multiple config profiles
- Config override via CLI flags

## Rule Engine
- Multi-rule execution
- Conditional rules
- Rule priority system
- Rule chaining
- Rule preview

## Safety Features
- Operation confirmation prompt
- Protected directory detection
- Safe mode
- Max file operation limits
- Undo stack improvements
- Operation history viewer

## Output & UX
- Colored terminal output
- Progress bars
- Verbose mode
- Debug mode
- JSON output mode
- Quiet mode
- Operation summary improvements

## Performance
- Parallel file processing
- Batch file operations
- Optimized directory scanning
- Memory usage optimization
- Large directory handling

## Duplicate Handling
- Duplicate file detection
- Hash-based duplicate detection
- Duplicate removal
- Duplicate grouping
- Duplicate reporting

## CLI Improvements
- Shell autocompletion (bash/zsh/fish)
- Interactive mode
- Command aliases
- Better help formatting
- Command suggestions

## Logging
- File logging
- Structured logs
- Log levels
- Operation logs

## Integration
- Homebrew installation
- Scoop installation
- AUR package
- Docker image
- OS context menu integration

## Developer Features
- Plugin system
- Hook system
- Custom rule extensions
- External script execution
- API mode

## Reporting
- File operation reports
- Directory statistics
- File distribution reports
- Export reports (JSON/CSV)

## Long-term Features
- Remote directory support
- Cloud storage support
- GUI companion tool
- Web dashboard
- AI-assisted file categorization