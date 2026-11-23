"""Recorded v5 push and workflow_run events, including a push larger than the webhook limit."""

import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
from unittest import mock

import support


FIXTURES = Path(support.FIXTURES, "merge-watch")
PREFIX = "repos/Habit130/tally"
OPEN = PREFIX + "/issues?labels=miss&state=open&per_page=100&page=1"


def case_file(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class PushAndOpenRecords:
    """The workflow entry, with gh responses served in-process for multi-thousand-commit pushes."""

    def replay_event(self, event, api, expected, *, name="push", incomplete=None, throttled=None,
                     waits=(), refused=False):
        path = Path(self.path("event.json"))
        path.write_text(json.dumps(event), encoding="utf-8")
        posts = []

        def gh(args, **kwargs):
            include = "--include" in args
            args = [arg for arg in args if arg != "--include"]
            key = "POST" if "--method" in args else args[-1]
            if throttled and throttled.get(key):
                status, headers = throttled[key].pop(0)
                body = b'{"message":"API rate limit exceeded"}' if status in (403, 429) else b"request failed"
                if include and status:
                    body = f"HTTP/2.0 {status} Error\r\n{headers}\r\n\r\n".encode() + body
                return subprocess.CompletedProcess(args, 1, body, b"gh: request failed")
            if args == ["gh", "api", "--method", "POST", "--input", "-", PREFIX + "/issues"]:
                posts.append(json.loads(kwargs["input"]))
                value = {}
            else:
                value = api[args[-1]]
            if value is None:
                return subprocess.CompletedProcess(args, 1, b"", b"fixture read failure")
            data = value if isinstance(value, str) else json.dumps(value)
            if include:
                data = "HTTP/2.0 200 OK\r\nContent-Type: application/json\r\n\r\n" + data
            return subprocess.CompletedProcess(args, 0, data.encode(), b"")

        output = io.StringIO()
        with mock.patch.dict(os.environ, GITHUB_EVENT_NAME=name, GITHUB_EVENT_PATH=str(path)), \
                mock.patch.object(subprocess, "run", gh), contextlib.redirect_stdout(output), \
                mock.patch("time.sleep") as sleep, mock.patch("time.time", return_value=1000):
            result = self.watch.main(["--post"])
        self.assertEqual(result, int(incomplete is not None or refused), output.getvalue()[:2000])
        self.assertEqual(sorted(posts, key=lambda rec: rec["body"]), sorted(expected, key=lambda rec: rec["body"]))
        self.assertEqual([call.args[0] for call in sleep.call_args_list], list(waits))
        if refused:
            self.assertIn("FAIL opening the record", output.getvalue())
        if incomplete:
            self.assertIn("INCOMPLETE ", output.getvalue())
            self.assertIn(incomplete, output.getvalue())
            self.assertNotIn("No miss in this", output.getvalue())

    def test_only_a_genuine_open_red_record_covers_a_continuing_failure(self):
        case = case_file("cases/red-push-run.json")
        event = case["event"]
        sha = event["workflow_run"]["head_sha"]
        path = f"{PREFIX}/commits/{sha}/pulls"
        api = {path + "?per_page=100&page=1": case["github"][path]}
        original, = case["expected"]
        red = dict(original, labels=["miss"], body=original["body"].replace("ci failed", "ci concluded failure"))
        prior = case_file("v5/open-red-record.json")
        api[PREFIX + "/actions/runs/100"] = dict(event["workflow_run"], id=100, head_sha="b" * 40)
        for issue, expected in (
            (prior, []),
            (dict(prior, body="An example follows.\n\n" + prior["body"]), [red]),
            (dict(prior, state="closed"), [red]),
            (dict(prior, body=prior["body"].replace(prior["body"].splitlines()[3], "Observed: placeholder")), [red]),
            (dict(prior, body=prior["body"].replace("Habit130/tally/actions", "Habit130/another/actions")), [red]),
            (dict(prior, body=prior["body"].replace("b" * 40, "b" * 7)), [red]),
            (dict(prior, body=prior["body"].replace("concluded failure", "concluded success")), [red]),
            (dict(prior, body=prior["body"].replace("Workflow ci concluded failure", "CI failed")), []),
            (dict(prior, title=red["title"]), [red]),
            (dict(prior, labels=[{"name": "bug"}]), [red]),
            (dict(prior, body=prior["body"].replace("Found by: Builder", "Found by: ")), [red]),
            (dict(prior, body=prior["body"].replace("Bug issue: none", "Bug issue: pending")), [red]),
        ):
            with self.subTest(issue=issue):
                api[OPEN] = [issue]
                self.replay_event(event, api, expected, name="workflow_run")

    def push_range(self, direct_count):
        # The published v4-to-v5 transition supplies two different historical policies.
        case = case_file("v5/summary-upgrade.json")
        event = case["event"]
        upgrade, follow_on = [row["id"] for row in event["commits"]]
        history = "a" * 40
        direct = [f"{i:040x}" for i in range(1, direct_count + 1)]
        # The second squash's seven-digit title is a miss only under its own v5 parent.
        case["github"][PREFIX + "/issues/43/comments"][0]["body"] = (
            "## Merge summary: low at 1a95462\nRequired reviews: self-verification=clear")
        api = {}
        for path, value in case["github"].items():
            if "/contents/" not in path and "/git/commits/" not in path:
                path += ("&" if "?" in path else "?") + "per_page=100&page=1"
            api[path] = value
        # The Upgrade follows the direct pushes. The event's before SHA has no policy response.
        api[f"{PREFIX}/git/commits/{upgrade}"]["parents"] = [{"sha": direct[-1]}]
        record_path = PREFIX + "/contents/.github/governance/record.yml?ref="
        api[record_path + direct[-1]] = api.pop(record_path + event["before"])
        pr_path = f"{PREFIX}/commits/{upgrade}/pulls?per_page=100&page=1"
        api[f"{PREFIX}/commits/{history}/pulls?per_page=100&page=1"] = api[pr_path]
        for sha in direct:
            api[f"{PREFIX}/commits/{sha}/pulls?per_page=100&page=1"] = []

        shas = [history, *direct, upgrade, follow_on]
        event.update(commits=[{"id": sha} for sha in shas], after=follow_on)
        baseline = case_file("cases/push-without-pr.json")
        direct_record, = baseline["expected"]
        original_sha = baseline["event"]["after"]
        expected = [dict(direct_record, body=direct_record["body"].replace(original_sha, sha), labels=["miss"])
                    for sha in direct]
        expected.append({
            "title": "Miss: process miss, missing-review in #43", "labels": ["miss"],
            "body": "Merged PR: #43\nKind: process miss\nCategory: missing-review\n"
                    "Observed: Merged head 1a95462000000000000000000000000000000000, declared low, "
                    "lacks: merge-summary.\nFound by: Merge watch\nBug issue: none\n",
        })
        return event, api, shas, expected

    def test_ordinary_push_and_identical_rerun(self):
        event, api, _, expected = self.push_range(2)
        self.replay_event(event, api, expected)
        api[OPEN] = [dict(record, state="open", labels=[{"name": "miss"}]) for record in expected]
        self.replay_event(event, api, [])
        api[OPEN][0]["body"] = "Quoted for discussion:\n\n" + expected[0]["body"]
        self.replay_event(event, api, expected[:1])

    def test_paginated_range_recovers_each_commit_and_uses_its_actual_parent(self):
        event, api, shas, expected = self.push_range(2047)
        before, after = event["before"], event["after"]
        for offset in range(0, len(shas), 100):
            page = offset // 100 + 1
            api[f"{PREFIX}/compare/{before}...{after}?per_page=100&page={page}"] = {
                "base_commit": {"sha": before}, "total_commits": len(shas),
                "commits": [{"sha": sha} for sha in shas[offset:offset + 100]],
            }
        # Reconstruct the same range whichever end the webhook retained.
        for retained in (shas[:2048], shas[-2048:]):
            with self.subTest(first=retained[0]):
                event["commits"] = [{"id": sha} for sha in retained]
                self.replay_event(event, api, expected)

    def test_unavailable_comparison_keeps_event_commits_and_the_known_fast_forward_tip(self):
        event, api, _, expected = self.push_range(2)
        before, after = event["before"], event["after"]
        event.update(commits=[event["commits"][1]], size=5, forced=False)
        api[f"{PREFIX}/compare/{before}...{after}?per_page=100&page=1"] = None
        self.replay_event(event, api, [expected[0], expected[-1]],
                          incomplete=f"push range {before}..{after}: could not read comparison page 1")

    def test_failed_later_page_preserves_both_recovered_and_event_records(self):
        event, api, shas, expected = self.push_range(101)
        before, after = event["before"], event["after"]
        event.update(commits=[{"id": after}], size=len(shas))
        path = f"{PREFIX}/compare/{before}...{after}?per_page=100&page="
        api[path + "1"] = {"base_commit": {"sha": before}, "total_commits": len(shas),
                           "commits": [{"sha": sha} for sha in shas[:100]]}
        api[path + "2"] = None
        self.replay_event(event, api, expected[:99] + expected[-1:],
                          incomplete=f"push range {before}..{after}: could not read comparison page 2")

    def test_short_or_unrelated_comparison_never_establishes_coverage(self):
        event, api, shas, expected = self.push_range(2)
        before, after = event["before"], event["after"]
        event.update(commits=[{"id": after}], size=len(shas))
        path = f"{PREFIX}/compare/{before}...{after}?per_page=100&page=1"
        for base, rows, known in (
            (before, shas[1:2], expected[:1] + expected[-1:]),
            (shas[1], shas, expected[-1:]),
            (before, [shas[1], shas[1], None, shas[-1], shas[0]], expected[:1] + expected[-1:]),
        ):
            with self.subTest(base=base, rows=rows):
                api[path] = {"base_commit": {"sha": base}, "total_commits": len(shas),
                             "commits": [{"sha": sha} for sha in rows]}
                self.replay_event(event, api, known, incomplete=f"push range {before}..{after}")

    def test_missing_comparison_count_keeps_readable_commits(self):
        event, api, shas, expected = self.push_range(2)
        before, after = event["before"], event["after"]
        event.update(commits=[{"id": after}], size=len(shas))
        api[f"{PREFIX}/compare/{before}...{after}?per_page=100&page=1"] = {
            "base_commit": {"sha": before}, "commits": [{"sha": shas[1]}],
        }
        self.replay_event(event, api, expected[:1] + expected[-1:],
                          incomplete=f"push range {before}..{after}")

    def test_large_push_resumes_reads_and_issue_posts_after_rate_limits(self):
        event, api, _, expected = self.push_range(2)
        first = event["commits"][0]["id"]
        throttled = {
            f"{PREFIX}/commits/{first}/pulls?per_page=100&page=1": [
                (403, "X-RateLimit-Remaining: 0\r\nX-RateLimit-Reset: 1010"),
            ],
            "POST": [(429, "Retry-After: 2")],
        }
        self.replay_event(event, api, expected, throttled=throttled, waits=(11, 2))

    def test_unrecoverable_rate_limit_stops_after_preserving_prior_posts(self):
        event, api, shas, expected = self.push_range(2)
        later = f"{PREFIX}/commits/{shas[2]}/pulls?per_page=100&page=1"
        self.replay_event(event, api, expected[:1], incomplete="GitHub still rate limited the audit at " + later,
                          throttled={later: [(429, "Retry-After: 99999")]})

    def test_secondary_rate_limit_without_a_header_uses_backoff(self):
        event, api, _, expected = self.push_range(2)
        self.replay_event(event, api, expected, throttled={"POST": [(429, ""), (429, "")]}, waits=(60, 120))

    def test_ambiguous_post_failure_is_reported_without_a_duplicate_write(self):
        event, api, _, expected = self.push_range(2)
        for status in (None, 502):
            with self.subTest(status=status):
                self.replay_event(event, api, expected[1:], refused=True, throttled={"POST": [(status, "")]})

    def test_compare_rate_limit_preserves_payload_and_first_page_records(self):
        event, api, shas, expected = self.push_range(101)
        before, after = event["before"], event["after"]
        event.update(commits=[{"id": after}], size=len(shas))
        path = f"{PREFIX}/compare/{before}...{after}?per_page=100&page="
        api[path + "1"] = {"base_commit": {"sha": before}, "total_commits": len(shas),
                           "commits": [{"sha": sha} for sha in shas[:100]]}
        self.replay_event(event, api, expected[:99] + expected[-1:], incomplete=path + "2",
                          throttled={path + "2": [(429, "Retry-After: 99999")]})

    def test_free_form_red_record_identifies_a_real_red_push_run_on_the_named_commit(self):
        case = case_file("cases/red-push-run.json")
        event = case["event"]
        current = event["workflow_run"]
        previous = case_file("v5/open-red-record.json")
        previous_sha = "b" * 40
        link = "https://github.com/Habit130/tally/actions/runs/100"
        observation = f"Observed: [CI run]({link}) at {previous_sha}."
        previous["body"] = previous["body"].replace(previous["body"].splitlines()[3], observation)
        path = f"{PREFIX}/commits/{current['head_sha']}/pulls"
        run_path = PREFIX + "/actions/runs/100"
        api = {OPEN: [previous], path + "?per_page=100&page=1": case["github"][path]}
        original, = case["expected"]
        red = dict(original, labels=["miss"], body=original["body"].replace("ci failed", "ci concluded failure"))
        prior_run = dict(current, id=100, head_sha=previous_sha, html_url=link, run_attempt=1)
        for run, expected in ((prior_run, []), (dict(prior_run, conclusion="success"), [red]),
                              (dict(prior_run, head_branch="topic"), [red]),
                              (dict(prior_run, head_sha="a" * 40), [red])):
            with self.subTest(run=run):
                api[run_path] = run
                self.replay_event(event, api, expected, name="workflow_run")
        api[run_path] = dict(prior_run, conclusion="success")
        previous["body"] = previous["body"].replace(observation, observation + " No failure was seen.")
        self.replay_event(event, api, [red], name="workflow_run")

    def test_standard_and_free_form_red_records_survive_a_green_rerun_only_after_a_red_attempt(self):
        case = case_file("cases/red-push-run.json")
        present = case["event"]["workflow_run"]
        previous = case_file("v5/open-red-record.json")
        sha = "b" * 40
        link = "https://github.com/Habit130/tally/actions/runs/100"
        run_path = PREFIX + "/actions/runs/100"
        associations = f"{PREFIX}/commits/{present['head_sha']}/pulls"
        red = dict(case["expected"][0], labels=["miss"],
                   body=case["expected"][0]["body"].replace("ci failed", "ci concluded failure"))
        latest = dict(present, id=100, html_url=link, head_sha=sha, conclusion="success", run_attempt=2)
        api = {associations + "?per_page=100&page=1": case["github"][associations], run_path: latest}
        standard = previous["body"].splitlines()[3]
        for observation in (standard, f"Observed: CI check at {sha}. [Run]({link})."):
            api[OPEN] = [dict(previous, body=previous["body"].replace(standard, observation))]
            for old, expected in ((dict(latest, conclusion="timed_out", run_attempt=1), []),
                                  (dict(latest, run_attempt=1), [red])):
                with self.subTest(observation=observation, old=old["conclusion"]):
                    api[run_path + "/attempts/1"] = old
                    self.replay_event(case["event"], api, expected, name="workflow_run")
        api[run_path + "/attempts/1"] = dict(latest, conclusion="failure", run_attempt=1)
        api[run_path + "/attempts/2"] = latest
        for number, expected in ((1, []), (2, [red])):
            with self.subTest(explicit_attempt=number):
                api[OPEN] = [dict(previous, body=previous["body"].replace(link, f"{link}/attempts/{number}"))]
                self.replay_event(case["event"], api, expected, name="workflow_run")
