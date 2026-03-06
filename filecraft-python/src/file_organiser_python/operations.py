"""
Core file organization operations.

All separate/merge operations funnel through ``_organize_files`` which owns
the discover -> filter -> move -> history loop.  Public functions are thin
wrappers that supply a file filter and a per-file destination builder.
"""

import errno
import os
import shutil
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Optional


def _safe_print(message: str) -> None:
    """Print *message*, replacing unencodable characters on narrow-codec terminals (e.g. cp1252 on Windows)."""
    try:
        print(message)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", "utf-8") or "utf-8"
        safe = message.encode(encoding, errors="backslashreplace").decode(encoding)
        print(safe)


from file_organiser_python.constants import (
    ARCHIVE_EXTENSIONS,
    AUDIO_EXTENSIONS,
    CODE_EXTENSIONS,
    DISK_IMAGE_EXTENSIONS,
    DOCUMENT_EXTENSIONS,
    EXECUTABLE_EXTENSIONS,
    FONT_EXTENSIONS,
    IMAGE_EXTENSIONS,
    PRESENTATION_EXTENSIONS,
    SPREADSHEET_EXTENSIONS,
    VIDEO_EXTENSIONS,
)
from file_organiser_python.history import save_history
from file_organiser_python.utils import (
    build_non_conflicting_path,
    ensure_directory,
    get_extension,
)

# ---------------------------------------------------------------------------
# Extension -> category mapping
# ---------------------------------------------------------------------------

_CATEGORY_SOURCES: list[tuple[set[str], str]] = [
    (IMAGE_EXTENSIONS, "IMAGES"),
    (VIDEO_EXTENSIONS, "VIDEOS"),
    (AUDIO_EXTENSIONS, "AUDIO"),
    (DOCUMENT_EXTENSIONS, "DOCUMENTS"),
    (SPREADSHEET_EXTENSIONS, "SPREADSHEETS"),
    (PRESENTATION_EXTENSIONS, "PRESENTATIONS"),
    (ARCHIVE_EXTENSIONS, "ARCHIVES"),
    (EXECUTABLE_EXTENSIONS, "EXECUTABLES"),
    (CODE_EXTENSIONS, "CODE"),
    (FONT_EXTENSIONS, "FONTS"),
    (DISK_IMAGE_EXTENSIONS, "DISK_IMAGES"),
]

EXTENSION_TYPE_MAP: dict[str, str] = {}
for _exts, _cat in _CATEGORY_SOURCES:
    for _ext in _exts:
        EXTENSION_TYPE_MAP[_ext] = _cat

KNOWN_EXTENSIONS: set[str] = set(EXTENSION_TYPE_MAP.keys())
KNOWN_FILE_TYPES: set[str] = set(EXTENSION_TYPE_MAP.values()) | {"OTHERS"}

# ---------------------------------------------------------------------------
# File-type normalisation
# ---------------------------------------------------------------------------


def normalize_file_type(file_type: Optional[str]) -> Optional[tuple[str, str]]:
    """Return ``(kind, value)`` for a user-supplied type filter.

    *kind* is ``"extension"``, ``"category"`` or ``"invalid"``.
    Returns ``None`` when *file_type* is empty / ``None``.
    """
    if not file_type:
        return None

    stripped = file_type.strip().lower()
    if not stripped:
        return None

    ext_candidate = f".{stripped.lstrip('.')}"
    if ext_candidate in KNOWN_EXTENSIONS:
        return ("extension", ext_candidate)

    cat_candidate = stripped.upper().replace("-", "_").replace(" ", "_")
    if cat_candidate in KNOWN_FILE_TYPES:
        return ("category", cat_candidate)

    return ("invalid", "")


# ---------------------------------------------------------------------------
# Low-level move helpers
# ---------------------------------------------------------------------------


def _paths_refer_to_same_file(source: Path, destination: Path) -> bool:
    src_abs = source.absolute()
    dst_abs = destination.absolute()

    if src_abs == dst_abs:
        return True

    if not destination.exists():
        return False

    try:
        return os.path.samefile(src_abs, dst_abs)
    except OSError:
        return False


