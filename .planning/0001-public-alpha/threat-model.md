# Public alpha threat model

Scope: product naming, managed MCP paths, public source, and native CI publishing.
This is a focused review, not an audit of the unfinished provider controller.

| Failure or abuse | Impact and priority | Control and evidence | Remaining limit |
| --- | --- | --- | --- |
| Private history or auth files included in the first push | High: exposes project/account material | Fresh public history; selected source payload; generic fixtures; redacted secret scan before push | A scanner is not proof of absence; manual payload review remains necessary |
| Renamed registry selects different saved accounts | High: cross-project access | One canonical config path, existing repository/account conflict checks; private one-time migration must preserve bindings | No permanent old-name fallback; migration is not discovery behavior |
| Renamed MCP ownership loses existing native auth or overwrites manual edits | High: breaks current sessions or account isolation | Existing state/native entry conflict checks and project-home ownership journal remain; migrate existing private state separately before using the new runtime | Active processes must keep their current auth paths until they exit; no server restart for this rename |
| Contributor PR executes with publishing or cloud credentials | High: supply-chain or spending impact | PR CI has contents:read only, no cloud secrets, no pull_request_target; publication only on maintainer tag after checks | Maintainers must review workflow changes; repository admins remain trusted |
| Tag publishes an unchecked revision or wrong version | High: substituted release | Reusable CI gates, main ancestry and tag/version checks, full-SHA actions, native archive checksums | Cross-build does not prove execution on each architecture; native releases are not signed/notarized yet |
| Retry overwrites a partially released artifact | Medium: ambiguous downloaded bytes | Release creation fails if already present; preserve CI artifacts and reconcile missing uploads without clobbering | Recovery is documented manual work, not yet automated |

Configuration MCP commands run code under the remote user. The rename adds no
new sandbox or permission boundary. Native auth files remain private and excluded
from machine templates. No live abuse tests, cloud provisioning, or active-server
restarts are required to verify this public-source increment.
