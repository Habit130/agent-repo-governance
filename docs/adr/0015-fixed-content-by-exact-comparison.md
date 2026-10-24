# Fixed content is checked by exact comparison, not re-read

Fixed content is identical in every governed repository at one version. So a check compares it byte for byte with that version's templates. The templates themselves are reviewed once, when this repository delivers the version. Review effort in each repository goes to what differs there: confirmed values, repository-owned content and carried rules.

Decided in [How the generator turns a repository's state into its governance](https://github.com/Habit130/agent-repo-governance/issues/17).
