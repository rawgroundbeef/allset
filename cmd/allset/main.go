//go:build darwin || linux

// AllSet opens independently configured remote projects from any terminal.
package main

import (
	"os"

	"github.com/rawgroundbeef/allset/internal/entrypoint"
)

func main() { os.Exit(entrypoint.Run()) }
