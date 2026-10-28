"""Seam C's inputs (#44 Testing Decisions): a source tree, a throwaway home, and stand-ins for gh and Codex.

The source tree is a git repository built at test time from this checkout's real `machine/`
and `generator/govern-repository/`, with a small synthetic `skill-copies/`, so the recorded
Codex output for a fixture home stays true when the real copies are refreshed. The home's
`HOME`, `XDG_*`, `TMPDIR` and `CODEX_HOME` all point into it. A `ghm` tripwire sits first on
the path, so a call to it leaves a mark.
"""

import hashlib
import json
import os
import subprocess
import sys
from urllib.parse import quote

import support
from standins import environment

MACHINE = os.path.join(support.REPO, "machine")
ENTRY = os.path.join(MACHINE, "scripts", "machine.py")
READY = os.path.join(MACHINE, "ready.sh")
GENERATOR = os.path.join(support.REPO, "generator", "govern-repository")
STANDIN_CODEX = os.path.join(environment.BIN, "codex")
if os.path.join(MACHINE, "scripts") not in sys.path:
    sys.path.insert(0, os.path.join(MACHINE, "scripts"))
RECORDINGS = os.path.join(support.FIXTURES, "machine")
UPSTREAM_COMMIT = "1111111111111111111111111111111111111111"
AGENT_ID = 147811321
NOREPLY = "%d+Habit098@users.noreply.github.com" % AGENT_ID

# The synthetic copies: one model-invoked skill with a stored dot segment, one user-invoked
# skill that carries Codex's user-only key.
COPIES = {
    "alpha-check": {
        "SKILL.md": "---\nname: alpha-check\ndescription: Alpha copy for the machine suites.\n---\n\nAlpha body.\n",
        "dot-notes/kept.md": "A stored dot segment, decoded at install.\n",
    },
    "beta-flow": {
        "SKILL.md": "---\nname: beta-flow\ndescription: Beta copy, user-invoked.\ndisable-model-invocation: true\n---\n\nBeta body.\n",
        "agents/openai.yaml": "policy:\n  allow_implicit_invocation: false\n",
    },
}
MACHINE_NAMES = sorted(list(COPIES) + ["govern-repository"])


def _tree(root):
    """{relative path: {"content", "mode"}} for every file under root, as on disk, without bytecode."""
    files = {}
    for base, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for name in names:
            if name.endswith(".pyc") or name == ".DS_Store":
                continue
            full = os.path.join(base, name)
            with open(full, "rb") as handle:
                content = handle.read().decode("utf-8")
            files[os.path.relpath(full, root).replace(os.sep, "/")] = {
                "content": content,
                "mode": "100755" if os.stat(full).st_mode & 0o111 else "100644",
            }
    return files


def source_files(copies=None):
    """The source tree's files: the real machine/ and generator, and the synthetic copies."""
    copies = COPIES if copies is None else copies
    files = {}
    for prefix, root in (("machine", MACHINE), ("generator/govern-repository", GENERATOR)):
        for rel, spec in _tree(root).items():
            files["%s/%s" % (prefix, rel)] = spec
    for name, skill in copies.items():
        for rel, content in skill.items():
            files["skill-copies/skills/%s/%s" % (name, rel)] = content
    files["skill-copies/provenance.json"] = json.dumps(
        {
            "license": {"repository": "mattpocock/skills", "path": "LICENSE", "commit": UPSTREAM_COMMIT},
            "copies": [
                {"name": name, "repository": "mattpocock/skills", "path": "skills/test/%s" % name,
                 "commit": UPSTREAM_COMMIT, "codex_key_added": False}
                for name in sorted(copies)
            ],
        },
        indent=2,
    ) + "\n"
    return files


def build_source(path, copies=None):
    """A git repository holding the source tree, committed on main; return its commit."""
    support.init_repo(path)
    return support.commit_tree(path, source_files(copies), "source tree")


def make_home(path, files=None):
    """A throwaway home, with the directories its variables name, and optional files."""
    for directory in (".config", ".local/state", ".local/share", ".cache", "tmp"):
        os.makedirs(os.path.join(path, *directory.split("/")))
    if files:
        support.write_tree(path, files)
    return os.path.realpath(path)


