package cmd

import (
	"bytes"
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
