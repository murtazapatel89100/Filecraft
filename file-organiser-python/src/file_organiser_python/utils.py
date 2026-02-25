from pathlib import Path
from typing import List


def validate_directory(path: Path) -> None:
    """
    Ensure the given path exists and is a directory.
    """
    if not path.exists():
        raise ValueError(f"Directory does not exist: {path}")

    if not path.is_dir():
        raise ValueError(f"Path is not a directory: {path}")


def list_files(directory: Path) -> List[Path]:
    """
    Return all files (not directories) inside a directory.
    """
    return [item for item in directory.iterdir() if item.is_file()]


def get_extension(file: Path) -> str:
    """
    Return the normalized file extension (without dot, lowercase).
    Example: '.PDF' -> 'pdf'
    """
    return file.suffix.lower().lstrip(".")


def filter_by_extension(files: List[Path], extension: str) -> List[Path]:
    """
    Filter files by a specific extension.
    """
    extension = extension.lower().lstrip(".")
    return [file for file in files if get_extension(file) == extension]


def ensure_directory(path: Path, dry_run: bool = False) -> None:
    """
    Create directory if it does not exist.
    """
    if not path.exists():
        if dry_run:
            print(f"[DRY RUN] Would create directory: {path}")
        else:
            path.mkdir(parents=True, exist_ok=True)


def perform_action(message: str, dry_run: bool) -> None:
    """
    Print action message.
    If dry_run is True, prefix with DRY RUN.
    """
    if dry_run:
        print(f"[DRY RUN] {message}")
    else:
        print(message)
