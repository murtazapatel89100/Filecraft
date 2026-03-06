import os
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
KNOWN_FILE_TYPES = set(EXTENSION_TYPE_MAP.values()) | {"OTHERS"}


def _normalize_file_type(file_type: Optional[str]) -> Optional[tuple[str, str]]:
    if not file_type:
        return None

    normalized_value = file_type.strip().lower()
    if not normalized_value:
        return None

    normalized_extension = f".{normalized_value.lstrip('.')}"
    if normalized_extension in KNOWN_EXTENSIONS:
        return ("extension", normalized_extension)

    normalized_type = normalized_value.upper().replace("-", "_").replace(" ", "_")
    if normalized_type in KNOWN_FILE_TYPES:
        return ("category", normalized_type)

    return ("invalid", "")


def _files_from_working_dirs(
    working_dirs: list[Path],
    recursive: bool = False,
    excluded_dirs: Optional[list[Path]] = None,
) -> list[Path]:
    def _is_relative_to(path: Path, parent: Path) -> bool:
        try:
            path.relative_to(parent)
            return True
        except ValueError:
            return False

    def _is_excluded_path(path: Path, exclusions: list[Path]) -> bool:
        return any(_is_relative_to(path, excluded) for excluded in exclusions)

    def _normalized_roots(paths: list[Path]) -> list[Path]:
        resolved = sorted(
            {path.resolve() for path in paths},
            key=lambda path: (len(path.parts), str(path)),
        )
        roots: list[Path] = []
        for candidate in resolved:
            if any(_is_relative_to(candidate, root) for root in roots):
                continue
            roots.append(candidate)
        return roots

    normalized_exclusions = [path.resolve() for path in excluded_dirs or []]

    files: list[Path] = []
    for working_dir in _normalized_roots(working_dirs):
        effective_exclusions = [
            excluded for excluded in normalized_exclusions if excluded != working_dir
        ]

        if _is_excluded_path(working_dir, effective_exclusions):
            continue

        if recursive:
            for root, dirs, filenames in os.walk(working_dir, topdown=True):
                root_path = Path(root)

                dirs[:] = [
                    dir_name
                    for dir_name in dirs
                    if not _is_excluded_path(root_path / dir_name, effective_exclusions)
                ]

                files.extend(
                    candidate
                    for candidate in (root_path / file_name for file_name in filenames)
                    if candidate.is_file()
                )
        else:
            files.extend(
                [
                    f
                    for f in working_dir.iterdir()
                    if f.is_file() and not _is_excluded_path(f, effective_exclusions)
                ]
            )
    return files


