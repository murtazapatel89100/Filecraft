package cmd

import (
	"filecraft-go/internal/organizer"

	"github.com/spf13/cobra"
)

func newSeparateCmd() *cobra.Command {
	var mode string
	var extension string
	var fileType string
	var sortDate string
	var targetDir string
	var workingDir string
	var recursive bool
	var dryRun bool
	var saveHistory bool

	cmd := &cobra.Command{
		Use:   "separate",
		Short: "Separate files by mode",
		RunE: func(cmd *cobra.Command, args []string) error {
			if err := validateOptionalDirectory(workingDir, "--working-dir"); err != nil {
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
				FileType:    fileType,
				SortDate:    sortDate,
				TargetDir:   resolvedTargetDir,
				WorkingDir:  workingDir,
				Recursive:   recursive,
				DryRun:      dryRun,
				SaveHistory: saveHistory,
			}

			fo, err := organizer.NewFileOrganizer(cfg)
			if err != nil {
				return err
			}

			return fo.Separate(cmd.OutOrStdout())
		},
	}

	cmd.Flags().StringVar(&mode, "mode", string(organizer.ModeExtension), "How to separate files: extension, date, extension_and_date, file")
	cmd.Flags().StringVar(&extension, "extension", "", "Extension to filter, e.g. .pdf or pdf")
	cmd.Flags().StringVar(&fileType, "file-type", "", "File type filter for --mode file (e.g. documents, images, pdf)")
	cmd.Flags().StringVar(&sortDate, "date", "", "Date in YYYY-MM-DD format")
	cmd.Flags().StringVar(&targetDir, "target-dir", "", "Where separated files are moved")
	cmd.Flags().StringVar(&workingDir, "working-dir", "", "Source directory to process")
	cmd.Flags().BoolVar(&recursive, "recursive", false, "Recursively include files from all subdirectories")
	cmd.Flags().BoolVar(&dryRun, "dry-run", false, "Preview actions without making changes")
	cmd.Flags().BoolVar(&saveHistory, "history", false, "Save operation history")

	return cmd
}
