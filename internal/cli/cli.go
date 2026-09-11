// Package cli exposes project operations without owning a terminal UI or an agent loop.
package cli

import (
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"strings"
	"text/tabwriter"

	"github.com/rawgroundbeef/allset/internal/config"
	"github.com/rawgroundbeef/allset/internal/execution"
	"github.com/rawgroundbeef/allset/internal/strategy"
	"github.com/rawgroundbeef/allset/internal/terminal"
)

const Version = "0.5.0-alpha.1"

type App struct {
	ConfigPath  string
	CurrentDir  string
	In          io.Reader
	Strategies  strategy.Registry
	Import      func(string) (config.File, error)
	Out, Err    io.Writer
	Interactive bool
	Exec        func(execution.Plan) error
	Capture     func(context.Context, string, ...string) ([]byte, error)
	LookPath    func(string) (string, error)
}

const help = `AllSet — open your remote project and choose your agent.

  allset                            Review setup if needed; otherwise open this project
  allset init                       Review project configuration without opening
  allset dashboard                    Open/resume a registered project
  allset .                         Explicit form of bare allset
  allset mcp list [PROJECT]         Show this project's MCP declarations
  allset mcp sync [PROJECT]         Apply native MCP settings on its running VM
  allset mcp login SERVER [PROJECT] Sign in to a declared Trigger MCP
  allset projects                  List registered projects
  allset backends                  List installed service strategies
  allset status dashboard [--cached]  Check the VM; cached output is labeled
  allset doctor dashboard [--offline] Diagnose without changing anything
  allset login dashboard codex        Sign in to one project's agent account
  allset connect dashboard            Connect in this terminal; never resumes the VM
  allset resume dashboard             Resume/open the saved project shell
  allset collect dashboard            Save changes from the default project shell
  allset stop dashboard               Save results and stop this project's VM
  allset config import SOURCE      Import registrations from a supported old format
  allset config validate            Validate registry and repository bindings
  allset config show [PROJECT]      Inspect registration or project account bindings
  allset config schema             Print the supported registry JSON Schema
  allset config guide              Print the agent-assisted configuration guide
  allset config claude [PROJECT]    Sign in to Claude on this project's running Box
  allset config codex [PROJECT]     Sign in to Codex on this project's running Box
  allset config cursor [PROJECT]    Sign in to Cursor on this project's running Box
  allset config path                Print the registry location

Use --dry-run on open/resume/connect/login/collect/stop to inspect dispatch.
Open/resume accept --ttl SECONDS (default 7200; existing trial cap retained).
Agent sign-in uses the existing running VM; open the project first if it is stopped.
Open/resume/connect accept --attach auto|workspace|herdr|ssh|none|terminal (default auto).
Auto in a Herdr pane prepares a remote workspace, then returns for a sidebar click.
Elsewhere, auto opens an ordinary SSH shell without installing a session manager.
--attach workspace prepares the Herdr sidebar handoff explicitly.
--attach herdr opens a separate Herdr client; --attach terminal attaches to its PTY.
--attach none prepares the project without opening a connection.
No terminal setting belongs in project config. No client takeover.
Projects/status/doctor and dry-run accept --json. Doctor exits 2 for incomplete
checks, 1 for failures. --config PATH must precede the command.

Without .allset, interactive open reviews project setup and returns without opening.
Choose terminal guidance, a prompt for your coding agent, or cancel. Saved bindings
are shown for review. Run allset again to open; allset init reopens setup anytime.
Read-only commands and dry-run never create configuration.

Box is the first compute backend. Its current workspace strategy delegates setup
and sign-ins to the bundled controller; Python remains required for that adapter.
Other providers require their own strategies. No agent starts by default.
It works in normal terminals, cmux, and Herdr Local panes. Run it on your laptop.
`

func (a App) fail(err error) int { fmt.Fprintln(a.Err, "allset:", err); return 1 }
func (a App) json(v any) int {
	enc := json.NewEncoder(a.Out)
	enc.SetIndent("", "  ")
	if err := enc.Encode(v); err != nil {
		return a.fail(err)
	}
	return 0
}

func (a App) flags(name string) *flag.FlagSet {
	f := flag.NewFlagSet(name, flag.ContinueOnError)
	f.SetOutput(a.Err)
	return f
}

