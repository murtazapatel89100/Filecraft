package organizer

import (
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"
)

func parseSelectedDate(sortDate string) (time.Time, error) {
	if sortDate == "" {
		now := time.Now()
		return time.Date(now.Year(), now.Month(), now.Day(), 0, 0, 0, 0, now.Location()), nil
	}

	parsed, err := time.Parse("2006-01-02", sortDate)
	if err != nil {
		return time.Time{}, err
	}

	return parsed, nil
}

func sameDate(a time.Time, b time.Time) bool {
	ay, am, ad := a.Date()
	by, bm, bd := b.Date()
	return ay == by && am == bm && ad == bd
}

func selectFilesByExtension(files []string, extension string) []string {
	selected := make([]string, 0)
	for _, file := range files {
		if getExtension(file, knownExtensions) == extension {
			selected = append(selected, file)
		}
	}
	return selected
}

func selectFilesByDate(files []string, selectedDate time.Time) []string {
	selected := make([]string, 0)
	for _, file := range files {
		info, err := os.Stat(file)
		if err != nil {
			continue
		}
		if sameDate(info.ModTime(), selectedDate) {
			selected = append(selected, file)
		}
	}
	return selected
}

func normalizeFileTypeFilter(fileType string) (string, string, bool) {
	normalized := strings.ToLower(strings.TrimSpace(fileType))
	if normalized == "" {
		return "", "", true
	}

	normalizedExtension := "." + strings.TrimPrefix(normalized, ".")
	if _, ok := extensionTypeMap[normalizedExtension]; ok {
		return "extension", normalizedExtension, true
	}

	normalizedType := strings.ToUpper(strings.ReplaceAll(strings.ReplaceAll(normalized, "-", "_"), " ", "_"))
	if normalizedType == "OTHERS" {
		return "category", normalizedType, true
	}

	for _, folderName := range extensionTypeMap {
		if folderName == normalizedType {
			return "category", normalizedType, true
		}
	}

	return "", "", false
}

func moveFiles(files []string, destinationDir string, dryRun bool, out io.Writer) (map[string]string, error) {
	revertMap := map[string]string{}

	for _, file := range files {
		destinationPath := filepath.Join(destinationDir, filepath.Base(file))
		newPath := buildNonConflictingPath(destinationPath)
		originalPath, resolveErr := filepath.Abs(file)
		if resolveErr != nil {
			return revertMap, resolveErr
		}

		if dryRun {
			fmt.Fprintf(out, "[DRY RUN] Would move %s → %s\n", file, newPath)
			continue
		}

		fmt.Fprintf(out, "Moving %s → %s...\n", file, newPath)
		if err := os.Rename(file, newPath); err != nil {
			return revertMap, err
		}

		newResolved, resolveNewErr := filepath.Abs(newPath)
		if resolveNewErr != nil {
			return revertMap, resolveNewErr
		}

		revertMap[newResolved] = originalPath
	}

	return revertMap, nil
}

func (f *FileOrganizer) separateByExtension(out io.Writer) error {
	folder := strings.ToUpper(strings.TrimPrefix(f.sortExt, "."))
	sortedDir := filepath.Join(f.targetDir, folder)

	fmt.Fprintf(out, "Separating by extension: %s in %s → %s\n", f.sortExt, f.workingDir, f.targetDir)
	fmt.Fprintf(out, "Ensuring directory exists: %s...\n", sortedDir)

	if err := ensureDirectory(sortedDir, f.dryRun); err != nil {
		return err
	}

	files, err := filesFromWorkingDirs([]string{f.workingDir}, f.recursive)
	if err != nil {
		return err
	}

	selected := selectFilesByExtension(files, f.sortExt)
	if len(selected) == 0 {
		fmt.Fprintf(out, "No files with extension '%s' found in %s.\n", f.sortExt, f.workingDir)
		return nil
	}

	revertMap, err := moveFiles(selected, sortedDir, f.dryRun, out)
	if err != nil {
		return err
	}

	if f.saveHistory && !f.dryRun {
		if f.historyPath == "" {
			fmt.Fprintln(out, "Failed to validate History path, cannot save history.")
			return nil
		}
		return SaveHistory(f.historyPath, revertMap, "separate_by_extension")
	}

	return nil
}

