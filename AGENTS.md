# AllSet — contributor guide

AllSet prepares persistent project environments from the terminal the developer
already uses. Go is the primary implementation language. The executable is `allset`;
project configuration is the `.allset` JSON file.

## Sources of truth

- [CONTEXT.md](CONTEXT.md): domain vocabulary and ownership, not implementation.
- [Architecture](docs/architecture.md): current module boundaries and limitations.
- [Configuration](docs/configuration.md) and [MCPs](docs/mcps.md): current contracts;
  validate against the parsers and schemas in `internal/config/`.
- `.planning/{NNNN-slug}/`: slice discovery, decisions, acceptance, and handoff.
  [Public alpha](.planning/0001-public-alpha/discovery.md) tracks the current alpha.
- [PROGRESS.md](PROGRESS.md): completed work, evidence, blockers, and next action.

When code, docs, and intent disagree, identify the discrepancy. Do not describe a
planned capability as implemented or let historical adapter names define the domain.

## Skills

Canonical skills live in `.agents/skills/`. Load the linked `SKILL.md` for the work
at hand, plus any companion it calls for. These are contributor skills for building
AllSet; they are not a claim that AllSet installs skills in users' environments.
Keep them portable, with repository-relative references. Do not commit duplicate
skill trees under `.claude/` or `.cursor/`, or rely on personal global skills.

| Work | Skill |
| --- | --- |
| Define concepts, ownership, or lifecycle invariants | [allset-domain](.agents/skills/allset-domain/SKILL.md) |
| Write or refactor Go, adapters, configuration, or subprocess code | [allset-patterns](.agents/skills/allset-patterns/SKILL.md) |
| Stress-test an idea and record decisions | [allset-grill](.agents/skills/allset-grill/SKILL.md) |
| Plan a feature through discovery, UAT, PRD, and handoff | [allset-slice](.agents/skills/allset-slice/SKILL.md) |
| Define or execute user acceptance checks | [allset-uat](.agents/skills/allset-uat/SKILL.md) |
| Write requirements from agreed acceptance | [allset-prd](.agents/skills/allset-prd/SKILL.md) |
| Change a trust boundary, credentials, privileged execution, or publishing | [allset-threat-model](.agents/skills/allset-threat-model/SKILL.md) |
| Review a diff for correctness, security, performance, and testing | [allset-review](.agents/skills/allset-review/SKILL.md) |
| Prepare a PR from the final diff | [allset-pr](.agents/skills/allset-pr/SKILL.md) |

Routine fixes and documentation changes do not need the full slice pipeline.
Use threat modeling when the changed behavior warrants it, not for every edit.

## Working rules

- Preserve branches, worktrees, credentials, services, agent conversations, and
  terminal sessions. Create a fresh Git worktree for each new branch/task; never
  switch another worktree. Determine the base from Git and the task. Use the current main branch as the base unless the task specifies another.
- Continue routine, reversible work within the user's authorization. Ask one
  focused question only for a missing sign-in, permission, budget, or consequential
  decision that cannot be resolved from evidence. Do not ask users to run commands
  the agent can run. Delegation requires an explicit user request.
- Box is a compute provider. Herdr/cmux are interfaces. Keep compute, connection,
  agent clients, account bindings, and shared project configuration separate.
- Use native provider features and supported authentication flows. Never print
  secrets, put credentials in templates, or infer one project's identity from
  another project's active login. A shared config does not authorize new accounts.
- Reject unknown configuration fields and contradictory project/account bindings.
  Status, diagnosis, inspection, and dry-run must not mutate environments or auth.
- A timed-out mutation has an uncertain outcome: reconcile before retrying.
  Authenticated SSH does not prove filesystem restoration or project readiness.
- Reconnect must preserve active work. Do not replace running servers or change
  active agent branches to repair setup. A VM stop ends processes even when files
  persist. Keep the existing Box/Herdr setup working during extraction.
- Honor session budgets and concurrency limits. Do not provision to answer a
  read-only question. Reusable tests use synthetic accounts and disposable state.
- No public push, release, package publication, or purchase follows merely from
  preparing a plan or PR description. Follow the actual requested scope.

## Verification and handoff

Run from the repository root before handing off implementation:

```sh
go test -race ./...
go vet ./...
go build -o bin/allset ./cmd/allset
```

Python 3.11+ is required by runtime tests, which the Go suite invokes. Format changed Go with
`gofmt`. Add meaningful regression/fault tests for lifecycle and authentication;
do not add tests that merely duplicate the implementation.

For documentation/skill-only work, check links, skill frontmatter, routing, and
consistency with current code; no live VM test is required. Update `PROGRESS.md`
with decisions, completed work, blockers, and next action, without secrets.
Label local/mock, real remote, interactive, and unverified evidence separately.
