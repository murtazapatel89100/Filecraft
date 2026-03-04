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
