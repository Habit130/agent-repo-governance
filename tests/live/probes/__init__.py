"""The live check's probes (#44 §11, step 5), and the one shape every probe takes.

A probe is one `Probe` in a module's `PROBES` tuple in this package. The runner imports
every module here and collects them, so a live-check delivery adds its probes as a new module
and never changes the runner. A probe has:

- `name`: unique across modules, given to `live.py prepare` and `live.py probe` as `--probe`.
- `sandboxes`: the sandboxes it runs in, `public`, `private` or both.
- `commands(context)`: habit's ready commands for this probe, `[(input or None, label,
  line)]`, in order. `prepare` prints them after the pinned merge command and the
  owner-script command, whose report is the input `owner_report` in every check. A command
  with an input gets
  `2>&1 | tee <check directory>/<input>.txt` appended, so its output reaches both habit and
  the probe, which reads it with `context.input(name)`. A missing input fails the probe; it
  is never skipped.
- `run(context)`: the checks, as the agent account. It returns one `Result` per assertion,
  `(assertion, passed, detail)`, in plain English. A probe never writes to GitHub outside
  the sandbox and prints no credential.

The context gives `repository`, `visibility`, `default_branch`, `confirmed` (the sandbox's
fixed confirmed values), `commit` (the PR head the check rendered), `sandbox_pr` and
`directory`, plus `input(name)`, `remember(name, value)` and `recall(name)` for values a later
run of the same check needs, and `api(path)` and `gh(args)` as the agent account.
"""

import collections
import importlib
import json
import os
import pkgutil
import subprocess

Probe = collections.namedtuple("Probe", "name sandboxes commands run")
Result = collections.namedtuple("Result", "assertion passed detail")


class ProbeError(Exception):
    """A probe couldn't read what it checks: one failed result naming why."""


def registered():
    """Every probe in this package, by name; ValueError on a repeated name or a bad shape."""
    found = collections.OrderedDict()
    for info in sorted(pkgutil.iter_modules(__path__), key=lambda module: module.name):
        module = importlib.import_module("%s.%s" % (__name__, info.name))
        for probe in getattr(module, "PROBES", ()):
            if not isinstance(probe, Probe):
                raise ValueError("%s.PROBES holds %r, not a Probe" % (info.name, probe))
            if probe.name in found:
                raise ValueError("two probes are named %s" % probe.name)
            if not set(probe.sandboxes) <= {"public", "private"} or not probe.sandboxes:
                raise ValueError("probe %s names sandboxes %r; it takes public, private or both" % (probe.name, probe.sandboxes))
            found[probe.name] = probe
    return found


class Context(object):
    def __init__(self, repository, visibility, default_branch, confirmed, commit, sandbox_pr, directory):
        self.repository, self.visibility, self.default_branch = repository, visibility, default_branch
        self.confirmed, self.commit, self.sandbox_pr, self.directory = confirmed, commit, sandbox_pr, directory

    def input_path(self, name):
        return os.path.join(self.directory, "%s.txt" % name)

    def input(self, name):
        path = self.input_path(name)
        if not os.path.isfile(path):
            raise ProbeError("the input %s is missing: run habit's command for it first, which writes %s" % (name, path))
        with open(path, encoding="utf-8") as handle:
            return handle.read()

    def remember(self, name, value):
        with open(os.path.join(self.directory, "%s.json" % name), "w") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)

    def recall(self, name):
        path = os.path.join(self.directory, "%s.json" % name)
        if not os.path.isfile(path):
            return None
        with open(path) as handle:
            return json.load(handle)

    def gh(self, args, stdin=None):
        """(exit code, stdout, stderr) of `gh <args>` as the agent account."""
        result = subprocess.run(["gh"] + list(args), input=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                universal_newlines=True)
        return result.returncode, result.stdout, result.stderr

    def api(self, path):
        """The parsed JSON of `gh api <path>` as the agent account; ProbeError on a failure."""
        code, out, err = self.gh(["api", path])
        if code != 0:
            raise ProbeError("`gh api %s` failed: %s" % (path, " ".join(err.split())))
        return json.loads(out) if out.strip() else None


def run(probe, context):
    """A probe's results; a ProbeError or a missing input becomes one failed result."""
    try:
        results = list(probe.run(context))
    except ProbeError as error:
        return [Result("%s ran" % probe.name, False, str(error))]
    if not results:
        return [Result("%s checked something" % probe.name, False, "the probe returned no result")]
    return results
