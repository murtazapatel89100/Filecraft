package cmd

import (
	"file-organiser-go/internal/organizer"
	"os"

	"github.com/spf13/cobra"
)

func newRenameCmd() *cobra.Command {
	var targetDir string
	var workingDir string
	var dryRun bool
	var saveHistory bool

	cmd := &cobra.Command{
		Use:   "rename",
		Short: "Rename files sequentially",
		RunE: func(cmd *cobra.Command, args []string) error {
			resolvedTargetDir, err := resolveTargetDir(targetDir, cmd.InOrStdin(), cmd.OutOrStdout(), os.Getwd)
			if err != nil {
				return err
			}

			if err := validateOptionalDirectory(workingDir, "--working-dir"); err != nil {
				return err
			}

			cfg := organizer.Config{
				TargetDir:   resolvedTargetDir,
				WorkingDir:  workingDir,
				DryRun:      dryRun,
				SaveHistory: saveHistory,
			}

			fo, err := organizer.NewFileOrganizer(cfg)
			if err != nil {
				return err
			}

			return fo.Rename(cmd.OutOrStdout())
		},
	}

	cmd.Flags().StringVar(&targetDir, "target-dir", "", "Where renamed files are moved")
	cmd.Flags().StringVar(&workingDir, "working-dir", "", "Source directory to process")
	cmd.Flags().BoolVar(&dryRun, "dry-run", false, "Preview actions without making changes")
	cmd.Flags().BoolVar(&saveHistory, "history", false, "Save operation history")

	return cmd
}
