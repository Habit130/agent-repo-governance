"""The inspection facts (#44 §6.3), gathered by script for the session's judgment.

- GitHub: owner, visibility, default branch, the agent account's permission, labels,
  rulesets, branch protection, the readable settings, and open PRs with their authors.
- The record, if any.
- Instructions and process files, from the tracked tree: `AGENTS.md`, `AGENTS.override.md`
  and `CLAUDE.md` in any directory, with `CLAUDE.local.md`; `docs/agents/`; contributing and
  process documents; `.github/` templates and CODEOWNERS; review-bot rule files.
- Harness files under `.claude/`, `.opencode/`, `.dsh/`, `.agents/` and `.codex/`, and
  `opencode.json`; the repository's own skills, by name against the machine skill set.
- CI: every workflow's triggers, jobs and path filters, whether each job runs or reports on
  every PR with uncertain cases flagged, and the Actions secrets each references
  (`workflows.py`).
- The build and test commands the manifests and documents name.
- Credentials found in the files read here, by type and location only (#41 §10). Version 1
  has no credential scanner (#38), so nothing else is searched.

`GLOSSARY.md` and `docs/adr/` are left as they are. Nothing here writes.
"""

import json
import os
import re

from govlib import GovernError, checkout, github, harness, workflows
from govlib.preconditions import installed_skills

INSTRUCTION_NAMES = ("AGENTS.md", "AGENTS.override.md", "CLAUDE.md", "CLAUDE.local.md")
PROCESS_STEMS = ("contributing", "code_of_conduct", "security", "support", "governance", "maintainers",
                 "releasing", "release", "development", "hacking")
PROCESS_DIRS = ("", "docs", ".github")
REVIEW_BOT_FILES = (
    re.compile(r"(^|.*/)\.cursor/BUGBOT\.md$"),
    re.compile(r"^\.cursor/rules/"),
    re.compile(r"^\.cursorrules$"),
    re.compile(r"^\.coderabbit\.ya?ml$"),
    re.compile(r"^\.github/copilot-instructions\.md$"),
    re.compile(r"^\.github/instructions/"),
    re.compile(r"^\.gemini/"),
    re.compile(r"^\.greptile/|^greptile\.json$"),
    re.compile(r"^\.sourcery\.ya?ml$"),
)
HARNESS_DIRS = (".claude", ".opencode", ".dsh", ".agents", ".codex")
HARNESS_FILES = ("opencode.json", "opencode.jsonc")
SKILL = re.compile(r"^(\.agents|\.claude|\.opencode|\.codex|\.dsh)/skills/([^/]+)/SKILL\.md$")
WORKFLOW = re.compile(r"^\.github/workflows/[^/]+\.ya?ml$")
GENERATOR = "govern-repository"

MANIFESTS = {
    "package.json": "npm", "Makefile": "make", "makefile": "make", "GNUmakefile": "make", "justfile": "just",
    "Justfile": "just", "pyproject.toml": "python", "setup.py": "python", "tox.ini": "tox", "noxfile.py": "nox",
    "Cargo.toml": "cargo", "go.mod": "go", "Gemfile": "bundler", "Rakefile": "rake", "build.gradle": "gradle",
    "build.gradle.kts": "gradle", "pom.xml": "maven", "Taskfile.yml": "task", "deno.json": "deno",
}
_MAKE_TARGET = re.compile(r"^([A-Za-z0-9][A-Za-z0-9_./-]*)\s*:(?![=:])")
_JUST_RECIPE = re.compile(r"^@?([A-Za-z0-9][A-Za-z0-9_-]*)(?:\s+[^:=]*)?:(?![=])")
_FENCE = re.compile(r"^\s*(```|~~~)\s*([A-Za-z0-9_-]*)")
SHELL_FENCES = ("", "sh", "bash", "shell", "console", "zsh", "terminal")
COMMAND_DOCS = re.compile(r"(^|/)(readme|contributing|development|hacking|building|testing)[^/]*\.(md|rst|txt)$|^docs/agents/build\.md$", re.I)

# Credential shapes, by the type habit hears; the value is never kept.
CREDENTIALS = (
    ("GitHub token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{22,})")),
    ("AWS access key ID", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("Anthropic API key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    ("OpenAI API key", re.compile(r"\bsk-(?!ant-)(?:proj-)?[A-Za-z0-9_-]{20,}")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}")),
)


