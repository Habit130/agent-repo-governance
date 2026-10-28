"""Seam C, the install (#44 §8, Testing Decisions): every install fixture, the ready command and the machine rules."""

import json
import os
import subprocess
import unittest

import machine_support as ms
import support
from standins import environment


class InstallCase(support.TempDirCase):
    def setUp(self):
        super(InstallCase, self).setUp()
        self.source = self.path("source")
        self.commit = ms.build_source(self.source)
        self.home = ms.ready_home(self.path("home"))
        self.runs = 0

    def env(self, gh=None, codex_recording=None, extra=None):
        self.runs += 1
        scratch = self.path("scratch-%d" % self.runs)
        os.makedirs(scratch)
        self.scratch = scratch
        gh = gh or ms.write_gh_recording(os.path.join(scratch, "gh.json"))
        return ms.machine_env(self.home, scratch, gh_recording=gh, codex_recording=codex_recording, extra=extra)

    def install(self, env=None, codex=None):
        env = env or self.env()
        args = ["install", "--source", self.source, "--home", self.home]
        if codex:
            args += ["--codex", codex]
        code, out, err = ms.run_machine(args, env)
        self.assertEqual(err, "", out)
        self.assertFalse(ms.ghm_called(self.scratch), "ghm was called")
        return code, out

    def h(self, *parts):
        return os.path.join(self.home, *parts)

    def read(self, *parts):
        return support.read_text(self.h(*parts))

    def write(self, files):
        support.write_tree(self.home, files)

    def notes(self, out, subject):
        return [detail for _, s, detail in ms.lines("\n".join(ms.section(out, "install %s" % self.commit))) if s == subject]

    def check(self, out):
        return ms.statuses(out, "machine check")


