"""Check explicit Python terminal writes without importing the programs.

Only recognized data-preserving operations carry redaction to a write. An opaque
destination can be a terminal. Path proofs cover the programs' ordinary file writes.
"""

import ast
from collections import defaultdict
from importlib.util import resolve_name
import posixpath
from typing import NamedTuple

from skill_file_inputs import FLOWS, relative_skill_inputs


UNKNOWN = "<unknown>"
FILE = "<ordinary file>"
PATH = "<pathname>"
UNRESOLVED_PATH = "<unresolved pathname>"
LITERAL = "<literal>:"
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


def matches(node, expression):
    return ast.dump(node) == ast.dump(ast.parse(expression, mode="eval").body)


def function_name(path, name):
    return path.rpartition("/scripts/")[2].removesuffix(".py").replace("/", ".") + "." + name


def parameters(args):
    return [a for a in (*args.posonlyargs, *args.args, args.vararg, *args.kwonlyargs, args.kwarg) if a]


def path_origin(value):
    if isinstance(value, bytes):
        value = value.decode("utf-8", "replace")
    normalized = posixpath.normpath(value)
    if normalized.startswith("//"):
        normalized = "/" + normalized.lstrip("/")
    return "terminal fd" if normalized in TERMINAL_PATHS else PATH


def literal(origins):
    if len(origins) == 1:
        value = next(iter(origins))
        if value.startswith(LITERAL):
            return value[len(LITERAL):]
    return None


def ordinary_paths(origins):
    return bool(origins) and all(value == PATH or value.startswith(LITERAL) and
                                 path_origin(value[len(LITERAL):]) == PATH for value in origins)


def ordinary_suffix(suffix):
    leaf = suffix.rsplit("/", 1)[-1] if suffix else ""
    return leaf not in ("", ".", "..") and not any(name.endswith(leaf) for name in ("stdout", "stderr", "1", "2"))


class ListColumn(NamedTuple):
    name: str
    index: int


