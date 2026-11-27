"""Builder and Reviewer rows from #229, rechecked at 00d80a0 for #316."""

from policy_text import Clause, PolicyRow, Section

START = Section("AGENTS.md", "## How to start")
LIMITS = Section("AGENTS.md", "## Hard limits")
VOICES = Section("AGENTS.md", "## Talking to habit and to other agents")
TIER_CHALLENGE = Section("AGENTS.md", "### The tier challenge")
ROUND_TWO = Section("AGENTS.md", "### From round 2")


def builder(heading):
    return Section("docs/agents/builder.md", "## " + heading)


def reviewer(heading):
    return Section("docs/agents/reviewer.md", "## " + heading)


def review(heading, level=2):
    return Section("docs/agents/review.md", "#" * level + " " + heading)


WHOLE = builder("Whole-spec delivery")
BUILD_STEPS = builder("Steps")
HANDOFF = builder("The Reviewer handoff")
BUILD_WAIT = builder("Syncing and waiting")
AFTER_MERGE = builder("After merge")
BUILD_ESCALATE = builder("Escalations")
RESULTS = builder("Results-comment tickets")
DIRECT = builder("A direct request")
REVIEW_START = reviewer("Start")
REVIEW_STEPS = reviewer("Steps")
REVIEW_OUTPUTS = reviewer("Outputs")
REVIEW_ESCALATE = reviewer("Escalations")
NO_HISTORY = review("Subagents with no conversation context")
MINIMUM = review("Minimum reviews")
BOTS = review("Review bots")
SECURITY = review("Security review")
EVIDENCE = review("Evidence comment")
REVIEW_TITLE = review("On the PR", 3)
TICKETS = Section("docs/agents/issue-tracker.md", "## Tickets")
EXAMPLES = Section("docs/agents/handoff.md", "## Examples")
PLAN_ESCALATE = Section("docs/agents/planner.md", "## Escalations")
MESSAGES = Section("docs/agents/handoff.md", "## Three kinds of message")

VENDOR_CONSTRAINT = "a vendor different from every Builder session that pushed to the PR, judged by the session marks"
COVERAGE = "For the set of tickets this PR covers, follow `builder.md`, Whole-spec delivery."
CLAIM = "**Claim** under `issue-tracker.md`, Tickets."
WAITS = "For PR waiting and the fallback, follow `AGENTS.md`, How to start."
ESCALATE = "For the escalation message, follow `handoff.md`, Three kinds of message."
NO_BOT_HIGH = "For an exhausted bot slot at high, follow `review.md`, Review bots, No bot left at high."
SECURITY_DECISION = "Use `review.md`, Security review, to decide whether the security review applies and run it when required."

