from pathlib import Path
from typing import Optional

from file_organiser_python.utils import (
    ensure_directory,
    build_non_conflicting_path,
    get_extension,
)
from file_organiser_python.history import save_history
from file_organiser_python.constants import (
    IMAGE_EXTENSIONS,
    DOCUMENT_EXTENSIONS,
    SPREADSHEET_EXTENSIONS,
    PRESENTATION_EXTENSIONS,
    VIDEO_EXTENSIONS,
    AUDIO_EXTENSIONS,
    ARCHIVE_EXTENSIONS,
    EXECUTABLE_EXTENSIONS,
    CODE_EXTENSIONS,
    FONT_EXTENSIONS,
    DISK_IMAGE_EXTENSIONS,
)

from datetime import date, datetime


EXTENSION_TYPE_MAP: dict[str, str] = {}

for ext in IMAGE_EXTENSIONS:
    EXTENSION_TYPE_MAP[ext] = "IMAGES"
for ext in VIDEO_EXTENSIONS:
    EXTENSION_TYPE_MAP[ext] = "VIDEOS"
for ext in AUDIO_EXTENSIONS:
    EXTENSION_TYPE_MAP[ext] = "AUDIO"
for ext in DOCUMENT_EXTENSIONS:
    EXTENSION_TYPE_MAP[ext] = "DOCUMENTS"
for ext in SPREADSHEET_EXTENSIONS:
    EXTENSION_TYPE_MAP[ext] = "SPREADSHEETS"
for ext in PRESENTATION_EXTENSIONS:
    EXTENSION_TYPE_MAP[ext] = "PRESENTATIONS"
for ext in ARCHIVE_EXTENSIONS:
    EXTENSION_TYPE_MAP[ext] = "ARCHIVES"
for ext in EXECUTABLE_EXTENSIONS:
    EXTENSION_TYPE_MAP[ext] = "EXECUTABLES"
for ext in CODE_EXTENSIONS:
    EXTENSION_TYPE_MAP[ext] = "CODE"
for ext in FONT_EXTENSIONS:
    EXTENSION_TYPE_MAP[ext] = "FONTS"
for ext in DISK_IMAGE_EXTENSIONS:
    EXTENSION_TYPE_MAP[ext] = "DISK_IMAGES"

KNOWN_EXTENSIONS = set(EXTENSION_TYPE_MAP.keys())


def SeparateByExtension(
    extension: str,
    target_dir: Path,
    working_dir: Path,
    history_path: Optional[Path],
    history: bool = False,
    dry_run: bool = False,
) -> None:
    print(f"Separating by extension: {extension} in {working_dir} → {target_dir}")

    normalized_extension = extension.lower()
    sorted_dir = target_dir / normalized_extension.lstrip(".").upper()

    print(f"Ensuring directory exists: {sorted_dir}...")

    ensure_directory(sorted_dir, dry_run=dry_run)

    revert_map: dict[str, str] = {}
    operation = "separate_by_extension"

    files = [
        f
        for f in working_dir.iterdir()
        if f.is_file() and get_extension(f, KNOWN_EXTENSIONS) == normalized_extension
    ]
    if not files:
        print(f"No files with extension '{extension}' found in {working_dir}.")
        return

    for f in files:
        destination_path = sorted_dir / f.name
        new_path = build_non_conflicting_path(destination_path)
        original_path = f.resolve()
        if dry_run:
            print(f"[DRY RUN] Would move {f.name} → {new_path}...")
            continue

        print(f"Moving {f.name} → {new_path}...")
        f.rename(new_path)
        revert_map[str(new_path.resolve())] = str(original_path)

    if history and not dry_run:
        if not history_path:
            print("Failed to validate History path, cannot save history.")
            return

        save_history(
            history_path=history_path, revert_map=revert_map, operation=operation
        )


def SeparateByDate(
    sort_date: Optional[str],
    target_dir: Path,
    working_dir: Path,
    history: bool,
    history_path: Optional[Path],
    dry_run: bool,
) -> None:
    if sort_date:
        print(
            f"Seperating files modified on {sort_date} in {working_dir} → {target_dir}"
        )
    else:
        print(f"Seperating files modified today in {working_dir} → {target_dir}")

    sorted_dir = target_dir / (sort_date if sort_date else date.today().isoformat())

    print(f"Ensuring directory exists: {sorted_dir}...")

    ensure_directory(sorted_dir, dry_run=dry_run)

    revert_map: dict[str, str] = {}
    operation = "separate_by_date"

    target_date = date.fromisoformat(sort_date) if sort_date else date.today()
    files = [
        f
        for f in working_dir.iterdir()
        if f.is_file()
        and datetime.fromtimestamp(f.stat().st_mtime).date() == target_date
    ]

    if not files:
        print(
            f"No files modified on {sort_date if sort_date else 'today'} found in {working_dir}."
        )
        return

    for f in files:
        destination_path = sorted_dir / f.name
        new_path = build_non_conflicting_path(destination_path)
        original_path = f.resolve()
        if dry_run:
            print(f"[DRY RUN] Would move {f.name} → {new_path}...")
            continue

        print(f"Moving {f.name} → {new_path}...")
        f.rename(new_path)
        revert_map[str(new_path.resolve())] = str(original_path)

    if history and not dry_run:
        if not history_path:
            print("Failed to validate History path, cannot save history.")
            return

        save_history(
            history_path=history_path, revert_map=revert_map, operation=operation
        )


