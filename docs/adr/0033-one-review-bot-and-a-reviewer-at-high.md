# One review bot from medium, and a Reviewer session only at high

From version 4, the tier sets independent agent review this way:

- low: self-verification only;
- medium: self-verification and one review bot, in the one bot slot, `bot-1`;
- high: self-verification, one review bot, and a Reviewer session on a vendor different from every Builder's, which writes the high-risk report.

At medium the Builder writes the Merge summary, saying that no independent session looked at the change. The governance record's enabled review bots stay a confirmed value, but their order is now the order in which bots are tried for the one slot: when one is unavailable, the next takes the slot at medium and at high. At medium, when no enabled bot is left, a same-vendor Reviewer session substitutes; otherwise habit waives the slot. At high, with no bot left, habit waits or waives the slot. A Builder that wants to reject a review bot's Important finding at medium first raises the PR to high, as at low. The Reviewer's security review at high is unchanged.

Version 3's ladder asked more than its reviews returned. The planning round's review of this repository's merged PRs found that Copilot code review never completed a review, and every high PR since version 3's adoption waived `bot-2`; the Codex review bot raised no inline finding in 35 requests since 2026-11-06; Reviewer sessions raised 11 Important findings across 27 high PRs and none across 9 medium PRs. The second bot slot and the medium Reviewer cost habit a request or a waiver on nearly every PR and caught little, while the high Reviewer is where review found problems. Tiers still differ by independent agent review, never by how deeply habit reads, so this keeps [ADR 0003](0003-tiers-scale-agent-review.md)'s principle and replaces its ladder. It keeps [ADR 0027](0027-review-requirements-name-bot-slots.md)'s slots and confirmed list, with one slot instead of two.

Version 4 is an unpublished draft. Until a repository adopts it, version 3's ladder binds there, `bot-2` and its waivers included.

Decided in [the version 4 planning round](https://github.com/Habit130/agent-repo-governance/issues/182), specified in [spec #183](https://github.com/Habit130/agent-repo-governance/issues/183), with the medium substitute narrowed by habit's [approved clarification](https://github.com/Habit130/agent-repo-governance/issues/183#issuecomment-6943794251). Supersedes ADR 0003 and ADR 0027 from version 4.