def SeparateByExtension(
    extension: str,
    target_dir: Path,
    working_dir: Path,
    recursive: bool,
    history_path: Optional[Path],
    history: bool = False,
    dry_run: bool = False,
) -> None:
    print(f"Separating by extension: {extension} in {working_dir} -> {target_dir}")

    normalized_extension = extension.lower()
    sorted_dir = target_dir / normalized_extension.lstrip(".").upper()

    print(f"Ensuring directory exists: {sorted_dir}...")

    ensure_directory(sorted_dir, dry_run=dry_run)

    revert_map: dict[str, str] = {}
    operation = "separate_by_extension"

    files = [
        f
        for f in _files_from_working_dirs(
            [working_dir], recursive=recursive, excluded_dirs=[target_dir]
        )
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
            print(f"[DRY RUN] Would move {f.name} -> {new_path}...")
            continue

        print(f"Moving {f.name} -> {new_path}...")
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
    recursive: bool,
    history: bool,
    history_path: Optional[Path],
    dry_run: bool,
) -> None:
    if sort_date:
        print(
            f"Seperating files modified on {sort_date} in {working_dir} -> {target_dir}"
        )
    else:
        print(f"Seperating files modified today in {working_dir} -> {target_dir}")

    sorted_dir = target_dir / (sort_date if sort_date else date.today().isoformat())

    print(f"Ensuring directory exists: {sorted_dir}...")

    ensure_directory(sorted_dir, dry_run=dry_run)

    revert_map: dict[str, str] = {}
    operation = "separate_by_date"

    target_date = date.fromisoformat(sort_date) if sort_date else date.today()
    files = [
        f
        for f in _files_from_working_dirs(
            [working_dir], recursive=recursive, excluded_dirs=[target_dir]
        )
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
            print(f"[DRY RUN] Would move {f.name} -> {new_path}...")
            continue

        print(f"Moving {f.name} -> {new_path}...")
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
    recursive: bool,
    history: bool = False,
    history_path: Optional[Path] = None,
    dry_run: bool = False,
) -> None:
    normalized_extension = extension.lower()
    selected_date = date.fromisoformat(sort_date) if sort_date else date.today()
    date_folder_name = selected_date.isoformat()

    print(
        f"Separating by extension and date: {extension}, {date_folder_name} in {working_dir} -> {target_dir}"
    )

    sorted_dir = (
        target_dir / date_folder_name / normalized_extension.lstrip(".").upper()
    )
    print(f"Ensuring directory exists: {sorted_dir}...")
    ensure_directory(sorted_dir, dry_run=dry_run)

    files = [
        f
        for f in _files_from_working_dirs(
            [working_dir], recursive=recursive, excluded_dirs=[target_dir]
        )
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
            print(f"[DRY RUN] Would move {f.name} -> {new_path}...")
            continue

        print(f"Moving {f.name} -> {new_path}...")
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
    recursive: bool,
    file_type: Optional[str] = None,
    history: bool = False,
    history_path: Optional[Path] = None,
    dry_run: bool = False,
) -> None:
    selected_file_type = _normalize_file_type(file_type)
    if selected_file_type and selected_file_type[0] == "invalid":
        print(f"Unsupported file type filter '{file_type}'.")
        return

    if selected_file_type:
        print(
            f"Separating files with filter {file_type} in {working_dir} -> {target_dir}"
        )
    else:
        print(f"Separating all files by file type in {working_dir} -> {target_dir}")

    files = _files_from_working_dirs(
        [working_dir], recursive=recursive, excluded_dirs=[target_dir]
    )
    if not files:
        print(f"No files found in {working_dir}.")
        return

    revert_map: dict[str, str] = {}
    operation = "separate_by_file_type"

    moved_files = 0

    for f in files:
        extension = get_extension(f, KNOWN_EXTENSIONS)
        folder_name = EXTENSION_TYPE_MAP.get(extension, "OTHERS")

        if selected_file_type:
            filter_kind, filter_value = selected_file_type
            if filter_kind == "category" and folder_name != filter_value:
                continue
            if filter_kind == "extension" and extension != filter_value:
                continue

        sorted_dir = target_dir / folder_name

        ensure_directory(sorted_dir, dry_run=dry_run)

        destination_path = sorted_dir / f.name
        new_path = build_non_conflicting_path(destination_path)
        original_path = f.resolve()

        if dry_run:
            print(f"[DRY RUN] Would move {f.name} -> {new_path}...")
            continue

        print(f"Moving {f.name} -> {new_path}...")
        f.rename(new_path)
        revert_map[str(new_path.resolve())] = str(original_path)
        moved_files += 1

    if moved_files == 0:
        print(f"No files found for file type '{file_type}' in {working_dir}.")
        return

    if history and not dry_run:
        if not history_path:
            print("Failed to validate History path, cannot save history.")
            return

        save_history(
            history_path=history_path,
            revert_map=revert_map,
            operation=operation,
        )


def MergeByExtension(
    extension: str,
    target_dir: Path,
    working_dirs: list[Path],
    recursive: bool,
    history_path: Optional[Path],
    history: bool = False,
    dry_run: bool = False,
) -> None:
    print(
        f"Merging by extension: {extension} from {len(working_dirs)} working directories -> {target_dir}"
    )

    normalized_extension = extension.lower()
    sorted_dir = target_dir / normalized_extension.lstrip(".").upper()

    print(f"Ensuring directory exists: {sorted_dir}...")
    ensure_directory(sorted_dir, dry_run=dry_run)

    files = [
        f
        for f in _files_from_working_dirs(
            working_dirs, recursive=recursive, excluded_dirs=[target_dir]
        )
        if get_extension(f, KNOWN_EXTENSIONS) == normalized_extension
    ]
    if not files:
        print(
            f"No files with extension '{extension}' found in provided working directories."
        )
        return

    revert_map: dict[str, str] = {}
    operation = "merge_by_extension"

    for f in files:
        destination_path = sorted_dir / f.name
        new_path = build_non_conflicting_path(destination_path)
        original_path = f.resolve()

        if dry_run:
            print(f"[DRY RUN] Would move {f} -> {new_path}...")
            continue

        print(f"Moving {f} -> {new_path}...")
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


