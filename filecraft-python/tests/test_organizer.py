import sys
import tempfile
import unittest
import os
from datetime import datetime
from pathlib import Path

from typer.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from file_organiser_python.main import app
from file_organiser_python.organizer import (
    FileOrganizer,
    MissingTargetDirectoryError,
    TargetPathNotDirectoryError,
)
from file_organiser_python.enums import SeparateChoices
from file_organiser_python.history import revert_history
from file_organiser_python.operations import _files_from_working_dirs


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

    def test_renameWith_prefix_handles_collision(self) -> None:
        (self.work / "a.txt").write_text("a", encoding="utf-8")
        (self.work / "b.txt").write_text("b", encoding="utf-8")
        (self.out / "invoice_1.txt").write_text("existing", encoding="utf-8")

        organizer = FileOrganizer(
            target_dir=self.out,
            working_dir=self.work,
            renameWith="invoice",
        )
        organizer.rename()

        self.assertTrue((self.out / "invoice_1_1.txt").exists())
        self.assertTrue((self.out / "invoice_2.txt").exists())

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

    def test_file_organizer_raises_for_missing_target_dir(self) -> None:
        missing_target = self.base / "missing-target"

        with self.assertRaises(MissingTargetDirectoryError):
            FileOrganizer(target_dir=missing_target)

    def test_file_organizer_raises_for_non_directory_target_path(self) -> None:
        target_file = self.base / "target.txt"
        target_file.write_text("x", encoding="utf-8")

        with self.assertRaises(TargetPathNotDirectoryError):
            FileOrganizer(target_dir=target_file)

    def test_file_organizer_allows_missing_target_dir_in_dry_run(self) -> None:
        missing_target = self.base / "missing-target-dry"

        organizer = FileOrganizer(target_dir=missing_target, dry_run=True)

        self.assertEqual(organizer.target_dir, missing_target.resolve())

    def test_cli_missing_target_dir_create_option_creates_directory(self) -> None:
        missing_target = self.base / "missing-create"

        result = self.runner.invoke(
            app,
            [
                "rename",
                "--working-dir",
                str(self.work),
                "--target-dir",
                str(missing_target),
            ],
            input="y\n",
        )

        self.assertEqual(result.exit_code, 0)
        self.assertTrue(missing_target.exists())
        self.assertIn("Created target directory", result.output)

    def test_cli_missing_target_dir_rejects_when_user_declines_options(self) -> None:
        missing_target = self.base / "missing-reject"

        result = self.runner.invoke(
            app,
            [
                "rename",
                "--working-dir",
                str(self.work),
                "--target-dir",
                str(missing_target),
            ],
            input="n\n",
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Target directory does not exist", result.output)

    def test_cli_dry_run_missing_target_dir_skips_prompt_and_creation(self) -> None:
        missing_target = self.base / "missing-target-dry-cli"

        result = self.runner.invoke(
            app,
            [
                "rename",
                "--working-dir",
                str(self.work),
                "--target-dir",
                str(missing_target),
                "--dry-run",
            ],
        )

        self.assertEqual(result.exit_code, 0)
        self.assertFalse(missing_target.exists())
        self.assertIn("[DRY RUN] Target directory does not exist", result.output)
        self.assertNotIn("Create it?", result.output)

    def test_cli_validates_working_dir_before_target_dir_prompt(self) -> None:
        missing_target = self.base / "missing-target"
        invalid_working_dir = self.base / "missing-work"

        result = self.runner.invoke(
            app,
            [
                "rename",
                "--working-dir",
                str(invalid_working_dir),
                "--target-dir",
                str(missing_target),
            ],
            input="y\n",
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Directory does not exist", result.output)
        self.assertNotIn("Create it?", result.output)

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

    def test_merge_file_type_with_category_filter(self) -> None:
        (self.work / "paper.pdf").write_text("doc", encoding="utf-8")
        (self.work2 / "song.mp3").write_text("audio", encoding="utf-8")
        (self.work2 / "notes.docx").write_text("doc2", encoding="utf-8")

        organizer = FileOrganizer(
            target_dir=self.out,
            working_dirs=[self.work, self.work2],
            separate_choice=SeparateChoices.FILE,
            file_type="documents",
        )
        organizer.merge()

        self.assertTrue((self.out / "DOCUMENTS" / "paper.pdf").exists())
        self.assertTrue((self.out / "DOCUMENTS" / "notes.docx").exists())
        self.assertTrue((self.work2 / "song.mp3").exists())

    def test_merge_file_type_with_extension_filter(self) -> None:
        (self.work / "invoice.pdf").write_text("doc", encoding="utf-8")
        (self.work2 / "notes.txt").write_text("txt", encoding="utf-8")
        (self.work2 / "report.pdf").write_text("doc2", encoding="utf-8")

        organizer = FileOrganizer(
            target_dir=self.out,
            working_dirs=[self.work, self.work2],
            separate_choice=SeparateChoices.FILE,
            file_type="pdf",
        )
        organizer.merge()

        self.assertTrue((self.out / "DOCUMENTS" / "invoice.pdf").exists())
        self.assertTrue((self.out / "DOCUMENTS" / "report.pdf").exists())
        self.assertTrue((self.work2 / "notes.txt").exists())

    def test_merge_file_type_with_invalid_filter(self) -> None:
        (self.work / "paper.pdf").write_text("doc", encoding="utf-8")

        result = self.runner.invoke(
            app,
            [
                "merge",
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

    def test_merge_file_type_cli_with_category_filter(self) -> None:
        (self.work / "photo.jpg").write_text("img", encoding="utf-8")
        (self.work2 / "song.mp3").write_text("audio", encoding="utf-8")

        result = self.runner.invoke(
            app,
            [
                "merge",
                "--mode",
                "file",
                "--file-type",
                "images",
                "--working-dir",
                str(self.work),
                "--working-dir",
                str(self.work2),
                "--target-dir",
                str(self.out),
            ],
        )

        self.assertEqual(result.exit_code, 0)
        self.assertTrue((self.out / "IMAGES" / "photo.jpg").exists())
        self.assertTrue((self.work2 / "song.mp3").exists())

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

    def test_separate_extension_recursive_finds_nested_files(self) -> None:
        nested = self.work / "nested"
        nested.mkdir(parents=True, exist_ok=True)
        (nested / "doc.pdf").write_text("pdf", encoding="utf-8")

        organizer = FileOrganizer(
            target_dir=self.out,
            working_dir=self.work,
            separate_choice=SeparateChoices.EXTENSION,
            sort_extension=".pdf",
            recursive=True,
        )
        organizer.separate()

        self.assertTrue((self.out / "PDF" / "doc.pdf").exists())

    def test_separate_extension_non_recursive_ignores_nested_files(self) -> None:
        nested = self.work / "nested"
        nested.mkdir(parents=True, exist_ok=True)
        (nested / "doc.pdf").write_text("pdf", encoding="utf-8")

        organizer = FileOrganizer(
            target_dir=self.out,
            working_dir=self.work,
            separate_choice=SeparateChoices.EXTENSION,
            sort_extension=".pdf",
        )
        organizer.separate()

        self.assertFalse((self.out / "PDF" / "doc.pdf").exists())
        self.assertTrue((nested / "doc.pdf").exists())

    def test_merge_recursive_across_multiple_working_dirs(self) -> None:
        nested_one = self.work / "a"
        nested_two = self.work2 / "b"
        nested_one.mkdir(parents=True, exist_ok=True)
        nested_two.mkdir(parents=True, exist_ok=True)

        (nested_one / "one.pdf").write_text("1", encoding="utf-8")
        (nested_two / "two.pdf").write_text("2", encoding="utf-8")

        organizer = FileOrganizer(
            target_dir=self.out,
            working_dirs=[self.work, self.work2],
            separate_choice=SeparateChoices.EXTENSION,
            sort_extension=".pdf",
            recursive=True,
        )
        organizer.merge()

        self.assertTrue((self.out / "PDF" / "one.pdf").exists())
        self.assertTrue((self.out / "PDF" / "two.pdf").exists())

    def test_separate_recursive_dry_run_does_not_move_files(self) -> None:
        nested = self.work / "nested"
        nested.mkdir(parents=True, exist_ok=True)
        file_path = nested / "dry.pdf"
        file_path.write_text("pdf", encoding="utf-8")

        result = self.runner.invoke(
            app,
            [
                "separate",
                "--mode",
                "extension",
                "--extension",
                "pdf",
                "--working-dir",
                str(self.work),
                "--target-dir",
                str(self.out),
                "--recursive",
                "--dry-run",
            ],
        )

        self.assertEqual(result.exit_code, 0)
        self.assertIn("[DRY RUN] Would move", result.output)
        self.assertTrue(file_path.exists())
        self.assertFalse((self.out / "PDF" / "dry.pdf").exists())

    def test_rename_recursive_excludes_target_subtree_within_working_dir(self) -> None:
        nested = self.work / "nested"
        nested.mkdir(parents=True, exist_ok=True)

        target_inside_work = self.work / "out"
        target_inside_work.mkdir(parents=True, exist_ok=True)
        (target_inside_work / "existing.txt").write_text("existing", encoding="utf-8")
        (target_inside_work / "archived" / "older.txt").parent.mkdir(
            parents=True, exist_ok=True
        )
        (target_inside_work / "archived" / "older.txt").write_text(
            "older", encoding="utf-8"
        )

        (nested / "source.txt").write_text("source", encoding="utf-8")

        organizer = FileOrganizer(
            target_dir=target_inside_work,
            working_dir=self.work,
            recursive=True,
            renameWith="doc",
        )
        organizer.rename()

        self.assertTrue((target_inside_work / "doc_1.txt").exists())
        self.assertTrue((target_inside_work / "existing.txt").exists())
        self.assertTrue((target_inside_work / "archived" / "older.txt").exists())

    def test_rename_recursive_sorts_by_basename_then_path(self) -> None:
        (self.work / "a").mkdir(parents=True, exist_ok=True)
        (self.work / "b").mkdir(parents=True, exist_ok=True)

        (self.work / "a" / "same.txt").write_text("from-a", encoding="utf-8")
        (self.work / "b" / "same.txt").write_text("from-b", encoding="utf-8")

        organizer = FileOrganizer(
            target_dir=self.out,
            working_dir=self.work,
            recursive=True,
            renameWith="order",
        )
        organizer.rename()

        self.assertEqual(
            (self.out / "order_1.txt").read_text(encoding="utf-8"),
            "from-a",
        )
        self.assertEqual(
            (self.out / "order_2.txt").read_text(encoding="utf-8"),
            "from-b",
        )

    def test_rename_recursive_target_equals_working_dir_processes_files(self) -> None:
        (self.work / "same.txt").write_text("x", encoding="utf-8")

        organizer = FileOrganizer(
            target_dir=self.work,
            working_dir=self.work,
            recursive=True,
        )
        organizer.rename()

        self.assertTrue((self.work / "1.txt").exists())

    def test_files_from_working_dirs_recursive_filters_non_regular_entries(
        self,
    ) -> None:
        if os.name == "nt" or not hasattr(os, "mkfifo"):
            self.skipTest("mkfifo not available on this platform")

        fifo_path = self.work / "named_pipe"
        os.mkfifo(fifo_path)
        regular_file = self.work / "a.txt"
        regular_file.write_text("a", encoding="utf-8")

        files = _files_from_working_dirs([self.work], recursive=True)

        self.assertIn(regular_file, files)
        self.assertNotIn(fifo_path, files)

    def test_merge_recursive_overlapping_working_dirs_avoids_duplicate_processing(
        self,
    ) -> None:
        nested = self.work / "nested"
        nested.mkdir(parents=True, exist_ok=True)
        (nested / "doc.pdf").write_text("pdf", encoding="utf-8")

        organizer = FileOrganizer(
            target_dir=self.out,
            working_dirs=[self.work, nested],
            separate_choice=SeparateChoices.EXTENSION,
            sort_extension=".pdf",
            recursive=True,
        )
        organizer.merge()

        self.assertTrue((self.out / "PDF" / "doc.pdf").exists())
        self.assertFalse((self.out / "PDF" / "doc_1.pdf").exists())

    def test_separate_extension_recursive_in_place_skips_already_sorted_file(
        self,
    ) -> None:
        sorted_dir = self.work / "PDF"
        sorted_dir.mkdir(parents=True, exist_ok=True)

        (sorted_dir / "doc.pdf").write_text("already-sorted", encoding="utf-8")
        (self.work / "doc.pdf").write_text("source", encoding="utf-8")

        organizer = FileOrganizer(
            target_dir=self.work,
            working_dir=self.work,
            separate_choice=SeparateChoices.EXTENSION,
            sort_extension=".pdf",
            recursive=True,
        )
        organizer.separate()

        self.assertTrue((sorted_dir / "doc.pdf").exists())
        self.assertTrue((sorted_dir / "doc_1.pdf").exists())
        self.assertFalse((sorted_dir / "doc_2.pdf").exists())

    def test_merge_extension_recursive_in_place_skips_already_sorted_file(
        self,
    ) -> None:
        sorted_dir = self.work / "PDF"
        sorted_dir.mkdir(parents=True, exist_ok=True)

        (sorted_dir / "doc.pdf").write_text("already-sorted", encoding="utf-8")
        nested = self.work / "nested"
        nested.mkdir(parents=True, exist_ok=True)
        (nested / "doc.pdf").write_text("source", encoding="utf-8")

        organizer = FileOrganizer(
            target_dir=self.work,
            working_dirs=[self.work],
            separate_choice=SeparateChoices.EXTENSION,
            sort_extension=".pdf",
            recursive=True,
        )
        organizer.merge()

        self.assertTrue((sorted_dir / "doc.pdf").exists())
        self.assertTrue((sorted_dir / "doc_1.pdf").exists())
        self.assertFalse((sorted_dir / "doc_2.pdf").exists())


if __name__ == "__main__":
    unittest.main()
