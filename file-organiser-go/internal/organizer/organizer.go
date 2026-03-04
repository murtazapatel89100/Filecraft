package organizer

import (
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

type Config struct {
	Mode        Mode
	SortDate    string
	SortExt     string
	FileType    string
	TargetDir   string
	WorkingDir  string
	WorkingDirs []string
	DryRun      bool
	SaveHistory bool
	RenameWith  string
}

type FileOrganizer struct {
	mode        Mode
	sortDate    string
	sortExt     string
	fileType    string
	targetDir   string
	workingDir  string
	workingDirs []string
	dryRun      bool
	saveHistory bool
	historyPath string
	renameWith  string
}

func NewFileOrganizer(cfg Config) (*FileOrganizer, error) {
	cwd, err := os.Getwd()
	if err != nil {
		return nil, err
	}

	targetDir := cfg.TargetDir
	if targetDir == "" {
		targetDir = cwd
	}

	workingDir := cfg.WorkingDir
	if workingDir == "" {
		workingDir = cwd
	}

	resolvedTarget, err := filepath.Abs(targetDir)
	if err != nil {
		return nil, err
	}

	resolvedWorking, err := filepath.Abs(workingDir)
	if err != nil {
		return nil, err
	}

	resolvedWorkingDirs := make([]string, 0)
	if len(cfg.WorkingDirs) > 0 {
		for _, dir := range cfg.WorkingDirs {
			resolved, absErr := filepath.Abs(dir)
			if absErr != nil {
				return nil, absErr
			}
			resolvedWorkingDirs = append(resolvedWorkingDirs, resolved)
		}
	} else {
		resolvedWorkingDirs = append(resolvedWorkingDirs, resolvedWorking)
	}

	mode := cfg.Mode
	if mode == "" {
		mode = ModeExtension
	}

	fo := &FileOrganizer{
		mode:        mode,
		sortDate:    cfg.SortDate,
		sortExt:     strings.ToLower(cfg.SortExt),
		fileType:    cfg.FileType,
		targetDir:   resolvedTarget,
		workingDir:  resolvedWorking,
		workingDirs: resolvedWorkingDirs,
		dryRun:      cfg.DryRun,
		saveHistory: cfg.SaveHistory,
		renameWith:  cfg.RenameWith,
	}

	if fo.saveHistory {
		now := time.Now()
		timestamp := fmt.Sprintf("%s-%06d", now.Format("2006-01-02_15-04-05"), now.Nanosecond()/1000)
		candidate := filepath.Join(fo.targetDir, HistoryFilePrefix+timestamp+".json")
		fo.historyPath = buildNonConflictingPath(candidate)
	}

	return fo, nil
}

func (f *FileOrganizer) Rename(out io.Writer) error {
	entries, err := os.ReadDir(f.workingDir)
	if err != nil {
		return err
	}

	files := make([]string, 0)
	for _, entry := range entries {
		if entry.Type().IsRegular() {
			files = append(files, filepath.Join(f.workingDir, entry.Name()))
		}
	}

	if len(files) == 0 {
		fmt.Fprintln(out, "No files found in the working directory.")
		return nil
	}

	sort.Slice(files, func(i, j int) bool {
		return filepath.Base(files[i]) < filepath.Base(files[j])
	})

	renameMap := map[string]string{}
	for index, filePath := range files {
		ext := filepath.Ext(filePath)
		newName := fmt.Sprintf("%d%s", index+1, ext)
		if f.renameWith != "" {
			newName = fmt.Sprintf("%s_%d%s", f.renameWith, index+1, ext)
		}
		destinationPath := filepath.Join(f.targetDir, newName)
		newPath := buildNonConflictingPath(destinationPath)

		originalPath, resolveErr := filepath.Abs(filePath)
		if resolveErr != nil {
			return resolveErr
		}

		if f.dryRun {
			fmt.Fprintf(out, "[DRY RUN] %s → %s\n", filepath.Base(filePath), filepath.Base(newPath))
			continue
		}

		if err := os.Rename(filePath, newPath); err != nil {
			return err
		}

		fmt.Fprintf(out, "%s → %s\n", filepath.Base(filePath), filepath.Base(newPath))

		newResolved, resolveNewErr := filepath.Abs(newPath)
		if resolveNewErr != nil {
			return resolveNewErr
		}

		renameMap[newResolved] = originalPath
	}

	if f.saveHistory && f.historyPath != "" && !f.dryRun {
		if err := SaveHistory(f.historyPath, renameMap, "rename"); err != nil {
			return err
		}

		fmt.Fprintf(out, "History saved to %s\n", filepath.Base(f.historyPath))
	}

	return nil
}

func (f *FileOrganizer) Separate(out io.Writer) error {
	switch f.mode {
	case ModeExtension:
		if f.sortExt == "" {
			fmt.Fprintln(out, "No extension specified for separation.")
			return nil
		}
		return f.separateByExtension(out)
	case ModeDate:
		return f.separateByDate(out)
	case ModeExtensionAndDate:
		if f.sortExt == "" {
			fmt.Fprintln(out, "No extension specified for separation.")
			return nil
		}
		return f.separateByExtensionAndDate(out)
	case ModeFile:
		return f.separateByFileType(out)
	default:
		return errors.New("invalid separation choice")
	}
}

func (f *FileOrganizer) Merge(out io.Writer) error {
	if len(f.workingDirs) == 0 {
		fmt.Fprintln(out, "No working directories specified for merge.")
		return nil
	}

	switch f.mode {
	case ModeExtension:
		if f.sortExt == "" {
			fmt.Fprintln(out, "No extension specified for merge.")
			return nil
		}
		return f.mergeByExtension(out)
	case ModeDate:
		return f.mergeByDate(out)
	case ModeExtensionAndDate:
		if f.sortExt == "" {
			fmt.Fprintln(out, "No extension specified for merge.")
			return nil
		}
		return f.mergeByExtensionAndDate(out)
	case ModeFile:
		return f.mergeByFileType(out)
	default:
		return errors.New("invalid merge choice")
	}
}

func (f *FileOrganizer) HistoryPath() string {
	return f.historyPath
}
