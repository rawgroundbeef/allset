package cli

import (
	"bufio"
	"errors"
	"fmt"
	"io"
	"sort"
	"strings"

	"github.com/rawgroundbeef/allset/internal/config"
)

// The caller renders an agent handoff as a successful configuration-only exit,
// without treating it as a saved project or continuing to environment setup.
var errSetupHandoff = errors.New("setup handed to the user's coding agent")

func setupAnswer(reader *bufio.Reader, output io.Writer, label, fallback string) (string, error) {
	fmt.Fprintf(output, "%s [%s]: ", label, fallback)
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

// reviewSetup keeps saved registrations visible and requires a real choice
// before restoring a deleted manifest. It reads no credentials or provider state.
func (a App) reviewSetup(p config.Project, existing bool) (*bufio.Reader, error) {
	if !a.Interactive || a.In == nil {
		return nil, errors.New("initial setup needs an interactive terminal; an agent can use allset init --name NAME --backend SERVICE --yes")
	}
	fmt.Fprintln(a.Out, "Setup reviews project configuration. It does not start or resume a VM.")
	first := "Answer the project configuration questions"
	if p.Name != "" {
		fmt.Fprintf(a.Out, "Project: %s\nRepository: %s\nCompute provider: %s\n", p.Name, p.Repository, p.Backend)
		servers := make([]string, 0, len(p.MCPs))
		for name := range p.MCPs {
			servers = append(servers, name)
		}
		sort.Strings(servers)
		if len(servers) > 0 {
			fmt.Fprintln(a.Out, "Declared MCPs:", strings.Join(servers, ", "))
		}
		first = "Save .allset using these registered settings"
		if existing {
			first = "Keep the existing .allset configuration"
		}
	}
	fmt.Fprintf(a.Out, "\n1) %s\n2) Work through setup with my coding agent\n3) Cancel\n", first)
	reader := bufio.NewReader(io.LimitReader(a.In, 8192))
	for {
		choice, err := setupAnswer(reader, a.Out, "How would you like to continue?", "1")
		if err != nil {
			return nil, err
		}
		switch choice {
		case "1":
			return reader, nil
		case "2":
			fmt.Fprintln(a.Out, "\nOpen your preferred coding agent in this repository and give it this prompt:")
			fmt.Fprintln(a.Out, "Run allset config guide, inspect this repo and its existing AllSet bindings, and walk me through the supported project settings. Keep account choices private and ask about anything missing. Save only agreed configuration; leave VM creation, resume, and connection for a separate allset run. Report any provider/account setup that is still incomplete.")
			fmt.Fprintln(a.Out, "\nConfiguration and VMs were left unchanged. Run allset init to return to this review.")
			return nil, errSetupHandoff
		case "3":
			return nil, errors.New("setup cancelled; configuration and VMs were left unchanged")
		default:
			fmt.Fprintln(a.Out, "Choose 1, 2, or 3.")
		}
	}
}
