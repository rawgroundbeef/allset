//go:build darwin || linux

// Package entrypoint starts AllSet in the caller's terminal.
package entrypoint

import (
	"context"
	"fmt"
	"os"
	"syscall"

	"github.com/rawgroundbeef/allset/internal/execution"
	"github.com/rawgroundbeef/allset/internal/wiring"
)

func Run() int {
	home, err := os.UserHomeDir()
	if err != nil {
		fmt.Fprintln(os.Stderr, "allset: cannot determine home directory")
		return 1
	}
	app := wiring.Default(home, os.Stdout, os.Stderr)
	if info, err := os.Stdin.Stat(); err == nil {
		app.Interactive = info.Mode()&os.ModeCharDevice != 0
	}
	// Preserve foreground terminal signals, resize events, and exit codes when
	// handing the connection to the controller and its native SSH client.
	app.Exec = func(plan execution.Plan) error {
		return syscall.Exec(plan.Executable, append([]string{plan.Executable}, plan.Args...), os.Environ())
	}
	return app.Run(context.Background(), os.Args[1:])
}