def _text(root, path):
    data = checkout.read(root, path)
    if data is None:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def credentials(root, paths):
    """[{type, path, line}] for every credential shape in the files given."""
    found = []
    for path in paths:
        text = _text(root, path)
        if text is None:
            continue
        for number, line in enumerate(text.splitlines(), 1):
            for kind, pattern in CREDENTIALS:
                if pattern.search(line):
                    found.append({"type": kind, "path": path, "line": number})
    return found


def _github(gh, repository, data, branch):
    owner = data.get("owner") or {}
    labels = gh.get("repos/%s/labels?per_page=100" % repository)
    pulls = gh.get("repos/%s/pulls?state=open&per_page=100" % repository)
    rulesets, message = github.rulesets(gh, repository)
    rules = gh.get(github.branch_rules_path(repository, branch))
    applying = set(rule.get("ruleset_id") for rule in rules.data or []) if rules.ok else set()
    protection = gh.get(github.branch_path(repository, branch))
    facts = {
        "owner": {"login": owner.get("login"), "type": owner.get("type")},
        "visibility": "private" if data.get("private") else "public",
        "default_branch": branch,
        "permission": data.get("permissions"),
        "labels": [{k: label.get(k) for k in ("name", "color", "description")} for label in labels.data or []]
        if labels.ok else None,
        "rulesets": None if rulesets is None else [
            {
                "id": r.get("id"),
                "name": r.get("name"),
                "target": r.get("target"),
                "enforcement": r.get("enforcement"),
                "conditions": r.get("conditions"),
                "applies_to_default_branch": github.ruleset_applies(r, branch, applying),
                "unreadable": r.get("unreadable"),
            }
            for r in rulesets
        ],
        "branch_protection": {
            "protected": bool((protection.data or {}).get("protected")),
            "classic_protection": bool(((protection.data or {}).get("protection") or {}).get("enabled")),
        } if protection.ok else None,
        "settings": dict((key, data.get(key)) for key in
                         ("allow_squash_merge", "allow_merge_commit", "allow_rebase_merge", "delete_branch_on_merge", "allow_auto_merge")),
        "open_pull_requests": [
            {"number": p.get("number"), "title": p.get("title"), "author": (p.get("user") or {}).get("login"),
             "draft": bool(p.get("draft"))}
            for p in pulls.data or []
        ] if pulls.ok else None,
        "unreadable": [what for what, response in (("labels", labels), ("open pull requests", pulls), ("the default branch", protection))
                       if not response.ok] + ([] if rulesets is not None else ["rulesets: %s" % message]),
    }
    return facts


def _process_file(path):
    directory, name = os.path.split(path)
    stem = name.split(".")[0].lower()
    return directory in PROCESS_DIRS and stem in PROCESS_STEMS


def _template_file(path):
    lower = path.lower()
    if re.match(r"^\.github/(issue_template|pull_request_template|discussion_template)/", lower):
        return True
    directory, name = os.path.split(lower)
    return directory in ("", "docs", ".github") and name in ("pull_request_template.md", "codeowners")


def instruction_files(paths):
    found = {"instructions": [], "docs_agents": [], "process": [], "github_templates": [], "review_bot_rules": []}
    for path in paths:
        name = path.rsplit("/", 1)[-1]
        if name in INSTRUCTION_NAMES:
            found["instructions"].append({"path": path, "name": name, "nested": "/" in path})
        if path.startswith("docs/agents/"):
            found["docs_agents"].append(path)
        if _process_file(path):
            found["process"].append(path)
        if _template_file(path):
            found["github_templates"].append(path)
        if any(pattern.search(path) for pattern in REVIEW_BOT_FILES):
            found["review_bot_rules"].append(path)
    return found


def _skill_name(root, path, fallback):
    text = _text(root, path) or ""
    if text.startswith("---\n"):
        for line in text.split("\n")[1:]:
            if line == "---":
                break
            if line.startswith("name:"):
                return line[5:].strip().strip("'\"") or fallback
    return fallback


