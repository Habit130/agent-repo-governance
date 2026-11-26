# Machine and skill copies

Start with [Build and verification](../agents/build.md) for the ordered checks and
habit-only commands. This reference describes the current state.

`machine/scripts/machine.py` is the one entry for the install, the machine check, the
governed-repository list and the account wizard (#44 §8, §9). Its subcommands, `install
--source <tree> --home <dir>`, `check`, `list` and `wizard`, print Chinese reports and exit 0
when nothing failed, 1 when an item or line failed or the wizard stopped at a step, and 2 on a
refusal that wrote nothing. `machinelib/__init__.py` names the layout; `install.py`'s and
`wizard.py`'s docstrings give the steps.

- **The ready command**: see [habit-only commands](../agents/build.md#commands-only-habit-runs).
- **The account wizard command**: see [habit-only commands](../agents/build.md#commands-only-habit-runs).

  It reads each login with `gh auth status --hostname github.com --active --json hosts`. From
  gh 2.98.0's source (`pkg/cmd/auth/status/status.go`, `internal/config/config.go`, read
  2026-11-04): with `--json` it always exits 0, no login prints `{"hosts":{}}`, the token is
  dropped from the output, a keychain token's `tokenSource` is `keyring`, a plain-text one's
  the `hosts.yml` path, and `scopes` is the `X-OAuth-Scopes` header, comma-separated.
  `gh auth login --web` stays interactive on a terminal and may ask whether to set up git's
  credential; either answer is fine, since the wizard runs `gh auth setup-git` itself. Its
   credential step conservatively models Git's `credential.c` and `urlmatch.c` (read
   2026-11-05): system and global helpers in config order; only an unconditional or exact
   `https://github.com[/]` / `github.com[/]` match may apply an empty reset. Only canonical
   literal lowercase DNS HTTPS hosts other than github.com are certainly excluded. Other
   URL spellings (including username/port qualifiers, parse failures, patterns, paths and
   normalization such as a trailing host dot) add uncertainty, never clear earlier helpers
   or prove gh's route; a later
   certain reset clears that uncertainty too. Residual uncertainty stops the step in Chinese.
   `fill` stops at the first helper that answers and `approve` stores to every one, so the
   step passes only with exactly gh's helper and no uncertainty (AC-48's Acceptance A1).
   Isolated real-Git regressions cover the false resets and no-op reruns. It reads outside any repository, so a
  repository-dependent conditional include (`includeIf`) may stay inactive. The step lists
  every observed condition and origin and explicitly leaves repository-local routing
  unverified. Its checklist asks habit to authorize a scoped read-only check of matching
  repositories, including directory, branch and remote conditions, all configuration
  scopes and nested includes; it does not perform that check or execute helpers.
  On an uncertain stop, diagnostics name the remaining helper keys and origins, never
  helper bodies. They prioritize preserving unrelated services and verifying an equivalent
  correction before changing anything; meaningful URL qualifiers must be retained.
  Metadata is quoted and known credential shapes redacted. URL fields (credential keys
  and remote-URL include conditions) additionally hide userinfo, including bare URL forms,
  and withhold query/fragment tails before userinfo processing, so a later `@` cannot
  erase the delimiter that marks sensitive tail data; origins and non-URL conditions retain legal path
  punctuation. The credential-route tests exercise the wizard with synthetic included
  files, credential-bearing metadata and unchanged source-file assertions. The
  `machine-wizard` suite never runs `ghm` or any `gh` inside a login shell: macOS's login
  profile reorders PATH, so a real gh there could reach the keychain.
- **Generated credential routes**, in `machine-wizard`'s `GeneratedCredentialCorpus1` to
  `GeneratedCredentialCorpus3`, compare the credential step with the runner's real Git;
  `GeneratedCredentialRoute` holds the oracle's negative controls and checks that the three
  parts cover the corpus once. The exhaustive bounded corpus combines three schemes, eight
  hosts and five decorations, each before/after gh's section and with/without a reset: 480
  routes, every third URL in each part, and each part keeps every assertion.
  Each route starts with an earlier synthetic helper. Certified routes must call only the
  test-local gh helper on both `fill` and `approve`; certain nonmatches are checked without
  a masking reset. Successful reruns preserve the home's bytes. Two deliberately unsafe
  matcher substitutions prove the oracle catches false resets and storage fan-out hidden
  by `fill`'s short circuit, with the offending helper calls pinned before the expected
  invariant failure. An unrelated Git-action failure cannot satisfy the reset control.
  An explicit disposable `GIT_DIR` prevents parent-repository discovery by both the
  credential step and the oracle; a planted parent helper tests this even when the step's
  temporary directory sits inside that repository. Helper usernames are synthetic, and
  failed fill-field checks omit the returned fields from assertion output, with a
  regression for both username and password failures.
  Output names Git's version and the corpus parameters; Git
  credential subprocesses have a ten-second timeout. All helpers, configuration, homes
  and call logs are disposable and synthetic; no login, keychain or real configuration is
  used. This bounded sweep is not proof for every Git URL spelling; a newly exposed
  product mismatch returns to habit rather than relaxing the fail-closed model.
