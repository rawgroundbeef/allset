// Package strategy defines service-independent project operations. A service strategy
// composes its compute provider, workspace preparation, and connection adapters.
package strategy

import (
	"context"
	"errors"
	"fmt"
	"sort"
	"strings"

	"github.com/rawgroundbeef/allset/internal/config"
	"github.com/rawgroundbeef/allset/internal/execution"
)

var ErrOnboardingChoicesRequired = errors.New("choose at least one coding client")

type Check struct {
	Name   string `json:"name"`
	State  string `json:"state"`
	Detail string `json:"detail"`
}

type Diagnosis struct {
	Project string  `json:"project"`
	Overall string  `json:"overall"`
	Checks  []Check `json:"checks"`
}

// ClientBinding is a deliberate private account choice. It is passed only to
// an executing interactive onboarding plan; credential material stays native.
type ClientBinding struct {
	Client          string `json:"client"`
	ExpectedAccount string `json:"expected_account"`
}

// Onboarder is implemented by strategies that can create a missing private
// project binding. Keeping it separate preserves the read-only Strategy contract.
type Onboarder interface {
	OnboardingPlan(config.Project, []ClientBinding, int, string) (execution.Plan, error)
}

// Strategy is the contract consumed by the CLI. Implementations must keep Validate,
// Inspect, Status, Diagnose, and Plan free of lifecycle mutations. Only executing
// an explicitly requested Plan may change a remote environment.
// Inspect must return a curated public view, never raw provider responses or
// credential contents. Strategies own service-specific identity and allowance checks.
// Plans must contain credential references rather than credential values because
// dry-run output is intended for inspection and logs.
type Strategy interface {
	Validate(config.Project) error
	Inspect(config.Project) (any, error)
	Status(context.Context, config.Project, bool) (Status, error)
	Diagnose(context.Context, config.Project, bool) Diagnosis
	Plan(config.Project, string, string, int, string) (execution.Plan, error)
}

type Registry map[string]Strategy

func (r Registry) Names() []string {
	names := make([]string, 0, len(r))
	for name := range r {
		names = append(names, name)
	}
	sort.Strings(names)
	return names
}

// Lookup never substitutes another provider for a missing implementation.
func (r Registry) Lookup(name string) (Strategy, error) {
	if s, ok := r[name]; ok && s != nil {
		return s, nil
	}
	return nil, fmt.Errorf("backend %q has no installed strategy; available backends: %s", name, strings.Join(r.Names(), ", "))
}
