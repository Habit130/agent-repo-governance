"""Source-only check for the machine and generator programs' terminal writes."""

import ast
from collections import defaultdict
from importlib.util import resolve_name


UNKNOWN = "<unknown>"
FILE = "<ordinary file>"
REDACTED = "<redacted text>"
ENCODED = "<encoded redacted text>"
SHARED = "govlib.secrets.redact"
SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)
STREAMS = {"sys.stdout", "sys.stderr", "sys.__stdout__", "sys.__stderr__"}
MUTATORS = {"append", "extend", "insert", "update", "setdefault", "__setitem__"}

# If govlib cannot load, #248's machine writer substitutes this fixed refusal.
BOOTSTRAP_REFUSAL = "拒绝：找不到 generator 的 govlib"


class Scope:
    """Consider every binding in this lexical scope when proving redaction."""

    def __init__(self, node, path, parent=None):
        self.node = node
        self.path = path
        self.parent = parent
        self.machine_writer = path == "machine/scripts/machine.py" and getattr(node, "name", "") == "write_line"
        self.bindings = defaultdict(list)
        self.calls = []
        self.children = []
        for child in ast.iter_child_nodes(node):
            self.collect(child, node)

    def collect(self, node, parent):
        if isinstance(node, SCOPES):
            self.children.append(node)
            if hasattr(node, "name"):
                self.bindings[node.name].append(UNKNOWN)
            return
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if isinstance(node, ast.ImportFrom):
                    package = self.path.rpartition("/scripts/")[2].rpartition("/")[0].replace("/", ".")
                    try:
                        module = resolve_name("." * node.level + (node.module or ""), package)
                    except ImportError:
                        module = UNKNOWN
                    self.bindings[alias.asname or alias.name].append(module + "." + alias.name)
                else:
                    first = alias.name.split(".")[0]
                    self.bindings[alias.asname or first].append(alias.name if alias.asname else first)
        elif isinstance(node, ast.arg):
            self.bindings[node.arg].append(UNKNOWN)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            value = UNKNOWN
            if isinstance(parent, (ast.Assign, ast.AnnAssign, ast.NamedExpr)) and parent.value is not None:
                value = parent.value
            elif isinstance(parent, ast.withitem):
                value = parent.context_expr
            self.bindings[node.id].append(value)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            self.bindings[node.name].append(UNKNOWN)
        elif isinstance(node, (ast.Subscript, ast.Attribute)) and isinstance(node.ctx, ast.Store):
            self.invalidate(node.value)
        elif isinstance(node, ast.Call):
            self.calls.append(node)
            if isinstance(node.func, ast.Attribute) and node.func.attr in MUTATORS:
                self.invalidate(node.func.value)
        for child in ast.iter_child_nodes(node):
            self.collect(child, node)

    def invalidate(self, target):
        while isinstance(target, (ast.Subscript, ast.Attribute)):
            target = target.value
        if isinstance(target, ast.Name):
            self.bindings[target.id].append(UNKNOWN)

    def origins(self, node, seen=frozenset()):
        """Imported names, output handles, or redacted values this expression can produce."""
        if isinstance(node, str):
            return {node}
        if isinstance(node, ast.Name):
            scope = self
            while scope and node.id not in scope.bindings:
                scope = scope.parent
            if not scope:
                return {"builtins." + node.id}
            key = (scope, node.id)
            if key not in seen:
                return set().union(*(scope.origins(v, seen | {key}) for v in scope.bindings[node.id]))
        if isinstance(node, ast.Attribute):
            return {name + "." + node.attr for name in self.origins(node.value, seen)}
        if isinstance(node, ast.Constant):
            if node.value is None:
                return {"None"}
            if isinstance(node.value, int):
                return {"terminal fd" if node.value in (1, 2) else "other fd"}
            if node.value in ("/dev/stdout", "/dev/stderr", "/dev/fd/1", "/dev/fd/2",
                              "/proc/self/fd/1", "/proc/self/fd/2"):
                return {"terminal fd"}
        if isinstance(node, ast.IfExp):
            body = self.origins(node.body, seen)
            if self.machine_writer and body == {REDACTED} and isinstance(node.orelse, ast.Constant):
                if node.orelse.value == BOOTSTRAP_REFUSAL:
                    return body
            return body | self.origins(node.orelse, seen)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            if isinstance(node.right, ast.Constant) and node.right.value in ("\n", b"\n"):
                return self.origins(node.left, seen)
        if isinstance(node, ast.Call):
            return self.call_result(node, seen)
        return {UNKNOWN}

    def call_result(self, call, seen):
        names = self.origins(call.func, seen)
        if names - {"None"} == {SHARED}:  # bootstrap failure makes the imported callable None
            return {REDACTED}
        # The machine writer removes additional URI fields from the already-redacted text.
        if self.machine_writer and ast.unparse(call.func) == "_URI.sub" and len(call.args) == 2 and not call.keywords:
            if ast.unparse(call.args[0]) == "_hide_private_uri" and self.origins(call.args[1], seen) == {REDACTED}:
                return {REDACTED}
        if names == {REDACTED + ".encode"} and not call.keywords:
            if all(isinstance(arg, ast.Constant) for arg in call.args):
                return {ENCODED}
        if names == {"json.dumps"} and len(call.args) == 1:
            fixed_options = all(
                kw.arg in ("indent", "sort_keys", "ensure_ascii") and isinstance(kw.value, ast.Constant)
                and isinstance(kw.value.value, (int, type(None))) for kw in call.keywords
            )
            if fixed_options and self.origins(call.args[0], seen) == {REDACTED}:
                return {REDACTED}
        if names in ({"builtins.open"}, {"io.open"}, {"os.fdopen"}):
            options = {kw.arg: kw.value for kw in call.keywords}
            target = call.args[0] if call.args else options.get("fd" if names == {"os.fdopen"} else "file")
            fd = self.origins(target, seen)
            if "terminal fd" in fd:
                mode = call.args[1] if len(call.args) > 1 else options.get("mode")
                if mode is not None and not (isinstance(mode, ast.Constant) and
                                             isinstance(mode.value, str) and "b" not in mode.value):
                    return {"sys.stdout.buffer"}
                return {"sys.stdout"}  # either terminal stream needs redaction
            if target is not None and (names != {"os.fdopen"} or fd == {"other fd"}):
                return {FILE}
        if names in ({"io.StringIO"}, {"io.BytesIO"}):
            return {FILE}
        if any(name.endswith(".fileno") and name.startswith(tuple(s + "." for s in STREAMS)) for name in names):
            return {"terminal fd"}
        if names == {FILE + ".fileno"}:
            return {"other fd"}
        return {UNKNOWN}

    def safe(self, value, binary=False):
        allowed = {ENCODED} if binary else {REDACTED, ENCODED}
        return self.origins(value) <= allowed

    def unredacted(self, call):
        for name in self.origins(call.func):
            if name == "builtins.print":
                if self.unredacted_print(call):
                    return True
            elif name in ("os.write", "os.writev"):
                if call.args and self.origins(call.args[0]) != {"other fd"}:
                    if len(call.args) != 2 or not self.safe_sequence(call.args[1], name == "os.writev", binary=True):
                        return True
            elif name.endswith((".write", ".writelines")) and not name.startswith(FILE + "."):
                # An unresolved handle (including write_line's stream parameter) can be a terminal.
                if len(call.args) != 1 or not self.safe_sequence(
                    call.args[0], name.endswith(".writelines"), binary=".buffer." in name
                ):
                    return True
        return False

    def unredacted_print(self, call):
        options = {kw.arg: kw.value for kw in call.keywords}
        if self.origins(options.get("file")) == {FILE}:
            return False
        values = list(call.args)
        for key in ("sep", "end"):
            value = options.get(key)
            if isinstance(value, ast.Constant) and (value.value is None
                    or isinstance(value.value, str) and not value.value.strip()):
                continue
            if value is not None:
                values.append(value)
        return None in options or not values or not all(self.safe(value) for value in values)

    def safe_sequence(self, value, sequence, binary):
        if sequence and isinstance(value, (ast.List, ast.Tuple)):
            return all(self.safe(item, binary) for item in value.elts)
        return self.safe(value, binary)

    def problems(self):
        lines = [call.lineno for call in self.calls if self.unredacted(call)]
        for child in self.children:
            outer = self.parent if isinstance(self.node, ast.ClassDef) else self
            lines.extend(Scope(child, self.path, outer).problems())
        return lines


def unredacted_writes(path, source):
    """Return line numbers only. Never import a scanned program or echo its source."""
    return sorted(Scope(ast.parse(source, filename=path), path).problems())
