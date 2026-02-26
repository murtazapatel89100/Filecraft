from pathlib import Path

from file_organiser_python.utils import ensure_directory
from file_organiser_python.history import save_history
from datetime import date


def SeparateByExtension(
    extension: str,
    target_dir: Path,
    working_dir: Path,
    history: bool,
    history_path: Path,
    dry_run: bool,
) -> None:
    print(f"Separating by extension: {extension} in {working_dir} → {target_dir}")

    sorted_dir = target_dir / extension.upper()

    print(f"Ensuring directory exists: {sorted_dir}...")

    ensure_directory(sorted_dir, dry_run=dry_run)

    revert_map: dict[str, str] = {working_dir.name: sorted_dir.name}
    operation = "separate_by_extension"

    files = [
        f
        for f in working_dir.iterdir()
        if f.is_file() and f.suffix.lower() == extension.lower()
    ]
    if not files:
        print(f"No files with extension '{extension}' found in {working_dir}.")
        return

    for f in files:
        new_path = sorted_dir / f.name
        if dry_run:
            print(f"[DRY RUN] Would move {f.name} → {new_path}...")
            continue

        print(f"Moving {f.name} → {new_path}...")
        f.rename(new_path)
        revert_map[f.name] = str(f.resolve())

    if history and not dry_run:
        if not history_path:
            print("Failed to validate History path, cannot save history.")
            return

        save_history(
            history_path=history_path, revert_map=revert_map, operation=operation
        )


def SeperateByDate(
    date: str,
    target_dir: Path,
    working_dir: Path,
    history: bool,
    history_path: Path,
    dry_run: bool,
) -> None:
    pass