def ready_home(path):
    """A home whose machine check passes after an install: global file, identity and ghm."""
    return make_home(
        path,
        {
            ".agents/AGENTS.md": "# AGENTS.md (全局)\n\nhabit's global instructions.\n",
            ".gitconfig": "[user]\n\tname = Habit098\n\temail = %s\n" % NOREPLY,
            ".zshrc": "alias ghm='GH_CONFIG_DIR=$HOME/.config/gh-maintainer gh'\n",
        },
    )


def write_gh_recording(path, user="Habit098", repositories=(), records=None, misses=None, upstream_ahead=0,
                       extra=()):
    """The stand-in GitHub for Seam C, in the shapes gh printed for the agent account on 2026-10-27.

    records maps a repository to its record text, or None to fail the read; misses maps a
    repository to its open miss-record count.
    """
    records = records or {}
    misses = misses or {}
    calls = [
        {"args": ["api", "user"], "stdout": json.dumps({"login": user, "id": AGENT_ID}) + "\n", "stderr": "", "exit": 0},
        {
            "args": ["repo", "list", "Habit130", "--limit", "1000", "--json", "nameWithOwner,isPrivate,defaultBranchRef"],
            "stdout": json.dumps(list(repositories)) + "\n",
            "stderr": "",
            "exit": 0,
        },
        {
            "args": ["api", "repos/mattpocock/skills/compare/%s...HEAD" % UPSTREAM_COMMIT, "--jq", "{ahead_by, status}"],
            "stdout": json.dumps({"ahead_by": upstream_ahead, "status": "ahead" if upstream_ahead else "identical"}) + "\n",
            "stderr": "",
            "exit": 0,
        },
    ]
    for entry in repositories:
        name = entry["nameWithOwner"]
        branch = (entry.get("defaultBranchRef") or {}).get("name")
        if not branch:
            continue
        args = ["api", "repos/%s/contents/.github/governance/record.yml?ref=%s" % (name, quote(branch, safe="")),
                "-H", "Accept: application/vnd.github.raw"]
        text = records.get(name, "")
        if name not in records:
            not_found = '{"message":"Not Found","documentation_url":"https://docs.github.com/rest/repos/contents#get-repository-content","status":"404"}'
            calls.append({"args": args, "stdout": not_found, "stderr": "gh: Not Found (HTTP 404)\n", "exit": 1})
        elif text is None:
            calls.append({"args": args, "stdout": "", "stderr": "gh: Server Error (HTTP 500)\n", "exit": 1})
        else:
            calls.append({"args": args, "stdout": text, "stderr": "", "exit": 0})
        calls.append(
            {
                "args": ["issue", "list", "--repo", name, "--label", "miss", "--state", "open", "--json", "number", "--limit", "1000"],
                "stdout": json.dumps([{"number": n + 1} for n in range(misses.get(name, 0))]) + "\n",
                "stderr": "",
                "exit": 0,
            }
        )
    calls.extend(extra)
    with open(path, "w") as handle:
        json.dump({"description": "Seam C's stand-in GitHub, written by machine_support.py.", "tool": "gh", "calls": calls}, handle)
    return path


def merge_codex_recordings(path, *names):
    """One Codex recording from several committed ones under tests/fixtures/machine/."""
    calls = []
    for name in names:
        with open(os.path.join(RECORDINGS, name)) as handle:
            calls.extend(json.load(handle)["calls"])
    with open(path, "w") as handle:
        json.dump({"tool": "codex", "calls": calls}, handle)
    return path


