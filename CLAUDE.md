@AGENTS.md

# CLAUDE.md

`AGENTS.md`, imported above, is this repository's canonical instruction file, and this file
never overrides it. What follows is specific to Claude Code.

- Name a user-invoked skill for habit as `/<name>`, or as `/<plugin>:<name>` when a built-in
  command shares its name.
- Subagents are helpers: they inherit your role and permissions, and each parallel writer
  needs its own git worktree.
- Claude Code's built-in `/init` is not the governance path here; initialization and upgrades
  run through `/initialize-repository`.
- Memory is context, not authority: rules live in `AGENTS.md` and `docs/agents/`, and
  anything memory says that they contradict is wrong.
