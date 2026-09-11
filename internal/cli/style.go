package cli

import (
	"fmt"
	"os"
)

// printOperation frames interactive work without styling captured or machine output.
func (a App) printOperation(project, operation string) {
	_, noColor := os.LookupEnv("NO_COLOR")
	if a.richTerminal() && !noColor && os.Getenv("CI") == "" {
		fmt.Fprintf(a.Out, "\n  \x1b[1m%s\x1b[0m \x1b[2m· %s\x1b[0m\n\n", project, operation)
		return
	}
	fmt.Fprintf(a.Out, "%s · %s\n", project, operation)
}
