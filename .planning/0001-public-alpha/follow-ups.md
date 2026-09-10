# Public alpha follow-ups

## Bugs and incomplete workflows

- A new laptop cannot open a project without the external prototype controller.
  Extract provisioning, account bindings, allowance checks, restore readiness,
  and repository setup into a distributable provider strategy.
- Default SSH sessions do not guarantee agent persistence after disconnect.
  Keep explicit Herdr support and define a terminal-independent persistent path.
- Full three-project previews and browser login, two simultaneous agent worktrees
  with separate apps, and stop/resume isolation are unverified as public CLI flows.
- Collection currently selects only the default worktree. Expose task/worktree
  selection without stopping unrelated agents.
- npm packaging and trusted publisher setup are pending. Do not advertise an
  npm installation or claim the unscoped name is reserved before publication.

## Next configuration slices

- Shared tools/setup/services/skills with explicit trust before executing code.
- Private account bindings across Infisical instances, agent identities, GitHub,
  and MCP services; supported expiry/renewal without cross-project fallback.
- Diagnostics with useful redaction, stage timing, and no secrets or project content.
- Versioned config upgrades and recovery, resource limits, and preview exposure.

## Deferred ideas

- Additional compute services need real adapters and live evidence.
- Evaluate managed compute after independent CLI use establishes workloads,
  restoration reliability, isolation requirements, costs, and support effort.
- Optional website/demo; neither blocks a quiet public alpha.

Live tests require confirmed allowance and must preserve active sessions. PR CI
must not provision cloud resources or use real credentials.
