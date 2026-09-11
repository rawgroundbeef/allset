package cli

import (
	"bufio"
	"errors"
	"fmt"
	"io"
	"sort"
	"strings"

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

func (a App) onboardingClients(reader *bufio.Reader, p config.Project) ([]strategy.ClientBinding, error) {
	if reader == nil {
		return nil, errors.New("first-time onboarding needs an interactive terminal")
	}
	fmt.Fprintln(a.Out, "\nCoding tools")
	if len(p.MCPs) > 0 {
		fmt.Fprintln(a.Out, "  MCPs:   "+strings.Join(sortedKeys(p.MCPs), ", "))
	}
	if len(p.Skills) > 0 {
		fmt.Fprintln(a.Out, "  Skills: "+strings.Join(sortedKeys(p.Skills), ", "))
	}
	if len(p.SessionEnvironment) > 0 {
		fmt.Fprintf(a.Out, "  Scoped environment values: %d\n", len(p.SessionEnvironment))
	}
	raw, err := setupAnswer(reader, a.Out, "Clients (codex, claude, cursor)", "codex")
	if err != nil {
		return nil, err
	}
	seen := map[string]bool{}
	clients := []strategy.ClientBinding{}
	for _, item := range strings.Split(raw, ",") {
		client := strings.TrimSpace(strings.ToLower(item))
		if (client != "codex" && client != "claude" && client != "cursor") || seen[client] {
			return nil, errors.New("coding clients must uniquely select codex, claude, or cursor")
		}
		seen[client] = true
		labels := map[string]string{"codex": "Codex", "claude": "Claude", "cursor": "Cursor"}
		account, err := setupAnswer(reader, a.Out, labels[client]+" account email", "")
		if err != nil {
			return nil, err
		}
		if !strings.Contains(account, "@") || strings.ContainsAny(account, "\x00\r\n") {
			return nil, errors.New("each coding client needs the account email you intend to use")
		}
		clients = append(clients, strategy.ClientBinding{Client: client, ExpectedAccount: account})
	}
	return clients, nil
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
