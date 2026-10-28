"""The parsers registered for the shared parser fixtures (#44 §5: one parser per side).

Each side's parser registers as one `Parser` in `PARSERS`: a name and two adapters.

- `record(data)` takes a record file's bytes. It returns the record as
  `{"version": int, "agent_account": str, "sensitive_paths": [{"pattern": str, "floor": str}],
  "confirmed": {"sensitive_paths": [...], "required_checks": [str]}}`, or `DOESNT_PARSE`.
- `pr_body(text)` takes a PR body as text. It returns `{"risk": ..., "reverts": ...}`:
  `risk` is `{"tier": str, "reason": str}` or one of `"missing"`, `"more than one"` and
  `"malformed"`; `reverts` is `None`, `{"sha": str}`, `"more than one"` or `"malformed"`.

`tests/fixtures/parsers/expected.json` holds every fixture's expected result in those shapes,
so registering a parser changes no fixture or expected result. An adapter wraps whatever its
parser offers, an import or a subprocess, and converts the result.
"""

import collections
import importlib.util
import os

import support
from govlib import prbody, record

DOESNT_PARSE = "doesn't parse"

Parser = collections.namedtuple("Parser", "name record pr_body")


def machine_record(data):
    try:
        return record.parse(data)
    except record.RecordError:
        return DOESNT_PARSE


# The gate script's template in version 1's store. Its only token sits in its first line, a
# comment, so the template loads as it is.
GATE = os.path.join(support.REAL_STORE, "1", "templates", "dot-github", "governance", "gate.py")


def load_gate():
    """The gate script's template as a module."""
    spec = importlib.util.spec_from_file_location("governed_gate", GATE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = load_gate()


def governed_record(data):
    try:
        return gate.parse_record(data)
    except gate.RecordError:
        return DOESNT_PARSE


PARSERS = (
    # The generator's library: the drift check, the governed-repository list and the
    # scenario runner use it.
    Parser("machine", machine_record, prbody.parse),
    # The gate script: the gate, Merge watch's script and the owner script use it.
    Parser("governed", governed_record, gate.parse_body),
)
