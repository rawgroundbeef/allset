// Package terminal chooses a connection independently of the compute provider.
package terminal

import (
	_ "embed"
	"fmt"
)

// Bridge is embedded while workspace preparation still runs in Python. Its
// target contract is independent of the compute service and installed controller.
//
//go:embed connect.py
var Bridge string

func Valid(name string) bool {
	return name == "herdr" || name == "ssh" || name == "none"
}

// Resolve uses the caller's current terminal by default. UI integrations are
// explicit connection overrides, never repository configuration.
func Resolve(override string) (string, error) {
	if override == "auto" {
		return "ssh", nil
	}
	if !Valid(override) && override != "terminal" {
		return "", fmt.Errorf("unsupported attachment; choose auto, herdr, ssh, none, or terminal")
	}
	return override, nil
}
