from pathlib import Path
import json
from typing import Dict, Optional


def save_history(
    history_path: Path,
    revert_map: Dict[str, str],
    operation: str = "rename",
) -> None:
    data = {
        "operation": operation,
        "mappings": revert_map,
    }

    with open(history_path, "w") as f:
        json.dump(data, f, indent=4)


def load_latest_history(directory: Path) -> Path | None:
    history_files = list(directory.glob(".organizer_history_*.json"))

    if not history_files:
        return None

    return max(history_files, key=lambda f: f.stat().st_mtime)


def read_history(history_path: Path) -> Dict[str, str]:
    with open(history_path, "r") as f:
        data = json.load(f)

    return data.get("mappings", {})


def delete_history(history_path: Path) -> None:
    if history_path.exists():
        history_path.unlink()


def revert_hostory():
    pass
