package cmd

import "github.com/spf13/cobra"

func NewRootCmd() *cobra.Command {
	rootCmd := &cobra.Command{
		Use:   "organizer",
		Short: "File organiser CLI",
	}

	rootCmd.AddCommand(newRenameCmd())
	rootCmd.AddCommand(newSeparateCmd())
	rootCmd.AddCommand(newMergeCmd())
	rootCmd.AddCommand(newRevertCmd())

	return rootCmd
}
