# Changes accumulate in one draft version, and habit decides when to release

The template store holds at most one draft version: the highest, marked by having no change note. PRs change it freely, and released versions stay frozen. A separate release delivery adds the note. Merging a fix, releasing a version, installing on the machine and upgrading a repository are four separate decisions, and none triggers the next.

A reader would expect each fix to ship as its own version, as versions 1 and 2 did. habit chose to batch: the machine is updated once a coherent set has accumulated, with no fixed count, and an urgent bug or a severe usability problem may release earlier.

- Ordinary rendering and comparison select released versions only. A draft is rendered only by a test or a live check that asks for it explicitly.
- The install may copy a draft's files without making it the installed version.

Decided in [Decision: decouple review providers and batch governance updates](https://github.com/Habit130/agent-repo-governance/issues/127) and [Enable unpublished governance-model changes across PRs](https://github.com/Habit130/agent-repo-governance/issues/128).
