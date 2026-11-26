# The Antigravity app replaces the CLI as the fifth harness, and its limits rest on instructions

From version 6, the Antigravity app, Google's Antigravity desktop app, is the supported harness for Planner, Builder and Reviewer sessions, in place of the Antigravity CLI that [ADR 0039](0039-the-antigravity-cli-joins-without-the-generator.md) chose. On 2026-11-26 habit made the app the main entry and decided that, if supporting both surfaces cost too much, governance supports only the app. The CLI is unsupported. The generator stays out of the app, as ADR 0039 kept it out of the CLI: it refuses every shell carrying the `ANTIGRAVITY_` names, which habit's probe found in the app's shell as in the CLI's.

The app keeps its permission rules in its settings UI, and its documentation names no file for them. So the install can't write deny rules against habit's account alias and Actions-secret writes there, and the machine check can't confirm them. As for deepseekharness, those limits rest on instructions in the app. Governance guards against honest agents' mistakes, which the instructions cover; a file-based route, such as the app's global hooks, can come later. The rejected alternative was to keep probing where the app stores its rules and whether they hold, which habit found too costly and asked for a simpler plan. The machine part keeps the app's global instruction link and the check against a conflicting global instruction file ([clarification](https://github.com/Habit130/agent-repo-governance/issues/321#issuecomment-7184824507)). Governed app sessions run under habit's Auto preset, since governance doesn't require habit to approve each commit or push.

habit's probe on 2026-11-26 also showed the app injects the model notice of [ADR 0038](0038-a-harness-injected-model-notice-is-a-harness-source.md) at the start and again after a mid-conversation model switch, hides skills marked user-only from the model, and finds the machine skill root without configuration.

A repository supports the app once all of these hold:

- the repository has adopted version 6;
- the install carrying the app's link and check has run, and the machine check's items for it pass;
- the repository holds none of the app's own instruction or configuration files.

Before that, no app session takes a governed role. The acceptance follows this repository's Upgrade to version 6: the next ordinary ticket goes to an app Builder, and the next PR needing a Reviewer goes to an app Reviewer when the vendor rule allows. It also observes habit's explicit `/name` invocation of a user-invoked skill and the worktree use, which weren't probed. A failure is a miss. Whole-spec delivery, teamwork, swarms and remote agents stay out of the harness.

Version 6 was a draft when habit approved this on 2026-11-26. Supersedes ADR 0039. [Decisions](https://github.com/Habit130/agent-repo-governance/issues/321#issuecomment-7184746344) · [Probe](https://github.com/Habit130/agent-repo-governance/issues/321#issuecomment-7184477993) · [Spec](https://github.com/Habit130/agent-repo-governance/issues/322)
