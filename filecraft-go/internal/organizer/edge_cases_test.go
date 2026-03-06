package organizer

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestGetExtensionNoExtension(t *testing.T) {
	ext := getExtension("/tmp/Makefile", nil)
	if ext != "" {
		t.Fatalf("expected empty extension, got %q", ext)
	}
}

func TestGetExtensionDotFile(t *testing.T) {
	ext := getExtension("/tmp/.gitignore", nil)
	if ext != "" {
		t.Fatalf("expected empty extension for dotfile, got %q", ext)
	}
}

func TestGetExtensionCompoundKnown(t *testing.T) {
	ext := getExtension("/tmp/archive.tar.gz", knownExtensions)
	if ext != ".tar.gz" {
		t.Fatalf("expected .tar.gz, got %q", ext)
	}
}

func TestGetExtensionCaseInsensitive(t *testing.T) {
	ext := getExtension("/tmp/PHOTO.JPG", knownExtensions)
	if ext != ".jpg" {
		t.Fatalf("expected .jpg, got %q", ext)
	}
}

func TestGetExtensionMultipleDots(t *testing.T) {
	ext := getExtension("/tmp/my.project.notes.txt", knownExtensions)
	if ext != ".txt" {
		t.Fatalf("expected .txt, got %q", ext)
	}
}

// ---------------------------------------------------------------------------
// buildNonConflictingPath edge cases
// ---------------------------------------------------------------------------

func TestBuildNonConflictingPathNoConflict(t *testing.T) {
	base := t.TempDir()
	path := filepath.Join(base, "new.txt")
	result := buildNonConflictingPath(path)
	if result != path {
		t.Fatalf("expected %s, got %s", path, result)
	}
}

func TestBuildNonConflictingPathSingleConflict(t *testing.T) {
	base := t.TempDir()
	existing := filepath.Join(base, "dup.txt")
	mustWriteFile(t, existing, "x")
	result := buildNonConflictingPath(existing)
	expected := filepath.Join(base, "dup_1.txt")
	if result != expected {
		t.Fatalf("expected %s, got %s", expected, result)
	}
}

func TestBuildNonConflictingPathMultipleConflicts(t *testing.T) {
	base := t.TempDir()
	mustWriteFile(t, filepath.Join(base, "dup.txt"), "x")
	mustWriteFile(t, filepath.Join(base, "dup_1.txt"), "x")
	mustWriteFile(t, filepath.Join(base, "dup_2.txt"), "x")
	result := buildNonConflictingPath(filepath.Join(base, "dup.txt"))
	expected := filepath.Join(base, "dup_3.txt")
	if result != expected {
		t.Fatalf("expected %s, got %s", expected, result)
	}
}

// ---------------------------------------------------------------------------
// normalizeFileTypeFilter edge cases
// ---------------------------------------------------------------------------

func TestNormalizeFileTypeFilterEmpty(t *testing.T) {
	kind, _, valid := normalizeFileTypeFilter("")
	if !valid || kind != "" {
		t.Fatalf("expected valid empty filter, got kind=%q valid=%v", kind, valid)
	}
}

func TestNormalizeFileTypeFilterKnownExtension(t *testing.T) {
	kind, value, valid := normalizeFileTypeFilter("pdf")
	if !valid || kind != "extension" || value != ".pdf" {
		t.Fatalf("expected extension/.pdf, got %q/%q/%v", kind, value, valid)
	}
}

func TestNormalizeFileTypeFilterCategory(t *testing.T) {
	kind, value, valid := normalizeFileTypeFilter("documents")
	if !valid || kind != "category" || value != "DOCUMENTS" {
		t.Fatalf("expected category/DOCUMENTS, got %q/%q/%v", kind, value, valid)
	}
}

func TestNormalizeFileTypeFilterCategoryWithDash(t *testing.T) {
	kind, value, valid := normalizeFileTypeFilter("disk-images")
	if !valid || kind != "category" || value != "DISK_IMAGES" {
		t.Fatalf("expected category/DISK_IMAGES, got %q/%q/%v", kind, value, valid)
	}
}

