# Roles arrive by the start instruction, not by agent definitions

In a governed repository, a session's start instruction names its role, in the same text in every harness. Each role's duties live in committed, harness-neutral role files.

Per-harness agent definitions were rejected for three reasons:

- A non-empty Claude Code agent body replaces Claude Code's own system prompt.
- deepseekharness discovers no committed agent preset.
- Three formats of the same duties would drift apart.

Decided in [How one canonical policy reaches every harness](https://github.com/Habit130/agent-repo-governance/issues/16).
