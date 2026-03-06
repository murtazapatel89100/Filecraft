package organizer

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func mustWriteFile(t *testing.T, path string, content string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatalf("mkdir failed: %v", err)
	}
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatalf("write failed: %v", err)
	}
}

func mustSetModTime(t *testing.T, path string, modTime time.Time) {
	t.Helper()
	if err := os.Chtimes(path, modTime, modTime); err != nil {
		t.Fatalf("chtimes failed: %v", err)
	}
}

func TestFileModeRoutesCompoundExtensionToArchives(t *testing.T) {
	base := t.TempDir()
	work := filepath.Join(base, "work")
	out := filepath.Join(base, "out")

	mustWriteFile(t, filepath.Join(work, "backup.tar.gz"), "x")
	if err := os.MkdirAll(out, 0o755); err != nil {
		t.Fatal(err)
	}

	fo, err := NewFileOrganizer(Config{TargetDir: out, WorkingDir: work, Mode: ModeFile})
	if err != nil {
		t.Fatal(err)
	}

	var outBuf bytes.Buffer
	if err := fo.Separate(&outBuf); err != nil {
		t.Fatal(err)
	}

	if _, err := os.Stat(filepath.Join(out, "ARCHIVES", "backup.tar.gz")); err != nil {
		t.Fatalf("expected archived file: %v", err)
	}
}

func TestRenameCollisionAndRevertRoundTrip(t *testing.T) {
	base := t.TempDir()
	work := filepath.Join(base, "work")
	out := filepath.Join(base, "out")

	mustWriteFile(t, filepath.Join(work, "a.txt"), "a")
	mustWriteFile(t, filepath.Join(out, "1.txt"), "existing")

	fo, err := NewFileOrganizer(Config{TargetDir: out, WorkingDir: work, SaveHistory: true})
	if err != nil {
		t.Fatal(err)
	}

	var outBuf bytes.Buffer
	if err := fo.Rename(&outBuf); err != nil {
		t.Fatal(err)
	}

	if _, err := os.Stat(filepath.Join(out, "1_1.txt")); err != nil {
		t.Fatalf("expected renamed collision file: %v", err)
	}

	historyPath := fo.HistoryPath()
	if historyPath == "" {
		t.Fatal("expected history path")
	}

	var revertBuf bytes.Buffer
	reverted, err := RevertHistory(historyPath, "", false, true, &revertBuf)
	if err != nil {
		t.Fatal(err)
	}

	if reverted != 1 {
		t.Fatalf("expected 1 reverted file, got %d", reverted)
	}

	if _, err := os.Stat(filepath.Join(work, "a.txt")); err != nil {
		t.Fatalf("expected original file restored: %v", err)
	}

	if _, err := os.Stat(filepath.Join(out, "1_1.txt")); !os.IsNotExist(err) {
		t.Fatalf("expected collision file removed, got err=%v", err)
	}

	if _, err := os.Stat(historyPath); !os.IsNotExist(err) {
		t.Fatalf("expected history file deleted, got err=%v", err)
	}
}

func TestRenameWithPrefixHandlesCollision(t *testing.T) {
	base := t.TempDir()
	work := filepath.Join(base, "work")
	out := filepath.Join(base, "out")

	mustWriteFile(t, filepath.Join(work, "a.txt"), "a")
	mustWriteFile(t, filepath.Join(work, "b.txt"), "b")
	mustWriteFile(t, filepath.Join(out, "invoice_1.txt"), "existing")

	fo, err := NewFileOrganizer(Config{TargetDir: out, WorkingDir: work, RenameWith: "invoice"})
	if err != nil {
		t.Fatal(err)
	}

	var outBuf bytes.Buffer
	if err := fo.Rename(&outBuf); err != nil {
		t.Fatal(err)
	}

	if _, err := os.Stat(filepath.Join(out, "invoice_1_1.txt")); err != nil {
		t.Fatalf("expected collision-safe prefixed file: %v", err)
	}
	if _, err := os.Stat(filepath.Join(out, "invoice_2.txt")); err != nil {
		t.Fatalf("expected second prefixed file: %v", err)
	}
}

