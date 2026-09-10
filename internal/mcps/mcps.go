// Package mcps owns native agent MCP configuration independently of compute and UI.
package mcps

import _ "embed"

// Runtime is sent over authenticated SSH. It only changes AllSet-owned MCP
// entries; native agent auth, unrelated settings, and running processes survive.
//
//go:embed runtime.py
var Runtime string

// Bridge stages or inspects MCPs on an already-running, identity-verified host.
