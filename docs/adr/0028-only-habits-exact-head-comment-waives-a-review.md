# Only habit's own PR comment, naming the exact head, waives a required review or verification

From version 3, a required review or verification goes unmet in one way only: habit's waiver. It is a PR comment from the repository owner's account whose first line names the item and the full head SHA. A new head voids it. Merge watch counts a waived review as present only when it finds that comment.

At low and medium, versions 1 and 2 let the Codex review bot stand in for an unavailable Bugbot. At high they let habit accept one bot fewer, in a PR comment that the Merge summary linked. Nothing checked who had approved, and the first wording of that exception was wider than the rule ([env: Merge summary review waiver followed #41's general wording past the one-bot-at-high limit](https://github.com/Habit130/agent-repo-governance/issues/77)).

- An agent may draft the line. A comment by the agent account that quotes habit approves nothing, because a transcription can't be told from an invention.
- Waiving review bots only, and having no waiver at all, were both rejected: habit holds the final decision and isn't locked out by an unavailable service.
- The required status checks, the `Risk:` line, the evidence comment and the Merge summary are never waived.

This replaces the substitute and the one-bot-fewer exception that [ADR 0021](0021-review-minimums-checked-after-merge.md) mentions.

Decided in [Decision: decouple review providers and batch governance updates](https://github.com/Habit130/agent-repo-governance/issues/127) and [Version 3: provider-independent review requirements, exact-head waivers, Copilot in and Bugbot out](https://github.com/Habit130/agent-repo-governance/issues/148).
