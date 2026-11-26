"""Rows with handoff, tracker and label decision sites, rechecked at 00d80a0."""

import re

import machine_support
from machinelib import SANDBOXES
from policy_text import Clause, PolicyRow, Section


def agent_doc(name, heading=None):
    return Section("docs/agents/" + name + ".md", heading)


START = Section("AGENTS.md", "## How to start")
TALKING = Section("AGENTS.md", "## Talking to habit and to other agents")
SECRETS = Section("AGENTS.md", "## Secrets")
RISK = Section("AGENTS.md", "### Risk tiers")
SPECS = agent_doc("planner", "## Specs")
PLANNER_TICKETS = agent_doc("planner", "## Tickets")
RESULTS = agent_doc("builder", "## Results-comment tickets")
DIRECT = agent_doc("builder", "## A direct request")
OUTSIDE = agent_doc("builder", "## Outside PRs")
HANDOFF = agent_doc("handoff", "## A final handoff")
DISPATCH = agent_doc("handoff", "## Only the Planner arranges what comes next")
EXAMPLES = agent_doc("handoff", "## Examples")
MERGE = agent_doc("review", "### The merge handoff")
TRACKER_INTRO = agent_doc("issue-tracker")
TRACKER_TICKETS = agent_doc("issue-tracker", "## Tickets")
BLOCKING = agent_doc("issue-tracker", "## Sub-issues and blocking")
PR_TRIAGE = agent_doc("issue-tracker", "## Pull requests as a triage surface")
WAYFINDING = agent_doc("issue-tracker", "## Wayfinding operations")
MISS = agent_doc("issue-tracker", "## Miss records")
MISS_FORMAT = agent_doc("issue-tracker", "### Format")
CATEGORY = agent_doc("triage-labels", "## Category roles")
STATE = agent_doc("triage-labels", "## State roles")
READY = agent_doc("triage-labels", "## `ready-for-agent`")
OTHER = agent_doc("triage-labels", "## Other labels")
MERGE_WATCH = Section(".github/governance/merge_watch.py")

