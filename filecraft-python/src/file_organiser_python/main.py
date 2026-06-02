from pathlib import Path
from datetime import date
from typing import Optional
import importlib.metadata

import typer

from file_organiser_python.enums import SeparateChoices
from file_organiser_python.history import revert_history
from file_organiser_python.organizer import (
    FileOrganizer,
    MissingTargetDirectoryError,
    TargetPathNotDirectoryError,
)
from file_organiser_python.utils import validate_directory

from rich.console import Console

app = typer.Typer()
console = Console()


def _resolve_target_directory(
    target_dir: Optional[Path],
    dry_run: bool,
) -> Optional[Path]:
    if not target_dir:
        return None

    if target_dir.exists():
        if not target_dir.is_dir():
            raise typer.BadParameter(
                f"Path is not a directory: {target_dir}",
                param_hint="--target-dir",
            )
        return target_dir

    if dry_run:
        console.print(
            f"[dim][DRY RUN] Target directory does not exist: {target_dir}[/dim]"
        )
        return target_dir

    if typer.confirm(
        f"Target directory '{target_dir}' does not exist. Create it?",
        default=False,
    ):
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise typer.BadParameter(
                f"Unable to create target directory: {target_dir}",
                param_hint="--target-dir",
            ) from exc
        console.print(
            f"[green]Created target directory: {target_dir.resolve()}[/green]"
        )
        return target_dir

    raise typer.BadParameter(
        f"Target directory does not exist: {target_dir}",
        param_hint="--target-dir",
    )


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
    recursive: bool = typer.Option(
        False,
        "--recursive",
        help="Recursively include files from all subdirectories.",
    ),
    dry_run: bool = typer.Option(False, help="Preview actions without making changes."),
    history: bool = typer.Option(False, "--history", help="Save operation history."),
    renameWith: Optional[str] = typer.Option(
        None,
        "--rename-with",
        help="Base name to use for renamed files (e.g. 'file' to get 'file_1.pdf', 'file_2.pdf', etc.).",
    ),
) -> None:
    _validate_optional_directory(working_dir, "--working-dir")
    target_dir = _resolve_target_directory(target_dir, dry_run=dry_run)

    try:
        organizer = FileOrganizer(
            target_dir=target_dir,
            working_dir=working_dir,
            recursive=recursive,
            dry_run=dry_run,
            save_history=history,
            renameWith=renameWith,
        )
    except (MissingTargetDirectoryError, TargetPathNotDirectoryError) as exc:
        raise typer.BadParameter(str(exc), param_hint="--target-dir") from exc
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
    file_type: Optional[str] = typer.Option(
        None,
        "--file-type",
        help="File type filter for --mode file (e.g. documents, images, pdf).",
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
    recursive: bool = typer.Option(
        False,
        "--recursive",
        help="Recursively include files from all subdirectories.",
    ),
    dry_run: bool = typer.Option(False, help="Preview actions without making changes."),
    history: bool = typer.Option(False, "--history", help="Save operation history."),
) -> None:
    _validate_optional_directory(working_dir, "--working-dir")
    _validate_optional_iso_date(sort_date)
    target_dir = _resolve_target_directory(target_dir, dry_run=dry_run)

    normalized_extension = f".{extension.lstrip('.').lower()}" if extension else None

    try:
        organizer = FileOrganizer(
            target_dir=target_dir,
            working_dir=working_dir,
            recursive=recursive,
            dry_run=dry_run,
            save_history=history,
            sort_date=sort_date,
            sort_extension=normalized_extension,
            file_type=file_type,
            separate_choice=mode,
        )
    except (MissingTargetDirectoryError, TargetPathNotDirectoryError) as exc:
        raise typer.BadParameter(str(exc), param_hint="--target-dir") from exc
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
    console.print(f"[green]Reverted {reverted} file(s).[/green]")


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
    recursive: bool = typer.Option(
        False,
        "--recursive",
        help="Recursively include files from all subdirectories of every --working-dir.",
    ),
    dry_run: bool = typer.Option(False, help="Preview actions without making changes."),
    history: bool = typer.Option(False, "--history", help="Save operation history."),
) -> None:
    _validate_required_directories(working_dirs, "--working-dir")
    _validate_optional_iso_date(sort_date)
    target_dir = _resolve_target_directory(target_dir, dry_run=dry_run)

    normalized_extension = f".{extension.lstrip('.').lower()}" if extension else None

    try:
        organizer = FileOrganizer(
            target_dir=target_dir,
            working_dirs=working_dirs,
            recursive=recursive,
            dry_run=dry_run,
            save_history=history,
            sort_date=sort_date,
            sort_extension=normalized_extension,
            separate_choice=mode,
        )
    except (MissingTargetDirectoryError, TargetPathNotDirectoryError) as exc:
        raise typer.BadParameter(str(exc), param_hint="--target-dir") from exc
    organizer.merge()


def version_callback(value: bool) -> None:
    if value:
        try:
            version = importlib.metadata.version("filecraft-cli")
            console.print(f"Filecraft CLI version: {version}")
        except importlib.metadata.PackageNotFoundError:
            console.print("Filecraft CLI version: unknown")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show the application's version and exit.",
    )
) -> None:
    """Filecraft CLI - Organize your files easily."""
    pass


if __name__ == "__main__":
    app()
