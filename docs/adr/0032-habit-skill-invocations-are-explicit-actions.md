# A skill habit must invoke is an explicit action in the handoff

In version 4, a message whose next step needs a user-invoked skill tells habit which session needs it and gives the whole invocation line, arguments included. A start instruction's `Skills:` names only skills the session calls; a ticket distinguishes those from skills habit invokes. Which skills belong to habit does not change.

Merely listing a user-invoked skill in `Skills:` did not invoke it or tell habit to act. A session reaching such a step, or started without the needed invocation, stops for a mid-session request. It does not read and follow the skill's text or otherwise substitute for habit's invocation. The invocation itself is habit's reply, with no extra confirmation needed.

The canonical form in role files and on GitHub, dispatch plans included, stays harness-neutral: `habit invokes: <skill> <arguments>.` precedes the start instruction when needed. The terminal start request translates that form for one named harness, normally the sender's; choosing another needs a reason. This refines [ADR 0004](0004-roles-arrive-by-start-instruction.md): the role and target remain canonical, while the invocation takes the harness's syntax.

habit verified one paste as the first message of a fresh Claude Code session with `/name` and of a fresh Codex app Local-mode chat with `$name`. `@name` did not load the skill in the Codex app. These are habit's tests recorded on 2026-11-14, not new verification by this docs PR. The Codex CLI, OpenCode, deepseekharness and starting Claude Code with the invocation as a terminal argument remain unverified for one paste. Their start requests keep the start instruction separate and add a third part, "habit 调用", with the invocation to type after the session starts. A request needing no user-invoked skill keeps two parts.

The choice keeps one canonical policy while making habit's next action copyable, instead of assuming that one combined line works in every harness. There is no new machine check or review finding for an omitted invocation; the omission is a miss handled through `retro`.

Decided in [the explicit-invocation ticket](https://github.com/Habit130/agent-repo-governance/issues/172) as part of [the version 4 planning round](https://github.com/Habit130/agent-repo-governance/issues/167). Version 4 is an unpublished draft. Until a repository adopts it, its existing wording remains in force; this decision introduces no interim rule.