- **Run on their own** from the installed copy: `/usr/bin/python3
  ~/.agents/governance/machine/scripts/machine.py check` and `... list`. The installed state
  is `~/.agents/governance/installed.json`; there the entry imports `govlib` from the
  installed generator.
- **Codex's real behaviour**, recorded under `tests/fixtures/machine/` from the ChatGPT app's
  CLI: `codex execpolicy check --rules <file> <words...>` takes no `--` (it would become a
  command word), exits 0 whatever the decision, and omits `decision` when no rule matches.
  `codex debug prompt-input` prints no budget warning; it shortens descriptions and drops
  entries silently, in name order, so the check compares the listed names with the home's skills.
- **Personal skills**: a machine skill is a directory in
  `~/.agents/skills` named in the machine skill set; every other skill there and every skill
  in `~/.codex/skills` is personal. The install never writes inside a personal skill, nor
  through a link inside one, and adds no Codex user-only key anywhere: machine skills carry
  theirs in this repository. The check fails a machine skill's missing key, omitted entry or
  shortened description, and reports a personal skill's as a `说明` line that never fails. A
  machine skill whose key reads `unclear` is still looked for in Codex's list, so its omission
  fails; a personal one's is left out.
- **Codex's user-only key** is read by its effective value in one detector,
  `machinelib.skills.codex_policy`, which the copies share. Only `false` is user-only. Codex
  ignores an `agents/openai.yaml` that real YAML refuses (repeated keys, tabs, open quotes, a
  plain value continued after a comment or by a line holding `: `), or where a field it
  types, such as `interface`, `dependencies.tools` or a `policy` field, holds the wrong type.
  So a shape the detector can't read safely is `unclear`, flow collections, escapes and a
  value's next line that isn't plain text included, which fails a machine skill and never
  reads as user-only. `tests/fixtures/machine/codex-policy-shapes.json` is the shared shape
  set; a new shape the detector reads as `false` joins it and its real recording,
  `codex-prompt-input-policy-shapes.json`, re-recorded with the shape's skill.
  A block scalar's first nonblank content line fixes its content indentation for the
  whole scalar: deeper lines may return to it, but a line below it (even above the
  key's indentation) is `unclear`. Leading-blank, tab and hidden-policy refusals remain.
  The generated `PolicyShapes` tests exercise both consumers and copies' byte-preserving
  acceptance or refusal. The 2026-11-02 recording uses the installed ChatGPT CLI,
  `codex-cli 0.166.0-alpha.5.1`, invoked as
  `/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex debug prompt-input x`
  through `Home.run_codex`: synthetic HOME, XDG configuration/state/data/cache and
  TMPDIR, plus disposable CODEX_HOME and cwd, all inside scratch space. No model,
  authentication or network call is needed. All shared shapes are present as
  inputs; `no-policy` is the listable control, and no old shape changes visibility.
  The recording normalizes only home, disposable CODEX_HOME and cwd paths as above.
- **Seam C suites** build the source tree from this checkout's `machine/` and generator with
  synthetic copies (`tests/suites/machine_support.py`), so the real recordings stay true
  when the copies change. They pass the Codex stand-in or a missing path, never the app,
  and put a `ghm` tripwire first on the path. Re-record a fixture home's Codex output with
  the real CLI when its skills change, replacing the scratch home's path with
  `/fixture-home`.

## Skill copies

`skill-copies/` holds the third-party skill copies (#44 §10, ADR 0020): upstream's `LICENSE`,
`provenance.json`, one whole upstream skill directory per copy under `skills/<name>/`, and the
scripts under `scripts/`. `scripts/copylib.py`'s docstring defines the manifest and the one
allowed change, the Codex user-only key appended to a user-invoked skill whose
`agents/openai.yaml` has no `policy` key. The copies read the key with the machine's detector
(this document).

- **The copies check**, `python3 tests/run.py copies`, fails unless the copies under
  `skills/`, the manifest's entries and the highest version's `relied_on_skills`
  (`govern-repository` aside) name the same skills, all from one upstream commit, and every
  user-invoked copy reads as user-only. The `skill-copies` suite runs it on the real tree in
  the `linux` job.
- **An update PR** refreshes every copy from one upstream commit with
  `python3 skill-copies/scripts/refresh.py --commit <sha>`, which replaces `skills/`,
  `LICENSE` and the manifest and refuses, writing nothing, when a relied-on skill is missing,
  a user-invoked one has no `agents/openai.yaml` or a policy that one appended block can't
  make user-only (one that isn't `false`, or `unclear`), or an upstream path fails stored form.
- **Verification**: `python3 skill-copies/scripts/verify.py` fetches each recorded commit and
  prints a PASS or FAIL line per copy and for the license, then each added Codex key. CI has
  no network, so the Builder runs it on the PR head and the Reviewer reruns it. For a planted
  change, pass `--copies` a modified copy of `skill-copies/` in a temporary directory.
- **The change list**: `python3 skill-copies/scripts/changes.py --to <newer sha>` prints, in
  plain Chinese, what changed per copy since the recorded commit, quoting up to ten changed
  lines per file, for the Merge summary; `--from` names another older commit.
- Only these evidence runs reach GitHub, read-only. Suites pass `--upstream` a local
  repository built at test time instead.