ROWS = (
    # B60-67 B89-93 V23-25 V49-50 B230-233 I41-43 R29
    PolicyRow(
        "12",
        home=(Clause(WHOLE, "Self-verification, the evidence comment and every review cover that one PR, "
                            "against the spec and every ticket."),),
        pointers=(Clause(REVIEW_STEPS, COVERAGE), Clause(REVIEW_START, COVERAGE)),
        red=(Clause(REVIEW_STEPS, r"for a whole-spec PR, every ticket's"),
             Clause(REVIEW_START, r"for a whole-spec PR, the spec and every ticket it closes")),
        search=r"every ticket|each of its tickets|closes the spec",
        branches=(
            ("whole spec", (
                Clause(WHOLE, "Each subagent runs only its ticket's focused tests."),
                Clause(WHOLE, "On each committed integration head, run the union of all tickets' "
                              "Verification commands, each distinct command once."),
                Clause(WHOLE, "One PR** closes the spec and its tickets, with a `Closes` line for each."),
                Clause(WHOLE, "Their work merges onto one integration branch"),
                Clause(WHOLE, "and only that branch is pushed."),
            )),
            ("one ticket", (Clause(REVIEW_STEPS, "Verify the ticket on the pinned head."),)),
        ),
    ),
    # I41-43 B60 B78-81 I75-76 L37-38
    PolicyRow(
        "16",
        home=(
            Clause(TICKETS, "--add-assignee @me`. It is the Builder's first write, and it posts no comment."),
            Clause(TICKETS, "An assigned ticket is claimed."),
        ),
        pointers=(Clause(BUILD_STEPS, CLAIM), Clause(WHOLE, CLAIM)),
        red=(Clause(BUILD_STEPS, r"your first write"), Clause(WHOLE, r"Claim\*\* the spec and each")),
        search=r"first write|first.*write|claims the spec",
        branches=(
            ("single ticket", (Clause(TICKETS, "An assigned ticket is claimed."),)),
            ("whole spec", (Clause(TICKETS, "A Builder on a whole-spec delivery claims the spec and each of its tickets"),)),
            ("results comment", (Clause(BUILD_STEPS, "For a results-comment ticket, continue with Results-comment tickets above"),)),
        ),
    ),
    # A29-30 B11-13 B19-20 P15-18 B27-28
    PolicyRow(
        "19",
        home=(Clause(START, "No role: read-only; habit's change request makes it a Builder"),),
        pointers=(Clause(DIRECT, "For a direct change request with no ticket, apply `AGENTS.md`, How to start."),),
        red=(Clause(DIRECT, r"explicit request for a change.*makes the session a Builder"),),
        search=r"direct request|change request makes|explicit request for a change|outgrew one session",
        branches=(
            ("direct request", (
                Clause(DIRECT, "The direct request carries no difficulty"),
                Clause(DIRECT, "Open an issue quoting habit's request and every clarifying question and answer verbatim"),
                Clause(RESULTS, "Direct requests use the PR path."),
            )),
            ("scope exceeds one session", (Clause(
                DIRECT, "Work that needs more than one session, a spec or further decisions: hand habit a start "
                        "request for a Planner instead, and stop. A fresh Builder builds what the Planner produces.",
            ),)),
        ),
    ),
    # B208-210 B41-44
    PolicyRow(
        "20",
        home=(Clause(AFTER_MERGE, "When the dispatch plan gave a difficulty and the actual difficulty differed, "
                                  "say so in one sentence."),),
        pointers=(Clause(RESULTS, "Apply the completion-difficulty rule in After merge."),),
        red=(Clause(RESULTS, r"actual difficulty differed|say nothing otherwise"),),
        search=r"actual difficulty differed|say nothing otherwise|planned difficulty",
        branches=(
            ("same difficulty", (Clause(AFTER_MERGE, "Otherwise omit the difficulty."),)),
            ("direct request with no planned difficulty", (
                Clause(DIRECT, "The direct request carries no difficulty"),
                Clause(AFTER_MERGE, "When the dispatch plan gave a difficulty and the actual difficulty differed, "
                                    "say so in one sentence. Otherwise omit the difficulty."),
            )),
        ),
    ),
    # H14-19 B157-159 P159-161 V95-100 V32-35
    PolicyRow(
        "21",
        home=(Clause(MESSAGES, 'An escalation is a mid-session request: the full question and its options in the '
                               'terminal, and one "Waiting on habit: …" line on the PR or ticket.'),),
        pointers=(Clause(BUILD_ESCALATE, ESCALATE), Clause(REVIEW_ESCALATE, ESCALATE),
                  Clause(PLAN_ESCALATE, ESCALATE)),
        red=(Clause(BUILD_ESCALATE, r'full question|one "Waiting on habit'),
             Clause(REVIEW_ESCALATE, r'question and the options in the terminal'),
             Clause(PLAN_ESCALATE, r'question and the options in the terminal|one "Waiting on habit')),
        search=r"full question|question and the options|Waiting on habit|options in the terminal",
        branches=(
            ("Builder PR or ticket", (Clause(BUILD_ESCALATE, "Use the affected PR or ticket."),)),
            ("Planner issue", (Clause(PLAN_ESCALATE, "Use the issue."),)),
            ("Reviewer PR", (Clause(REVIEW_ESCALATE, "Use the PR."),)),
            ("missing Builder mark or matching vendor at high", (Clause(
                REVIEW_STEPS, "If any required Builder mark is missing or a vendor matches, stop before reviewing and escalate",
            ),)),
        ),
    ),
    # V12-19 B129-131 H122 H139 E65-67
    PolicyRow(
        "22",
        home=(Clause(REVIEW_START, "```text Role: Reviewer. PR: #<n>. Skills: code-review. Post on the PR: the Comment review, "
                                  "the Reviewer status and, when clear, the Merge summary. ```"),),
        pointers=(Clause(HANDOFF, 'For **"粘贴给 agent"**, use the start instruction in `reviewer.md`, Start.'),),
        red=(Clause(HANDOFF, r"Role: Reviewer\. PR|Post on the PR"),),
        search=r"Role: Reviewer\. PR|Post on the PR|start instruction the Builder|requests the Comment review",
        branches=(
            ("start", (Clause(REVIEW_START, "once the PR is open and its self-verification findings are dealt with"),)),
            ("outputs", (Clause(REVIEW_START, "Follow [Outputs](#outputs) for when to post each one."),)),
        ),
    ),
    # R121-122 B165-166 V51-52 V98-100 F56-57
    PolicyRow(
        "30",
        home=(Clause(BOTS, "No bot left at high.** Escalate to habit, who waits or waives the slot (Waivers). "
                           "The Reviewer's review proceeds either way."),),
        pointers=(Clause(REVIEW_ESCALATE, NO_BOT_HIGH),),
        red=(Clause(REVIEW_ESCALATE, r"at high the bot slot has no enabled bot left"),),
        search=r"no bot left at high|no enabled bot left|waits or waives",
        branches=(
            ("completed review or waiver", (Clause(
                REVIEW_STEPS, "At high, wait for its review on the head or habit's waiver",
            ),)),
            ("exhausted medium slot", (Clause(
                BOTS, "No bot left at medium.** After reading the bot policy, check whether every enabled bot is "
                      "unavailable or the list started empty. A Reviewer session substitutes only when one of these conditions holds.",
            ),)),
        ),
    ),
    # R262-266 R32 V57-59 R332-337 M55-63 R353-358 F83-85
    PolicyRow(
        "32",
        home=(Clause(SECURITY, "At high, when the change involves authentication, privacy or secret handling, "
                               "the Reviewer runs a security-review subagent"),),
        pointers=(Clause(REVIEW_STEPS, SECURITY_DECISION), Clause(REVIEW_TITLE, "At high, use `review.md`, Security review, to decide whether the security review applies.")),
        red=(Clause(REVIEW_STEPS, r"authentication, privacy or secret handling"),
             Clause(REVIEW_TITLE, r"judge whether the change involves authentication, privacy or secret handling")),
        search=r"security applies|security review applies|authentication, privacy",
        branches=(
            ("applies", (Clause(REVIEW_TITLE, "With `yes`, include `security=clear` or `security=waived` on the second line. "
                                            "A waiver requires habit's exact-head comment for `security`."),)),
            ("does not apply", (Clause(REVIEW_TITLE, "With `no`, list `security=clear` only if a security review ran, "
                                                   "otherwise omit the row."),)),
            ("low and medium", (Clause(MINIMUM, "| Security review | — | — | See [Security review](#security-review) |"),)),
        ),
    ),
    # R138-144 B127-128 R257 R335-337
    PolicyRow(
        "33",
        home=(Clause(review("The Codex review bot", 3),
                     "offered in the Builder's Reviewer handoff only on a PR that is high for authentication, privacy or secret handling."),),
        pointers=(Clause(HANDOFF, "For the optional extra, follow `review.md`, The Codex review bot, "
                                  "and record the request and output under Evidence comment."),),
        red=(Clause(HANDOFF, r"high for authentication|offer habit the optional"),),
        search=r"optional.*security|security review request|offer habit|high for authentication",
        branches=(
            ("requested", (Clause(EVIDENCE, "whether habit requested the optional Codex security review and what it posted"),)),
            ("declined", (Clause(review("The Codex review bot", 3), "habit may leave the request with no waiver."),)),
            ("no output", (Clause(review("The Codex review bot", 3), "no posted finding is not a completed clean review."),)),
        ),
    ),
    # R276-278 B107-110 R33 R37-38 R115-117 R199-206 H29-33 R399-401
    PolicyRow(
        "34",
        home=(Clause(review("Merge summary"), "after the last clear review"),),
        pointers=(Clause(BUILD_STEPS, "Use the writer selected in `review.md`, Merge summary."),
                  Clause(MINIMUM, "For the summary writer, see [Merge summary](#merge-summary)."),
                  Clause(review("Waivers"), "The writer selected in Merge summary runs the checks,")),
        red=(Clause(BUILD_STEPS, r"the Builder writes (?:it|the Merge summary)|write the high-risk report"),),
        search=r"summary by|writes (it|the (Merge summary|high-risk report))|summary to the Builder|summary by the Builder",
        branches=(
            ("low or medium without a Reviewer", (Clause(review("Merge summary"), "Written by the Builder at low and medium"),)),
            ("medium with Reviewer", (Clause(review("Merge summary"), "when a Reviewer ran at medium, that Reviewer writes it."),)),
            ("high with Reviewer", (Clause(review("Merge summary"), "At high the Reviewer writes the high-risk report"),)),
            ("high Reviewer waived", (Clause(review("Merge summary"), "the Builder does when habit waived the Reviewer session"),)),
        ),
    ),
    # R11-15 A136 A153-154 A164-166 V41-44 B64-65 B87-93 G13-14 M68-70
    PolicyRow(
        "36",
        home=(
            Clause(review("The tier"), "`Risk: <tier> — <reason>` line is the only record of the effective tier."),
            Clause(TIER_CHALLENGE, "Under-declaration is Important: name the warranted tier and why."),
        ),
        pointers=(Clause(REVIEW_STEPS, "Apply `AGENTS.md`, The tier challenge, and follow `review.md`, The tier, for the effective tier."),),
        red=(Clause(REVIEW_STEPS, r"yours is higher than the `Risk:` line"),),
        search=r"Risk: <|effective tier|declared tier below",
        branches=(
            ("raised to high", (Clause(REVIEW_STEPS, "If the tier rises to high, post the tier finding, then repeat step 1"),)),
            ("raised tier", (Clause(review("The tier"), "the Builder updates the line. Reviews run under the lower tier "
                                                       "don't count toward the new one."),)),
            ("lower tier", (Clause(review("The tier"), "Only habit lowers a tier, in a PR comment. The Builder records it by "
                                                      "updating the line, its reason linking habit's comment."),)),
        ),
    ),
    # R231-238 A168-171 B94-101 B124-126 B138-139 V37-38 V89-91 R244-248 R320-321
    PolicyRow(
        "41",
        home=(Clause(review("Rounds"), "a sync included"),),
        pointers=(Clause(BUILD_WAIT, "On a new head follow `review.md`, Rounds, and `AGENTS.md`, From round 2."),),
        red=(Clause(BUILD_WAIT, r"The new head is reviewed again"),),
        search=r"any new head|on every new head|new head.*review",
        branches=(
            ("new head", (Clause(review("Rounds"), "First the Builder reruns self-verification (`builder.md`, step 6) "
                                                   "on the committed head before pushing, deals with its findings, "
                                                   "then updates the evidence comment on the pushed head."),)),
            ("bot review decision", (Clause(
                review("Rounds"), "Any new head, a sync included, gets its applicable bot-slot review under "
                "[Review bots](#review-bots)",
            ),)),
            ("high or medium Reviewer", (Clause(review("Rounds"), "at high or when a Reviewer ran at medium, a Reviewer pass over the change."),)),
            ("round 2", (Clause(ROUND_TWO, "Review only changes since the last reviewed head and open findings."),)),
            ("three rounds", (Clause(review("Rounds"), "After three rounds with an Important finding still open, the Builder escalates"),)),
        ),
    ),
    # R90-93 B87-93 R262-265 A29 B61-63
    PolicyRow(
        "42",
        home=(Clause(NO_HISTORY, "Self-verification and the security review each run in a subagent that receives none of "
                                "the starting session's conversation."),),
        pointers=(Clause(BUILD_STEPS, "After it passes, start a subagent under `review.md`, Subagents with no conversation context."),
                  Clause(SECURITY, "Start it under Subagents with no conversation context.")),
        red=(Clause(BUILD_STEPS, r"start a subagent with no conversation context"),
             Clause(SECURITY, r"subagent with no conversation context")),
        search=r"no conversation context|none of the|self-verification subagent",
        branches=(
            ("self-verification", (Clause(BUILD_STEPS, "run `code-review` on the committed diff against its merge-base"),)),
            ("security", (Clause(SECURITY, "Its task names the diff against the merge-base, the ticket, and these checks"),)),
            ("implementation", (Clause(WHOLE, "subagents build the tickets, each in its own worktree"),)),
        ),
    ),
    # A71-72 A94 V5-8 V23-26 V83-85
    PolicyRow(
        "47",
        home=(Clause(LIMITS, "Separate context. No pushes or PR, ticket or label edits."),
              Clause(VOICES, "Reviewer never commits Builder to changes.")),
        pointers=(Clause(REVIEW_OUTPUTS, "For independence and write limits, follow `AGENTS.md`, Hard limits and Voices."),),
        red=(Clause(REVIEW_OUTPUTS, r"never commits the Builder to changes|the Reviewer never pushes"),),
        search=r"separate context|didn.t write|conversation stays unread",
        branches=(
            ("context", (Clause(REVIEW_START, "Leave the Builder's conversation unread and base the review on what GitHub holds."),)),
            ("Comment review", (Clause(REVIEW_OUTPUTS, "**One Comment review**"),)),
            ("commit status", (Clause(REVIEW_OUTPUTS, "**A `Reviewer` commit status**"),)),
            ("handoff", (Clause(REVIEW_OUTPUTS, "before publishing the Merge summary (the high-risk report at high)."),)),
        ),
    ),
    # A39-45 A49-53 B150-153 B188-192 B203-207 V62-63 R296-299 R413-416 H143 H146-149 E68-71
    PolicyRow(
        "56",
        home=(
            Clause(START, "Waiting on a PR is unverified: stop and say what you wait for."),
            Clause(START, "The generator never runs there. Waiting is unverified: stop and say what you wait for."),
            Clause(START, "use the installed `wait-on-pr` skill when available; if unavailable, poll within that limit "
                          "or stop and say what the session is waiting for."),
        ),
        pointers=(Clause(REVIEW_STEPS, WAITS), Clause(BUILD_WAIT, WAITS)),
        red=(Clause(REVIEW_STEPS, r"Wait in your harness when it can wait|Otherwise stop and say what you wait for"),
             Clause(BUILD_WAIT, r"other waits the harness cannot perform")),
        search=r"cannot wait|can't wait|stop and say",
        branches=(
            ("high in-session return", (Clause(AFTER_MERGE, "At high, when its permitted in-session wait returns, the original "
                                                          "Builder must read the intended repository and PR number on GitHub."),)),
            ("high manual return", (Clause(AFTER_MERGE, "If that wait is unsupported or interrupted, or the GitHub read is inconclusive, "
                                                       "say what evidence is pending, keep your worktree and stop. To resume, habit may "
                                                       "say “继续” (continue) in the original Builder chat. On return, repeat the same "
                                                       "GitHub checks, including the open-PR branch."),)),
            ("medium unavailable", (Clause(AFTER_MERGE, "At medium, a Builder that cannot wait leaves its worktree, and nobody nudges it."),)),
            ("wrong PR or no merge", (Clause(AFTER_MERGE, "For a PR closed without merge, an unrelated event or a mismatched identity, "
                                                         "report the discrepancy and stop."),)),
            ("merged", (Clause(AFTER_MERGE, "If GitHub shows a merge, confirm that habit merged it into the intended default branch, "
                                           "the full PR head SHA at merge matches the reviewed head pinned for habit, and GitHub "
                                           "identifies the resulting squash commit. Only then begin verification"),)),
        ),
    ),
    # V17-20 V95-100 B155-159 B175
    PolicyRow(
        "69",
        home=(Clause(REVIEW_START, "A Reviewer that cannot make these writes, under a read-only instruction or a denied "
                                  "permission, stops and tells habit instead of posting a summary alone."),),
        pointers=(Clause(REVIEW_ESCALATE, "For permission problems, follow Start and the escalation message above."),),
        red=(Clause(REVIEW_ESCALATE, r"a permission is denied"),),
        search=r"permission is denied|denied permission|cannot make these writes",
        branches=(
            ("other work blocked", (Clause(REVIEW_START, "If a denied permission blocks other Reviewer work, "
                                                       "stop the affected work and follow Escalations."),)),
            ("Builder permission denied", (Clause(BUILD_ESCALATE, "**A permission is denied.**"),)),
            ("Reviewer outputs permitted", (Clause(REVIEW_START, "Follow [Outputs](#outputs) for when to post each one."),)),
        ),
    ),
    # v6 recheck: builder.md 118–119, review.md 31 and 250, reviewer.md 31;
    # docs/build/releasing.md 67 and 88 agree and are historical.
    PolicyRow(
        "82",
        home=(Clause(MINIMUM, VENDOR_CONSTRAINT),),
        pointers=(Clause(HANDOFF, "At high state the vendor constraint from `review.md`, Minimum reviews."),
                  Clause(REVIEW_STEPS, "At high apply the vendor constraint from `review.md`, Minimum reviews."),
                  Clause(EXAMPLES, "The vendor choice follows `review.md`, Minimum reviews.")),
        red=(Clause(HANDOFF, r"vendor different from every Builder mark on the PR"),
             Clause(EXAMPLES, r"Reviewer 的 vendor 必须不同于所有 Builder session")),
        search=r"every Builder mark|every Builder session|Builder mark on the PR",
        branches=(
            ("medium", (Clause(REVIEW_STEPS, "At medium, record your own mark without comparing vendors or requiring Builder marks."),)),
            ("high missing mark or same vendor", (Clause(REVIEW_STEPS, "If any required Builder mark is missing or a vendor matches, stop before reviewing"),)),
            ("high no different vendor", (Clause(REVIEW_STEPS, "if no different vendor is available, see `review.md`, Waivers."),)),
        ),
    ),
)
