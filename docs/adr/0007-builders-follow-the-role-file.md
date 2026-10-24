# Builders follow the committed role file, not the published `implement`

mattpocock's published `implement` skill has three gaps for this flow. It creates no branch, pushes nothing and opens no PR. It also reviews before it commits, so on a fresh branch its review sees an empty diff.

So in a governed repository, the Builder role file calls the useful model-invoked steps, `tdd` and `code-review`, directly. That also keeps habit's start instruction the same plain text in every harness.

Decided in [How work flows from idea to merged PR](https://github.com/Habit130/agent-repo-governance/issues/14).