def _preflight_cross_device_space(
    files: list[Path],
    destination_for_file: Callable[[Path], Path],
) -> None:
    """Raise ``OSError(ENOSPC)`` when a cross-device move would run out of space."""
    needed: dict[int, int] = {}
    sample: dict[int, Path] = {}

    for fp in files:
        dst = destination_for_file(fp)
        if _paths_refer_to_same_file(fp, dst):
            continue

        dst_parent = dst.parent
        if not dst_parent.exists():
            continue

        dst_dev = dst_parent.stat().st_dev
        if fp.stat().st_dev == dst_dev:
            continue

        needed[dst_dev] = needed.get(dst_dev, 0) + fp.stat().st_size
        sample[dst_dev] = dst_parent

    for dev, req in needed.items():
        free = shutil.disk_usage(sample[dev]).free
        if req > free:
            raise OSError(
                errno.ENOSPC,
                f"Insufficient free space on destination filesystem. "
                f"Required {req} bytes, available {free} bytes in {sample[dev]}.",
            )


def _move_file(
    file_path: Path,
    destination_path: Path,
    dry_run: bool,
) -> Optional[Path]:
    """Move *file_path* to *destination_path*, handling conflicts and cross-device moves."""
    if _paths_refer_to_same_file(file_path, destination_path):
        _safe_print(f"Skipping {file_path} (already at destination).")
        return None

    new_path = build_non_conflicting_path(destination_path)

    if dry_run:
        _safe_print(f"[DRY RUN] Would move {file_path} -> {new_path}...")
        return new_path

    _safe_print(f"Moving {file_path} -> {new_path}...")

    try:
        file_path.rename(new_path)
    except OSError as exc:
        if exc.errno == errno.EXDEV:
            src_size = file_path.stat().st_size
            free = shutil.disk_usage(new_path.parent).free
            if src_size > free:
                raise OSError(
                    errno.ENOSPC,
                    f"Insufficient free space while moving across filesystems. "
                    f"Required {src_size} bytes, available {free} bytes in {new_path.parent}.",
                ) from exc
            shutil.copy2(file_path, new_path)
            file_path.unlink()
        elif exc.errno == errno.ENOSPC:
            raise OSError(
                errno.ENOSPC,
                f"Insufficient free space while moving {file_path} to {new_path}. "
                "Free space on the destination and retry.",
            ) from exc
        else:
            raise

    return new_path


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------


def _files_from_working_dirs(
    working_dirs: list[Path],
    recursive: bool = False,
    excluded_dirs: Optional[list[Path]] = None,
) -> list[Path]:
    """Collect regular files from *working_dirs*, pruning *excluded_dirs*."""

    def _abs(p: Path) -> Path:
        return p.absolute()

    def _is_excluded(p: Path, exclusions: list[Path]) -> bool:
        return any(p.is_relative_to(ex) for ex in exclusions)

    # De-duplicate and prune nested roots so each file is visited once.
    resolved = sorted(
        {_abs(d) for d in working_dirs},
        key=lambda p: (len(p.parts), str(p)),
    )
    roots: list[Path] = []
    for candidate in resolved:
        if any(candidate.is_relative_to(r) for r in roots):
            continue
        roots.append(candidate)

    abs_excluded = [_abs(d) for d in excluded_dirs or []]

    files: list[Path] = []
    for root in roots:
        effective = [ex for ex in abs_excluded if ex != root]

        if _is_excluded(root, effective):
            continue

        if recursive:
            for dirpath, dirnames, filenames in os.walk(root, topdown=True):
                dp = Path(dirpath)
                dirnames[:] = [
                    d for d in dirnames if not _is_excluded(dp / d, effective)
                ]
                files.extend(c for c in (dp / fn for fn in filenames) if c.is_file())
        else:
            files.extend(
                f
                for f in root.iterdir()
                if f.is_file() and not _is_excluded(f, effective)
            )

    return files


# ---------------------------------------------------------------------------
# Core organise loop
# ---------------------------------------------------------------------------


def _organize_files(
    *,
    working_dirs: list[Path],
    target_dir: Path,
    file_filter: Callable[[Path], bool],
    dest_for_file: Callable[[Path], Path],
    operation: str,
    header_message: str,
    no_match_message: str,
    recursive: bool = False,
    dry_run: bool = False,
    history: bool = False,
    history_path: Optional[Path] = None,
) -> None:
    """Discover -> filter -> create dirs -> preflight -> move -> save history."""
    _safe_print(header_message)

    files = [
        f
        for f in _files_from_working_dirs(
            working_dirs, recursive=recursive, excluded_dirs=[target_dir]
        )
        if f.is_file() and file_filter(f)
    ]

    if not files:
        _safe_print(no_match_message)
        return

    # Ensure every unique destination directory exists.
    seen_dirs: set[Path] = set()
    for f in files:
        parent = dest_for_file(f).parent
        if parent not in seen_dirs:
            ensure_directory(parent, dry_run=dry_run)
            seen_dirs.add(parent)

    if not dry_run:
        _preflight_cross_device_space(files, dest_for_file)

    revert_map: dict[str, str] = {}
    for f in files:
        original = f.resolve()
        moved = _move_file(f, dest_for_file(f), dry_run)
        if not moved or dry_run:
            continue
        revert_map[str(moved.resolve())] = str(original)

    if history and not dry_run and revert_map:
        if not history_path:
            _safe_print("Failed to validate History path, cannot save history.")
            return
        save_history(
            history_path=history_path, revert_map=revert_map, operation=operation
        )


