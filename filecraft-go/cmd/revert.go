package cmd

import (
	"fmt"

	"filecraft-go/internal/organizer"

	"github.com/spf13/cobra"
)

func newRevertCmd() *cobra.Command {
	var directory string
	var historyFile string
	var dryRun bool
	var keepHistory bool

	cmd := &cobra.Command{
		Use:   "revert",
		Short: "Revert moves using history",
		RunE: func(cmd *cobra.Command, args []string) error {
			if err := validateOptionalDirectory(directory, "--directory"); err != nil {
				return err
			}

			var reverted int
			if err := runWithSpinner("Reverting files", cmd.ErrOrStderr(), func() error {
				count, err := organizer.RevertHistory(
					historyFile,
					directory,
					dryRun,
					!keepHistory,
					cmd.OutOrStdout(),
				)
				reverted = count
				return err
			}); err != nil {
				return err
			}

			fmt.Fprintf(cmd.OutOrStdout(), "Reverted %d file(s).\n", reverted)
			return nil
		},
	}

	cmd.Flags().StringVar(&directory, "directory", "", "Directory containing history files")
	cmd.Flags().StringVar(&historyFile, "history-file", "", "Specific history file path to revert")
	cmd.Flags().BoolVar(&dryRun, "dry-run", false, "Preview revert actions without making changes")
	cmd.Flags().BoolVar(&keepHistory, "keep-history", false, "Do not delete history file after successful revert")

	return cmd
}
