# Triage Labels

The engineering skills speak in five canonical triage roles. This file maps each role to the
string the tracker uses (a label, or the `Status:` value of a local issue file) and keeps
the upstream meanings.

| Label in mattpocock/skills | Label in our tracker | Meaning |
| --- | --- | --- |
| `needs-triage` | `needs-triage` | Maintainer needs to evaluate this issue |
| `needs-info` | `needs-info` | Waiting on reporter for more information |
| `ready-for-agent` | `ready-for-agent` | Fully specified, ready for an AFK agent |
| `ready-for-human` | `ready-for-human` | Requires human implementation |
| `wontfix` | `wontfix` | Will not be actioned |

When a skill mentions a role, use the string from this table, and preserve unrelated type
and domain labels.

Governance reads the roles this way:

- `ready-for-agent` states that the issue is fully specified. It never authorizes work:
  dispatch is Orchestration's handoff comment (`delivery.md`).
- `ready-for-human` also marks a contract paused for habit's decision, or one whose repair
  rounds ran out.
- Environment-improvement and follow-up issues open as `needs-triage`.
