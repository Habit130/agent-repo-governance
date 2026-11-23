"""Check explicit Python terminal writes without importing the programs.

Only recognized data-preserving operations carry redaction to a write. An opaque
destination can be a terminal. Path proofs cover the programs' ordinary file writes.
"""

import ast
from collections import defaultdict
from importlib.util import resolve_name
import posixpath
from typing import NamedTuple


UNKNOWN = "<unknown>"
FILE = "<ordinary file>"
PATH = "<pathname>"
REDACTED = "<redacted text>"
ENCODED = "<encoded redacted text>"
SHARED = "govlib.secrets.redact"
CHECK_TARGET = "govlib.storedform.check_target"
STORED_FORM = "generator/govern-repository/scripts/govlib/storedform.py"
COMPREHENSIONS = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda) + COMPREHENSIONS
STREAMS = {"sys.stdout", "sys.stderr", "sys.__stdout__", "sys.__stderr__"}
STREAM_PREFIXES = tuple(stream + "." for stream in STREAMS)
MUTATORS = {"append", "extend", "insert", "update", "setdefault", "__setitem__"}
TERMINAL_PATHS = {"/dev/stdout", "/dev/stderr", "/dev/fd/1", "/dev/fd/2", "/proc/self/fd/1", "/proc/self/fd/2"}

# If govlib cannot load, #248's machine writer substitutes this fixed refusal.
BOOTSTRAP_REFUSAL = "拒绝：找不到 generator 的 govlib"
# The reviewed replacement only copies substrings of the redacted match or fixed
# labels. A different callback must establish its output provenance separately.
URI_REPLACEMENT = ast.parse('''\
def _hide_private_uri(match):
    uri = match[0]
    if any(part in uri for part in "@?#"):
        markers = [marker for marker in _TYPE_MARKERS if marker in uri]
        return (match["before"] or "") + ("、".join(markers) or "（已隐藏）")
    return uri
''').body[0]


def parameters(args):
    return [a for a in (*args.posonlyargs, *args.args, args.vararg, *args.kwonlyargs, args.kwarg) if a]


def path_origin(value):
    if isinstance(value, bytes):
        value = value.decode("utf-8", "replace")
    return "terminal fd" if posixpath.normpath(value) in TERMINAL_PATHS else PATH


class ListColumn(NamedTuple):
    name: str
    index: int


