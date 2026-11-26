"""Review rows from #229, rechecked on the v6 draft at 00d80a0 for #317."""

from policy_text import Clause, PolicyRow, Section


class AuditSection(Section):
    """Select one audit contract or function, bounded by the next named block."""

    def read(self, text):
        start, end = self.heading
        _, delimiter, remainder = text.partition("\n" + start + "\n")
        if not delimiter or ("\n" + start + "\n") in remainder:
            raise AssertionError("%s must contain one start for %r" % (self.path, start))
        body, delimiter, _ = remainder.partition("\n" + end)
        if not delimiter:
            raise AssertionError("%s has no end %r for %r" % (self.path, end, start))
        return start + "\n" + body


AGENTS = "AGENTS.md"
REVIEW = "docs/agents/review.md"
WATCH = ".github/governance/merge_watch.py"
TIER = Section(REVIEW, "## The tier")
BOTS = Section(REVIEW, "## Review bots")
CODEX = Section(REVIEW, "### The Codex review bot")
ROUNDS = Section(REVIEW, "## Rounds")
BUILD_STEPS = Section("docs/agents/builder.md", "## Steps")
REVIEWER_HANDOFF = Section("docs/agents/builder.md", "## The Reviewer handoff")
MINIMUM = Section(REVIEW, "## Minimum reviews")
REVIEW_STATE = Section(REVIEW, "## Review state")
ON_PR = Section(REVIEW, "### On the PR")
HANDOFF = Section(REVIEW, "### The merge handoff")
DISPATCH = Section("docs/agents/planner.md", "## Tickets")
ANSWERING = Section(REVIEW, "## Answering findings")
EXCEPTIONS = Section(REVIEW, "## Exceptions")
FINDINGS = Section(AGENTS, "### Findings")
CHECKS_FIRST = Section(REVIEW, "### Checks first")
REVIEWER_OUTPUTS = Section("docs/agents/reviewer.md", "## Outputs")
WAIVERS = Section(REVIEW, "## Waivers")
HARD_LIMITS = Section(AGENTS, "## Hard limits")

GATE_STEPS = AuditSection(".github/governance/gate.py", (
    "3. Pure revert: a `Reverts:` line names a full commit SHA on the default branch. The PR is",
    "Every rule runs and reports.",
))
WATCH_PARSER = AuditSection(WATCH, (
    "def parse_reviews(line, tier, *, require_minimum=True):", "def _summary_lines(",
))
WATCH_REVIEW_MISSES = AuditSection(WATCH, (
    "  - **the Merge summary**: the historical agent account's newest comment titled",
    "  - **a bot slot**",
))