def SeparateByExtensionAndDate(
    sort_date: Optional[str],
    extension: str,
    target_dir: Path,
    working_dir: Path,
    history: bool = False,
    history_path: Optional[Path] = None,
    dry_run: bool = False,
) -> None:
    normalized_extension = extension.lower()
    selected_date = date.fromisoformat(sort_date) if sort_date else date.today()
    date_folder_name = selected_date.isoformat()

    print(
        f"Separating by extension and date: {extension}, {date_folder_name} in {working_dir} → {target_dir}"
    )

    sorted_dir = (
        target_dir / date_folder_name / normalized_extension.lstrip(".").upper()
    )
    print(f"Ensuring directory exists: {sorted_dir}...")
    ensure_directory(sorted_dir, dry_run=dry_run)

    files = [
        f
        for f in working_dir.iterdir()
        if f.is_file()
        and get_extension(f, KNOWN_EXTENSIONS) == normalized_extension
        and datetime.fromtimestamp(f.stat().st_mtime).date() == selected_date
    ]

    if not files:
        print(
            f"No files with extension '{extension}' modified on {date_folder_name} found in {working_dir}."
        )
        return

    revert_map: dict[str, str] = {}
    operation = "separate_by_extension_and_date"

    for f in files:
        destination_path = sorted_dir / f.name
        new_path = build_non_conflicting_path(destination_path)
        original_path = f.resolve()

        if dry_run:
            print(f"[DRY RUN] Would move {f.name} → {new_path}...")
            continue

        print(f"Moving {f.name} → {new_path}...")
        f.rename(new_path)
        revert_map[str(new_path.resolve())] = str(original_path)

    if history and not dry_run:
        if not history_path:
            print("Failed to validate History path, cannot save history.")
            return

        save_history(
            history_path=history_path,
            revert_map=revert_map,
            operation=operation,
        )


def SeparateByFileType(
    target_dir: Path,
    working_dir: Path,
    history: bool = False,
    history_path: Optional[Path] = None,
    dry_run: bool = False,
) -> None:
    print(f"Separating all files by file type in {working_dir} → {target_dir}")

    files = [f for f in working_dir.iterdir() if f.is_file()]
    if not files:
        print(f"No files found in {working_dir}.")
        return

    revert_map: dict[str, str] = {}
    operation = "separate_by_file_type"

    for f in files:
        extension = get_extension(f, KNOWN_EXTENSIONS)
        folder_name = EXTENSION_TYPE_MAP.get(extension, "OTHERS")
        sorted_dir = target_dir / folder_name

        ensure_directory(sorted_dir, dry_run=dry_run)

        destination_path = sorted_dir / f.name
        new_path = build_non_conflicting_path(destination_path)
        original_path = f.resolve()

        if dry_run:
            print(f"[DRY RUN] Would move {f.name} → {new_path}...")
            continue

        print(f"Moving {f.name} → {new_path}...")
        f.rename(new_path)
        revert_map[str(new_path.resolve())] = str(original_path)

    if history and not dry_run:
        if not history_path:
            print("Failed to validate History path, cannot save history.")
            return

        save_history(
            history_path=history_path,
            revert_map=revert_map,
            operation=operation,
        )


def SeperateByDate(
    sort_date: Optional[str],
    target_dir: Path,
    working_dir: Path,
    history: bool,
    history_path: Optional[Path],
    dry_run: bool,
) -> None:
    SeparateByDate(
        sort_date=sort_date,
        target_dir=target_dir,
        working_dir=working_dir,
        history=history,
        history_path=history_path,
        dry_run=dry_run,
    )


def SeperateByExtensionAndDate(
    sort_date: Optional[str],
    extension: str,
    target_dir: Path,
    working_dir: Path,
    history: bool = False,
    history_path: Optional[Path] = None,
    dry_run: bool = False,
) -> None:
    SeparateByExtensionAndDate(
        sort_date=sort_date,
        extension=extension,
        target_dir=target_dir,
        working_dir=working_dir,
        history=history,
        history_path=history_path,
        dry_run=dry_run,
    )
