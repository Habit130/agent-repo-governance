# Third-party skills that governance relies on are copied here and reach the machine only through the install

This repository keeps byte-identical copies of the third-party skills that governance relies on, with their upstream commits. The one allowed change is adding a missing Codex user-only key. The install takes those skills over from the `skills` CLI, so `npx skills update` no longer manages them.

A skill update therefore reaches the machine together with the governance model version that adapts to it, never before. The cost is a reviewed PR for each update.

Decided in [How the machine skill set is installed and updated](https://github.com/Habit130/agent-repo-governance/issues/26).
