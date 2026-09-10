# Public alpha

AllSet's first public increment exposes the existing Go CLI for feedback while
its standalone provider setup is being extracted.

## Implemented in source

- AllSet-only command, `.allset` manifest, local registry, schemas, and help.
- Git-boundary discovery, origin/account binding checks, non-clobbering init,
  read-only inspection, and provider-independent dispatch contracts.
- Box status and existing-profile operations through the prototype workspace
  controller; SSH by default and explicit remote Herdr attachment.
- Native MCP configuration for Codex, Claude, and Cursor, including a pinned
  Trigger.dev preset with an isolated project login context.
- Repository skills, MIT license, contribution/security instructions, issue forms,
  Linux/macOS CI, and tag-driven native release builds with checksums.

## Limits

The Box adapter still needs a separately installed local prototype controller.
A new manifest cannot provision a complete environment on a fresh laptop.
Default SSH is not a persistent session transport. Declarative setup/services,
Infisical account binding, skill installation, multiple-project browser previews,
and concurrent-agent app isolation are not complete.

Do not count the mocked Go/Python contract suite as proof of real VM readiness,
provider recovery, app login, or independent coworker onboarding. Existing
prototype experience guides extraction; it does not close these acceptance gaps.

## Next work

1. Publish source with accurate limitations and normal CI, without a launch ceremony.
2. Extract a complete supported Box strategy and private account-binding flow.
3. Package the Go CLI for npm; verify packed installation and trusted publication.
4. Prove fresh checkout to working app, reconnect, and independent concurrent work.
5. Use public issues and actual trials to prioritize further adapters and reliability.

See [decisions](decisions.md), [follow-ups](follow-ups.md),
[source preparation](public-source-inventory.md), [threat model](threat-model.md),
and [release mechanics](../../docs/releasing.md).