class Scope:
    """Consider every binding in this lexical scope when proving redaction."""

    def __init__(self, node, path, parent=None, path_functions=None, definition_scope=None, field_writes=None):
        self.node = node
        self.path = path
        self.parent = parent
        self.path_functions = path_functions if parent is None else parent.path_functions
        self.field_writes = field_writes if parent is None else parent.field_writes
        self.fields = None
        if definition_scope and isinstance(definition_scope.node, ast.ClassDef):
            self.fields = definition_scope.fields
        if isinstance(node, ast.ClassDef):
            self.fields = set()
        self.external_writes = set()
        self.shared_bindings = defaultdict(list)
        self.declarations = {}
        self.machine_writer = path == "machine/scripts/machine.py" and getattr(node, "name", "") == "write_line"
        self.bindings = defaultdict(list)
        self.blocks = {}
        self.parents = {}
        self.aliases = defaultdict(set)
        self.mutations = []
        self.calls = []
        self.returns = []
        self.escapes = []
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
        if isinstance(node, ast.Lambda):
            self.returns.append(node.body)
        self.nested_reads = {n.id for child in self.children for n in ast.walk(child) if isinstance(n, ast.Name)}
        # A helper can modify a redacted list or dictionary it receives.
        for ref, parent_node in self.parents.items():
            if not isinstance(ref, ast.Name) or not isinstance(ref.ctx, ast.Load):
                continue
            if (isinstance(parent_node, (ast.List, ast.Tuple, ast.Dict, ast.Set))
                    or isinstance(parent_node, ast.Attribute) and parent_node.attr != "encode"):
                if REDACTED in self.origins(ref):
                    self.invalidate(ref, parent_node)
        for value in [*self.returns, *self.escapes]:
            if value is not None:
                for ref in ast.walk(value):
                    if isinstance(ref, ast.Name) and REDACTED in self.origins(ref):
                        self.invalidate(ref, value)
        for call in self.calls:
            targets = self.origins(call.func)
            if "builtins.setattr" in targets and len(call.args) == 3:
                field = literal(self.origins(call.args[1]))
                self.field_writes[field].append((self, call.args[2]))
            if all(target in ("builtins.print", SHARED, "json.dumps") or (
                target.startswith((*STREAM_PREFIXES, FILE + "."))
                and target.endswith((".write", ".writelines"))
            ) for target in targets):
                continue
            for arg in [*call.args, *(kw.value for kw in call.keywords)]:
                for ref in ast.walk(arg):
                    if isinstance(ref, ast.Name) and REDACTED in self.origins(ref):
                        self.invalidate(ref, call)
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
                outer = self.owner_of(name)
                if outer:
                    outer.external_writes.update(outer.related_names(name))
                    outer.shared_bindings[name].extend((self, value) for _, value, _ in self.bindings[name])
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
                if isinstance(self.node, ast.Module) and isinstance(node, ast.FunctionDef):
                    if (self.path, node.name) in FLOWS or (self.path == STORED_FORM and node.name == "check_target"):
                        symbol = function_name(self.path, node.name)
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
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            # Only a plain local copy is covered by the alias graph. A conditional
            # reference or a store through another object can escape anywhere.
            if (any(not isinstance(t, ast.Name) for t in targets)
                    or isinstance(node.value, (ast.IfExp, ast.BoolOp, ast.Starred))):
                self.escapes.append(node.value)
        elif isinstance(node, (ast.Subscript, ast.Attribute)) and isinstance(node.ctx, ast.Store):
            self.invalidate(node.value, node)
            if isinstance(node, ast.Attribute):
                value = parent.value if isinstance(parent, (ast.Assign, ast.AnnAssign)) else UNKNOWN
                self.field_writes[node.attr].append((self, value))
                if self.fields is not None and isinstance(node.value, ast.Name) and node.value.id == "self":
                    self.fields.add(node.attr)
        elif isinstance(node, ast.Call):
            self.calls.append(node)
            if isinstance(node.func, ast.Attribute) and node.func.attr in MUTATORS:
                self.invalidate(node.func.value, node)
        elif isinstance(node, ast.AugAssign):
            self.invalidate(node.target, node)
        elif isinstance(node, ast.Return):
            self.returns.append(node.value)
        elif isinstance(node, (ast.Yield, ast.YieldFrom)):
            self.escapes.append(node.value)
        for child in ast.iter_child_nodes(node):
            self.collect(child, node, block)

    def invalidate(self, target, site):
        while isinstance(target, (ast.Subscript, ast.Attribute)):
            target = target.value
        if isinstance(target, ast.Name):
            self.mutations.append((target.id, site))

    def values_at(self, name, read):
        bindings = self.bindings.get(name, ())
        if len(bindings) > 1 and read in self.blocks:
            # A preceding assignment in this same statement list overwrites earlier values.
            # Keep all subsequent possibilities, including conditional assignments and mutations.
            use = (read.lineno, read.col_offset)
            last = max(((site.end_lineno, site.end_col_offset) for site, _, definite in bindings
                        if definite and self.blocks[site] == self.blocks[read]
                        and (site.end_lineno, site.end_col_offset) <= use), default=None)
            if last is not None:
                return [value for site, value, _ in bindings if last <= (site.end_lineno, site.end_col_offset) <= use]
        values = [value for _, value, _ in bindings]
        if isinstance(self.node, ast.Module) and name in ("open", "print"):
            # A conditional module binding can leave the builtin visible, including
            # to a nested function with an explicit global declaration.
            top_level = id(self.node.body)
            use = (read.lineno, read.col_offset)
            if not any(definite and self.blocks.get(site) == top_level
                       and (site.end_lineno, site.end_col_offset) <= use for site, _, definite in bindings):
                values.append("builtins." + name)
        return values

    def owner_of(self, name):
        scope = self
        while scope:
            declaration = scope.declarations.get(name)
            if declaration == "global":
                while scope.parent:
                    scope = scope.parent
                return scope
            if declaration != "nonlocal" and (name in scope.bindings or name in scope.shared_bindings):
                return scope
            scope = scope.parent
        return None

    def origins(self, node, seen=frozenset()):
        """Imported names, output handles, or redacted values this expression can produce."""
        if isinstance(node, str):
            return {node}
        if isinstance(node, ListColumn) and node not in seen:
            return self.column_origins(node, seen | {node})
        if isinstance(node, ast.Name):
            scope = self.owner_of(node.id)
            if not scope:
                return {"builtins." + node.id}
            if node not in seen:
                result = set().union(*(scope.origins(v, seen | {node}) for v in scope.values_at(node.id, node)))
                if not scope.bindings.get(node.id):
                    result.add("builtins." + node.id)
                for writer, value in scope.shared_bindings.get(node.id, ()):
                    result.update(writer.origins(value, seen | {node}))
                if node.id in scope.external_writes:
                    result.add(UNKNOWN)
                return result
        if isinstance(node, ast.Attribute):
            if (self.fields is not None and isinstance(node.value, ast.Name) and node.value.id == "self"
                    and node.attr in self.fields and node not in seen):
                values = self.field_writes[node.attr]
                if (None not in self.field_writes
                        and all(ordinary_paths(scope.origins(value, seen | {node})) for scope, value in values)):
                    return {PATH}
            return {name + "." + node.attr for name in self.origins(node.value, seen)}
        if isinstance(node, ast.Constant):
            if node.value is None:
                return {"None"}
            if isinstance(node.value, int):
                return {"terminal fd" if node.value in (1, 2) else "other fd"}
            if isinstance(node.value, (str, bytes)):
                text = node.value.decode("utf-8", "replace") if isinstance(node.value, bytes) else node.value
                return {LITERAL + text}
        if isinstance(node, ast.IfExp):
            body = self.origins(node.body, seen)
            if self.machine_writer and body == {REDACTED} and isinstance(node.orelse, ast.Constant):
                if node.orelse.value == BOOTSTRAP_REFUSAL:
                    return body
            return body | self.origins(node.orelse, seen)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            if isinstance(node.right, ast.Constant) and node.right.value in ("\n", b"\n"):
                return self.origins(node.left, seen)
            left = literal(self.origins(node.left, seen))
            right = literal(self.origins(node.right, seen))
            if left is not None and right is not None:
                return {LITERAL + left + right}
            if right is not None:
                return {PATH if ordinary_suffix(right) else UNRESOLVED_PATH}
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

    def joins_fresh_skill_directory(self, call):
        """Only the checked relative-name maps can certify this otherwise opaque join."""
        return ("machinelib.skills.write_dir" in self.path_functions
                and self.path == "machine/scripts/machinelib/skills.py"
                and getattr(self.node, "name", "") == "write_dir"
                and matches(call, 'os.path.join(path, *rel.split("/"))'))

    def call_result(self, call, seen):
        names = self.origins(call.func, seen)
        if names == {"builtins.getattr"} and len(call.args) >= 2:
            owners = self.origins(call.args[0], seen)
            attrs = self.origins(call.args[1], seen)
            resolved = {owner + "." + attr[len(LITERAL):] for owner in owners
                        for attr in attrs if attr.startswith(LITERAL)}
            if len(call.args) == 3:
                resolved.update(self.origins(call.args[2], seen))
            if any(not attr.startswith(LITERAL) for attr in attrs):
                resolved.add(UNKNOWN)
                resolved.update(owner + ".write" for owner in owners if owner in STREAMS or owner == "os")
            return resolved
        if names == {"os.path.join"}:
            parts = [literal(self.origins(arg, seen)) for arg in call.args]
            suffix = []
            for part in reversed(parts):
                if part is None:
                    break
                suffix.insert(0, part)
                if posixpath.isabs(part):
                    return {LITERAL + posixpath.join(*suffix)}
            if suffix and len(suffix) == len(parts):
                return {LITERAL + posixpath.join(*suffix)}
            if suffix and ordinary_suffix(suffix[-1]):
                return {PATH}
            if self.joins_fresh_skill_directory(call):
                return {PATH}
            return {UNRESOLVED_PATH}
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
            if fd == {"other fd"} or ordinary_paths(fd) and names != {"os.fdopen"}:
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