func TestNormalizeFileTypeFilterOthers(t *testing.T) {
	kind, value, valid := normalizeFileTypeFilter("others")
	if !valid || kind != "category" || value != "OTHERS" {
		t.Fatalf("expected category/OTHERS, got %q/%q/%v", kind, value, valid)
	}
}

func TestNormalizeFileTypeFilterInvalid(t *testing.T) {
	_, _, valid := normalizeFileTypeFilter("not-a-real-type")
	if valid {
		t.Fatal("expected invalid filter")
	}
}

// ---------------------------------------------------------------------------
// History edge cases
// ---------------------------------------------------------------------------

func TestReadHistoryCorruptedJSON(t *testing.T) {
	base := t.TempDir()
	path := filepath.Join(base, ".organizer_history_bad.json")
	mustWriteFile(t, path, "NOT VALID JSON!!!")
	_, err := readHistory(path)
	if err == nil {
		t.Fatal("expected error for corrupted JSON")
	}
	if !strings.Contains(err.Error(), "corrupted history file") {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestReadHistoryEmptyMappings(t *testing.T) {
	base := t.TempDir()
	path := filepath.Join(base, ".organizer_history_empty.json")
	if err := SaveHistory(path, map[string]string{}, "test"); err != nil {
		t.Fatal(err)
	}
	result, err := readHistory(path)
	if err != nil {
		t.Fatal(err)
	}
	if len(result) != 0 {
		t.Fatalf("expected empty map, got %v", result)
	}
}

func TestRevertHistoryCorruptedFileReturnsZero(t *testing.T) {
	base := t.TempDir()
	path := filepath.Join(base, ".organizer_history_bad2.json")
	mustWriteFile(t, path, "{{{")
	var buf bytes.Buffer
	reverted, err := RevertHistory(path, "", false, false, &buf)
	if err == nil {
		t.Fatal("expected error for corrupted file")
	}
	if reverted != 0 {
		t.Fatalf("expected 0 reverted, got %d", reverted)
	}
}

func TestRevertWithMissingSourceFiles(t *testing.T) {
	base := t.TempDir()
	path := filepath.Join(base, ".organizer_history_gone.json")
	if err := SaveHistory(path, map[string]string{
		"/tmp/nonexistent_abc123.txt": "/tmp/original.txt",
	}, "test"); err != nil {
		t.Fatal(err)
	}
	var buf bytes.Buffer
	reverted, err := RevertHistory(path, "", false, false, &buf)
	if err != nil {
		t.Fatal(err)
	}
	if reverted != 0 {
		t.Fatalf("expected 0 reverted, got %d", reverted)
	}
}

func TestLoadLatestHistoryNoFiles(t *testing.T) {
	base := t.TempDir()
	result, err := LoadLatestHistory(base)
	if err != nil {
		t.Fatal(err)
	}
	if result != "" {
		t.Fatalf("expected empty, got %s", result)
	}
}

func TestLoadLatestHistoryPicksNewest(t *testing.T) {
	base := t.TempDir()
	older := filepath.Join(base, ".organizer_history_older.json")
	newer := filepath.Join(base, ".organizer_history_newer.json")
	if err := SaveHistory(older, map[string]string{"a": "b"}, "old"); err != nil {
		t.Fatal(err)
	}
	time.Sleep(50 * time.Millisecond)
	if err := SaveHistory(newer, map[string]string{"c": "d"}, "new"); err != nil {
		t.Fatal(err)
	}
	result, err := LoadLatestHistory(base)
	if err != nil {
		t.Fatal(err)
	}
	if result != newer {
		t.Fatalf("expected %s, got %s", newer, result)
	}
}

// ---------------------------------------------------------------------------
// File discovery edge cases
// ---------------------------------------------------------------------------

func TestFilesFromWorkingDirsEmptyDir(t *testing.T) {
	base := t.TempDir()
	work := filepath.Join(base, "work")
	if err := os.MkdirAll(work, 0o755); err != nil {
		t.Fatal(err)
	}
	files, err := filesFromWorkingDirs([]string{work}, false, nil)
	if err != nil {
		t.Fatal(err)
	}
	if len(files) != 0 {
		t.Fatalf("expected 0 files, got %d", len(files))
	}
}

func TestFilesFromWorkingDirsIncludesDotFiles(t *testing.T) {
	base := t.TempDir()
	work := filepath.Join(base, "work")
	mustWriteFile(t, filepath.Join(work, ".env"), "SECRET=x")
	files, err := filesFromWorkingDirs([]string{work}, false, nil)
	if err != nil {
		t.Fatal(err)
	}
	if len(files) != 1 {
		t.Fatalf("expected 1 file, got %d", len(files))
	}
}

func TestFilesFromWorkingDirsIncludesNoExtensionFiles(t *testing.T) {
	base := t.TempDir()
	work := filepath.Join(base, "work")
	mustWriteFile(t, filepath.Join(work, "Makefile"), "all:")
	files, err := filesFromWorkingDirs([]string{work}, false, nil)
	if err != nil {
		t.Fatal(err)
	}
	if len(files) != 1 {
		t.Fatalf("expected 1 file, got %d", len(files))
	}
}

func TestFilesFromWorkingDirsDuplicateDeduped(t *testing.T) {
	base := t.TempDir()
	work := filepath.Join(base, "work")
	mustWriteFile(t, filepath.Join(work, "a.txt"), "a")
	files, err := filesFromWorkingDirs([]string{work, work}, false, nil)
	if err != nil {
		t.Fatal(err)
	}
	if len(files) != 1 {
		t.Fatalf("expected 1 file, got %d", len(files))
	}
}

// ---------------------------------------------------------------------------
// Organizer edge cases
// ---------------------------------------------------------------------------

func TestFileWithoutExtensionGoesToOthers(t *testing.T) {
	base := t.TempDir()
	work := filepath.Join(base, "work")
	out := filepath.Join(base, "out")
	mustWriteFile(t, filepath.Join(work, "Makefile"), "all:")
	if err := os.MkdirAll(out, 0o755); err != nil {
		t.Fatal(err)
	}

	fo, err := NewFileOrganizer(Config{TargetDir: out, WorkingDir: work, Mode: ModeFile})
	if err != nil {
		t.Fatal(err)
	}
	var buf bytes.Buffer
	if err := fo.Separate(&buf); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(filepath.Join(out, "OTHERS", "Makefile")); err != nil {
		t.Fatalf("expected Makefile in OTHERS: %v", err)
	}
}

func TestDotFileGoesToOthers(t *testing.T) {
	base := t.TempDir()
	work := filepath.Join(base, "work")
	out := filepath.Join(base, "out")
	mustWriteFile(t, filepath.Join(work, ".gitignore"), "*.pyc")
	if err := os.MkdirAll(out, 0o755); err != nil {
		t.Fatal(err)
	}

	fo, err := NewFileOrganizer(Config{TargetDir: out, WorkingDir: work, Mode: ModeFile})
	if err != nil {
		t.Fatal(err)
	}
	var buf bytes.Buffer
	if err := fo.Separate(&buf); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(filepath.Join(out, "OTHERS", ".gitignore")); err != nil {
		t.Fatalf("expected .gitignore in OTHERS: %v", err)
	}
}

func TestRenameEmptyWorkingDir(t *testing.T) {
	base := t.TempDir()
	work := filepath.Join(base, "work")
	out := filepath.Join(base, "out")
	if err := os.MkdirAll(work, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(out, 0o755); err != nil {
		t.Fatal(err)
	}

	fo, err := NewFileOrganizer(Config{TargetDir: out, WorkingDir: work})
	if err != nil {
		t.Fatal(err)
	}
	var buf bytes.Buffer
	if err := fo.Rename(&buf); err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(buf.String(), "No files found") {
		t.Fatalf("expected no-files message, got: %s", buf.String())
	}
}

func TestSeparateNoMatchingExtension(t *testing.T) {
	base := t.TempDir()
	work := filepath.Join(base, "work")
	out := filepath.Join(base, "out")
	mustWriteFile(t, filepath.Join(work, "notes.txt"), "content")
	if err := os.MkdirAll(out, 0o755); err != nil {
		t.Fatal(err)
	}

	fo, err := NewFileOrganizer(Config{
		TargetDir:  out,
		WorkingDir: work,
		Mode:       ModeExtension,
		SortExt:    ".pdf",
	})
	if err != nil {
		t.Fatal(err)
	}
	var buf bytes.Buffer
	if err := fo.Separate(&buf); err != nil {
		t.Fatal(err)
	}
	// txt file should remain
	if _, err := os.Stat(filepath.Join(work, "notes.txt")); err != nil {
		t.Fatalf("expected notes.txt to remain: %v", err)
	}
}

func TestSeparateAllFileTypes(t *testing.T) {
	base := t.TempDir()
	work := filepath.Join(base, "work")
	out := filepath.Join(base, "out")
	mustWriteFile(t, filepath.Join(work, "song.mp3"), "audio")
	mustWriteFile(t, filepath.Join(work, "photo.jpg"), "img")
	mustWriteFile(t, filepath.Join(work, "data.xyz"), "unknown")
	if err := os.MkdirAll(out, 0o755); err != nil {
		t.Fatal(err)
	}

	fo, err := NewFileOrganizer(Config{TargetDir: out, WorkingDir: work, Mode: ModeFile})
	if err != nil {
		t.Fatal(err)
	}
	var buf bytes.Buffer
	if err := fo.Separate(&buf); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(filepath.Join(out, "AUDIO", "song.mp3")); err != nil {
		t.Fatalf("expected song.mp3 in AUDIO: %v", err)
	}
	if _, err := os.Stat(filepath.Join(out, "IMAGES", "photo.jpg")); err != nil {
		t.Fatalf("expected photo.jpg in IMAGES: %v", err)
	}
	if _, err := os.Stat(filepath.Join(out, "OTHERS", "data.xyz")); err != nil {
		t.Fatalf("expected data.xyz in OTHERS: %v", err)
	}
}

func TestDryRunHistoryNotSaved(t *testing.T) {
	base := t.TempDir()
	work := filepath.Join(base, "work")
	out := filepath.Join(base, "out")
	mustWriteFile(t, filepath.Join(work, "a.txt"), "a")
	if err := os.MkdirAll(out, 0o755); err != nil {
		t.Fatal(err)
	}

	fo, err := NewFileOrganizer(Config{
		TargetDir:   out,
		WorkingDir:  work,
		SaveHistory: true,
		DryRun:      true,
	})
	if err != nil {
		t.Fatal(err)
	}
	var buf bytes.Buffer
	if err := fo.Rename(&buf); err != nil {
		t.Fatal(err)
	}
	entries, _ := os.ReadDir(out)
	for _, e := range entries {
		if strings.HasPrefix(e.Name(), HistoryFilePrefix) {
			t.Fatalf("expected no history file in dry-run, found %s", e.Name())
		}
	}
}

func TestRenamePreservesExtension(t *testing.T) {
	base := t.TempDir()
	work := filepath.Join(base, "work")
	out := filepath.Join(base, "out")
	mustWriteFile(t, filepath.Join(work, "document.pdf"), "doc")
	mustWriteFile(t, filepath.Join(work, "image.jpg"), "img")
	if err := os.MkdirAll(out, 0o755); err != nil {
		t.Fatal(err)
	}

	fo, err := NewFileOrganizer(Config{
		TargetDir:  out,
		WorkingDir: work,
		RenameWith: "file",
	})
	if err != nil {
		t.Fatal(err)
	}
	var buf bytes.Buffer
	if err := fo.Rename(&buf); err != nil {
		t.Fatal(err)
	}
	// Should have file_1 and file_2 with original extensions
	entries, _ := os.ReadDir(out)
	exts := map[string]bool{}
	for _, e := range entries {
		exts[filepath.Ext(e.Name())] = true
	}
	if !exts[".pdf"] || !exts[".jpg"] {
		t.Fatalf("expected both .pdf and .jpg extensions preserved, got: %v", exts)
	}
}
