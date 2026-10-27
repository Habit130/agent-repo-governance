"""A machine home's paths, and the report every machine program prints.

Every path derives from one home directory and the environment the harnesses read
(`XDG_CONFIG_HOME`, `XDG_STATE_HOME`, `CODEX_HOME`, `DSH_HOME`), so a suite that points them
all into a throwaway home never touches the real one.
"""

import os
import shutil
import subprocess
import tempfile

PASS, FAIL, SKIP, NOTE = "通过", "失败", "跳过", "说明"


class Home(object):
    def __init__(self, root, env=None):
        self.root = os.path.realpath(root)
        self.env = dict(os.environ if env is None else env)
        self.env["HOME"] = self.root

    def _under(self, variable, *default):
        value = self.env.get(variable)
        return value if value else os.path.join(self.root, *default)

    @property
    def agents(self):
        return os.path.join(self.root, ".agents")

    @property
    def skills(self):
        return os.path.join(self.agents, "skills")

    @property
    def agents_md(self):
        return os.path.join(self.agents, "AGENTS.md")

    @property
    def governance(self):
        """Where the install keeps its own files: the installed state and the machine tools."""
        return os.path.join(self.agents, "governance")

    @property
    def state(self):
        return os.path.join(self.governance, "installed.json")

    @property
    def tools(self):
        return os.path.join(self.governance, "machine")

    @property
    def staging(self):
        return os.path.join(self.governance, "staging")

    @property
    def lock(self):
        """The `skills` CLI's lock file, where that CLI puts it (format version 3)."""
        state = self.env.get("XDG_STATE_HOME")
        if state:
            return os.path.join(state, "skills", ".skill-lock.json")
        return os.path.join(self.agents, ".skill-lock.json")

    @property
    def claude(self):
        return os.path.join(self.root, ".claude")

    @property
    def opencode(self):
        return os.path.join(self._under("XDG_CONFIG_HOME", ".config"), "opencode")

    @property
    def codex(self):
        return self._under("CODEX_HOME", ".codex")

    @property
    def dsh(self):
        return self._under("DSH_HOME", ".dsh")

    @property
    def claude_settings(self):
        return os.path.join(self.claude, "settings.json")

    @property
    def opencode_settings(self):
        return os.path.join(self.opencode, "opencode.json")

    @property
    def codex_rules(self):
        return os.path.join(self.codex, "rules", "governance.rules")

    @property
    def dsh_agents_md(self):
        return os.path.join(self.dsh, "AGENTS.md")

    def links(self):
        """The install's links (#44 §8 step 3), as (path, target)."""
        return [
            (os.path.join(self.claude, "skills"), self.skills),
            (os.path.join(self.claude, "CLAUDE.md"), self.agents_md),
            (os.path.join(self.opencode, "AGENTS.md"), self.agents_md),
            (os.path.join(self.codex, "AGENTS.md"), self.agents_md),
        ]

    def personal_roots(self):
        """Other skill directories a harness loads, where a personal skill could share a machine skill's name."""
        return [
            os.path.join(self.skills, "synced"),
            os.path.join(self.opencode, "skills"),
            os.path.join(self.dsh, "skills"),
        ]

    def show(self, path):
        """A path as habit reads it: under ~ when it is inside the home."""
        if path == self.root or path.startswith(self.root + os.sep):
            return "~" + path[len(self.root):]
        return path

    def run(self, args, cwd=None, stdin=None, binary=False, timeout=120, extra_env=None):
        """Run a tool with this home's environment; return (exit code, stdout, stderr)."""
        env = dict(self.env)
        env.update(extra_env or {})
        try:
            result = subprocess.run(
                args,
                env=env,
                cwd=cwd,
                input=stdin,
                stdin=None if stdin is not None else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            return 127, b"" if binary else "", str(error)
        out = result.stdout if binary else result.stdout.decode("utf-8", "replace")
        return result.returncode, out, result.stderr.decode("utf-8", "replace")

    def run_codex(self, codex, args):
        """Run the Codex CLI on this home's skills without writing to the home.

        Codex writes its own state into `CODEX_HOME` as it starts: an installation id, a
        sandbox migration marker, shell snapshots and its system skills under
        `skills/.system`. So it runs with a disposable `CODEX_HOME` that holds a copy of
        the home's `config.toml` and a link to each of the home's own Codex skills, and in
        a disposable working directory. `HOME` stays the home's, so `~/.agents/skills` lists
        as it does in a session.
        """
        scratch = tempfile.mkdtemp(prefix="machine-codex-")
        try:
            codex_home = os.path.join(scratch, "codex-home")
            os.makedirs(os.path.join(codex_home, "skills"))
            config = os.path.join(self.codex, "config.toml")
            if os.path.isfile(config):
                shutil.copy2(config, codex_home)
            own = os.path.join(self.codex, "skills")
            if os.path.isdir(own):
                for name in sorted(os.listdir(own)):
                    if not name.startswith("."):
                        os.symlink(os.path.join(own, name), os.path.join(codex_home, "skills", name))
            work = os.path.join(scratch, "work")
            os.makedirs(work)
            return self.run([codex] + list(args), cwd=work, extra_env={"CODEX_HOME": codex_home})
        finally:
            shutil.rmtree(scratch, True)


class Report(object):
    """Lines of one program's report, in Chinese: a status, a subject and what was found."""

    def __init__(self, title):
        self.title = title
        self.lines = []

    def add(self, status, subject, detail):
        self.lines.append((status, subject, detail))

    def failed(self):
        return any(status == FAIL for status, _, _ in self.lines)

    def render(self):
        out = ["== %s" % self.title]
        for status, subject, detail in self.lines:
            out.append("[%s] %s：%s" % (status, subject, detail))
        return "\n".join(out) + "\n"