func TestHistoryFilenameIsUniquePerRun(t *testing.T) {
	base := t.TempDir()
	out := filepath.Join(base, "out")
	if err := os.MkdirAll(out, 0o755); err != nil {
		t.Fatal(err)
	}

	fo1, err := NewFileOrganizer(Config{TargetDir: out, SaveHistory: true})
	if err != nil {
		t.Fatal(err)
	}

	time.Sleep(2 * time.Millisecond)

	fo2, err := NewFileOrganizer(Config{TargetDir: out, SaveHistory: true})
	if err != nil {
		t.Fatal(err)
	}

	if fo1.HistoryPath() == "" || fo2.HistoryPath() == "" {
		t.Fatal("history paths should not be empty")
	}

	if filepath.Base(fo1.HistoryPath()) == filepath.Base(fo2.HistoryPath()) {
		t.Fatal("history filenames should be unique")
	}
}

func TestMergeExtensionFromMultipleWorkingDirs(t *testing.T) {
	base := t.TempDir()
	work1 := filepath.Join(base, "work1")
	work2 := filepath.Join(base, "work2")
	out := filepath.Join(base, "out")

	mustWriteFile(t, filepath.Join(work1, "a.pdf"), "a")
	mustWriteFile(t, filepath.Join(work2, "b.pdf"), "b")
	mustWriteFile(t, filepath.Join(work2, "c.txt"), "c")

	fo, err := NewFileOrganizer(Config{
		TargetDir:   out,
		WorkingDirs: []string{work1, work2},
		Mode:        ModeExtension,
		SortExt:     ".pdf",
	})
	if err != nil {
		t.Fatal(err)
	}

	var outBuf bytes.Buffer
	if err := fo.Merge(&outBuf); err != nil {
		t.Fatal(err)
	}

	if _, err := os.Stat(filepath.Join(out, "PDF", "a.pdf")); err != nil {
		t.Fatalf("expected merged file a.pdf: %v", err)
	}
	if _, err := os.Stat(filepath.Join(out, "PDF", "b.pdf")); err != nil {
		t.Fatalf("expected merged file b.pdf: %v", err)
	}
	if _, err := os.Stat(filepath.Join(work2, "c.txt")); err != nil {
		t.Fatalf("expected c.txt untouched: %v", err)
	}
}

func TestMergeDateFromMultipleWorkingDirs(t *testing.T) {
	base := t.TempDir()
	work1 := filepath.Join(base, "work1")
	work2 := filepath.Join(base, "work2")
	out := filepath.Join(base, "out")

	dateValue := "2026-03-01"
	targetTime := time.Date(2026, 3, 1, 12, 0, 0, 0, time.Local)
	oldTime := time.Date(2025, 2, 1, 12, 0, 0, 0, time.Local)

	fileA := filepath.Join(work1, "a.txt")
	fileB := filepath.Join(work2, "b.txt")
	fileOld := filepath.Join(work2, "old.txt")

	mustWriteFile(t, fileA, "a")
	mustWriteFile(t, fileB, "b")
	mustWriteFile(t, fileOld, "old")

	mustSetModTime(t, fileA, targetTime)
	mustSetModTime(t, fileB, targetTime)
	mustSetModTime(t, fileOld, oldTime)

	fo, err := NewFileOrganizer(Config{
		TargetDir:   out,
		WorkingDirs: []string{work1, work2},
		Mode:        ModeDate,
		SortDate:    dateValue,
	})
	if err != nil {
		t.Fatal(err)
	}

	var outBuf bytes.Buffer
	if err := fo.Merge(&outBuf); err != nil {
		t.Fatal(err)
	}

	if _, err := os.Stat(filepath.Join(out, dateValue, "a.txt")); err != nil {
		t.Fatalf("expected a.txt merged by date: %v", err)
	}
	if _, err := os.Stat(filepath.Join(out, dateValue, "b.txt")); err != nil {
		t.Fatalf("expected b.txt merged by date: %v", err)
	}
	if _, err := os.Stat(fileOld); err != nil {
		t.Fatalf("expected old.txt untouched: %v", err)
	}
}

