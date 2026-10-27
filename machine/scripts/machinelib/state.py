"""The installed state (#26): the commit installed, and each managed skill's content hash as written.

`~/.agents/governance/installed.json` holds `{"commit": <sha>, "skills": {<name>: <hash>}}`.
It is separate from the governance model version: a skill update without a version cut
changes the commit, not the version.
"""

import json
import os
import re

_SHA = re.compile(r"^[0-9a-f]{40}$")
_HASH = re.compile(r"^[0-9a-f]{64}$")


class StateError(Exception):
    pass


def load(home):
    """The installed state, None before the first install, or StateError when it can't be read."""
    if not os.path.lexists(home.state):
        return None
    try:
        with open(home.state) as handle:
            data = json.load(handle)
    except (OSError, ValueError) as error:
        raise StateError("installed state %s 无法读取：%s" % (home.show(home.state), error))
    if (
        not isinstance(data, dict)
        or set(data) != {"commit", "skills"}
        or not isinstance(data["commit"], str)
        or not _SHA.match(data["commit"])
        or not isinstance(data["skills"], dict)
        or not all(isinstance(v, str) and _HASH.match(v) for v in data["skills"].values())
    ):
        raise StateError("installed state %s 的格式不对" % home.show(home.state))
    return data


def save(home, commit, managed):
    if not os.path.isdir(home.governance):
        os.makedirs(home.governance)
    temporary = home.state + ".new"
    with open(temporary, "w", encoding="utf-8") as handle:
        handle.write(json.dumps({"commit": commit, "skills": managed}, indent=2, sort_keys=True) + "\n")
    os.rename(temporary, home.state)