ROWS = (
    PolicyRow(
        "10",
        home=(Clause(SPECS, "A spec holds `to-spec`'s sections plus a Delivery section: the shape chosen above, and why."),),
        pointers=(
            Clause(READY, "For spec labels and the dispatch unit, see `planner.md`, Specs."),
            Clause(TRACKER_TICKETS, "For the dispatch unit and spec labels, see `planner.md`, Specs."),
        ),
        red=(
            Clause(READY, r"spec loses the label|spec keeps it|its tickets never take it"),
            Clause(TRACKER_TICKETS, r"approved for whole-spec delivery is dispatched as one"),
        ),
        search=r"whole-spec|spec keeps|spec loses",
        branches=(
            ("separate tickets", (Clause(SPECS, "remove `ready-for-agent` from the spec; only its tickets are dispatched."),)),
            ("approved whole spec", (Clause(
                SPECS, "A spec approved for whole-spec delivery is the exception: it keeps the label, "
                "its tickets never take it, and it is dispatched as one entry.",
            ),)),
        ),
    ),
    PolicyRow(
        "13",
        home=(
            Clause(RESULTS, "A ticket whose body carries the exact line `Delivery: results comment, no PR` is a results-comment ticket."),
            Clause(RESULTS, "habit approves this delivery by approving the ticket; there is no separate label or approval record."),
            Clause(RESULTS, "A Builder cannot choose this delivery: adding the line to a frozen ticket requires habit's recorded agreement"),
            Clause(RESULTS, "Completion requires passing Verification and every acceptance criterion met."),
            Clause(RESULTS, "On completion, post one English results comment answering each acceptance criterion"),
            Clause(RESULTS, "Then close the ticket as completed; if it is its spec's last open sub-issue, also close the spec."),
            Clause(RESULTS, "The work changes no tracked repository file, creates no branch and pushes nothing."),
        ),
        pointers=(
            Clause(BLOCKING, "For a ticket's delivery and completion rules, see `builder.md`, Results-comment tickets."),
            Clause(TRACKER_TICKETS, "results-comment tickets follow `builder.md`, Results-comment tickets."),
        ),
        red=(Clause(BLOCKING, r"PR-delivered ticket has merged|results-comment ticket .* is closed as completed"),),
        search=r"results.comment|no PR|PR-delivered",
        branches=(
            ("absent declaration and direct request", (
                Clause(RESULTS, "A ticket without the line follows the PR steps below."),
                Clause(RESULTS, "Direct requests use the PR path."),
                Clause(DIRECT, "Build it as your ticket."),
                Clause(TRACKER_TICKETS, "a PR's `Closes #<n>` lines close those issues when habit merges it"),
            )),
            ("incomplete results", (Clause(RESULTS, "Otherwise, leave the ticket open and stop under Escalations for habit's decision."),)),
        ),
    ),
    PolicyRow(
        "18",
        home=(
            Clause(PLANNER_TICKETS, "It is a list, never a table."),
            Clause(PLANNER_TICKETS, "with its paste block standing alone so habit copies it whole."),
            Clause(PLANNER_TICKETS, "The Planner also writes the plan in English, using the canonical form from `AGENTS.md`, How to start, as a comment on the effort's parent issue."),
        ),
        pointers=(Clause(DISPATCH, "For its terminal and GitHub forms, see `planner.md`, Tickets, The dispatch plan."),),
        red=(Clause(DISPATCH, r"list, never a table|stands alone in its own block|GitHub copy uses the canonical form"),),
        search=r"list, never a table|list, never a|standing alone",
        branches=(
            ("terminal start request", (Clause(PLANNER_TICKETS, "Each terminal translation uses a start request for one harness"),)),
            ("parent issue", (Clause(PLANNER_TICKETS, "using the canonical form from `AGENTS.md`, How to start, as a comment on the effort's parent issue."),)),
        ),
    ),
    PolicyRow(
        "24",
        home=(
            Clause(MERGE, "3. **Misses**, only when any is open: the count of open miss records, `gh issue list --label miss --state open --repo Habit130/tally`."),
        ),
        pointers=(Clause(DISPATCH, "for open misses in the delivery, follow `review.md`, The merge handoff, item 3;"),),
        red=(Clause(DISPATCH, r"count of open miss|shown only when above zero|Planner start request for `retro`|retro.*oldest"),),
        search=r"count of open miss|only when any is open|shown only when above zero|oldest",
        branches=(
            ("zero open", (Clause(MERGE, "**Misses**, only when any is open"),)),
            ("positive count outside the sandboxes", (
                Clause(MERGE, "In every repository except the two registered sandboxes, include a Planner start request in which habit invokes `retro` on the oldest open miss."),
            )),
            ("positive count in the registered sandboxes", (
                Clause(MERGE, "In `Habit130/governance-sandbox` and `Habit130/governance-sandbox-private`, give the count and omit the default start request."),
                Clause(MERGE, "habit can still invoke `retro` on any sandbox record."),
            )),
        ),
    ),
    PolicyRow(
        "25",
        home=(
            Clause(TALKING, "**Agent to agent**: on GitHub, in English; keep later sessions' needed context there."),
            Clause(TALKING, "**Agent to habit**: in the terminal, in plain Chinese"),
            Clause(TALKING, "**habit's decisions**: record needed terminal decisions on GitHub."),
            Clause(TALKING, "**Summaries**: keep an English Merge summary or high-risk report on the PR."),
            Clause(HANDOFF, "**This session**: whether it can be closed, or stays open, with what it waits for and the words habit says on return."),
        ),
        pointers=(Clause(HANDOFF, "Before closing, follow `AGENTS.md`, Talking to habit and to other agents, for the GitHub record and terminal language."),),
        red=(Clause(HANDOFF, r"Before a session ends, it records on GitHub"),),
        search=r"records on GitHub|on GitHub, in English|terminal, in plain Chinese",
        branches=(
            ("recorded context", (Clause(HANDOFF, "Under unfinished, name only what the session could not record."),)),
            ("session can close", (Clause(HANDOFF, "whether it can be closed"),)),
            ("session stays open", (Clause(HANDOFF, "with what it waits for and the words habit says on return."),)),
        ),
    ),
    PolicyRow(
        "26",
        home=(
            Clause(WAYFINDING, "- **Map**: an issue labelled `wayfinder:map`."),
            Clause(WAYFINDING, "- **Child ticket**: a sub-issue of the map labelled `wayfinder:<type>`, where type is `research`, `prototype`, `grilling` or `task`."),
        ),
        pointers=(Clause(OTHER, "For map and child labels, see `issue-tracker.md`, Wayfinding operations."),),
        red=(Clause(OTHER, r"(?:wayfinder:map|Wayfinder ticket)[^\n]*?\| `issue-tracker\.md`, Wayfinding operations \|"),),
        search=r"wayfinder:map|wayfinder:<type>|Wayfinder ticket",
        branches=(
            ("map", (Clause(WAYFINDING, "The **map** is one issue, and its **child** issues are its tickets."),)),
            ("children", (
                Clause(WAYFINDING, "**Frontier**: the map's open children with no open blocker and no assignee."),
                Clause(WAYFINDING, "First in map order wins."),
                Clause(WAYFINDING, "**Resolve**: comment the answer, close the ticket, then add a one-line gist and link to the map's Decisions so far."),
            )),
        ),
    ),
    PolicyRow(
        "44",
        home=(
            Clause(RISK, "**Trusted authors**: habit and the agent account; others' PRs are outside PRs"),
            Clause(OUTSIDE, "A PR by anyone but the repository owner or the agent account fails the governance gate."),
            Clause(OUTSIDE, "with its author credited as co-author, at medium or higher"),
        ),
        pointers=(Clause(PR_TRIAGE, "Identify outside PRs under `AGENTS.md`, Risk tiers. For re-landing, follow `builder.md`, Outside PRs."),),
        red=(Clause(PR_TRIAGE, r"by anyone but the repository owner or the agent account|fails the governance gate"),),
        search=r"repository owner or|repository owner and|Trusted authors",
        branches=(
            ("outside PR re-land requested", (Clause(OUTSIDE, "once your PR is open, close the original with a link to it."),)),
            ("only issues enter triage", (Clause(PR_TRIAGE, "**PRs as a request surface: no.** `triage` reads this flag and handles issues only."),)),
        ),
    ),
    PolicyRow(
        "55",
        home=(Clause(START, "On GitHub use the agent account, the machine's own `gh` login."),),
        pointers=(Clause(TRACKER_INTRO, "For the GitHub identity, see `AGENTS.md`, How to start."),),
        red=(Clause(TRACKER_INTRO, r"Sessions use the `gh` CLI, as the agent account"),),
        search=r"agent account|machine.s own|as the agent|historical account",
        branches=(
            ("ambiguous default target", (Clause(TRACKER_INTRO, "Pass `--repo Habit130/tally` on every `gh` call."),)),
        ),
    ),
    PolicyRow(
        "61",
        home=(
            Clause(MISS, "A miss is governance letting through something its rules should have stopped."),
            Clause(MISS, "Each one gets one issue labelled `miss`, in the repository where it happened."),
            Clause(MISS_FORMAT, "The body opens with these six field lines, in this order, each starting with its name"),
            Clause(MISS_FORMAT, "```text Merged PR: <#n | none> Kind: <escape | process miss> "
                   "Category: <category> Observed: <one line: what was seen, with links and full commit SHAs> "
                   "Found by: <Merge watch | Planner | Builder | Reviewer | habit> Bug issue: <#n | none> ```"),
        ),
        pointers=(Clause(OTHER, "For classification and record format, see `issue-tracker.md`, Miss records."),),
        red=(Clause(OTHER, r"something governance should have stopped got through \| `issue-tracker\.md`, Miss records \|"),),
        search=r"miss is governance|something governance should|one miss record",
        branches=(
            ("existing open record", (
                Clause(MISS, "When one already covers the miss, comment there instead."),
                Clause(MISS, "While a `red-default-branch` record is open, the default branch counts as still red, and no second one opens."),
            )),
            ("new record", (Clause(MISS, "with `miss` as its only label."),)),
            ("audit rerun", (
                Clause(MERGE_WATCH, "A matching open miss issue must identify the miss in its title and six opening fields."),
                Clause(MERGE_WATCH, "Exact observations deduplicate a rerun."),
            )),
            ("concurrent events", (
                Clause(MERGE_WATCH, "Two runs at once can each read no open record, so two workflows failing together may open two `red-default-branch` records"),
            )),
            ("bug linked separately", (Clause(MISS, "A bug keeps its own issue, which goes through triage as usual and which the record links."),)),
        ),
    ),
    PolicyRow(
        "64",
        home=(
            Clause(SECRETS, "Never read, print, commit or post a credential. Name only its type and location, even to habit or in a miss record."),
            Clause(SECRETS, "**An exposed credential**, merged or not, private or public: tell habit its type and location at once."),
            Clause(SECRETS, "Remove the value where possible by a new commit, deleting own comment or editing a body; never rewrite history."),
            Clause(SECRETS, "habit rotates it, whoever's it is."),
        ),
        pointers=(Clause(MISS, "For an exposed credential, follow `AGENTS.md`, Secrets, in the title, body and every comment."),),
        red=(Clause(MISS, r"An exposed credential\*\* is named by its type and location"),),
        search=r"credential value|type and location|type and its location",
        branches=(
            ("exposed during governance", (Clause(SECRETS, "Open a miss record (`issue-tracker.md`, Miss records) and give habit a start request for its `retro`."),)),
            ("pre-governance exposure", (Clause(SECRETS, "Pre-governance credentials follow this response without a miss record; removal is a ticket."),)),
        ),
    ),
    PolicyRow(
        "66",
        home=(
            Clause(MERGE, "**The pinned merge command**, for habit to run: `ghm pr merge <n> --admin --squash --match-head-commit <sha>`, with the full head SHA."),
            Clause(MERGE, "It is the only governed merge path."),
        ),
        pointers=(
            Clause(HANDOFF, "**Reviewer**: after the Merge summary, following `review.md`, The merge handoff."),
            Clause(EXAMPLES, "Give habit the command from `review.md`, The merge handoff, item 1"),
        ),
        red=(Clause(EXAMPLES, r"ghm pr merge.*--match-head-commit"),),
        search=r"match-head-commit|pinned merge|merge command|writer.s final handoff",
        branches=(
            ("human uses full reviewed head", (Clause(MERGE, "with the full head SHA."),)),
            ("example identifies its inputs and closes the session", (
                Clause(EXAMPLES, "using PR #57 and the full head SHA from the summary."),
                Clause(EXAMPLES, "本 session 可以关闭。"),
            )),
        ),
    ),
    PolicyRow(
        "70",
        home=(
            Clause(CATEGORY, "| `bug` | `bug` | Something isn't working |"),
            Clause(CATEGORY, "| `enhancement` | `enhancement` | New feature or request |"),
            Clause(STATE, "| `ready-for-agent` | `ready-for-agent` | Fully specified, ready for an AFK agent |"),
            Clause(READY, "It means habit approved the issue as a ticket and it can be dispatched. It authorizes nothing by itself."),
        ),
        pointers=(Clause(CATEGORY, "Use the table for category roles. For state and dispatch, see State roles and `ready-for-agent`."),),
        red=(Clause(CATEGORY, r"means something is broken|means a new feature or improvement"),),
        search=r"something is broken|new feature|fully specified|approved the issue as a ticket",
        branches=(
            ("ready alone", (Clause(READY, "It authorizes nothing by itself."),)),
            ("dispatched", (Clause(READY, "**Dispatch** is habit naming the ticket in a start instruction, which starts its Builder. No comment marks it, and the Builder's claim follows"),)),
        ),
    ),
)


def sandbox_names(handoff):
    """Read the repository literals from the exception in item 3."""
    item = re.search(r"^3\. \*\*Misses\*\*.*?(?=^4\. )", handoff, re.M | re.S)
    if not item:
        raise AssertionError("The merge handoff has no Misses item")
    return tuple(re.findall(r"`([\w-]+/[\w-]+)`", item.group()))
