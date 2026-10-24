# Risk tiers scale independent agent review, not human approvals

habit reads no code at any tier, so the human part is the same everywhere: habit reads a plain-language Merge summary and merges. In a governed repository the tier sets how much independent agent review a change must pass instead:

- low: self-verification and one review bot;
- medium: also a Reviewer session;
- high: also a second review bot, a Reviewer on a different vendor's model, and a high-risk report.

Tiers that differed only in how deeply habit reads would collapse low and medium into one.

Decided in [How risk tiers gate a change](https://github.com/Habit130/agent-repo-governance/issues/12).