def harness_files(root, paths, home):
    files = dict((d, [p for p in paths if p.startswith(d + "/")]) for d in HARNESS_DIRS)
    files["opencode.json"] = [p for p in paths if p in HARNESS_FILES]
    machine, reason = installed_skills(home)
    machine_names = None if machine is None else sorted(set(machine) | {GENERATOR})
    skills = []
    for path in paths:
        match = SKILL.match(path)
        if not match:
            continue
        name = _skill_name(root, path, match.group(2))
        skills.append({
            "path": path,
            "directory": match.group(2),
            "name": name,
            "shares_machine_skill_name": None if machine_names is None else (name in machine_names or match.group(2) in machine_names),
        })
    return {"files": files, "skills": skills, "machine_skill_set": machine_names,
            "machine_skill_set_unreadable": reason or None}


def commands(root, paths):
    manifests, documents = [], []
    for path in paths:
        name = path.rsplit("/", 1)[-1]
        if "node_modules/" in path:
            continue
        if name in MANIFESTS:
            text = _text(root, path) or ""
            entry = {"path": path, "tool": MANIFESTS[name], "commands": []}
            if name == "package.json":
                try:
                    scripts = json.loads(text).get("scripts") or {}
                except (ValueError, AttributeError):
                    scripts = {}
                    entry["unreadable"] = True
                entry["commands"] = [{"command": "npm run %s" % key, "runs": value} for key, value in sorted(scripts.items())
                                     if isinstance(value, str)]
            elif MANIFESTS[name] in ("make", "just"):
                pattern = _MAKE_TARGET if MANIFESTS[name] == "make" else _JUST_RECIPE
                for line in text.splitlines():
                    match = pattern.match(line)
                    if match and not match.group(1).startswith("."):
                        entry["commands"].append({"command": "%s %s" % (MANIFESTS[name], match.group(1))})
            manifests.append(entry)
        if COMMAND_DOCS.search(path):
            text = _text(root, path) or ""
            fence = None
            for number, line in enumerate(text.splitlines(), 1):
                match = _FENCE.match(line)
                if match and fence is None:
                    fence = match.group(2).lower()
                    continue
                if match and fence is not None:
                    fence = None
                    continue
                if fence in SHELL_FENCES and line.strip():
                    command = line.strip()
                    command = command[2:] if command.startswith("$ ") else command
                    documents.append({"path": path, "line": number, "command": command})
    return {"manifests": manifests, "documents": documents}


def run(worktree, home, env=None):
    """The inspection facts, read without writing."""
    judged = harness.require(env)
    root = checkout.toplevel(worktree)
    if root is None:
        raise GovernError("%s isn't inside a git checkout" % worktree)
    repository = checkout.repository(root)
    gh = github.GitHub(env)
    data = gh.require("repos/%s" % repository, "the repository")
    branch = data.get("default_branch")
    paths = checkout.tracked(root)
    files = instruction_files(paths)
    harness_facts = harness_files(root, paths, home)
    workflow_paths = [p for p in paths if WORKFLOW.match(p)]
    ci = [workflows.inspect(p, _text(root, p) or "", branch) for p in workflow_paths]
    found_commands = commands(root, paths)
    read = set(workflow_paths)
    for key in ("docs_agents", "process", "github_templates", "review_bot_rules"):
        read.update(files[key])
    read.update(entry["path"] for entry in files["instructions"])
    for listed in harness_facts["files"].values():
        read.update(listed)
    read.update(entry["path"] for entry in found_commands["manifests"])
    read.update(p for p in paths if COMMAND_DOCS.search(p))
    read.add(checkout.RECORD_PATH)
    facts = {
        "harness": judged,
        "repository": repository,
        "github": _github(gh, repository, data, branch),
        "record": checkout.read_record(root),
        "instructions": files,
        "harness_files": harness_facts,
        "ci": {"workflows": ci, "none": not ci,
               "secrets": sorted(set(name for workflow in ci for name in workflow["secrets"]))},
        "commands": found_commands,
        "credentials": credentials(root, sorted(p for p in read if p in set(paths))),
        "left_as_they_are": [p for p in ("GLOSSARY.md", "docs/adr") if p in paths or any(x.startswith(p + "/") for x in paths)],
    }
    return facts, 0
