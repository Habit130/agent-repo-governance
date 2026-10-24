# habit merges only by the pinned terminal command

In a governed repository, the one governed merge path is `ghm pr merge <n> --admin --squash --match-head-commit <sha>`, run through habit's account alias, since plain `gh` on the machine acts as the agent account. The command fails if anything was pushed after the Merge summary named its head.

The browser's bypass merge isn't a governed path. In a live test it followed the newest head. The gate doesn't check reviews, so a browser merge could land a head that no Reviewer saw.

Decided in [Which rules are enforced deterministically](https://github.com/Habit130/agent-repo-governance/issues/15).
