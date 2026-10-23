# Drift is found at generator runs, not by the governance gate

Before writing anything, every generator run checks for three kinds of drift:

- edited fixed content;
- damaged markers;
- GitHub state that differs from the target.

A run at the installed version repairs what it finds. Version 1 adds no drift check to the governance gate: a check joins the gate only once measurement shows misses.

Decided in [How governed repositories follow new governance model versions](https://github.com/Habit130/agent-repo-governance/issues/25).
