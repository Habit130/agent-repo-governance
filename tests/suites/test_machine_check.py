"""Seam C, the machine check (#44 §9): every item failing on its own, the home unchanged afterwards.

Each case installs into a ready home, plants one fault, and runs the check with the Codex
stand-in replaying real output, so every other item still passes. The check must leave the
home exactly as it found it.
"""

import json
import os
import unittest

import machine_support as ms
import support

ITEMS = ("Codex rules", "Codex skill list", "Codex user-only key", "名称冲突", "deny entries", "links", "managed skills", "identity")


class CheckCase(support.TempDirCase):
    def setUp(self):
        super(CheckCase, self).setUp()
        self.source = self.path("source")
        ms.build_source(self.source)
        self.home = ms.ready_home(self.path("home"))
        env = ms.machine_env(self.home, self.path("install-scratch"), gh_recording=ms.write_gh_recording(self.path("gh-install.json")))
        code, out, err = ms.run_machine(["install", "--source", self.source, "--home", self.home], env)
        self.assertEqual((code, err), (0, ""), out)
        self.runs = 0

    def h(self, *parts):
        return os.path.join(self.home, *parts)

    def check(self, codex=("codex-execpolicy.json", "codex-prompt-input-ready.json"), gh=None, absent=False):
        """Run the check; return {item: status} and the failing details, asserting the home is unchanged."""
        self.runs += 1
        scratch = self.path("scratch-%d" % self.runs)
        os.makedirs(scratch)
        gh = gh or {}
        recording = ms.write_gh_recording(os.path.join(scratch, "gh.json"), **gh)
        codex_recording = ms.merge_codex_recordings(os.path.join(scratch, "codex.json"), *codex)
        env = ms.machine_env(self.home, scratch, gh_recording=recording, codex_recording=codex_recording)
        before = ms.snapshot(self.home)
        args = ["check", "--home", self.home, "--codex", self.path("absent") if absent else ms.STANDIN_CODEX]
        code, out, err = ms.run_machine(args, env)
        self.assertEqual(err, "", out)
        self.assertEqual(ms.snapshot(self.home), before, "the check changed the home")
        self.assertFalse(ms.ghm_called(scratch), "the check called ghm")
        statuses = ms.statuses(out, "machine check")
        self.assertEqual(sorted(statuses), sorted(ITEMS), out)
        self.assertEqual(code, 1 if "失败" in statuses.values() else 0, out)
        failures = [detail for status, _, detail in ms.lines(out) if status == "失败"]
        return statuses, failures

    def assert_only(self, item, statuses, failures, *expected):
        self.assertEqual({k for k, v in statuses.items() if v != "通过"}, {item}, failures)
        self.assertEqual(statuses[item], "失败")
        for text in expected:
            self.assertTrue(any(text in failure for failure in failures), (text, failures))


