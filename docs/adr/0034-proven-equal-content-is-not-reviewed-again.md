# Content mechanically proven equal to reviewed content is not reviewed again

A change whose content a check proves identical to content that already passed review takes no second review of that content. The first case was the pure revert in [ADR 0008](0008-pure-revert-takes-the-low-path.md). The version 4 planning round added two more.

- **A pure Upgrade is medium.** An Upgrade is pure when exact comparison reports no differences and the governance record's confirmed part is unchanged from the default branch. Its fixed content is what the release reviewed, so the tier no longer treats it as generator output. Initialize, Repair, and an Upgrade that changes a confirmed value, the required checks or the owner script's target state stay high.
- **The release PR creates the next draft.** The PR releasing version N also adds draft N+1. The release check compares file contents and modes with the version being released, allowing for the new manifest version number and the absence of a change note in the draft.

In the planning round, 2 of the 15 high PRs since 2026-11-10 only created a draft as a byte-identical copy, and 1 was this repository's Upgrade: each took a high review of content a machine had already shown to be equal. The proof is narrower than review: it shows equality, never that the reviewed content was right, so it applies only where equality is the whole question.

Version 4 was still a draft at the November 2026 decision. The version a repository has already adopted determines the tier of its Upgrade PR. Under version 3 even a pure Upgrade is high. After the repository adopts version 4, a pure Upgrade is medium, subject to sensitive-path floors.

On 2026-11-19 (UTC), the version 4 release created draft version 5. Later that day this repository's Upgrade to version 4 took the high path under version 3. [Release PR](https://github.com/Habit130/agent-repo-governance/pull/199) · [Upgrade PR](https://github.com/Habit130/agent-repo-governance/pull/203) · [Release procedure](../build/releasing.md#cut-a-version) · [Release-check ticket](https://github.com/Habit130/agent-repo-governance/issues/186)

Decided in [the version 4 planning round](https://github.com/Habit130/agent-repo-governance/issues/182), round 2, questions 3 and 4.
