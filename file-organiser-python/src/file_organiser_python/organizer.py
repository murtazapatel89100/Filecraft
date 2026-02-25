from datetime import date
from pathlib import Path
from typing import Optional


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

        self.dry_run = dry_run
        self.save_history = save_history

        if save_history:
            self.history_path = (
                f".organizer_history_{date.today().strftime('%Y-%m-%d')}.json"
            )