func (f *FileOrganizer) separateByDate(out io.Writer) error {
	selectedDate, err := parseSelectedDate(f.sortDate)
	if err != nil {
		return err
	}

	folder := selectedDate.Format("2006-01-02")
	sortedDir := filepath.Join(f.targetDir, folder)

	if f.sortDate == "" {
		fmt.Fprintf(out, "Seperating files modified today in %s → %s\n", f.workingDir, f.targetDir)
	} else {
		fmt.Fprintf(out, "Seperating files modified on %s in %s → %s\n", f.sortDate, f.workingDir, f.targetDir)
	}

	fmt.Fprintf(out, "Ensuring directory exists: %s...\n", sortedDir)

	if err := ensureDirectory(sortedDir, f.dryRun); err != nil {
		return err
	}

	files, err := filesFromWorkingDirs([]string{f.workingDir}, f.recursive)
	if err != nil {
		return err
	}

	selected := selectFilesByDate(files, selectedDate)
	if len(selected) == 0 {
		targetLabel := f.sortDate
		if targetLabel == "" {
			targetLabel = "today"
		}
		fmt.Fprintf(out, "No files modified on %s found in %s.\n", targetLabel, f.workingDir)
		return nil
	}

	revertMap, err := moveFiles(selected, sortedDir, f.dryRun, out)
	if err != nil {
		return err
	}

	if f.saveHistory && !f.dryRun {
		if f.historyPath == "" {
			fmt.Fprintln(out, "Failed to validate History path, cannot save history.")
			return nil
		}
		return SaveHistory(f.historyPath, revertMap, "separate_by_date")
	}

	return nil
}

func (f *FileOrganizer) separateByExtensionAndDate(out io.Writer) error {
	selectedDate, err := parseSelectedDate(f.sortDate)
	if err != nil {
		return err
	}

	dateFolder := selectedDate.Format("2006-01-02")
	extFolder := strings.ToUpper(strings.TrimPrefix(f.sortExt, "."))
	sortedDir := filepath.Join(f.targetDir, dateFolder, extFolder)

	fmt.Fprintf(out, "Separating by extension and date: %s, %s in %s → %s\n", f.sortExt, dateFolder, f.workingDir, f.targetDir)
	fmt.Fprintf(out, "Ensuring directory exists: %s...\n", sortedDir)

	if err := ensureDirectory(sortedDir, f.dryRun); err != nil {
		return err
	}

	files, err := filesFromWorkingDirs([]string{f.workingDir}, f.recursive)
	if err != nil {
		return err
	}

	selected := selectFilesByExtension(files, f.sortExt)
	selected = selectFilesByDate(selected, selectedDate)
	if len(selected) == 0 {
		fmt.Fprintf(out, "No files with extension '%s' modified on %s found in %s.\n", f.sortExt, dateFolder, f.workingDir)
		return nil
	}

	revertMap, err := moveFiles(selected, sortedDir, f.dryRun, out)
	if err != nil {
		return err
	}

	if f.saveHistory && !f.dryRun {
		if f.historyPath == "" {
			fmt.Fprintln(out, "Failed to validate History path, cannot save history.")
			return nil
		}
		return SaveHistory(f.historyPath, revertMap, "separate_by_extension_and_date")
	}

	return nil
}

