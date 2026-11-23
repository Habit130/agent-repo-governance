# Retros

This repository pilots class retros beside `planner.md`, Running retro, under #226's
decisions. A miss record still gets its own `retro`. This file adds what every `retro`
here applies, and how a class retro runs.

## Every retro here

On top of `planner.md`, Running retro, for a miss record and a class retro alike:

- **Level.** Propose each lesson at the highest level that works. First structure, which
  removes the cause, such as stating a condition once or generating cases from one
  source. Then a mechanical check: the gate, Merge watch, CI or a test. Text comes last
  and says why neither higher level works.
- **Proof.** A candidate that adds a check names the past instance the check must fail
  on, and its ticket asks the delivery to show that failure. For an instance in a frozen
  version, the proof runs outside the committed suite.
- **Recurrence.** A bug class that recurs after its fix merged has a failed fix: propose
  the next level up.
- **Deletion.** Propose deleting text whose mistake a check now prevents.
- **Cost.** Each candidate states the CI time, files and fixtures it adds, the policy text
  it adds or removes, and whether it needs a version release. Text added to this
  repository's `AGENTS.md` section must fit that section's budget test.
- **Cap.** Recommend at most three new tickets per retro, and list the other candidates as
  not recommended, each with its reason.

A retro reports events, never rates.

## A class retro

A class retro looks for bug classes that repeat across PRs, before one escapes. During
the pilot, habit starts one with `retro #226` in a Planner session: after each governance
model release merges, from the cutting PR's after-merge report, and whenever habit
chooses.

1. **Window.** Take every PR merged after the last one the previous class retro covered.
   Done when the window's first and last PR are named.
2. **Occurrences.** Read each PR's inline review comments, Comment review bodies and bot
   findings, with the Builder's answers. An occurrence is a confirmed Important-level
   finding: a Reviewer's Important, a review bot's P0 or P1 or its stated equivalent, a
   security review's HIGH or MEDIUM, or an escape. A finding rejected with evidence is
   none, and a Nit only supports a class that qualifies. Done when every PR in the window
   is listed with its occurrences, or with none.
3. **Classes.** Give each occurrence one primary bug class: the class whose fix would
   have caught it. A class qualifies once it has occurrences in two different PRs,
   counting earlier class retros' baselines. Done when every occurrence has its class.
4. **Enforcement.** For each qualifying class, name the rule text that addresses it and
   what checks it today: the gate, Merge watch, CI, a policy-text test, or review judgment
   only. Read it from the code and tests at the window's last commit, and keep no standing
   copy. Done when every qualifying class has its row.
5. **Evidence binding.** For each PR in the window, check that its final evidence comment
   names the PR's final head by full SHA. A merged PR without one is a process miss: open
   its miss record (`issue-tracker.md`, Miss records). Done when every PR in the window is
   checked.
6. **Recurrence.** For each class in the previous class retro's baseline, compare its last
   occurrence with the fix in force. Done when each has a status: held, recurred or too
   early.
7. **Report.** Post one comment on #226 with the window, the occurrences by class, the
   enforcement view, the evidence-binding result, each class's recurrence status, the
   candidates under Every retro here, and a new baseline giving each class's last
   occurrence, the fix in force and what the next class retro checks. Then give habit the
   candidates in Chinese, by severity. Follow step 3 of `planner.md`, Running retro, for
   habit's picks. Record habit's decision on #226 and leave it open.

## The pilot's end

At the end of the second class retro, recommend to habit whether to promote class retros
into the governance model, judged by three things: whether classes recurred after their
fixes, the net CI time and policy text the picks added, and habit's judgement of the time
the retros took. A promotion writes class retros into `planner.md` in the next draft,
where a governed repository without releases starts one only when habit chooses.
