"""The owner-script command (#44 §7): the one line habit runs to apply a repository's GitHub target state.

This is its one home. The generator hands it to habit after a merge (#52), and the
live-check runner hands it to habit in a live check, both through `govern.py
owner-command`. habit runs it in Claude Code with the `!` prefix; agents never run it.

The line clones origin's default branch into a temporary directory, detaches at its head,
runs `.github/governance/owner.sh` from there with the maintainer account's own gh
configuration and no token variable, and removes the directory however the script ends.
"""

import re

from . import GovernError

# The maintainer account's own gh configuration, the one habit's `ghm` alias names. The
# command points GH_CONFIG_DIR there and never reads it.
MAINTAINER_GH_CONFIG = "$HOME/.config/gh-maintainer"
TOKEN_VARIABLES = ("GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN")
# The prefix of any other one-line command habit runs as the maintainer account, such as the
# live check's: gh reads the maintainer's configuration, and no token variable overrides it.
MAINTAINER_SHELL = 'export GH_CONFIG_DIR="%s"; unset %s; ' % (MAINTAINER_GH_CONFIG, " ".join(TOKEN_VARIABLES))
SCRIPT = ".github/governance/owner.sh"
_REPOSITORY = re.compile(r"[A-Za-z0-9-]+/[A-Za-z0-9._-]+")

COMMAND = (
    "/bin/bash -c 'set -eu; d=\"$(mktemp -d)\"; trap \"rm -rf \\\"\\$d\\\"\" EXIT; "
    "git clone --quiet --depth 1 --no-checkout https://github.com/%(repository)s.git \"$d/r\"; "
    "git -C \"$d/r\" checkout --quiet --detach origin/HEAD; "
    "env %(unset)s GH_CONFIG_DIR=\"%(config)s\" /bin/bash \"$d/r/%(script)s\"'"
)


def command(repository):
    """The owner-script command for repository, `owner/name`."""
    if not _REPOSITORY.fullmatch(repository or "") or repository.endswith(".git"):
        raise GovernError("%r is not a GitHub repository written owner/name" % repository)
    unset = " ".join("-u " + name for name in TOKEN_VARIABLES)
    return COMMAND % {"repository": repository, "config": MAINTAINER_GH_CONFIG, "script": SCRIPT, "unset": unset}
