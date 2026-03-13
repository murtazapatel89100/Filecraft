package cmd

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestSeparateInvalidDateReturnsError(t *testing.T) {
	root := NewRootCmd()
	buf := &bytes.Buffer{}
	root.SetOut(buf)
	root.SetErr(buf)
	root.SetArgs([]string{
		"separate",
		"--mode", "date",
		"--date", "bad-date",
	})

	err := root.Execute()
	if err == nil {
		t.Fatal("expected command to fail")
	}

	if !strings.Contains(strings.ToLower(err.Error()), "yyyy-mm-dd") {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestSeparateFileModeWithFileTypeCategoryFilter(t *testing.T) {
	base := t.TempDir()
	work := filepath.Join(base, "work")
	out := filepath.Join(base, "out")

	if err := os.MkdirAll(work, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(out, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(work, "paper.pdf"), []byte("doc"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(work, "song.mp3"), []byte("audio"), 0o644); err != nil {
		t.Fatal(err)
	}

	root := NewRootCmd()
	buf := &bytes.Buffer{}
	root.SetOut(buf)
	root.SetErr(buf)
	root.SetArgs([]string{
		"separate",
		"--mode", "file",
		"--file-type", "documents",
		"--working-dir", work,
		"--target-dir", out,
	})

	if err := root.Execute(); err != nil {
		t.Fatalf("expected command to succeed, got: %v", err)
	}

	if _, err := os.Stat(filepath.Join(out, "DOCUMENTS", "paper.pdf")); err != nil {
		t.Fatalf("expected paper.pdf moved to DOCUMENTS: %v", err)
	}
	if _, err := os.Stat(filepath.Join(work, "song.mp3")); err != nil {
		t.Fatalf("expected song.mp3 unchanged: %v", err)
	}
}

func TestSeparateFileModeWithInvalidFileTypeFilter(t *testing.T) {
	base := t.TempDir()
	work := filepath.Join(base, "work")
	out := filepath.Join(base, "out")

	if err := os.MkdirAll(work, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(out, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(work, "paper.pdf"), []byte("doc"), 0o644); err != nil {
		t.Fatal(err)
	}

	root := NewRootCmd()
	buf := &bytes.Buffer{}
	root.SetOut(buf)
	root.SetErr(buf)
	root.SetArgs([]string{
		"separate",
		"--mode", "file",
		"--file-type", "not-a-type",
		"--working-dir", work,
		"--target-dir", out,
	})

	if err := root.Execute(); err != nil {
		t.Fatalf("expected command to succeed, got: %v", err)
	}

	if !strings.Contains(buf.String(), "Unsupported file type filter") {
		t.Fatalf("expected unsupported file type message, got: %s", buf.String())
	}
	if _, err := os.Stat(filepath.Join(work, "paper.pdf")); err != nil {
		t.Fatalf("expected paper.pdf unchanged: %v", err)
	}
}

func TestSeparateValidatesWorkingDirBeforeTargetPrompt(t *testing.T) {
	base := t.TempDir()
	target := filepath.Join(base, "missing-target")
	invalidWorking := filepath.Join(base, "missing-work")

	root := NewRootCmd()
	buf := &bytes.Buffer{}
	root.SetOut(buf)
	root.SetErr(buf)
	root.SetIn(strings.NewReader("y\n"))
	root.SetArgs([]string{
		"separate",
		"--mode", "file",
		"--working-dir", invalidWorking,
		"--target-dir", target,
	})

	err := root.Execute()
	if err == nil {
		t.Fatal("expected command to fail")
	}
	if !strings.Contains(err.Error(), "--working-dir: directory does not exist") {
		t.Fatalf("unexpected error: %v", err)
	}
	if strings.Contains(buf.String(), "Target directory '") {
		t.Fatalf("did not expect target prompt output, got: %s", buf.String())
	}
}

func TestMergeFileModeWithFileTypeCategoryFilter(t *testing.T) {
	base := t.TempDir()
	work1 := filepath.Join(base, "work1")
	work2 := filepath.Join(base, "work2")
	out := filepath.Join(base, "out")

	if err := os.MkdirAll(work1, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(work2, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(out, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(work1, "photo.jpg"), []byte("img"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(work2, "song.mp3"), []byte("audio"), 0o644); err != nil {
		t.Fatal(err)
	}

	root := NewRootCmd()
	buf := &bytes.Buffer{}
	root.SetOut(buf)
	root.SetErr(buf)
	root.SetArgs([]string{
		"merge",
		"--mode", "file",
		"--file-type", "images",
		"--working-dir", work1,
		"--working-dir", work2,
		"--target-dir", out,
	})

	if err := root.Execute(); err != nil {
		t.Fatalf("expected command to succeed, got: %v", err)
	}

	if _, err := os.Stat(filepath.Join(out, "IMAGES", "photo.jpg")); err != nil {
		t.Fatalf("expected photo.jpg moved to IMAGES: %v", err)
	}
	if _, err := os.Stat(filepath.Join(work2, "song.mp3")); err != nil {
		t.Fatalf("expected song.mp3 unchanged: %v", err)
	}
}

func TestMergeFileModeWithInvalidFileTypeFilter(t *testing.T) {
	base := t.TempDir()
	work := filepath.Join(base, "work")
	out := filepath.Join(base, "out")

	if err := os.MkdirAll(work, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(out, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(work, "paper.pdf"), []byte("doc"), 0o644); err != nil {
		t.Fatal(err)
	}

	root := NewRootCmd()
	buf := &bytes.Buffer{}
	root.SetOut(buf)
	root.SetErr(buf)
	root.SetArgs([]string{
		"merge",
		"--mode", "file",
		"--file-type", "not-a-type",
		"--working-dir", work,
		"--target-dir", out,
	})

	if err := root.Execute(); err != nil {
		t.Fatalf("expected command to succeed, got: %v", err)
	}

	if !strings.Contains(buf.String(), "Unsupported file type filter") {
		t.Fatalf("expected unsupported file type message, got: %s", buf.String())
	}
	if _, err := os.Stat(filepath.Join(work, "paper.pdf")); err != nil {
		t.Fatalf("expected paper.pdf unchanged: %v", err)
	}
}
