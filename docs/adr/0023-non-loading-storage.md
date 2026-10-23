# Fixtures, released templates and skill copies are stored in a form no harness or review bot loads

Stored as literal files, they would cause three problems:

- They would load as instructions while a session worked on them.
- Nested Bugbot rule files would review changes under the fixture's own rules.
- Every nested `AGENTS.md` would floor its PR at medium as a sensitive path.

So they are stored in a form nothing loads. When used, they are materialized into a temporary directory or the target repository.

Decided in [How the generator and the install are verified before a version ships](https://github.com/Habit130/agent-repo-governance/issues/40), extending [How the machine skill set is installed and updated](https://github.com/Habit130/agent-repo-governance/issues/26).