ROWS = (
    PolicyRow(
        "04",
        home=(Clause(GATE_STEPS, "PR's changed paths match, deletions and both sides of a rename included."),),
        pointers=(Clause(
            TIER, "Apply the floors and confirmed-revert rules in the "
            "[gate contract](../../.github/governance/gate.py), steps 3–4.",
        ),),
        red=(Clause(TIER, r"highest floor|either rename|both sides|confirms takes the low path"),),
        search=r"highest floor|either rename|both sides",
        branches=(
            ("confirmed revert despite a floor", (Clause(
                GATE_STEPS, "3. Pure revert: a `Reverts:` line names a full commit SHA on the default branch. "
                "The PR is a pure revert, passing at any tier with step 4 skipped, only when that commit's parent "
                "holds the record as a regular file, its revert recomputed on the PR's merge-base equals "
                "the head's tree, and GitHub shows a PR merged into the default branch whose squash commit it is.",
            ),)),
            ("unconfirmed including unreadable provenance", (
                Clause(
                    GATE_STEPS, "a revert unconfirmed otherwise, GitHub unreadable included, adds no failure "
                    "line of its own, and the floors judge it.",
                ),
                Clause(
                    GATE_STEPS, "4. Floors: the declared tier reaches the highest floor among the sensitive paths",
                ),
            )),
            ("malformed declaration", (Clause(
                GATE_STEPS, "`Reverts:` line that is malformed, doubled or names no commit on the default branch fails this rule",
            ),)),
            ("owner lowers the tier", (Clause(
                TIER, "**Lowering.** Only habit lowers a tier, in a PR comment. The Builder records it by "
                "updating the line, its reason linking habit's comment.",
            ),)),
        ),
    ),
    PolicyRow(
        "07",
        home=(Clause(BOTS, "Only habit posts a manual request."),),
        # The repository-owned live-check pointer belongs to the v6 Upgrade.
        pointers=(
            Clause(ROUNDS, "gets its applicable bot-slot review under [Review bots](#review-bots)"),
            Clause(BUILD_STEPS, "fill the bot slot under `review.md`, Review bots, on every head that needs one"),
            Clause(REVIEWER_HANDOFF, "Any bot request needed on this head under `review.md`, Review bots."),
        ),
        red=(
            Clause(BOTS, r"(?i)a bot starts only on habit.s request"),
            Clause(ROUNDS, r"through habit.s requests"),
            Clause(BUILD_STEPS, r"through habit.s requests"),
            Clause(REVIEWER_HANDOFF, r"Give habit fresh ones after each repair push"),
        ),
        search=r"bot starts only|automatic Codex review|request comment|requests a review",
        branches=(
            ("manual request and repair push", (
                Clause(
                    BOTS, "When a request is needed, including after a repair push, the Builder hands habit "
                    "the request from the provider's subsection below.",
                ),
                Clause(BOTS, "Only a request comment writes a bot's trigger"),
                Clause(CODEX, '`ghm pr comment <n> --body "@codex review"`, which habit runs.'),
            )),
            ("automatic completion already on this head", (
                Clause(
                    BOTS, "When Codex takes the slot, first look for a completed review on the head under "
                    "[The Codex review bot](#the-codex-review-bot). An automatic completion fills the slot "
                    "without a manual request.",
                ),
                Clause(
                    CODEX, "its comment's `codex-review-state:v1` marker, whose `code_review.commit_sha` is the head "
                    "and whose `code_review.status` is `completed`.",
                ),
            )),
            ("old or incomplete review", (
                Clause(REVIEW_STATE, "A result for an older head never counts for this one, and only a "
                       "completed review is ever written as clear."),
                Clause(BOTS, "A completed review with findings is completed."),
            )),
            ("unavailable provider", (
                Clause(BOTS, "When it is unavailable, the next enabled bot takes the slot"),
                Clause(BOTS, "no completed review on the head within the bot's wait after one more request"),
            )),
        ),
    ),
    PolicyRow(
        "08",
        home=(Clause(
            WATCH_PARSER, "V5 also reads individual declarations when a required kind is omitted.",
        ),),
        pointers=(Clause(
            ON_PR, "Include every required kind and each listed bot slot's provider. For the "
            "audit of an incomplete line, see [`parse_reviews`](../../.github/governance/merge_watch.py).",
        ),),
        red=(Clause(ON_PR, r"(?i)a line that leaves out.*doesn.t read"),),
        search=r"doesn't read|reads individual|omitted required",
        branches=(
            ("complete ordered declarations", (Clause(
                WATCH_PARSER, "It reads when every item is `<kind>=<state>`, a bot slot's state with its provider in "
                "parentheses, the kinds in their order and none twice, and it lists every kind the tier requires.",
            ),)),
            ("v5 onward, missing required kind with surviving declarations", (Clause(
                WATCH_REVIEW_MISSES, "From v5, a missing required declaration yields `merge-summary`; "
                "see `parse_reviews` for incomplete lines and `_declared_missing` for the declarations they still carry",
            ),)),
        ),
    ),
    PolicyRow(
        "17",
        home=(Clause(
            DISPATCH, "Only a Planner updates it, such as when a Builder or a Reviewer reports something "
            "the plan didn't foresee.",
        ),),
        pointers=(Clause(
            HANDOFF, "For later tickets, use [Planner → Tickets](planner.md#tickets), The dispatch plan.",
        ),),
        red=(Clause(HANDOFF, r"(?i)comes from the planner.s dispatch plan|each start request takes the form"),),
        search=r"only the Planner|Planner.s dispatch|Planner updates",
        branches=(
            ("approved ordered plan", (
                Clause(
                    DISPATCH, "**The dispatch plan.** When habit approves, the Planner's final handoff (`handoff.md`) "
                    "carries the dispatch plan: every approved ticket of the effort, whether a spec, a map, a parent issue "
                    "or a release, in dispatch order, each with its difficulty line, start instruction and its condition",
                ),
                Clause(DISPATCH, "A spec approved for whole-spec delivery is one entry, with the spec's start instruction."),
                Clause(DISPATCH, "habit dispatches from it without opening a Planner after each merge."),
            )),
            ("changed plan", (Clause(
                DISPATCH, "The Planner also writes the plan in English, using the canonical form from `AGENTS.md`, "
                "How to start, as a comment on the effort's parent issue.",
            ),)),
        ),
    ),
    PolicyRow(
        "37",
        home=(Clause(
            TIER, "**Rejecting below high.** A Builder that wants to reject a review bot's Important finding "
            "at low or medium first raises the PR to high.",
        ),),
        pointers=(Clause(
            ANSWERING, "Before rejecting a bot's Important finding, apply [The tier](#the-tier).",
        ),),
        red=(Clause(ANSWERING, r"rejection of a bot.s important finding first raises|reject.*?first raises"),),
        search=r"first raises|reject a review bot|rejection of a bot",
        branches=(
            ("reject at low or medium", (
                Clause(TIER, "at low or medium first raises the PR to high."),
                Clause(TIER, "Reviews run under the lower tier don't count toward the new one."),
            )),
            ("rejection at high", (Clause(
                ANSWERING, "The Reviewer judges each rejection and reopens one it disagrees with.",
            ),)),
            ("fix or provide evidence", (Clause(
                ANSWERING, 'Fix it and reply "Fixed in `<sha>`", or reject it with evidence: '
                '"Not fixing:" plus a command and its output, or a concrete fact. Then resolve the thread.',
            ),)),
        ),
    ),
    PolicyRow(
        "38",
        home=(Clause(
            FINDINGS, "any review or authorization exception broader than its narrowest statement",
        ),),
        pointers=(Clause(
            EXCEPTIONS, "Judge each statement under [Findings](../../AGENTS.md#findings).",
        ),),
        red=(Clause(EXCEPTIONS, r"broader than.*narrowest"),),
        search=r"broader than|narrowest",
        branches=(
            ("review requirement or authorization exception", (Clause(
                EXCEPTIONS, "A change that adds or edits an exception to a review requirement or an authorization rule, "
                "such as a waiver or a fallback, is checked at every place that states it: the decision "
                "point, each machine-read grammar, the examples and the reports.",
            ),)),
            ("broadened exception blocks while open", (Clause(
                FINDINGS, "**Important** blocks the merge while open:",
            ),)),
        ),
    ),
    PolicyRow(
        "39",
        home=(Clause(FINDINGS, "**Pre-existing** never blocks: anything not introduced by the change, at any severity."),),
        pointers=(Clause(
            ANSWERING, "Classify findings and decide blocking under [Findings](../../AGENTS.md#findings).",
        ),),
        red=(Clause(ANSWERING, r"(?i)never blocks|while an important|no open important"),),
        search=r"never blocks|while an Important|no open Important",
        branches=(
            ("open Important on this head", (
                Clause(FINDINGS, "**Important** blocks the merge while open:"),
                Clause(REVIEW_STATE, "flagged (an Important finding is open)"),
                Clause(REVIEWER_OUTPUTS, "`failure` while an Important finding is open, `success` otherwise."),
            )),
            ("pre-existing Important severity", (Clause(
                ANSWERING, "**Pre-existing.** File the Important-severity findings in one `needs-triage` issue per PR. "
                "Link it from the Merge summary.",
            ),)),
        ),
    ),
    PolicyRow(
        "40",
        home=(Clause(
            CHECKS_FIRST, "2. At high, match each finding on the reviewed head, including Nits, to the Builder's "
            "answer on GitHub. Read the answer itself. A successful `Reviewer` status, a resolved "
            "thread or a mention in the report cannot supply it.",
        ),),
        pointers=(Clause(MINIMUM, "For answers required on this head, apply [Checks first](#checks-first), item 2."),),
        red=(Clause(MINIMUM, r"every finding answered|at high, answer each|including Nits"),),
        search=r"every finding answered|at high, answer each|including Nits",
        branches=(
            ("low or medium Nit", (Clause(ANSWERING, "**Nit.** Optional at low and medium; at high, answer each."),)),
            ("same-head reasoned Nit answer", (Clause(
                CHECKS_FIRST, "On the same head, a reasoned answer to keep the current behavior "
                "can settle a Nit without a repair push.",
            ),)),
            ("answer missing", (
                Clause(CHECKS_FIRST, "If any answer is missing, hold both the high-risk report and the pinned merge command."),
                Clause(CHECKS_FIRST, "Wait as the harness permits, then reread the PR and check the answers again"),
                Clause(CHECKS_FIRST, "If the head changed, follow Rounds."),
            )),
            ("all answers present and merge requirements pass", (Clause(
                CHECKS_FIRST, "Once all answers are present and the other merge requirements pass, publish the report "
                "and link each disposition to the Builder's answer.",
            ),)),
        ),
    ),
    PolicyRow(
        "48",
        home=(Clause(
            HARD_LIMITS, "No agent merges, enables auto-merge, force-pushes, rewrites pushed history, or changes "
            "rulesets, repository or Actions settings, or Actions secrets.",
        ),),
        pointers=(Clause(
            WAIVERS, "For merge authority, follow [Hard limits](../../AGENTS.md#hard-limits) and "
            "[The merge handoff](#the-merge-handoff) for habit's command.",
        ),),
        red=(Clause(WAIVERS, r"no agent merges|agent merge|merge by an agent"),),
        search=r"no agent merges|agent merge|merge by an agent",
        branches=(
            ("waiver", (Clause(WAIVERS, "No agent writes, edits or widens a waiver."),)),
            ("governed merge", (
                Clause(HARD_LIMITS, "Never call habit's alias `ghm`, even from handoffs"),
                Clause(
                    HANDOFF, "**The pinned merge command**, for habit to run: "
                    "`ghm pr merge <n> --admin --squash --match-head-commit <sha>`, with the full head SHA. "
                    "It is the only governed merge path.",
                ),
            )),
        ),
    ),
)
