package cmd

import (
	"filecraft-go/internal/organizer"

	"github.com/spf13/cobra"
)

func newMergeCmd() *cobra.Command {
	var mode string
	var extension string
	var sortDate string
	var targetDir string
	var workingDirs []string
	var recursive bool
	var dryRun bool
	var saveHistory bool

	cmd := &cobra.Command{
		Use:   "merge",
		Short: "Merge files from multiple working directories",
		RunE: func(cmd *cobra.Command, args []string) error {
			if err := validateRequiredDirectories(workingDirs, "--working-dir"); err != nil {
				return err
			}

			if err := validateOptionalISODate(sortDate); err != nil {
				return err
			}

			resolvedTargetDir, err := resolveTargetDir(targetDir, cmd.InOrStdin(), cmd.OutOrStdout(), dryRun)
			if err != nil {
				return err
			}

			cfg := organizer.Config{
				Mode:        organizer.Mode(mode),
				SortExt:     normalizeExtension(extension),
				SortDate:    sortDate,
				TargetDir:   resolvedTargetDir,
				WorkingDirs: workingDirs,
				Recursive:   recursive,
				DryRun:      dryRun,
				SaveHistory: saveHistory,
			}

			fo, err := organizer.NewFileOrganizer(cfg)
			if err != nil {
				return err
			}

			return runWithSpinner("Merging files", cmd.ErrOrStderr(), func() error {
				return fo.Merge(cmd.OutOrStdout())
			})
		},
	}

	cmd.Flags().StringVar(&mode, "mode", string(organizer.ModeExtension), "How to merge files: extension, date, extension_and_date, file")
	cmd.Flags().StringVar(&extension, "extension", "", "Extension to filter, e.g. .pdf or pdf")
	cmd.Flags().StringVar(&sortDate, "date", "", "Date in YYYY-MM-DD format")
	cmd.Flags().StringVar(&targetDir, "target-dir", "", "Where merged files are moved")
	cmd.Flags().StringSliceVar(&workingDirs, "working-dir", nil, "One or more source directories to merge from")
	cmd.Flags().BoolVar(&recursive, "recursive", false, "Recursively include files from all subdirectories of every --working-dir")
	cmd.Flags().BoolVar(&dryRun, "dry-run", false, "Preview actions without making changes")
	cmd.Flags().BoolVar(&saveHistory, "history", false, "Save operation history")

	return cmd
}
