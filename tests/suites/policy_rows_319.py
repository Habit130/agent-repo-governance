"""Planner rows 11, 14, 15, 45 and 63 from #229, rechecked at 00d80a0."""

from policy_text import Clause, PolicyRow, Section

START = Section("AGENTS.md", "## How to start")
DELIVERY = Section("docs/agents/planner.md", "## Delivery shape")
WHOLE_SPEC = Section("docs/agents/builder.md", "## Whole-spec delivery")

SPECS = Section("docs/agents/planner.md", "## Specs")
CLOSING_SPEC = Section("docs/agents/builder.md", "## Closing a spec")
RESULTS = Section("docs/agents/builder.md", "## Results-comment tickets")

TICKETS = Section("docs/agents/planner.md", "## Tickets")
TRACKER_TICKETS = Section("docs/agents/issue-tracker.md", "## Tickets")
BUILDER_ESCALATIONS = Section("docs/agents/builder.md", "## Escalations")

RISK_TIERS = Section("AGENTS.md", "### Risk tiers")
MINIMUM_REVIEWS = Section("docs/agents/review.md", "## Minimum reviews")
AFTER_MERGE = Section("docs/agents/builder.md", "## After merge")

ENTRY_POINTS = Section("docs/agents/planner.md", "## Entry points")
MISSES = Section("docs/agents/planner.md", "## Misses")
RUNNING_RETRO = Section("docs/agents/planner.md", "## Running retro")
MISS_RECORDS = Section("docs/agents/issue-tracker.md", "## Miss records")