func (f *FileOrganizer) separateByFileType(out io.Writer) error {
	filterKind, filterValue, isValid := normalizeFileTypeFilter(f.fileType)
	if !isValid {
		fmt.Fprintf(out, "Unsupported file type filter '%s'.\n", f.fileType)
		return nil
	}

	if filterKind == "" {
		fmt.Fprintf(out, "Separating all files by file type in %s → %s\n", f.workingDir, f.targetDir)
	} else {
		fmt.Fprintf(out, "Separating files with filter %s in %s → %s\n", f.fileType, f.workingDir, f.targetDir)
	}

	files, err := filesFromWorkingDirs([]string{f.workingDir}, f.recursive)
	if err != nil {
		return err
	}

	if len(files) == 0 {
		fmt.Fprintf(out, "No files found in %s.\n", f.workingDir)
		return nil
	}

	revertMap := map[string]string{}
	movedFiles := 0
	for _, file := range files {
		ext := getExtension(file, knownExtensions)
		folderName := extensionTypeMap[ext]
		if folderName == "" {
			folderName = "OTHERS"
		}

		if filterKind == "category" && folderName != filterValue {
			continue
		}
		if filterKind == "extension" && ext != filterValue {
			continue
		}

		sortedDir := filepath.Join(f.targetDir, folderName)
		if err := ensureDirectory(sortedDir, f.dryRun); err != nil {
			return err
		}

		mapped, moveErr := moveFiles([]string{file}, sortedDir, f.dryRun, out)
		if moveErr != nil {
			return moveErr
		}

		for k, v := range mapped {
			revertMap[k] = v
		}
		movedFiles += len(mapped)
	}

	if movedFiles == 0 {
		fmt.Fprintf(out, "No files found for file type '%s' in %s.\n", f.fileType, f.workingDir)
		return nil
	}

	if f.saveHistory && !f.dryRun {
		if f.historyPath == "" {
			fmt.Fprintln(out, "Failed to validate History path, cannot save history.")
			return nil
		}
		return SaveHistory(f.historyPath, revertMap, "separate_by_file_type")
	}

	return nil
}

func (f *FileOrganizer) mergeByExtension(out io.Writer) error {
	folder := strings.ToUpper(strings.TrimPrefix(f.sortExt, "."))
	sortedDir := filepath.Join(f.targetDir, folder)

	fmt.Fprintf(out, "Merging by extension: %s from %d working directories → %s\n", f.sortExt, len(f.workingDirs), f.targetDir)
	fmt.Fprintf(out, "Ensuring directory exists: %s...\n", sortedDir)

	if err := ensureDirectory(sortedDir, f.dryRun); err != nil {
		return err
	}

	files, err := filesFromWorkingDirs(f.workingDirs, f.recursive)
	if err != nil {
		return err
	}

	selected := selectFilesByExtension(files, f.sortExt)
	if len(selected) == 0 {
		fmt.Fprintf(out, "No files with extension '%s' found in provided working directories.\n", f.sortExt)
		return nil
	}

	revertMap, err := moveFiles(selected, sortedDir, f.dryRun, out)
	if err != nil {
		return err
	}

	if f.saveHistory && !f.dryRun {
		if f.historyPath == "" {
			fmt.Fprintln(out, "Failed to validate History path, cannot save history.")
			return nil
		}
		return SaveHistory(f.historyPath, revertMap, "merge_by_extension")
	}

	return nil
}

