package cli

import (
	"bufio"
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/rawgroundbeef/allset/internal/config"
)

func (a App) location() (config.Location, error) {
	cwd := a.CurrentDir
	if cwd == "" {
		var err error
		cwd, err = os.Getwd()
		if err != nil {
			return config.Location{}, err
		}
	}
	return config.Discover(cwd)
}

func (a App) repository(ctx context.Context, root string) (string, error) {
	if a.LookPath == nil || a.Capture == nil {
		return "", errors.New("Git discovery is unavailable")
	}
	git, err := a.LookPath("git")
	if err != nil {
		return "", errors.New("Git is required to identify this project")
	}
	remote, err := a.Capture(ctx, git, "-C", root, "remote", "get-url", "origin")
	if err != nil {
		return "", errors.New("this project needs an origin remote before AllSet can configure remote access")
	}
	// Normalize before printing or persisting. Git URLs can contain credentials.
	key, err := config.RepositoryKey(strings.TrimSpace(string(remote)))
	if err != nil {
		return "", err
	}
	return "https://" + key, nil
}

func (a App) current(ctx context.Context, f config.File) (config.Project, error) {
	location, err := a.location()
	if err != nil {
		return config.Project{}, err
	}
	repo, err := a.repository(ctx, location.Root)
	if err != nil {
		return config.Project{}, err
	}
	if location.ManifestPath == "" {
		return f.ResolveRepository(repo)
	}
	m, err := config.LoadProject(location.ManifestPath)
	if err != nil {
		return config.Project{}, fmt.Errorf("invalid %s: %w", filepath.Base(location.ManifestPath), err)
	}
	want, _ := config.RepositoryKey(m.Repository)
	actual, _ := config.RepositoryKey(repo)
	if want != actual {
		return config.Project{}, errors.New("project config repository does not match this checkout's origin; no machine opened")
	}
	if err := config.CheckLocalBinding(f, m.Project); err != nil {
		return config.Project{}, err
	}
	return m.Project, nil
}

// initialize creates a reviewable repository entry point. It never provisions a
// VM, guesses credentials, executes a package script, or replaces an existing file.
func (a App) initialize(ctx context.Context, f config.File, args []string) (config.Project, error) {
	flags := a.flags("init")
	name := flags.String("name", "", "Project name")
	backend := flags.String("backend", "", "Compute provider")
	accept := flags.Bool("yes", false, "Accept inferred project identity and provider")
	if err := flags.Parse(args); err != nil {
		return config.Project{}, err
	}
	if flags.NArg() != 0 {
		return config.Project{}, errors.New("use allset init [--name NAME] [--backend SERVICE] [--yes]")
	}
	location, err := a.location()
	if err != nil {
		return config.Project{}, err
	}
	if location.ManifestPath != "" {
		p, err := a.current(ctx, f)
		if err != nil {
			return p, err
		}
		if (*name != "" && p.Name != *name) || (*backend != "" && p.Backend != *backend) {
			return p, errors.New("project config already exists with a different binding; it was not replaced")
		}
		fmt.Fprintln(a.Out, "Using", location.ManifestPath)
		if !*accept {
			if _, err := a.reviewSetup(p, true); err != nil {
				return p, err
			}
		}
		return p, nil
	}
	repo, err := a.repository(ctx, location.Root)
	if err != nil {
		return config.Project{}, err
	}
	p, known := f.ResolveRepository(repo)
	if known != nil && !errors.Is(known, config.ErrUnregistered) {
		return p, known
	}
	fmt.Fprintf(a.Out, "Project setup: %s\n", repo)
	fmt.Fprintln(a.Out, "Shared project settings go in .allset. Account choices and credentials stay private.")
	var reader *bufio.Reader
	if !*accept {
		reader, err = a.reviewSetup(p, false)
		if err != nil {
			return p, err
		}
	}
	if known == nil {
		if (*name != "" && p.Name != *name) || (*backend != "" && p.Backend != *backend) {
			return p, errors.New("requested project identity conflicts with this repository's saved environment")
		}
		fmt.Fprintln(a.Out, "Using this repository's saved project settings.")
	} else {
		key, _ := config.RepositoryKey(repo)
		inferred := strings.TrimSuffix(filepath.Base(key), ".git")
		inferred = strings.Trim(strings.Map(func(r rune) rune {
			if r >= 'a' && r <= 'z' || r >= '0' && r <= '9' || r == '-' {
				return r
			}
			return '-'
		}, strings.ToLower(inferred)), "-")
		if *name != "" {
			inferred = *name
		}
		provider := *backend
		if provider == "" && len(a.Strategies.Names()) == 1 {
			provider = a.Strategies.Names()[0]
		}
		if !*accept {
			fmt.Fprintln(a.Out, "Press Enter to accept a suggested value, or Ctrl+C to cancel.")
			inferred, err = setupAnswer(reader, a.Out, "1/2 Project name", inferred)
			if err != nil {
				return p, err
			}
			provider, err = setupAnswer(reader, a.Out, "2/2 Compute provider ("+strings.Join(a.Strategies.Names(), ", ")+")", provider)
			if err != nil {
				return p, err
			}
		}
		p = config.Project{Name: inferred, Repository: repo, Backend: provider}
	}
	if _, err := a.Strategies.Lookup(p.Backend); err != nil {
		return p, err
	}
	if err := config.CheckLocalBinding(f, p); err != nil {
		return p, err
	}
	path := filepath.Join(location.Root, config.ProjectFilename)
	if err := config.WriteProject(path, config.Manifest{Version: 1, Project: p}); err != nil {
		return p, err
	}
	fmt.Fprintf(a.Out, "Saved %s\nProject: %s · Compute: %s\n", path, p.Name, p.Backend)
	return p, nil
}

