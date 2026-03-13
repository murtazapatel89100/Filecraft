package cmd

import (
	"fmt"
	"io"
	"os"
	"time"
)

func runWithSpinner(message string, errOut io.Writer, action func() error) error {
	if !isTerminalWriter(errOut) {
		return action()
	}

	stop := make(chan struct{})
	done := make(chan struct{})

	go func() {
		defer close(done)
		frames := []rune{'|', '/', '-', '\\'}
		i := 0
		ticker := time.NewTicker(100 * time.Millisecond)
		defer ticker.Stop()

		for {
			select {
			case <-stop:
				return
			case <-ticker.C:
				fmt.Fprintf(errOut, "\r%s... %c", message, frames[i%len(frames)])
				i++
			}
		}
	}()

	success := false
	defer func() {
		close(stop)
		<-done
		status := "failed"
		if success {
			status = "done"
		}
		fmt.Fprintf(errOut, "\r%s... %s\n", message, status)
	}()

	if err := action(); err != nil {
		return err
	}

	success = true
	return nil
}

func isTerminalWriter(w io.Writer) bool {
	file, ok := w.(*os.File)
	if !ok {
		return false
	}

	info, err := file.Stat()
	if err != nil {
		return false
	}

	return (info.Mode() & os.ModeCharDevice) != 0
}
