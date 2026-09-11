package cli

import (
	"bufio"
	"errors"
	"fmt"
	"io"
	"os"
	"sort"
	"strings"

	"charm.land/huh/v2"
	"github.com/rawgroundbeef/allset/internal/config"
	"github.com/rawgroundbeef/allset/internal/strategy"
)

func setupAnswer(reader *bufio.Reader, output io.Writer, label, fallback string) (string, error) {
	if fallback == "" {
		fmt.Fprintf(output, "%s: ", label)
	} else {
		fmt.Fprintf(output, "%s [%s]: ", label, fallback)
	}
	answer, err := reader.ReadString('\n')
	if err != nil {
		return "", errors.New("setup cancelled; configuration and VMs were left unchanged")
	}
	answer = strings.TrimSpace(answer)
	if answer == "" {
		answer = fallback
	}
	return answer, nil
}

func (a App) setupReader() (*bufio.Reader, error) {
	if !a.Interactive || a.In == nil {
		return nil, errors.New("setup needs an interactive terminal; use allset init --name NAME --backend SERVICE --yes when the choices are known")
	}
	return bufio.NewReader(io.LimitReader(a.In, 8192)), nil
}

func (a App) onboardingClients(reader *bufio.Reader, p config.Project) ([]strategy.ClientSelection, error) {
	if reader == nil {
		return nil, errors.New("first-time onboarding needs an interactive terminal")
	}
	if len(p.MCPs) > 0 || len(p.Skills) > 0 || len(p.SessionEnvironment) > 0 {
		fmt.Fprintln(a.Out, "\nIncludes")
	}
	if len(p.MCPs) > 0 {
		fmt.Fprintln(a.Out, "  MCPs:   "+strings.Join(sortedKeys(p.MCPs), ", "))
	}
	if len(p.Skills) > 0 {
		fmt.Fprintln(a.Out, "  Skills: "+strings.Join(sortedKeys(p.Skills), ", "))
	}
	if len(p.SessionEnvironment) > 0 {
		fmt.Fprintf(a.Out, "  Scoped environment values: %d\n", len(p.SessionEnvironment))
	}
	selected, err := a.selectCodingClients(reader)
	if err != nil {
		return nil, err
	}
	seen := map[string]bool{}
	clients := []strategy.ClientSelection{}
	for _, item := range selected {
		client := strings.TrimSpace(strings.ToLower(item))
		if (client != "codex" && client != "claude" && client != "cursor") || seen[client] {
			return nil, errors.New("coding clients must uniquely select codex, claude, or cursor")
		}
		seen[client] = true
		clients = append(clients, strategy.ClientSelection{Client: client})
	}
	return clients, nil
}

func (a App) selectCodingClients(reader *bufio.Reader) ([]string, error) {
	if a.richTerminal() {
		selected := []string{"codex"}
		keys := huh.NewDefaultKeyMap()
		keys.MultiSelect.Toggle.SetKeys("space")
		keys.MultiSelect.Toggle.SetHelp("space", "select")
		field := huh.NewMultiSelect[string]().
			Title("Choose your coding agents").
			Filterable(false).
			Height(4).
			Limit(3).
			Options(
				huh.NewOption("Codex", "codex").Selected(true),
				huh.NewOption("Claude Code", "claude"),
				huh.NewOption("Cursor", "cursor"),
			).
			Value(&selected).
			Validate(func(values []string) error {
				if len(values) == 0 {
					return errors.New("select at least one coding agent")
				}
				return nil
			})
		err := huh.NewForm(huh.NewGroup(field)).
			WithInput(a.In).
			WithOutput(a.Out).
			WithKeyMap(keys).
			WithShowHelp(true).
			Run()
		if err != nil {
			return nil, errors.New("setup cancelled; configuration and VMs were left unchanged")
		}
		return selected, nil
	}

	fmt.Fprintln(a.Out, "\nCoding agents")
	fmt.Fprintln(a.Out, "  codex (default) · claude · cursor")
	fmt.Fprintln(a.Out, "  Enter one or more names, separated by commas.")
	raw, err := setupAnswer(reader, a.Out, "Agents", "codex")
	if err != nil {
		return nil, err
	}
	return strings.Split(raw, ","), nil
}

func (a App) richTerminal() bool {
	if os.Getenv("ALLSET_ACCESSIBLE") != "" || os.Getenv("TERM") == "dumb" {
		return false
	}
	isTerminal := func(value any) bool {
		file, ok := value.(*os.File)
		if !ok {
			return false
		}
		info, err := file.Stat()
		return err == nil && info.Mode()&os.ModeCharDevice != 0
	}
	return isTerminal(a.In) && isTerminal(a.Out)
}

func sortedKeys[T any](values map[string]T) []string {
	keys := make([]string, 0, len(values))
	for key := range values {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	return keys
}

// reviewSetup keeps saved registrations visible and requires confirmation before
// restoring a deleted manifest. It reads no credentials or provider state.
func (a App) reviewSetup(p config.Project, existing bool, reader *bufio.Reader) (*bufio.Reader, error) {
	if reader == nil {
		var err error
		reader, err = a.setupReader()
		if err != nil {
			return nil, err
		}
	}
	heading := "Set up this project"
	question := "Use these settings?"
	if existing {
		heading = "Project configuration"
		question = "Keep these settings?"
	}
	fmt.Fprintf(a.Out, "%s\n  Name:       %s\n  Repository: %s\n  Compute:    %s\n", heading, p.Name, p.Repository, p.Backend)
	servers := sortedKeys(p.MCPs)
	if len(servers) > 0 {
		fmt.Fprintln(a.Out, "  MCPs:       "+strings.Join(servers, ", "))
	}
	for {
		choice, err := setupAnswer(reader, a.Out, question, "Y")
		if err != nil {
			return nil, err
		}
		switch strings.ToLower(choice) {
		case "y", "yes":
			return reader, nil
		case "n", "no":
			return nil, errors.New("setup cancelled; configuration and VMs were left unchanged")
		default:
			fmt.Fprintln(a.Out, "Enter y or n.")
		}
	}
}
