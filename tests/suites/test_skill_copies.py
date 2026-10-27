"""Skill copies (#44 §10, ADR 0020): refreshing, verifying and listing changes against an upstream.

A local repository stands in for `mattpocock/skills`, so no suite reaches the network. It holds
a model-invoked skill, a user-invoked skill without the Codex user-only key, which a refresh
adds, and a user-invoked skill that already carries it.
"""

import json
import os
import unittest

import support

SCRIPTS = os.path.join(support.REPO, "skill-copies", "scripts")
REFRESH = os.path.join(SCRIPTS, "refresh.py")
VERIFY = os.path.join(SCRIPTS, "verify.py")
CHANGES = os.path.join(SCRIPTS, "changes.py")

KEY = "policy:\n  allow_implicit_invocation: false\n"

UPSTREAM = {
    "LICENSE": "MIT License\n\nCopyright (c) 2026 Upstream\n",
    "README.md": "# Upstream\n",
    "skills/engineering/alpha/SKILL.md": "---\nname: alpha\ndescription: Alpha does things.\n---\n\n# Alpha\n",
    "skills/engineering/alpha/agents/openai.yaml": 'interface:\n  display_name: "Alpha"\n',
    "skills/engineering/alpha/REFERENCE.md": "Reference.\n",
    "skills/engineering/alpha/scripts/loop.sh": {"content": "#!/usr/bin/env bash\necho loop\n", "mode": "100755"},
    "skills/engineering/gated/SKILL.md": (
        "---\nname: gated\ndescription: Only habit starts it.\ndisable-model-invocation: true\n---\n\n# Gated\n"
    ),
    "skills/engineering/gated/agents/openai.yaml": 'interface:\n  display_name: "Gated"\n',
    "skills/productivity/keyed/SKILL.md": (
        "---\nname: keyed\ndescription: Keyed already.\ndisable-model-invocation: true\n---\n\n# Keyed\n"
    ),
    "skills/productivity/keyed/agents/openai.yaml": 'interface:\n  display_name: "Keyed"\n' + KEY,
    "skills/productivity/unrelied/SKILL.md": "---\nname: unrelied\ndescription: Not relied on.\n---\n",
}

RELIED_ON = ["alpha", "gated", "keyed"]


def manifest(skills):
    return json.dumps({"version": 1, "templates": [], "relied_on_skills": skills, "labels": []}) + "\n"


class SkillCopiesCase(support.TempDirCase):
    def setUp(self):
        super(SkillCopiesCase, self).setUp()
        self.upstream = support.init_repo(self.path("upstream"))
        self.first = support.commit_tree(self.upstream, UPSTREAM, "first")
        self.store = self.path("store")
        support.write_tree(self.store, {"1/manifest.json": manifest(RELIED_ON)})
        self.copies = self.path("skill-copies")
        os.makedirs(self.copies)

    def refresh(self, commit=None, store=None):
        return support.run_cli(
            REFRESH,
            ["--commit", commit or self.first, "--upstream", self.upstream, "--copies", self.copies,
             "--store", store or self.store],
        )

    def verify(self):
        return support.run_cli(VERIFY, ["--upstream", self.upstream, "--copies", self.copies])

    def copy_path(self, *parts):
        return os.path.join(self.copies, *parts)

    def provenance(self):
        with open(self.copy_path("provenance.json")) as handle:
            return json.load(handle)

    def write_provenance(self, data):
        with open(self.copy_path("provenance.json"), "w") as handle:
            json.dump(data, handle, indent=2)
            handle.write("\n")

    def flip_last_byte(self, *parts):
        path = self.copy_path(*parts)
        with open(path, "rb") as handle:
            data = handle.read()
        with open(path, "wb") as handle:
            handle.write(data[:-1] + (b"X" if data[-1:] != b"X" else b"Y"))


