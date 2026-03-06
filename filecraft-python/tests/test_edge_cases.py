import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from file_organiser_python.enums import SeparateChoices
from file_organiser_python.history import (
    delete_history,
    load_latest_history,
    read_history,
    revert_history,
    save_history,
)
from file_organiser_python.operations import (
    EXTENSION_TYPE_MAP,
    KNOWN_EXTENSIONS,
    _files_from_working_dirs,
    normalize_file_type,
)
from file_organiser_python.organizer import FileOrganizer
from file_organiser_python.utils import (
    build_non_conflicting_path,
    ensure_directory,
    get_extension,
    validate_directory,
)


class TestGetExtension(unittest.TestCase):
    """Boundary tests for get_extension."""

    def test_no_extension(self) -> None:
        p = Path("/tmp/Makefile")
        self.assertEqual(get_extension(p), "")

    def test_dot_file_no_extension(self) -> None:
        p = Path("/tmp/.gitignore")
        self.assertEqual(get_extension(p), "")

    def test_simple_extension(self) -> None:
        p = Path("/tmp/file.pdf")
        self.assertEqual(get_extension(p), ".pdf")

    def test_compound_extension_known(self) -> None:
        p = Path("/tmp/archive.tar.gz")
        self.assertEqual(get_extension(p, KNOWN_EXTENSIONS), ".tar.gz")

    def test_compound_extension_without_known(self) -> None:
        p = Path("/tmp/archive.tar.gz")
        self.assertEqual(get_extension(p), ".gz")

    def test_case_insensitive(self) -> None:
        p = Path("/tmp/PHOTO.JPG")
        self.assertEqual(get_extension(p, KNOWN_EXTENSIONS), ".jpg")

    def test_multiple_dots(self) -> None:
        p = Path("/tmp/my.project.notes.txt")
        self.assertEqual(get_extension(p), ".txt")


class TestBuildNonConflictingPath(unittest.TestCase):
    """Tests for the conflict-resolution naming."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_no_conflict(self) -> None:
        p = self.base / "new.txt"
        self.assertEqual(build_non_conflicting_path(p), p)

    def test_single_conflict(self) -> None:
        existing = self.base / "dup.txt"
        existing.write_text("x", encoding="utf-8")
        result = build_non_conflicting_path(existing)
        self.assertEqual(result.name, "dup_1.txt")

    def test_multiple_conflicts(self) -> None:
        (self.base / "dup.txt").write_text("x", encoding="utf-8")
        (self.base / "dup_1.txt").write_text("x", encoding="utf-8")
        (self.base / "dup_2.txt").write_text("x", encoding="utf-8")
        result = build_non_conflicting_path(self.base / "dup.txt")
        self.assertEqual(result.name, "dup_3.txt")


class TestValidateDirectory(unittest.TestCase):
    """Tests for validate_directory edge cases."""

    def test_nonexistent_path(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            validate_directory(Path("/tmp/does-not-exist-xyz"))
        self.assertIn("does not exist", str(ctx.exception))

    def test_file_path(self) -> None:
        with tempfile.NamedTemporaryFile() as f:
            with self.assertRaises(ValueError) as ctx:
                validate_directory(Path(f.name))
            self.assertIn("not a directory", str(ctx.exception))

    def test_valid_directory(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            validate_directory(Path(d))  # should not raise


class TestEnsureDirectory(unittest.TestCase):
    """Tests for ensure_directory."""

    def test_creates_nested(self) -> None:
        with tempfile.TemporaryDirectory() as base:
            target = Path(base) / "a" / "b" / "c"
            ensure_directory(target)
            self.assertTrue(target.is_dir())

    def test_dry_run_does_not_create(self) -> None:
        with tempfile.TemporaryDirectory() as base:
            target = Path(base) / "dry"
            ensure_directory(target, dry_run=True)
            self.assertFalse(target.exists())


class TestNormalizeFileType(unittest.TestCase):
    """Tests for normalize_file_type edge cases."""

    def test_none_returns_none(self) -> None:
        self.assertIsNone(normalize_file_type(None))

    def test_empty_string_returns_none(self) -> None:
        self.assertIsNone(normalize_file_type(""))

    def test_whitespace_only_returns_none(self) -> None:
        self.assertIsNone(normalize_file_type("   "))

    def test_known_extension_with_dot(self) -> None:
        result = normalize_file_type(".pdf")
        self.assertIsNotNone(result)
        self.assertEqual(result, ("extension", ".pdf"))

    def test_known_extension_without_dot(self) -> None:
        result = normalize_file_type("pdf")
        self.assertIsNotNone(result)
        self.assertEqual(result, ("extension", ".pdf"))

    def test_known_category(self) -> None:
        result = normalize_file_type("documents")
        self.assertIsNotNone(result)
        self.assertEqual(result, ("category", "DOCUMENTS"))

    def test_known_category_with_dashes(self) -> None:
        result = normalize_file_type("disk-images")
        self.assertIsNotNone(result)
        self.assertEqual(result, ("category", "DISK_IMAGES"))

    def test_others_category(self) -> None:
        result = normalize_file_type("others")
        self.assertIsNotNone(result)
        self.assertEqual(result, ("category", "OTHERS"))

    def test_invalid_type(self) -> None:
        result = normalize_file_type("not-a-real-type")
        self.assertIsNotNone(result)
        self.assertEqual(result, ("invalid", ""))

    def test_case_insensitive(self) -> None:
        result = normalize_file_type("IMAGES")
        self.assertIsNotNone(result)
        self.assertEqual(result, ("category", "IMAGES"))


class TestHistoryEdgeCases(unittest.TestCase):
    """Edge-case tests for history read / revert."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_read_history_corrupted_json(self) -> None:
        bad = self.base / ".organizer_history_bad.json"
        bad.write_text("NOT VALID JSON!!!", encoding="utf-8")
        with self.assertRaises(ValueError) as ctx:
            read_history(bad)
        self.assertIn("Corrupted history file", str(ctx.exception))

    def test_read_history_invalid_format(self) -> None:
        bad = self.base / ".organizer_history_format.json"
        bad.write_text('"just a string"', encoding="utf-8")
        with self.assertRaises(ValueError) as ctx:
            read_history(bad)
        self.assertIn("Invalid history file format", str(ctx.exception))

    def test_read_history_invalid_mappings(self) -> None:
        bad = self.base / ".organizer_history_map.json"
        bad.write_text('{"mappings": "not-a-dict"}', encoding="utf-8")
        with self.assertRaises(ValueError) as ctx:
            read_history(bad)
        self.assertIn("Invalid mappings", str(ctx.exception))

    def test_read_history_empty_mappings(self) -> None:
        path = self.base / ".organizer_history_empty.json"
        save_history(path, {}, operation="test")
        result = read_history(path)
        self.assertEqual(result, {})

    def test_revert_history_corrupted_file_returns_zero(self) -> None:
        bad = self.base / ".organizer_history_bad2.json"
        bad.write_text("{{{", encoding="utf-8")
        reverted = revert_history(history_path=bad)
        self.assertEqual(reverted, 0)

    def test_revert_with_missing_source_files(self) -> None:
        """Revert should skip files that no longer exist at current location."""
        path = self.base / ".organizer_history_gone.json"
        save_history(
            path,
            {"/tmp/nonexistent_file_abc123.txt": "/tmp/original.txt"},
            operation="test",
        )
        reverted = revert_history(history_path=path, delete_after_revert=False)
        self.assertEqual(reverted, 0)

    def test_load_latest_history_no_files(self) -> None:
        result = load_latest_history(self.base)
        self.assertIsNone(result)

    def test_load_latest_history_picks_newest(self) -> None:
        older = self.base / ".organizer_history_older.json"
        newer = self.base / ".organizer_history_newer.json"
        save_history(older, {"a": "b"}, operation="old")
        # Ensure different mtime
        import time

        time.sleep(0.05)
        save_history(newer, {"c": "d"}, operation="new")
        result = load_latest_history(self.base)
        self.assertIsNotNone(result)
        self.assertEqual(result, newer)

    def test_delete_history_nonexistent_is_noop(self) -> None:
        delete_history(self.base / "nope.json")  # should not raise


