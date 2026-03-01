from pathlib import Path
import json
from typing import Dict, Optional

from file_organiser_python.utils import build_non_conflicting_path


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
    with open(history_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("mappings", {})


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
            print(f"No history file found in {directory}")
            return 0

    with open(history_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    mappings: Dict[str, str] = data.get("mappings", {})
    if not mappings:
        print(f"No mappings found in history file: {history_path}")
        return 0

    reverted_count = 0
    for current, original in mappings.items():
        current_path = Path(current)
        original_path = Path(original)

        if not current_path.exists():
            continue

        if dry_run:
            print(f"[DRY RUN] Would move {current_path} → {original_path}")
            reverted_count += 1
            continue

        original_path.parent.mkdir(parents=True, exist_ok=True)
        destination_path = build_non_conflicting_path(original_path)
        current_path.rename(destination_path)
        reverted_count += 1

    if reverted_count and delete_after_revert and not dry_run:
        delete_history(history_path)

    return reverted_count
