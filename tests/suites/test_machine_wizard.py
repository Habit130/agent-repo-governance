"""The account wizard (#44 §8, #48), run through `machine.py wizard` in a throwaway home.

Every `gh` call reaches the stand-in GitHub, whose logins take effect in the throwaway home:
a login writes `standin-account` into the `GH_CONFIG_DIR` it ran under, a file real gh never
reads, and the next status read answers from it. `gh auth setup-git` appends gh's credential
section to the home's `~/.gitconfig`. Every `git` call goes through a logging shim to the
real git, whose global file is the home's. So the call log shows each step's calls, and a
second run finds the state the first one left.

Every answer the wizard reads carries a planted credential-shaped value, in fields it ignores
as well (`PLANTS`), and no test runs `ghm` or any `gh` inside a login shell: the macOS login
profile reorders PATH, and a real gh there could reach the keychain.
"""

import json
import os
import re
import shutil
import subprocess
import unittest

import machine_support as ms
import support
from standins import environment

AGENT, MAINTAINER, OTHER = "Habit098", "Habit130", "SomeoneElse"
IDS = {AGENT: ms.AGENT_ID, MAINTAINER: 2468, OTHER: 1357}
AGENT_SCOPES = "repo,read:org,gist,workflow"
HOST = ["--hostname", "github.com"]
STATUS = ["auth", "status"] + HOST + ["--active", "--json", "hosts"]
AGENT_LOGIN = ["auth", "login"] + HOST + ["--git-protocol", "https", "--web", "--scopes", AGENT_SCOPES]
MAINTAINER_LOGIN = ["auth", "login"] + HOST + ["--git-protocol", "https", "--web"]
SETUP_GIT = ["auth", "setup-git"] + HOST
UP_TO_MAINTAINER = [STATUS, AGENT_LOGIN, STATUS, SETUP_GIT, ["api", "user"], STATUS]
ALL_ACTING = ["agent account 登录", "git credential", "git commit 身份", "maintainer 配置", "ghm"]
STATE = "${GH_CONFIG_DIR}/standin-account"
ATTACHED = "stand-in login ran attached"
GH_HELPER = "!/opt/homebrew/bin/gh auth git-credential"


def credential_section(helper=GH_HELPER):
    """What `gh auth setup-git` writes for github.com: an empty reset, then gh's helper."""
    return '[credential "https://github.com"]\n\thelper = \n\thelper = %s\n' % helper


def _plant(n):
    return "ghp_" + ("PLANTED%02d" % n).ljust(36, "x")


PLANTS = [_plant(n) for n in range(12)]
WIZARD = os.path.join(ms.MACHINE, "wizard.sh")
REAL_GIT = shutil.which("git", path="/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin")


def status_entry(login, scopes="gist, read:org, repo, workflow", source="keyring", state="success"):
    return {"state": state, "active": True, "host": "github.com", "login": login, "tokenSource": source,
            "scopes": scopes, "gitProtocol": "https", "error": PLANTS[1], "token": PLANTS[2]}


