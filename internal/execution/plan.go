package execution

import "strings"

type Plan struct {
	Project     string   `json:"project"`
	Operation   string   `json:"operation"`
	Backend     string   `json:"backend"`
	Executable  string   `json:"executable"`
	Args        []string `json:"args"`
	Interactive bool     `json:"interactive"`
	Attachment  string   `json:"attachment,omitempty"`
}

func (p Plan) DisplayCommand() string {
	parts := append([]string{p.Executable}, p.Args...)
	for i, part := range parts {
		parts[i] = "'" + strings.ReplaceAll(part, "'", "'\"'\"'") + "'"
	}
	return strings.Join(parts, " ")
}
