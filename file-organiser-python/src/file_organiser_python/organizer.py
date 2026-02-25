from datetime import date
from pathlib import Path
from typing import Optional

from file_organiser_python.history import save_history
from file_organiser_python.constants import HISTORY_FILE_PREFIX


class FileOrganizer:
    def __init__(
        self,
        target_dir: Optional[Path] = None,
        working_dir: Optional[Path] = None,
        dry_run: bool = False,
        save_history: bool = False,
    ) -> None:
        self.target_dir = target_dir.resolve() if target_dir else Path.cwd()
        self.working_dir = working_dir.resolve() if working_dir else Path.cwd()
        self.dry_run = dry_run
        self.save_history = save_history

        if save_history:
            self.history_path = Path(
                self.target_dir
                / f"{HISTORY_FILE_PREFIX}{date.today().strftime('%Y-%m-%d')}.json"
            )

    def rename(self) -> None:
        files = [f for f in self.working_dir.iterdir() if f.is_file()]

        if not files:
            print("No files found in the working directory.")
            return

        rename_map: dict[str, str] = {}

        for index, file in enumerate(sorted(files), start=1):
            new_name = f"{index}{file.suffix}"
            new_path = self.target_dir / new_name

            rename_map[file.name] = new_name

            if self.dry_run:
                print(f"[DRY RUN] {file.name} → {new_name}")
            else:
                file.rename(new_path)
                print(f"{file.name} → {new_name}")

        if self.save_history and self.history_path and not self.dry_run:
            save_history(self.history_path, rename_map)
            print(f"History saved to {self.history_path.name}")

    def separate(self) -> None:
        print("Separating functionality is not implemented yet.")
