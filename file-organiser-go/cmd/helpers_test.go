package cmd

import (
	"bytes"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

type failingReader struct{}

func (f failingReader) Read(p []byte) (n int, err error) {
	return 0, errors.New("boom")
}

func TestResolveTargetDirMissingCreateOptionCreatesDirectory(t *testing.T) {
	base := t.TempDir()
	target := filepath.Join(base, "missing-create")

	in := strings.NewReader("y\n")
	out := &bytes.Buffer{}

	resolved, err := resolveTargetDir(target, in, out, false)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if resolved != target {
		t.Fatalf("expected resolved target %s, got %s", target, resolved)
	}

	info, statErr := os.Stat(target)
	if statErr != nil {
		t.Fatalf("expected directory to be created: %v", statErr)
	}
	if !info.IsDir() {
		t.Fatal("expected created target to be a directory")
	}
	if !strings.Contains(out.String(), "Created target directory") {
		t.Fatalf("expected creation message, got: %s", out.String())
	}
}

func TestResolveTargetDirMissingDeclineReturnsTargetDirError(t *testing.T) {
	base := t.TempDir()
	target := filepath.Join(base, "missing-decline")

	in := strings.NewReader("n\n")
	out := &bytes.Buffer{}

	_, err := resolveTargetDir(target, in, out, false)
	if err == nil {
		t.Fatal("expected error when user declines target directory creation")
	}
	if !strings.Contains(err.Error(), "--target-dir: directory does not exist") {
		t.Fatalf("unexpected error: %v", err)
	}
	if strings.Contains(out.String(), "Defaulting to current directory as target") {
		t.Fatalf("did not expect defaulting message, got: %s", out.String())
	}
}

func TestResolveTargetDirMissingInvalidInputReturnsTargetDirError(t *testing.T) {
	base := t.TempDir()
	target := filepath.Join(base, "missing-invalid")

	in := strings.NewReader("x\n")
	out := &bytes.Buffer{}

	_, err := resolveTargetDir(target, in, out, false)
	if err == nil {
		t.Fatal("expected error for invalid user input")
	}
	if !strings.Contains(err.Error(), "--target-dir: directory does not exist") {
		t.Fatalf("unexpected error: %v", err)
	}
	if !strings.Contains(err.Error(), target) {
		t.Fatalf("expected path in error, got: %v", err)
	}
}

func TestResolveTargetDirReadFailureHasTargetDirContext(t *testing.T) {
	base := t.TempDir()
	target := filepath.Join(base, "missing-read-fail")
	out := &bytes.Buffer{}

	_, err := resolveTargetDir(target, failingReader{}, out, false)
	if err == nil {
		t.Fatal("expected read error")
	}
	if !strings.Contains(err.Error(), "--target-dir: unable to read confirmation") {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestResolveTargetDirDryRunSkipsCreationAndPrompt(t *testing.T) {
	base := t.TempDir()
	target := filepath.Join(base, "missing-dry-run")
	out := &bytes.Buffer{}

	resolved, err := resolveTargetDir(target, strings.NewReader("y\n"), out, true)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
	if resolved != target {
		t.Fatalf("expected resolved target %s, got %s", target, resolved)
	}
	if _, statErr := os.Stat(target); !os.IsNotExist(statErr) {
		t.Fatalf("expected no target directory creation in dry run, got: %v", statErr)
	}
	if !strings.Contains(out.String(), "[DRY RUN] Target directory does not exist") {
		t.Fatalf("expected dry-run message, got: %s", out.String())
	}
}
