import sys
import tempfile
import unittest
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

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
        self.work2 = self.base / "work2"
        self.out = self.base / "out"
        self.work.mkdir(parents=True, exist_ok=True)
        self.work2.mkdir(parents=True, exist_ok=True)
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

    def test_target_dir_missing_create_option_creates_directory(self) -> None:
        missing_target = self.base / "missing-create"
        original_resolve = Path.resolve

        def resolve_with_missing_failure(path: Path, *args, **kwargs) -> Path:
            if path == missing_target and not missing_target.exists():
                raise FileNotFoundError("missing target")
            return original_resolve(path, *args, **kwargs)

        with patch(
            "file_organiser_python.organizer.Path.resolve",
            autospec=True,
            side_effect=resolve_with_missing_failure,
        ):
            with patch("builtins.input", return_value="1"):
                organizer = FileOrganizer(target_dir=missing_target)

        self.assertTrue(missing_target.exists())
        self.assertEqual(organizer.target_dir, missing_target.resolve())

    def test_target_dir_missing_default_option_uses_cwd(self) -> None:
        missing_target = self.base / "missing-default"
        original_resolve = Path.resolve

        def resolve_with_missing_failure(path: Path, *args, **kwargs) -> Path:
            if path == missing_target:
                raise FileNotFoundError("missing target")
            return original_resolve(path, *args, **kwargs)

        with patch(
            "file_organiser_python.organizer.Path.resolve",
            autospec=True,
            side_effect=resolve_with_missing_failure,
        ):
            with patch("builtins.input", return_value="2"):
                organizer = FileOrganizer(target_dir=missing_target)

        self.assertEqual(organizer.target_dir, Path.cwd())

    def test_target_dir_missing_invalid_input_exits(self) -> None:
        missing_target = self.base / "missing-invalid"
        original_resolve = Path.resolve

        def resolve_with_missing_failure(path: Path, *args, **kwargs) -> Path:
            if path == missing_target:
                raise FileNotFoundError("missing target")
            return original_resolve(path, *args, **kwargs)

        with patch(
            "file_organiser_python.organizer.Path.resolve",
            autospec=True,
            side_effect=resolve_with_missing_failure,
        ):
            with patch("builtins.input", return_value="x"):
                with self.assertRaises(SystemExit) as context:
                    FileOrganizer(target_dir=missing_target)

        self.assertEqual(context.exception.code, 1)

    def test_merge_extension_from_multiple_working_dirs(self) -> None:
        (self.work / "a.pdf").write_text("a", encoding="utf-8")
        (self.work2 / "b.pdf").write_text("b", encoding="utf-8")
        (self.work2 / "c.txt").write_text("c", encoding="utf-8")

        result = self.runner.invoke(
            app,
            [
                "merge",
                "--mode",
                "extension",
                "--extension",
                "pdf",
                "--working-dir",
                str(self.work),
                "--working-dir",
                str(self.work2),
                "--target-dir",
                str(self.out),
            ],
        )

        self.assertEqual(result.exit_code, 0)
        self.assertTrue((self.out / "PDF" / "a.pdf").exists())
        self.assertTrue((self.out / "PDF" / "b.pdf").exists())
        self.assertTrue((self.work2 / "c.txt").exists())

    def test_merge_date_from_multiple_working_dirs(self) -> None:
        target_date = "2026-03-01"
        expected_timestamp = datetime(2026, 3, 1, 12, 0, 0).timestamp()

        file_one = self.work / "a.txt"
        file_two = self.work2 / "b.txt"
        file_three = self.work2 / "old.txt"

        file_one.write_text("a", encoding="utf-8")
        file_two.write_text("b", encoding="utf-8")
        file_three.write_text("old", encoding="utf-8")

        os.utime(file_one, (expected_timestamp, expected_timestamp))
        os.utime(file_two, (expected_timestamp, expected_timestamp))

        old_timestamp = datetime(2025, 2, 1, 12, 0, 0).timestamp()
        os.utime(file_three, (old_timestamp, old_timestamp))

        organizer = FileOrganizer(
            target_dir=self.out,
            working_dirs=[self.work, self.work2],
            separate_choice=SeparateChoices.DATE,
            sort_date=target_date,
        )
        organizer.merge()

        self.assertTrue((self.out / target_date / "a.txt").exists())
        self.assertTrue((self.out / target_date / "b.txt").exists())
        self.assertTrue((self.work2 / "old.txt").exists())

    def test_merge_extension_and_date_from_multiple_working_dirs(self) -> None:
        target_date = "2026-03-01"
        expected_timestamp = datetime(2026, 3, 1, 8, 30, 0).timestamp()

        file_one = self.work / "image.jpg"
        file_two = self.work2 / "photo.jpg"
        file_three = self.work2 / "notes.txt"

        file_one.write_text("img", encoding="utf-8")
        file_two.write_text("img", encoding="utf-8")
        file_three.write_text("txt", encoding="utf-8")

        os.utime(file_one, (expected_timestamp, expected_timestamp))
        os.utime(file_two, (expected_timestamp, expected_timestamp))

        organizer = FileOrganizer(
            target_dir=self.out,
            working_dirs=[self.work, self.work2],
            separate_choice=SeparateChoices.EXTENSION_AND_DATE,
            sort_date=target_date,
            sort_extension=".jpg",
        )
        organizer.merge()

        self.assertTrue((self.out / target_date / "JPG" / "image.jpg").exists())
        self.assertTrue((self.out / target_date / "JPG" / "photo.jpg").exists())
        self.assertTrue((self.work2 / "notes.txt").exists())

    def test_merge_file_type_from_multiple_working_dirs(self) -> None:
        (self.work / "song.mp3").write_text("audio", encoding="utf-8")
        (self.work2 / "paper.pdf").write_text("doc", encoding="utf-8")

        organizer = FileOrganizer(
            target_dir=self.out,
            working_dirs=[self.work, self.work2],
            separate_choice=SeparateChoices.FILE,
        )
        organizer.merge()

        self.assertTrue((self.out / "AUDIO" / "song.mp3").exists())
        self.assertTrue((self.out / "DOCUMENTS" / "paper.pdf").exists())

    def test_separate_file_mode_with_file_type_category_filter(self) -> None:
        (self.work / "paper.pdf").write_text("doc", encoding="utf-8")
        (self.work / "song.mp3").write_text("audio", encoding="utf-8")

        result = self.runner.invoke(
            app,
            [
                "separate",
                "--mode",
                "file",
                "--file-type",
                "documents",
                "--working-dir",
                str(self.work),
                "--target-dir",
                str(self.out),
            ],
        )

        self.assertEqual(result.exit_code, 0)
        self.assertTrue((self.out / "DOCUMENTS" / "paper.pdf").exists())
        self.assertTrue((self.work / "song.mp3").exists())

    def test_separate_file_mode_with_file_type_extension_filter(self) -> None:
        (self.work / "invoice.pdf").write_text("doc", encoding="utf-8")
        (self.work / "notes.txt").write_text("txt", encoding="utf-8")

        organizer = FileOrganizer(
            target_dir=self.out,
            working_dir=self.work,
            separate_choice=SeparateChoices.FILE,
            file_type="pdf",
        )
        organizer.separate()

        self.assertTrue((self.out / "DOCUMENTS" / "invoice.pdf").exists())
        self.assertTrue((self.work / "notes.txt").exists())

    def test_separate_file_mode_with_invalid_file_type_filter(self) -> None:
        (self.work / "paper.pdf").write_text("doc", encoding="utf-8")

        result = self.runner.invoke(
            app,
            [
                "separate",
                "--mode",
                "file",
                "--file-type",
                "not-a-type",
                "--working-dir",
                str(self.work),
                "--target-dir",
                str(self.out),
            ],
        )

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Unsupported file type filter", result.output)
        self.assertTrue((self.work / "paper.pdf").exists())


if __name__ == "__main__":
    unittest.main()
