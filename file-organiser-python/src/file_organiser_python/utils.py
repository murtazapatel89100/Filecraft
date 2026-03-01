from pathlib import Path
from typing import Iterable


def validate_directory(path: Path) -> None:
    """
    Ensure the given path exists and is a directory.
    """
    if not path.exists():
        raise ValueError(f"Directory does not exist: {path}")

    if not path.is_dir():
        raise ValueError(f"Path is not a directory: {path}")


def get_extension(file: Path, known_extensions: Iterable[str] | None = None) -> str:
    """
    Return normalized file extension in lowercase.
    Supports compound extensions (e.g. '.tar.gz') when provided in known_extensions.
    """
    file_name = file.name.lower()

    if known_extensions:
        matches = [
            ext.lower() for ext in known_extensions if file_name.endswith(ext.lower())
        ]
        if matches:
            return max(matches, key=len)

    return file.suffix.lower()


def ensure_directory(path: Path, dry_run: bool = False) -> None:
    """
    Create directory if it does not exist.
    """
    if not path.exists():
        if dry_run:
            print(f"[DRY RUN] Would create directory: {path}")
        else:
            path.mkdir(parents=True, exist_ok=True)


def build_non_conflicting_path(path: Path) -> Path:
    """
    Return a non-conflicting path by appending an incrementing suffix when needed.
    Example: file.txt -> file_1.txt
    """
    if not path.exists():
        return path

    counter = 1
    while True:
        candidate = path.with_name(f"{path.stem}_{counter}{path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1
