package cmd

import (
	"errors"
	"fmt"
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
