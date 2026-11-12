# Review requirements name bot slots, and the record lists the enabled review bots

From version 3, a tier requires review bots by slot: none at low, `bot-1` at medium, and `bot-1` and `bot-2`, filled by two different bots, at high. Which bots fill the slots is a confirmed value in the governance record: the enabled review bots, in habit's order of preference. Everything specific to one bot sits in one subsection of `review.md` and one reader in Merge watch.

Versions 1 and 2 named Bugbot and the Codex review bot in the requirements themselves, so one bot's retirement needed a new version in every repository. Now choosing among the supported bots changes one confirmed value. Supporting a new bot still takes a version.

- A PR is judged by the list on the default branch before it merges, so a PR that changes the list can't lower its own requirements.
- Two results from one bot fill one slot.
- A general plugin or configuration framework was rejected: only the review chain's changeable facts moved into the record.
- Version 3 supports the Codex review bot and Copilot code review, and drops Bugbot. Low takes no review bot, by habit's decision.

Decided in [Decision: decouple review providers and batch governance updates](https://github.com/Habit130/agent-repo-governance/issues/127) and [Version 3: provider-independent review requirements, exact-head waivers, Copilot in and Bugbot out](https://github.com/Habit130/agent-repo-governance/issues/148).
