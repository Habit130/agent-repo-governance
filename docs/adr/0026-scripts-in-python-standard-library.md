# Every script uses Python's standard library at the 3.9 level, plus git and gh

Every script this repository ships, from the generator and the install to the owner script and the governance gate, is written against Python 3's standard library as of 3.9, plus `git` and `gh`. That is the Python the macOS Command Line Tools put at `/usr/bin/python3`, which Homebrew and git already need. So the scripts need no packages, virtual environments or third-party actions.

- **Shell** is fragile for logic, so it serves only as entries, compatible with macOS's `/bin/bash` 3.2.
- **Node** is ruled out, because a fresh Mac doesn't have it.

The choice is hard to reverse once the scripts exist, and a reader may expect shell for a GitHub tool.

Decided in [Spec: generator version 1](https://github.com/Habit130/agent-repo-governance/issues/44), which habit agreed to record when it was broken into tickets.
