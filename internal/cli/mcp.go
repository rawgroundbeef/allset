package cli

import (
	"context"
	"errors"
	"fmt"
	"github.com/rawgroundbeef/allset/internal/config"
	"strings"
)

func (a App) mcpCommand(ctx context.Context, f config.File, args []string) int {
	if len(args) == 0 {
		return a.fail(errors.New("use allset mcp list|sync [PROJECT], or allset mcp login SERVER [PROJECT]"))
	}
	operation := args[0]
	args = args[1:]
	if operation != "list" && operation != "sync" && operation != "login" {
		return a.fail(errors.New("MCP operation must be list, sync, or login"))
	}
	server := ""
	if operation == "login" {
		if len(args) == 0 || strings.HasPrefix(args[0], "-") {
			return a.fail(errors.New("name the MCP server to sign in"))
		}
		server = args[0]
		args = args[1:]
	}
	name := "."
	if len(args) > 0 && !strings.HasPrefix(args[0], "-") {
		name = args[0]
		args = args[1:]
	}
	flags := a.flags("mcp " + operation)
	dry := flags.Bool("dry-run", false, "Inspect dispatch without remote changes")
	if err := flags.Parse(args); err != nil {
		return a.fail(err)
	}
	if flags.NArg() != 0 {
		return a.fail(errors.New("unexpected MCP arguments"))
	}
	p, err := a.resolve(ctx, f, name)
	if err != nil {
		return a.fail(err)
	}
	if operation == "list" {
		return a.json(struct {
			Project string                `json:"project"`
			MCPs    map[string]config.MCP `json:"mcps"`
		}{p.Name, p.MCPs})
	}
	backend, err := a.Strategies.Lookup(p.Backend)
	if err != nil {
		return a.fail(err)
	}
	plan, err := backend.Plan(p, "mcp-"+operation, server, 0, "none")
	if err != nil {
		return a.fail(err)
	}
	if *dry {
		return a.json(plan)
	}
	if plan.Interactive && !a.Interactive {
		return a.fail(errors.New("MCP sign-in requires an interactive local terminal"))
	}
	if a.Exec == nil {
		return a.fail(errors.New("executor unavailable"))
	}
	fmt.Fprintf(a.Out, "%s · MCP %s\n", p.Name, operation)
	if err := a.Exec(plan); err != nil {
		return a.fail(err)
	}
	if operation == "sync" {
		fmt.Fprintln(a.Out, "Settings applied. Open a new agent session or use its native MCP reload; existing sessions were not restarted.")
	}
	return 0
}
