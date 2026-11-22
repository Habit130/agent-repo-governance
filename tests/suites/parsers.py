"""The parsers registered for the shared parser fixtures (#44 §5: machine and governed sides).

The machine parser registers once and every numbered version in the template store contributes
its gate, including the draft. Each `Parser` has a name, two adapters and its governed
version. The machine parser follows the current grammar.

- `record(data)` takes a record file's bytes. It returns the record as
  `{"version": int, "agent_account": str, "sensitive_paths": [{"pattern": str, "floor": str}],
  "confirmed": {"sensitive_paths": [...], "required_checks": [str]}}`, or `DOESNT_PARSE`. From
  version 3, `confirmed` also holds `"review_bots": [str]`.
- `pr_body(text)` takes a PR body as text. It returns `{"risk": ..., "reverts": ...}`:
  `risk` is `{"tier": str, "reason": str}` or one of `"missing"`, `"more than one"` and
  `"malformed"`; `reverts` is `None`, `{"sha": str}`, `"more than one"` or `"malformed"`.

`tests/fixtures/parsers/expected.json` holds every fixture's expected result in those shapes,
so registering a parser changes no fixture or expected result. An adapter wraps whatever its
parser offers, an import or a subprocess, and converts the result.
"""

import collections
import importlib.util

import support
from govlib import prbody, record, store

DOESNT_PARSE = "doesn't parse"


class Parser(collections.namedtuple("Parser", "name record pr_body version")):
    def supports(self, since):
        return self.version is None or self.version >= since


def record_adapter(parse, record_error):
    def parse_record(data):
        try:
            return parse(data)
        except record_error:
            return DOESNT_PARSE

    return parse_record


TEMPLATES = store.Store(support.REAL_STORE)
GATE_PATH = ".github/governance/gate.py"
GATE = TEMPLATES.template_path(1, GATE_PATH)


def load_gate(version=1):
    """The gate script's template as a module."""
    path = TEMPLATES.template_path(version, GATE_PATH)
    spec = importlib.util.spec_from_file_location("governed_gate_v%d" % version, path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except (Exception, SystemExit) as error:
        raise ImportError("cannot load governed-v%d parser from %s" % (version, path)) from error
    return module


_gates = {version: load_gate(version) for version in TEMPLATES.versions()}
gate = _gates[1]  # The gate suite also exercises version 1's module directly.
PARSERS = (
    Parser("machine", record_adapter(record.parse, record.RecordError), prbody.parse, version=None),
) + tuple(
    Parser(
        "governed-v%d" % version,
        record_adapter(module.parse_record, module.RecordError),
        module.parse_body,
        version=version,
    )
    for version, module in _gates.items()
)