def recording(path, agent_login=AGENT, maintainer_login=MAINTAINER, agent_exit=0, maintainer_exit=0, extra=(),
              helper=GH_HELPER):
    """The stand-in GitHub for the wizard: which account each login yields, or its failure."""
    calls = list(extra)
    calls.append({"args": STATUS, "when": [{"path": STATE, "absent": True}], "exit": 0,
                  "stdout": json.dumps({"hosts": {}, "note": PLANTS[0]}) + "\n",
                  "stderr": "You are not logged into any accounts on github.com %s\n" % PLANTS[3]})
    for login in (AGENT, MAINTAINER, OTHER):
        when = [{"path": STATE, "contains": login + "\n"}]
        calls.append({"args": STATUS, "when": when, "exit": 0, "stderr": PLANTS[4],
                      "stdout": json.dumps({"hosts": {"github.com": [status_entry(login)]}}) + "\n"})
        calls.append({"args": ["api", "user"], "when": when, "exit": 0, "stderr": PLANTS[5],
                      "stdout": json.dumps({"login": login, "id": IDS[login], "bio": PLANTS[6], "name": PLANTS[7]}) + "\n"})
    for args, login, code in ((AGENT_LOGIN, agent_login, agent_exit), (MAINTAINER_LOGIN, maintainer_login, maintainer_exit)):
        call = {"args": args, "exit": code, "stdout": "%s\n" % ATTACHED, "stderr": ""}
        if code == 0:
            call["effects"] = [{"path": STATE, "write": login + "\n"}]
        calls.append(call)
    calls.append({"args": SETUP_GIT, "exit": 0, "stdout": PLANTS[8], "stderr": PLANTS[9],
                  "effects": [{"path": "${HOME}/.gitconfig", "append": credential_section(helper)}]})
    with open(path, "w") as handle:
        json.dump({"description": "The account wizard's stand-in GitHub, written by test_machine_wizard.py.",
                   "tool": "gh", "calls": calls}, handle)
    return path


class WizardCase(support.TempDirCase):
    def setUp(self):
        super(WizardCase, self).setUp()
        self.home = ms.make_home(self.path("home"))
        self.runs = 0
        self.recording = recording(self.path("gh.json"))

    def env(self, path=None, extra=None):
        self.scratches = getattr(self, "scratches", 0) + 1
        scratch = self.path("scratch-%d" % self.scratches)
        env = ms.machine_env(self.home, scratch, gh_recording=self.recording, extra=extra)
        # The default gh configuration is the home's, as gh resolves it without the variable.
        env["GH_CONFIG_DIR"] = os.path.join(self.home, ".config", "gh")
        env.update(extra or {})  # after the stand-in environment, which drops token variables
        git_bin = os.path.join(scratch, "git-bin")
        os.makedirs(git_bin)
        shim = os.path.join(git_bin, "git")
        with open(shim, "w") as handle:
            handle.write(
                "#!/bin/bash\n\"$STANDIN_PYTHON\" -c 'import json, os, sys; "
                "open(os.environ[\"STANDIN_LOG\"], \"a\").write(json.dumps({\"tool\": \"git\", \"args\": sys.argv[1:], "
                "\"recorded\": True}) + \"\\n\")' \"$@\"\nexec '%s' \"$@\"\n" % REAL_GIT
            )
        os.chmod(shim, 0o755)
        tripwire, rest = env["PATH"].split(os.pathsep, 1)
        env["PATH"] = os.pathsep.join([tripwire, git_bin, rest]) if path is None else path(tripwire, git_bin, rest)
        return scratch, env

    def wizard(self, path=None, extra=None):
        """Run the wizard; return (exit code, stdout, the calls it made)."""
        self.runs += 1
        scratch, env = self.env(path, extra)
        code, out, err = ms.run_machine(["wizard", "--home", self.home], env)
        self.assertEqual(err, "", "the wizard wrote to stderr")
        self.assertFalse(ms.ghm_called(scratch), "the wizard called ghm")
        calls = environment.read_log(scratch)
        for call in calls:
            self.assertTrue(call["recorded"], "a call no recording answers: %r" % call)
            self.assertNotEqual(call["args"][:2], ["auth", "logout"])
            self.assertNotEqual(call["args"][:2], ["auth", "token"])
            self.assertNotIn("--insecure-storage", call["args"])
        for plant in PLANTS:
            self.assertNotIn(plant, out)
        return code, out, calls

    def gh_calls(self, calls):
        return [call["args"] for call in calls if call["tool"] == "gh"]

    def git_writes(self, calls):
        return [call["args"] for call in calls if call["tool"] == "git" and not any(a.startswith("--get") or a == "--list" for a in call["args"])]

    def steps(self, out):
        return [(status, subject) for status, subject, _ in ms.lines(out)]

    def read(self, rel):
        with open(os.path.join(self.home, rel)) as handle:
            return handle.read()


