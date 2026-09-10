# Public alpha decisions

Accepted 2026-09-09.

- AllSet is a free, open-source Go CLI under the MIT license, copyright Ben Tatum.
  The public repository is `rawgroundbeef/allset`. Developers bring their own
  compute and agent accounts.
- The command and exact npm package name are `allset`; the repository config is
  `.allset` (JSON). There are no alternate product names, CLI aliases, config
  filenames, schema aliases, or environment-variable fallbacks.
- Run inside a project from the terminal already open. No initial task prompt or
  terminal field is required. An agent can help author the declarative config.
- Each developer has a persistent environment per project. Additional agents can
  use separate worktrees and previews inside it. Shared services require deliberate
  isolation. These are product requirements, not claims of completed verification.
- Box is the first compute provider. Herdr and cmux are interfaces. Account bindings
  are per project and service, separate from shared requirements and VM state.
- Publish a quiet public alpha and iterate through issues. The first coworker
  trial is useful feedback, not a release ceremony or sign-off requirement.
- Repository-owned skills live under `.agents/skills/`, routed by AGENTS.md.
  CLAUDE.md points there; CONTEXT.md defines domain language.
- Keep existing development work and credentials intact during implementation.
  Publish a sanitized initial source snapshot, preserving private prototype history
  outside the public repository.
- Managed compute is a future feasibility question. No provider, subscription,
  price, infrastructure build, or spending commitment follows from this alpha.

Still to implement: standalone provider setup, complete shared requirements,
credential renewal contracts, persistent default connections, npm packaging and
trusted-publisher bootstrap. See [follow-ups](follow-ups.md).
