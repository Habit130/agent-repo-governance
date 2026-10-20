# Issue Tracker: GitHub

Issues and specs for this repository live as GitHub issues in `Habit130/agent-repo-governance`. Use the `gh`
CLI with `--repo Habit130/agent-repo-governance`, since the target is otherwise ambiguous.

## Conventions

- **Create an issue**: `gh issue create --repo Habit130/agent-repo-governance --title "..." --body-file <path>`
- **Read an issue**: `gh issue view <number> --repo Habit130/agent-repo-governance --comments`; add
  `--json number,title,body,labels,assignees,comments` for fields
- **List issues**: `gh issue list --repo Habit130/agent-repo-governance --state open --label <label> --json number,title,labels`
- **Comment on an issue**: `gh issue comment <number> --repo Habit130/agent-repo-governance --body-file <path>`
- **Apply or remove a label**: `gh issue edit <number> --repo Habit130/agent-repo-governance --add-label "..."`
  (or `--remove-label`)
- **Make a sub-issue**: `gh issue edit <parent> --repo Habit130/agent-repo-governance --add-sub-issue <child>`
  (gh 2.94+); without sub-issues, put `Part of #<parent>` at the top of the child body
- **Close**: `gh issue close <number> --repo Habit130/agent-repo-governance --comment "..."`

GitHub shares one number space between issues and PRs: resolve a bare `#42` with
`gh pr view 42`, then `gh issue view 42`.

## Delivery operations

- **Claim a contract**: `gh issue edit <number> --repo Habit130/agent-repo-governance --add-assignee @me`,
  then post the claim comment (`delivery.md`). Claim only an issue that has a handoff comment.
- **Dispatch** is the handoff comment (`delivery.md`).
- **Contract body** is frozen at dispatch; append evidence, ledgers and records as comments.

## Pull requests as a triage surface

**PRs as a request surface: no.** Set `yes` only if this repository treats external PRs as
feature requests; `triage` reads this flag.

## When a skill says "publish to the issue tracker"

Create a GitHub issue.

## When a skill says "fetch the relevant ticket"

Read it as in **Read an issue**, comments included.

## Wayfinding operations

Used by `wayfinder`. The **map** is one issue and its **child** issues are the tickets.

- **Map**: an issue labelled `wayfinder:map`.
- **Child ticket**: a sub-issue of the map (see **Make a sub-issue**) labelled
  `wayfinder:<type>`, where type is `research`, `prototype`, `grilling` or `task`; assigned
  to the driving developer once claimed.
- **Blocking**: GitHub's native issue dependencies,
  `gh api --method POST repos/Habit130/agent-repo-governance/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-db-id>`,
  where `<blocker-db-id>` is the blocker's database id
  (`gh api repos/Habit130/agent-repo-governance/issues/<n> --jq .id`). Without dependencies, put a
  `Blocked by: #<n>, #<n>` line at the top of the child body. A ticket is unblocked when
  every blocker is closed.
- **Frontier**: the map's open children with no open blocker and no assignee; first in map
  order wins.
- **Claim**: `gh issue edit <n> --repo Habit130/agent-repo-governance --add-assignee @me`, the session's first
  write.
- **Resolve**: comment the answer, close the ticket, then add a gist and link to the map's
  Decisions-so-far.
