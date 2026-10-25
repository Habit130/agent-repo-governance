#!/bin/bash
# Publishes the current version to npm. Run by a maintainer after a release PR merges.
set -euo pipefail
npm ci
npm run build
npm publish
