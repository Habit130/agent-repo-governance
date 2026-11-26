"""Policy cases generated from the grammar of each v5-or-later Merge watch."""

import itertools
import json

from merge_watch_history import EARLY, FIXTURE, LATE, merged_pr_snapshot, ordinary_change, saved_pr_head
import parsers


class ReviewCase:
    """One recorded push; both members of a pair share the same PR and merge time."""

    def __init__(self, version, tier):
        case = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.api, self.event = case["github"], case["event"]
        self.tier = tier
        self.repo = self.event["repository"]["full_name"]
        self.owner = self.repo.split("/")[0]
        prefix = "repos/" + self.repo
        base, squash = self.event["before"], self.event["after"]
        self.pr, = self.api[f"{prefix}/commits/{squash}/pulls"]
        self.pr["body"] = f"Risk: {tier} — review example"
        self.head = self.pr["head"]["sha"]
        number = self.pr["number"]
        self.comments = self.api[f"{prefix}/issues/{number}/comments"]
        self.summary, = self.comments
        self.statuses = self.api[f"{prefix}/commits/{self.head}/statuses"]
        self.reviews = self.api[f"{prefix}/pulls/{number}/reviews"]
        self.checks = next(rows for path, rows in self.api.items() if "/check-runs?" in path)
        self.record_key = f"{prefix}/contents/.github/governance/record.yml?ref={base}"
        self.record = self.api[self.record_key].replace("version: 5\n", f"version: {version}\n")
        self.order(("copilot", "codex"))
        self.change = ordinary_change(base, squash)
        self.api[f"{prefix}/compare/{base}...{squash}"] = self.change

    def read(self, path):
        prefix = "repos/" + self.repo
        number = self.pr["number"]
        if path == f"{prefix}/pulls/{number}/merge-description":
            return merged_pr_snapshot(self.pr)
        if path == f"{prefix}/git/ref/pull/{number}/head":
            return saved_pr_head(self.pr)
        return self.api[path]

    def order(self, bots):
        record = self.record.split("  review_bots:")[0]
        if bots is not None:
            record += "  review_bots:\n" + "".join(f'    - "{bot}"\n' for bot in bots)
        self.api[self.record_key] = record

    def declare(self, reviews, decision="no", title_head=None):
        head = self.head if title_head is None else title_head
        lines = [f"## Merge summary: {self.tier} at {head}", "Required reviews: " + ", ".join(reviews)]
        if self.tier == "high" and decision is not None:
            lines.append("Security review applies: " + decision)
        self.summary["body"] = "\n".join(lines)

    def comment(self, author, body):
        row = {"user": {"login": author}, "body": body, "created_at": EARLY, "updated_at": EARLY}
        self.comments.append(row)
        return row

    def waiver(self, item):
        return self.comment(self.owner, f"Waiver: {item} at {self.head} — fixture approval")

    def codex(self):
        marker = json.dumps({"code_review": {"commit_sha": self.head, "status": "completed"}})
        return self.comment("chatgpt-codex-connector[bot]", f"<!-- codex-review-state:v1 {marker} -->")

    def check(self, test, watch, missing=(), problems=()):
        diagnostics = []
        result = watch.decide("push", self.event, "CheckoutAccount", self.read, problems=diagnostics)
        expected = []
        if missing:
            number = self.pr["number"]
            observed = f"Merged head {self.head}, declared {self.tier}, lacks: {', '.join(missing)}."
            expected.append({
                "title": f"Miss: process miss, missing-review in #{number}",
                "body": f"Merged PR: #{number}\nKind: process miss\nCategory: missing-review\n"
                        f"Observed: {observed}\nFound by: Merge watch\nBug issue: none\n",
                "labels": ["miss"],
            })
        test.assertEqual((result, diagnostics), (expected, list(problems)))


# Independent policy examples. The script supplies the states to visit.
MINIMUM = {"low": ("self-verification",), "medium": ("self-verification", "bot-1"),
           "high": ("self-verification", "bot-1", "reviewer")}