class EveryItem(CheckCase):
    def test_a_ready_machine_passes_every_item(self):
        statuses, failures = self.check()
        self.assertEqual(set(statuses.values()), {"通过"}, failures)

    def test_codex_absent_skips_both_codex_items_and_reports_the_skip(self):
        statuses, _ = self.check(absent=True)
        self.assertEqual((statuses["Codex rules"], statuses["Codex skill list"]), ("跳过", "跳过"))
        self.assertEqual({k for k, v in statuses.items() if v != "通过"}, {"Codex rules", "Codex skill list"})

    def test_codex_rules(self):
        with open(self.h(".codex", "rules", "governance.rules"), "w"):
            pass
        statuses, failures = self.check(codex=("codex-execpolicy-empty-rules.json", "codex-prompt-input-ready.json"))
        self.assert_only("Codex rules", statuses, failures, "与 install 写入的内容不同", "`ghm pr merge 1` 未被禁止", "`gh secret set TOKEN` 未被禁止")

    def test_codex_skill_list_shortened(self):
        ms.crowd(self.home, *ms.CROWDS["shortened"])
        statuses, failures = self.check(codex=("codex-execpolicy.json", "codex-prompt-input-shortened.json"))
        self.assert_only("Codex skill list", statuses, failures, "描述被截短")

    def test_codex_skill_list_omitted(self):
        ms.crowd(self.home, *ms.CROWDS["omitted"])
        statuses, failures = self.check(codex=("codex-execpolicy.json", "codex-prompt-input-omitted.json"))
        self.assert_only("Codex skill list", statuses, failures, "被省略：")
        self.assertIn("crowd-1500", " ".join(failures))

    def test_codex_user_only_key(self):
        support.write_tree(self.h(".agents", "skills"), ms.KEYLESS)
        statuses, failures = self.check(codex=("codex-execpolicy.json", "codex-prompt-input-keyless.json"))
        self.assert_only("Codex user-only key", statuses, failures, "gamma-solo 缺少 Codex user-only key")

    def test_a_personal_skill_sharing_a_machine_skills_name(self):
        support.write_tree(self.h(".agents", "skills"), {"my-alpha/SKILL.md": ms.COPIES["alpha-check"]["SKILL.md"]})
        statuses, failures = self.check()
        self.assert_only("名称冲突", statuses, failures, "personal skill ~/.agents/skills/my-alpha 与 machine skill alpha-check 同名")

    def test_a_machine_skills_name_under_codex_skills(self):
        support.write_tree(self.h(".codex", "skills"), {"beta-flow/%s" % rel: text for rel, text in ms.COPIES["beta-flow"].items()})
        statuses, failures = self.check()
        self.assert_only("名称冲突", statuses, failures, "~/.codex/skills 里有 machine skill 的名称 beta-flow")

    def test_a_missing_claude_code_deny_entry(self):
        path = self.h(".claude", "settings.json")
        data = json.loads(support.read_text(path))
        data["permissions"]["deny"].remove("Bash(gh secret delete *)")
        support.write_tree(self.home, {".claude/settings.json": json.dumps(data)})
        statuses, failures = self.check()
        self.assert_only("deny entries", statuses, failures, "Claude Code 缺少 deny entries：Bash(gh secret delete *)")

    def test_opencode_denying_secret_listing(self):
        path = self.h(".config", "opencode", "opencode.json")
        data = json.loads(support.read_text(path))
        data["permission"]["bash"]["gh secret *"] = "deny"
        support.write_tree(self.home, {".config/opencode/opencode.json": json.dumps(data)})
        statuses, failures = self.check()
        self.assert_only("deny entries", statuses, failures, "OpenCode 也拒绝了 `gh secret list`：gh secret * = deny")

    def test_a_later_opencode_pattern_allowing_ghm_again(self):
        path = self.h(".config", "opencode", "opencode.json")
        data = json.loads(support.read_text(path))
        data["permission"]["bash"]["gh*"] = "allow"
        support.write_tree(self.home, {".config/opencode/opencode.json": json.dumps(data)})
        statuses, failures = self.check()
        self.assert_only("deny entries", statuses, failures, "OpenCode 里后面的条目覆盖了 deny：gh* = allow")

    def test_a_user_invoked_skill_under_codex_skills_missing_the_key(self):
        support.write_tree(self.h(".codex", "skills"), ms.KEYLESS)
        statuses, failures = self.check(absent=True)
        self.assertEqual({k for k, v in statuses.items() if v == "失败"}, {"Codex user-only key"}, failures)
        self.assertIn("~/.codex/skills 里的 gamma-solo 缺少 Codex user-only key", failures)

    def test_a_real_file_in_place_of_a_link(self):
        os.remove(self.h(".config", "opencode", "AGENTS.md"))
        support.write_tree(self.home, {".config/opencode/AGENTS.md": "OpenCode's own copy.\n"})
        statuses, failures = self.check()
        self.assert_only("links", statuses, failures, "~/.config/opencode/AGENTS.md 是真实文件或目录")

    def test_a_present_dsh_agents_md(self):
        support.write_tree(self.home, {".dsh/AGENTS.md": "dsh's copy.\n"})
        statuses, failures = self.check()
        self.assert_only("links", statuses, failures, "~/.dsh/AGENTS.md 存在")

    def test_a_managed_skill_changed_since_the_install(self):
        with open(self.h(".agents", "skills", "beta-flow", "SKILL.md"), "a") as handle:
            handle.write("A local edit.\n")
        statuses, failures = self.check()
        self.assert_only("managed skills", statuses, failures, "beta-flow 与上次 install 写入的内容不同")

    def test_gh_acting_as_another_account(self):
        statuses, failures = self.check(gh={"user": "Habit130"})
        self.assert_only("identity", statuses, failures, "gh 应以 agent account Habit098 操作，实际：Habit130")

    def test_git_committing_as_another_identity(self):
        support.write_tree(self.home, {".gitconfig": "[user]\n\temail = habit@example.com\n"})
        statuses, failures = self.check()
        self.assert_only("identity", statuses, failures, "git 的全局 commit 身份应是 %s，实际：habit@example.com" % ms.NOREPLY)

    def test_ghm_undefined(self):
        support.write_tree(self.home, {".zshrc": "# no ghm here\n"})
        statuses, failures = self.check()
        self.assert_only("identity", statuses, failures, "没有把 ghm 定义为 alias 或 function")


class CommentedKey(unittest.TestCase):
    """The detector reads the effective key, never a comment (#67's S-1, on the machine's wider surface)."""

    def test_shapes(self):
        from machinelib import skills

        cases = {
            b"policy:\n  allow_implicit_invocation: false\n": skills.FALSE,
            b"policy:\n  # allow_implicit_invocation: false\n  allow_implicit_invocation: true\n": skills.OTHER,
            b"# policy:\n#   allow_implicit_invocation: false\n": skills.ABSENT,
            b"policy:\n  allow_implicit_invocation: true # allow_implicit_invocation: false\n": skills.OTHER,
            b"policy: {allow_implicit_invocation: false}\n": skills.UNCLEAR,
            b"interface:\n  display_name: x\n": skills.ABSENT,
            b"policy:\n  allow_implicit_invocation: \"false\"\n": skills.OTHER,
            b"policy:\n  other: 1\n  nested:\n    allow_implicit_invocation: false\n": skills.OTHER,
        }
        for text, expected in cases.items():
            self.assertEqual(skills.codex_policy(text), expected, text)


if __name__ == "__main__":
    unittest.main()
