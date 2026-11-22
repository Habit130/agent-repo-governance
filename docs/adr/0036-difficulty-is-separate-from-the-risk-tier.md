# Difficulty is how much judgment a delivery leaves, separate from its risk tier

From version 4, the Planner grades each dispatch plan entry's difficulty, low, medium or high, always written with the word ("Difficulty: low", "难度：low"), so it never reads as a tier. Difficulty is how much judgment the finished ticket leaves the session; the risk tier is how much review the change needs. The two are independent axes: an important area doesn't make work hard, and hard work isn't riskier for that.

- **low**: the ticket fixes what changes and how, and a command, a test or a byte comparison confirms it.
- **medium**: the ticket fixes the outcome; the session chooses the implementation within one area, and tests can confirm it.
- **high**: a real design trade-off, a new rule or procedure agents follow with no test of its effect, several components that must stay consistent, a bug of unknown cause, or the main Builder of a whole-spec delivery.

When unsure, the lower level, and a medium or high names what makes it so. The grade lives in the dispatch plan, one line with one reason per entry, not in the ticket, so correcting it needs no change to a frozen ticket. It appears in the "给 habit" part of a start request, and a Builder says in one sentence when the actual difficulty differed.

habit wanted Builder sessions matched to the work to use agent allowance well, without quantifying it. Before this, 17 of the last 32 merged PRs declared high, and the tier was the only signal of how hard a ticket was; these criteria give about 12 low, 15 medium and 5 high for the same PRs. The session states difficulty and habit chooses the model and effort ([ADR 0025](0025-adapt-to-outside-changes.md)).

This repository graded the entries in its 2026-11-17 dispatch plan while version 4 was still a draft. Difficulty grading becomes a model requirement for a repository when it adopts version 4. [Dispatch plan](https://github.com/Habit130/agent-repo-governance/issues/182#issuecomment-6935592841)

Decided in [the version 4 planning round](https://github.com/Habit130/agent-repo-governance/issues/182), rounds 4 and 5.
