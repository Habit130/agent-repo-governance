"""Seam C, the governed-repository list (#44 §9): version and urgency, a newer record, an unparseable
record, the private mark, the miss count and the skipped sandboxes, read-only and as the agent account.

Each case sets the urgencies of versions 1 to 4 in its isolated installed store to cover
both highest-urgency outcomes.
"""

import io
import json
import os
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

import machine_support as ms
import support
import machine
from standins import environment

TALLY = os.path.join(support.FIXTURES, "parsers", "record", "tally.yml")
NOTES = {1: "when convenient", 2: "urgent", 3: "when convenient", 4: "when convenient"}


def record(version):
    return support.read_text(TALLY).replace("version: 1\n", "version: %d\n" % version, 1)


def repository(name, private=False, branch="main"):
    return {"nameWithOwner": "Habit130/%s" % name, "isPrivate": private,
            "defaultBranchRef": {"name": branch} if branch else None}


class ListCase(support.TempDirCase):
    def setUp(self):
        super(ListCase, self).setUp()
        source = support.init_repo(self.path("source"))
        self.commit = support.commit_tree(source, ms.list_source_files(), "list fixture")
        self.home = ms.ready_home(self.path("home"))
        env = ms.machine_env(self.home, self.path("install-scratch"), gh_recording=ms.write_gh_recording(self.path("gh-install.json")))
        code, out, err = ms.run_machine(["install", "--source", source, "--home", self.home], env)
        self.assertEqual((code, err), (0, ""), out)
        self.store = os.path.join(self.home, ".agents", "skills", "govern-repository", "store")
        for version in NOTES:
            self.write_note(version, "no")
        self.runs = 0

    def write_note(self, version, must_act):
        note = "urgency: %s\nmust-act: %s\n\n版本 %d 的说明。\n" % (NOTES[version], must_act, version)
        support.write_tree(self.store, {"%d/change-note.md" % version: note})

    def list(self, **gh):
        self.runs += 1
        scratch = self.path("scratch-%d" % self.runs)
        os.makedirs(scratch)
        env = ms.machine_env(self.home, scratch, gh_recording=ms.write_gh_recording(os.path.join(scratch, "gh.json"), **gh))
        before = ms.snapshot(self.home)
        code, out, err = ms.run_machine(["list"], env)
        self.assertEqual(err, "", out)
        self.assertEqual(ms.snapshot(self.home), before, "the list changed the home")
        self.assertFalse(ms.ghm_called(scratch), "the list called ghm")
        calls = environment.read_log(scratch)
        self.assertTrue(all(c["recorded"] for c in calls), [c["args"] for c in calls if not c["recorded"]])
        self.calls = calls
        return code, {subject: detail for _, subject, detail in ms.lines(out)}, out