class Scope:
    """Consider every binding in this lexical scope when proving redaction."""

    def __init__(self, node, path, parent=None, path_functions=None, definition_scope=None):
        self.node = node
        self.path = path
        self.parent = parent
        self.path_functions = path_functions if parent is None else parent.path_functions
        self.fields = None
        if definition_scope and isinstance(definition_scope.node, ast.ClassDef):
            self.fields = definition_scope.fields
        if isinstance(node, ast.ClassDef):
            self.fields = defaultdict(list)
        self.external_writes = set()
        self.declarations = {}
        self.machine_writer = path == "machine/scripts/machine.py" and getattr(node, "name", "") == "write_line"
        self.bindings = defaultdict(list)
        self.blocks = {}
        self.parents = {}
        self.aliases = defaultdict(set)
        self.mutations = []
        self.calls = []
        self.returns = []
        self.children = []
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            for arg in parameters(node.args):
                self.bindings[arg.arg].append((arg, UNKNOWN, False))
            defaults = zip(reversed(node.args.posonlyargs + node.args.args), reversed(node.args.defaults))
            for arg, default in [*defaults, *zip(node.args.kwonlyargs, node.args.kw_defaults)]:
                if default is not None:
                    for symbol in definition_scope.origins(default):
                        self.bindings[arg.arg].append((arg, symbol, False))
        if isinstance(node, COMPREHENSIONS):
            first, *rest = node.generators
            expressions = [node.key, node.value] if isinstance(node, ast.DictComp) else [node.elt]
            body = [first.target, *first.ifs, *rest, *expressions]
        else:
            body = node.body if isinstance(node.body, list) else [node.body]
        for child in body:
            self.collect(child, node)
        self.nested_reads = {n.id for child in self.children for n in ast.walk(child) if isinstance(n, ast.Name)}
        # A helper can modify a redacted list or dictionary it receives.
        for call in self.calls:
            for arg in [*call.args, *(kw.value for kw in call.keywords)]:
                if isinstance(arg, ast.Name) and REDACTED in self.origins(arg):
                    targets = self.origins(call.func)
                    if not all(target in ("builtins.print", SHARED, "json.dumps")
                               or target.endswith((".write", ".writelines")) for target in targets):
                        self.invalidate(arg, call)
        local_names = set(self.bindings)
        for name, site in self.mutations:
            if name not in local_names and parent:
                outer = parent
                while outer.parent and name not in outer.bindings:
                    outer = outer.parent
                outer.external_writes.update(outer.related_names(name))
            for alias in self.related_names(name):
                self.bindings[alias].append((site, UNKNOWN, False))
        for name, declaration in self.declarations.items():
            if name in self.bindings:
                outer = parent
                while outer and outer.parent and (declaration == "global" or name not in outer.bindings):
                    outer = outer.parent
                if outer:
                    outer.external_writes.update(outer.related_names(name))
        outer = parent if isinstance(node, ast.ClassDef) else self
        self.children = [Scope(child, path, outer, definition_scope=self) for child in self.children]

    def related_names(self, name):
        pending, reached = [name], set()
        while pending:
            alias = pending.pop()
            if alias not in reached:
                reached.add(alias)
                pending.extend(self.aliases[alias] - reached)
        return reached

    def collect(self, node, parent, block=None):
        if isinstance(node, ast.stmt):
            block = next(id(items) for _, items in ast.iter_fields(parent)
                         if isinstance(items, list) and node in items)
        self.blocks[node] = block
        self.parents[node] = parent
        if isinstance(node, SCOPES):
            self.children.append(node)
            if isinstance(node, COMPREHENSIONS):
                self.collect(node.generators[0].iter, node, block)
                return
            if hasattr(node, "name"):
                symbol = UNKNOWN
                if self.path == STORED_FORM and node.name == "check_target" and isinstance(self.node, ast.Module):
                    symbol = CHECK_TARGET
                if node.name == "_hide_private_uri" and ast.dump(node) == ast.dump(URI_REPLACEMENT):
                    symbol = "<reviewed regex replacement>"
                self.bindings[node.name].append((node, symbol, True))
            expressions = list(getattr(node, "decorator_list", []))
            if isinstance(node, ast.ClassDef):
                expressions.extend([*node.bases, *node.keywords])
            else:
                expressions.extend([*node.args.defaults, *node.args.kw_defaults, getattr(node, "returns", None)])
                expressions.extend(arg.annotation for arg in parameters(node.args))
            for expr in expressions:
                if expr is not None:
                    self.collect(expr, node, block)
            return
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if isinstance(node, ast.ImportFrom):
                    package = self.path.rpartition("/scripts/")[2].rpartition("/")[0].replace("/", ".")
                    try:
                        module = resolve_name("." * node.level + (node.module or ""), package)
                    except ImportError:
                        module = UNKNOWN
                    self.bindings[alias.asname or alias.name].append((node, module + "." + alias.name, True))
                else:
                    first = alias.name.split(".")[0]
                    self.bindings[alias.asname or first].append((node, alias.name if alias.asname else first, True))
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            declaration = "global" if isinstance(node, ast.Global) else "nonlocal"
            self.declarations.update(dict.fromkeys(node.names, declaration))
        elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            site, value, definite = node, UNKNOWN, False
            if isinstance(parent, (ast.Assign, ast.AnnAssign, ast.NamedExpr)) and parent.value is not None:
                site = parent
                value = parent.value
                definite = isinstance(parent, (ast.Assign, ast.AnnAssign))
                root = value
                while isinstance(root, ast.Subscript):
                    root = root.value
                if isinstance(root, ast.Name):
                    self.aliases[node.id].add(root.id)
                    self.aliases[root.id].add(node.id)
            elif isinstance(parent, ast.withitem):
                value = parent.context_expr
            elif isinstance(parent, ast.Tuple):
                loop = self.parents.get(parent)
                if isinstance(loop, ast.For) and loop.target is parent and isinstance(loop.iter, ast.Name):
                    value = ListColumn(loop.iter.id, parent.elts.index(node))
            self.bindings[node.id].append((site, value, definite))
        elif isinstance(node, ast.ExceptHandler) and node.name:
            self.bindings[node.name].append((node, UNKNOWN, False))
        elif isinstance(node, (ast.Subscript, ast.Attribute)) and isinstance(node.ctx, ast.Store):
            self.invalidate(node.value, node)
            if (self.fields is not None and isinstance(node, ast.Attribute)
                    and isinstance(node.value, ast.Name) and node.value.id == "self"):
                value = parent.value if isinstance(parent, (ast.Assign, ast.AnnAssign)) else UNKNOWN
                self.fields[node.attr].append((self, value))
        elif isinstance(node, ast.Call):
            self.calls.append(node)
            if isinstance(node.func, ast.Attribute) and node.func.attr in MUTATORS:
                self.invalidate(node.func.value, node)
        elif isinstance(node, ast.Return):
            self.returns.append(node.value)
        for child in ast.iter_child_nodes(node):
            self.collect(child, node, block)

    def invalidate(self, target, site):
        while isinstance(target, (ast.Subscript, ast.Attribute)):
            target = target.value
        if isinstance(target, ast.Name):
            self.mutations.append((target.id, site))

    def values_at(self, name, read):
        bindings = self.bindings[name]
        if isinstance(self.node, ast.Module) and name in ("open", "print") and read in self.blocks:
            if all((s.end_lineno, s.end_col_offset) > (read.lineno, read.col_offset) for s, _, _ in bindings):
                return ["builtins." + name]
        if len(bindings) > 1 and read in self.blocks:
            # A preceding assignment in this same statement list overwrites earlier values.
            # Keep all subsequent possibilities, including conditional assignments and mutations.
            use = (read.lineno, read.col_offset)
            last = max(((site.end_lineno, site.end_col_offset) for site, _, definite in bindings
                        if definite and self.blocks[site] == self.blocks[read]
                        and (site.end_lineno, site.end_col_offset) <= use), default=None)
            if last is not None:
                return [value for site, value, _ in bindings if last <= (site.end_lineno, site.end_col_offset) <= use]
        return [value for _, value, _ in bindings]

    def origins(self, node, seen=frozenset()):
        """Imported names, output handles, or redacted values this expression can produce."""
        if isinstance(node, str):
            return {node}
        if isinstance(node, ListColumn) and node not in seen:
            return self.column_origins(node, seen | {node})
        if isinstance(node, ast.Name):
            scope = self
            while scope and node.id not in scope.bindings:
                scope = scope.parent
            if not scope:
                return {"builtins." + node.id}
            if node not in seen:
                result = set().union(*(scope.origins(v, seen | {node}) for v in scope.values_at(node.id, node)))
                if node.id in scope.external_writes:
                    result.add(UNKNOWN)
                return result
        if isinstance(node, ast.Attribute):
            if (self.fields is not None and isinstance(node.value, ast.Name) and node.value.id == "self"
                    and node.attr in self.fields and node not in seen):
                values = self.fields[node.attr]
                if all(scope.origins(value, seen | {node}) == {PATH} for scope, value in values):
                    return {PATH}
            return {name + "." + node.attr for name in self.origins(node.value, seen)}
        if isinstance(node, ast.Constant):
            if node.value is None:
                return {"None"}
            if isinstance(node.value, int):
                return {"terminal fd" if node.value in (1, 2) else "other fd"}
            if isinstance(node.value, (str, bytes)):
                return {path_origin(node.value)}
        if isinstance(node, ast.IfExp):
            body = self.origins(node.body, seen)
            if self.machine_writer and body == {REDACTED} and isinstance(node.orelse, ast.Constant):
                if node.orelse.value == BOOTSTRAP_REFUSAL:
                    return body
            return body | self.origins(node.orelse, seen)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            if isinstance(node.right, ast.Constant) and node.right.value in ("\n", b"\n"):
                return self.origins(node.left, seen)
            if isinstance(node.right, ast.Constant) and isinstance(node.right.value, str):
                if isinstance(node.left, ast.Constant) and isinstance(node.left.value, str):
                    return {path_origin(node.left.value + node.right.value)}
                return {PATH}
        if isinstance(node, ast.Call):
            return self.call_result(node, seen)
        return {UNKNOWN}

    def column_origins(self, column, seen):
        """Marker repair opens paths from local (checked path, text) pairs. An escaping list loses that proof."""
        if column.name in self.nested_reads:
            return {UNKNOWN}
        values = set()
        initialized = False
        for ref, parent in self.parents.items():
            if not isinstance(ref, ast.Name) or ref.id != column.name:
                continue
            if isinstance(parent, ast.For) and parent.iter is ref:
                continue
            if isinstance(ref.ctx, ast.Store):
                assign = self.parents[parent] if isinstance(parent, ast.Tuple) else parent
                if not isinstance(assign, ast.Assign):
                    return {UNKNOWN}
                initial = assign.value
                if isinstance(parent, ast.Tuple):
                    if not isinstance(initial, ast.Tuple) or len(initial.elts) != len(parent.elts):
                        return {UNKNOWN}
                    initial = initial.elts[parent.elts.index(ref)]
                if not isinstance(initial, ast.List) or initial.elts:
                    return {UNKNOWN}
                initialized = True
                continue
            call = self.parents.get(parent)
            if not (isinstance(parent, ast.Attribute) and parent.attr == "append"
                    and isinstance(call, ast.Call) and call.func is parent and len(call.args) == 1):
                return {UNKNOWN}
            row = call.args[0]
            if not isinstance(row, ast.Tuple) or len(row.elts) <= column.index:
                return {UNKNOWN}
            values.update(self.origins(row.elts[column.index], seen))
        return values if initialized and values else {UNKNOWN}

    def call_result(self, call, seen):
        names = self.origins(call.func, seen)
        if names == {"builtins.getattr"} and len(call.args) >= 2:
            attr = call.args[1]
            if isinstance(attr, ast.Constant) and isinstance(attr.value, str):
                return {value + "." + attr.value for value in self.origins(call.args[0], seen)}
        if names == {"os.path.join"}:
            if call.args and all(isinstance(arg, ast.Constant) and isinstance(arg.value, str) for arg in call.args):
                return {path_origin(posixpath.join(*(arg.value for arg in call.args)))}
            return {PATH}
        if names == {CHECK_TARGET} and CHECK_TARGET in self.path_functions:
            return {PATH}
        if names == {"re.compile"}:
            return {"<compiled regex>"}
        if names - {"None"} == {SHARED}:  # bootstrap failure makes the imported callable None
            return {REDACTED}
        # The machine writer removes additional URI fields from the already-redacted text.
        if self.machine_writer and names == {"<compiled regex>.sub"} and len(call.args) == 2 and not call.keywords:
            if (self.origins(call.args[0], seen) == {"<reviewed regex replacement>"}
                    and self.origins(call.args[1], seen) == {REDACTED}):
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
            if fd == {"other fd"} or fd == {PATH} and names != {"os.fdopen"}:
                return {FILE}
            mode = call.args[1] if len(call.args) > 1 else options.get("mode")
            if mode is not None and not (isinstance(mode, ast.Constant) and
                                         isinstance(mode.value, str) and "b" not in mode.value):
                return {"sys.stdout.buffer"}
            return {"sys.stdout"}  # an unresolved descriptor can designate either terminal stream
        if names in ({"io.StringIO"}, {"io.BytesIO"}):
            return {FILE}
        if any(name.endswith(".fileno") and name.startswith(STREAM_PREFIXES) for name in names):
            return {"terminal fd"}
        if names == {FILE + ".fileno"}:
            return {"other fd"}
        return {UNKNOWN}

    def safe(self, value, binary=False):
        allowed = {ENCODED} if binary else {REDACTED, ENCODED}
        origins = self.origins(value)
        return bool(origins) and origins <= allowed

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
            lines.extend(child.problems())
        return lines


def unredacted_writes(path, source):
    """Return line numbers only. Never import a scanned program or echo its source."""
    return [line for _, line in program_writes({path: source})]


def program_writes(sources):
    path_functions = set()
    modules = {path: Scope(ast.parse(source, filename=path), path, path_functions=path_functions)
               for path, source in sources.items()}
    if STORED_FORM in modules:
        helpers = [s for s in modules[STORED_FORM].children if getattr(s.node, "name", "") == "check_target"]
        if len(helpers) == 1 and helpers[0].returns:
            if all(helpers[0].origins(value) == {PATH} for value in helpers[0].returns):
                path_functions.add(CHECK_TARGET)
    return [(path, line) for path, scope in modules.items() for line in sorted(scope.problems())]
