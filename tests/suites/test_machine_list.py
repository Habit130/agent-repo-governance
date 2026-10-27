"""Seam C, the governed-repository list (#44 §9): version and urgency, a newer record, an unparseable
record, the private mark, the miss count and the skipped sandboxes, read-only and as the agent account.

The installed store comes from the test-built source tree, where version 1 has no change
note. Each case adds change notes for versions 1 to 3 to the installed store, the way a
released machine would hold them, so the list has urgencies to read.
"""

import os
import unittest

import machine_support as ms
import support
from standins import environment

TALLY = os.path.join(support.FIXTURES, "parsers", "record", "tally.yml")
NOTES = {1: "when convenient", 2: "urgent", 3: "when convenient"}


def record(version):
    return support.read_text(TALLY).replace("version: 1\n", "version: %d\n" % version, 1)


def repository(name, private=False, branch="main"):
    return {"nameWithOwner": "Habit130/%s" % name, "isPrivate": private,
            "defaultBranchRef": {"name": branch} if branch else None}


class ListCase(support.TempDirCase):
    def setUp(self):
        super(ListCase, self).setUp()
        source = self.path("source")
        self.commit = ms.build_source(source)
        self.home = ms.ready_home(self.path("home"))
        env = ms.machine_env(self.home, self.path("install-scratch"), gh_recording=ms.write_gh_recording(self.path("gh-install.json")))
        code, out, err = ms.run_machine(["install", "--source", source, "--home", self.home], env)
        self.assertEqual((code, err), (0, ""), out)
        store = os.path.join(self.home, ".agents", "skills", "govern-repository", "store")
        for version, urgency in NOTES.items():
            support.write_tree(store, {"%d/change-note.md" % version: "urgency: %s\nmust-act: no\n\n版本 %d 的说明。\n" % (urgency, version)})
        self.runs = 0

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
    def test_each_line_and_the_header(self):
        repositories = [
            repository("at-one"), repository("at-two", private=True), repository("at-three"), repository("ahead"),
            repository("broken"), repository("plain"), repository("empty", branch=None),
            repository("governance-sandbox"), repository("governance-sandbox-private", private=True),
            repository("on-trunk", branch="release+stable"),
        ]
        records = {
            "Habit130/at-one": record(1), "Habit130/at-two": record(2), "Habit130/at-three": record(3),
            "Habit130/ahead": record(4), "Habit130/broken": "version: one\n", "Habit130/on-trunk": record(3),
        }
        code, found, out = self.list(repositories=repositories, records=records, misses={"Habit130/at-one": 2, "Habit130/broken": 1})
        self.assertEqual(code, 0, out)
        self.assertEqual(found["header"], "installed commit %s；installed version 3" % self.commit)
        self.assertEqual(found["Habit130/at-one"], "版本 1；缺少版本 2、3，最高紧急度 urgent；未关闭 miss record 2 条")
        self.assertEqual(found["Habit130/at-two"], "版本 2；缺少版本 3，最高紧急度 when convenient；未关闭 miss record 0 条；私有")
        self.assertEqual(found["Habit130/at-three"], "版本 3；已是最新版本；未关闭 miss record 0 条")
        self.assertEqual(found["Habit130/ahead"], "版本 4；record 比本机新，先更新本机；未关闭 miss record 0 条")
        self.assertEqual(found["Habit130/broken"], "record 无法解析，运行 generator 修复；未关闭 miss record 1 条")
        self.assertEqual(found["Habit130/on-trunk"], "版本 3；已是最新版本；未关闭 miss record 0 条")
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


class NoReleasedVersion(ListCase):
    def test_every_record_is_newer_than_a_machine_without_a_released_version(self):
        store = os.path.join(self.home, ".agents", "skills", "govern-repository", "store")
        for version in NOTES:
            os.remove(os.path.join(store, str(version), "change-note.md"))
        for version in (2, 3):
            os.rmdir(os.path.join(store, str(version)))
        code, found, out = self.list(repositories=[repository("at-one")], records={"Habit130/at-one": record(1)})
        self.assertEqual(found["header"], "installed commit %s；installed version 无（store 里没有已发布版本）" % self.commit)
        self.assertEqual(found["Habit130/at-one"], "版本 1；record 比本机新，先更新本机；未关闭 miss record 0 条")


if __name__ == "__main__":
    unittest.main()
