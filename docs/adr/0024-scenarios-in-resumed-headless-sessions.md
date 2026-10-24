# The generator's judgment is checked by planted cases in resumed headless sessions

A scenario checks the generator's judgment in three steps:

1. It runs the generator headless up to its one confirmation.
2. It resumes the same session with the fixture's recorded answer.
3. Over three runs, it asserts on planted cases, never on wording.

Two ready-made routes were rejected:

- `claude plugin eval` loads no project configuration, has no `gh` identity and can't answer the confirmation.
- The Agent SDK needs an API key.

Decided in [How the generator and the install are verified before a version ships](https://github.com/Habit130/agent-repo-governance/issues/40).
