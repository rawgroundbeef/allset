# AllSet project environments

AllSet gives a developer a prepared remote place to work on a project with their
chosen coding agents, tools, and accounts.

## Language

**Project**:
A body of source code and its shared development requirements.

**Project environment**:
A persistent remote development space belonging to one developer and one project.
_Avoid_: Task box, shared team machine

**Agent session**:
An interactive conversation with a coding agent working in a project environment.

**Agent client**:
The program a developer chooses to run agent sessions. Its signed-in identity is
independent of the project's application and secret-service identities.

**Project worktree**:
A checkout inside a project environment with its own working files and branch.
Concurrent agents can use separate worktrees without requiring separate machines.

**Project configuration**:
The shared declaration of what a project environment needs.
_Avoid_: Personal account profile, machine state

**Account binding**:
A developer's association of a project with an identity at an external service.

**Compute provider**:
A service supplying the remote machines that host project environments.
_Avoid_: Terminal, Herdr backend

**Terminal interface**:
The developer's chosen interface for entering and steering agent sessions.

**Preview**:
A browser-accessible running instance of a project's application.

## Relationships

- A **Project** has shared **Project configuration** and can have many developers'
  **Project environments**.
- A **Project environment** belongs to one developer and one **Project** and can
  contain multiple **Project worktrees**, **Agent sessions**, and **Previews**.
- **Agent clients** run **Agent sessions** against **Project worktrees**. Separate
  worktrees do not by themselves isolate application services or databases.
- **Account bindings** belong to the developer and project, independently of the
  shared **Project configuration**.
- A **Compute provider** hosts **Project environments**; a **Terminal interface**
  presents **Agent sessions** to the developer.

## Example dialogue

> **Developer:** If my coworker opens the same project, do we share a machine?
> **Domain expert:** You share the project configuration. Each of you has a
> project environment and your own account bindings.

## Resolved ambiguities

- Herdr and cmux are terminal interfaces, not compute providers.
- An agent account and an application's secret-service account are independent
  identities; selecting one does not select the other.
- Multiple agents in one project do not imply multiple project environments.