ROWS = (
    PolicyRow(
        "11",
        home=(
            Clause(START, "Start instructions name role, target and only session-called skills in `Skills:`"),
            Clause(START, "For a manual invocation, line one is the bare skill name and any arguments. Put the complete role instruction on the next line."),
        ),
        pointers=(
            Clause(DELIVERY, "Use `AGENTS.md`, How to start, for the canonical whole-spec start instruction and the tickets' session-called skills."),
            Clause(WHOLE_SPEC, "Use the canonical whole-spec start instruction in `AGENTS.md`, How to start."),
        ),
        red=(
            Clause(DELIVERY, r"Role: Builder\. Spec|habit invokes: implement-spec"),
            Clause(WHOLE_SPEC, r"Role: Builder\. Spec|habit invokes: implement-spec"),
        ),
        search=r"Role: Builder\. Spec|habit invokes: implement-spec",
        branches=(
            ("approved whole spec", (Clause(
                START,
                "Example for an approved whole-spec delivery: ```text implement-spec Role: Builder. Spec: #322. Skills: tdd, research, writing-for-agents. ```",
            ),)),
            ("ordinary ticket", (Clause(START, "```text Role: Builder. Ticket: #<n>. Skills: tdd. ```"),)),
        ),
    ),
    PolicyRow(
        "14",
        home=(Clause(CLOSING_SPEC, "There is no spec-level acceptance."),),
        pointers=(
            Clause(SPECS, "For spec closure, see `builder.md`, Closing a spec."),
            Clause(RESULTS, "Then close the ticket as completed and see Closing a spec for its parent."),
        ),
        red=(
            Clause(SPECS, r"close any spec still open|all its tickets are done"),
            Clause(RESULTS, r"if it is its spec's last open sub-issue, also close the spec"),
        ),
        search=r"last open sub-issue|all its tickets are done|closes the spec|closes their spec",
        branches=(
            ("last results-comment ticket", (Clause(
                CLOSING_SPEC, "After closing a results-comment ticket, close its spec if that ticket was its last open sub-issue.",
            ),)),
            ("whole-spec PR", (
                Clause(CLOSING_SPEC, "A whole-spec PR closes the spec and its tickets (Whole-spec delivery)."),
                Clause(WHOLE_SPEC, "`Closes` line for each."),
            )),
            ("last individual PR", (Clause(
                CLOSING_SPEC, "For an individual ticket PR, add `Closes #<spec>` only if the ticket is its spec's last open sub-issue.",
            ),)),
            ("spec still open after all tickets", (Clause(
                CLOSING_SPEC, "If a spec remains open once all its tickets are done, the Planner closes it (`issue-tracker.md`, Sub-issues and blocking).",
            ),)),
        ),
    ),
    PolicyRow(
        "15",
        home=(Clause(BUILDER_ESCALATIONS, "A published ticket is frozen."),),
        pointers=(
            Clause(TICKETS, "For changes to a published ticket, see `builder.md`, Escalations, The ticket must change."),
            Clause(TRACKER_TICKETS, "For changes to a published ticket, see `builder.md`, Escalations, The ticket must change."),
        ),
        red=(
            Clause(TICKETS, r"once published it is frozen|habit agrees, and the ticket records both"),
            Clause(TRACKER_TICKETS, r"a published ticket is frozen"),
        ),
        search=r"frozen|recorded agreement|agreement is recorded",
        branches=(
            ("proposal enters the ticket", (Clause(
                BUILDER_ESCALATIONS, "Propose the change on the ticket",
            ),)),
            ("edit after recorded agreement", (Clause(
                BUILDER_ESCALATIONS, "edit it only after habit's agreement is recorded there.",
            ),)),
        ),
    ),
    PolicyRow(
        "45",
        home=(
            Clause(RISK_TIERS, "One-way doors (data migrations, destructive operations, releases, publishing)"),
            Clause(MINIMUM_REVIEWS, "**High adds:** give before-and-after evidence in plain words."),
            Clause(MINIMUM_REVIEWS, "Keep only the high part in the PR."),
        ),
        pointers=(Clause(
            DELIVERY,
            "See `AGENTS.md`, Risk tiers, for what counts as a one-way door, `review.md`, Minimum reviews, "
            "for high PR scope and rehearsal, and `builder.md`, After merge, for approval before execution.",
        ),),
        red=(Clause(DELIVERY, r"one-way door:|data migration|a high PR holds only its high part"),),
        search=r"one-way door|only the high part|only its high|data migration",
        branches=(
            ("eligible foreseen-high whole spec", (Clause(
                DELIVERY,
                "Foreseen-high tickets join it only when every ticket is high for the same reason and none holds a one-way door.",
            ),)),
            ("a one-way door needs its own PR", (
                Clause(DELIVERY, "A ticket with a one-way door always gets its own PR."),
                Clause(MINIMUM_REVIEWS, "Rehearse each one-way door on a copy, attach the result and perform its recovery once."),
                Clause(
                    AFTER_MERGE,
                    "At high, after product smoke passes, ask habit's go-ahead for each one-way-door step, one at a time, "
                    "saying what it does and whether it can be undone.",
                ),
            )),
        ),
    ),
    PolicyRow(
        "63",
        home=(
            Clause(
                MISSES,
                "When triage traces a bug to a merged PR, open a miss record for that PR "
                "(`issue-tracker.md`), linking the bug's own triaged issue.",
            ),
            Clause(MISSES, "Tell habit at once, with a start request for a Planner session"),
            Clause(MISSES, "```text retro #<miss> Role: Planner. Issue: #<miss>. ```"),
        ),
        pointers=(Clause(
            ENTRY_POINTS,
            "For a bug linked to a merged PR, follow Misses below. For closing its miss record, "
            "see `issue-tracker.md`, Miss records.",
        ),),
        red=(Clause(ENTRY_POINTS, r"triage traces|bug traced|traced.*merged PR|open a miss record"),),
        search=r"triage traces|bug traced|traced.*merged PR",
        branches=(
            ("bug issue stays in triage", (
                Clause(ENTRY_POINTS, "**A bug** arrives as an issue, through `triage`, or as a direct request to a Builder"),
                Clause(MISS_RECORDS, "A bug keeps its own issue, which goes through triage as usual and which the record links."),
            )),
            ("miss record closes after retro", (
                Clause(MISS_RECORDS, "**Close it** only after its `retro`, quoting habit's decision"),
                Clause(RUNNING_RETRO, "4. Close the record, quoting habit's decision."),
            )),
        ),
    ),
)