def MergeByDate(
    sort_date: Optional[str],
    target_dir: Path,
    working_dirs: list[Path],
    recursive: bool,
    history: bool,
    history_path: Optional[Path],
    dry_run: bool,
) -> None:
    if sort_date:
        print(
            f"Merging files modified on {sort_date} from {len(working_dirs)} working directories -> {target_dir}"
        )
    else:
        print(
            f"Merging files modified today from {len(working_dirs)} working directories -> {target_dir}"
        )

    sorted_dir = target_dir / (sort_date if sort_date else date.today().isoformat())

    print(f"Ensuring directory exists: {sorted_dir}...")
    ensure_directory(sorted_dir, dry_run=dry_run)

    target_date = date.fromisoformat(sort_date) if sort_date else date.today()
    files = [
        f
        for f in _files_from_working_dirs(
            working_dirs, recursive=recursive, excluded_dirs=[target_dir]
        )
        if datetime.fromtimestamp(f.stat().st_mtime).date() == target_date
    ]

    if not files:
        print(
            f"No files modified on {sort_date if sort_date else 'today'} found in provided working directories."
        )
        return

    revert_map: dict[str, str] = {}
    operation = "merge_by_date"

    for f in files:
        destination_path = sorted_dir / f.name
        new_path = build_non_conflicting_path(destination_path)
        original_path = f.resolve()
        if dry_run:
            print(f"[DRY RUN] Would move {f} -> {new_path}...")
            continue

        print(f"Moving {f} -> {new_path}...")
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


def MergeByExtensionAndDate(
    sort_date: Optional[str],
    extension: str,
    target_dir: Path,
    working_dirs: list[Path],
    recursive: bool,
    history: bool = False,
    history_path: Optional[Path] = None,
    dry_run: bool = False,
) -> None:
    normalized_extension = extension.lower()
    selected_date = date.fromisoformat(sort_date) if sort_date else date.today()
    date_folder_name = selected_date.isoformat()

    print(
        f"Merging by extension and date: {extension}, {date_folder_name} from {len(working_dirs)} working directories -> {target_dir}"
    )

    sorted_dir = (
        target_dir / date_folder_name / normalized_extension.lstrip(".").upper()
    )
    print(f"Ensuring directory exists: {sorted_dir}...")
    ensure_directory(sorted_dir, dry_run=dry_run)

    files = [
        f
        for f in _files_from_working_dirs(
            working_dirs, recursive=recursive, excluded_dirs=[target_dir]
        )
        if get_extension(f, KNOWN_EXTENSIONS) == normalized_extension
        and datetime.fromtimestamp(f.stat().st_mtime).date() == selected_date
    ]

    if not files:
        print(
            f"No files with extension '{extension}' modified on {date_folder_name} found in provided working directories."
        )
        return

    revert_map: dict[str, str] = {}
    operation = "merge_by_extension_and_date"

    for f in files:
        destination_path = sorted_dir / f.name
        new_path = build_non_conflicting_path(destination_path)
        original_path = f.resolve()

        if dry_run:
            print(f"[DRY RUN] Would move {f} -> {new_path}...")
            continue

        print(f"Moving {f} -> {new_path}...")
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


def MergeByFileType(
    target_dir: Path,
    working_dirs: list[Path],
    recursive: bool,
    history: bool = False,
    history_path: Optional[Path] = None,
    dry_run: bool = False,
) -> None:
    print(
        f"Merging all files by file type from {len(working_dirs)} working directories -> {target_dir}"
    )

    files = _files_from_working_dirs(
        working_dirs, recursive=recursive, excluded_dirs=[target_dir]
    )
    if not files:
        print("No files found in provided working directories.")
        return

    revert_map: dict[str, str] = {}
    operation = "merge_by_file_type"

    for f in files:
        extension = get_extension(f, KNOWN_EXTENSIONS)
        folder_name = EXTENSION_TYPE_MAP.get(extension, "OTHERS")
        sorted_dir = target_dir / folder_name

        ensure_directory(sorted_dir, dry_run=dry_run)

        destination_path = sorted_dir / f.name
        new_path = build_non_conflicting_path(destination_path)
        original_path = f.resolve()

        if dry_run:
            print(f"[DRY RUN] Would move {f} -> {new_path}...")
            continue

        print(f"Moving {f} -> {new_path}...")
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
    recursive: bool,
    history: bool,
    history_path: Optional[Path],
    dry_run: bool,
) -> None:
    SeparateByDate(
        sort_date=sort_date,
        target_dir=target_dir,
        working_dir=working_dir,
        recursive=recursive,
        history=history,
        history_path=history_path,
        dry_run=dry_run,
    )


def SeperateByExtensionAndDate(
    sort_date: Optional[str],
    extension: str,
    target_dir: Path,
    working_dir: Path,
    recursive: bool,
    history: bool = False,
    history_path: Optional[Path] = None,
    dry_run: bool = False,
) -> None:
    SeparateByExtensionAndDate(
        sort_date=sort_date,
        extension=extension,
        target_dir=target_dir,
        working_dir=working_dir,
        recursive=recursive,
        history=history,
        history_path=history_path,
        dry_run=dry_run,
    )