func TestMergeExtensionAndDateFromMultipleWorkingDirs(t *testing.T) {
	base := t.TempDir()
	work1 := filepath.Join(base, "work1")
	work2 := filepath.Join(base, "work2")
	out := filepath.Join(base, "out")

	dateValue := "2026-03-01"
	targetTime := time.Date(2026, 3, 1, 8, 30, 0, 0, time.Local)

	fileA := filepath.Join(work1, "image.jpg")
	fileB := filepath.Join(work2, "photo.jpg")
	fileTxt := filepath.Join(work2, "notes.txt")

	mustWriteFile(t, fileA, "img")
	mustWriteFile(t, fileB, "img")
	mustWriteFile(t, fileTxt, "txt")

	mustSetModTime(t, fileA, targetTime)
	mustSetModTime(t, fileB, targetTime)

	fo, err := NewFileOrganizer(Config{
		TargetDir:   out,
		WorkingDirs: []string{work1, work2},
		Mode:        ModeExtensionAndDate,
		SortDate:    dateValue,
		SortExt:     ".jpg",
	})
	if err != nil {
		t.Fatal(err)
	}

	var outBuf bytes.Buffer
	if err := fo.Merge(&outBuf); err != nil {
		t.Fatal(err)
	}

	if _, err := os.Stat(filepath.Join(out, dateValue, "JPG", "image.jpg")); err != nil {
		t.Fatalf("expected image.jpg merged by extension and date: %v", err)
	}
	if _, err := os.Stat(filepath.Join(out, dateValue, "JPG", "photo.jpg")); err != nil {
		t.Fatalf("expected photo.jpg merged by extension and date: %v", err)
	}
	if _, err := os.Stat(fileTxt); err != nil {
		t.Fatalf("expected notes.txt untouched: %v", err)
	}
}

func TestMergeFileTypeFromMultipleWorkingDirs(t *testing.T) {
	base := t.TempDir()
	work1 := filepath.Join(base, "work1")
	work2 := filepath.Join(base, "work2")
	out := filepath.Join(base, "out")

	mustWriteFile(t, filepath.Join(work1, "song.mp3"), "audio")
	mustWriteFile(t, filepath.Join(work2, "paper.pdf"), "doc")

	fo, err := NewFileOrganizer(Config{
		TargetDir:   out,
		WorkingDirs: []string{work1, work2},
		Mode:        ModeFile,
	})
	if err != nil {
		t.Fatal(err)
	}

	var outBuf bytes.Buffer
	if err := fo.Merge(&outBuf); err != nil {
		t.Fatal(err)
	}

	if _, err := os.Stat(filepath.Join(out, "AUDIO", "song.mp3")); err != nil {
		t.Fatalf("expected audio file merged to AUDIO: %v", err)
	}
	if _, err := os.Stat(filepath.Join(out, "DOCUMENTS", "paper.pdf")); err != nil {
		t.Fatalf("expected pdf file merged to DOCUMENTS: %v", err)
	}
}

func TestSeparateExtensionRecursiveFindsNestedFiles(t *testing.T) {
	base := t.TempDir()
	work := filepath.Join(base, "work")
	out := filepath.Join(base, "out")

	mustWriteFile(t, filepath.Join(work, "nested", "doc.pdf"), "pdf")

	fo, err := NewFileOrganizer(Config{
		TargetDir:  out,
		WorkingDir: work,
		Mode:       ModeExtension,
		SortExt:    ".pdf",
		Recursive:  true,
	})
	if err != nil {
		t.Fatal(err)
	}

	var outBuf bytes.Buffer
	if err := fo.Separate(&outBuf); err != nil {
		t.Fatal(err)
	}

	if _, err := os.Stat(filepath.Join(out, "PDF", "doc.pdf")); err != nil {
		t.Fatalf("expected nested pdf to be separated with recursive mode: %v", err)
	}
}

func TestSeparateExtensionNonRecursiveIgnoresNestedFiles(t *testing.T) {
	base := t.TempDir()
	work := filepath.Join(base, "work")
	out := filepath.Join(base, "out")

	mustWriteFile(t, filepath.Join(work, "nested", "doc.pdf"), "pdf")

	fo, err := NewFileOrganizer(Config{
		TargetDir:  out,
		WorkingDir: work,
		Mode:       ModeExtension,
		SortExt:    ".pdf",
	})
	if err != nil {
		t.Fatal(err)
	}

	var outBuf bytes.Buffer
	if err := fo.Separate(&outBuf); err != nil {
		t.Fatal(err)
	}

	if _, err := os.Stat(filepath.Join(out, "PDF", "doc.pdf")); !os.IsNotExist(err) {
		t.Fatalf("expected nested pdf to remain untouched without recursive mode: %v", err)
	}
	if _, err := os.Stat(filepath.Join(work, "nested", "doc.pdf")); err != nil {
		t.Fatalf("expected original nested file to remain: %v", err)
	}
}

