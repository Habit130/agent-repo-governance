# Bugbot rules

## Risk tiers

A change takes the highest tier any part of it reaches.

| Tier | The change |
| --- | --- |
| low | A two-way door with a small blast radius, touching no sensitive path, and covered by its verification. Examples: docs, copy, comments, tests, internal refactors that keep behavior, small fixes covered by tests, additive changes behind a default-off flag. |
| medium | Ordinary product changes, such as user-visible behavior or an interface, CLI or API. Also: dependency changes, build or CI configuration, shared modules, any sensitive path, and any PR whose author isn't trusted. |
| high | One-way doors: data migrations, destructive operations, releases and publishing. Also: authentication, privacy and secret handling; production resources; a broad blast radius; changes that loosen governance or its enforcement, such as removing a required check or shrinking the sensitive-path list; and the generator's Initialize and Upgrade output. |

## Sensitive paths

A change to any of these paths is at least medium:

- `AGENTS.md`
- `docs/agents/`
- any `CLAUDE.md`
- `.github/`
- `.claude/`
- `.opencode/`
- `.dsh/`
- `.agents/`
- `opencode.json`
- each review bot's rule file, `.cursor/BUGBOT.md` included

## Tier check

The PR body declares `Risk: <tier> — <reason>`. If the change warrants a higher tier, report it as a blocking bug.

## Canary

Always add one non-blocking finding titled `rule-file canary`.
