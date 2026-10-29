#!/bin/bash
# Tags the current commit as a release. Run by habit after a release PR merges.
set -euo pipefail
version="${1:?usage: scripts/release.sh <version>}"
git tag -a "v$version" -m "Release $version"
git push origin "v$version"
