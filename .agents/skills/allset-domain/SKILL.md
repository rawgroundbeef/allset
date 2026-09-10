---
name: allset-domain
description: Define AllSet domain terms, ownership, lifecycle invariants, and boundaries. Use when adding project configuration, environment or session behavior, account bindings, providers, previews, or integrations, or when those concepts are being conflated.
---

# Domain modeling

Read [CONTEXT.md](../../../CONTEXT.md), the relevant slice decisions, and
[architecture](../../../docs/architecture.md). Search existing types and callers
before creating a competing name or abstraction.

## Separate the concepts

- A project has shared requirements. Each developer has their own project
  environment and account bindings. A project shortcut is a lookup, not identity.
- A compute provider supplies machines. A strategy orchestrates project
  operations. A terminal interface presents work. An agent client runs sessions.
  Herdr is not a compute provider, and an SSH connection is not an agent session.
- Shared declarations express desired requirements. Local account references,
  observed provider state, and process/session state have different owners and
  lifetimes. Do not collapse them into a single persisted profile object.
- Agent, GitHub, Infisical, and MCP identities are independent bindings. Access
  to a repository or project reference does not establish authorization at another
  service. A logged-in client does not establish access to every declared resource.

## Establish ownership and invariants

For the changed behavior, write a short statement of actor, owner, identity,
allowed transition, and observable result. Use it to choose where logic belongs:

| Responsibility | Boundary |
| --- | --- |
| Validate a declaration and resolve repository identity | Configuration |
| Decide which project operation is permitted and needed | Strategy/workflow |
| Read or change a machine at a specific service | Compute provider adapter |
| Launch and attach to the intended host/session | Connection transport |
| Translate integration declarations to native client config | MCP/client adapter |
| Report a safe, curated result | CLI/status projection |

The Go packages implementing these boundaries are documented in architecture.
Do not introduce a database repository/service hierarchy merely to imitate another
project. Prefer types and functions that make this CLI's actual invariants explicit.

Probe the transitions the change can affect:

- Missing binding versus corrupt binding versus stopped versus unreachable: none
  may silently become permission to create a replacement machine.
- Reconnect versus resume: running sessions may survive the first, not VM stop.
- Machine reachable versus restored files versus ready repository versus usable
  app/integration: report the stage actually proven.
- One more agent versus a new environment: worktree, branch, service ownership,
  and preview allocation must be deliberate. Stopping one agent preserves others.
- Template/fork reuse versus project state: reusable tooling must not carry a
  previous project's credentials or private workspace into a new environment.

## Record the result

Keep reusable vocabulary and ownership in CONTEXT.md, implementation boundaries
in architecture, and slice choices in `decisions.md`. Mark a proposed domain
change as proposed until resolved. Do not put commands, provider schemas, or
temporary migration details in the glossary.

Use [allset-grill](../allset-grill/SKILL.md) for unresolved product choices and
[allset-patterns](../allset-patterns/SKILL.md) when implementing the resulting
boundary. The model is useful when a future agent can name the owner and reject
an invalid transition without relying on the conversation.
