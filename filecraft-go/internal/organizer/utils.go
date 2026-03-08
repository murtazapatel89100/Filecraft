package organizer

import (
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
)

func ensureDirectory(path string, dryRun bool) error {
	if _, err := os.Stat(path); err == nil {
		return nil
	}

	if dryRun {
		return nil
	}

	return os.MkdirAll(path, 0o755)
}

func buildNonConflictingPath(path string) string {
	if _, err := os.Stat(path); os.IsNotExist(err) {
		return path
	}

	dir := filepath.Dir(path)
	base := filepath.Base(path)
	ext := filepath.Ext(base)
	stem := strings.TrimSuffix(base, ext)

	for index := 1; ; index++ {
		candidate := filepath.Join(dir, stem+"_"+strconv.Itoa(index)+ext)
		if _, err := os.Stat(candidate); os.IsNotExist(err) {
			return candidate
		}
	}
}

func getExtension(path string, known []string) string {
	name := strings.ToLower(filepath.Base(path))

	if len(known) > 0 {
		matches := make([]string, 0)
		for _, ext := range known {
			candidate := strings.ToLower(ext)
			if strings.HasSuffix(name, candidate) {
				matches = append(matches, candidate)
			}
		}

		if len(matches) > 0 {
			sort.Slice(matches, func(i, j int) bool {
				return len(matches[i]) > len(matches[j])
			})
			return matches[0]
		}
	}

	ext := strings.ToLower(filepath.Ext(name))
	if ext == name {
		return ""
	}
	return ext
}

func isWithinPath(path string, root string) bool {
	rel, err := filepath.Rel(root, path)
	if err != nil {
		return false
	}

	return rel == "." || (rel != ".." && !strings.HasPrefix(rel, ".."+string(filepath.Separator)))
}

func pruneNestedRoots(dirs []string) ([]string, error) {
	resolvedSet := map[string]struct{}{}
	for _, dir := range dirs {
		resolved, err := filepath.Abs(dir)
		if err != nil {
			return nil, err
		}
		resolvedSet[resolved] = struct{}{}
	}

	resolvedDirs := make([]string, 0, len(resolvedSet))
	for dir := range resolvedSet {
		resolvedDirs = append(resolvedDirs, dir)
	}

	sort.Slice(resolvedDirs, func(i, j int) bool {
		leftDepth := strings.Count(resolvedDirs[i], string(filepath.Separator))
		rightDepth := strings.Count(resolvedDirs[j], string(filepath.Separator))
		if leftDepth == rightDepth {
			return resolvedDirs[i] < resolvedDirs[j]
		}
		return leftDepth < rightDepth
	})

	roots := make([]string, 0, len(resolvedDirs))
	for _, candidate := range resolvedDirs {
		nested := false
		for _, root := range roots {
			if isWithinPath(candidate, root) {
				nested = true
				break
			}
		}

		if !nested {
			roots = append(roots, candidate)
		}
	}

	return roots, nil
}

func shouldExcludePath(path string, excluded []string) bool {
	for _, excludedDir := range excluded {
		if isWithinPath(path, excludedDir) {
			return true
		}
	}
	return false
}

func filesFromWorkingDirs(dirs []string, recursive bool, excludedDirs []string) ([]string, error) {
	files := make([]string, 0)

	roots, err := pruneNestedRoots(dirs)
	if err != nil {
		return nil, err
	}

	resolvedExcluded := make([]string, 0, len(excludedDirs))
	for _, excludedDir := range excludedDirs {
		resolved, absErr := filepath.Abs(excludedDir)
		if absErr != nil {
			return nil, absErr
		}
		resolvedExcluded = append(resolvedExcluded, resolved)
	}

	for _, dir := range roots {
		rootExclusions := make([]string, 0, len(resolvedExcluded))
		for _, excluded := range resolvedExcluded {
			if excluded == dir {
				continue
			}
			if isWithinPath(excluded, dir) {
				rootExclusions = append(rootExclusions, excluded)
			}
		}

		if recursive {
			err := filepath.WalkDir(dir, func(path string, entry os.DirEntry, walkErr error) error {
				if walkErr != nil {
					return walkErr
				}

				if entry.IsDir() && path != dir && shouldExcludePath(path, rootExclusions) {
					return filepath.SkipDir
				}

				if entry.Type().IsRegular() {
					files = append(files, path)
				}

				return nil
			})
			if err != nil {
				return nil, err
			}
			continue
		}

		entries, readErr := os.ReadDir(dir)
		if readErr != nil {
			return nil, readErr
		}

		for _, entry := range entries {
			entryPath := filepath.Join(dir, entry.Name())
			if entry.Type().IsRegular() && !shouldExcludePath(entryPath, rootExclusions) {
				files = append(files, entryPath)
			}
		}
	}

	return files, nil
}