class FreshMachine(InstallCase):
    """A fresh machine, with the Codex stand-in replaying real output (CRIT-1, CRIT-3, CRIT-4)."""

    def test_installs_every_step_and_passes_the_check(self):
        recording = ms.merge_codex_recordings(self.path("codex.json"), "codex-execpolicy.json", "codex-prompt-input-ready.json")
        env = self.env(codex_recording=recording)
        for name in ("HOME", "XDG_CONFIG_HOME", "XDG_STATE_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "TMPDIR", "CODEX_HOME"):
            self.assertTrue(env[name].startswith(self.home), name)
        code, out = self.install(env, codex=ms.STANDIN_CODEX)
        self.assertEqual(code, 0, out)
        self.assertEqual(set(self.check(out).values()), {"通过"}, out)

        # 1. Machine skills: copies decoded, the generator copied whole in stored form.
        self.assertEqual(sorted(os.listdir(self.h(".agents", "skills"))), ms.MACHINE_NAMES)
        self.assertEqual(self.read(".agents", "skills", "alpha-check", ".notes", "kept.md"), "A stored dot segment, decoded at install.\n")
        generator = self.h(".agents", "skills", "govern-repository")
        self.assertTrue(os.path.isfile(os.path.join(generator, "store", "1", "templates", "dot-github", "governance", "record.yml")))
        self.assertFalse(os.path.exists(os.path.join(generator, "store", "1", "templates", ".github")))
        # 2. Machine rules.
        claude = json.loads(self.read(".claude", "settings.json"))
        self.assertEqual(claude, {"permissions": {"deny": ["Bash(ghm *)", "Bash(gh secret set *)", "Bash(gh secret delete *)", "Bash(gh secret remove *)"]}})
        opencode = json.loads(self.read(".config", "opencode", "opencode.json"))
        self.assertEqual(opencode, {"permission": {"bash": {p: "deny" for p in ("ghm", "ghm *", "gh secret set *", "gh secret delete *", "gh secret remove *")}}})
        self.assertIn('pattern = ["ghm"]', self.read(".codex", "rules", "governance.rules"))
        calls = environment.read_log(self.scratch)
        policy = [c["args"][4:] for c in calls if c["tool"] == "codex" and c["args"][:2] == ["execpolicy", "check"]]
        self.assertIn(["gh", "secret", "list"], policy)
        self.assertTrue(all(c["recorded"] for c in calls), [c for c in calls if not c["recorded"]])
        self.assertIn("[通过] Codex rules：`codex execpolicy check` 验证通过", out)
        # 3. Links.
        for path, target in ((".claude/skills", ".agents/skills"), (".claude/CLAUDE.md", ".agents/AGENTS.md"),
                             (".config/opencode/AGENTS.md", ".agents/AGENTS.md"), (".codex/AGENTS.md", ".agents/AGENTS.md")):
            self.assertTrue(os.path.islink(self.h(path)), path)
            self.assertEqual(os.path.realpath(self.h(path)), self.h(target))
        # 4. Installed state, and the machine tools.
        state = json.loads(self.read(".agents", "governance", "installed.json"))
        self.assertEqual(state["commit"], self.commit)
        self.assertEqual(sorted(state["skills"]), ms.MACHINE_NAMES)
        self.assertTrue(os.path.isfile(self.h(".agents", "governance", "machine", "scripts", "machine.py")))
        self.assertFalse(os.path.exists(self.h(".agents", "governance", "staging")))
        # 5 to 7. The check, the list and the upstream report ran.
        self.assertIn("== governed-repository list", out)
        self.assertIn("[说明] upstream：mattpocock/skills 没有比 111111111111 更新的 commit", out)

    def test_a_rerun_writes_nothing_new(self):
        self.install()
        before = ms.snapshot(self.home)
        code, out = self.install()
        self.assertEqual(code, 0, out)
        self.assertEqual(ms.snapshot(self.home), before)
        self.assertEqual(self.notes(out, "Claude Code settings") + self.notes(out, "machine skills")[:-1], [])

    def test_codex_absent_skips_and_reports(self):
        code, out = self.install(codex=self.path("no-codex"))
        self.assertEqual(code, 0, out)
        self.assertIn("[跳过] Codex rules：没有找到 Codex CLI，未用 `codex execpolicy check` 验证", out)
        self.assertEqual(self.check(out)["Codex skill list"], "跳过")
        self.assertTrue(os.path.isfile(self.h(".codex", "rules", "governance.rules")))

    def test_the_installed_check_and_list_run_on_their_own(self):
        self.install()
        entry = self.h(".agents", "governance", "machine", "scripts", "machine.py")
        env = self.env()
        for command in ("check", "list"):
            result = subprocess.run(["/usr/bin/python3" if os.path.exists("/usr/bin/python3") else "python3", entry, command],
                                    env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            self.assertEqual((result.returncode, result.stderr), (0, ""), result.stdout)
        code, out, _ = ms.run_machine(["check"], env)
        self.assertEqual(self.check(out)["managed skills"], "通过", out)
        self.assertEqual([p for p in ms.snapshot(self.home) if "__pycache__" in p], [])

    def test_the_real_copies_install(self):
        real = self.path("real-source")
        support.init_repo(real)
        files = ms.source_files()
        files = {path: spec for path, spec in files.items() if not path.startswith("skill-copies/")}
        for rel, spec in ms._tree(os.path.join(support.REPO, "skill-copies")).items():
            files["skill-copies/%s" % rel] = spec
        commit = support.commit_tree(real, files, "real copies")
        code, out, err = ms.run_machine(["install", "--source", real, "--home", self.home], self.env())
        self.assertEqual((code, err), (0, ""), out)
        state = json.loads(self.read(".agents", "governance", "installed.json"))
        expected = sorted(os.listdir(os.path.join(support.REPO, "skill-copies", "skills"))) + ["govern-repository"]
        self.assertEqual((state["commit"], sorted(state["skills"])), (commit, sorted(expected)))
        self.assertEqual(self.check(out)["Codex user-only key"], "通过", out)


class SkillsTakenOver(InstallCase):
    LOCK = {
        "version": 3,
        "skills": {
            name: {"source": "mattpocock/skills", "sourceType": "github", "sourceUrl": "https://github.com/mattpocock/skills.git",
                   "skillPath": "skills/x/%s/SKILL.md" % name, "skillFolderHash": "0" * 40,
                   "installedAt": "2026-10-16T00:00:00.000Z", "updatedAt": "2026-10-16T00:00:00.000Z"}
            for name in ("alpha-check", "beta-flow", "grill-me")
        },
        "dismissed": {"findSkillsPrompt": True},
    }

    def plant(self, lock_path):
        self.write({
            ".agents/skills/alpha-check/SKILL.md": ms.COPIES["alpha-check"]["SKILL.md"],
            ".agents/skills/alpha-check/.notes/kept.md": ms.COPIES["alpha-check"]["dot-notes/kept.md"],
            ".agents/skills/beta-flow/SKILL.md": "---\nname: beta-flow\ndescription: An older upstream text.\n---\n",
            ".agents/skills/grill-me/SKILL.md": "---\nname: grill-me\ndescription: Stays with npx skills.\n---\n",
            lock_path: json.dumps(self.LOCK, indent=2) + "\n",
        })

    def assert_taken_over(self, lock_path, out):
        lock = json.loads(self.read(*lock_path.split("/")))
        self.assertEqual(sorted(lock["skills"]), ["grill-me"])
        self.assertEqual(lock["dismissed"], {"findSkillsPrompt": True})
        self.assertEqual(lock["version"], 3)
        self.assertTrue(self.read(*lock_path.split("/")).endswith("}\n"))
        notes = self.notes(out, "machine skills")
        self.assertIn("接管同名 skill beta-flow：内容不同，已替换", notes)
        self.assertFalse(any("alpha-check" in n for n in notes[:-1]), notes)
        self.assertEqual(self.read(".agents", "skills", "beta-flow", "SKILL.md"), ms.COPIES["beta-flow"]["SKILL.md"])
        self.assertEqual(self.read(".agents", "skills", "grill-me", "SKILL.md"), "---\nname: grill-me\ndescription: Stays with npx skills.\n---\n")
        backups = [n for n in os.listdir(os.path.dirname(self.h(lock_path))) if ".governance-backup-" in n]
        self.assertEqual(len(backups), 1)
        self.assertIn("已从 ~/%s 移除被接管的条目：alpha-check、beta-flow" % lock_path, " ".join(self.notes(out, "lock file")))

    def test_skills_cli_installs_are_taken_over_and_their_lock_entries_removed(self):
        lock = ".local/state/skills/.skill-lock.json"
        self.plant(lock)
        code, out = self.install()
        self.assertEqual(code, 0, out)
        self.assert_taken_over(lock, out)

    def test_without_xdg_state_home_the_lock_is_under_agents(self):
        lock = ".agents/.skill-lock.json"
        self.plant(lock)
        env = self.env()
        del env["XDG_STATE_HOME"]
        code, out = self.install(env)
        self.assertEqual(code, 0, out)
        self.assert_taken_over(lock, out)

    def test_a_managed_skill_overwritten_after_an_install_is_restored_and_listed(self):
        self.install()
        self.write({".agents/skills/alpha-check/SKILL.md": "---\nname: alpha-check\ndescription: Overwritten by npx skills.\n---\n"})
        code, out = self.install()
        self.assertEqual(code, 0, out)
        self.assertIn("alpha-check 在上次 install 后被改动或删除，已恢复", self.notes(out, "machine skills"))
        self.assertEqual(self.read(".agents", "skills", "alpha-check", "SKILL.md"), ms.COPIES["alpha-check"]["SKILL.md"])
        self.assertEqual(self.check(out)["managed skills"], "通过")

    def test_a_skill_dropped_from_the_set_is_removed(self):
        self.install()
        copies = {"alpha-check": ms.COPIES["alpha-check"]}
        self.commit = support.commit_tree(self.source, ms.source_files(copies), "drop beta-flow")
        code, out = self.install()
        self.assertEqual(code, 0, out)
        self.assertIn("beta-flow 已不在 machine skill set 里，已移除", self.notes(out, "machine skills"))
        self.assertFalse(any("本地改动" in n for n in self.notes(out, "machine skills")))
        self.assertFalse(os.path.lexists(self.h(".agents", "skills", "beta-flow")))
        state = json.loads(self.read(".agents", "governance", "installed.json"))
        self.assertEqual(sorted(state["skills"]), ["alpha-check", "govern-repository"])


    def test_a_dropped_skill_with_local_edits_says_so(self):
        self.install()
        with open(self.h(".agents", "skills", "beta-flow", "SKILL.md"), "a") as handle:
            handle.write("habit's edit.\n")
        self.commit = support.commit_tree(self.source, ms.source_files({"alpha-check": ms.COPIES["alpha-check"]}), "drop beta-flow")
        code, out = self.install()
        self.assertIn("beta-flow 已不在 machine skill set 里，已移除（它在上次 install 后有本地改动）", self.notes(out, "machine skills"))


class PersonalSkills(InstallCase):
    def test_a_personal_skill_sharing_a_machine_skills_name_is_kept_and_reported(self):
        personal = "---\nname: alpha-check\ndescription: habit's own alpha.\n---\n"
        self.write({".agents/skills/my-alpha/SKILL.md": personal, ".config/opencode/skills/beta-flow/SKILL.md": personal})
        code, out = self.install()
        self.assertEqual(code, 1, out)
        self.assertEqual(self.read(".agents", "skills", "my-alpha", "SKILL.md"), personal)
        failures = [d for s, subject, d in ms.lines(out) if subject == "名称冲突" and s == "失败"]
        self.assertEqual(len(failures), 2, failures)
        self.assertIn("~/.agents/skills/my-alpha", failures[0])
        self.assertIn("~/.config/opencode/skills/beta-flow", failures[1])

    def test_a_linked_personal_skill_missing_the_codex_key_is_only_reported(self):
        target = self.path("elsewhere", "linked-flow")
        skill_md = "---\nname: linked-flow\ndescription: Linked.\ndisable-model-invocation: true\n---\n"
        support.write_tree(target, {"SKILL.md": skill_md})
        os.makedirs(self.h(".agents", "skills"))
        os.symlink(target, self.h(".agents", "skills", "linked-flow"))
        code, out = self.install()
        self.assertEqual(code, 0, out)
        self.assertEqual(os.listdir(target), ["SKILL.md"])
        self.assertEqual(self.notes(out, "Codex user-only key"), [])
        self.assertEqual(self.check(out)["Codex user-only key"], "通过")
        self.assertIn("[说明] Codex user-only key：personal skill linked-flow（链接） 缺少 Codex user-only key（只报告，不算失败）", out)

    def test_the_install_writes_nothing_inside_a_personal_skill_in_either_root(self):
        """CRIT-3, #69's S-2 to S-4: missing, quoted, spaced and commented keys, and links inside a skill."""
        flow = "---\nname: %s\ndescription: Personal.\ndisable-model-invocation: true\n---\n"
        keyless = 'interface:\n  display_name: "Shared"\n'
        external = self.path("dotfiles")
        roots = {".agents/skills": "agents", ".codex/skills": "codex"}
        files, targets = {}, {}
        for root, tag in sorted(roots.items()):
            for name, codex in (("plain", None), ("shown", keyless),
                                ("quoted", '"policy":\n  allow_implicit_invocation: true\n'),
                                ("spaced", "policy :\n  allow_implicit_invocation: true\n"),
                                ("commented", "policy:\n  # allow_implicit_invocation: false\n  allow_implicit_invocation: true\n"),
                                ("dirlink", None), ("filelink", None)):
                skill = "%s-%s" % (name, tag)
                files["%s/%s/SKILL.md" % (root, skill)] = flow % skill
                if codex is not None:
                    files["%s/%s/agents/openai.yaml" % (root, skill)] = codex
            targets[tag] = os.path.join(external, tag)
            support.write_tree(targets[tag], {"agents/openai.yaml": keyless, "openai.yaml": keyless})
        self.write(files)
        for root, tag in roots.items():
            os.symlink(os.path.join(targets[tag], "agents"), self.h(root, "dirlink-%s" % tag, "agents"))
            os.makedirs(self.h(root, "filelink-%s" % tag, "agents"))
            os.symlink(os.path.join(targets[tag], "openai.yaml"), self.h(root, "filelink-%s" % tag, "agents", "openai.yaml"))
        personal = sorted(self.h(root, name) for root in roots for name in os.listdir(self.h(root)))
        self.assertEqual(len(personal), 14)
        before = [ms.snapshot(path) for path in personal + [external]]

        code, out = self.install()
        self.assertEqual(code, 0, out)
        self.assertEqual([ms.snapshot(path) for path in personal + [external]], before)
        self.assertEqual(self.notes(out, "Codex user-only key"), [])
        self.assertNotIn("添加 Codex user-only key", out)
        self.assertEqual(self.check(out)["Codex user-only key"], "通过", out)
        noted = [d for s, subject, d in ms.lines(out) if subject == "Codex user-only key" and s == "说明"]
        self.assertEqual(len(noted), 14, noted)
        self.assertIn("personal skill ~/.codex/skills 里的 quoted-codex 缺少 Codex user-only key（只报告，不算失败）", noted)

    def test_a_machine_skills_name_under_codex_skills_is_reported(self):
        self.write({".codex/skills/alpha-check/SKILL.md": ms.COPIES["alpha-check"]["SKILL.md"]})
        code, out = self.install()
        self.assertEqual(code, 1, out)
        self.assertTrue(os.path.isfile(self.h(".codex", "skills", "alpha-check", "SKILL.md")))
        self.assertIn("[失败] 名称冲突：~/.codex/skills 里有 machine skill 的名称 alpha-check，Codex 会列出两次", out)


class GlobalFiles(InstallCase):
    def test_a_real_file_at_a_global_instruction_path_is_reported_never_overwritten(self):
        self.write({".codex/AGENTS.md": "Codex's own copy.\n"})
        code, out = self.install()
        self.assertEqual(code, 1, out)
        self.assertEqual(self.read(".codex", "AGENTS.md"), "Codex's own copy.\n")
        self.assertIn("~/.codex/AGENTS.md 是真实文件或目录，应链接到 ~/.agents/AGENTS.md；未覆盖", self.notes(out, "links"))
        self.assertTrue(os.path.islink(self.h(".claude", "CLAUDE.md")))
        self.assertEqual(self.check(out)["links"], "失败")

    def test_a_present_dsh_agents_md_is_reported_and_kept(self):
        self.write({".dsh/AGENTS.md": "dsh's copy.\n"})
        code, out = self.install()
        self.assertEqual(code, 1, out)
        self.assertEqual(self.read(".dsh", "AGENTS.md"), "dsh's copy.\n")
        self.assertIn("[失败] links：~/.dsh/AGENTS.md 存在，dsh 会把全局指令加载两次", out)

    def test_without_the_global_file_no_dangling_link_is_made(self):
        os.remove(self.h(".agents", "AGENTS.md"))
        code, out = self.install()
        self.assertFalse(os.path.lexists(self.h(".claude", "CLAUDE.md")))
        self.assertTrue(os.path.islink(self.h(".claude", "skills")))
        self.assertIn("~/.agents/AGENTS.md 不存在，未创建 ~/.claude/CLAUDE.md", self.notes(out, "links"))


class Settings(InstallCase):
    CLAUDE = {"permissions": {"defaultMode": "auto", "allow": ["Bash(ls *)"], "deny": ["Bash(rm -rf *)"]}, "model": "opus"}
    OPENCODE = {"$schema": "https://opencode.ai/config.json", "permission": {"bash": {"*": "ask", "git *": "allow"}}, "theme": "x"}

    def test_other_entries_are_kept_and_the_file_backed_up(self):
        claude_text = json.dumps(self.CLAUDE, indent=4)
        opencode_text = json.dumps(self.OPENCODE)
        self.write({".claude/settings.json": claude_text, ".config/opencode/opencode.json": opencode_text})
        code, out = self.install()
        self.assertEqual(code, 0, out)
        claude = json.loads(self.read(".claude", "settings.json"))
        self.assertEqual(claude["model"], "opus")
        self.assertEqual(claude["permissions"]["allow"], ["Bash(ls *)"])
        self.assertEqual(claude["permissions"]["defaultMode"], "auto")
        self.assertEqual(claude["permissions"]["deny"][0], "Bash(rm -rf *)")
        self.assertEqual(len(claude["permissions"]["deny"]), 5)
        opencode = json.loads(self.read(".config", "opencode", "opencode.json"))
        self.assertEqual(list(opencode["permission"]["bash"])[:2], ["*", "git *"])
        self.assertEqual(list(opencode["permission"]["bash"].values())[2:], ["deny"] * 5)
        self.assertEqual((opencode["$schema"], opencode["theme"]), (self.OPENCODE["$schema"], "x"))
        for directory, name, text in ((".claude", "settings.json", claude_text), (".config/opencode", "opencode.json", opencode_text)):
            backups = [n for n in os.listdir(self.h(directory)) if n.startswith(name + ".governance-backup-")]
            self.assertEqual(len(backups), 1, backups)
            self.assertEqual(self.read(directory, backups[0]), text)
        self.assertEqual(self.check(out)["deny entries"], "通过")
        before = ms.snapshot(self.home)
        self.install()
        self.assertEqual(ms.snapshot(self.home), before)

    def test_an_existing_entry_that_isnt_deny_is_reported_not_changed(self):
        self.write({".config/opencode/opencode.json": json.dumps({"permission": {"bash": {"ghm": "allow"}}})})
        code, out = self.install()
        opencode = json.loads(self.read(".config", "opencode", "opencode.json"))
        self.assertEqual(opencode["permission"]["bash"]["ghm"], "allow")
        self.assertIn("这些已有条目不是 deny，未改动：ghm = allow", self.notes(out, "OpenCode settings"))
        self.assertEqual((code, self.check(out)["deny entries"]), (1, "失败"))

    def test_an_unparseable_settings_file_is_reported_and_left_unwritten(self):
        jsonc = '{\n  // habit\'s comment\n  "permissions": {}\n}\n'
        self.write({".claude/settings.json": jsonc})
        code, out = self.install()
        self.assertEqual(code, 1, out)
        self.assertEqual(self.read(".claude", "settings.json"), jsonc)
        self.assertEqual([n for n in os.listdir(self.h(".claude")) if "backup" in n], [])
        self.assertTrue(any("无法解析" in n and "未写入" in n for n in self.notes(out, "Claude Code settings")), out)
        self.assertEqual(self.check(out)["deny entries"], "失败")


class ForwardOnly(InstallCase):
    def test_an_older_commit_is_refused_and_nothing_is_written(self):
        older = self.commit
        self.install()
        newer = support.commit_tree(self.source, dict(ms.source_files(), **{"machine/NOTE.txt": "newer\n"}), "newer")
        self.commit = newer
        self.install()
        support.git(self.source, "checkout", "-q", older)
        before = ms.snapshot(self.home)
        code, out = self.install()
        self.assertEqual(code, 2, out)
        self.assertIn("拒绝：本机已安装 %s，而源码树的 %s 不比它新" % (newer, older), out)
        self.assertEqual(ms.snapshot(self.home), before)

    def test_a_commit_outside_the_installed_commits_history_is_refused(self):
        self.install()
        support.git(self.source, "checkout", "-q", "--orphan", "other")
        support.commit_tree(self.source, ms.source_files(), "unrelated")
        code, out = self.install()
        self.assertEqual(code, 2, out)
        self.assertIn("不比它新（install 只向前移动）；install 未写入任何内容", out)


class ReadyCommand(InstallCase):
    def ready_line(self):
        with open(ms.READY) as handle:
            lines = [line for line in handle.read().splitlines() if line and not line.startswith("#")]
        self.assertEqual(len(lines), 1)
        return lines[0]

    def test_readme_and_build_quote_it_byte_for_byte_and_it_parses_under_bash(self):
        line = self.ready_line()
        for doc in ("README.md", os.path.join("docs", "agents", "build.md")):
            self.assertIn(line, support.read_text(os.path.join(support.REPO, doc)), doc)
        self.assertTrue(line.startswith("/bin/bash -c '") and line.endswith("'"))
        inner = line[len("/bin/bash -c '"):-1]
        for text, code in ((inner, 0), (inner + "; if then", 2)):
            result = subprocess.run(["/bin/bash", "-n", "-c", text], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(result.returncode, code, result.stderr)

    def origin(self):
        """A bare origin whose default branch is main, and a git config that sends the ready command there."""
        bare = self.path("origin.git")
        subprocess.run(["git", "clone", "-q", "--bare", self.source, bare], check=True, env=support.isolated_env())
        config = self.path("gitconfig")
        with open(config, "w") as handle:
            handle.write("[user]\n\temail = %s\n[url \"%s\"]\n\tinsteadOf = https://github.com/Habit130/agent-repo-governance.git\n"
                         % (ms.NOREPLY, bare))
        return bare, config

    def run_ready(self, config):
        env = self.env(extra={"GIT_CONFIG_GLOBAL": config})
        result = subprocess.run(["/bin/bash", "-c", self.ready_line()], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                universal_newlines=True, stdin=subprocess.DEVNULL)
        return result.returncode, result.stdout + result.stderr

    @unittest.skipUnless(os.path.exists("/usr/bin/python3"), "the ready command runs /usr/bin/python3, as on macOS")
    def test_it_installs_origins_default_branch_afresh_never_the_local_checkout(self):
        bare, config = self.origin()
        support.git(self.source, "checkout", "-q", "-b", "local-work")
        support.commit_tree(self.source, dict(ms.source_files(), **{"machine/NOTE.txt": "local only\n"}), "local work")
        code, out = self.run_ready(config)
        self.assertEqual(code, 0, out)
        state = json.loads(self.read(".agents", "governance", "installed.json"))
        self.assertEqual(state["commit"], self.commit)
        self.assertFalse(os.path.exists(self.h(".agents", "governance", "machine", "NOTE.txt")))
        self.assertEqual([n for n in os.listdir(self.h("tmp")) if n.startswith("tmp")], [], "the fetched tree was not removed")

    @unittest.skipUnless(os.path.exists("/usr/bin/python3"), "the ready command runs /usr/bin/python3, as on macOS")
    def test_it_refuses_an_origin_older_than_the_installed_state(self):
        bare, config = self.origin()
        newer = support.commit_tree(self.source, dict(ms.source_files(), **{"machine/NOTE.txt": "newer\n"}), "newer")
        self.commit = newer
        self.install()
        before = ms.snapshot(self.home)
        code, out = self.run_ready(config)
        self.assertNotEqual(code, 0, out)
        self.assertIn("不比它新（install 只向前移动）", out)
        self.assertEqual(ms.snapshot(self.home), before)


if __name__ == "__main__":
    unittest.main()