class Refreshing(SkillCopiesCase):
    def test_copies_each_relied_on_skill_whole_with_the_license_and_provenance(self):
        code, out, err = self.refresh()
        self.assertEqual(code, 0, out + err)
        self.assertEqual(sorted(os.listdir(self.copy_path("skills"))), RELIED_ON)
        self.assertEqual(
            support.read_text(self.copy_path("skills", "alpha", "REFERENCE.md")), "Reference.\n"
        )
        self.assertEqual(support.file_mode(self.copy_path("skills", "alpha", "scripts", "loop.sh")), "100755")
        self.assertEqual(support.read_text(self.copy_path("LICENSE")), UPSTREAM["LICENSE"])
        self.assertFalse(os.path.exists(self.copy_path("skills", "unrelied")))
        self.assertEqual(
            self.provenance(),
            {
                "license": {"repository": "mattpocock/skills", "path": "LICENSE", "commit": self.first},
                "copies": [
                    {"name": "alpha", "repository": "mattpocock/skills", "path": "skills/engineering/alpha",
                     "commit": self.first, "codex_key_added": False},
                    {"name": "gated", "repository": "mattpocock/skills", "path": "skills/engineering/gated",
                     "commit": self.first, "codex_key_added": True},
                    {"name": "keyed", "repository": "mattpocock/skills", "path": "skills/productivity/keyed",
                     "commit": self.first, "codex_key_added": False},
                ],
            },
        )

    def test_adds_the_codex_key_only_to_a_user_invoked_skill_that_lacks_it(self):
        self.refresh()
        self.assertEqual(
            support.read_text(self.copy_path("skills", "gated", "agents", "openai.yaml")),
            UPSTREAM["skills/engineering/gated/agents/openai.yaml"] + KEY,
        )
        self.assertEqual(
            support.read_text(self.copy_path("skills", "keyed", "agents", "openai.yaml")),
            UPSTREAM["skills/productivity/keyed/agents/openai.yaml"],
        )
        self.assertEqual(
            support.read_text(self.copy_path("skills", "alpha", "agents", "openai.yaml")),
            UPSTREAM["skills/engineering/alpha/agents/openai.yaml"],
        )

    def test_a_second_refresh_replaces_the_copies_and_drops_a_skill_no_longer_relied_on(self):
        self.refresh()
        support.write_tree(self.store, {"1/manifest.json": manifest(["alpha", "keyed"])})
        code, out, err = self.refresh()
        self.assertEqual(code, 0, out + err)
        self.assertEqual(sorted(os.listdir(self.copy_path("skills"))), ["alpha", "keyed"])
        self.assertEqual([c["name"] for c in self.provenance()["copies"]], ["alpha", "keyed"])

    def test_refuses_a_relied_on_skill_missing_at_the_commit_and_writes_nothing(self):
        support.write_tree(self.store, {"1/manifest.json": manifest(["alpha", "absent"])})
        code, out, err = self.refresh()
        self.assertEqual(code, 2, out + err)
        self.assertIn("absent", out + err)
        self.assertEqual(os.listdir(self.copies), [])

    def test_refuses_a_user_invoked_skill_without_its_codex_file(self):
        files = dict(UPSTREAM)
        del files["skills/engineering/gated/agents/openai.yaml"]
        commit = support.commit_tree(self.upstream, files, "no codex file")
        code, out, err = self.refresh(commit)
        self.assertEqual(code, 2, out + err)
        self.assertIn("gated", out + err)
        self.assertIn("agents/openai.yaml", out + err)

    def test_refuses_upstream_bytes_stored_form_would_refuse(self):
        files = dict(UPSTREAM)
        files["skills/engineering/alpha/AGENTS.md.stored"] = "x\n"
        commit = support.commit_tree(self.upstream, files, "undecodable name")
        code, out, err = self.refresh(commit)
        self.assertEqual(code, 2, out + err)
        self.assertIn("AGENTS.md.stored", out + err)

    def test_stores_a_loaded_name_and_a_dot_segment_in_stored_form(self):
        files = dict(UPSTREAM)
        files["skills/engineering/alpha/.hidden/CLAUDE.md"] = "nested\n"
        commit = support.commit_tree(self.upstream, files, "loaded name")
        code, out, err = self.refresh(commit)
        self.assertEqual(code, 0, out + err)
        self.assertTrue(os.path.isfile(self.copy_path("skills", "alpha", "dot-hidden", "CLAUDE.md.stored")))
        code, out, err = self.verify()
        self.assertEqual(code, 0, out + err)


