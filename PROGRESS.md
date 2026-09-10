# AllSet progress

## Decisions

- AllSet-only naming: `allset`, `.allset`, `ALLSET_CONFIG`.
- Free Go CLI under MIT; public source at `rawgroundbeef/allset`.
- Quiet alpha with issue-driven iteration; no coworker release gate.
- Box is compute; terminal interfaces and project account bindings stay separate.

## Completed in source

- Canonical executable/module/schema/config paths; alternate product aliases removed.
- Generic public examples; private prototype history excluded from the public snapshot.
- Repository-owned skills and domain/context docs.
- MIT, contribution/security guidance, issue forms, Linux/macOS CI, native release workflow.

## Verification

Local verification on macOS arm64:

- `go test -race ./...`, `go vet ./...`, and `git diff --check` passed.
- Four macOS/Linux arm64/amd64 native archives built; contents and checksums passed.
- Extracted macOS arm64 binary passed version/help/schema/backend smoke checks.
- Documentation links passed; Gitleaks 8.30.1 reported no findings in the source tree.
- Local review covered naming/identity, managed-file ownership, publication authority,
  resource behavior, and test gaps. This was a self-review, not an independent agent review.

The public repository is live. The first [CI run](https://github.com/rawgroundbeef/allset/actions/runs/34438370846)
passed on both GitHub-hosted Linux and macOS runners for initial commit `6cbfb8b`.
Private vulnerability reporting is enabled. The tag release workflow is present
but has not been exercised by publishing a release; npm packaging remains pending.
Remote provisioning, agent persistence, browser login/previews, and multi-agent
isolation were not tested by this source preparation work.

## Blockers and next action

- Extract standalone provider preparation and implement/test npm distribution.
- npm publication is pending packaging and supported maintainer sign-in.
- Extract the prototype controller before claiming standalone onboarding.
- See [.planning/0001-public-alpha/follow-ups.md](.planning/0001-public-alpha/follow-ups.md)
  for the remaining product workflows.