func (a App) load() (config.File, error) {
	f, err := config.Load(a.ConfigPath)
	if errors.Is(err, os.ErrNotExist) {
		return f, errors.New("no registry yet; run allset config guide to configure your projects")
	}
	return f, err
}

func (a App) resolve(ctx context.Context, f config.File, name string) (config.Project, error) {
	if name != "." {
		return f.Resolve(name)
	}
	return a.current(ctx, f)
}

func (a App) configCommand(ctx context.Context, args []string) int {
	if len(args) == 2 && args[1] == "--project" && (args[0] == "show" || args[0] == "validate" || args[0] == "path") {
		return a.projectConfigCommand(ctx, args[0])
	}
	if len(args) > 0 && args[0] == "show" && (len(args) == 1 || (len(args) == 2 && args[1] == "--json")) {
		if loc, err := a.location(); err == nil && loc.ManifestPath != "" {
			return a.projectConfigCommand(ctx, "show")
		} else if err != nil && !errors.Is(err, config.ErrNoProject) {
			return a.fail(err)
		}
	}
	if len(args) == 2 && args[0] == "show" && args[1] == "--registry" {
		args = args[:1]
	}
	if (len(args) == 1 && (args[0] == "schema" || args[0] == "guide")) || (len(args) == 2 && args[0] == "schema" && args[1] == "--project") {
		document := config.RegistrySchema
		if len(args) == 2 {
			document = config.ProjectSchema
		}
		if args[0] == "guide" {
			document = config.AgentGuide
		}
		_, err := fmt.Fprint(a.Out, document)
		if err != nil {
			return a.fail(err)
		}
		return 0
	}
	if len(args) > 0 && args[0] == "show" {
		name := ""
		rest := args[1:]
		if len(rest) > 0 && !strings.HasPrefix(rest[0], "-") {
			name, rest = rest[0], rest[1:]
		}
		flags := a.flags("config show")
		asJSON := flags.Bool("json", true, "JSON output (the default)")
		if err := flags.Parse(rest); err != nil {
			return a.fail(err)
		}
		if flags.NArg() != 0 {
			return a.fail(errors.New("use config show [PROJECT] [--json]"))
		}
		if !*asJSON {
			return a.fail(errors.New("config show emits JSON; omit --json=false"))
		}
		f, err := a.load()
		if err != nil {
			return a.fail(err)
		}
		if name == "" {
			return a.json(f)
		}
		p, err := a.resolve(ctx, f, name)
		if err != nil {
			return a.fail(err)
		}
		backend, err := a.Strategies.Lookup(p.Backend)
		if err != nil {
			return a.fail(err)
		}
		view, err := backend.Inspect(p)
		if err != nil {
			return a.fail(err)
		}
		return a.json(view)
	}
	if len(args) == 1 && args[0] == "path" {
		fmt.Fprintln(a.Out, a.ConfigPath)
		return 0
	}
	if len(args) == 2 && args[0] == "import" {
		if a.Import == nil {
			return a.fail(errors.New("this import source is unavailable"))
		}
		f, err := a.Import(args[1])
		if err != nil {
			return a.fail(err)
		}
		if err := config.WriteNew(a.ConfigPath, f); err != nil {
			return a.fail(err)
		}
		fmt.Fprintf(a.Out, "Registered %d projects in %s\nCredentials and runtime state were not copied.\n", len(f.Projects), a.ConfigPath)
		return 0
	}
	if len(args) == 1 && args[0] == "validate" {
		f, err := a.load()
		if err != nil {
			return a.fail(err)
		}
		for _, p := range f.Projects {
			backend, err := a.Strategies.Lookup(p.Backend)
			if err != nil {
				return a.fail(err)
			}
			if err := backend.Validate(p); err != nil {
				return a.fail(fmt.Errorf("%s: %w", p.Name, err))
			}
		}
		fmt.Fprintf(a.Out, "Valid registry: %d project bindings. Runtime readiness has not been checked.\n", len(f.Projects))
		return 0
	}
	return a.fail(errors.New("use config claude|codex|cursor [PROJECT], config show [PROJECT], config schema, config guide, config path, config validate, or config import SOURCE"))
}

