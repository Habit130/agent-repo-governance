# Build and verification

The commands, CI and Actions secrets that a Builder runs and checks, and that a Planner
draws on to write a ticket's Verification. The generator wrote this file at Initialize from
what it ran. It is repository-owned, kept current by this repository's own PRs, and it sits
under `docs/agents/`, a sensitive path with a medium floor, so a PR that edits it is at
least medium.

## Commands

<!-- Replace with the build and test commands the generator ran successfully, in the order
     a Builder runs them, and anything they need, such as a service or no network. -->

| Purpose | Command |
| --- | --- |
| <purpose> | `<command>` |

## CI

<!-- Replace with each workflow that runs on PRs or on the default branch: its jobs,
     triggers and path filters, and which jobs are required checks. With no CI, say so: the
     governance gate is then the only required check, and there is no smoke check. -->

## Actions secrets

<!-- Replace with each Actions secret a workflow uses, GITHUB_TOKEN aside: its name, what CI
     uses it for and the service that issues it, never a value. With none, say that CI uses
     no Actions secret. -->

| Name | Purpose | Issuing service |
| --- | --- | --- |
| `<NAME>` | <purpose> | <issuing service> |

Only habit writes Actions secrets (`AGENTS.md`, Secrets).