func TestMergeRecursiveAcrossMultipleWorkingDirs(t *testing.T) {
	base := t.TempDir()
	work1 := filepath.Join(base, "work1")
	work2 := filepath.Join(base, "work2")
	out := filepath.Join(base, "out")

	mustWriteFile(t, filepath.Join(work1, "a", "one.pdf"), "1")
	mustWriteFile(t, filepath.Join(work2, "b", "two.pdf"), "2")

	fo, err := NewFileOrganizer(Config{
		TargetDir:   out,
		WorkingDirs: []string{work1, work2},
		Mode:        ModeExtension,
		SortExt:     ".pdf",
		Recursive:   true,
	})
	if err != nil {
		t.Fatal(err)
	}

	var outBuf bytes.Buffer
	if err := fo.Merge(&outBuf); err != nil {
		t.Fatal(err)
	}

	if _, err := os.Stat(filepath.Join(out, "PDF", "one.pdf")); err != nil {
		t.Fatalf("expected first nested file merged recursively: %v", err)
	}
	if _, err := os.Stat(filepath.Join(out, "PDF", "two.pdf")); err != nil {
		t.Fatalf("expected second nested file merged recursively: %v", err)
	}
}

func TestSeparateRecursiveDryRunDoesNotMoveFiles(t *testing.T) {
	base := t.TempDir()
	work := filepath.Join(base, "work")
	out := filepath.Join(base, "out")

	mustWriteFile(t, filepath.Join(work, "nested", "dry.pdf"), "pdf")

	fo, err := NewFileOrganizer(Config{
		TargetDir:  out,
		WorkingDir: work,
		Mode:       ModeExtension,
		SortExt:    ".pdf",
		Recursive:  true,
		DryRun:     true,
	})
	if err != nil {
		t.Fatal(err)
	}

	var outBuf bytes.Buffer
	if err := fo.Separate(&outBuf); err != nil {
		t.Fatal(err)
	}

	if !strings.Contains(outBuf.String(), "[DRY RUN] Would move") {
		t.Fatalf("expected dry-run output, got: %s", outBuf.String())
	}
	if _, err := os.Stat(filepath.Join(work, "nested", "dry.pdf")); err != nil {
		t.Fatalf("expected nested file to remain in place during dry run: %v", err)
	}
	if _, err := os.Stat(filepath.Join(out, "PDF", "dry.pdf")); !os.IsNotExist(err) {
		t.Fatalf("expected no moved output file during dry run: %v", err)
	}
}

func TestRenameRecursiveExcludesTargetSubtreeWithinWorkingDir(t *testing.T) {
	base := t.TempDir()
	work := filepath.Join(base, "work")
	targetInsideWork := filepath.Join(work, "out")

	mustWriteFile(t, filepath.Join(work, "nested", "source.txt"), "source")
	mustWriteFile(t, filepath.Join(targetInsideWork, "existing.txt"), "existing")
	mustWriteFile(t, filepath.Join(targetInsideWork, "archived", "older.txt"), "older")

	fo, err := NewFileOrganizer(Config{
		TargetDir:  targetInsideWork,
		WorkingDir: work,
		Recursive:  true,
		RenameWith: "doc",
	})
	if err != nil {
		t.Fatal(err)
	}

	var outBuf bytes.Buffer
	if err := fo.Rename(&outBuf); err != nil {
		t.Fatal(err)
	}

	if _, err := os.Stat(filepath.Join(targetInsideWork, "doc_1.txt")); err != nil {
		t.Fatalf("expected source file renamed into target: %v", err)
	}
	if _, err := os.Stat(filepath.Join(targetInsideWork, "existing.txt")); err != nil {
		t.Fatalf("expected existing target file to remain untouched: %v", err)
	}
	if _, err := os.Stat(filepath.Join(targetInsideWork, "archived", "older.txt")); err != nil {
		t.Fatalf("expected nested target file to remain untouched: %v", err)
	}
}

