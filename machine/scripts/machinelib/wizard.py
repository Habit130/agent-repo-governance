"""The account wizard (#44 §8, #41 §14, #19): a new machine's one-time account setup.

habit runs it in habit's own terminal, before the machine's first install, from a fresh clone
(`machine/wizard.sh`). Each step reads the state first and acts only when the state isn't
there yet, so a rerun changes nothing and a run that stopped picks up at the step it stopped
at. In order:

1. 前提: `gh` and `git` are on the path; no token variable and no other `GH_CONFIG_DIR` is set,
   since either would decide who gh acts as instead of the stored logins.
2. agent account 登录: the agent account is gh's default login, its token in the keychain, with
   `AGENT_SCOPES`. A missing login, or one gh reports broken, goes to habit as `gh auth login`;
   missing scopes as `gh auth refresh`.
3. git credential: git's github.com credential goes through gh alone (`gh auth setup-git`): the
   helpers git takes for it, system and global config together, are exactly gh's.
4. git commit 身份: the global `user.email` is the agent account's noreply address, built from
   the id `gh api user` answers, and `user.name` is the agent account.
5. maintainer 配置: the maintainer account is logged in under `~/.config/gh-maintainer`, the
   directory `govlib/owner.py`'s owner-script command names.
6. ghm: `~/.zshrc` defines `ghm` (`GHM_BLOCK`) in #19's form. It resolves the maintainer's
   token only when habit calls it, so the profile holds none.
7. identity: the machine check's identity item (§9) on the result.

A step that can't finish stops the wizard there with a plain Chinese line and exit 1. It
installs nothing and logs nothing out: an account other than the expected one is habit's to
log out, with the command the line gives.

The logins run attached to the terminal, so habit answers gh directly and the wizard captures
nothing from them; they store the token in the keychain, never with `--insecure-storage`. Every
other call is captured and read for named fields only: a login is printed only when it has
GitHub's login form, and every line passes through `govlib.secrets.redact`. The wizard never
calls `gh auth token`; that text appears only inside `ghm`'s definition.
"""

import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

from govlib import secrets
from govlib.owner import MAINTAINER_GH_CONFIG

from machinelib import AGENT, MAINTAINER, check
from machinelib import home as homes

HOST = "github.com"
AGENT_SCOPES = ("repo", "read:org", "gist", "workflow")
TOKEN_VARIABLES = ("GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN")
DONE, READY, STOP, PASS, FAIL = "已完成", "已就绪", "停止", homes.PASS, homes.FAIL
MAINTAINER_PREFIX = 'GH_CONFIG_DIR="%s" ' % MAINTAINER_GH_CONFIG
LOGIN_FORM = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
READY_COMMAND = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "ready.sh")

GHM_BEGIN = "# >>> agent-repo-governance account wizard: ghm >>>"
GHM_END = "# <<< agent-repo-governance account wizard: ghm <<<"
# The maintainer's gh configuration is the one the owner-script command names (govlib/owner.py).
GHM_BLOCK = """%s
# ghm runs gh as the maintainer account %s, with its own gh configuration. The token is
# looked up only when ghm runs, so this file holds none. Agents never call ghm.
ghm() {
  GH_CONFIG_DIR="%s" \\
    GH_TOKEN="$(GH_CONFIG_DIR="%s" command gh auth token --user %s)" \\
    command gh "$@"
}
%s
""" % (GHM_BEGIN, MAINTAINER, MAINTAINER_GH_CONFIG, MAINTAINER_GH_CONFIG, MAINTAINER, GHM_END)


class Stop(Exception):
    """A step that can't finish: the line says why and what habit does next, in Chinese."""


def say(text):
    sys.stdout.write(secrets.redact(text) + "\n")
    sys.stdout.flush()


def helper_matches(key):
    """Whether a config key is a credential helper git applies to https://github.com."""
    lowered = key.lower()
    if not (lowered.startswith("credential.") and lowered.endswith(".helper")):
        return False
    url = key[len("credential."):-len(".helper")]
    if not url:
        return True
    parsed = urlsplit(url if "://" in url else "https://" + url)
    host = (parsed.hostname or "").lower()
    return parsed.scheme.lower() == "https" and parsed.path in ("", "/") and fnmatch.fnmatchcase(HOST, host)


