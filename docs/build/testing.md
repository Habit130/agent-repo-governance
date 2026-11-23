# Testing

Start with [Build and verification](../agents/build.md) for the ordered checks and
habit-only commands. This reference describes the current state.

The suites command runs one child process per selected suite using the invoking interpreter.
Concurrency defaults to the CPU count (one if unavailable); `--workers N` sets a positive
limit, and `--workers 1` runs serially for debugging. `machine-wizard` starts first, then
`owner`, then the remaining suites in registry order. Tests within each suite stay serial.
Completed suites print their captured stdout and stderr as whole blocks, without interleaving.
After all suites finish, summaries in scheduling order report each result, test count and
duration, followed by the total count and wall time. Failure, error, load failure or worker
crash makes the command fail without suppressing other suites. A worker without a completed
result reports an unknown count and the total is marked incomplete; it is never a pass.
Selection by names, `--job linux`, `--job macos` or `--all` retains the suite registry's jobs;
the macOS compatibility command still runs every suite under `/usr/bin/python3`.

## Suites

### Unpublished model development

The release check permits one draft: the highest consecutive numeric version in the
store, identified by the absence of `change-note.md`. All earlier versions must have
valid change notes. A sole unpublished v1 remains valid for bootstrap. Draft files may
accumulate changes across PRs; an all-released store is also valid. Multiple drafts,
a draft below a released version, gaps, non-version entries and malformed notes fail.

Merge fixes, release a model, install machine components/skills, and adopt a version in
a repository are separate decisions. habit chooses a coherent accumulated update without
a fixed issue-count threshold; urgent bugs or severe usability problems may justify an
earlier installation. Installation does not automatically Upgrade repositories.

