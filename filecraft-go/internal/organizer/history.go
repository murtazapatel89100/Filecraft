package organizer

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"time"
)

type historyPayload struct {
	Operation string            `json:"operation"`
	Mappings  map[string]string `json:"mappings"`
}

func SaveHistory(historyPath string, revertMap map[string]string, operation string) error {
	payload := historyPayload{Operation: operation, Mappings: revertMap}

	if err := os.MkdirAll(filepath.Dir(historyPath), 0o755); err != nil {
		return err
	}

	content, err := json.MarshalIndent(payload, "", "    ")
	if err != nil {
		return err
	}

	return os.WriteFile(historyPath, content, 0o644)
}

func LoadLatestHistory(directory string) (string, error) {
	entries, err := os.ReadDir(directory)
	if err != nil {
		return "", err
	}

	type item struct {
		path    string
		modTime time.Time
	}

	historyFiles := make([]item, 0)
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}

		name := entry.Name()
		if len(name) < len(HistoryFilePrefix) || name[:len(HistoryFilePrefix)] != HistoryFilePrefix {
			continue
		}

		if filepath.Ext(name) != ".json" {
			continue
		}

		fullPath := filepath.Join(directory, name)
		info, statErr := os.Stat(fullPath)
		if statErr != nil {
			continue
		}

		historyFiles = append(historyFiles, item{path: fullPath, modTime: info.ModTime()})
	}

	if len(historyFiles) == 0 {
		return "", nil
	}

	sort.Slice(historyFiles, func(i, j int) bool {
		return historyFiles[i].modTime.After(historyFiles[j].modTime)
	})

	return historyFiles[0].path, nil
}

func readHistory(historyPath string) (map[string]string, error) {
	content, err := os.ReadFile(historyPath)
	if err != nil {
		return nil, fmt.Errorf("failed to read history file %s: %w", historyPath, err)
	}

	var payload historyPayload
	if err := json.Unmarshal(content, &payload); err != nil {
		return nil, fmt.Errorf("corrupted history file (invalid JSON) %s: %w", historyPath, err)
	}

	if payload.Mappings == nil {
		return map[string]string{}, nil
	}

	return payload.Mappings, nil
}

func deleteHistory(historyPath string) error {
	if _, err := os.Stat(historyPath); os.IsNotExist(err) {
		return nil
	}

	return os.Remove(historyPath)
}

func RevertHistory(historyPath string, directory string, dryRun bool, deleteAfterRevert bool, out io.Writer) (int, error) {
	if historyPath == "" {
		if directory == "" {
			cwd, err := os.Getwd()
			if err != nil {
				return 0, err
			}
			directory = cwd
		}

		latest, err := LoadLatestHistory(directory)
		if err != nil {
			return 0, err
		}

		if latest == "" {
			fmt.Fprintf(out, "No history file found in %s\n", directory)
			return 0, nil
		}

		historyPath = latest
	}

	mappings, err := readHistory(historyPath)
	if err != nil {
		return 0, err
	}

	if len(mappings) == 0 {
		fmt.Fprintf(out, "No mappings found in history file: %s\n", historyPath)
		return 0, nil
	}

	revertedCount := 0
	for current, original := range mappings {
		if _, err := os.Stat(current); os.IsNotExist(err) {
			continue
		}

		if dryRun {
			fmt.Fprintf(out, "[DRY RUN] Would move %s → %s\n", current, original)
			revertedCount++
			continue
		}

		if err := os.MkdirAll(filepath.Dir(original), 0o755); err != nil {
			return revertedCount, err
		}

		destinationPath := buildNonConflictingPath(original)
		if err := os.Rename(current, destinationPath); err != nil {
			return revertedCount, err
		}

		revertedCount++
	}

	if revertedCount > 0 && deleteAfterRevert && !dryRun {
		if err := deleteHistory(historyPath); err != nil {
			return revertedCount, err
		}
	}

	return revertedCount, nil
}
