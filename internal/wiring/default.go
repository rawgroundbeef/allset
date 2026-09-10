// Package wiring selects installed strategies; the command dispatcher knows no
// provider-specific paths, machine ID formats, interpreters, or account adapters.
package wiring

import (
	"errors"
	"io"
	"os"
	"os/exec"
	"path/filepath"

	"github.com/rawgroundbeef/allset/internal/cli"
	"github.com/rawgroundbeef/allset/internal/config"
	"github.com/rawgroundbeef/allset/internal/execution"
	"github.com/rawgroundbeef/allset/internal/legacy"
	boxstrategy "github.com/rawgroundbeef/allset/internal/strategies/box"
	"github.com/rawgroundbeef/allset/internal/strategy"
)

func Default(home string, out, stderr io.Writer) cli.App {
	configRoot := os.Getenv("XDG_CONFIG_HOME")
	if configRoot == "" {
		configRoot = filepath.Join(home, ".config")
	}
	path := registryPath(configRoot)
	python, _ := exec.LookPath("python3")
	controller := legacy.Backend{Root: filepath.Join(home, ".local", "share", "box-herdr"), Box: filepath.Join(home, ".ascii", "bin", "box"), Python: python}
	return cli.App{ConfigPath: path, Strategies: strategy.Registry{"box": boxstrategy.Strategy{Controller: controller}},
		Import: func(source string) (config.File, error) {
			if source != "box-herdr" {
				return config.File{}, errors.New("unknown import source")
			}
			return controller.Import()
		}, In: os.Stdin, Out: out, Err: stderr, Capture: execution.Capture, LookPath: exec.LookPath}
}

// registryPath resolves the local registry without reading or modifying it.
// Explicit --config overrides this default in the CLI.
func registryPath(configRoot string) string {
	if path := os.Getenv("ALLSET_CONFIG"); path != "" {
		return path
	}
	return filepath.Join(configRoot, "allset", "config.json")
}