class Walkthrough(WizardCase):
    def test_a_fresh_home_ends_set_up_and_names_the_install(self):
        code, out, calls = self.wizard()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.steps(out), [
            ("通过", "前提"),
            ("已完成", "agent account 登录"),
            ("已完成", "git credential"),
            ("已完成", "git commit 身份"),
            ("已完成", "maintainer 配置"),
            ("已完成", "ghm"),
            ("通过", "identity"),
        ])
        self.assertEqual(self.gh_calls(calls), [
            STATUS, AGENT_LOGIN, STATUS, SETUP_GIT, ["api", "user"], STATUS, MAINTAINER_LOGIN, STATUS,
            ["api", "user"],
        ])
        # The logins ran attached: their output reached the terminal, in order, uncaptured.
        self.assertEqual(out.count(ATTACHED), 2)
        self.assertEqual(self.git_writes(calls), [
            ["config", "--global", "user.email", ms.NOREPLY],
            ["config", "--global", "user.name", AGENT],
        ])
        # The last message names the install and quotes the ready command.
        with open(ms.READY) as handle:
            ready = handle.read().splitlines()[-1]
        last = out.rstrip("\n").splitlines()
        self.assertIn("install", last[-2])
        self.assertEqual(last[-1], ready)
        with open(os.path.join(self.home, ".config", "gh", "standin-account")) as handle:
            self.assertEqual(handle.read(), AGENT + "\n")
        with open(os.path.join(self.home, ".config", "gh-maintainer", "standin-account")) as handle:
            self.assertEqual(handle.read(), MAINTAINER + "\n")

    def test_the_end_state_passes_the_machine_checks_identity_item(self):
        self.assertEqual(self.wizard()[0], 0)
        scratch, env = self.env()
        code, out, _ = ms.run_machine(["check", "--home", self.home], env)
        self.assertEqual(ms.statuses(out, "machine check")["identity"], "通过", out)
        self.assertFalse(ms.ghm_called(scratch))

    def test_ghm_takes_19s_form_and_the_profile_holds_no_token(self):
        self.assertEqual(self.wizard()[0], 0)
        profile = self.read(".zshrc")
        self.assertIn('GH_CONFIG_DIR="$HOME/.config/gh-maintainer"', profile)
        self.assertEqual(profile.count("gh auth token"), 1)
        definition = re.search(r"^ghm\(\) \{\n(.*?)^\}\n", profile, re.S | re.M)
        self.assertIsNotNone(definition, profile)
        self.assertIn("gh auth token --user Habit130", definition.group(1))
        self.assertIn('"$@"', definition.group(1))
        self.assertNotRegex(profile, r"gh[pousr]_[A-Za-z0-9]{36}")
        # zsh reads the block and names ghm a function, without running it.
        result = subprocess.run(["/bin/zsh", "-f", "-c", "source %s; whence -w ghm" % os.path.join(self.home, ".zshrc")],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
                                env={"HOME": self.home, "PATH": "/bin"})
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "ghm: function\n", ""))