class GovernedRepositories(ListCase):
    def test_only_missing_notes_that_call_for_action_are_referenced(self):
        for version in (1, 3, 4):
            self.write_note(version, "yes")
        code, found, out = self.list(repositories=[repository("at-one")], records={"Habit130/at-one": record(1)})
        self.assertEqual(code, 0, out)
        note3 = os.path.join(self.store, "3", "change-note.md")
        note4 = os.path.join(self.store, "4", "change-note.md")
        self.assertEqual(found["Habit130/at-one"],
                         "版本 1；缺少版本 2、3、4，最高紧急度 urgent；版本说明要求 habit 操作："
                         "版本 3（%s）、版本 4（%s）；未关闭 miss record 0 条" % (note3, note4))
        self.assertIn("版本 3 的说明。", support.read_text(note3))
        self.assertIn("版本 4 的说明。", support.read_text(note4))

    def test_each_line_and_the_header(self):
        repositories = [
            repository("at-one"), repository("at-two", private=True), repository("at-three"), repository("ahead"),
            repository("broken"), repository("plain"), repository("empty", branch=None),
            repository("governance-sandbox"), repository("governance-sandbox-private", private=True),
            repository("on-trunk", branch="release+stable"),
        ]
        records = {
            "Habit130/at-one": record(1), "Habit130/at-two": record(2), "Habit130/at-three": record(3),
            "Habit130/ahead": record(5), "Habit130/broken": "version: one\n", "Habit130/on-trunk": record(4),
        }
        code, found, out = self.list(repositories=repositories, records=records, misses={"Habit130/at-one": 2, "Habit130/broken": 1})
        self.assertEqual(code, 0, out)
        self.assertEqual(found["header"], "installed commit %s；installed version 4" % self.commit)
        self.assertEqual(found["Habit130/at-one"], "版本 1；缺少版本 2、3、4，最高紧急度 urgent；版本说明要求 habit 操作：无；未关闭 miss record 2 条")
        self.assertEqual(found["Habit130/at-two"], "版本 2；缺少版本 3、4，最高紧急度 when convenient；版本说明要求 habit 操作：无；未关闭 miss record 0 条；私有")
        self.assertEqual(found["Habit130/at-three"], "版本 3；缺少版本 4，最高紧急度 when convenient；版本说明要求 habit 操作：无；未关闭 miss record 0 条")
        self.assertEqual(found["Habit130/ahead"], "版本 5；record 比本机新，先更新本机；未关闭 miss record 0 条")
        self.assertEqual(found["Habit130/broken"], "record 无法解析，运行 generator 修复；未关闭 miss record 1 条")
        self.assertEqual(found["Habit130/on-trunk"], "版本 4；已是最新版本；未关闭 miss record 0 条")
        for absent in ("Habit130/plain", "Habit130/empty", "Habit130/governance-sandbox", "Habit130/governance-sandbox-private"):
            self.assertNotIn(absent, found)
        touched = " ".join(" ".join(c["args"]) for c in self.calls)
        self.assertNotIn("governance-sandbox", touched)
        self.assertIn("record.yml?ref=release%2Bstable", touched)
        self.assertTrue(all(c["args"][0] in ("api", "repo", "issue") for c in self.calls))

    def test_a_record_that_cannot_be_read_is_a_failed_line(self):
        code, found, out = self.list(repositories=[repository("flaky")], records={"Habit130/flaky": None})
        self.assertEqual(code, 1, out)
        self.assertIn("读取 record 失败", found["Habit130/flaky"])

    def test_no_governed_repository(self):
        code, found, out = self.list(repositories=[repository("plain")])
        self.assertEqual(code, 0, out)
        self.assertEqual(found["repositories"], "没有找到 governed repository")

    def test_another_account_is_refused(self):
        code, found, out = self.list(user="Habit130", repositories=[repository("at-one")], records={"Habit130/at-one": record(1)})
        self.assertEqual(code, 1, out)
        self.assertIn("gh 应以 agent account Habit098 运行，实际：Habit130", found["account"])
        self.assertEqual([c["args"] for c in self.calls], [["api", "user"]])


class AccountDiagnostic(support.TempDirCase):
    """The two inputs to the account failure line in miss #245."""

    aws_key = "AKIA" + "Z" * 16

    def assert_account_failure(self, response, expected):
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(machine.homes.Home, "run", return_value=response) as run:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = machine.main(["list", "--home", self.tmp])

        for stream, output in (("stdout", stdout.getvalue()), ("stderr", stderr.getvalue())):
            self.assertFalse(self.aws_key in output, "AWS access key ID in list " + stream)
        self.assertEqual(code, 1)
        account = [detail for status, subject, detail in ms.lines(stdout.getvalue())
                   if status == "失败" and subject == "account"]
        self.assertTrue(any(expected in line and "列表未生成" in line for line in account),
                        "missing account failure or list outcome in stdout")
        self.assertTrue(run.call_args_list == [mock.call(["gh", "api", "user"])],
                        "list must stop at the identity lookup")

    def test_aws_access_key_id_in_login_is_withheld(self):
        response = (0, json.dumps({"login": self.aws_key}), "")
        self.assert_account_failure(response, "gh 应以 agent account Habit098 运行")

    def test_aws_access_key_id_in_lookup_error_is_withheld(self):
        response = (1, "", "gh: lookup failed: " + self.aws_key)
        self.assert_account_failure(response, "无法确认 gh 是否以 agent account Habit098 运行")


class NoReleasedVersion(ListCase):
    def test_every_record_is_newer_than_a_machine_without_a_released_version(self):
        for version in NOTES:
            os.remove(os.path.join(self.store, str(version), "change-note.md"))
        for version in (2, 3):
            directory = os.path.join(self.store, str(version))
            # A real version may now occupy a formerly synthetic note-only directory.
            if not os.listdir(directory):
                os.rmdir(directory)
        code, found, out = self.list(repositories=[repository("at-one")], records={"Habit130/at-one": record(1)})
        self.assertEqual(found["header"], "installed commit %s；installed version 无（store 里没有已发布版本）" % self.commit)
        self.assertEqual(found["Habit130/at-one"], "版本 1；record 比本机新，先更新本机；未关闭 miss record 0 条")


if __name__ == "__main__":
    unittest.main()