class Verifying(SkillCopiesCase):
    def setUp(self):
        super(Verifying, self).setUp()
        code, out, err = self.refresh()
        self.assertEqual(code, 0, out + err)

    def test_passes_byte_identical_copies_and_lists_each_added_key(self):
        code, out, err = self.verify()
        self.assertEqual(code, 0, out + err)
        self.assertIn("PASS copy alpha:", out)
        self.assertIn("PASS copy keyed:", out)
        self.assertIn("PASS license:", out)
        self.assertIn("added Codex key: gated", out)
        self.assertNotIn("added Codex key: keyed", out)
        self.assertNotIn("FAIL", out)

    def test_fails_on_a_planted_one_byte_change_naming_the_file(self):
        self.flip_last_byte("skills", "alpha", "REFERENCE.md")
        code, out, err = self.verify()
        self.assertEqual(code, 1, out + err)
        self.assertIn("FAIL copy alpha:", out)
        self.assertIn("REFERENCE.md", out)
        self.assertIn("PASS copy keyed:", out)

    def test_fails_on_a_one_byte_change_to_the_license(self):
        self.flip_last_byte("LICENSE")
        code, out, err = self.verify()
        self.assertEqual(code, 1, out + err)
        self.assertIn("FAIL license:", out)

    def test_fails_on_a_change_beside_the_added_key(self):
        self.flip_last_byte("skills", "gated", "agents", "openai.yaml")
        code, out, err = self.verify()
        self.assertEqual(code, 1, out + err)
        self.assertIn("FAIL copy gated:", out)

    def test_fails_on_an_extra_or_a_missing_file_and_a_changed_mode(self):
        support.write_tree(self.copies, {"skills/keyed/EXTRA.md": "extra\n"})
        os.remove(self.copy_path("skills", "alpha", "REFERENCE.md"))
        os.chmod(self.copy_path("skills", "alpha", "scripts", "loop.sh"), 0o644)
        code, out, err = self.verify()
        self.assertEqual(code, 1, out + err)
        self.assertIn("EXTRA.md", out)
        self.assertIn("REFERENCE.md", out)
        self.assertIn("loop.sh", out)

    def test_fails_when_a_user_invoked_copy_lacks_the_key(self):
        with open(self.copy_path("skills", "gated", "agents", "openai.yaml"), "w") as handle:
            handle.write(UPSTREAM["skills/engineering/gated/agents/openai.yaml"])
        data = self.provenance()
        data["copies"][1]["codex_key_added"] = False
        self.write_provenance(data)
        code, out, err = self.verify()
        self.assertEqual(code, 1, out + err)
        self.assertIn("FAIL copy gated:", out)
        self.assertIn("Codex", out)

    def test_fails_when_the_key_is_recorded_as_added_where_upstream_has_it(self):
        data = self.provenance()
        data["copies"][2]["codex_key_added"] = True
        self.write_provenance(data)
        code, out, err = self.verify()
        self.assertEqual(code, 1, out + err)
        self.assertIn("FAIL copy keyed:", out)

    def test_fails_when_provenance_and_the_copies_on_disk_disagree(self):
        support.write_tree(self.copies, {"skills/stray/SKILL.md": "stray\n"})
        data = self.provenance()
        data["copies"] = [c for c in data["copies"] if c["name"] != "keyed"]
        self.write_provenance(data)
        code, out, err = self.verify()
        self.assertEqual(code, 1, out + err)
        self.assertIn("stray", out)
        self.assertIn("keyed", out)

    def test_refuses_a_commit_upstream_does_not_have(self):
        data = self.provenance()
        data["license"]["commit"] = "0" * 40
        self.write_provenance(data)
        code, out, err = self.verify()
        self.assertEqual(code, 2, out + err)


class ChangeList(SkillCopiesCase):
    def setUp(self):
        super(ChangeList, self).setUp()
        self.refresh()
        newer = dict(UPSTREAM)
        newer["skills/engineering/alpha/SKILL.md"] = (
            "---\nname: alpha\ndescription: Alpha does more.\n---\n\n# Alpha\n"
        )
        newer["skills/engineering/alpha/NEW.md"] = "one\ntwo\nthree\n"
        del newer["skills/engineering/alpha/scripts/loop.sh"]
        del newer["skills/productivity/keyed/SKILL.md"]
        del newer["skills/productivity/keyed/agents/openai.yaml"]
        newer["skills/engineering/keyed/SKILL.md"] = "---\nname: keyed\ndescription: Keyed already.\n---\n\n# Keyed\n"
        newer["skills/engineering/keyed/agents/openai.yaml"] = UPSTREAM["skills/productivity/keyed/agents/openai.yaml"]
        newer["README.md"] = "# Upstream, changed outside every skill\n"
        self.second = support.commit_tree(self.upstream, newer, "second")

    def changes(self, *args):
        return support.run_cli(CHANGES, ["--upstream", self.upstream, "--copies", self.copies] + list(args))

    def test_lists_what_changed_per_skill_in_chinese_from_the_recorded_commit(self):
        code, out, err = self.changes("--to", self.second)
        self.assertEqual(code, 0, out + err)
        self.assertIn("%s 到 %s" % (self.first[:12], self.second[:12]), out)
        self.assertIn("3 个 skill 中 2 个有变化", out)
        alpha = out.split("- alpha：", 1)[1].split("\n- ", 1)[0]
        self.assertIn("用途说明（description）改为：“Alpha does more.”", alpha)
        self.assertIn("SKILL.md 有改动：增加 1 行，删除 1 行", alpha)
        self.assertIn("新增文件 NEW.md（3 行）", alpha)
        self.assertIn("删除文件 scripts/loop.sh", alpha)
        keyed = out.split("- keyed：", 1)[1]
        self.assertIn("位置从 skills/productivity/keyed 移到 skills/engineering/keyed", keyed)
        self.assertIn("模型也能自行调用", keyed)
        self.assertIn("无变化：gated。", out)
        self.assertIn("LICENSE：无变化", out)
        self.assertNotIn("README", out)

    def test_a_skill_gone_at_the_newer_commit_is_named_for_a_decision(self):
        files = dict(UPSTREAM)
        del files["skills/engineering/gated/SKILL.md"]
        del files["skills/engineering/gated/agents/openai.yaml"]
        files["LICENSE"] = UPSTREAM["LICENSE"] + "More.\n"
        newer = support.commit_tree(self.upstream, files, "gated dropped")
        code, out, err = self.changes("--to", newer)
        self.assertEqual(code, 0, out + err)
        self.assertIn("- gated：在新提交中找不到", out)
        self.assertIn("LICENSE：有改动", out)

    def test_a_skill_becoming_user_invoked_names_the_key_it_needs(self):
        files = dict(UPSTREAM)
        files["skills/engineering/alpha/SKILL.md"] = (
            "---\nname: alpha\ndescription: Alpha does things.\ndisable-model-invocation: true\n---\n\n# Alpha\n"
        )
        newer = support.commit_tree(self.upstream, files, "alpha user-invoked")
        code, out, err = self.changes("--to", newer)
        self.assertEqual(code, 0, out + err)
        self.assertIn("改为只由 habit 调用", out)
        self.assertIn("Codex", out)

    def test_takes_another_older_commit_in_the_recorded_ones_place(self):
        code, out, err = self.changes("--from", self.first, "--to", self.second)
        self.assertEqual(code, 0, out + err)
        self.assertIn("2 个有变化", out)

    def test_refuses_a_commit_that_is_not_newer(self):
        code, out, err = self.changes("--from", self.second, "--to", self.first)
        self.assertEqual(code, 2, out + err)
        self.assertIn("REFUSED", out)