# ---------------------------------------------------------------------------
# Convenience helpers for dest / filter builders
# ---------------------------------------------------------------------------


def _ext_folder(ext: str) -> str:
    """``'.pdf'`` -> ``'PDF'``"""
    return ext.lstrip(".").upper()


def _resolve_date(sort_date: Optional[str]) -> date:
    return date.fromisoformat(sort_date) if sort_date else date.today()


def _date_label(sort_date: Optional[str]) -> str:
    return sort_date if sort_date else date.today().isoformat()


def _matches_date(f: Path, target: date) -> bool:
    return datetime.fromtimestamp(f.stat().st_mtime).date() == target


def _category_for_file(f: Path) -> str:
    ext = get_extension(f, KNOWN_EXTENSIONS)
    return EXTENSION_TYPE_MAP.get(ext, "OTHERS")


# ---------------------------------------------------------------------------
# Public operation functions  (separate_*)
# ---------------------------------------------------------------------------


def separate_by_extension(
    extension: str,
    target_dir: Path,
    working_dir: Path,
    recursive: bool,
    history_path: Optional[Path],
    history: bool = False,
    dry_run: bool = False,
) -> None:
    ext = extension.lower()
    folder = target_dir / _ext_folder(ext)

    _organize_files(
        working_dirs=[working_dir],
        target_dir=target_dir,
        file_filter=lambda f: get_extension(f, KNOWN_EXTENSIONS) == ext,
        dest_for_file=lambda f: folder / f.name,
        operation="separate_by_extension",
        header_message=f"Separating by extension: {ext} in {working_dir} -> {target_dir}",
        no_match_message=f"No files with extension '{extension}' found in {working_dir}.",
        recursive=recursive,
        dry_run=dry_run,
        history=history,
        history_path=history_path,
    )


def separate_by_date(
    sort_date: Optional[str],
    target_dir: Path,
    working_dir: Path,
    recursive: bool,
    history: bool,
    history_path: Optional[Path],
    dry_run: bool,
) -> None:
    td = _resolve_date(sort_date)
    label = _date_label(sort_date)
    folder = target_dir / label

    _organize_files(
        working_dirs=[working_dir],
        target_dir=target_dir,
        file_filter=lambda f: _matches_date(f, td),
        dest_for_file=lambda f: folder / f.name,
        operation="separate_by_date",
        header_message=f"Separating files modified on {label} in {working_dir} -> {target_dir}",
        no_match_message=f"No files modified on {label} found in {working_dir}.",
        recursive=recursive,
        dry_run=dry_run,
        history=history,
        history_path=history_path,
    )


def separate_by_extension_and_date(
    sort_date: Optional[str],
    extension: str,
    target_dir: Path,
    working_dir: Path,
    recursive: bool,
    history: bool = False,
    history_path: Optional[Path] = None,
    dry_run: bool = False,
) -> None:
    ext = extension.lower()
    td = _resolve_date(sort_date)
    dl = _date_label(sort_date)
    folder = target_dir / dl / _ext_folder(ext)

    _organize_files(
        working_dirs=[working_dir],
        target_dir=target_dir,
        file_filter=lambda f: (
            get_extension(f, KNOWN_EXTENSIONS) == ext and _matches_date(f, td)
        ),
        dest_for_file=lambda f: folder / f.name,
        operation="separate_by_extension_and_date",
        header_message=(
            f"Separating by extension and date: {ext}, {dl} "
            f"in {working_dir} -> {target_dir}"
        ),
        no_match_message=(
            f"No files with extension '{extension}' modified on {dl} "
            f"found in {working_dir}."
        ),
        recursive=recursive,
        dry_run=dry_run,
        history=history,
        history_path=history_path,
    )


