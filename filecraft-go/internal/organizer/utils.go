package organizer

import (
	"os"
	"path/filepath"
	"sort"
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
		candidate := filepath.Join(dir, stem+"_"+itoa(index)+ext)
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

	return strings.ToLower(filepath.Ext(name))
}

func filesFromWorkingDirs(dirs []string) ([]string, error) {
	files := make([]string, 0)

	for _, dir := range dirs {
		entries, err := os.ReadDir(dir)
		if err != nil {
			return nil, err
		}

		for _, entry := range entries {
			if entry.Type().IsRegular() {
				files = append(files, filepath.Join(dir, entry.Name()))
			}
		}
	}

	return files, nil
}

func itoa(n int) string {
	if n == 0 {
		return "0"
	}

	negative := n < 0
	if negative {
		n = -n
	}

	buf := make([]byte, 0, 11)
	for n > 0 {
		buf = append(buf, byte('0'+(n%10)))
		n /= 10
	}

	if negative {
		buf = append(buf, '-')
	}

	for i, j := 0, len(buf)-1; i < j; i, j = i+1, j-1 {
		buf[i], buf[j] = buf[j], buf[i]
	}

	return string(buf)
}