class CopiesCheck(support.TempDirCase):
    """CRIT-6: CI fails when the copies' names and the version manifest's relied-on list disagree."""

    COMMIT = "a" * 40

    def check(self, repo):
        return support.run_cli(support.RUN, ["copies", "--repo", repo])

    def plant(self, relied_on, on_disk, listed=None, commits=None):
        listed = on_disk if listed is None else listed
        commits = commits or {}
        repo = support.init_repo(self.path("repo"))
        files = {
            "generator/govern-repository/store/1/manifest.json": manifest(relied_on),
            "skill-copies/LICENSE": "MIT\n",
            "skill-copies/scripts/verify.py": "# not a copy\n",
            "skill-copies/provenance.json": json.dumps(
                {
                    "license": {"repository": "mattpocock/skills", "path": "LICENSE", "commit": self.COMMIT},
                    "copies": [
                        {"name": name, "repository": "mattpocock/skills", "path": "skills/engineering/" + name,
                         "commit": commits.get(name, self.COMMIT), "codex_key_added": False}
                        for name in listed
                    ],
                }
            ),
        }
        for name in on_disk:
            files["skill-copies/skills/%s/SKILL.md" % name] = "---\nname: %s\n---\n" % name
        support.write_tree(repo, files)
        support.git(repo, "add", "-A")
        return repo

    def test_passes_the_real_repository(self):
        code, out, err = self.check(support.REPO)
        self.assertEqual(code, 0, out + err)
        self.assertIn("PASS copies:", out)

    def test_passes_agreeing_names_without_counting_the_license_or_the_scripts(self):
        code, out, err = self.check(self.plant(["alpha", "gated", "govern-repository"], ["alpha", "gated"]))
        self.assertEqual(code, 0, out + err)
        self.assertIn("PASS copies: 2 copies", out)

    def test_fails_on_a_copy_the_relied_on_list_lacks(self):
        code, out, err = self.check(self.plant(["alpha"], ["alpha", "stray"]))
        self.assertEqual(code, 1, out + err)
        self.assertIn("FAIL copies:", out)
        self.assertIn("stray", out)

    def test_fails_on_a_relied_on_skill_without_a_copy(self):
        code, out, err = self.check(self.plant(["alpha", "gated"], ["alpha"], listed=["alpha", "gated"]))
        self.assertEqual(code, 1, out + err)
        self.assertIn("gated", out)

    def test_fails_when_provenance_lists_other_names(self):
        code, out, err = self.check(self.plant(["alpha", "gated"], ["alpha", "gated"], listed=["alpha"]))
        self.assertEqual(code, 1, out + err)
        self.assertIn("provenance", out)
        self.assertIn("gated", out)

    def test_fails_when_the_copies_come_from_more_than_one_commit(self):
        repo = self.plant(["alpha", "gated"], ["alpha", "gated"], commits={"gated": "b" * 40})
        code, out, err = self.check(repo)
        self.assertEqual(code, 1, out + err)
        self.assertIn("one upstream commit", out)


if __name__ == "__main__":
    unittest.main()
