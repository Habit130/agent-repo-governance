# governance sandbox

A standing sandbox for live checks of agent-repo-governance. It is not a governed repository:
it holds whatever governance version a live check writes, and nothing here is real.

- `src/auth.py` checks an API token against a stored digest.
- `scripts/release.sh` tags a release.
- `tests/` holds the one CI job's tests, run with Python's standard library.
