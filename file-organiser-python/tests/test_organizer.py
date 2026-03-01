import sys
import tempfile
import unittest
from pathlib import Path

from typer.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from file_organiser_python.main import app
from file_organiser_python.organizer import FileOrganizer
from file_organiser_python.enums import SeparateChoices
from file_organiser_python.history import revert_history


class TestOrganizerFixes(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.work = self.base / "work"
        self.out = self.base / "out"
        self.work.mkdir(parents=True, exist_ok=True)
        self.out.mkdir(parents=True, exist_ok=True)
        self.runner = CliRunner()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_file_mode_routes_compound_extension_to_archives(self) -> None:
        (self.work / "backup.tar.gz").write_text("x", encoding="utf-8")

        organizer = FileOrganizer(
            target_dir=self.out,
            working_dir=self.work,
            separate_choice=SeparateChoices.FILE,
        )
        organizer.separate()

        self.assertTrue((self.out / "ARCHIVES" / "backup.tar.gz").exists())

    def test_invalid_date_returns_cli_error(self) -> None:
        result = self.runner.invoke(
            app,
            [
                "separate",
                "--mode",
                "date",
                "--date",
                "bad-date",
                "--working-dir",
                str(self.work),
                "--target-dir",
                str(self.out),
            ],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Date must be in YYYY-MM-DD format.", result.output)

    def test_rename_collision_and_revert_round_trip(self) -> None:
        (self.work / "a.txt").write_text("a", encoding="utf-8")
        (self.out / "1.txt").write_text("existing", encoding="utf-8")

        organizer = FileOrganizer(
            target_dir=self.out,
            working_dir=self.work,
            save_history=True,
        )
        organizer.rename()

        self.assertTrue((self.out / "1_1.txt").exists())
        self.assertTrue((self.out / "1.txt").exists())
        history_path = organizer.history_path
        assert history_path is not None
        reverted = revert_history(history_path=history_path, delete_after_revert=True)

        self.assertEqual(reverted, 1)
        self.assertTrue((self.work / "a.txt").exists())
        self.assertFalse((self.out / "1_1.txt").exists())
        self.assertFalse(history_path.exists())

    def test_history_filename_is_unique_per_run(self) -> None:
        organizer1 = FileOrganizer(target_dir=self.out, save_history=True)
        organizer2 = FileOrganizer(target_dir=self.out, save_history=True)

        self.assertIsNotNone(organizer1.history_path)
        self.assertIsNotNone(organizer2.history_path)
        history_path_1 = organizer1.history_path
        history_path_2 = organizer2.history_path
        assert history_path_1 is not None
        assert history_path_2 is not None
        self.assertNotEqual(history_path_1.name, history_path_2.name)


if __name__ == "__main__":
    unittest.main()
