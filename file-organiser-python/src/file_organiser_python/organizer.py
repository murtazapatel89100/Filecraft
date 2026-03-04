from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from file_organiser_python.history import save_history
from file_organiser_python.constants import HISTORY_FILE_PREFIX
from file_organiser_python.enums import SeparateChoices
from file_organiser_python.operations import (
    SeparateByExtension,
    SeparateByDate,
    SeparateByExtensionAndDate,
    SeparateByFileType,
    MergeByExtension,
    MergeByDate,
    MergeByExtensionAndDate,
    MergeByFileType,
)
from file_organiser_python.utils import build_non_conflicting_path


class FileOrganizer:
    def __init__(
        self,
        target_dir: Optional[Path] = None,
        working_dir: Optional[Path] = None,
        working_dirs: Optional[list[Path]] = None,
        dry_run: bool = False,
        save_history: bool = False,
        sort_date: Optional[str] = None,
        sort_extension: Optional[str] = None,
        file_type: Optional[str] = None,
        separate_choice: Optional[SeparateChoices] = SeparateChoices.EXTENSION,
    ) -> None:
        try:
            self.target_dir = target_dir.resolve() if target_dir else Path.cwd()

        except FileNotFoundError:
            print(
                f"Target directory '{target_dir}' does not exist. Do you want to create it? (1.) or default to current directory (2.): ",
                end="",
            )

            input_choice = input().strip()

            if input_choice == "1" and target_dir:
                target_dir.mkdir(parents=True, exist_ok=True)
                self.target_dir = target_dir.resolve()
                print(f"Created target directory: {self.target_dir}")

            elif input_choice == "2":
                self.target_dir = Path.cwd()
                print(f"Defaulting to current directory as target: {self.target_dir}")

            else:
                print("User response not recognized. Exiting.")
                raise SystemExit(1)

        self.working_dir = working_dir.resolve() if working_dir else Path.cwd()
        self.working_dirs = (
            [path.resolve() for path in working_dirs]
            if working_dirs
            else [self.working_dir]
        )
        self.dry_run = dry_run
        self.save_history = save_history
        self.sort_date = sort_date
        self.sort_extension = sort_extension
        self.file_type = file_type
        self.separate_choice = separate_choice
        self.history_path: Optional[Path] = None

        if save_history:
            candidate_history_path = Path(
                self.target_dir
                / f"{HISTORY_FILE_PREFIX}{datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')}_{uuid4().hex[:8]}.json"
            )
            self.history_path = build_non_conflicting_path(candidate_history_path)

    def rename(self) -> None:
        files = [f for f in self.working_dir.iterdir() if f.is_file()]

        if not files:
            print("No files found in the working directory.")
            return

        rename_map: dict[str, str] = {}

        for index, file in enumerate(sorted(files), start=1):
            new_name = f"{index}{file.suffix}"
            destination_path = self.target_dir / new_name
            new_path = build_non_conflicting_path(destination_path)

            original_path = file.resolve()

            if self.dry_run:
                print(f"[DRY RUN] {file.name} -> {new_path.name}")
            else:
                file.rename(new_path)
                print(f"{file.name} -> {new_path.name}")
                rename_map[str(new_path.resolve())] = str(original_path)

        if self.save_history and self.history_path and not self.dry_run:
            save_history(self.history_path, rename_map)
            print(f"History saved to {self.history_path.name}")

    def separate(self) -> None:
        match self.separate_choice:
            case SeparateChoices.EXTENSION:
                if not self.sort_extension:
                    print("No extension specified for separation.")
                    return

                SeparateByExtension(
                    extension=self.sort_extension,
                    target_dir=self.target_dir,
                    working_dir=self.working_dir,
                    history=self.save_history,
                    history_path=self.history_path if self.save_history else None,
                    dry_run=self.dry_run,
                )
            case SeparateChoices.DATE:
                SeparateByDate(
                    dry_run=self.dry_run,
                    sort_date=self.sort_date,
                    target_dir=self.target_dir,
                    working_dir=self.working_dir,
                    history=self.save_history,
                    history_path=self.history_path,
                )
            case SeparateChoices.EXTENSION_AND_DATE:
                if not self.sort_extension:
                    print("No extension specified for separation.")
                    return

                SeparateByExtensionAndDate(
                    sort_date=self.sort_date,
                    extension=self.sort_extension,
                    target_dir=self.target_dir,
                    working_dir=self.working_dir,
                    history=self.save_history,
                    history_path=self.history_path,
                    dry_run=self.dry_run,
                )
            case SeparateChoices.FILE:
                SeparateByFileType(
                    target_dir=self.target_dir,
                    working_dir=self.working_dir,
                    file_type=self.file_type,
                    history=self.save_history,
                    history_path=self.history_path,
                    dry_run=self.dry_run,
                )
            case _:
                print("Invalid separation choice.")

    def merge(self) -> None:
        if not self.working_dirs:
            print("No working directories specified for merge.")
            return

        match self.separate_choice:
            case SeparateChoices.EXTENSION:
                if not self.sort_extension:
                    print("No extension specified for merge.")
                    return

                MergeByExtension(
                    extension=self.sort_extension,
                    target_dir=self.target_dir,
                    working_dirs=self.working_dirs,
                    history=self.save_history,
                    history_path=self.history_path if self.save_history else None,
                    dry_run=self.dry_run,
                )
            case SeparateChoices.DATE:
                MergeByDate(
                    sort_date=self.sort_date,
                    target_dir=self.target_dir,
                    working_dirs=self.working_dirs,
                    history=self.save_history,
                    history_path=self.history_path,
                    dry_run=self.dry_run,
                )
            case SeparateChoices.EXTENSION_AND_DATE:
                if not self.sort_extension:
                    print("No extension specified for merge.")
                    return

                MergeByExtensionAndDate(
                    sort_date=self.sort_date,
                    extension=self.sort_extension,
                    target_dir=self.target_dir,
                    working_dirs=self.working_dirs,
                    history=self.save_history,
                    history_path=self.history_path,
                    dry_run=self.dry_run,
                )
            case SeparateChoices.FILE:
                MergeByFileType(
                    target_dir=self.target_dir,
                    working_dirs=self.working_dirs,
                    history=self.save_history,
                    history_path=self.history_path,
                    dry_run=self.dry_run,
                )
            case _:
                print("Invalid merge choice.")
