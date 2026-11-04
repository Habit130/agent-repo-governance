#!/bin/bash
# The account wizard's command (#44 §8, #48). habit runs the line below once, in habit's own
# terminal on a new machine, before the first install and before any login. It clones this
# public repository's default branch into a temporary directory, runs the wizard from that
# tree with the terminal attached for the logins, and removes the directory. README.md and
# docs/agents/build.md quote the line byte for byte; the machine-wizard suite checks it.
/bin/bash -c 'set -eu; d="$(mktemp -d)"; trap "rm -rf \"\$d\"" EXIT; git clone --quiet --depth 1 https://github.com/Habit130/agent-repo-governance.git "$d/src"; /usr/bin/python3 "$d/src/machine/scripts/machine.py" wizard'
