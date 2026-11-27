# Generator command line

Start with [Build and verification](../agents/build.md) for the ordered checks and
habit-only commands. This reference describes the current state.

`generator/govern-repository/scripts/govern.py` is the generator's one entry. Its
subcommands (`store`, `change-note`, `render`, `compare`, `materialize`, `owner-command`,
`handover`, `identity`, `mend-markers`, and the mechanical core's `preconditions`, `mode`, `inspect`, `read` and `accept-invitation`) print JSON
and exit 0 on good facts; 1 when exact comparison finds differences, a precondition or a file read fails, or
the mode is stop; and 2 on a refusal, with the reason under `error`.

- **Reading repository text.** `inspect` reports the commit in `byte_identity.head` and a
  boolean per inspected path in `byte_identity.files`. Only matching files supply content
  facts. `read --worktree <checkout> -- <path>` returns JSON with the path and the raw
  committed text after credential redaction. Each redaction names the type, path and
  original line. Valid Unicode is printed as UTF-8. Undecodable bytes use JSON surrogate
  escapes. Exit 1 returns only the path, with no credential finding from either version.
  Both commands check the index and the pinned commit for regular files and compare the
  working bytes without following links or applying filters. A failed record check also
  stops `preconditions`, `mode` and `mend-markers`. When checking drift, `mode` reports
  present but unverifiable targets under `drift.unverified_files` by location. Marker
  repair checks its inputs before writing or reporting dropped lines.

- **Damaged markers** are mended before rendering: `mend-markers --worktree <path>` gives each
  fixed part's file whose markers `mode` reports damaged one well-formed block at the record's
  version, so `render` can fill it. Intact governance text gets its markers back; edited text
  is rebuilt, keeping the text before the begin marker and the repository's own part from
  the line the template puts after its end marker, or from the one end marker left. It lists
  each file's `repair` and the non-version lines it `dropped`, and refuses, writing nothing,
  when the repository's own text can't be told apart: with the begin marker gone, text above
  the version's first line, or with the end marker gone, neither it nor the line after it left.
  A path through a symlinked directory is refused too. It is tested in `generator-core`.

- **Relied-on skill names** in a version manifest must be a list of unique lowercase,
  hyphenated strings. Each entry's type and spelling are checked before deduplicating;
  objects and lists receive the same JSON refusal as other malformed entries, with no
  traceback or store writes. `tests/fixtures/stores/relied-on-skills.json` records the
  S-1 miss and the rejected and accepted CLI inputs; the `store` suite also checks stderr
  and snapshots every fixture-store file's bytes and mode.
- **Exact comparison in a governed worktree** is one command:
  `python3 generator/govern-repository/scripts/govern.py compare --worktree <path>`. It reads
  the repository and default branch from the worktree's `origin`, and compares the installed
  version unless `--version` names another.
- **Literal default branches** use Git's rules, not a punctuation allowlist. Both render
  and compare run `git check-ref-format refs/heads/<name>` as an argument vector without
  a shell, plus Git's branch-only leading-`-` and `HEAD` restrictions. They never use
  `--branch`, which expands `@{-n}` using checkout history, or normalize the spelling.
  A name containing the exact substring `${{` is explicitly unsupported: both commands
  return exit 2 and a JSON `error` identifying the unsupported Actions-expression marker
  before writes. This is the chosen support boundary, not a claim of platform
  impossibility; no expression-based encoding (including a static string expression) is
  generated. Dollar signs and braces without that substring remain supported.
- **Branch filter encoding has two layers.** In the Gate and Merge watch workflow templates,
  a bare `@@default_branch@@` on its own six-space-indented list-item line represents one
  complete filter scalar. Actions `+` and leading `!` are escaped with backslashes, then
  JSON-compatible double quoting encodes the YAML scalar (quotes, backslashes and YAML
  line breaks included). For example `release+stable` becomes YAML `"release\\+stable"`,
  whose decoded filter is `release\+stable`. Gate's one filter and Merge watch's two
  filters use the same path in rendering and comparison. Prose uses retain the unescaped
  literal name; ordinary `main` retains its previous rendered bytes. Substitution is a
  single pass: inserted values never become template source. The existing three token
  names and unknown/leftover-token refusal remain unchanged, and render plans every file
  before writing any of them.
  `tests/fixtures/stores/branch-names.json` records S-2's miss, hand-written expected
  filters and nearby nonmatches, invalid Git names, unsupported marker inputs and token
  safeguards. The `render` suite exercises both real CLIs against synthetic and real v1
  stores, plants mismatches at all three filter sites, and keeps complete no-write
  snapshots including `.git` and its objects.
  Primary sources read 2026-11-02: [Git naming and shorthand rules](https://git-scm.com/docs/git-check-ref-format#_description),
  [Git's branch-only checks](https://github.com/git/git/blob/master/refs.c) (`check_branch_ref`),
  [Actions branch filters and filter grammar](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#filter-pattern-cheat-sheet),
  [YAML quoted scalar escapes](https://yaml.org/spec/1.2.2/#73-flow-scalar-styles).
  Git forbids the filter operators `*`, `?`, `[` and backslash in literal branch names;
  `+` repeats the preceding character, and leading `!` negates a filter. YAML quoting
  alone does not escape those filter operators.
- **Unreleased versions** are rendered or compared only with `--allow-unreleased`, which a
  test or live-check runner passes for its own run. The generator's procedure never passes
  it. A scenario needs none, since its synthetic store carries a change note.
- **Scenario settings.** Three environment settings only the scenario runner sets:
  `GOVERN_SCENARIO_STORE` and `GOVERN_SCENARIO_HOME` replace the `--store` and `--home`
  defaults, and `GOVERN_SCENARIO_REPOSITORY` names the repository in place of a local
  `origin`, which `git remote get-url` can't show as GitHub. Absent, the entry behaves as
  without them, and the skill text names none of them, so no skill file changes for a run.
- **Exact comparison** checks content and mode of every fixed file, every fixed part between
  its markers, and the record up to its one top-level `confirmed:` key, after which only
  indented values, blank lines and comments may follow. It excludes confirmed values and
  repository-owned skeletons. For changes to confirmed values, follow
  [Governance files](../../AGENTS.md#governance-files).
- **Rendering a fixed part** writes the whole template when the target is absent, replaces
  the one well-formed marker block when there is one, and refuses anything else. A skeleton
  is written only when its target is absent. `mode` reports damaged markers; restoring or
  rebuilding them is the write phase's (#52).
- **One template per target path.** A mixed file's template holds its fixed part between the
  markers and its skeleton text after them. The record template ends at its `confirmed:`
  key, and rendering writes the confirmed values below it. Rendering refuses confirmed
  values, or a template, whose record wouldn't parse.
- **Writes stay inside the destination.** Rendering and materializing refuse a target whose
  parent is a symlink or not a directory before writing anything.
- **The mechanical core** (#44 §6.1 to §6.3) runs before habit's confirmation and writes
  nothing, to GitHub or to the checkout, except `accept-invitation`. Each takes `--worktree`
  (default: the current directory); `preconditions` and `inspect` take `--home` (default: ~),
  `preconditions` and `mode` take `--store` (default: the store beside the entry). The
  modules' docstrings define the facts: `govlib/preconditions.py`, `drift.py`,
  `inspection.py`, `workflows.py`.
  - **Harness eligibility** follows [How to start](../../AGENTS.md#how-to-start).
    The harness check runs first in all four. A refusal prints the harness facts under
    `harness` with exit 2. `govlib/harness.py` passes only when `CLAUDECODE` (Claude Code)
    or `OPENCODE` (OpenCode) is set, not both, and no `CODEX_…`, `DSH_…` or `ANTIGRAVITY_…` variable is,
    the homes `CODEX_HOME`, `DSH_HOME` and `DSH_AGENTS_HOME` aside. Each harness's shell was
    probed by name (the first four on 2026-10-29, Antigravity's CLI on 2026-11-25 and its app on
    2026-11-26), and the names are recorded in
    `tests/fixtures/generator/harness-probes.json` with each harness's version.
  - **`preconditions`** reports every §6.1 item together with habit's checklist. It runs the
    installed machine check, `~/.agents/governance/machine/scripts/machine.py check --home`,
    and reads the managed skills from `~/.agents/governance/installed.json`. On a private
    repository its `private` item takes #17's read through `govlib/rules.py` (#53): the
    rulesets list at Initialize, the default branch's rules otherwise, after-merge included.
    It passes only on rulesets available or every Gate and Merge rule type listed; the Pro
    refusal, a missing type and any case it can't decide fail, each with the Chinese lines
    habit hears and the English line the issue records under `rules_in_effect`.
  - **`mode`** gives the mode and, at Upgrade and Repair, drift against the record's version:
    exact comparison with GitHub's default branch, the markers with whether the generator's
    text between them is intact, and GitHub state against `govlib/target.py`, which Seam A
    checks against `tests/target_state.py`.
  - **Every GitHub read in `mode` gets one retry** (`github.Retried`, CRIT-10). One that stays
    failed sits under `drift.github.unreadable`, and an inactive ruleset the agent read but
    can't place sits under `unplaced`; either keeps the outcome from reading as no drift.
  - **`handover`** takes a saved `mode` report, `--mode-facts <file>`, and
    `--required-checks-changed` when habit's answer changed them. It prints `owner_command`
    and the Chinese lines habit hears with the command; `mode` reports the same rule under
    `drift.handover` before the answer. It is the only place that rule lives, and
    `tests/fixtures/generator/handover.json` holds its table.
  - **`accept-invitation`** accepts the agent account's pending invitation to the
    repository, the one write before habit's answer.
  - **Antigravity's project scope.** `inspect` reads `GEMINI.md` and the files under
    `.agents/`, `_agents/`, `.agent/` and `_agent/` (rules, hooks, MCP servers, plugins,
    custom subagents, workflows and skills). The root `.gemini/config.json` can name a
    personal folder in `personal_customization_dir`. Inspection lists the config separately
    from Gemini Code Assist's rules. See [Customization discovery](https://antigravity.google/docs/customization-discovery.md),
    read on 2026-11-27. The public documentation, read on 2026-11-26, says the app keeps project
    permissions in its settings UI (Settings > Projects) and names no storage location for
    them, so no repository location gets the same treatment.
  - **No credential value is printed** (#41 §10). `inspect` names each credential shape it
    finds by type and location, and the entry passes every JSON it prints through
    `govlib/secrets.py`'s `redact`, which replaces each shape with its type, so a command's
    text, a title or an error carries none. A private key is redacted from its header to its end
    marker, or to the text's end without one, and in a document's shell block its lines are
    never read as commands.

    Seam A's source-to-output inventory is `tests/suites/credential_support.py`: it names
    each selected input and output field, the command-producing manifest names, document
    families and GitHub strings. Full-entry tests require exact redacted fields (proving
    echo reachability), type/location reports and no plant in stdout or stderr. Runtime
    plants cover every `SHAPES` class; set equality requires a plant for a new class.
    An isolated copy with redaction bypassed is the negative control for inspection facts
    and caught errors. `CommittedReads` checks every shape's original location in both
    the reader's `text` and marker repair's `dropped` lines, including a multiline key. Existing private-key fixtures retain the document-discard and
    truncated-key checks. Review the inventory when adding an echoed source; supported
    manifest names and the document-name expression are checked mechanically. Make/just
    target grammar and discarded document key lines limit which shapes can echo there.
    The single-writer AST guard covers direct print, process-stream references/aliases and
    low-level descriptor writes in the entry and `govlib`, allowing exactly one stdout
    writer in `emit`; it is not dynamic information-flow analysis. It leaves subprocess
    capture and unrelated tools alone. Focused command: `python3 tests/run.py suites generator-core`.
    Diagnostics name plants, never their values.
- **GitHub's facts the core relies on**, as the agent account, a write collaborator, read on
  2026-10-29 from Habit130/governance-sandbox and Habit130/agent-repo-governance, and from
  GitHub's REST reference pages for rules, branches and invitations the same day:
  - `GET repos/{r}` gives `permissions` and the five merge settings; `security_and_analysis`
    is null, and `actions/permissions` and `actions/permissions/workflow` answer 403. That is
    the blind spot the owner script checks.
  - `GET repos/{r}/rulesets/{id}` returns `bypass_actors` as null (the reference: "only
    returned if the user making the API request has write access to the ruleset"), and adds
    `pull_request` parameters the owner script never sends.
  - `GET repos/{r}/rules/branches/{b}` lists each active rule on the branch with its
    `ruleset_id`; rules of `evaluate` or `disabled` rulesets aren't returned, so whether such
    a ruleset applies is reported as unknown unless its patterns name the branch outright.
  - `GET repos/{r}/branches/{b}` returns `protection.enabled`, undocumented: `true` on
    python/cpython's `main`, which has classic protection and no ruleset, and `false` on the
    two repositories above, protected by rulesets only. It is the classic-protection fact;
    `.../protection` needs admin.
  - On a private repository, #17's revision (phase 1 on Free, phase 2 on Pro, and its lapse
    simulation, run 2026-10-23 and 2026-10-26): `GET repos/{r}/rulesets` and
    `GET repos/{r}/rules/branches/{b}` answer 403 "Upgrade to GitHub Pro or make this
    repository public to enable this feature." when the rules can't bind, and 200 when they
    can, the rules read listing `deletion`, `non_fast_forward`, `pull_request`,
    `required_status_checks` and `update`; the agent's push, force-push and merge were
    accepted in the first case and rejected in the second. Seam A's stand-in answers both
    reads that way under `rulesets_forbidden`.
  - `GET user/repository_invitations` lists the agent's open invitations;
    `PATCH user/repository_invitations/{id}` accepts one and answers 204.
- **The change note** opens with `urgency: urgent` or `urgency: when convenient`, then
  `must-act: yes` or `must-act: no`, then a blank line and the plain-Chinese body. Its parser
  and fixtures: `govlib/store.py` and `tests/fixtures/change-notes/`.


## Version manifests and retired paths

Version 3 and later support `review_bots` (`codex`, `copilot`) and `retired`, the generated
paths removed by that version. A manifest with `review_bots` requires a confirmed list
containing supported bots without duplicates; render refuses a missing list before writing.
Versions 1 and 2 refuse that key. Render removes a retired path only when its first line
carries the generated notice, and lists it under `removed`; exact comparison reports it
as a `retired` difference. The preconditions' review-bots item names the installed version's
bots, or Bugbot and the Codex review bot for a version without them.