func (a App) projects(f config.File, args []string) int {
	flags := a.flags("projects")
	asJSON := flags.Bool("json", false, "JSON output")
	if err := flags.Parse(args); err != nil {
		return a.fail(err)
	}
	if flags.NArg() != 0 {
		return a.fail(errors.New("projects accepts no positional arguments"))
	}
	if *asJSON {
		return a.json(f.Projects)
	}
	w := tabwriter.NewWriter(a.Out, 0, 4, 2, ' ', 0)
	fmt.Fprintln(w, "PROJECT\tALIASES\tREPOSITORY\tBACKEND")
	for _, p := range f.Projects {
		fmt.Fprintf(w, "%s\t%s\t%s\t%s\n", p.Name, strings.Join(p.Aliases, ", "), p.Repository, p.Backend)
	}
	w.Flush()
	return 0
}

// Run validates all arguments and project ownership before handing over the terminal.
func (a App) Run(ctx context.Context, args []string) int {
	global := a.flags("allset")
	path := global.String("config", a.ConfigPath, "Registry path")
	showHelp := global.Bool("help", false, "Help")
	shortHelp := global.Bool("h", false, "Help")
	showVersion := global.Bool("version", false, "Version")
	globalDry := global.Bool("dry-run", false, "Inspect opening the current project")
	globalJSON := global.Bool("json", false, "JSON output")
	globalAttach := global.String("attach", "auto", "Connection override")
	globalTTL := global.Int("ttl", 7200, "Auto-stop seconds")
	if err := global.Parse(args); err != nil {
		return a.fail(err)
	}
	a.ConfigPath = *path
	args = global.Args()
	var forwarded []string
	global.Visit(func(f *flag.Flag) {
		switch f.Name {
		case "dry-run":
			forwarded = append(forwarded, "--dry-run="+fmt.Sprint(*globalDry))
		case "json":
			forwarded = append(forwarded, "--json="+fmt.Sprint(*globalJSON))
		case "attach":
			forwarded = append(forwarded, "--attach="+*globalAttach)
		case "ttl":
			forwarded = append(forwarded, "--ttl="+fmt.Sprint(*globalTTL))
		}
	})
	args = append(args, forwarded...)
	if *showHelp || *shortHelp || (len(args) > 0 && args[0] == "help") {
		fmt.Fprint(a.Out, help)
		return 0
	}
	if *showVersion || (len(args) == 1 && args[0] == "version") {
		fmt.Fprintln(a.Out, "allset "+Version)
		return 0
	}
	if len(args) > 0 && args[0] == "init" {
		return a.initCommand(ctx, args[1:])
	}
	// Project-local sign-in shortcuts use the same resolution, dry-run and
	// interactive dispatch as explicit login. They never enter project setup.
	if len(args) > 1 && args[0] == "config" {
		switch args[1] {
		case "claude", "codex", "cursor":
			agent, name, rest := args[1], ".", args[2:]
			if len(rest) > 0 && !strings.HasPrefix(rest[0], "-") {
				name, rest = rest[0], rest[1:]
			}
			args = append([]string{"login", name, agent}, rest...)
		}
	}
	if len(args) > 0 && args[0] == "config" {
		return a.configCommand(ctx, args[1:])
	}
	if len(args) > 0 && args[0] == "backends" {
		flags := a.flags("backends")
		asJSON := flags.Bool("json", false, "JSON output")
		if err := flags.Parse(args[1:]); err != nil {
			return a.fail(err)
		}
		if flags.NArg() != 0 {
			return a.fail(errors.New("backends accepts no positional arguments"))
		}
		if *asJSON {
			return a.json(a.Strategies.Names())
		}
		for _, name := range a.Strategies.Names() {
			fmt.Fprintln(a.Out, name)
		}
		return 0
	}
	f, err := config.Load(a.ConfigPath)
	if errors.Is(err, os.ErrNotExist) {
		f = config.File{Version: 3, Projects: []config.Project{}}
	} else if err != nil {
		return a.fail(err)
	}
	if len(args) > 0 && args[0] == "projects" {
		return a.projects(f, args[1:])
	}
	if len(args) > 0 && args[0] == "mcp" {
		return a.mcpCommand(ctx, f, args[1:])
	}
	operation, name := "open", "."
	if len(args) > 0 {
		switch args[0] {
		case "open", "resume", "connect", "stop", "status", "doctor", "login", "collect":
			operation = args[0]
			args = args[1:]
		}
		if len(args) > 0 && !strings.HasPrefix(args[0], "-") {
			name = args[0]
			args = args[1:]
		}
	}
	agent := ""
	if operation == "login" {
		if len(args) == 0 {
			return a.fail(errors.New("use allset login PROJECT claude|codex|cursor"))
		}
		agent = args[0]
		args = args[1:]
	}
	flags := a.flags(operation)
	asJSON := flags.Bool("json", false, "JSON output")
	var dry, cached, offline bool
	ttl := 7200
	attach := "auto"
	if operation == "status" {
		flags.BoolVar(&cached, "cached", false, "Read cached metadata only")
	} else if operation == "doctor" {
		flags.BoolVar(&offline, "offline", false, "Skip remote checks")
	} else {
		flags.BoolVar(&dry, "dry-run", false, "Show dispatch without running it")
	}
	if operation == "open" || operation == "resume" {
		flags.IntVar(&ttl, "ttl", 7200, "Auto-stop seconds")
	}
	if operation == "open" || operation == "resume" || operation == "connect" {
		flags.StringVar(&attach, "attach", "auto", "auto, workspace, herdr, ssh, none, or terminal")
	}
	if err := flags.Parse(args); err != nil {
		return a.fail(err)
	}
	if flags.NArg() != 0 {
		return a.fail(errors.New("unexpected arguments; run allset --help"))
	}
	if *asJSON && !dry && operation != "status" && operation != "doctor" {
		return a.fail(errors.New("--json on lifecycle operations requires --dry-run"))
	}
	attach, err = terminal.Resolve(attach, os.Getenv("HERDR_ENV") == "1")
	if err != nil {
		return a.fail(err)
	}
	p, err := a.resolve(ctx, f, name)
	if (err == nil || errors.Is(err, config.ErrUnregistered)) && name == "." && operation == "open" && !dry && !*asJSON && a.Interactive {
		location, locationErr := a.location()
		if locationErr != nil {
			return a.fail(locationErr)
		}
		if location.ManifestPath == "" {
			// A first-run setup is the same configuration-only operation as
			// explicit init. It must never fall through into a VM lifecycle plan.
			return a.initCommand(ctx, nil)
		}
	}
	if err != nil {
		return a.fail(err)
	}
	backend, err := a.Strategies.Lookup(p.Backend)
	if err != nil {
		return a.fail(err)
	}
	if err := backend.Validate(p); err != nil {
		return a.fail(err)
	}
	switch operation {
	case "status":
		s, err := backend.Status(ctx, p, cached)
		if err != nil {
			return a.fail(err)
		}
		if *asJSON {
			return a.json(s)
		}
		fmt.Fprintf(a.Out, "%s: %s\nMachine: %s\nSource: %s\nChecked: %s\n", s.Project, s.State, s.MachineID, s.Source, s.CheckedAt)
		if s.AutoStop != "" {
			fmt.Fprintln(a.Out, "Auto-stop:", s.AutoStop)
		}
		fmt.Fprintln(a.Out, "VM state only; agent, credential, and preview readiness are not implied.")
		return 0
	case "doctor":
		d := backend.Diagnose(ctx, p, offline)
		if *asJSON {
			if code := a.json(d); code != 0 {
				return code
			}
		} else {
			fmt.Fprintf(a.Out, "%s: %s\n", d.Project, d.Overall)
			for _, check := range d.Checks {
				fmt.Fprintf(a.Out, "  %-9s %-20s %s\n", check.State, check.Name, check.Detail)
			}
		}
		switch d.Overall {
		case "ready":
			return 0
		case "incomplete":
			return 2
		default:
			return 1
		}
	}
	plan, err := backend.Plan(p, operation, agent, ttl, attach)
	if err != nil {
		return a.fail(err)
	}
	if dry {
		if *asJSON {
			return a.json(plan)
		}
		fmt.Fprintf(a.Out, "%s: %s via %s\n%s\nNo operation executed.\n", p.Name, operation, plan.Backend, plan.DisplayCommand())
		return 0
	}
	if plan.Interactive && !a.Interactive {
		return a.fail(errors.New("this operation needs an interactive local terminal; use --dry-run to inspect it"))
	}
	if a.Exec == nil {
		return a.fail(errors.New("interactive executor is unavailable"))
	}
	fmt.Fprintf(a.Out, "%s · %s\n", p.Name, operation)
	if err := a.Exec(plan); err != nil {
		return a.fail(err)
	}
	return 0
}
