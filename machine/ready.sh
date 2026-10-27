#!/bin/bash
# The ready command (#44 §8). habit runs the line below, the same every time, in Claude Code
# with the `!` prefix. It clones the latest commit of origin's default branch afresh into a
# temporary directory, installs from that tree into habit's home, and removes the directory.
# README.md and docs/agents/build.md quote the line byte for byte; the machine suites check it.
/bin/bash -c 'set -eu; d="$(mktemp -d)"; trap "rm -rf \"\$d\"" EXIT; git clone --quiet --filter=blob:none https://github.com/Habit130/agent-repo-governance.git "$d/src"; /usr/bin/python3 "$d/src/machine/scripts/machine.py" install --source "$d/src" --home "$HOME"'