func (f *FileOrganizer) mergeByDate(out io.Writer) error {
	selectedDate, err := parseSelectedDate(f.sortDate)
	if err != nil {
		return err
	}

	folder := selectedDate.Format("2006-01-02")
	sortedDir := filepath.Join(f.targetDir, folder)

	if f.sortDate == "" {
		fmt.Fprintf(out, "Merging files modified today from %d working directories → %s\n", len(f.workingDirs), f.targetDir)
	} else {
		fmt.Fprintf(out, "Merging files modified on %s from %d working directories → %s\n", f.sortDate, len(f.workingDirs), f.targetDir)
	}

	fmt.Fprintf(out, "Ensuring directory exists: %s...\n", sortedDir)

	if err := ensureDirectory(sortedDir, f.dryRun); err != nil {
		return err
	}

	files, err := filesFromWorkingDirs(f.workingDirs, f.recursive)
	if err != nil {
		return err
	}

	selected := selectFilesByDate(files, selectedDate)
	if len(selected) == 0 {
		targetLabel := f.sortDate
		if targetLabel == "" {
			targetLabel = "today"
		}
		fmt.Fprintf(out, "No files modified on %s found in provided working directories.\n", targetLabel)
		return nil
	}

	revertMap, err := moveFiles(selected, sortedDir, f.dryRun, out)
	if err != nil {
		return err
	}

	if f.saveHistory && !f.dryRun {
		if f.historyPath == "" {
			fmt.Fprintln(out, "Failed to validate History path, cannot save history.")
			return nil
		}
		return SaveHistory(f.historyPath, revertMap, "merge_by_date")
	}

	return nil
}

func (f *FileOrganizer) mergeByExtensionAndDate(out io.Writer) error {
	selectedDate, err := parseSelectedDate(f.sortDate)
	if err != nil {
		return err
	}

	dateFolder := selectedDate.Format("2006-01-02")
	extFolder := strings.ToUpper(strings.TrimPrefix(f.sortExt, "."))
	sortedDir := filepath.Join(f.targetDir, dateFolder, extFolder)

	fmt.Fprintf(out, "Merging by extension and date: %s, %s from %d working directories → %s\n", f.sortExt, dateFolder, len(f.workingDirs), f.targetDir)
	fmt.Fprintf(out, "Ensuring directory exists: %s...\n", sortedDir)

	if err := ensureDirectory(sortedDir, f.dryRun); err != nil {
		return err
	}

	files, err := filesFromWorkingDirs(f.workingDirs, f.recursive)
	if err != nil {
		return err
	}

	selected := selectFilesByExtension(files, f.sortExt)
	selected = selectFilesByDate(selected, selectedDate)
	if len(selected) == 0 {
		fmt.Fprintf(out, "No files with extension '%s' modified on %s found in provided working directories.\n", f.sortExt, dateFolder)
		return nil
	}

	revertMap, err := moveFiles(selected, sortedDir, f.dryRun, out)
	if err != nil {
		return err
	}

	if f.saveHistory && !f.dryRun {
		if f.historyPath == "" {
			fmt.Fprintln(out, "Failed to validate History path, cannot save history.")
			return nil
		}
		return SaveHistory(f.historyPath, revertMap, "merge_by_extension_and_date")
	}

	return nil
}

func (f *FileOrganizer) mergeByFileType(out io.Writer) error {
	fmt.Fprintf(out, "Merging all files by file type from %d working directories → %s\n", len(f.workingDirs), f.targetDir)

	files, err := filesFromWorkingDirs(f.workingDirs, f.recursive)
	if err != nil {
		return err
	}

	if len(files) == 0 {
		fmt.Fprintln(out, "No files found in provided working directories.")
		return nil
	}

	revertMap := map[string]string{}
	for _, file := range files {
		ext := getExtension(file, knownExtensions)
		folderName := extensionTypeMap[ext]
		if folderName == "" {
			folderName = "OTHERS"
		}

		sortedDir := filepath.Join(f.targetDir, folderName)
		if err := ensureDirectory(sortedDir, f.dryRun); err != nil {
			return err
		}

		mapped, moveErr := moveFiles([]string{file}, sortedDir, f.dryRun, out)
		if moveErr != nil {
			return moveErr
		}

		for k, v := range mapped {
			revertMap[k] = v
		}
	}

	if f.saveHistory && !f.dryRun {
		if f.historyPath == "" {
			fmt.Fprintln(out, "Failed to validate History path, cannot save history.")
			return nil
		}
		return SaveHistory(f.historyPath, revertMap, "merge_by_file_type")
	}

	return nil
}
