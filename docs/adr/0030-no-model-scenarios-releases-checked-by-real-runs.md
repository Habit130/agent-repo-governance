# No PR runs a model scenario, and a release is checked by two real runs

No PR in this repository runs a scenario or a replacement for one, releases included. A release's behavior is checked by its end-to-end run, an Initialize of the public sandbox repository, and by this repository's own Upgrade to the new version. Repair and OpenCode have no behavioral check before a release. A failure in use is a miss, repaired in a later version.

habit stopped scenarios for their cost in model quota: ten headless runs on every head. One run of each scenario before a release was the alternative, and it wasn't chosen.

This changes the first row of [ADR 0022](0022-verification-by-change-not-tier.md): a PR that touches the generator now records final-head model behavior as unverified. The runner that [ADR 0024](0024-scenarios-in-resumed-headless-sessions.md) describes stays as reference, and its offline tests still run.

Decided in [Record that model scenarios are no longer run](https://github.com/Habit130/agent-repo-governance/issues/139) and [Whether and how to replace the model scenarios as verification](https://github.com/Habit130/agent-repo-governance/issues/138).
