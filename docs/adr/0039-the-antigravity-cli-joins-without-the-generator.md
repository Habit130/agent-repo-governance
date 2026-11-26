# The Antigravity CLI joins as a fifth harness, and the generator stays out

From version 6, the Antigravity CLI is a supported harness for Planner, Builder and Reviewer sessions. [ADR 0013](0013-generator-in-claude-code-and-opencode.md) kept the generator to the harnesses where the machine deny rules against habit's account alias and Actions-secret writes hold. Under #322, the install will give the Antigravity CLI those rules, and still habit chose to keep the generator out of it, as habit did for the Codex harness. The generator will refuse every Antigravity CLI shell, including one that inherited another harness's marker.

A repository's committed governance decides which harnesses it supports. So the Antigravity CLI becomes supported in a repository only once all of these hold:

- the repository has adopted version 6;
- the install carrying its rules has run, and the machine check's items for it pass;
- habit's probe of the installed rules is recorded;
- the repository holds none of the harness's own instruction or configuration files.

Before that, no Antigravity CLI session takes a governed role, including review of the PRs that enable it.

There is no trial before the release, which would replace a model scenario ([ADR 0030](0030-no-model-scenarios-releases-checked-by-real-runs.md)). The acceptance comes after this repository's Upgrade to version 6: the next ordinary ticket goes to an Antigravity CLI Builder, and the next PR needing a Reviewer goes to an Antigravity CLI Reviewer when the vendor rule allows. A failure there is a miss. Only the CLI is supported: the Antigravity desktop app loads the same rules but wasn't tested. Whole-spec delivery, teamwork, swarms and remote agents stay out of the harness.

Version 6 was a draft when habit approved this on 2026-11-25. [Decisions](https://github.com/Habit130/agent-repo-governance/issues/321#issuecomment-7180945790) · [Spec](https://github.com/Habit130/agent-repo-governance/issues/322)
