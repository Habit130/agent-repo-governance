# A pure revert takes the low path, sensitive paths included

A PR that exactly undoes one merged squash commit takes the low path even on a sensitive path when the governance gate confirms it, so an emergency revert does not wait for a Reviewer session. The original rationale was returning to a state that already passed review; a commit from before governance does not support that rationale.

From version 4, confirmation also requires the governance record to exist in the reverted commit's parent. The commit must still be on the default branch with one parent, and its revert recomputed on the PR's merge-base must equal the head's tree. A revert of a commit from before governance, including the commit that first added the record, is unconfirmed and tiered as usual. Reverting a one-way door remains an escalation.

The gate uses git objects alone rather than a GitHub lookup proving that the commit was a merged PR's squash commit: an API fault must not become another reason the required check fails. The accepted boundary is that a qualifying commit pushed without a PR after governance began can still confirm; Merge watch records that push as a miss. Confirmation is not proof that review occurred.

Version 4 is an unpublished draft. Its release and each repository's Upgrade remain separate decisions; this ADR does not upgrade a repository's gate. Until adoption, the planning decision says a pre-governance revert is tiered as usual by instruction.

Originally decided in [How work flows from idea to merged PR](https://github.com/Habit130/agent-repo-governance/issues/14) and [Which rules are enforced deterministically](https://github.com/Habit130/agent-repo-governance/issues/15). Narrowed in [the version 4 planning round](https://github.com/Habit130/agent-repo-governance/issues/167) and [its revert-rule ticket](https://github.com/Habit130/agent-repo-governance/issues/169), with the interim instruction in [the approved dispatch plan](https://github.com/Habit130/agent-repo-governance/issues/167#issuecomment-6869028046).
