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

//go:embed workspace.py
var WorkspaceBridge string

func Valid(name string) bool {
	return name == "herdr" || name == "ssh" || name == "none" || name == "workspace"
}

// Resolve chooses an interface from the caller context, never a target machine.
// In Herdr, auto prepares a remote workspace for the existing client's sidebar.
func Resolve(override string, inHerdr bool) (string, error) {
	if override == "auto" {
		if inHerdr {
			return "workspace", nil
		}
		return "ssh", nil
	}
	if !Valid(override) && override != "terminal" {
		return "", fmt.Errorf("unsupported attachment; choose auto, workspace, herdr, ssh, none, or terminal")
	}
	return override, nil
}
