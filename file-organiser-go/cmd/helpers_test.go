package cmd

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestResolveTargetDirMissingCreateOptionCreatesDirectory(t *testing.T) {
	base := t.TempDir()
	target := filepath.Join(base, "missing-create")

	in := strings.NewReader("1\n")
	out := &bytes.Buffer{}

	resolved, err := resolveTargetDir(target, in, out, os.Getwd)
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

func TestResolveTargetDirMissingDefaultOptionUsesCurrentDirectory(t *testing.T) {
	base := t.TempDir()
	target := filepath.Join(base, "missing-default")
	fakeCwd := filepath.Join(base, "cwd")

	in := strings.NewReader("2\n")
	out := &bytes.Buffer{}

	resolved, err := resolveTargetDir(target, in, out, func() (string, error) {
		return fakeCwd, nil
	})
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if resolved != fakeCwd {
		t.Fatalf("expected resolved target %s, got %s", fakeCwd, resolved)
	}
	if !strings.Contains(out.String(), "Defaulting to current directory as target") {
		t.Fatalf("expected defaulting message, got: %s", out.String())
	}
}

func TestResolveTargetDirMissingInvalidInputReturnsError(t *testing.T) {
	base := t.TempDir()
	target := filepath.Join(base, "missing-invalid")

	in := strings.NewReader("x\n")
	out := &bytes.Buffer{}

	_, err := resolveTargetDir(target, in, out, os.Getwd)
	if err == nil {
		t.Fatal("expected error for invalid user input")
	}
	if !strings.Contains(err.Error(), "user response not recognized") {
		t.Fatalf("unexpected error: %v", err)
	}
	if !strings.Contains(out.String(), "User response not recognized. Exiting.") {
		t.Fatalf("expected exit message, got: %s", out.String())
	}
}
