package organizer

import (
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"syscall"
	"time"
)

// ---------------------------------------------------------------------------
// Date helpers
// ---------------------------------------------------------------------------

func parseSelectedDate(sortDate string) (time.Time, error) {
	if sortDate == "" {
		now := time.Now()
		return time.Date(now.Year(), now.Month(), now.Day(), 0, 0, 0, 0, now.Location()), nil
	}
	return time.Parse("2006-01-02", sortDate)
}

func sameDate(a, b time.Time) bool {
	ay, am, ad := a.Date()
	by, bm, bd := b.Date()
	return ay == by && am == bm && ad == bd
}

// ---------------------------------------------------------------------------
// File-type filter normalisation
// ---------------------------------------------------------------------------

func normalizeFileTypeFilter(fileType string) (string, string, bool) {
	normalized := strings.ToLower(strings.TrimSpace(fileType))
	if normalized == "" {
		return "", "", true
	}

	normalizedExt := "." + strings.TrimPrefix(normalized, ".")
	if _, ok := extensionTypeMap[normalizedExt]; ok {
		return "extension", normalizedExt, true
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

// ---------------------------------------------------------------------------
// Same-file / cross-device helpers
// ---------------------------------------------------------------------------

func pathsReferToSameFile(source, destination string) bool {
	srcAbs, srcErr := filepath.Abs(source)
	dstAbs, dstErr := filepath.Abs(destination)
	if srcErr != nil || dstErr != nil {
		return false
	}
	if srcAbs == dstAbs {
		return true
	}
	srcInfo, srcStat := os.Stat(srcAbs)
	dstInfo, dstStat := os.Stat(dstAbs)
	if srcStat != nil || dstStat != nil {
		return false
	}
	return os.SameFile(srcInfo, dstInfo)
}

func isCrossDeviceMoveError(err error) bool {
	if err == nil {
		return false
	}
	var linkErr *os.LinkError
	if errors.As(err, &linkErr) {
		return errors.Is(linkErr.Err, syscall.EXDEV)
	}
	return errors.Is(err, syscall.EXDEV)
}

func isNoSpaceError(err error) bool {
	if err == nil {
		return false
	}
	return errors.Is(err, syscall.ENOSPC)
}

// ---------------------------------------------------------------------------
// File move primitives
// ---------------------------------------------------------------------------

func copyFileAndRemoveSource(source, destination string) error {
	srcFile, err := os.Open(source)
	if err != nil {
		return err
	}
	defer srcFile.Close()

	srcInfo, err := srcFile.Stat()
	if err != nil {
		return err
	}

	dstFile, err := os.OpenFile(destination, os.O_CREATE|os.O_EXCL|os.O_WRONLY, srcInfo.Mode())
	if err != nil {
		return err
	}

	_, copyErr := io.Copy(dstFile, srcFile)
	closeErr := dstFile.Close()
	if copyErr != nil {
		_ = os.Remove(destination)
		return copyErr
	}
	if closeErr != nil {
		_ = os.Remove(destination)
		return closeErr
	}

	if err := os.Chtimes(destination, srcInfo.ModTime(), srcInfo.ModTime()); err != nil {
		_ = os.Remove(destination)
		return err
	}

	if err := os.Remove(source); err != nil {
		_ = os.Remove(destination)
		return err
	}
	return nil
}

func moveFile(file, destinationPath string, dryRun bool, out io.Writer) (string, bool, error) {
	if pathsReferToSameFile(file, destinationPath) {
		fmt.Fprintf(out, "Skipping %s (already at destination).\n", file)
		return destinationPath, true, nil
	}

	newPath := buildNonConflictingPath(destinationPath)

	if dryRun {
		fmt.Fprintf(out, "[DRY RUN] Would move %s → %s\n", file, newPath)
		return newPath, false, nil
	}

	fmt.Fprintf(out, "Moving %s → %s...\n", file, newPath)

	if err := os.Rename(file, newPath); err != nil {
		if isCrossDeviceMoveError(err) {
			if copyErr := copyFileAndRemoveSource(file, newPath); copyErr == nil {
				return newPath, false, nil
			} else if isNoSpaceError(copyErr) {
				return "", false, fmt.Errorf(
					"insufficient free space while moving across filesystems into %s: %w",
					filepath.Dir(newPath), copyErr,
				)
			} else {
				return "", false, copyErr
			}
		}
		if isNoSpaceError(err) {
			return "", false, fmt.Errorf(
				"insufficient free space while moving %s to %s: %w", file, newPath, err,
			)
		}
		return "", false, err
	}

	return newPath, false, nil
}

// ---------------------------------------------------------------------------
// Core organise loop
// ---------------------------------------------------------------------------

type organizeConfig struct {
	workingDirs []string
	targetDir   string
	recursive   bool
	dryRun      bool
	saveHistory bool
	historyPath string
	operation   string
	headerMsg   string
	noMatchMsg  string
	fileFilter  func(string) bool
	destForFile func(string) string
}

func organizeFiles(cfg organizeConfig, out io.Writer) error {
	fmt.Fprintln(out, cfg.headerMsg)

	files, err := filesFromWorkingDirs(cfg.workingDirs, cfg.recursive, []string{cfg.targetDir})
	if err != nil {
		return err
	}

	// Filter
	selected := make([]string, 0, len(files))
	for _, f := range files {
		if cfg.fileFilter(f) {
			selected = append(selected, f)
		}
	}

	if len(selected) == 0 {
		fmt.Fprintln(out, cfg.noMatchMsg)
		return nil
	}

	// Ensure destination directories exist
	seenDirs := map[string]bool{}
	for _, f := range selected {
		dir := filepath.Dir(cfg.destForFile(f))
		if !seenDirs[dir] {
			if err := ensureDirectory(dir, cfg.dryRun); err != nil {
				return err
			}
			seenDirs[dir] = true
		}
	}

	// Move files
	revertMap := map[string]string{}
	for _, file := range selected {
		originalPath, err := filepath.Abs(file)
		if err != nil {
			return err
		}

		dest := cfg.destForFile(file)
		newPath, skipped, moveErr := moveFile(file, dest, cfg.dryRun, out)
		if moveErr != nil {
			return moveErr
		}
		if skipped || cfg.dryRun {
			continue
		}

		newResolved, err := filepath.Abs(newPath)
		if err != nil {
			return err
		}
		revertMap[newResolved] = originalPath
	}

	// Save history
	if cfg.saveHistory && !cfg.dryRun && len(revertMap) > 0 {
		if cfg.historyPath == "" {
			fmt.Fprintln(out, "Failed to validate History path, cannot save history.")
			return nil
		}
		return SaveHistory(cfg.historyPath, revertMap, cfg.operation)
	}

	return nil
}

// ---------------------------------------------------------------------------
// Separate operations
// ---------------------------------------------------------------------------

func (f *FileOrganizer) separateByExtension(out io.Writer) error {
	folder := strings.ToUpper(strings.TrimPrefix(f.sortExt, "."))
	sortedDir := filepath.Join(f.targetDir, folder)

	return organizeFiles(organizeConfig{
		workingDirs: []string{f.workingDir},
		targetDir:   f.targetDir,
		recursive:   f.recursive,
		dryRun:      f.dryRun,
		saveHistory: f.saveHistory,
		historyPath: f.historyPath,
		operation:   "separate_by_extension",
		headerMsg:   fmt.Sprintf("Separating by extension: %s in %s → %s", f.sortExt, f.workingDir, f.targetDir),
		noMatchMsg:  fmt.Sprintf("No files with extension '%s' found in %s.", f.sortExt, f.workingDir),
		fileFilter:  func(file string) bool { return getExtension(file, knownExtensions) == f.sortExt },
		destForFile: func(file string) string { return filepath.Join(sortedDir, filepath.Base(file)) },
	}, out)
}

func (f *FileOrganizer) separateByDate(out io.Writer) error {
	selectedDate, err := parseSelectedDate(f.sortDate)
	if err != nil {
		return err
	}

	folder := selectedDate.Format("2006-01-02")
	sortedDir := filepath.Join(f.targetDir, folder)

	label := f.sortDate
	if label == "" {
		label = "today"
	}

	return organizeFiles(organizeConfig{
		workingDirs: []string{f.workingDir},
		targetDir:   f.targetDir,
		recursive:   f.recursive,
		dryRun:      f.dryRun,
		saveHistory: f.saveHistory,
		historyPath: f.historyPath,
		operation:   "separate_by_date",
		headerMsg:   fmt.Sprintf("Separating files modified on %s in %s → %s", label, f.workingDir, f.targetDir),
		noMatchMsg:  fmt.Sprintf("No files modified on %s found in %s.", label, f.workingDir),
		fileFilter: func(file string) bool {
			info, err := os.Stat(file)
			if err != nil {
				return false
			}
			return sameDate(info.ModTime(), selectedDate)
		},
		destForFile: func(file string) string { return filepath.Join(sortedDir, filepath.Base(file)) },
	}, out)
}

func (f *FileOrganizer) separateByExtensionAndDate(out io.Writer) error {
	selectedDate, err := parseSelectedDate(f.sortDate)
	if err != nil {
		return err
	}

	dateFolder := selectedDate.Format("2006-01-02")
	extFolder := strings.ToUpper(strings.TrimPrefix(f.sortExt, "."))
	sortedDir := filepath.Join(f.targetDir, dateFolder, extFolder)

	return organizeFiles(organizeConfig{
		workingDirs: []string{f.workingDir},
		targetDir:   f.targetDir,
		recursive:   f.recursive,
		dryRun:      f.dryRun,
		saveHistory: f.saveHistory,
		historyPath: f.historyPath,
		operation:   "separate_by_extension_and_date",
		headerMsg:   fmt.Sprintf("Separating by extension and date: %s, %s in %s → %s", f.sortExt, dateFolder, f.workingDir, f.targetDir),
		noMatchMsg:  fmt.Sprintf("No files with extension '%s' modified on %s found in %s.", f.sortExt, dateFolder, f.workingDir),
		fileFilter: func(file string) bool {
			if getExtension(file, knownExtensions) != f.sortExt {
				return false
			}
			info, err := os.Stat(file)
			if err != nil {
				return false
			}
			return sameDate(info.ModTime(), selectedDate)
		},
		destForFile: func(file string) string { return filepath.Join(sortedDir, filepath.Base(file)) },
	}, out)
}

func (f *FileOrganizer) separateByFileType(out io.Writer) error {
	filterKind, filterValue, isValid := normalizeFileTypeFilter(f.fileType)
	if !isValid {
		fmt.Fprintf(out, "Unsupported file type filter '%s'.\n", f.fileType)
		return nil
	}

	label := "by file type"
	if filterKind != "" {
		label = fmt.Sprintf("with filter %s", f.fileType)
	}

	noMatch := fmt.Sprintf("No files found in %s.", f.workingDir)
	if f.fileType != "" {
		noMatch = fmt.Sprintf("No files found for file type '%s' in %s.", f.fileType, f.workingDir)
	}

	return organizeFiles(organizeConfig{
		workingDirs: []string{f.workingDir},
		targetDir:   f.targetDir,
		recursive:   f.recursive,
		dryRun:      f.dryRun,
		saveHistory: f.saveHistory,
		historyPath: f.historyPath,
		operation:   "separate_by_file_type",
		headerMsg:   fmt.Sprintf("Separating files %s in %s → %s", label, f.workingDir, f.targetDir),
		noMatchMsg:  noMatch,
		fileFilter: func(file string) bool {
			if filterKind == "" {
				return true
			}
			ext := getExtension(file, knownExtensions)
			folder := extensionTypeMap[ext]
			if folder == "" {
				folder = "OTHERS"
			}
			if filterKind == "category" {
				return folder == filterValue
			}
			return ext == filterValue
		},
		destForFile: func(file string) string {
			ext := getExtension(file, knownExtensions)
			folder := extensionTypeMap[ext]
			if folder == "" {
				folder = "OTHERS"
			}
			return filepath.Join(f.targetDir, folder, filepath.Base(file))
		},
	}, out)
}

// ---------------------------------------------------------------------------
// Merge operations
// ---------------------------------------------------------------------------

func (f *FileOrganizer) mergeByExtension(out io.Writer) error {
	folder := strings.ToUpper(strings.TrimPrefix(f.sortExt, "."))
	sortedDir := filepath.Join(f.targetDir, folder)

	return organizeFiles(organizeConfig{
		workingDirs: f.workingDirs,
		targetDir:   f.targetDir,
		recursive:   f.recursive,
		dryRun:      f.dryRun,
		saveHistory: f.saveHistory,
		historyPath: f.historyPath,
		operation:   "merge_by_extension",
		headerMsg:   fmt.Sprintf("Merging by extension: %s from %d directories → %s", f.sortExt, len(f.workingDirs), f.targetDir),
		noMatchMsg:  fmt.Sprintf("No files with extension '%s' found in provided working directories.", f.sortExt),
		fileFilter:  func(file string) bool { return getExtension(file, knownExtensions) == f.sortExt },
		destForFile: func(file string) string { return filepath.Join(sortedDir, filepath.Base(file)) },
	}, out)
}

func (f *FileOrganizer) mergeByDate(out io.Writer) error {
	selectedDate, err := parseSelectedDate(f.sortDate)
	if err != nil {
		return err
	}

	folder := selectedDate.Format("2006-01-02")
	sortedDir := filepath.Join(f.targetDir, folder)

	label := f.sortDate
	if label == "" {
		label = "today"
	}

	return organizeFiles(organizeConfig{
		workingDirs: f.workingDirs,
		targetDir:   f.targetDir,
		recursive:   f.recursive,
		dryRun:      f.dryRun,
		saveHistory: f.saveHistory,
		historyPath: f.historyPath,
		operation:   "merge_by_date",
		headerMsg:   fmt.Sprintf("Merging files modified on %s from %d directories → %s", label, len(f.workingDirs), f.targetDir),
		noMatchMsg:  fmt.Sprintf("No files modified on %s found in provided working directories.", label),
		fileFilter: func(file string) bool {
			info, err := os.Stat(file)
			if err != nil {
				return false
			}
			return sameDate(info.ModTime(), selectedDate)
		},
		destForFile: func(file string) string { return filepath.Join(sortedDir, filepath.Base(file)) },
	}, out)
}

func (f *FileOrganizer) mergeByExtensionAndDate(out io.Writer) error {
	selectedDate, err := parseSelectedDate(f.sortDate)
	if err != nil {
		return err
	}

	dateFolder := selectedDate.Format("2006-01-02")
	extFolder := strings.ToUpper(strings.TrimPrefix(f.sortExt, "."))
	sortedDir := filepath.Join(f.targetDir, dateFolder, extFolder)

	return organizeFiles(organizeConfig{
		workingDirs: f.workingDirs,
		targetDir:   f.targetDir,
		recursive:   f.recursive,
		dryRun:      f.dryRun,
		saveHistory: f.saveHistory,
		historyPath: f.historyPath,
		operation:   "merge_by_extension_and_date",
		headerMsg:   fmt.Sprintf("Merging by extension and date: %s, %s from %d directories → %s", f.sortExt, dateFolder, len(f.workingDirs), f.targetDir),
		noMatchMsg:  fmt.Sprintf("No files with extension '%s' modified on %s found in provided working directories.", f.sortExt, dateFolder),
		fileFilter: func(file string) bool {
			if getExtension(file, knownExtensions) != f.sortExt {
				return false
			}
			info, err := os.Stat(file)
			if err != nil {
				return false
			}
			return sameDate(info.ModTime(), selectedDate)
		},
		destForFile: func(file string) string { return filepath.Join(sortedDir, filepath.Base(file)) },
	}, out)
}

func (f *FileOrganizer) mergeByFileType(out io.Writer) error {
	filterKind, filterValue, isValid := normalizeFileTypeFilter(f.fileType)
	if !isValid {
		fmt.Fprintf(out, "Unsupported file type filter '%s'.\n", f.fileType)
		return nil
	}

	label := "by file type"
	if filterKind != "" {
		label = fmt.Sprintf("with filter %s", f.fileType)
	}

	noMatch := "No files found in provided working directories."
	if f.fileType != "" {
		noMatch = fmt.Sprintf("No files found for file type '%s' in provided working directories.", f.fileType)
	}

	return organizeFiles(organizeConfig{
		workingDirs: f.workingDirs,
		targetDir:   f.targetDir,
		recursive:   f.recursive,
		dryRun:      f.dryRun,
		saveHistory: f.saveHistory,
		historyPath: f.historyPath,
		operation:   "merge_by_file_type",
		headerMsg:   fmt.Sprintf("Merging files %s from %d directories → %s", label, len(f.workingDirs), f.targetDir),
		noMatchMsg:  noMatch,
		fileFilter: func(file string) bool {
			if filterKind == "" {
				return true
			}
			ext := getExtension(file, knownExtensions)
			folder := extensionTypeMap[ext]
			if folder == "" {
				folder = "OTHERS"
			}
			if filterKind == "category" {
				return folder == filterValue
			}
			return ext == filterValue
		},
		destForFile: func(file string) string {
			ext := getExtension(file, knownExtensions)
			folder := extensionTypeMap[ext]
			if folder == "" {
				folder = "OTHERS"
			}
			return filepath.Join(f.targetDir, folder, filepath.Base(file))
		},
	}, out)
}
