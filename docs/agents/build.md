# Build and Verification

The executable paths and the non-obvious ordering that delivery sessions need. Human-facing
setup stays in the README.

## Required order

No build or test dependency order exists. Run the whitespace check, then the scope check;
for governance deliveries also perform the structural checks below.

## Commands

| Task | Command | Evidence / notes |
| --- | --- | --- |
| Whitespace | `git diff --check` | Run before committing; exits 0 on the verified skeleton. |
| Committed whitespace | `git show --format= --check HEAD` | Run after committing. |
| Scope | `git diff --stat origin/main...HEAD` and `git status --short` | Inspect against the frozen contract; before committing also inspect `git diff --stat`. |

## Operational constraints

- No product runtime, build, lint, typecheck, test suite or CI workflow is configured.
  No required CI check names exist on the default branch. Documentation checks do not
  demonstrate runtime compatibility of future implementations.
- For governance deliveries, verify paths, links, headings, router targets, unresolved
  rendering placeholders, the root instruction budget (near 100 lines and below 12 KiB),
  and ignore behavior with `git check-ignore`. Template prompts are intentional;
  frozen contract bodies must have every prompt filled. Parse changed JSON when present.
- Local read-only checks run autonomously. GitHub operations require repository access
  and follow the frozen contract and `delivery.md`. Preserve unrelated work.
- No shared machine-level runtime, data store, deployment resource or product module
  boundary has been identified in this skeleton. Allocate any newly introduced shared
  resource explicitly before parallel writers use it.
- Engineering skills are installed in the local environment; availability in a session
  depends on its harness. If a listed skill is unavailable, report the gap and ask habit
  to launch it in an environment where it is available; never substitute a denied load.