class Command(WizardCase):
    """The one line habit runs (`machine/wizard.sh`), quoted in README.md and build.md."""

    def line(self):
        with open(WIZARD) as handle:
            lines = [line for line in handle.read().splitlines() if line and not line.startswith("#")]
        self.assertEqual(len(lines), 1)
        return lines[0]

    def test_readme_and_build_quote_it_byte_for_byte_and_it_parses_under_bash(self):
        line = self.line()
        for doc in ("README.md", os.path.join("docs", "agents", "build.md")):
            self.assertIn(line, support.read_text(os.path.join(support.REPO, doc)), doc)
        self.assertTrue(line.startswith("/bin/bash -c '") and line.endswith("'"))
        result = subprocess.run(["/bin/bash", "-n", "-c", line[len("/bin/bash -c '"):-1]], stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(os.path.exists("/usr/bin/python3"), "the command runs /usr/bin/python3, as on macOS")
    def test_it_runs_the_wizard_from_a_fresh_clone_of_origin(self):
        source = self.path("source")
        ms.build_source(source)
        bare = self.path("origin.git")
        subprocess.run(["git", "clone", "-q", "--bare", source, bare], check=True, env=support.isolated_env())
        # The clone's URL goes to the local origin, through an include the home's own gitconfig
        # carries, so the wizard's global writes still land in the home.
        support.write_tree(self.home, {".gitconfig": "[include]\n\tpath = %s\n" % self.path("redirect")})
        with open(self.path("redirect"), "w") as handle:
            handle.write('[url "%s"]\n\tinsteadOf = https://github.com/Habit130/agent-repo-governance.git\n' % bare)
        scratch, env = self.env()
        result = subprocess.run(["/bin/bash", "-c", self.line()], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                universal_newlines=True, stdin=subprocess.DEVNULL)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(result.stdout.startswith("== account wizard\n"), result.stdout)
        self.assertIn("下一步：install", result.stdout)
        self.assertEqual([n for n in os.listdir(os.path.join(self.home, "tmp")) if n.startswith("tmp")], [],
                         "the cloned tree was not removed")
        self.assertIn(["clone", "--quiet", "--depth", "1", "https://github.com/Habit130/agent-repo-governance.git"],
                      [call["args"][:5] for call in environment.read_log(scratch) if call["tool"] == "git"])


class Rerun(WizardCase):
    def test_a_second_run_finds_every_step_in_place_and_changes_nothing(self):
        self.assertEqual(self.wizard()[0], 0)
        before = ms.snapshot(self.home)
        code, out, calls = self.wizard()
        self.assertEqual(code, 0, out)
        self.assertEqual(ms.snapshot(self.home), before)
        self.assertEqual(self.steps(out), [
            ("通过", "前提"),
            ("已就绪", "agent account 登录"),
            ("已就绪", "git credential"),
            ("已就绪", "git commit 身份"),
            ("已就绪", "maintainer 配置"),
            ("已就绪", "ghm"),
            ("通过", "identity"),
        ])
        # Only reads: no login, no setup-git, no git write.
        self.assertEqual(self.gh_calls(calls), [STATUS, ["api", "user"], STATUS, ["api", "user"]])
        self.assertEqual(self.git_writes(calls), [])
        self.assertNotIn(ATTACHED, out)


class Stops(WizardCase):
    """CRIT-6: each stop names its step, made only the calls listed, and the next run picks up."""

    def assert_stops(self, step, gh_calls, fragment, **kwargs):
        code, out, calls = self.wizard(**kwargs)
        self.assertEqual(code, 1, out)
        status, subject, detail = ms.lines(out)[-1]
        self.assertEqual((status, subject), ("停止", step), out)
        self.assertIn(fragment, detail)
        self.assertEqual(self.gh_calls(calls), gh_calls)
        self.assertFalse(os.path.exists(os.path.join(self.home, ".agents")), "the wizard installed something")
        self.assertNotIn("下一步", out)
        return out, calls

    def assert_picks_up(self, done_now):
        self.recording = recording(self.path("gh-fixed.json"))
        code, out, _ = self.wizard()
        self.assertEqual(code, 0, out)
        done = [subject for status, subject in self.steps(out) if status == "已完成"]
        self.assertEqual(done, done_now)
        return out

    def write_account(self, config, login):
        support.write_tree(self.home, {".config/%s/standin-account" % config: login + "\n"})

    def test_gh_missing(self):
        _, calls = self.assert_stops("前提", [], "找不到 gh",
                                     path=lambda tripwire, git_bin, rest: os.pathsep.join([tripwire, git_bin, "/usr/bin", "/bin"]))
        self.assertEqual(calls, [])
        self.assert_picks_up(ALL_ACTING)

    def test_git_missing(self):
        _, calls = self.assert_stops("前提", [], "找不到 git",
                                     path=lambda tripwire, git_bin, rest: os.pathsep.join([tripwire, environment.BIN]))
        self.assertEqual(calls, [])
        self.assert_picks_up(ALL_ACTING)

    def test_a_token_variable_in_the_environment(self):
        self.assert_stops("前提", [], "GH_TOKEN", extra={"GH_TOKEN": PLANTS[10]})
        self.assert_picks_up(ALL_ACTING)

    def test_the_default_login_held_by_another_account(self):
        self.write_account("gh", OTHER)
        self.assert_stops("agent account 登录", [STATUS], "gh auth logout --hostname github.com --user %s" % OTHER)
        os.remove(os.path.join(self.home, ".config", "gh", "standin-account"))  # habit logs it out
        self.assert_picks_up(ALL_ACTING)

    def test_the_agent_login_signed_in_as_the_maintainer_in_the_browser(self):
        self.recording = recording(self.path("gh-wrong.json"), agent_login=MAINTAINER)
        self.assert_stops("agent account 登录", [STATUS, AGENT_LOGIN, STATUS], "不是 Habit098")
        os.remove(os.path.join(self.home, ".config", "gh", "standin-account"))
        self.assert_picks_up(ALL_ACTING)

    def test_the_maintainer_configurations_login_held_by_another_account(self):
        self.recording = recording(self.path("gh-wrong.json"), maintainer_login=AGENT)
        self.assert_stops(
            "maintainer 配置", UP_TO_MAINTAINER + [MAINTAINER_LOGIN, STATUS],
            'GH_CONFIG_DIR="$HOME/.config/gh-maintainer" gh auth logout --hostname github.com --user Habit098')
        os.remove(os.path.join(self.home, ".config", "gh-maintainer", "standin-account"))
        self.assert_picks_up(["maintainer 配置", "ghm"])

    def test_the_maintainer_configuration_already_held_by_another_account(self):
        self.write_account("gh-maintainer", OTHER)
        self.assert_stops("maintainer 配置", UP_TO_MAINTAINER,
                          'GH_CONFIG_DIR="$HOME/.config/gh-maintainer" gh auth logout --hostname github.com --user %s' % OTHER)
        os.remove(os.path.join(self.home, ".config", "gh-maintainer", "standin-account"))
        self.assert_picks_up(["maintainer 配置", "ghm"])

    def test_a_maintainer_token_outside_the_keychain_names_the_maintainer_configuration(self):
        self.recording = recording(self.path("gh-plain.json"), extra=[
            {"args": STATUS, "when": [{"path": STATE, "contains": MAINTAINER + "\n"}],
             "stdout": json.dumps({"hosts": {"github.com": [status_entry(MAINTAINER, source="/x/hosts.yml")]}}) + "\n"},
        ])
        self.write_account("gh-maintainer", MAINTAINER)
        self.assert_stops("maintainer 配置", UP_TO_MAINTAINER,
                          'GH_CONFIG_DIR="$HOME/.config/gh-maintainer" gh auth logout --hostname github.com --user Habit130')

    def test_a_failing_identity_item_names_what_it_expects_and_never_what_it_found(self):
        # gh answers the agent account to the wizard's own read, then a planted login to the check's.
        self.recording = recording(self.path("gh-check.json"), extra=[
            {"args": ["api", "user"], "once": True, "when": [{"path": STATE, "contains": AGENT + "\n"}],
             "stdout": json.dumps({"login": AGENT, "id": ms.AGENT_ID}) + "\n"},
            {"args": ["api", "user"], "when": [{"path": STATE, "contains": AGENT + "\n"}], "exit": 1,
             "stdout": "", "stderr": "gh: Bad credentials %s\n" % PLANTS[11]},
        ])
        code, out, _ = self.wizard()  # wizard() asserts no plant in the output
        self.assertEqual(code, 1, out)
        self.assertIn("[失败] identity：gh 应以 agent account Habit098 操作", out)
        self.assertNotIn("下一步", out)

    def test_habit_declines_the_agent_login(self):
        self.recording = recording(self.path("gh-declined.json"), agent_exit=1)
        self.assert_stops("agent account 登录", [STATUS, AGENT_LOGIN], "没有完成")
        self.assertFalse(os.path.exists(os.path.join(self.home, ".gitconfig")))
        self.assert_picks_up(ALL_ACTING)

    def test_the_maintainer_login_fails(self):
        self.recording = recording(self.path("gh-failed.json"), maintainer_exit=1)
        self.assert_stops("maintainer 配置", UP_TO_MAINTAINER + [MAINTAINER_LOGIN], "没有完成")
        self.assertFalse(os.path.exists(os.path.join(self.home, ".zshrc")))
        self.assert_picks_up(["maintainer 配置", "ghm"])

    def test_a_login_shell_other_than_zsh(self):
        self.assert_stops("ghm", UP_TO_MAINTAINER + [MAINTAINER_LOGIN, STATUS], "不是 zsh", extra={"SHELL": "/bin/bash"})
        self.assertFalse(os.path.exists(os.path.join(self.home, ".zshrc")))
        self.assert_picks_up(["ghm"])

    def test_an_edited_ghm_block(self):
        self.assertEqual(self.wizard()[0], 0)
        support.write_tree(self.home, {".zshrc": self.read(".zshrc").replace('command gh "$@"', "command gh")})
        before = ms.snapshot(self.home)
        self.assert_stops("ghm", [STATUS, ["api", "user"], STATUS], "被改过")
        self.assertEqual(ms.snapshot(self.home), before)

    def test_another_ghm_definition(self):
        support.write_tree(self.home, {".zshrc": "alias ghm='gh'\n"})
        self.assert_stops("ghm", UP_TO_MAINTAINER + [MAINTAINER_LOGIN, STATUS], "别的 ghm 定义")
        self.assertEqual(self.read(".zshrc"), "alias ghm='gh'\n")


class CredentialRoute(WizardCase):
    """A1: git takes every matching helper in config order, an empty value clearing the list,
    and asks them in turn. The step is done only when that list is exactly gh's helper.

    Each case asks the real git, in the throwaway home, which helper answers github.com. Every
    helper is test-local: gh's is a fake gh printing the agent account, the others print the
    maintainer account and leave a mark, so no real gh, keychain or credential is reached.
    """

    def setUp(self):
        super(CredentialRoute, self).setUp()
        fake = self.path("fake-gh-bin", "gh")
        support.write_tree(self.path("fake-gh-bin"), {"gh": (
            "#!/bin/bash\ncat >/dev/null\n[ \"$*\" = 'auth git-credential get' ] && "
            "printf 'username=Habit098\\npassword=agent-marker\\n'\nexit 0\n")})
        os.chmod(fake, 0o755)
        self.gh_helper = "!%s auth git-credential" % fake
        self.recording = recording(self.path("gh-route.json"), helper=self.gh_helper)
        self.other_mark = self.path("other-helper-ran")
        # A helper that supplies a complete credential for the maintainer account, and a planted value.
        self.other = "!f() { cat >/dev/null; touch '%s'; echo username=Habit130; echo password=%s; }; f" % (
            self.other_mark, PLANTS[9])

    def after_setup_git(self, text):
        """Have the stand-in's setup-git leave text after gh's section, where its reset can't clear it."""
        with open(self.recording) as handle:
            calls = json.load(handle)
        calls["calls"][-1]["effects"][0]["append"] += text
        with open(self.recording, "w") as handle:
            json.dump(calls, handle)

    def fill(self, extra=None):
        """(username git's credential fill gets for github.com, whether the other helper ran)."""
        _, env = self.env(extra=extra)
        env["GIT_TERMINAL_PROMPT"] = "0"
        for name in ("GIT_ASKPASS", "SSH_ASKPASS"):
            env.pop(name, None)
        work = self.path("fill-%d" % self.scratches)
        os.makedirs(work)
        result = subprocess.run([REAL_GIT, "credential", "fill"], input="protocol=https\nhost=github.com\n\n", cwd=work,
                                env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        names = [line[len("username="):] for line in result.stdout.splitlines() if line.startswith("username=")]
        ran = os.path.exists(self.other_mark)
        if ran:
            os.remove(self.other_mark)
        return (names[0] if names else None), ran

    def assert_routed_through_gh_alone(self, extra=None):
        code, out, calls = self.wizard(extra=extra)
        self.assertEqual(code, 0, out)
        self.assertIn(("已完成", "git credential"), self.steps(out))
        self.assertIn(SETUP_GIT, self.gh_calls(calls))
        self.assertEqual(self.fill(extra), (AGENT, False))
        before = ms.snapshot(self.home)
        code, out, calls = self.wizard(extra=extra)
        self.assertEqual(code, 0, out)
        self.assertIn(("已就绪", "git credential"), self.steps(out))
        self.assertNotIn(SETUP_GIT, self.gh_calls(calls))
        self.assertEqual(ms.snapshot(self.home), before)

    def test_an_earlier_helper_before_a_trailing_gh_helper_without_its_reset(self):
        # Acceptance's A1: the last github.com helper is gh's, but nothing clears the one before it.
        support.write_tree(self.home, {".gitconfig": (
            "[credential]\n\thelper = \"%s\"\n[credential \"https://github.com\"]\n\thelper = %s\n"
            % (self.other, self.gh_helper))})
        self.assertEqual(self.fill()[0], MAINTAINER)  # before: the earlier helper answers
        self.assert_routed_through_gh_alone()

    def test_a_system_helper_such_as_the_keychains(self):
        system = self.path("system-gitconfig")
        with open(system, "w") as handle:
            handle.write("[credential]\n\thelper = \"%s\"\n" % self.other)
        extra = {"GIT_CONFIG_SYSTEM": system, "GIT_CONFIG_NOSYSTEM": "0"}
        self.assertEqual(self.fill(extra)[0], MAINTAINER)
        self.assert_routed_through_gh_alone(extra)

    def test_a_helper_after_gh_that_setup_git_leaves_in_place_stops_the_step(self):
        # Applied after gh's reset, it would also receive every credential git approves.
        self.after_setup_git("[credential]\n\thelper = \"%s\"\n" % self.other)
        code, out, made = self.wizard()  # wizard() asserts no plant in the output
        self.assertEqual(code, 1, out)
        status, subject, detail = ms.lines(out)[-1]
        self.assertEqual((status, subject), ("停止", "git credential"))
        self.assertIn("仍不只是 gh 的", detail)
        self.assertEqual(self.git_writes(made), [])

    def test_a_helper_for_every_https_host_after_gh_stops_the_step(self):
        # Bugbot on 2aec3b6: an empty host is a pattern git applies to github.com too.
        self.after_setup_git('[credential "https://"]\n\thelper = "%s"\n' % self.other)
        code, out, _ = self.wizard()
        self.assertEqual(code, 1, out)
        self.assertEqual(ms.lines(out)[-1][:2], ("停止", "git credential"))
        # git itself applies it: reject runs every helper for github.com, and the other one leaves its mark.
        _, env = self.env()
        work = self.path("reject")
        os.makedirs(work)
        for name in ("GIT_ASKPASS", "SSH_ASKPASS"):
            env.pop(name, None)
        subprocess.run([REAL_GIT, "credential", "reject"], input="protocol=https\nhost=github.com\nusername=x\npassword=y\n\n",
                       cwd=work, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        self.assertTrue(os.path.exists(self.other_mark), "git didn't apply the empty-host helper to github.com")

    def test_a_conditional_include_is_named_as_unchecked(self):
        support.write_tree(self.home, {".gitconfig": '[includeIf "gitdir:~/work/"]\n\tpath = ~/.gitconfig-work\n'})
        code, out, _ = self.wizard()
        self.assertEqual(code, 0, out)
        detail = [d for _, subject, d in ms.lines(out) if subject == "git credential"][0]
        self.assertIn("includeIf", detail)

    def test_a_key_git_can_read_but_urlsplit_cant_still_counts(self):
        self.after_setup_git('[credential "https://["]\n\thelper = "%s"\n' % self.other)
        code, out, _ = self.wizard()
        self.assertEqual(code, 1, out)
        self.assertEqual(ms.lines(out)[-1][:2], ("停止", "git credential"))


class Scopes(WizardCase):
    def test_missing_scopes_go_to_habit_as_a_refresh(self):
        refreshed = "${GH_CONFIG_DIR}/standin-refreshed"
        refresh = ["auth", "refresh", "--hostname", "github.com", "--scopes", AGENT_SCOPES]
        self.recording = recording(self.path("gh-narrow.json"), extra=[
            {"args": STATUS, "when": [{"path": STATE, "contains": AGENT + "\n"}, {"path": refreshed, "absent": True}],
             "stdout": json.dumps({"hosts": {"github.com": [status_entry(AGENT, scopes="gist, read:org, repo")]}}) + "\n"},
            {"args": refresh, "stdout": ATTACHED + "\n", "effects": [{"path": refreshed, "write": "yes\n"}]},
        ])
        support.write_tree(self.home, {".config/gh/standin-account": AGENT + "\n"})
        code, out, calls = self.wizard()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.gh_calls(calls)[:3], [STATUS, refresh, STATUS])
        self.assertIn(("已完成", "agent account 登录"), self.steps(out))
        self.assertIn("缺少 scopes workflow", out)


class Credentials(WizardCase):
    """CRIT-7 beyond the stand-in's answers: planted values in the files the wizard reads."""

    def test_no_planted_value_reaches_the_output_or_what_the_wizard_writes(self):
        gitconfig = "[user]\n\temail = %s\n\tname = %s\n[credential]\n\thelper = %s\n" % (PLANTS[10], PLANTS[11], PLANTS[0])
        zshrc = "export NOT_A_SECRET=%s\n" % PLANTS[3]
        support.write_tree(self.home, {".gitconfig": gitconfig, ".zshrc": zshrc})
        code, out, _ = self.wizard()  # wizard() asserts no plant in the output
        self.assertEqual(code, 0, out)
        for rel, old in ((".gitconfig", gitconfig), (".zshrc", zshrc)):
            added = [line for line in self.read(rel).splitlines() if line not in old.splitlines()]
            for plant in PLANTS:
                self.assertNotIn(plant, "\n".join(added), rel)
        self.assertNotIn(PLANTS[10], self.read(".gitconfig"))  # the old email is replaced, never echoed
        self.assertTrue(self.read(".zshrc").startswith(zshrc))

    def test_a_token_outside_the_keychain_stops_the_login_step(self):
        self.recording = recording(self.path("gh-plain.json"), extra=[
            {"args": STATUS, "when": [{"path": STATE, "contains": AGENT + "\n"}],
             "stdout": json.dumps({"hosts": {"github.com": [status_entry(AGENT, source="/x/hosts.yml %s" % PLANTS[6])]}}) + "\n"},
        ])
        support.write_tree(self.home, {".config/gh/standin-account": AGENT + "\n"})
        code, out, _ = self.wizard()
        self.assertEqual(code, 1)
        self.assertEqual(ms.lines(out)[-1][:2], ("停止", "agent account 登录"))
        self.assertIn("keychain", out)


if __name__ == "__main__":
    unittest.main()