def verified_path_helper(module):
    bindings = module.bindings.get("check_target", [])
    if len(bindings) != 1 or bindings[0][1] != CHECK_TARGET or "check_target" in module.external_writes:
        return False
    helper = next(s for s in module.children if s.node is bindings[0][0])
    if helper.returns and all(ordinary_paths(helper.origins(v)) for v in helper.returns):
        return True
    # The generator can also prove a dynamic pathname by rejecting links and existing
    # nonregular files immediately before returning it. A new return path needs evidence.
    if len(helper.returns) != 1 or len(helper.node.body) < 2:
        return False
    guard, result = helper.node.body[-2:]
    return (isinstance(result, ast.Return) and matches(result.value, "full") and isinstance(guard, ast.If)
            and matches(guard.test, "os.path.islink(full) or (os.path.lexists(full) and not os.path.isfile(full))")
            and helper.origins(guard.test.values[0].func) == {"os.path.islink"}
            and len(guard.body) == 1 and isinstance(guard.body[0], ast.Raise) and not guard.orelse
            and helper.origins(result.value) == {UNRESOLVED_PATH})


def program_writes(sources):
    path_functions = set()
    trees = {path: ast.parse(source, filename=path) for path, source in sources.items()}
    field_writes = defaultdict(list)
    modules = {path: Scope(tree, path, path_functions=path_functions, field_writes=field_writes)
               for path, tree in trees.items()}
    if relative_skill_inputs(trees) and bound_skill_inputs(modules, field_writes):
        path_functions.add("machinelib.skills.write_dir")
    if STORED_FORM in modules and verified_path_helper(modules[STORED_FORM]):
        path_functions.add(CHECK_TARGET)
    return [(path, line) for path, scope in modules.items() for line in sorted(scope.problems())]


def bound_skill_inputs(modules, field_writes):
    """The reviewed functions must still be the bindings their callers invoke."""
    if None in field_writes:
        return False
    callees = {name: function_name(path, name) for path, name in FLOWS if name != "run"}
    imported = {
        "skills": "machinelib.skills", "storedform": "govlib.storedform",
        "subprocess": "subprocess", "os": "os",
    }
    for path, name in FLOWS:
        module = modules[path]
        bindings = module.bindings.get(name, ())
        if (len(bindings) != 1 or not isinstance(bindings[0][0], ast.FunctionDef)
                or name in module.external_writes or name in field_writes):
            return False
        function = next(child for child in module.children if child.node is bindings[0][0])
        for ref in function.parents:
            if isinstance(ref, ast.Name) and isinstance(ref.ctx, ast.Load) and ref.id in imported:
                if function.origins(ref) != {imported[ref.id]}:
                    return False
        for call in function.calls:
            callee = call.func
            called = callee.attr if isinstance(callee, ast.Attribute) else getattr(callee, "id", "")
            # A bytes/text decode method is distinct from the stored-path decoder.
            if called == "decode" and not (isinstance(callee, ast.Attribute)
                                          and isinstance(callee.value, ast.Name) and callee.value.id == "storedform"):
                continue
            if called in callees and function.origins(callee) != {callees[called]}:
                return False
    return True
