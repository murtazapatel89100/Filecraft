import json
from pathlib import Path
from typing import Dict, Optional

from file_organiser_python.utils import build_non_conflicting_path

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
)

console = Console()


def save_history(
    history_path: Path,
    revert_map: Dict[str, str],
    operation: str = "rename",
) -> None:
    data = {
        "operation": operation,
        "mappings": revert_map,
    }

    history_path.parent.mkdir(parents=True, exist_ok=True)
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def load_latest_history(directory: Path) -> Path | None:
    history_files = list(directory.glob(".organizer_history_*.json"))

    if not history_files:
        return None

    return max(history_files, key=lambda f: f.stat().st_mtime)


def read_history(history_path: Path) -> Dict[str, str]:
    try:
        with open(history_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Corrupted history file (invalid JSON): {history_path}"
        ) from exc

    if not isinstance(data, dict):
        raise ValueError(f"Invalid history file format: {history_path}")

    mappings = data.get("mappings", {})
    if not isinstance(mappings, dict):
        raise ValueError(f"Invalid mappings in history file: {history_path}")

    return mappings


def delete_history(history_path: Path) -> None:
    if history_path.exists():
        history_path.unlink()


def revert_history(
    history_path: Optional[Path] = None,
    directory: Optional[Path] = None,
    dry_run: bool = False,
    delete_after_revert: bool = True,
) -> int:
    if history_path is None:
        if directory is None:
            directory = Path.cwd()

        history_path = load_latest_history(directory)
        if history_path is None:
            console.print(f"[yellow]No history file found in {directory}[/yellow]")
            return 0

    try:
        mappings = read_history(history_path)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        return 0

    if not mappings:
        console.print(
            f"[yellow]No mappings found in history file: {history_path}[/yellow]"
        )
        return 0

    reverted_count = 0
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Reverting files...", total=len(mappings))
        for current, original in mappings.items():
            progress.advance(task)
            current_path = Path(current)
            original_path = Path(original)

            if not current_path.exists():
                continue

            if dry_run:
                console.print(
                    f"[dim][DRY RUN] Would move[/dim] {current_path.name} -> {original_path.name}"
                )
                reverted_count += 1
                continue

            original_path.parent.mkdir(parents=True, exist_ok=True)
            destination_path = build_non_conflicting_path(original_path)
            current_path.rename(destination_path)
            reverted_count += 1

    if reverted_count and delete_after_revert and not dry_run:
        delete_history(history_path)

    return reverted_count
