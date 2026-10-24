# Governance model versions only move forward, and released templates never change

A governance model version is an increasing integer. A new one is cut only when what lands in a governed repository changes. The generator keeps every released version's templates unchanged.

Exact comparison and drift detection rely on that. So a fix or a rollback is always a new version, and the generator never writes an older version into a repository.

Decided in [How governed repositories follow new governance model versions](https://github.com/Habit130/agent-repo-governance/issues/25).