func (a App) initCommand(ctx context.Context, args []string) int {
	f, err := config.Load(a.ConfigPath)
	if errors.Is(err, os.ErrNotExist) {
		f = config.File{Version: 3, Projects: []config.Project{}}
	} else if err != nil {
		return a.fail(err)
	}
	p, err := a.initialize(ctx, f, args)
	if errors.Is(err, errSetupHandoff) {
		return 0
	}
	if err != nil {
		return a.fail(err)
	}
	s, err := a.Strategies.Lookup(p.Backend)
	if err != nil {
		return a.fail(err)
	}
	if err := s.Validate(p); err != nil {
		fmt.Fprintln(a.Err, "Project config saved, but environment setup is incomplete:", err)
		fmt.Fprintln(a.Err, "No VM was created. Run allset config guide for the remaining provider/account setup.")
		return 2
	}
	fmt.Fprintln(a.Out, "Project binding verified. Run allset to open it; VM and account readiness are checked during opening.")
	return 0
}

// projectConfigCommand remains read-only, including when a provider is unconfigured.
func (a App) projectConfigCommand(ctx context.Context, action string) int {
	loc, err := a.location()
	if err != nil {
		return a.fail(err)
	}
	path := loc.ManifestPath
	if path == "" {
		path = filepath.Join(loc.Root, config.ProjectFilename)
	}
	if action == "path" {
		fmt.Fprintln(a.Out, path)
		return 0
	}
	m, err := config.LoadProject(path)
	if err != nil {
		return a.fail(err)
	}
	f, err := config.Load(a.ConfigPath)
	if errors.Is(err, os.ErrNotExist) {
		f = config.File{Version: 3, Projects: []config.Project{}}
	} else if err != nil {
		return a.fail(err)
	}
	p, err := a.current(ctx, f)
	if err != nil {
		return a.fail(err)
	}
	if action == "show" {
		return a.json(m)
	}
	backend, err := a.Strategies.Lookup(p.Backend)
	if err != nil {
		return a.fail(err)
	}
	if err := backend.Validate(p); err != nil {
		return a.fail(err)
	}
	fmt.Fprintf(a.Out, "Valid %s and local project binding. Runtime readiness has not been checked.\n", filepath.Base(path))
	return 0
}
