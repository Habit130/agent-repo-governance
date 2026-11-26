"""Rows 05, 09 and 65 from #229, rechecked at 00d80a0 for #312."""

from policy_text import Clause, PolicyRow, Section

RISK_TIERS = Section("AGENTS.md", "### Risk tiers")
FINDINGS = Section("AGENTS.md", "### Findings")
SECRETS = Section("AGENTS.md", "## Secrets")
DOMAIN_OWNERS = Section("docs/agents/domain.md", "## Who changes them")
DOCS_PR = Section("docs/agents/planner.md", "## The docs PR")
TICKETS = Section("docs/agents/planner.md", "## Tickets")
RERUNS = Section("docs/agents/review.md", "## Rerun-only passes")
BUILD_SECRETS = Section("docs/agents/build.md", "## Actions secrets")
BUILDER_SECRETS = Section("docs/agents/builder.md", "## Actions secrets")
BUILDER_STEPS = Section("docs/agents/builder.md", "## Steps")
EVIDENCE = Section("docs/agents/review.md", "## Evidence comment")
CHECKS_FIRST = Section("docs/agents/review.md", "### Checks first")

DOCS_TIER_POINTER = "Tier the Planner's docs PR under `AGENTS.md`, Risk tiers, using this repository's actual sensitive paths."
RERUN_POINTER = "For the cause issue and merge condition, see `review.md`, Rerun-only passes."

ROWS = (
    PolicyRow(
        "05",
        home=(Clause(RISK_TIERS, "Highest tier in the change wins."),),
        pointers=(
            Clause(DOMAIN_OWNERS, DOCS_TIER_POINTER),
            Clause(DOCS_PR, DOCS_TIER_POINTER),
        ),
        red=(
            Clause(DOMAIN_OWNERS, r"low path|no floor|aren't sensitive"),
            Clause(DOCS_PR, r"low path|no floor|aren't sensitive"),
        ),
        search=r"low path|no floor|aren't sensitive",
        branches=(
            ("confirmed path", (Clause(
                RISK_TIERS,
                "**Sensitive paths**: `.github/governance/record.yml`; defaults medium, confirmed medium/high. "
                "Changes, deletions and either rename side take at least the path's floor.",
            ),)),
            ("plain docs", (Clause(
                RISK_TIERS, "| low | Verified two-way doors, small blast radius, no sensitive paths: docs,",
            ),)),
        ),
    ),
    PolicyRow(
        "09",
        home=(
            Clause(
                RERUNS,
                "A required check that failed, timed out or was cancelled on a head, then passed on that "
                "same head, is a **rerun-only pass** unless a change to an input or configuration used by "
                "that check repairs the failure. A rerun-only pass counts as unrepaired.",
            ),
            Clause(
                RERUNS,
                "The Reviewer and the Merge summary's writer inspect the required checks' run history on the head, "
                "earlier attempts included: GitHub's default listing shows only the latest attempt.",
            ),
            Clause(
                RERUNS,
                "Compare changes between attempts with the evidence comment, verifying that each claimed repair "
                "addresses that check's failure.",
            ),
            Clause(
                RERUNS,
                "For each rerun-only pass, the Builder links an open issue for its cause, including an outside cause.",
            ),
            Clause(
                RERUNS,
                "The Reviewer and the writer confirm the issue is open and covers the cause. A missing, closed or "
                "unrelated issue is an Important finding and blocks the merge.",
            ),
        ),
        pointers=(
            Clause(FINDINGS, "- For rerun-only findings, see `review.md`, Rerun-only passes."),
            Clause(BUILDER_STEPS, RERUN_POINTER),
        ),
        red=(
            Clause(FINDINGS, r"rerun.only.*(?:cause.s open issue|linked open issue)"),
            Clause(BUILDER_STEPS, r"link an open issue for its cause"),
        ),
        search=r"rerun.only|cause.s open issue|linked open issue",
        branches=(
            ("repaired", (Clause(
                RERUNS,
                "A governance gate run after a PR body edit qualifies as repaired only when the edit "
                "corrects the failed gate input, such as its Risk declaration.",
            ),)),
            ("unrepaired", (
                Clause(RERUNS, "An unrelated PR edit is not a repair."),
                Clause(
                    EVIDENCE, "each required check's rerun-only pass on this head, with the failed run and "
                    "the cause's open issue, or an explicit statement that there were none;",
                ),
                Clause(
                    CHECKS_FIRST, "perform the history and issue checks in Rerun-only passes and link "
                    "each cause's open issue in the summary.",
                ),
            )),
        ),
    ),
    PolicyRow(
        "65",
        home=(
            Clause(
                SECRETS,
                "Only habit writes Actions secrets, in the browser, from a session's settings link and exact name. "
                "No session writes them by command.",
            ),
            Clause(
                TICKETS, "**Actions secrets**: each one CI needs, by name, purpose and issuing service, never a value.",
            ),
        ),
        pointers=(
            Clause(BUILD_SECRETS, "For the owner action follow `AGENTS.md`, Secrets. Use the ticket fields from `planner.md`, Tickets."),
            Clause(TICKETS, "For the owner action follow `AGENTS.md`, Secrets, during ticket approval."),
            Clause(BUILDER_SECRETS, "For the owner action follow `AGENTS.md`, Secrets."),
        ),
        red=(
            Clause(BUILD_SECRETS, r"writes Actions secrets|Actions secrets settings|sets it in the browser"),
            Clause(TICKETS, r"sets it in the browser"),
            Clause(BUILDER_SECRETS, r"writes Actions secrets"),
        ),
        search=r"writes Actions secrets|Actions secrets settings|sets it in the browser",
        branches=(
            ("named in the ticket", (Clause(
                BUILDER_SECRETS,
                "Before relying on an Actions secret the ticket names, confirm it exists by name with `gh secret list`, "
                "which shows names only.",
            ),)),
            ("secret missing or unnamed", (Clause(
                Section("docs/agents/builder.md", "## Escalations"),
                "**An Actions secret** the ticket names is missing, or the work needs one the ticket doesn't name.",
            ),)),
            ("workflow uses a secret", (
                Clause(BUILD_SECRETS, "List each Actions secret a workflow uses, GITHUB_TOKEN aside"),
                Clause(BUILD_SECRETS, "| Name | Purpose | Issuing service |"),
            )),
            ("workflow uses none", (Clause(BUILD_SECRETS, "With none, say that CI uses no Actions secret."),)),
        ),
    ),
)