func TestRenameRecursiveSortsByBasenameThenPath(t *testing.T) {
	base := t.TempDir()
	work := filepath.Join(base, "work")
	out := filepath.Join(base, "out")
	if err := os.MkdirAll(out, 0o755); err != nil {
		t.Fatal(err)
	}

	mustWriteFile(t, filepath.Join(work, "a", "same.txt"), "from-a")
	mustWriteFile(t, filepath.Join(work, "b", "same.txt"), "from-b")

	fo, err := NewFileOrganizer(Config{
		TargetDir:  out,
		WorkingDir: work,
		Recursive:  true,
		RenameWith: "order",
	})
	if err != nil {
		t.Fatal(err)
	}

	var outBuf bytes.Buffer
	if err := fo.Rename(&outBuf); err != nil {
		t.Fatal(err)
	}

	firstContent, err := os.ReadFile(filepath.Join(out, "order_1.txt"))
	if err != nil {
		t.Fatalf("expected first renamed output file: %v", err)
	}
	secondContent, err := os.ReadFile(filepath.Join(out, "order_2.txt"))
	if err != nil {
		t.Fatalf("expected second renamed output file: %v", err)
	}

	if string(firstContent) != "from-a" {
		t.Fatalf("expected order_1.txt from directory a, got %q", string(firstContent))
	}
	if string(secondContent) != "from-b" {
		t.Fatalf("expected order_2.txt from directory b, got %q", string(secondContent))
	}
}

func TestRenameRecursiveDoesNotSkipRootWhenTargetEqualsWorkingDir(t *testing.T) {
	base := t.TempDir()
	work := filepath.Join(base, "work")

	mustWriteFile(t, filepath.Join(work, "keep.txt"), "content")

	fo, err := NewFileOrganizer(Config{
		TargetDir:  work,
		WorkingDir: work,
		Recursive:  true,
	})
	if err != nil {
		t.Fatal(err)
	}

	var outBuf bytes.Buffer
	if err := fo.Rename(&outBuf); err != nil {
		t.Fatal(err)
	}

	if _, err := os.Stat(filepath.Join(work, "1.txt")); err != nil {
		t.Fatalf("expected file to be processed when target equals working dir in recursive mode: %v", err)
	}
}

func TestMergeRecursiveOverlappingWorkingDirsAvoidsDuplicateProcessing(t *testing.T) {
	base := t.TempDir()
	work := filepath.Join(base, "work")
	nested := filepath.Join(work, "nested")
	out := filepath.Join(base, "out")

	mustWriteFile(t, filepath.Join(nested, "doc.pdf"), "pdf")

	fo, err := NewFileOrganizer(Config{
		TargetDir:   out,
		WorkingDirs: []string{work, nested},
		Mode:        ModeExtension,
		SortExt:     ".pdf",
		Recursive:   true,
	})
	if err != nil {
		t.Fatal(err)
	}

	var outBuf bytes.Buffer
	if err := fo.Merge(&outBuf); err != nil {
		t.Fatal(err)
	}

	if _, err := os.Stat(filepath.Join(out, "PDF", "doc.pdf")); err != nil {
		t.Fatalf("expected merged file once: %v", err)
	}
	if _, err := os.Stat(filepath.Join(out, "PDF", "doc_1.pdf")); !os.IsNotExist(err) {
		t.Fatalf("expected no duplicate merge output: %v", err)
	}
}

func TestSeparateExtensionRecursiveInPlaceSkipsAlreadySortedFile(t *testing.T) {
	base := t.TempDir()
	work := filepath.Join(base, "work")
	sortedDir := filepath.Join(work, "PDF")

	mustWriteFile(t, filepath.Join(sortedDir, "doc.pdf"), "already-sorted")
	mustWriteFile(t, filepath.Join(work, "doc.pdf"), "source")

	fo, err := NewFileOrganizer(Config{
		TargetDir:  work,
		WorkingDir: work,
		Mode:       ModeExtension,
		SortExt:    ".pdf",
		Recursive:  true,
	})
	if err != nil {
		t.Fatal(err)
	}

	var outBuf bytes.Buffer
	if err := fo.Separate(&outBuf); err != nil {
		t.Fatal(err)
	}

	if _, err := os.Stat(filepath.Join(sortedDir, "doc.pdf")); err != nil {
		t.Fatalf("expected already sorted file to remain: %v", err)
	}
	if _, err := os.Stat(filepath.Join(sortedDir, "doc_1.pdf")); err != nil {
		t.Fatalf("expected source file moved with one suffix: %v", err)
	}
	if _, err := os.Stat(filepath.Join(sortedDir, "doc_2.pdf")); !os.IsNotExist(err) {
		t.Fatalf("expected no extra self-conflict rename: %v", err)
	}
}

