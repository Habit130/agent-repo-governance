# Review minimums are checked after merge, in Merge watch, before they can bind in the gate

Merge watch checks each merged head for the reviews its declared tier requires. It records any missing review as a process miss, unless habit accepted a substitute or one bot fewer, and it blocks nothing.

A review-minimum check joins the governance gate only after a real process miss, by habit's decision and in a new version. Without a standing check, the rule that the gate gains such checks would fire only on escapes.

Decided in [How governance measures itself and turns misses into checks or instructions](https://github.com/Habit130/agent-repo-governance/issues/36).
