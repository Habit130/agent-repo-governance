# The governance gate judges the PR as GitHub shows it when it runs

From version 5, every gate run reads the PR's head, body and author from GitHub when it runs, not from its triggering event, and judges and posts its check on that head. A manual re-run replays its original event, so version 4's gate could judge a superseded `Risk:` or `Reverts:` line and post a fresh check on the same head, overriding the verdict the current body earned; the re-run could also cancel a newer run in the PR's concurrency group. The check's title names the declared tier it judged, so a reader of a green check can match it against the body's current `Risk:` line.

When the PR can't be read from GitHub, the gate fails with one line telling the reader to rerun it, posted on the event's head. habit chose that over judging the event's possibly stale copy; posting the check already depended on GitHub, so an outage blocked the check before too. A superseded run that posts nothing was rejected: a re-run can cancel the newer run and leave no current verdict. The pure-revert lookup differs on purpose ([ADR 0008](0008-pure-revert-takes-the-low-path.md)): its failed read only leaves the revert unconfirmed.

The default branch's checkout still judges, so a verdict made under an older record stands until the PR's next gate run. A re-run executes its original run's checkout, so a run from before a repository's Upgrade to version 5 still runs the older gate; the practice of never re-running an older gate run stays until such runs no longer matter.

Version 5 was still a draft when habit approved this decision on 2026-11-19. New gate runs use the current PR once a repository adopts version 5. Releasing the version and upgrading each repository are separate decisions. [ADR 0029](0029-changes-accumulate-in-one-draft-version.md)

Decided in [the version 5 planning round's triage](https://github.com/Habit130/agent-repo-governance/issues/201#issuecomment-7003030399), from [the re-run finding](https://github.com/Habit130/agent-repo-governance/issues/201#issuecomment-7002917737), and built by [its spec](https://github.com/Habit130/agent-repo-governance/issues/204).
