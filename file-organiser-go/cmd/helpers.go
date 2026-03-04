package cmd

import (
	"bufio"
	"errors"
	"fmt"
	"io"
	"os"
	"strings"
	"time"
)

func validateOptionalDirectory(path string, optionName string) error {
	if path == "" {
		return nil
	}

	info, err := os.Stat(path)
	if err != nil {
		return fmt.Errorf("%s: directory does not exist: %s", optionName, path)
	}

	if !info.IsDir() {
		return fmt.Errorf("%s: path is not a directory: %s", optionName, path)
	}

	return nil
}

func resolveTargetDir(path string, in io.Reader, out io.Writer, getwd func() (string, error)) (string, error) {
	if path == "" {
		return path, nil
	}

	info, err := os.Stat(path)
	if err == nil {
		if !info.IsDir() {
			return "", fmt.Errorf("--target-dir: path is not a directory: %s", path)
		}
		return path, nil
	}

	if !os.IsNotExist(err) {
		return "", err
	}

	fmt.Fprintf(out, "Target directory '%s' does not exist. Do you want to create it? (1.) or default to current directory (2.): ", path)
	reader := bufio.NewReader(in)
	inputChoice, readErr := reader.ReadString('\n')
	if readErr != nil && readErr != io.EOF {
		return "", readErr
	}

	switch strings.TrimSpace(inputChoice) {
	case "1":
		if err := os.MkdirAll(path, 0o755); err != nil {
			return "", err
		}
		fmt.Fprintf(out, "Created target directory: %s\n", path)
		return path, nil
	case "2":
		cwd, cwdErr := getwd()
		if cwdErr != nil {
			return "", cwdErr
		}
		fmt.Fprintf(out, "Defaulting to current directory as target: %s\n", cwd)
		return cwd, nil
	default:
		fmt.Fprintln(out, "User response not recognized. Exiting.")
		return "", errors.New("user response not recognized")
	}
}

func validateRequiredDirectories(paths []string, optionName string) error {
	if len(paths) == 0 {
		return fmt.Errorf("%s: at least one working directory is required", optionName)
	}

	for _, path := range paths {
		if err := validateOptionalDirectory(path, optionName); err != nil {
			return err
		}
	}

	return nil
}

func validateOptionalISODate(value string) error {
	if value == "" {
		return nil
	}

	if _, err := time.Parse("2006-01-02", value); err != nil {
		return errors.New("date must be in YYYY-MM-DD format")
	}

	return nil
}

func normalizeExtension(ext string) string {
	if ext == "" {
		return ""
	}

	clean := ext
	if clean[0] != '.' {
		clean = "." + clean
	}

	return strings.ToLower(clean)
}
