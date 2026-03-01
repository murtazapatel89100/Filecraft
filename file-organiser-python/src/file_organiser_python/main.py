from pathlib import Path
from datetime import date
from typing import Optional

import typer

from file_organiser_python.enums import SeparateChoices
from file_organiser_python.history import revert_history
from file_organiser_python.organizer import FileOrganizer
from file_organiser_python.utils import validate_directory

app = typer.Typer()


def _validate_optional_directory(path: Optional[Path], option_name: str) -> None:
    if not path:
        return

    try:
        validate_directory(path)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint=option_name) from exc


def _validate_optional_iso_date(sort_date: Optional[str]) -> None:
    if not sort_date:
        return

    try:
        date.fromisoformat(sort_date)
    except ValueError as exc:
        raise typer.BadParameter(
            "Date must be in YYYY-MM-DD format.",
            param_hint="--date",
        ) from exc


def _validate_required_directories(paths: list[Path], option_name: str) -> None:
    if not paths:
        raise typer.BadParameter(
            "At least one working directory is required.",
            param_hint=option_name,
        )

    for path in paths:
        try:
            validate_directory(path)
        except ValueError as exc:
            raise typer.BadParameter(str(exc), param_hint=option_name) from exc


@app.command()
def rename(
    target_dir: Optional[Path] = typer.Option(
        None, help="Where renamed files are moved."
    ),
    working_dir: Optional[Path] = typer.Option(
        None, help="Source directory to process."
    ),
    dry_run: bool = typer.Option(False, help="Preview actions without making changes."),
    history: bool = typer.Option(False, "--history", help="Save operation history."),
) -> None:
    _validate_optional_directory(target_dir, "--target-dir")
    _validate_optional_directory(working_dir, "--working-dir")

    organizer = FileOrganizer(
        target_dir=target_dir,
        working_dir=working_dir,
        dry_run=dry_run,
        save_history=history,
    )
    organizer.rename()


@app.command()
def separate(
    mode: SeparateChoices = typer.Option(
        SeparateChoices.EXTENSION,
        "--mode",
        help="How to separate files: extension, date, extension_and_date, file.",
    ),
    extension: Optional[str] = typer.Option(
        None,
        "--extension",
        help="Extension to filter, e.g. .pdf or pdf.",
    ),
    sort_date: Optional[str] = typer.Option(
        None,
        "--date",
        help="Date in YYYY-MM-DD format. Defaults to today when mode uses date.",
    ),
    target_dir: Optional[Path] = typer.Option(
        None, help="Where separated files are moved."
    ),
    working_dir: Optional[Path] = typer.Option(
        None, help="Source directory to process."
    ),
    dry_run: bool = typer.Option(False, help="Preview actions without making changes."),
    history: bool = typer.Option(False, "--history", help="Save operation history."),
) -> None:
    _validate_optional_directory(target_dir, "--target-dir")
    _validate_optional_directory(working_dir, "--working-dir")
    _validate_optional_iso_date(sort_date)

    normalized_extension = f".{extension.lstrip('.').lower()}" if extension else None

    organizer = FileOrganizer(
        target_dir=target_dir,
        working_dir=working_dir,
        dry_run=dry_run,
        save_history=history,
        sort_date=sort_date,
        sort_extension=normalized_extension,
        separate_choice=mode,
    )
    organizer.separate()


@app.command()
def revert(
    directory: Optional[Path] = typer.Option(
        None,
        help="Directory containing history files. Defaults to current directory.",
    ),
    history_file: Optional[Path] = typer.Option(
        None,
        "--history-file",
        help="Specific history file path to revert.",
    ),
    dry_run: bool = typer.Option(
        False, help="Preview revert actions without making changes."
    ),
    keep_history: bool = typer.Option(
        False,
        "--keep-history",
        help="Do not delete history file after successful revert.",
    ),
) -> None:
    _validate_optional_directory(directory, "--directory")

    reverted = revert_history(
        history_path=history_file,
        directory=directory,
        dry_run=dry_run,
        delete_after_revert=not keep_history,
    )
    print(f"Reverted {reverted} file(s).")


@app.command()
def merge(
    mode: SeparateChoices = typer.Option(
        SeparateChoices.EXTENSION,
        "--mode",
        help="How to merge files: extension, date, extension_and_date, file.",
    ),
    extension: Optional[str] = typer.Option(
        None,
        "--extension",
        help="Extension to filter, e.g. .pdf or pdf.",
    ),
    sort_date: Optional[str] = typer.Option(
        None,
        "--date",
        help="Date in YYYY-MM-DD format. Defaults to today when mode uses date.",
    ),
    target_dir: Optional[Path] = typer.Option(
        None, help="Where merged files are moved."
    ),
    working_dirs: list[Path] = typer.Option(
        ..., "--working-dir", help="One or more source directories to merge from."
    ),
    dry_run: bool = typer.Option(False, help="Preview actions without making changes."),
    history: bool = typer.Option(False, "--history", help="Save operation history."),
) -> None:
    _validate_optional_directory(target_dir, "--target-dir")
    _validate_required_directories(working_dirs, "--working-dir")
    _validate_optional_iso_date(sort_date)

    normalized_extension = f".{extension.lstrip('.').lower()}" if extension else None

    organizer = FileOrganizer(
        target_dir=target_dir,
        working_dirs=working_dirs,
        dry_run=dry_run,
        save_history=history,
        sort_date=sort_date,
        sort_extension=normalized_extension,
        separate_choice=mode,
    )
    organizer.merge()


if __name__ == "__main__":
    app()
