---
name: allset-pr
description: Prepare an AllSet pull-request title and description from the final diff and verified behavior. Use when asked to draft, open, or update a PR, or summarize a change for review; execute only the requested publication scope.
---

# Pull requests

Read [AGENTS.md](../../../AGENTS.md), verify the current branch and actual base,
then inspect the final diff and relevant test results. Use the slice for intent
and constraints, while grounding every implementation claim in the diff.

Write for someone who did not see the conversation:

- Lead with the concrete problem and resulting behavior. Name a trigger and
  before/after outcome when useful.
- Include the details needed to assess ownership, compatibility, trust, recovery,
  and material limitations. Scale the length to the change.
- State commands actually run and their results; identify unverified acceptance.
- Link slice documents without restating them. Omit chronological work logs,
  abandoned designs, and file inventories.

Write the title last around the final behavior. Recheck each claim against the
diff, especially after scope changes. Use an existing repository template when
one exists. Use [allset-review](../allset-review/SKILL.md) when a quality pass is
requested or required by the active slice.

A request to draft a description is not a request to publish. When asked to
open/update a PR and the destination is established, complete that authorized
action. Use structured multiline bodies or `gh --body-file`; do not interpolate
markdown through shell command strings. If no remote or repository owner has
been selected, prepare the local result and ask only for that missing destination.
Do not create a public repository, push private history, merge, or publish npm
artifacts merely as a consequence of loading this skill.
