# A private repository qualifies only when its rules are in effect

Without enforced rulesets, nothing on GitHub's side stops an agent's push or merge. So the generator governs a private repository only after confirming that its rules bind the default branch.

- Rulesets don't apply to private repositories on GitHub Free, so a private repository on Free never qualifies.
- If a governed private repository's rules lapse, it is handled like a disabled ruleset. Whoever writes the Merge summary tells habit the remedies and still hands over the merge command.

Revised on 2026-10-22, after habit's GitHub Education application was approved. Its GitHub Pro benefit takes effect around 2026-10-25. The earlier decision was that private repositories aren't governed on GitHub Free.

Decided in [How the generator turns a repository's state into its governance](https://github.com/Habit130/agent-repo-governance/issues/17), as revised in [this comment](https://github.com/Habit130/agent-repo-governance/issues/17#issuecomment-6337855914).
