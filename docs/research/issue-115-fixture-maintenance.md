# Setup-only maintenance control (#115)

Provenance: #99's diagnosis, PR #114, and the bounded repair ticket #115.
The historical report and JSON remain unchanged. The historical hosted CI writer
is still probable, not proven, attribution; this repair does not estimate a hosted
flake rate or exclude independent writers.

## Mechanism

Both generator fixture setup commits use command-scoped
`git -c maintenance.auto=false commit`. The initial tally helper exposes an opt-in;
its other callers keep their existing behavior. No repository, global or system
configuration is written. `case_env`, product execution, complete `tree_snapshot`
and existing snapshot equality assertions are unchanged.

Primary sources consulted 2026-11-06:

- [Git v2.54.0 maintenance configuration](https://github.com/git/git/blob/v2.54.0/Documentation/config/maintenance.adoc):
  `maintenance.auto` controls commands invoking automatic maintenance, default true.
- [Git v2.54.0 run-command.c](https://github.com/git/git/blob/v2.54.0/run-command.c),
  `prepare_auto_maintenance`: false returns before preparing a maintenance child.
- [Git command-scoped configuration](https://git-scm.com/docs/git#Documentation/git.txt--cltnamegtltvaluegt):
  `-c` passes configuration to that invocation, overriding configuration files.

This prevents the worker from being launched, rather than waiting for an arbitrary
quiet period. In this fixture's nonempty construction path these are the two
porcelain commits; the remaining Git calls do not request auto-maintenance.

## Deterministic regression and controls

Run `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tests/suites python3 -m unittest
test_generator_core.FixtureSetup -v` (one shell line), or
`python3 tests/run.py suites generator-core`, which CI runs automatically.

The test-local Git exec-path adapter intercepts the actual automatic-maintenance
child dispatched by real Git, only in the measured tally repository. It changes
that child's scheduling: a worker acknowledges readiness before commit returns,
then waits on a socket until the real complete baseline has been captured.
After release, real `maintenance run --auto --no-detach --task=commit-graph` uses
the documented negative `maintenance.commit-graph.auto` trigger. The parent waits
for its result before product execution and the final snapshot. Each setup commit
is selected separately; there is no sleep, probabilistic threshold or golden object
hash. Timeouts bound protocol failures, not ordering. All coordination files are
outside the measured repository; no snapshot path is excluded.

Before the repair, both selections failed the unchanged complete snapshot equality
after real commit-graph files appeared. After the repair, neither setup commit
dispatches a maintenance child, both commits are present, and equality passes.
The default tally caller remains a positive dispatch control. A commit injected
between baseline and product execution using the exact product environment still
dispatches maintenance and fails equality. Real ordinary-file and loose-object
writes in that same interval also fail equality; each product environment is
queried with real Git to exclude persistent maintenance configuration.

This substitutes controlled scheduling and a portable forced task for the natural
repack race. It proves the setup dispatch control and retained write detection,
not the timing/frequency of an unmodified hosted maintenance worker. The original
sampled-object and repack evidence remains in the #99 report.

Full tested commit, Git/OS/Python versions, red/green results, required verification
and CI results belong to the PR's head-bound evidence comment and the #111 handoff.
No scenarios or live sandbox check are needed for this tests-only repair.
