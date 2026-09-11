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
func (a App) initialize(ctx context.Context, f config.File, args []string) (config.Project, *bufio.Reader, error) {
	flags := a.flags("init")
	name := flags.String("name", "", "Project name")
	backend := flags.String("backend", "", "Compute provider")
	accept := flags.Bool("yes", false, "Accept inferred project identity and provider")
	if err := flags.Parse(args); err != nil {
		return config.Project{}, nil, err
	}
	if flags.NArg() != 0 {
		return config.Project{}, nil, errors.New("use allset init [--name NAME] [--backend SERVICE] [--yes]")
	}
	location, err := a.location()
	if err != nil {
		return config.Project{}, nil, err
	}
	if location.ManifestPath != "" {
		p, err := a.current(ctx, f)
		if err != nil {
			return p, nil, err
		}
		if (*name != "" && p.Name != *name) || (*backend != "" && p.Backend != *backend) {
			return p, nil, errors.New("project config already exists with a different binding; it was not replaced")
		}
		fmt.Fprintln(a.Out, "Using", location.ManifestPath)
		if !*accept {
			reader, err := a.reviewSetup(p, true, nil)
			if err != nil {
				return p, nil, err
			}
			return p, reader, nil
		}
		return p, nil, nil
	}
	repo, err := a.repository(ctx, location.Root)
	if err != nil {
		return config.Project{}, nil, err
	}
	p, known := f.ResolveRepository(repo)
	if known != nil && !errors.Is(known, config.ErrUnregistered) {
		return p, nil, known
	}
	var reader *bufio.Reader
	if known == nil {
		if (*name != "" && p.Name != *name) || (*backend != "" && p.Backend != *backend) {
			return p, nil, errors.New("requested project identity conflicts with this repository's saved environment")
		}
		fmt.Fprintln(a.Out, "Using this repository's saved project settings.")
	} else {
		if !*accept {
			reader, err = a.setupReader()
			if err != nil {
				return p, nil, err
			}
		}
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
			fmt.Fprintf(a.Out, "Set up this project\n  Repository: %s\n", repo)
			inferred, err = setupAnswer(reader, a.Out, "Project name", inferred)
			if err != nil {
				return p, nil, err
			}
			provider, err = setupAnswer(reader, a.Out, "Compute provider ("+strings.Join(a.Strategies.Names(), ", ")+")", provider)
			if err != nil {
				return p, nil, err
			}
		}
		p = config.Project{Name: inferred, Repository: repo, Backend: provider}
	}
	if !*accept && known == nil {
		reader, err = a.reviewSetup(p, false, reader)
		if err != nil {
			return p, nil, err
		}
	}
	if _, err := a.Strategies.Lookup(p.Backend); err != nil {
		return p, nil, err
	}
	if err := config.CheckLocalBinding(f, p); err != nil {
		return p, nil, err
	}
	path := filepath.Join(location.Root, config.ProjectFilename)
	if err := config.WriteProject(path, config.Manifest{Version: 1, Project: p}); err != nil {
		return p, nil, err
	}
	fmt.Fprintf(a.Out, "Saved .allset — %s on %s\n", p.Name, p.Backend)
	return p, reader, nil
}

func (a App) initCommand(ctx context.Context, args []string) int {
	f, err := config.Load(a.ConfigPath)
	if errors.Is(err, os.ErrNotExist) {
		f = config.File{Version: 3, Projects: []config.Project{}}
	} else if err != nil {
		return a.fail(err)
	}
	p, _, err := a.initialize(ctx, f, args)
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