def machine_env(home, scratch, gh_recording=None, codex_recording=None, extra=None):
    """The environment a machine program runs in: everything points into home, stand-ins first."""
    base = support.isolated_env(
        {
            "HOME": home,
            "XDG_CONFIG_HOME": os.path.join(home, ".config"),
            "XDG_STATE_HOME": os.path.join(home, ".local", "state"),
            "XDG_DATA_HOME": os.path.join(home, ".local", "share"),
            "XDG_CACHE_HOME": os.path.join(home, ".cache"),
            "TMPDIR": os.path.join(home, "tmp"),
            "CODEX_HOME": os.path.join(home, ".codex"),
            "SHELL": "/bin/zsh",
            "MACHINE_CODEX": os.path.join(home, "no-codex-here"),
        }
    )
    for name in ("GIT_CONFIG_GLOBAL", "ZDOTDIR", "DSH_HOME", "DSH_AGENTS_HOME", "CLAUDE_CONFIG_DIR"):
        base.pop(name, None)
    if extra:
        base.update(extra)
    env = environment.environment(scratch, gh_recording=gh_recording, codex_recording=codex_recording, base=base)
    tripwire_bin = os.path.join(scratch, "tripwire-bin")
    os.makedirs(tripwire_bin)
    tripwire = os.path.join(tripwire_bin, "ghm")
    with open(tripwire, "w") as handle:
        handle.write("#!/bin/bash\necho \"$*\" >> '%s'\nexit 0\n" % os.path.join(scratch, "ghm-called"))
    os.chmod(tripwire, 0o755)
    env["PATH"] = tripwire_bin + os.pathsep + env["PATH"]
    return env


def ghm_called(scratch):
    return os.path.exists(os.path.join(scratch, "ghm-called"))


def run_machine(args, env):
    """Run machine.py; return (exit code, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, ENTRY] + list(args), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        universal_newlines=True, stdin=subprocess.DEVNULL,
    )
    return result.returncode, result.stdout, result.stderr


def lines(out):
    """[(status, subject, detail)] from a printed report."""
    found = []
    for line in out.splitlines():
        if line.startswith("[") and "] " in line and "：" in line:
            status, rest = line[1:].split("] ", 1)
            subject, detail = rest.split("：", 1)
            found.append((status, subject, detail))
    return found


def statuses(out, title):
    """{subject: worst status} for one report section, by its title."""
    section, found = None, {}
    for line in out.splitlines():
        if line.startswith("== "):
            section = line[3:]
            continue
        if section != title:
            continue
        for status, subject, _ in lines(line):
            if found.get(subject) != "失败":
                found[subject] = status
    return found


def section(out, title):
    """The printed lines of one report section."""
    chosen, current = [], None
    for line in out.splitlines():
        if line.startswith("== "):
            current = line[3:]
            continue
        if current == title:
            chosen.append(line)
    return chosen


def snapshot(root):
    """Every path under root with its kind, mode and content hash or link target.

    Except the cache macOS's xcrun shims (/usr/bin/git, /usr/bin/python3) may keep in
    `$TMPDIR/xcrun_db`, which machine_env puts in the home: the OS writes it, depending on the
    machine, and a real home's TMPDIR is never inside it.
    """
    found = {}
    for base, dirs, names in os.walk(root):
        for name in dirs + names:
            full = os.path.join(base, name)
            rel = os.path.relpath(full, root)
            if rel == os.path.join("tmp", "xcrun_db"):
                continue
            if os.path.islink(full):
                found[rel] = ("link", os.readlink(full))
            elif os.path.isdir(full):
                found[rel] = ("dir", oct(os.stat(full).st_mode & 0o777))
            else:
                with open(full, "rb") as handle:
                    found[rel] = ("file", oct(os.stat(full).st_mode & 0o777), hashlib.sha256(handle.read()).hexdigest())
    return found


def crowd(home, count, description, prefix="crowd"):
    """Fill ~/.agents/skills with count personal skills, <prefix>-1 to <prefix>-<count>, for the budget cases."""
    for number in range(1, count + 1):
        name = "%s-%d" % (prefix, number)
        support.write_tree(
            os.path.join(home, ".agents", "skills"),
            {"%s/SKILL.md" % name: "---\nname: %s\ndescription: %s\n---\n\nBody.\n" % (name, description)},
        )


# The budget homes: the ready home after an install, plus a crowd of personal skills. Their
# recorded `codex debug prompt-input` output shortens descriptions, and drops entries. Codex
# keeps entries in name order, so a crowd whose names sort before `alpha-check` drops it.
CROWDS = {
    "shortened": (300, " ".join(["word"] * 200)),
    "omitted": (1500, "short"),
    "crowded-out": (1500, "short", "aa-crowd"),
}

# A personal user-invoked skill without Codex's user-only key, written after an install.
KEYLESS = {
    "gamma-solo/SKILL.md": "---\nname: gamma-solo\ndescription: Gamma personal skill, user-invoked, without the Codex key.\n"
    "disable-model-invocation: true\n---\n\nBody.\n",
}
