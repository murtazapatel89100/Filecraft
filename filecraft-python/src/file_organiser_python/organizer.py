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


class MissingTargetDirectoryError(FileNotFoundError):
    def __init__(self, path: Path) -> None:
        super().__init__(f"Target directory does not exist: {path}")
        self.path = path


class TargetPathNotDirectoryError(NotADirectoryError):
    def __init__(self, path: Path) -> None:
        super().__init__(f"Target path is not a directory: {path}")
        self.path = path


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
        renameWith: Optional[str] = None,
        file_type: Optional[str] = None,
        separate_choice: Optional[SeparateChoices] = SeparateChoices.EXTENSION,
    ) -> None:
        if target_dir and not dry_run and not target_dir.exists():
            raise MissingTargetDirectoryError(target_dir)

        if target_dir and not dry_run and not target_dir.is_dir():
            raise TargetPathNotDirectoryError(target_dir)

        self.target_dir = target_dir.resolve() if target_dir else Path.cwd()

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
        self.renameWith = renameWith
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
            if self.renameWith:
                new_name = f"{self.renameWith}_{index}{file.suffix}"
            else:
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