def shown(login):
    return login if isinstance(login, str) and LOGIN_FORM.match(login) else "一个无法识别的账户"


class Wizard(object):
    def __init__(self, home):
        self.home = home
        config = home.env.get("XDG_CONFIG_HOME") or os.path.join(home.root, ".config")
        self.default_config = os.path.join(config, "gh")
        self.maintainer_config = MAINTAINER_GH_CONFIG.replace("$HOME", home.root, 1)
        self.profile = os.path.join(home.env.get("ZDOTDIR") or home.root, ".zshrc")

    # -- tools

    def gh(self, config, *args):
        return self.home.run(["gh"] + list(args), extra_env={"GH_CONFIG_DIR": config})

    def git(self, *args):
        return self.home.run(["git"] + list(args))

    def attached(self, config, *args):
        """Run gh on the terminal itself, for habit to answer; return its exit code."""
        env = dict(self.home.env, GH_CONFIG_DIR=config)
        sys.stdout.flush()
        try:
            return subprocess.call(["gh"] + list(args), env=env)
        except KeyboardInterrupt:
            return 130  # habit cancelled: the step stops like a declined login
        except OSError:
            return 127

    def account(self, config):
        """gh's active github.com login under config: a dict of named fields, or None."""
        code, out, _ = self.gh(config, "auth", "status", "--hostname", HOST, "--active", "--json", "hosts")
        try:
            hosts = json.loads(out).get("hosts") if code == 0 else None
        except ValueError:
            hosts = None
        if not isinstance(hosts, dict):
            raise Stop("读不出 gh 的登录状态（`gh auth status --json` 失败）。请把 gh 更新到最新版本后重跑。")
        for entry in hosts.get(HOST) or []:
            if isinstance(entry, dict) and entry.get("active"):
                scopes = entry.get("scopes") if isinstance(entry.get("scopes"), str) else ""
                return {
                    "login": entry.get("login"),
                    "state": entry.get("state"),
                    "keyring": entry.get("tokenSource") == "keyring",
                    "scopes": set(scope.strip() for scope in scopes.split(",") if scope.strip()),
                }
        return None

    # -- steps

    def prerequisites(self):
        path = self.home.env.get("PATH", "")
        missing = [tool for tool in ("gh", "git") if not shutil.which(tool, path=path)]
        if missing:
            raise Stop("找不到 %s。wizard 不安装任何东西：请先装好（git 来自 Command Line Tools，gh 用 Homebrew 装），再重跑。"
                       % "、".join(missing))
        tokens = [name for name in TOKEN_VARIABLES if self.home.env.get(name)]
        if tokens:
            raise Stop("环境里设置了 %s，gh 会用它而不是保存的登录。请在没有它的终端里重跑。" % "、".join(tokens))
        config = self.home.env.get("GH_CONFIG_DIR")
        if config and os.path.realpath(config) != os.path.realpath(self.default_config):
            raise Stop("环境里设置了 GH_CONFIG_DIR，gh 不会用默认配置。请在没有它的终端里重跑。")
        return PASS, "gh 和 git 都在，环境里没有替代保存登录的设置"

    def login(self, config, expected, who, scopes=()):
        """Make expected gh's active login under config; return the step's (status, detail)."""
        account = self.account(config)
        acted = False
        if account is None or (account["login"] == expected and account["state"] == "error"):
            say("—— 现在交给 habit：用 %s 登录 gh。gh 会给出一次性 code 并打开浏览器；"
                "请在浏览器里以 %s 登录后授权（浏览器若已登录别的账户，先在无痕窗口打开 gh 给的网址）。" % (who, expected))
            args = ["auth", "login", "--hostname", HOST, "--git-protocol", "https", "--web"]
            if scopes:
                args += ["--scopes", ",".join(scopes)]
            if self.attached(config, *args) != 0:
                raise Stop("%s 的登录没有完成（被取消或失败）。重跑 wizard 会从这一步继续。" % who)
            acted = True
            account = self.account(config)
            if account is None:
                raise Stop("登录后 gh 仍没有 %s 的登录。重跑 wizard 会从这一步继续。" % who)
        if account["login"] != expected:
            prefix = "" if config == self.default_config else MAINTAINER_PREFIX
            login = account["login"]
            if isinstance(login, str) and LOGIN_FORM.match(login):
                how = "运行 `%sgh auth logout --hostname %s --user %s`" % (prefix, HOST, login)
            else:
                how = "用 `%sgh auth status` 找到它并登出" % prefix
            raise Stop("这里的 gh 登录是 %s，不是 %s。wizard 不会登出任何账户：请 habit 自己%s，再重跑。"
                       % (shown(login), expected, how))
        if account["state"] != "success":
            raise Stop("gh 现在无法确认 %s 的登录（可能是网络问题）。网络正常后重跑。" % expected)
        if not account["keyring"]:
            prefix = "" if config == self.default_config else MAINTAINER_PREFIX
            raise Stop("%s 的 token 不在 keychain 里。请 habit 运行 `%sgh auth logout --hostname %s --user %s` 登出它，"
                       "再重跑 wizard 重新登录。" % (expected, prefix, HOST, expected))
        missing = [scope for scope in scopes if scope not in account["scopes"]]
        if missing:
            say("—— 现在交给 habit：%s 的登录缺少 scopes %s，gh 会打开浏览器补授权。" % (expected, "、".join(missing)))
            if self.attached(config, "auth", "refresh", "--hostname", HOST, "--scopes", ",".join(scopes)) != 0:
                raise Stop("补授权没有完成（被取消或失败）。重跑 wizard 会从这一步继续。")
            acted = True
            account = self.account(config)
            if account is None or account["login"] != expected or not set(scopes) <= account["scopes"]:
                raise Stop("补授权后 %s 的 scopes 仍不齐。重跑 wizard 会从这一步继续。" % expected)
        detail = "gh 的登录是 %s，token 在 keychain 里" % expected
        if scopes:
            detail += "，scopes：%s" % "、".join(scopes)
        return (DONE if acted else READY), detail

    def agent_login(self):
        return self.login(self.default_config, AGENT, "agent account %s" % AGENT, AGENT_SCOPES)

    def credential_helpers(self):
        """The helpers git uses for https://github.com, in order, from the system and global config.

        As git's credential.c builds them: every `credential.helper` and every
        `credential.<url>.helper` whose URL matches is taken in config order, and an empty
        value clears the list so far. Read outside any repository, so no local config counts.
        """
        scratch = tempfile.mkdtemp(prefix="wizard-")
        try:
            code, out, _ = self.home.run(["git", "config", "-z", "--list"], cwd=scratch)
        finally:
            shutil.rmtree(scratch, True)
        helpers = []
        for entry in out.split("\0") if code == 0 else []:
            key, _, value = entry.partition("\n")
            if helper_matches(key):
                helpers = helpers + [value] if value else []
        return helpers

    def git_credential(self):
        def through_gh():
            # Exactly gh's helper: git asks the helpers in order and stores an approved
            # credential in every one of them, so another helper could answer first or keep a copy.
            helpers = self.credential_helpers()
            return len(helpers) == 1 and helpers[0].strip().endswith("gh auth git-credential")

        if through_gh():
            return READY, "git 的 github.com credential 只经过 gh"
        code, _, _ = self.gh(self.default_config, "auth", "setup-git", "--hostname", HOST)
        if code != 0:
            raise Stop("`gh auth setup-git` 没能把 git 的 credential 交给 gh。重跑 wizard 会从这一步继续。")
        if not through_gh():
            raise Stop("运行 `gh auth setup-git` 之后，git 的 github.com credential 除了 gh 还会经过别的 credential helper。"
                       "请 habit 删掉 ~/.gitconfig 里 gh 那一段之后的 `credential.helper` 设置，再重跑。")
        return DONE, "git 的 github.com credential 现在只经过 gh"

    def commit_identity(self):
        code, out, _ = self.gh(self.default_config, "api", "user")
        try:
            user = json.loads(out) if code == 0 else {}
        except ValueError:
            user = {}
        user_id = user.get("id") if isinstance(user, dict) else None
        if not isinstance(user_id, int) or isinstance(user_id, bool) or user.get("login") != AGENT:
            raise Stop("`gh api user` 没有答出 agent account %s 和它的 id。网络正常后重跑。" % AGENT)
        wanted = (("user.email", "%d+%s@users.noreply.github.com" % (user_id, AGENT)), ("user.name", AGENT))
        acted = False
        for key, value in wanted:
            code, out, _ = self.git("config", "--global", "--get", key)
            if code == 0 and out.strip() == value:
                continue
            if self.git("config", "--global", key, value)[0] != 0:
                raise Stop("没能写入 git 的全局 %s。重跑 wizard 会从这一步继续。" % key)
            acted = True
        detail = "git 的全局 commit 身份是 %s <%s>" % (AGENT, wanted[0][1])
        return (DONE if acted else READY), detail

    def maintainer(self):
        status, detail = self.login(self.maintainer_config, MAINTAINER, "maintainer account %s" % MAINTAINER)
        return status, "~/.config/gh-maintainer 里，" + detail

    def ghm_kind(self, shell):
        """What an interactive login shell calls ghm, read as the machine check reads it."""
        code, out, _ = self.home.run([shell, "-l", "-i", "-c", "unset HISTFILE; whence -w ghm"], timeout=30,
                                     extra_env={"SHELL_SESSIONS_DISABLE": "1"})
        return out.strip().split()[-1] if code == 0 and out.strip() else ""

    def ghm(self):
        shell = self.home.env.get("SHELL") or "/bin/zsh"
        if os.path.basename(shell) != "zsh":
            raise Stop("登录 shell 不是 zsh，wizard 只会在 ~/.zshrc 里定义 ghm。请把登录 shell 改成 zsh（`chsh -s /bin/zsh`）后重跑。")
        text = ""
        shown_profile = self.home.show(self.profile)
        if os.path.exists(self.profile):
            try:
                with open(self.profile, encoding="utf-8") as handle:
                    text = handle.read()
            except (OSError, UnicodeError):
                raise Stop("读不了 %s（不是 UTF-8 文本，或没有读权限）。wizard 没有改它；请检查后重跑。" % shown_profile)
        if GHM_BEGIN in text or GHM_END in text:
            if GHM_BLOCK not in text:
                raise Stop("%s 里 wizard 写的 ghm 段落被改过。请删掉整个段落（两行标记之间）后重跑。" % shown_profile)
            if self.ghm_kind(shell) != "function":
                raise Stop("%s 里有 ghm 段落，但交互式登录 shell 没有把 ghm 读成 function。请检查文件后重跑。" % shown_profile)
            return READY, "%s 定义了 ghm" % shown_profile
        if self.ghm_kind(shell) in ("alias", "function"):
            raise Stop("交互式登录 shell 里已经有别的 ghm 定义。wizard 不改它：请删掉它后重跑。")
        try:
            with open(self.profile, "a", encoding="utf-8") as handle:
                handle.write(("\n" if text and not text.endswith("\n") else "") + ("\n" if text else "") + GHM_BLOCK)
        except OSError:
            raise Stop("没能写入 %s。请检查它的权限后重跑。" % shown_profile)
        if self.ghm_kind(shell) != "function":
            raise Stop("写入 %s 后，交互式登录 shell 仍没有把 ghm 读成 function。请检查文件后重跑。" % shown_profile)
        return DONE, "%s 定义了 ghm，只在调用时取 maintainer account 的 token" % shown_profile

    def run(self):
        say("== account wizard")
        steps = (
            ("前提", self.prerequisites),
            ("agent account 登录", self.agent_login),
            ("git credential", self.git_credential),
            ("git commit 身份", self.commit_identity),
            ("maintainer 配置", self.maintainer),
            ("ghm", self.ghm),
        )
        for name, step in steps:
            try:
                status, detail = step()
            except Stop as stop:
                say("[%s] %s：%s" % (STOP, name, stop))
                return 1
            say("[%s] %s：%s" % (status, name, detail))
        problems = check._identity_problems(self.home)
        for problem in problems:
            # Only what the item expects: the value it found stays out of the output.
            say("[%s] identity：%s" % (FAIL, problem.split("，实际：")[0]))
        if problems:
            say("machine check 的 identity 项没有通过，wizard 停在这里。按上面的说明处理后重跑。")
            return 1
        say("[%s] identity：machine check 的 identity 项通过" % PASS)
        with open(READY_COMMAND, encoding="utf-8") as handle:
            ready = handle.read().rstrip("\n").splitlines()[-1]
        say("下一步：install。在 Claude Code 里用 `!` 前缀运行这条 ready command：")
        say(ready)
        return 0


def run(home):
    """Run the wizard in home; return its exit code."""
    return Wizard(home).run()
