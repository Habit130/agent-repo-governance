# Deterministic enforcement lives on GitHub's server side

Rulesets, repository settings, collaborator permissions and required checks bind sessions in every harness alike. deepseekharness has no command-level rules at all. So a governed repository's hard rules are enforced on GitHub.

Harness rules exist only at machine level, for the two actions GitHub can't stop: calling habit's account alias and writing Actions secrets.

## Considered options

- **Committed harness permission files per repository.** Rejected: the account alias and the agent account are machine facts.
- **Per-role agent definitions.** Rejected: the roles need almost every tool, deepseekharness can't load them, and starting with an agent flag would break the one start instruction that works in every harness.
- **A default read-only agent.** Rejected: it would conflict with habit's direct request making a session a Builder.
- **Harness hooks.** Rejected: version 1 needs none.

Decided in [Which rules are enforced deterministically](https://github.com/Habit130/agent-repo-governance/issues/15).
