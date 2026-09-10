package config

import _ "embed"

// RegistrySchema describes the supported registry, not future project manifest fields.
//
//go:embed registry.schema.json
var RegistrySchema string

// AgentGuide documents the supported configuration workflow without assuming an agent vendor.
//
//go:embed agent-guide.md
var AgentGuide string

// ProjectSchema describes the repository entry point.
//
//go:embed allset.schema.json
var ProjectSchema string