CLEAR = {"self-verification": "clear", "bot-1": "clear(copilot)", "reviewer": "clear", "security": "clear"}


def items(watch, tier, overrides=None):
    rows = {kind: CLEAR[kind] for kind in MINIMUM[tier]}
    rows.update(overrides or {})
    return [f"{kind}={rows[kind]}" for kind in watch.KINDS if rows.get(kind) is not None]


class ReviewGrammarCases:
    def versions(self):
        for version in parsers.TEMPLATES.versions():
            if version >= 5:
                yield version, self.load_watch(version)

    def test_title_and_required_kinds(self):
        for version, watch in self.versions():
            self.assertEqual(watch.KINDS, tuple(CLEAR))
            self.assertEqual(set(watch.REQUIRED), set(MINIMUM))
            for tier, required in watch.REQUIRED.items():
                with self.subTest(version=version, tier=tier):
                    self.assertEqual(required, MINIMUM[tier])
                    case = ReviewCase(version, tier)
                    rows = items(watch, tier)
                    case.declare(rows)
                    case.check(self, watch)
                    correct = case.summary["body"]
                    other_tier = next(t for t in watch.REQUIRED if t != tier)
                    first, rest = correct.split("\n", 1)
                    for invalid in (first.replace(tier, other_tier), first.replace(case.head, case.head[:7]),
                                    first.replace(case.head, case.head[:7] + "0" * 33),
                                    first.replace(case.head, "0" * 40), "preface\n" + first):
                        case.summary["body"] = invalid + "\n" + rest
                        case.check(self, watch, ("merge-summary",))
                    case.summary["body"] = correct
                    with self.subTest(author="other"):
                        case.summary["user"]["login"] = "OtherAgent"
                        case.check(self, watch, ("merge-summary",))
                    case.summary["user"]["login"] = "HistoricalAgent"
                    for kind in watch.KINDS:
                        with self.subTest(kind=kind):
                            self.assertIn(kind, CLEAR)
                            case.declare(items(watch, tier, {kind: CLEAR[kind]}))
                            case.check(self, watch)
                            case.declare(items(watch, tier, {kind: None}))
                            case.check(self, watch, ("merge-summary",) if kind in required else ())

    def test_slot_state_and_provider_order(self):
        def slot_verdict(state, provider, order, tier):
            if state == "clear":
                return () if provider in order[:1] else ("bot-1",)
            if state == "fallback":
                if tier == "low":
                    return ("merge-summary",)
                return () if provider in order[1:] else ("bot-1",)
            if state == "unavailable":
                return () if tier == "medium" and provider in order[-1:] else ("bot-1",)
            if state == "no-provider":
                return () if tier == "medium" else ("bot-1",)
            if state == "waived":
                return () if provider == "none" or provider in order else ("bot-1",)
            self.fail(f"no evidence example for slot state {state}")

        for version, watch in self.versions():
            targets = {"provider": tuple(watch.PROVIDERS), "none": (watch.NO_PROVIDER,),
                       "provider or none": (*watch.PROVIDERS, watch.NO_PROVIDER)}
            for tier in watch.REQUIRED:
                case = ReviewCase(version, tier)
                codex = case.codex()
                waiver = case.waiver("bot-1")
                for state, domain in watch.SLOT_STATES.items():
                    with self.subTest(version=version, tier=tier, state=state, domain=domain):
                        self.assertIn(domain, targets)
                        for provider in targets[domain]:
                            rows = items(watch, tier, {"bot-1": f"{state}({provider})", "reviewer": "clear"})
                            case.declare(rows)
                            for size in range(len(watch.PROVIDERS) + 1):
                                for order in itertools.permutations(watch.PROVIDERS, size):
                                    with self.subTest(provider=provider, order=order):
                                        case.order(order)
                                        expected = slot_verdict(state, provider, order, tier)
                                        case.check(self, watch, expected)
                                        if expected:
                                            continue
                                        if state == "waived":
                                            index = case.comments.index(waiver)
                                            case.comments.pop(index)
                                            case.check(self, watch, ("bot-1",))
                                            case.comments.insert(index, waiver)
                                        elif state in ("unavailable", "no-provider"):
                                            status = case.statuses.pop()
                                            case.check(self, watch, ("bot-1", "reviewer"))
                                            case.statuses.append(status)
                                            saved = case.summary["body"]
                                            case.summary["body"] = saved.replace(", reviewer=clear", "")
                                            case.check(self, watch, ("bot-1",))
                                            case.summary["body"] = saved
                                        else:
                                            witnesses = {"codex": (case.comments, codex),
                                                         "copilot": (case.reviews, case.reviews[0])}
                                            evidence, witness = witnesses[provider]
                                            index = evidence.index(witness)
                                            evidence.pop(index)
                                            case.check(self, watch, ("bot-1",))
                                            evidence.insert(index, witness)

    def test_declarations_and_waiver_evidence(self):
        for version, watch in self.versions():
            for tier in watch.REQUIRED:
                for kind in watch.KINDS:
                    if kind in watch.BOT_SLOTS:
                        continue  # The slot grammar includes its provider.
                    for state in watch.OTHER_STATES:
                        with self.subTest(version=version, tier=tier, kind=kind, state=state):
                            case = ReviewCase(version, tier)
                            decision = "yes" if kind == "security" else "no"
                            case.declare(items(watch, tier, {kind: state}), decision)
                            if state == "clear":
                                case.check(self, watch)
                                if kind == "reviewer":
                                    case.statuses.clear()
                                    case.check(self, watch, (kind,))
                                elif kind == "security" and tier == "high":
                                    case.declare(items(watch, tier), decision)
                                    case.check(self, watch, ("security", "merge-summary"))
                                else:
                                    # The row itself is the writer's attestation. Optional rows may be omitted.
                                    case.declare(items(watch, tier, {kind: None}), decision)
                                    case.check(self, watch, ("merge-summary",) if kind in MINIMUM[tier] else ())
                            elif state == "waived":
                                self.check_waiver(case, watch, kind)
                            else:
                                self.fail(f"no evidence example for {kind}={state}")

    def check_waiver(self, case, watch, kind):
        case.check(self, watch, (kind,))
        row = case.waiver(kind)
        good = row["body"]
        self.assertEqual(watch.WAIVER.fullmatch(good).group(1), kind)
        row["user"]["login"] = case.owner.swapcase()
        case.check(self, watch)
        for author in ("HistoricalAgent", "AnotherAccount"):
            row["user"]["login"] = author
            case.check(self, watch, (kind,))
        row["user"]["login"] = case.owner
        verification = good.replace(kind + " at ", 'verification "fixture row" at ')
        self.assertEqual(watch.WAIVER.fullmatch(verification).group(1), 'verification "fixture row"')
        self.assertIsNone(watch.WAIVER.fullmatch(verification.replace('"fixture row"', '""')))
        for item in ("bot-2", "checks", "risk", "merge-summary"):
            row["body"] = good.replace(kind + " at ", item + " at ")
            self.assertIsNone(watch.WAIVER.fullmatch(row["body"]))
            case.check(self, watch, (kind,))
        for bad in (good.replace(case.head, case.head[:7]), good.replace(case.head, "f" * 40),
                    good.replace(case.head, case.head.upper()), "note\n" + good, good.split(" — ")[0] + " — ",
                    good.replace(" — ", " - "), verification):
            row["body"] = bad
            case.check(self, watch, (kind,))
        row["body"] = good
        row.update(created_at=LATE, updated_at=LATE)
        case.check(self, watch, (kind,))

    def test_each_provider_completion_has_independent_witnesses(self):
        for version, watch in self.versions():
            with self.subTest(version=version):
                self.assertEqual(set(watch.gate.REVIEW_BOTS), set(watch.PROVIDERS),
                                 "each configurable provider needs a completion reader and evidence examples")
            for tier, provider in itertools.product(watch.REQUIRED, watch.PROVIDERS):
                with self.subTest(version=version, tier=tier, provider=provider):
                    case = ReviewCase(version, tier)
                    case.order((provider,))
                    case.declare(items(watch, tier, {"bot-1": f"clear({provider})"}))
                    if provider == "codex":
                        comment = case.codex()
                        marker = comment["body"]
                        variants = [(comment, "body", text) for text in (
                            "review requested", marker.replace("completed", "pending"),
                            marker.replace("completed", "error"), marker.replace(case.head, "a" * 40),
                            marker.replace("{", "[", 1))]
                        variants += [(comment["user"], "login", "OtherAccount"), (comment, "created_at", LATE)]
                    elif provider == "copilot":
                        review, = case.reviews
                        check, = case.checks
                        run = next(row for path, row in case.api.items() if "/actions/runs/" in path)
                        job = next(row for path, row in case.api.items() if "/actions/jobs/" in path)
                        for accepted in ("COMMENTED", "APPROVED", "CHANGES_REQUESTED"):
                            review["state"] = accepted
                            case.check(self, watch)
                        review["state"] = "COMMENTED"
                        for row, field, value, message in (
                            (review, "state", None, "Copilot review: missing review state"),
                            (review, "state", "DISMISSED", "Copilot review: state at merge before dismissal cannot be established"),
                            (check, "details_url", None, "Copilot check: ambiguous producer: no matching Actions job and suite"),
                            (job, "check_run_url", None, "Copilot check: ambiguous producer: linked Actions job does not corroborate this check"),
                            (run, "check_suite_id", None, "Copilot check: ambiguous producer: linked Actions run cannot be corroborated"),
                        ):
                            original = row[field]
                            row[field] = value
                            case.check(self, watch, problems=(f"#{case.pr['number']} {message}",))
                            row[field] = original
                        variants = [
                            (review, "state", "UNRECOGNIZED"), (check["app"], "slug", "another-app"),
                            (run, "path", ".github/workflows/ci.yml"), (run["actor"], "login", "OtherActor"),
                            (review["user"], "login", "OtherAccount"), (review, "is_copilot_code_review", False),
                            (review, "commit_id", "a" * 40), (review, "state", "PENDING"),
                            (review, "submitted_at", LATE), (check, "head_sha", "a" * 40),
                            (check, "name", "another-check"), (check, "status", "in_progress"),
                            (check, "completed_at", LATE),
                            *((check, "conclusion", value) for value in ("failure", "cancelled", "neutral")),
                        ]
                        for rows in (case.reviews, case.checks):
                            original = rows.pop()
                            case.check(self, watch, ("bot-1",))
                            rows.append(original)
                    else:
                        self.fail(f"no completion evidence for provider {provider}")
                    case.check(self, watch)
                    for row, field, bad in variants:
                        with self.subTest(field=field, value=bad):
                            original = row[field]
                            row[field] = bad
                            case.check(self, watch, ("bot-1",))
                            row[field] = original

    def test_reviewer_status_and_medium_companion(self):
        for version, watch in self.versions():
            for tier in watch.REQUIRED:
                case = ReviewCase(version, tier)
                case.declare(items(watch, tier, {"reviewer": "clear"}))
                status, = case.statuses
                status["creator"]["login"] = status["creator"]["login"].swapcase()
                with self.subTest(version=version, tier=tier):
                    case.check(self, watch)
                    for delta in ({"context": "Other"}, {"creator": {"login": "AnotherAccount"}},
                                  {"created_at": LATE}, *({"state": s} for s in ("pending", "error", "failure"))):
                        case.statuses[:] = [dict(status, **delta)]
                        case.check(self, watch, ("reviewer",))
                    case.statuses[:] = [dict(status, state="failure"), status]
                    case.check(self, watch, ("reviewer",))
                    case.statuses[0]["created_at"] = LATE
                    case.check(self, watch)
                    case.statuses.clear()
                    case.check(self, watch, ("reviewer",))
            case = ReviewCase(version, "medium")
            case.declare(items(watch, "medium"))
            case.check(self, watch)
            case.change["files"][0]["filename"] = "AGENTS.md"
            case.check(self, watch, ("merge-summary",))
            case.declare(items(watch, "medium", {"reviewer": "clear"}))
            case.check(self, watch)
            case.statuses.clear()
            case.check(self, watch, ("reviewer",))

    def test_historical_policies_and_indeterminate_evidence(self):
        for version, watch in self.versions():
            for tier in watch.REQUIRED:
                for base in range(1, watch.REVIEW_BOTS_VERSION):
                    with self.subTest(version=version, tier=tier, historical_base=base):
                        case = ReviewCase(base, tier)
                        if base < 3:
                            case.order(None)
                        case.declare(items(watch, tier), title_head=case.head[:7])
                        case.check(self, watch)
                        case.statuses.clear()
                        needs_status = ("reviewer",) if tier != "low" else ()
                        case.check(self, watch, needs_status)
                        row = case.waiver("reviewer")
                        case.check(self, watch, () if base == 3 else needs_status)
                        row["body"] = row["body"].replace(case.head, "b" * 40)
                        case.check(self, watch, needs_status)
            case = ReviewCase(version, "medium")
            case.declare(items(watch, "medium", {"bot-1": "no-provider(none)", "reviewer": "clear"}))
            case.order(())
            case.check(self, watch)
            case.order(None)
            case.check(self, watch, problems=("#54 policy: historical record omits review_bots",))

    def test_required_line_grammar(self):
        for version, watch in self.versions():
            for tier in watch.REQUIRED:
                for kind in watch.KINDS:
                    if kind in watch.BOT_SLOTS:
                        entries = ((state, provider) for state in watch.SLOT_STATES
                                   for provider in (*watch.PROVIDERS, watch.NO_PROVIDER, "unknown", None))
                    else:
                        entries = itertools.product(watch.OTHER_STATES, (None, *watch.PROVIDERS, watch.NO_PROVIDER))
                    for state, provider in entries:
                        with self.subTest(version=version, tier=tier, kind=kind, state=state, provider=provider):
                            value = state if provider is None else f"{state}({provider})"
                            line = watch.SUMMARY_REVIEWS + ", ".join(items(watch, tier, {kind: value}))
                            if kind not in watch.BOT_SLOTS:
                                valid = provider is None
                            else:
                                allowed = {"clear": set(watch.PROVIDERS),
                                           "fallback": set() if tier == "low" else set(watch.PROVIDERS),
                                           "waived": {*watch.PROVIDERS, "none"}, "unavailable": set(watch.PROVIDERS),
                                           "no-provider": {"none"}}
                                self.assertIn(state, allowed)
                                valid = provider in allowed[state]
                            parsed = watch.parse_reviews(line, tier)
                            if valid:
                                self.assertIsNotNone(parsed)
                                self.assertEqual(parsed[kind], (state, provider))
                            else:
                                self.assertIsNone(parsed)
                rows = items(watch, tier, CLEAR)
                for bad in (rows[::-1], rows + rows[-1:], rows + ["bot-2=clear(copilot)"],
                            ["self-verification=flagged"] + rows[1:]):
                    with self.subTest(version=version, tier=tier, rows=bad):
                        self.assertIsNone(watch.parse_reviews(watch.SUMMARY_REVIEWS + ", ".join(bad), tier))

    def test_high_security_decision(self):
        for version, watch in self.versions():
            case = ReviewCase(version, "high")
            for state in watch.OTHER_STATES:
                with self.subTest(version=version, state=state):
                    rows = items(watch, "high", {"security": state})
                    case.declare(rows, "yes")
                    if state == "waived":
                        case.waiver("security")
                    case.check(self, watch)
                    for decision in (None, "unknown"):
                        case.declare(rows, decision)
                        case.check(self, watch, ("merge-summary",))
                    case.declare(rows, "no")
                    case.check(self, watch, ("security",) if state == "waived" else ())

    def test_workflow_run_and_exact_duplicate_record(self):
        for version, watch in self.versions():
            case = ReviewCase(version, "low")
            prefix = "repos/" + case.repo
            run = {"id": 101, "run_attempt": 1, "event": "push", "head_branch": "main",
                   "head_sha": case.event["after"], "name": "ci", "path": ".github/workflows/ci.yml",
                   "html_url": f"https://github.com/{case.repo}/actions/runs/101"}
            event = dict(case.event, workflow_run=run)
            case.api[prefix + "/actions/runs/101"] = run
            issues = case.api[prefix + "/issues?labels=miss&state=open"]

            def outcome():
                diagnostics = []
                records = watch.decide("workflow_run", event, "CheckoutAccount", case.read,
                                       problems=diagnostics)
                self.assertEqual(diagnostics, [])
                return records

            self.assertEqual(set(watch.RED), {"failure", "cancelled", "timed_out", "startup_failure"})
            for conclusion in watch.RED:
                with self.subTest(version=version, conclusion=conclusion):
                    run["conclusion"] = conclusion
                    observed = (f"Workflow ci concluded {conclusion} on its push-triggered run "
                                f"{run['html_url']} at commit {run['head_sha']}.")
                    expected = {"title": "Miss: escape, red-default-branch in #54", "labels": ["miss"],
                                "body": f"Merged PR: #54\nKind: escape\nCategory: red-default-branch\n"
                                        f"Observed: {observed}\nFound by: Merge watch\nBug issue: none\n"}
                    self.assertEqual(outcome(), [expected])
                    issues.append(dict(expected, state="open"))
                    self.assertEqual(outcome(), [])
                    issues.clear()
                    for field, value in (("event", "pull_request"), ("event", "workflow_dispatch"),
                                         ("head_branch", "topic"), ("path", watch.WORKFLOW),
                                         ("path", watch.WORKFLOW + "@main")):
                        original = run[field]
                        run[field] = value
                        self.assertEqual(outcome(), [])
                        run[field] = original
            for neutral in ("success", "neutral", "skipped", "stale", "action_required", None):
                run["conclusion"] = neutral
                self.assertEqual(outcome(), [])

    def test_newest_summary_and_evidence_at_merge(self):
        for version, watch in self.versions():
            for tier in watch.REQUIRED:
                with self.subTest(version=version, tier=tier):
                    case = ReviewCase(version, tier)
                    case.declare(items(watch, tier))
                    case.check(self, watch)
                    latest = case.comment("HistoricalAgent", case.summary["body"].splitlines()[0] + "\nnotes")
                    case.check(self, watch, ("merge-summary",))
                    latest.update(created_at=LATE, updated_at=LATE)
                    case.check(self, watch)
                    latest["created_at"] = EARLY
                    case.check(self, watch, problems=(
                        "#54 comments by HistoricalAgent: pre-edit content cannot be established",))

    def test_base_record_is_absent_unreadable_or_malformed(self):
        for version, watch in self.versions():
            for tier in watch.REQUIRED:
                case = ReviewCase(version, tier)
                case.declare(items(watch, tier))
                new_record = case.record_key.replace(case.event["before"], case.event["after"])
                case.api[new_record] = case.api[case.record_key]
                for error, expected in ((watch.NotFound, []), (watch.ReadError, ["#54 policy: historical record could not be read"])):
                    with self.subTest(version=version, tier=tier, read_error=error.__name__):
                        def read(path):
                            if path == case.record_key:
                                raise error(path)
                            return case.read(path)
                        notes, problems = [], []
                        self.assertEqual(watch.decide("push", case.event, "Checkout", read, notes, problems), [])
                        self.assertEqual(problems, expected)
                        self.assertEqual(bool(notes), error is watch.NotFound)
                def neither_record(path):
                    if path in (case.record_key, new_record):
                        raise watch.NotFound(path)
                    return case.read(path)

                problems = []
                self.assertEqual(watch.decide("push", case.event, "Checkout", neither_record, problems=problems), [])
                self.assertEqual(problems, ["#54 policy: historical record could not be read"])
                for raw, message in (("not a record", "invalid historical record"),
                                     (case.record.replace(f"version: {version}", "version: 999"),
                                      "unsupported historical version 999")):
                    with self.subTest(version=version, tier=tier, issue=message):
                        case.api[case.record_key] = raw
                        case.check(self, watch, problems=("#54 policy: " + message,))

    def test_push_association_and_exact_rerun(self):
        for version, watch in self.versions():
            case = ReviewCase(version, "low")
            case.declare(items(watch, "low"))
            case.check(self, watch)
            case.summary["body"] = ""
            case.check(self, watch, ("merge-summary",))
            records = watch.decide("push", case.event, "Checkout", case.read)
            issues = case.api["repos/" + case.repo + "/issues?labels=miss&state=open"]
            issues.extend(dict(record, state="open") for record in records)
            case.check(self, watch)
            issues[0]["state"] = "closed"
            case.check(self, watch, ("merge-summary",))
            case.event["ref"] = "refs/heads/other"
            case.check(self, watch)
            case.event["ref"] = "refs/heads/main"
            case.pr["merge_commit_sha"] = "e" * 40  # A commit from a merged PR's history.
            case.check(self, watch)
            case.pr["base"]["ref"] = "other"
            squash = case.event["after"]
            problems = []
            expected = {"title": "Miss: process miss, push-without-pr", "labels": ["miss"],
                        "body": "Merged PR: none\nKind: process miss\nCategory: push-without-pr\n"
                                f"Observed: Commit {squash} was pushed to main with no merged PR.\n"
                                "Found by: Merge watch\nBug issue: none\n"}
            self.assertEqual(watch.decide("push", case.event, "Checkout", case.read, problems=problems),
                             [expected])
            self.assertEqual(problems, [])

    def test_versions_workflow_filters(self):
        def section(text, key):
            # Blank and comment lines can occur anywhere inside a YAML mapping.
            lines = [line.rstrip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
            self.assertEqual(lines.count(key + ":"), 1)
            start = lines.index(key + ":") + 1
            fields = itertools.takewhile(lambda line: line.startswith(" "), lines[start:])
            return "\n".join(fields)

        for version, watch in self.versions():
            with self.subTest(version=version):
                gate_path = parsers.TEMPLATES.template_path(version, ".github/workflows/governance-gate.yml")
                with open(gate_path, encoding="utf-8") as handle:
                    gate = handle.read()
                watch_path = parsers.TEMPLATES.template_path(version, watch.WORKFLOW)
                with open(watch_path, encoding="utf-8") as handle:
                    audit = handle.read()
                gate_events = section(gate, "on")
                self.assertEqual(gate_events, "  pull_request_target:\n    types: [opened, edited, synchronize, reopened]\n"
                                 "    branches:\n      - @@default_branch@@")
                self.assertIn("group: governance-gate-${{ github.event.pull_request.number }}\n"
                              "  cancel-in-progress: true", gate)
                self.assertIn("fetch-depth: 0", gate)
                self.assertNotIn("ref:", gate.split("steps:", 1)[1])
                self.assertEqual(gate.count("permissions:"), 1)
                self.assertEqual(section(gate, "permissions").splitlines(),
                                 ["  contents: read", "  pull-requests: read", "  checks: write"])
                audit_events = section(audit, "on")
                self.assertEqual(audit_events, "  push:\n    branches:\n      - @@default_branch@@\n  workflow_run:\n"
                                 "    types: [completed]\n    branches:\n      - @@default_branch@@\n    workflows:\n"
                                 '      - "**"\n      - "!merge-watch"')
                self.assertNotIn("\nconcurrency:", audit)
                self.assertEqual(audit.count("permissions:"), 1)
                permissions = section(audit, "permissions").splitlines()
                self.assertCountEqual(permissions, ["  contents: read", "  pull-requests: read", "  issues: write",
                                                    "  checks: read", "  statuses: read", "  actions: read"])
