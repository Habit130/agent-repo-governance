<!-- Repository-owned: written once at Initialize from what the generator ran, then
     maintained by ordinary PRs. No generated notice. -->

# Build

Commands the generator ran successfully at Initialize:

| Purpose | Command |
| --- | --- |
| Install | `npm ci` |
| Lint | `npm run lint` |
| Build | `npm run build` |
| Test | `npm test` |

- CI: `.github/workflows/ci.yml`, job `test`, runs lint, build and test on every PR and on
  every push to `main`. It has no path filters, so it is a required check.
- Tests use the mock sync server; they need no network or token.
- Release: `scripts/release.sh` publishes to npm. Never run it in a delivery; publishing
  is a one-way-door step after merge.
