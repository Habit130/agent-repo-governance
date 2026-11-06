# #99: bounded Git-object snapshot investigation

## Conclusion and decision boundary

**Locally reproduced and causally supported; historical attribution remains
probable, not proven. No repair delivered.** One of ten unforced probes of the
exact historical CI checkout failed the complete snapshot. Its Git process
lineage is fixture `commit → maintenance → repack → pack-objects`; 96 paths
changed, including loose objects converted to packs. A separate deterministic
one-variable control demonstrates why even a tiny repository can cross the
installed Git version's automatic-maintenance threshold. The historical CI log
has no process trace, so the local reproduction does not prove its writer.

For #111: the false-alarm risk remains unresolved. Successful probes or this
ticket's closure must not be described as fixing the flake. Before enabling
default-branch CI, habit must either accept that risk explicitly or commission
the separately bounded fixture-setup repair proposed below. No snapshot
exclusion, normalization, or product change is authorized by this diagnosis.

## Historical facts

The [failing macOS attempt](https://github.com/Habit130/agent-repo-governance/actions/runs/41037668254/attempts/1)
and [passing attempt](https://github.com/Habit130/agent-repo-governance/actions/runs/41037668254/attempts/2)
have the same PR head `37c939f3461467fbd537c52061a7b6b8570de2b8`.
CI actually checked out the synthetic merge
`69222d117293b20235ec165349ca30b65e656959`, not the PR head directly.
Both logs identify macOS 15.7.9 (24G830), image
`macos-15-arm64` version `20260907.0337.1`, runner 2.338.0 and Git 2.55.0.
The failing command was `/usr/bin/python3 tests/run.py suites --all`;
the compatibility step establishes Python 3.9, but these logs do not print its
patch version. Only `older-record` failed; the second attempt passed 921 tests.

The failure is the existing `assertEqual(after, before, "a run changed the
worktree")`, not a case expectation or a GitHub stand-in failure. Its abbreviated
dictionary shows `.git/objects/03` and `.git/objects/9b` before, and
`.git/objects/pack` and `.git/objects/info` after. The full dictionary diff was
26,189 characters and unittest suppressed it. **The logs do not preserve the
complete changed-path list, object hashes, writer PID, or a Git trace.** Those
historical details cannot be recovered from the displayed assertion. Inferring
all loose objects were removed or naming the process would exceed the evidence.

Read-only retrieval (log fingerprints are in the evidence JSON):

```sh
gh api repos/Habit130/agent-repo-governance/actions/runs/41037668254
gh api repos/Habit130/agent-repo-governance/actions/runs/41037668254/attempts/1/jobs
gh api repos/Habit130/agent-repo-governance/actions/runs/41037668254/attempts/2/jobs
gh api --allow-escape-sequences repos/Habit130/agent-repo-governance/actions/jobs/124002406791/logs
gh api --allow-escape-sequences repos/Habit130/agent-repo-governance/actions/jobs/124007431247/logs
```

## Local protocol and results

Local environment: macOS 27.3 arm64, Python 3.9.6, Apple Git 2.54.0
(Apple Git-157). This is **not** the historical hosted image or Git version.
The machine environment was not changed to imitate that image.

`tests/diagnostics/git_snapshot.py` uses the existing `run_case` boundary and
`tree_snapshot` unchanged. Each repetition builds a new disposable fixture
repository; the existing helper caches synthetic stores/homes within a process,
as in the suite. Git setup uses the existing isolated configuration; product
commands run against the synthetic home and stand-in GitHub. Trace2 output stays
outside the measured repository/home. Only command names and process hierarchy
are retained, never arbitrary command arguments or environment values.

| Source | Probe | Repetitions | Snapshot rejections |
| --- | --- | ---: | ---: |
| `ea687abe4cd0fe0aae417737a5cd1612ee041ea2` | Original `older-record` | 30 | 0 |
| `37c939f3461467fbd537c52061a7b6b8570de2b8` | Original case, historical PR head | 10 | 0 |
| `69222d117293b20235ec165349ca30b65e656959` | Original case, historical CI checkout | 10 | 1 (run 8) |
| `ea687abe4cd0fe0aae417737a5cd1612ee041ea2` | Same fixture, no product commands (`idle`) | 10 | 0 |
| `ea687abe4cd0fe0aae417737a5cd1612ee041ea2` | Real worktree write | 1 | 1 (expected) |
| `ea687abe4cd0fe0aae417737a5cd1612ee041ea2` | Real loose-object write | 1 | 1 (expected) |
| `ea687abe4cd0fe0aae417737a5cd1612ee041ea2` | Independent repack | 1 | 1 (expected) |
| `69222d117293b20235ec165349ca30b65e656959` | Pinned-date case / idle | 3 each | 0 / 0 |
| `ea687abe4cd0fe0aae417737a5cd1612ee041ea2` | One sampled loose object | 3 | 0 |
| `ea687abe4cd0fe0aae417737a5cd1612ee041ea2` | Two sampled loose objects | 3 | 3 (expected) |

Original-case runs left the fixture home unchanged and returned the checked
case-fact subsets with no unexpected stand-in writes/calls. Threshold controls
create no machine home. The initial one-off baseline also
passed; it is not counted in the bounded series above.
`tests/diagnostics/evidence/issue-99.json` records source heads, fixture SHA-256,
environment, every measured path difference (kind/mode/content SHA-256), and
per-run Git command-hierarchy counts, and timestamped PID chains for the
unforced failure. Empty lists mean no changed paths, not
filtered paths. The JSON is historical evidence, not a deterministic golden
fixture: fixture commit times and Git versions can change object/pack hashes.

Reproduce the current probes with:

```sh
python3 -B tests/diagnostics/git_snapshot.py --runs 30
python3 -B tests/diagnostics/git_snapshot.py --runs 10 --control idle
python3 -B tests/diagnostics/git_snapshot.py --runs 1 --control worktree-write
python3 -B tests/diagnostics/git_snapshot.py --runs 1 --control object-write
python3 -B tests/diagnostics/git_snapshot.py --runs 1 --control repack
python3 -B tests/diagnostics/git_snapshot.py --runs 3 --control threshold-1
python3 -B tests/diagnostics/git_snapshot.py --runs 3 --control threshold-2
```

For each historical source, a disposable local clone with `--no-checkout
--no-hardlinks` was detached at the full SHA above, then only this diagnostic
script was copied into its `tests/diagnostics/` and run with `--runs 10` under
the existing isolated environment. No historical product/helper source was
patched. These are local probes of historical code, not reruns on GitHub's old
runner. The fetched historical merge was probed separately from its PR head.
The case, `generator_support.py`, `support.py` and `materialized.py` are identical
between those two historical commits; the different outcomes do not establish
a source-code difference as the trigger.
The merge series exited 1, correctly signalling the unforced snapshot failure;
the other series exited 0, including controls whose explicit expectation is
snapshot rejection. A preliminary attempt to pin the trace's UTC second with
`--commit-date 2026-11-06T09:05:01Z` did not reproduce the object layout (three
case and three idle runs); it is not claimed as a deterministic race reproducer.

## Causal probes and controls

1. **Deferred setup maintenance.** In historical-merge run 8, Trace2 records the
   final fixture commit PID 98533, maintenance 98534, repack 98536 and
   pack-objects 98538/98540 (UTC 09:05:01 on 2026-11-06). The first fixture commit
   also called maintenance, but only the second's lineage contains repack.
   The before-snapshot holds two real loose objects under `.git/objects/17/`;
   both are gone afterwards. This is positive evidence for deferred setup Git
   activity crossing the snapshot interval in this local reproduction.
2. **Product-triggered activity.** Original product commands return the checked
   expected facts even in the failing run. The observed packing lineage descends
   from fixture setup's commit, not a product command. This distinguishes the
   reproduced snapshot false alarm from a demonstrated product write, without
   claiming every product path is write-free.
3. **Independent Git activity.** After a clean product run, take another complete
   snapshot, synchronously run `git repack -ad`, then snapshot again. With no
   product process running, the equality assertion rejects 92 changed paths,
   including removed loose objects and added pack/index files. Trace2 records
   `repack/pack-objects`. Removing that one action leaves the unforced loop green.
   This positively attributes the **control's** writes to the injected Git
   command, without attributing the historical writes.

4. **Threshold cause, one variable.** Create a minimal disposable repository with
   either one or two real reachable blob objects whose SHA-1 starts with `17`.
   Use `write-tree`/`commit-tree`/`update-ref` for setup, avoiding any porcelain
   auto-maintenance. Hold fixed dates, Git version, configuration and the command
   `git maintenance run --auto --no-detach`; change only the number of sampled
   blobs. One gives zero changes in 3/3 runs; two causes repack and 13 changed
   paths in 3/3 runs. No threshold was lowered or maintenance setting changed.
   Foreground execution removes the race from this causal test; it establishes
   the automatic trigger, not deterministic timing of the original snapshot.

The negative controls against weakening the assertion are a real ordinary-file
write (one changed path) and `git hash-object -w --stdin` (two changed paths,
including a new loose-object directory). Both turn the same complete snapshot
equality red; the probe exits zero only because a labelled control is expected
to be rejected. In unforced mode any inequality exits nonzero. No `.git` path
or object is omitted, and shared suite assertions are untouched.

Git's generic [maintenance documentation](https://git-scm.com/docs/git-maintenance)
alone is insufficient here. Version-pinned source consulted 2026-11-06:
[v2.54.0 gc.c](https://github.com/git/git/blob/v2.54.0/builtin/gc.c),
[v2.54.0 object-file.c](https://github.com/git/git/blob/v2.54.0/object-file.c),
and [v2.55.0 gc.c](https://github.com/git/git/blob/v2.55.0/builtin/gc.c).
These versions use the geometric default strategy and an automatic geometric
repack default of **100**, not `gc.auto`'s 6700. The heuristic samples shard `17`,
estimates its count times 256, and compares it to `ceil(100/256)*256 = 256`.
Two sampled loose objects estimate 512, exceeding the threshold even when the
actual repository is tiny. Commit hashes depend on timestamps, providing a
plausible layout-variance source; the historical timestamps/layout are not known.
The local one-versus-two experiment validates the source-derived prediction on
Apple Git rather than assuming the upstream implementation matches it.

## Limits and next evidence

The original race reproduced only once within the stated bounds. The historical
CI writer remains unproven. The explicit repack control is synchronous and
deliberate; unlike the unforced failure, it does not reproduce a race or automatic
maintenance.
The `idle` control has no added waiting period and cannot exclude a longer-delay
writer. Trace2 observes Git processes that inherit it, not arbitrary writers;
tracing can itself perturb timing. The observed local frequency is not a
statistical estimate or upper bound on the hosted flake rate.

**Separate repair proposal, subject to habit's approval:** prevent only fixture
construction's porcelain commits from launching asynchronous maintenance (for
example, a command-scoped setting on those setup commits), or explicitly finish
setup maintenance before the baseline snapshot. Keep product command environments
and complete no-write comparisons unchanged. A repair ticket should first lock
down the sampled-object layout/default-maintenance trigger above, prove no setup
worker survives the snapshot boundary, and retain both real-write rejection
controls. Do not disable maintenance for the product run, which could hide writes.
No such repair is implemented here.

If further investigation is commissioned instead, capture complete before/after
path/hash differences and timestamped process lineage on the next hosted failure,
with traces outside the snapshot boundary. Distinguish setup/command phases and
capture a writer before choosing a repair. That requires its own bounded scope;
neither CI changes nor maintenance suppression is implemented here.
