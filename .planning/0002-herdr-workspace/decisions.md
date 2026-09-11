# Herdr workspace handoff — 2026-09-10

The accepted interaction is to run AllSet in a Herdr Local pane, prepare the
project environment, and enter its workspace through the existing sidebar.
No plugin or nested client is required. Existing ordinary SSH conversations
stay in place; AllSet does not start, resume, or migrate an agent conversation.

The project binding owns target selection. Herdr caller context selects only
the interface and local catalog. Remote workspaces belong to the selected
project VM's named Herdr server. Preserve workspace panes, focus, branches,
services, and agents. Explicit attachment choices remain available.

Herdr 0.9.0 requires a sidebar click to select a different machine in the current
client. Workspace preparation is not proof that an agent is running or detected.
The command returns, so the old attachment-scoped credential cache monitor does
not continue; persistent native account refresh after VM stop is a separate concern.

This work starts from main `97b76e3` in a fresh worktree. It carries the uncommitted
plain-SSH fixes from `fix/plain-ssh-setup`, which were already installed locally,
to preserve current SSH, preparation-only, login, and explicit PTY behavior.
The private installed controller is unchanged and remains required.

See [UAT](uat.md) and [threat model](threat-model.md).