func TestMergeExtensionRecursiveInPlaceSkipsAlreadySortedFile(t *testing.T) {
	base := t.TempDir()
	work := filepath.Join(base, "work")
	sortedDir := filepath.Join(work, "PDF")

	mustWriteFile(t, filepath.Join(sortedDir, "doc.pdf"), "already-sorted")
	mustWriteFile(t, filepath.Join(work, "nested", "doc.pdf"), "source")

	fo, err := NewFileOrganizer(Config{
		TargetDir:   work,
		WorkingDirs: []string{work},
		Mode:        ModeExtension,
		SortExt:     ".pdf",
		Recursive:   true,
	})
	if err != nil {
		t.Fatal(err)
	}

	var outBuf bytes.Buffer
	if err := fo.Merge(&outBuf); err != nil {
		t.Fatal(err)
	}

	if _, err := os.Stat(filepath.Join(sortedDir, "doc.pdf")); err != nil {
		t.Fatalf("expected already sorted file to remain: %v", err)
	}
	if _, err := os.Stat(filepath.Join(sortedDir, "doc_1.pdf")); err != nil {
		t.Fatalf("expected source file merged with one suffix: %v", err)
	}
	if _, err := os.Stat(filepath.Join(sortedDir, "doc_2.pdf")); !os.IsNotExist(err) {
		t.Fatalf("expected no extra self-conflict rename: %v", err)
	}
}

func TestSeparateFileTypeWithCategoryFilter(t *testing.T) {
	base := t.TempDir()
	work := filepath.Join(base, "work")
	out := filepath.Join(base, "out")

	mustWriteFile(t, filepath.Join(work, "paper.pdf"), "doc")
	mustWriteFile(t, filepath.Join(work, "song.mp3"), "audio")

	fo, err := NewFileOrganizer(Config{
		TargetDir:  out,
		WorkingDir: work,
		Mode:       ModeFile,
		FileType:   "documents",
	})
	if err != nil {
		t.Fatal(err)
	}

	var outBuf bytes.Buffer
	if err := fo.Separate(&outBuf); err != nil {
		t.Fatal(err)
	}

	if _, err := os.Stat(filepath.Join(out, "DOCUMENTS", "paper.pdf")); err != nil {
		t.Fatalf("expected pdf moved to DOCUMENTS: %v", err)
	}
	if _, err := os.Stat(filepath.Join(work, "song.mp3")); err != nil {
		t.Fatalf("expected song.mp3 to remain in work dir: %v", err)
	}
}

func TestSeparateFileTypeWithExtensionFilter(t *testing.T) {
	base := t.TempDir()
	work := filepath.Join(base, "work")
	out := filepath.Join(base, "out")

	mustWriteFile(t, filepath.Join(work, "invoice.pdf"), "doc")
	mustWriteFile(t, filepath.Join(work, "notes.txt"), "txt")

	fo, err := NewFileOrganizer(Config{
		TargetDir:  out,
		WorkingDir: work,
		Mode:       ModeFile,
		FileType:   "pdf",
	})
	if err != nil {
		t.Fatal(err)
	}

	var outBuf bytes.Buffer
	if err := fo.Separate(&outBuf); err != nil {
		t.Fatal(err)
	}

	if _, err := os.Stat(filepath.Join(out, "DOCUMENTS", "invoice.pdf")); err != nil {
		t.Fatalf("expected invoice.pdf moved to DOCUMENTS: %v", err)
	}
	if _, err := os.Stat(filepath.Join(work, "notes.txt")); err != nil {
		t.Fatalf("expected notes.txt to remain in work dir: %v", err)
	}
}

func TestSeparateFileTypeWithInvalidFilter(t *testing.T) {
	base := t.TempDir()
	work := filepath.Join(base, "work")
	out := filepath.Join(base, "out")

	mustWriteFile(t, filepath.Join(work, "paper.pdf"), "doc")

	fo, err := NewFileOrganizer(Config{
		TargetDir:  out,
		WorkingDir: work,
		Mode:       ModeFile,
		FileType:   "not-a-type",
	})
	if err != nil {
		t.Fatal(err)
	}

	var outBuf bytes.Buffer
	if err := fo.Separate(&outBuf); err != nil {
		t.Fatal(err)
	}

	if _, err := os.Stat(filepath.Join(work, "paper.pdf")); err != nil {
		t.Fatalf("expected paper.pdf to remain in work dir: %v", err)
	}
	if !strings.Contains(outBuf.String(), "Unsupported file type filter") {
		t.Fatalf("expected unsupported file type message, got: %s", outBuf.String())
	}
}