def separate_by_file_type(
    target_dir: Path,
    working_dir: Path,
    recursive: bool,
    file_type: Optional[str] = None,
    history: bool = False,
    history_path: Optional[Path] = None,
    dry_run: bool = False,
) -> None:
    selected = normalize_file_type(file_type)
    if selected and selected[0] == "invalid":
        _safe_print(f"Unsupported file type filter '{file_type}'.")
        return

    def _filter(f: Path) -> bool:
        if not selected:
            return True
        kind, value = selected
        if kind == "category":
            return _category_for_file(f) == value
        return get_extension(f, KNOWN_EXTENSIONS) == value  # extension filter

    def _dest(f: Path) -> Path:
        return target_dir / _category_for_file(f) / f.name

    label = f"with filter {file_type}" if selected else "by file type"

    _organize_files(
        working_dirs=[working_dir],
        target_dir=target_dir,
        file_filter=_filter,
        dest_for_file=_dest,
        operation="separate_by_file_type",
        header_message=f"Separating files {label} in {working_dir} -> {target_dir}",
        no_match_message=(
            f"No files found for file type '{file_type}' in {working_dir}."
            if file_type
            else f"No files found in {working_dir}."
        ),
        recursive=recursive,
        dry_run=dry_run,
        history=history,
        history_path=history_path,
    )


# ---------------------------------------------------------------------------
# Public operation functions  (merge_*)
# ---------------------------------------------------------------------------


def merge_by_extension(
    extension: str,
    target_dir: Path,
    working_dirs: list[Path],
    recursive: bool,
    history_path: Optional[Path],
    history: bool = False,
    dry_run: bool = False,
) -> None:
    ext = extension.lower()
    folder = target_dir / _ext_folder(ext)

    _organize_files(
        working_dirs=working_dirs,
        target_dir=target_dir,
        file_filter=lambda f: get_extension(f, KNOWN_EXTENSIONS) == ext,
        dest_for_file=lambda f: folder / f.name,
        operation="merge_by_extension",
        header_message=(
            f"Merging by extension: {ext} from {len(working_dirs)} "
            f"directories -> {target_dir}"
        ),
        no_match_message=(
            f"No files with extension '{extension}' found in "
            "provided working directories."
        ),
        recursive=recursive,
        dry_run=dry_run,
        history=history,
        history_path=history_path,
    )


def merge_by_date(
    sort_date: Optional[str],
    target_dir: Path,
    working_dirs: list[Path],
    recursive: bool,
    history: bool,
    history_path: Optional[Path],
    dry_run: bool,
) -> None:
    td = _resolve_date(sort_date)
    label = _date_label(sort_date)
    folder = target_dir / label

    _organize_files(
        working_dirs=working_dirs,
        target_dir=target_dir,
        file_filter=lambda f: _matches_date(f, td),
        dest_for_file=lambda f: folder / f.name,
        operation="merge_by_date",
        header_message=(
            f"Merging files modified on {label} from {len(working_dirs)} "
            f"directories -> {target_dir}"
        ),
        no_match_message=(
            f"No files modified on {label} found in " "provided working directories."
        ),
        recursive=recursive,
        dry_run=dry_run,
        history=history,
        history_path=history_path,
    )


def merge_by_extension_and_date(
    sort_date: Optional[str],
    extension: str,
    target_dir: Path,
    working_dirs: list[Path],
    recursive: bool,
    history: bool = False,
    history_path: Optional[Path] = None,
    dry_run: bool = False,
) -> None:
    ext = extension.lower()
    td = _resolve_date(sort_date)
    dl = _date_label(sort_date)
    folder = target_dir / dl / _ext_folder(ext)

    _organize_files(
        working_dirs=working_dirs,
        target_dir=target_dir,
        file_filter=lambda f: (
            get_extension(f, KNOWN_EXTENSIONS) == ext and _matches_date(f, td)
        ),
        dest_for_file=lambda f: folder / f.name,
        operation="merge_by_extension_and_date",
        header_message=(
            f"Merging by extension and date: {ext}, {dl} from "
            f"{len(working_dirs)} directories -> {target_dir}"
        ),
        no_match_message=(
            f"No files with extension '{extension}' modified on {dl} "
            "found in provided working directories."
        ),
        recursive=recursive,
        dry_run=dry_run,
        history=history,
        history_path=history_path,
    )


def merge_by_file_type(
    target_dir: Path,
    working_dirs: list[Path],
    recursive: bool,
    history: bool = False,
    history_path: Optional[Path] = None,
    dry_run: bool = False,
) -> None:
    def _dest(f: Path) -> Path:
        return target_dir / _category_for_file(f) / f.name

    _organize_files(
        working_dirs=working_dirs,
        target_dir=target_dir,
        file_filter=lambda _: True,
        dest_for_file=_dest,
        operation="merge_by_file_type",
        header_message=(
            f"Merging all files by file type from {len(working_dirs)} "
            f"directories -> {target_dir}"
        ),
        no_match_message="No files found in provided working directories.",
        recursive=recursive,
        dry_run=dry_run,
        history=history,
        history_path=history_path,
    )