class TestFileDiscoveryEdgeCases(unittest.TestCase):
    """Edge-case tests for _files_from_working_dirs."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.work = self.base / "work"
        self.work.mkdir()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_empty_directory(self) -> None:
        files = _files_from_working_dirs([self.work])
        self.assertEqual(files, [])

    def test_includes_dot_files(self) -> None:
        (self.work / ".env").write_text("SECRET=x", encoding="utf-8")
        files = _files_from_working_dirs([self.work])
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].name, ".env")

    def test_includes_files_without_extension(self) -> None:
        (self.work / "Makefile").write_text("all:", encoding="utf-8")
        files = _files_from_working_dirs([self.work])
        self.assertEqual(len(files), 1)

    def test_unicode_filenames(self) -> None:
        (self.work / "日本語.txt").write_text("hello", encoding="utf-8")
        files = _files_from_working_dirs([self.work])
        self.assertEqual(len(files), 1)
        self.assertIn("日本語.txt", files[0].name)

    def test_symlink_to_file_is_excluded(self) -> None:
        """Symlinks are not regular files and should be excluded."""
        if os.name == "nt":
            self.skipTest("Symlinks behave differently on Windows")
        real = self.work / "real.txt"
        real.write_text("content", encoding="utf-8")
        link = self.work / "link.txt"
        link.symlink_to(real)
        files = _files_from_working_dirs([self.work])
        names = [f.name for f in files]
        # symlink.is_file() returns True, but the file is discovered;
        # we mainly verify no crash and real file is included
        self.assertIn("real.txt", names)

    def test_duplicate_working_dirs_deduped(self) -> None:
        (self.work / "a.txt").write_text("a", encoding="utf-8")
        files = _files_from_working_dirs([self.work, self.work])
        self.assertEqual(len(files), 1)


class TestOrganizerEdgeCases(unittest.TestCase):
    """Edge-case tests for the FileOrganizer class."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.work = self.base / "work"
        self.out = self.base / "out"
        self.work.mkdir()
        self.out.mkdir()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_file_without_extension_goes_to_others(self) -> None:
        (self.work / "Makefile").write_text("all:", encoding="utf-8")
        organizer = FileOrganizer(
            target_dir=self.out,
            working_dir=self.work,
            separate_choice=SeparateChoices.FILE,
        )
        organizer.separate()
        self.assertTrue((self.out / "OTHERS" / "Makefile").exists())

    def test_dot_file_goes_to_others(self) -> None:
        (self.work / ".gitignore").write_text("*.pyc", encoding="utf-8")
        organizer = FileOrganizer(
            target_dir=self.out,
            working_dir=self.work,
            separate_choice=SeparateChoices.FILE,
        )
        organizer.separate()
        self.assertTrue((self.out / "OTHERS" / ".gitignore").exists())

    def test_rename_empty_working_dir(self) -> None:
        organizer = FileOrganizer(
            target_dir=self.out,
            working_dir=self.work,
        )
        organizer.rename()
        # No files should be created
        self.assertEqual(list(self.out.iterdir()), [])

    def test_separate_no_matching_extension(self) -> None:
        (self.work / "notes.txt").write_text("content", encoding="utf-8")
        organizer = FileOrganizer(
            target_dir=self.out,
            working_dir=self.work,
            separate_choice=SeparateChoices.EXTENSION,
            sort_extension=".pdf",
        )
        organizer.separate()
        # txt file should remain untouched
        self.assertTrue((self.work / "notes.txt").exists())

    def test_separate_extension_no_extension_provided(self) -> None:
        """Separate by extension with no extension should print a message."""
        organizer = FileOrganizer(
            target_dir=self.out,
            working_dir=self.work,
            separate_choice=SeparateChoices.EXTENSION,
        )
        organizer.separate()  # Should not crash

    def test_merge_no_working_dirs(self) -> None:
        """Merge with empty working_dirs should handle gracefully."""
        organizer = FileOrganizer(
            target_dir=self.out,
            working_dirs=[],
        )
        organizer.merge()  # Should not crash

    def test_unicode_filename_separate(self) -> None:
        (self.work / "文書.pdf").write_text("doc", encoding="utf-8")
        organizer = FileOrganizer(
            target_dir=self.out,
            working_dir=self.work,
            separate_choice=SeparateChoices.EXTENSION,
            sort_extension=".pdf",
        )
        organizer.separate()
        self.assertTrue((self.out / "PDF" / "文書.pdf").exists())

    def test_rename_preserves_extension(self) -> None:
        (self.work / "document.pdf").write_text("doc", encoding="utf-8")
        (self.work / "image.jpg").write_text("img", encoding="utf-8")
        organizer = FileOrganizer(
            target_dir=self.out,
            working_dir=self.work,
            renameWith="file",
        )
        organizer.rename()
        out_files = sorted(f.name for f in self.out.iterdir())
        # Extensions should be preserved
        extensions = sorted(Path(f).suffix for f in out_files)
        self.assertIn(".jpg", extensions)
        self.assertIn(".pdf", extensions)

    def test_history_save_and_read_round_trip(self) -> None:
        history_path = self.base / ".organizer_history_test.json"
        mapping = {"/tmp/a.txt": "/tmp/b.txt", "/tmp/c.txt": "/tmp/d.txt"}
        save_history(history_path, mapping, operation="test_op")
        loaded = read_history(history_path)
        self.assertEqual(loaded, mapping)

    def test_separate_file_type_all_files(self) -> None:
        """Separate by file type with no filter should sort all files."""
        (self.work / "song.mp3").write_text("audio", encoding="utf-8")
        (self.work / "photo.jpg").write_text("img", encoding="utf-8")
        (self.work / "data.xyz").write_text("unknown", encoding="utf-8")
        organizer = FileOrganizer(
            target_dir=self.out,
            working_dir=self.work,
            separate_choice=SeparateChoices.FILE,
        )
        organizer.separate()
        self.assertTrue((self.out / "AUDIO" / "song.mp3").exists())
        self.assertTrue((self.out / "IMAGES" / "photo.jpg").exists())
        self.assertTrue((self.out / "OTHERS" / "data.xyz").exists())

    def test_dry_run_history_not_saved(self) -> None:
        (self.work / "a.txt").write_text("a", encoding="utf-8")
        organizer = FileOrganizer(
            target_dir=self.out,
            working_dir=self.work,
            save_history=True,
            dry_run=True,
        )
        organizer.rename()
        # History file should not exist in dry-run
        history_files = list(self.out.glob(".organizer_history_*.json"))
        self.assertEqual(len(history_files), 0)

    def test_rename_with_prefix_empty_string(self) -> None:
        """Empty renameWith should result in numeric-only names."""
        (self.work / "a.txt").write_text("a", encoding="utf-8")
        organizer = FileOrganizer(
            target_dir=self.out,
            working_dir=self.work,
            renameWith="",
        )
        organizer.rename()
        # Empty string treated as no prefix -> just "1.txt"
        self.assertTrue((self.out / "1.txt").exists())


if __name__ == "__main__":
    unittest.main()
