"""GitHub as the agent account, through `gh api`: reads, plus the one write before habit's answer.

Before habit's confirmation a run writes nothing to GitHub (#44 §6), except accepting the
collaborator invitation habit sent from the checklist. So `GitHub` offers GET reads and that
one PATCH, nothing else. Endpoints and what the agent account can read, read 2026-10-29:
`docs/agents/build.md`, The generator's command line.
"""

import json
import re
import subprocess
from urllib.parse import quote

from govlib import GovernError

_HTTP_STATUS = re.compile(r"\(HTTP (\d{3})\)")


class GitHubError(GovernError):
    """A read the facts can't go without failed."""


class Response(object):
    def __init__(self, status, data, message):
        self.status, self.data, self.message = status, data, message

    @property
    def ok(self):
        return self.status == 200


class GitHub(object):
    def __init__(self, env=None):
        self.env = env

    def _call(self, args):
        try:
            result = subprocess.run(
                ["gh", "api"] + args,
                env=self.env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except OSError as error:
            return Response(None, None, "gh can't run: %s" % error)
        out = result.stdout.decode("utf-8", "replace")
        if result.returncode != 0:
            err = result.stderr.decode("utf-8", "replace")
            status = _HTTP_STATUS.search(err)
            message = ""
            try:
                message = json.loads(out).get("message", "")
            except (ValueError, AttributeError):
                pass
            return Response(int(status.group(1)) if status else None, None, message or " ".join(err.split()) or "gh failed")
        if not out.strip():
            return Response(200, None, "")
        try:
            return Response(200, json.loads(out), "")
        except ValueError:
            return Response(None, None, "gh printed something that isn't JSON")

    def get(self, path):
        """One GET; a Response, never raising."""
        return self._call([path])

    def require(self, path, what):
        """One GET whose JSON the facts need; GitHubError when it fails."""
        response = self.get(path)
        if not response.ok:
            raise GitHubError("can't read %s as the agent account: %s" % (what, response.message))
        return response.data

    def accept_invitation(self, invitation_id):
        """The one write before habit's answer: accept a repository invitation habit sent."""
        return self._call(["--method", "PATCH", "user/repository_invitations/%d" % invitation_id])


def branch_path(repository, branch):
    return "repos/%s/branches/%s" % (repository, quote(branch, safe=""))


def branch_rules_path(repository, branch):
    return "repos/%s/rules/branches/%s" % (repository, quote(branch, safe=""))


def rulesets(github, repository):
    """Every ruleset of the repository itself, in full, or None when GitHub won't list them.

    A ruleset whose own read fails keeps what the list gave, with the reason under `unreadable`.
    """
    listed = github.get("repos/%s/rulesets?includes_parents=false&per_page=100" % repository)
    if not listed.ok:
        return None, listed.message
    found = []
    for item in listed.data or []:
        response = github.get("repos/%s/rulesets/%s" % (repository, item["id"]))
        if response.ok:
            found.append(response.data)
        else:
            found.append(dict(item, unreadable=response.message))
    return found, ""


def ruleset_applies(ruleset, branch, applying):
    """Whether a ruleset applies to the default branch: True, False, or None when the agent can't tell."""
    if ruleset.get("target") != "branch":
        return False
    if ruleset.get("id") in applying:
        return True
    ref_name = (ruleset.get("conditions") or {}).get("ref_name") or {}
    names = ("~ALL", "~DEFAULT_BRANCH", branch, "refs/heads/" + branch)
    if any(p in names for p in ref_name.get("exclude") or []):
        return False
    if any(p in names for p in ref_name.get("include") or []):
        return True
    # GitHub lists the active rules on a branch, so an active ruleset that isn't listed
    # doesn't apply; for one that isn't active, only its patterns could tell.
    return False if ruleset.get("enforcement") == "active" else None