Follow [Releasing](releasing.md#cut-a-version) to cut the version and prepare the next draft.
Once a version's note exists on the comparison base, its complete tree is frozen. Adding,
deleting or editing a file, changing a mode, removing the version or removing its note all fail.

Ordinary store/render/compare selection stays released-only. Explicit draft rendering
and comparison require the existing per-call `--allow-unreleased` in isolated tests or
sandboxes. Installation may copy draft bytes without advancing the installed governance
version; this needs no filtering mechanism. Apply `AGENTS.md`'s verification-by-change
requirements to each draft delivery, including the [standing model-scenario decision](releasing.md#scenarios).

Seam E's `release-check/drafts/lifecycle.json` covers draft creation, updates, release,
frozen-tree mutations and invalid layouts. `release-check/release-and-copy.json` covers
cutting a version and copying its next draft in one change, plus divergent copies.
The lifecycle and combined cut run through depth-two PR-merge and squash-push histories
with CI's base/head contract.
The render suite checks released-only defaults, no-write draft refusals and explicit opt-in
against the real store. Machine-install verifies that copying draft bytes leaves the
installed version unchanged. The live runner selects the released version for a cut and
tests the two-slot v3 and one-slot v4 Initialize instructions offline. The policy-text checks
cover version 4's session marks and skill-invocation wording.

### Suite index

`SUITES` in `tests/run.py` names each suite, its module under `tests/suites/` and its job.
Register a new suite there under the job appropriate to its dependencies.

| Suite | Covers | Job |
| --- | --- | --- |
| `stored-form` | Stored form's round trip, materializing, and the stored-form check failing on planted paths | linux |
| `store` | Version 1's manifest, the change-note parser fixtures, released and installed versions | linux |
| `render` | Rendering's placeholders, confirmed values and unreleased versions, into a temporary directory and a worktree; version 3's retired Bugbot rule file removed from a version 2 tree | linux |
| `compare` | Exact comparison naming each difference | linux |
| `materialized-version` | Version 1 from the real store, rendered into tally and compared exactly, and its record parsed; each fixed file's notice, the Markdown form an HTML comment on line 1 (`MARKDOWN_NOTICE`); the mixed files' markers, well formed at version 1, with their notice as the first line inside them (`MIXED_NOTICE`) and their skeleton text after the end marker left uncompared; `AGENTS.md`'s sections in order and its bytes within `AGENTS_BUDGET`; `.cursor/BUGBOT.md` equal to its notice, a blank line and `AGENTS.md`'s Code Review Rules section, heading included; every path pointer in a Markdown file version 1 writes naming a file version 1 writes, with what stays outside in `UNROUTED`; no root `CLAUDE.md`, `AGENTS.override.md` or `.codex/` written; the `build.md` skeleton written with no notice and left uncompared; the role files' skill lists against #41 §13 and the relied-on list; the PR template's comment lines, continuation lines included, none starting with `Risk:` or `Reverts:`, and its one `Risk:` line, once filled, read by both parsers; `triage-labels.md` against the manifest's labels; Merge watch's workflow and script with the notice, their mode and exact comparison; planted mismatches failing; later templates' seam-3 checks join it | linux |
| `record` | Version 1's record template, rendered with sample confirmed values and read back; confirmed values the parser would refuse, refused at rendering; version 3's `review_bots` rendered, read back and refused when missing or malformed | linux |
| `parser-fixtures` | One result per parser and applicable fixture for the machine parser and every stored governed version, including the draft. Checks the reported results against the store and fixture catalogs. | linux |
| `gate` | Seam 1: every case in `tests/fixtures/gate/cases/` built into git and judged by version 1's gate, by version 4's and by version 5's, every case under `cases/v4/` by version 4's and by version 5's, and every case under `cases/v5/` by version 5's alone, each existing case given a lookup that confirms any commit and a `cases/v5/` case's `merged` key (`found`, `none` or `unreadable`) giving it, a case's `record_in` naming the commit that adds the record; the failure lines, the pattern rules, the rendered workflow, a sibling script importing the parser, and the entry fetching the head and posting through the stand-in; version 5's entry run against a recorded `gh` that answers the PR read, judging GitHub's body and head over the event's, posting on the event's head with one failure line when the read fails, calling the commit lookup only for a `Reverts:` line and reading its failure as unconfirmed, and titling the check with the declared tier; its workflow equal to version 4's byte for byte | linux |
| `merge-watch` | Seam 2: every case in `tests/fixtures/merge-watch/cases/` judged on its recorded event and GitHub answers, its records exact and compared field by field with `issue-tracker.md`'s format; the gate's parser imported from beside the script; the rendered workflow's triggers, `workflows` glob and six permissions, and it not being a required check; the six permissions on v4 and v5 (v5 uses Actions read for Copilot attribution); the entry reading and posting through the stand-in; version 3's cases under `v3/`, its review cases and its no-record base cases among them, judged by version 3's script beside version 3's gate; v4 declarations replayed in v5 with synthetic pre-merge dates and producer links, plus the v5 workflow entry on the #131 recording and the #233 historical-evidence cases, including incomplete results; GitHub's own `Not Found` told apart from a failed read | linux |
| `release-check` | Seam E covers [version transitions and copy equality](#unpublished-model-development), fixture preservation, and CI's PR/main-push event contract, jobs, commands and permissions | linux |
| `skill-copies` | Refreshing, verifying and listing changes against a local stand-in upstream, a planted one-byte change failing; the copies check on the real tree and on planted mismatches; both Codex key detectors on every shape in `tests/fixtures/machine/codex-policy-shapes.json`, one test per shape and detector | linux |
| `suite-runner` | Real suites CLI with isolated synthetic modules: concurrent rendezvous, serial scheduling and longest-first order, interpreter identity, complete output blocks, selection and worker limits, counts and summaries, failures/errors/load failures/crashes with a passing sibling | linux |
| `standins` | The stand-in GitHub and the Codex stand-in, a stray call included | macos |
| `machine-install` | Seam C: every install fixture of #44's Testing Decisions, the machine rules, forward-only refusals and the ready command against a local origin | macos |
| `machine-check` | Seam C: each machine-check item failing on its own with the home unchanged, Codex absent, personal skills' Codex problems only reported, and the Codex key detector's shapes | macos |
| `machine-list` | Seam C: the list's lines, header, private mark, miss count, sandbox skip and account refusal | macos |
| `machine-wizard` | Seam C: the account wizard in a throwaway home against the stand-in GitHub, whose logins take effect there; the walkthrough's steps, calls and last line, the machine check's identity item on its end state, a rerun changing nothing, each stop and the next run picking up, planted credential shapes in every answer and file it reads, and `machine/wizard.sh` from a fresh clone of a local origin | macos |
| `owner` | Seam D: every case in `tests/fixtures/owner/cases/` run through the rendered owner script of its `version` (default 1) against the stand-in, its writes, bodies and report lines exact; version 4's missing event-policy lines with their consequence and manual steps, and its private skip line equal to version 3's; the token refusal, the embedded program parsed as 3.9, and the owner-script command against a local origin | macos |
| `live-runner` | The live-check runner offline: the probe registry, the owner probes reading Seam D's reports and the stand-in's agent view, the gate probes judging recorded setups and rejections, Merge watch's probes against a small sandbox of their own with the real script judging their Merge summary, version 3's review probes the same way with version 3's script, the result comment, and habit's commands under `/bin/bash`; the real gate attempts command with test-local git and gh stand-ins, stopping at each possible success, carrying on after preparation failures, and its captured stopped and healthy output through `gate-rulesets`; the cut's `reset` and `end-to-end` against a local bare sandbox, each naming the version cut and its review bots and refusing a version that names none and the stand-in with no harness's variables, an ignored file beside the generator left out of the plugin and its identity, each refusal leaving nothing behind; the reset staging exactly the seed's tree, the plugin holding the committed generator under `cut`, habit's start line under `/bin/bash` with every scenario setting the generator reads unset | macos |
| `generator-core` | Seam A: every case in `tests/fixtures/generator/cases/` through the one entry, against the stand-in GitHub, synthetic stores and installed fixture homes, its exit codes and facts as `generator_support.py`'s docstring defines them; in every case no stand-in call writes but the invitation's acceptance and the worktree and home are unchanged; each probed harness's names judged as ADR 0013 requires; drift's target against `tests/target_state.py`, and the agent account's recorded view of a Gate in place; the handover rule, the skill files' four conditions and the identity hash, and the scenario settings | macos |
| `scenario-runner` | Seam B's runner with no model: the stand-in accepting a run's writes, the issue's block parsed, each assertion on planted evidence, and the three-run rule | macos |

## Generated Codex policy corpus

`tests/policy_corpus.py` generates inputs independently of both policy readers. The recipe
combines explicit continuation, comment, tab and block-scalar boundaries with 32 sampled
prefixes for each seed 1–4, then crosses them with four policy-key spellings. It retains
valid and malformed inputs without consulting a reader. The hand-written shapes and
their recording remain separate.

To reproduce the corpus, run `python3 tests/policy_corpus.py generate`. To re-record it,
run `python3 tests/policy_corpus.py record --codex <absolute-installed-codex-path>`.
Use the installed CLI only; installation or upgrade requires separate authorization. The recording
identifies its consumer version and corpus SHA-256. The initial recording used
`codex-cli 0.167.0-alpha.3.2` and `debug prompt-input x`, with no authentication, model or
network call. The recorder supplies only a synthetic HOME, CODEX_HOME, XDG directories,
TMPDIR and cwd, with a minimal environment; it never copies real-home configuration.

Each batch contains at most 16 inputs and one listable control sorted after them. First,
all skills must appear with their full unique descriptions without policy files. Then the
same skills are recorded with their policy files; every visible description and the control
must still be complete. This baseline prevents silent budget omission from masquerading
as policy enforcement. The recording keeps the CLI's complete skills-instruction strings,
normalizing scratch paths, and omits unrelated prompt content. It rejects nonzero exits,
stderr, missing skill sections, duplicate entries, omitted controls and shortened entries.

CI's `skill-copies` suite regenerates the corpus, binds it to the recording digest, verifies
batch coverage and budgets, and checks both current consumers: every user-only reading
must be hidden in the recorded real consumer. Deliberately unsafe reader substitutions
must fail on the original invalid-continuation defect; stale, incomplete and shortened
recordings also fail. Run `python3 tests/run.py suites skill-copies machine-check` for the
focused checks. CI never launches real Codex.

To extend coverage, append recipe inputs or seeds while preserving existing shapes and
names, regenerate, and re-record the whole corpus. Review the corpus/recording diff and
run the focused checks. This bounded corpus is evidence for its recorded CLI version,
not proof for all YAML or future consumers. A new reader mismatch returns to habit for
a bounded contract amendment; never filter it out or change product semantics here.

## Parsers

One parser implementation per side (#44 §5): the generator's library holds the machine
side's, and each stored version's gate script holds the governed repository's. The
`parser-fixtures` suite registers the machine parser once and loads the gate from every
numbered directory in the template store. Adding a draft directory brings its parser into
the next run automatically. A gate that fails to load fails the suite and the error names
the governed version. Verbose results name the machine parser or governed version and the
individual fixture.

- **The gate script's interface.** In a governed repository it is
  `.github/governance/gate.py`, and a script beside it, such as Merge watch's
  `merge_watch.py` or the owner script's embedded Python, runs `import gate`. A script run
  by path finds it on its own directory; embedded Python first puts `.github/governance/`
  on `sys.path`. Set
  `sys.dont_write_bytecode = True` before the import, so no `__pycache__` lands in the
  governed tree. The module's docstring gives the gate's rules and the pattern rules.
  - `parse_record(data)` takes the record's bytes and returns it in the shape
    `tests/suites/parsers.py`'s docstring gives, or raises `gate.RecordError`.
  - `parse_body(body)` returns `{"risk": ..., "reverts": ...}` in that docstring's shapes.
  - `matches(pattern, path)` matches a sensitive-path pattern against a root-relative path.
  - `verdict(repo, author, owner, body, default_head, head)` is Seam 1. It returns
    `passed`, `failures` and `pure_revert`. Each failure is one line led by its rule.
    Version 5 also takes the `merged` callback and can return `revert_note`.
  - **Version 4's pure revert** also requires the governance record at its fixed path
    in the reverted commit's parent: a commit that landed on a default branch already
    governed. One from before, the commit that first added the record included, is
    unconfirmed like a revert with a resolved conflict: no failure line of its own, and the
    floors judge it. When the floors then fail it, the `Floors:` line adds that the named
    commit predates governance. It reads git objects only, with no GitHub API call. A commit
    pushed without a PR after the record arrived still confirms; that boundary is accepted.
    Versions 1 to 3 keep the rule without the record condition.
  - **Version 5's pure revert** requires the historical record to be a regular file in the
    parent tree. After the git checks, GitHub must show a PR merged into the default branch
    whose squash commit is the named one. Merge watch uses the same match criteria.
    The gate validates the association's fields, including its merge timestamp, to tell
    an incomplete response from a definite negative. The `merged(sha)` callback passed to
    `verdict` returns `True`, `False` or `None` (unreadable, an exception included). The entry reads
    `gh api "repos/<repository>/commits/<sha>/pulls?per_page=100"`, with the event's
    `repository.default_branch`, whose checkout judges, as the branch (never the PR's current
    target, which a retargeted PR changes). A positive association
    confirms provenance even if another row is unreadable. With no match, a malformed
    association or a full first page leaves provenance indeterminate. Both negative and
    indeterminate lookups apply the ordinary floors. A failing floor includes the
    explanation in its `Floors:` line. Otherwise `revert_note` supplies the explanation for the
    posted summary, including when a different rule fails.
- **Its template loads as it is**, since its one token sits in its first line, a comment:
  `PARSERS` in `tests/suites/parsers.py` loads it by path.
- **The record**: `govlib/record.py`, whose docstring defines the format in full. A list key
  with no items is null in YAML, and the record reads it as an empty list, which is how
  rendering writes one. Text that starts like a number, or that YAML could read as null or
  a boolean, doesn't parse unless double-quoted, and rendering double-quotes every
  confirmed value.
- **The PR body's `Risk:` and `Reverts:` lines**: `govlib/prbody.py`. Only lines that start
  with `Risk:` or `Reverts:` count, inside comments and code fences too, and a CRLF body
  reads as LF.
- **The shared parser fixtures** live in `tests/fixtures/parsers/`. Every parser runs the
  common record and PR-body cases in `expected.json`, including its inline texts for inputs
  that `git diff --check` would flag. The machine parser and governed versions 3 and later
  also run the `record-v3/` fixtures in `expected-v3.json` for the confirmed `review_bots`
  format. Versions 1 and 2 predate that format and run the common cases. Add a fixture and
  its expectation to the corresponding family to exercise it across all applicable
  parsers. For an inline PR-body case whose grammar changed in v5, set `expected` to the
  current result and `expected_before_v5` to the released v1–v4 result. Each adapter
  returns the shapes described in `tests/suites/parsers.py`. A record
  that doesn't parse expects only "doesn't parse".

### Reproducing the ref-pattern corpus

`tests/fixtures/owner/ref-patterns.json` retains the historical Ruby answers; its
original seeds are unavailable. The separate `ref-patterns-generated.json` is a reproducible
supplement, generated by `tests/ref_patterns.py` independently of the owner matcher.
`FAMILIES`, `SEEDS` and `SAMPLES_PER_SEED` define its coverage and bound: token cross-products
cover each family, then seeded compositions combine them. Candidate strings only supply
inputs; Ruby alone determines the verdicts. Inputs include malformed and unsupported forms
to exercise the matcher; matching them does not certify that GitHub accepts them. Seam D's
existing unsupported-pattern checks still require unknown reach and no destructive write.

To add a token family, extend `FAMILIES` and its generation-coverage test, then re-record
the entire supplement using `/usr/bin/ruby` (the original recording used Ruby 2.6.10):

```sh
python3 tests/ref_patterns.py pairs > /tmp/ref-pattern-pairs.json
python3 tests/ref_patterns.py record > /tmp/ref-patterns-generated.json
```

The recording includes Ruby's version and description and invokes `File.fnmatch` with
`FNM_PATHNAME` for every pair. After the recording command succeeds, replace only
`tests/fixtures/owner/ref-patterns-generated.json` with its output and run
`python3 tests/run.py suites owner`. Review the corpus diff and Ruby version; describe any
changed existing expectation in the PR body (or the change note when cutting a version).
Keep the historical fixture unchanged. If Ruby and the released matcher disagree, escalate
for later-version product work; changing a recorded answer to fit the port defeats the oracle.

CI runs the supplement's exact generated-pair equality and matcher/verdict checks in the
`owner` suite, without Ruby or network. Added, missing, reordered or changed pairs fail the
equality check; a wrong verdict fails the matcher comparison. Re-recording is an explicit
maintenance command, never a CI step, and doesn't run the owner script or touch GitHub.
