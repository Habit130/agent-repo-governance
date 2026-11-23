"""Check explicit Python terminal writes without importing the programs.

Only recognized data-preserving operations carry redaction to a write. An untyped
handle or descriptor can denote either stream. Pathname I/O is checked for explicit
device destinations visible in source. The check does not simulate the filesystem.
"""

import ast
import builtins
from collections import defaultdict
from importlib.util import resolve_name
from itertools import product
import posixpath
from typing import NamedTuple


UNKNOWN = "<unknown>"
UNBOUND = "<unbound>"
MUTATED = "<possibly modified>"
FILE = "<ordinary file>"
PATH = "<pathname>"
UNRESOLVED_PATH = "<unresolved pathname>"
LITERAL = "<literal>:"
CLASS = "<class>:"
INSTANCE = "<instance>:"
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
IMMUTABLE_READERS = {"builtins.str", "builtins.bytes", "builtins.repr", "builtins.len", "builtins.format"}
MAX_ALTERNATIVES = 128
MAX_PATH_COMPONENTS = 4096
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


def imports_govlib(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.level or (node.module or "").split(".")[0] == "govlib"):
            return True
        if isinstance(node, ast.Import) and any(a.name.split(".")[0] == "govlib" for a in node.names):
            return True
    return False


def parameters(args):
    return [a for a in (*args.posonlyargs, *args.args, args.vararg, *args.kwonlyargs, args.kwarg) if a]


def class_id(path, node):
    return "%s:%s:%d" % (path, node.name, node.lineno)


def reads_argument(target, call):
    if target in ("builtins.print", SHARED) or target in IMMUTABLE_READERS:
        return True
    if target == "json.dumps":
        return not any(kw.arg in (None, "default", "cls") for kw in call.keywords)
    return target.startswith((*STREAM_PREFIXES, FILE + ".")) and target.endswith((".write", ".writelines"))


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


def fold_literals(operands, combine):
    """Keep finite literal alternatives. A large product remains an unproven destination."""
    choices, count, complete = [], 1, True
    for origins in operands:
        parts = [value[len(LITERAL):] for value in origins if value.startswith(LITERAL)]
        if not parts:
            return set(), False
        complete &= len(parts) == len(origins)
        count *= len(parts)
        if count > MAX_ALTERNATIVES:
            return {UNRESOLVED_PATH}, False
        choices.append(parts)
    return {LITERAL + combine(parts) for parts in product(*choices)}, complete


def ordinary_suffix(suffix):
    leaf = suffix.rsplit("/", 1)[-1] if suffix else ""
    return leaf not in ("", ".", "..") and not any(name.endswith(leaf) for name in ("stdout", "stderr", "1", "2"))


def device_hint(value):
    if value in ("terminal fd", UNRESOLVED_PATH):
        return True
    if not value.startswith(LITERAL):
        return False
    part = posixpath.normpath(value[len(LITERAL):])
    return (path_origin(part) == "terminal fd" or part in ("/dev", "/dev/fd", "/proc/self/fd")
            or len(part) > 1 and part.startswith("/") and any(path.startswith(part) for path in TERMINAL_PATHS)
            or posixpath.basename(part) in ("stdout", "stderr", "1", "2"))


def joined_paths(operands):
    if not operands:
        return set()  # join() raises before an open or a write can occur.
    candidates, complete = fold_literals(operands, lambda parts: posixpath.join(*parts))
    if complete:
        return candidates
    parts = [literal(values) for values in operands]
    suffix = []
    for part in reversed(parts):
        if part is None:
            break
        suffix.insert(0, part)
        if posixpath.isabs(part):
            return {LITERAL + posixpath.join(*suffix)}
    if suffix and ordinary_suffix(suffix[-1]):
        return candidates | {PATH}
    # A join produces a pathname. Check known device components, including
    # alternatives in branches. General filesystem routing is outside this
    # direct-output check, just as opening a literal log filename is.
    if any(device_hint(value) for values in operands for value in values):
        return candidates | {UNRESOLVED_PATH}
    return candidates | {PATH}


class ListColumn(NamedTuple):
    name: str
    index: int


class ClassHierarchy:
    """Identify field writes that can affect the same instance, including through inherited methods."""

    def __init__(self):
        self.bases = {}
        self.declarations = {}
        self.exported = {}
        self.overlap = None
        self.uncertain = set()

    def register(self, scope, node):
        key = class_id(scope.path, node)
        instance = INSTANCE + key
        self.bases[instance] = (scope, node.bases)
        if isinstance(scope.node, ast.Module):
            module = scope.path.rpartition("/scripts/")[2].removesuffix(".py").replace("/", ".")
            name = module.removesuffix(".__init__") + "." + node.name
            self.declarations[name] = (scope, node, instance)
        return CLASS + key

    def instance_for(self, name):
        return INSTANCE + name[len(CLASS):] if name.startswith(CLASS) else self.exported.get(name)

    def resolve(self, field_writes):
        parents = defaultdict(set)
        unknown = set()
        for name, (scope, node, instance) in self.declarations.items():
            bindings = scope.bindings.get(node.name, ())
            module, _, attribute = name.rpartition(".")
            assignments = [*field_writes.get(attribute, ()), *field_writes.get(None, ())]
            replaced = any(module in writer.origins(receiver) for writer, receiver, _ in assignments)
            if (len(bindings) == 1 and bindings[0][0] is node and not node.decorator_list
                    and node.name not in scope.external_writes
                    and not scope.shared_bindings.get(node.name) and not replaced):
                self.exported[name] = instance
        for child, (scope, bases) in self.bases.items():
            for base in bases:
                for origin in scope.origins(base):
                    parent = self.instance_for(origin)
                    if parent is not None:
                        parents[child].add(parent)
                    else:
                        owner, _, name = origin.rpartition(".")
                        if owner != "builtins" or not isinstance(getattr(builtins, name, None), type):
                            # An imported alias or computed base can still designate a scanned
                            # class. Only a recognized independent base proves separation.
                            unknown.add(child)
        overlap = defaultdict(set)
        for child in self.bases:
            lineage, pending = set(), [child]
            while pending:
                member = pending.pop()
                if member not in lineage:
                    lineage.add(member)
                    pending.extend(parents[member] - lineage)
            if lineage & unknown:
                self.uncertain.update(lineage)
            for member in lineage:
                overlap[member].update(lineage)
        self.overlap = overlap

    def disjoint(self, owner, target):
        return (self.overlap is not None and owner.startswith(INSTANCE) and target is not None
                and owner not in self.uncertain and target not in self.uncertain and owner not in self.overlap[target])


class Scope:
    """Consider every binding in this lexical scope when proving redaction."""

    def __init__(self, node, path, parent=None, path_functions=None, definition_scope=None, field_writes=None,
                 classes=None):
        self.node = node
        self.path = path
        self.parent = parent
        self.classes = classes if parent is None else parent.classes
        self.has_redactor = imports_govlib(node) if parent is None else parent.has_redactor
        self.path_functions = path_functions if parent is None else parent.path_functions
        self.field_writes = field_writes if parent is None else parent.field_writes
        self.fields = None
        self.instance = None
        if definition_scope and isinstance(definition_scope.node, ast.ClassDef):
            self.fields = definition_scope.fields
            self.instance = INSTANCE + class_id(path, definition_scope.node)
        if isinstance(node, ast.ClassDef):
            self.fields = set()
        self.external_writes = set()
        self.shared_bindings = defaultdict(list)
        self.declarations = {}
        self.annotation_locals = set()
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
                origin = self.instance if self.instance and arg.arg == "self" else UNKNOWN
                self.bindings[arg.arg].append((arg, origin, False))
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
        if isinstance(node, ast.ClassDef):
            receiver = INSTANCE + class_id(path, node)
            for name, bindings in self.bindings.items():
                self.fields.add(name)
                self.field_writes[name].extend((self, receiver, value) for _, value, _ in bindings)
        if isinstance(node, ast.Lambda):
            self.returns.append(node.body)
        self.nested_reads = {n.id for child in self.children for n in ast.walk(child) if isinstance(n, ast.Name)}
        if self.has_redactor:
            self.record_escapes()
        for call in self.calls:
            targets = self.origins(call.func)
            if "builtins.setattr" in targets and len(call.args) == 3:
                field = literal(self.origins(call.args[1]))
                self.field_writes[field].append((self, call.args[0], call.args[2]))
            if not self.has_redactor or all(reads_argument(target, call) for target in targets):
                continue
            for arg in [*call.args, *(kw.value for kw in call.keywords)]:
                for ref in self.retained_names(arg):
                    if REDACTED in self.origins(ref):
                        self.invalidate(ref, call)
        local_names = set(self.bindings) | self.annotation_locals
        for name, site in self.mutations:
            for alias in self.related_names(name):
                if alias in self.declarations or alias not in local_names:
                    outer = self.owner_of(alias) if alias in self.declarations else parent and parent.owner_of(alias)
                    if outer is not None and outer is not self:
                        outer.external_writes.update(outer.related_names(alias))
                if alias in local_names:
                    self.bindings[alias].append((site, MUTATED, False))
        for name in self.declarations:
            if name in self.bindings:
                outer = self.owner_of(name)
                if outer:
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

    def record_escapes(self):
        for ref, parent in self.parents.items():
            if isinstance(ref, ast.Name) and isinstance(ref.ctx, ast.Load):
                if (isinstance(parent, (ast.List, ast.Tuple, ast.Dict, ast.Set))
                        or isinstance(parent, ast.Attribute) and parent.attr != "encode"):
                    if REDACTED in self.origins(ref):
                        self.invalidate(ref, parent)
        for value in [*self.returns, *self.escapes]:
            if value is not None:
                for ref in self.retained_names(value):
                    if REDACTED in self.origins(ref):
                        self.invalidate(ref, value)

    def retained_names(self, value):
        """Names whose objects can be returned or stored through this expression."""
        if isinstance(value, ast.Name):
            if isinstance(value.ctx, ast.Load):
                yield value
            return
        if isinstance(value, (ast.JoinedStr, ast.FormattedValue, ast.Constant, ast.Compare)):
            return  # Formatting and comparison cannot retain the original container.
        if isinstance(value, ast.Call):
            targets = self.origins(value.func)
            if targets and targets <= IMMUTABLE_READERS:
                return
        if isinstance(value, ast.IfExp):
            children = (value.body, value.orelse)
        elif isinstance(value, (ast.Subscript, ast.Attribute)):
            children = (value.value,)
        else:
            children = ast.iter_child_nodes(value)
        for child in children:
            yield from self.retained_names(child)

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
                if isinstance(node, ast.ClassDef):
                    symbol = self.classes.register(self, node)
                if isinstance(self.node, ast.Module) and isinstance(node, ast.FunctionDef):
                    if self.path == STORED_FORM and node.name == "check_target":
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
            site, value, definite = node, UNBOUND if isinstance(node.ctx, ast.Del) else UNKNOWN, False
            if isinstance(parent, ast.AnnAssign) and parent.value is None:
                if not isinstance(self.node, (ast.ClassDef, ast.Module)):
                    self.annotation_locals.add(node.id)
                return
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
            self.bindings[node.name].append((node, UNBOUND, False))
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            # Only a plain local copy is covered by the alias graph. A conditional
            # reference or a store through another object can escape anywhere.
            if (any(not isinstance(t, ast.Name) or t.id in self.declarations for t in targets)
                    or isinstance(self.node, ast.ClassDef)
                    or isinstance(node.value, (ast.IfExp, ast.BoolOp, ast.Starred))):
                self.escapes.append(node.value)
        elif (isinstance(node, (ast.Subscript, ast.Attribute)) and isinstance(node.ctx, ast.Store)
              and not (isinstance(parent, ast.AnnAssign) and parent.value is None)):
            self.invalidate(node.value, node)
            if isinstance(node, ast.Attribute):
                value = parent.value if isinstance(parent, (ast.Assign, ast.AnnAssign)) else UNKNOWN
                self.field_writes[node.attr].append((self, node.value, value))
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
        use = (read.lineno, read.col_offset)
        last = None
        if read in self.blocks:
            # A preceding assignment in this same statement list overwrites earlier values.
            # Keep all subsequent possibilities, including conditional assignments and mutations.
            last = max(((site.end_lineno, site.end_col_offset) for site, _, definite in bindings
                        if definite and self.blocks[site] == self.blocks[read]
                        and (site.end_lineno, site.end_col_offset) <= use), default=None)
            if last is not None:
                bindings = [(site, value, definite) for site, value, definite in bindings
                            if last <= (site.end_lineno, site.end_col_offset) <= use]
        values = [value for _, value, _ in bindings]
        if isinstance(self.node, (ast.Module, ast.ClassDef)):
            # Both namespaces can fall back when a conditional binding was skipped or
            # deleted. A class body can also see a writer bound in the enclosing scope.
            guaranteed = last is not None or any(
                definite and self.blocks.get(site) == id(self.node.body)
                and (site.end_lineno, site.end_col_offset) <= use for site, _, definite in bindings
            )
            if not guaranteed:
                values.append(UNBOUND)
        return values

    def owner_of(self, name):
        scope = self
        while scope:
            declaration = scope.declarations.get(name)
            if declaration == "global":
                while scope.parent:
                    scope = scope.parent
                return scope
            if declaration != "nonlocal" and (
                name in scope.bindings or name in scope.annotation_locals or name in scope.shared_bindings
            ):
                return scope
            scope = scope.parent
        return None

    def binding_sources(self, name):
        scope = self.owner_of(name.id)
        if scope is None:
            return [(self, "builtins." + name.id)] if hasattr(builtins, name.id) else []
        sources = [(scope, value) for value in scope.values_at(name.id, name)]
        sources.extend(scope.shared_bindings.get(name.id, ()))
        if not scope.bindings.get(name.id):
            sources.append((scope, UNBOUND))
        if name.id in scope.external_writes:
            sources.append((scope, MUTATED))
        if any(value == UNBOUND for _, value in sources):
            # A missing local raises before the write. Only module and class
            # namespaces can contribute an actual lookup fallback.
            sources = [(owner, value) for owner, value in sources if value != UNBOUND]
            if isinstance(scope.node, ast.ClassDef):
                sources.extend(scope.parent.binding_sources(name))
            elif isinstance(scope.node, ast.Module) and hasattr(builtins, name.id):
                sources.append((scope, "builtins." + name.id))
        return sources

    def origins(self, node, seen=frozenset()):
        """Imported names, output handles, or redacted values this expression can produce."""
        if isinstance(node, str):
            return {node}
        if isinstance(node, ListColumn) and node not in seen:
            return self.column_origins(node, seen | {node})
        if isinstance(node, ast.Name):
            if node not in seen:
                sources = self.binding_sources(node)
                if not sources:
                    return {UNKNOWN}
                result = set().union(*(owner.origins(value, seen | {node}) for owner, value in sources))
                if MUTATED in result:
                    result.discard(MUTATED)
                    # Changing a field can invalidate a payload or callable, but the
                    # receiver remains an instance of the same class.
                    if not result or not all(value.startswith(INSTANCE) for value in result):
                        result.add(UNKNOWN)
                return result
        if isinstance(node, ast.Attribute):
            if (self.fields is not None and isinstance(node.value, ast.Name) and node.value.id == "self"
                    and node.attr in self.fields and node not in seen):
                values = self.field_writes[node.attr] + self.field_writes.get(None, [])
                if self.ordinary_field(values, seen | {node}):
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
        if isinstance(node, ast.JoinedStr):
            parts = []
            possible = set()
            redacted_parts = True
            for part in node.values:
                if isinstance(part, ast.Constant):
                    parts.append({LITERAL + part.value})
                    possible.add(LITERAL + part.value)
                    redacted_parts &= not part.value.strip()
                else:
                    origins = self.origins(part.value, seen)
                    possible.update(origins)
                    simple = part.format_spec is None and part.conversion in (-1, ord("s"))
                    parts.append(origins if simple else {UNKNOWN})
                    redacted_parts &= simple and bool(origins) and origins <= {REDACTED, ENCODED}
            candidates, complete = fold_literals(parts, "".join)
            if complete:
                return candidates
            if redacted_parts:
                return {REDACTED}
            if node.values and isinstance(node.values[-1], ast.Constant) and ordinary_suffix(node.values[-1].value):
                return candidates | {PATH}
            return candidates | {UNRESOLVED_PATH if any(device_hint(v) for v in possible) else PATH}
        if isinstance(node, ast.IfExp):
            body = self.origins(node.body, seen)
            if self.machine_writer and body == {REDACTED} and isinstance(node.orelse, ast.Constant):
                if node.orelse.value == BOOTSTRAP_REFUSAL:
                    return body
            return body | self.origins(node.orelse, seen)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            if isinstance(node.right, ast.Constant) and node.right.value in ("\n", b"\n"):
                return self.origins(node.left, seen)
            operands = (self.origins(node.left, seen), self.origins(node.right, seen))
            candidates, complete = fold_literals(operands, "".join)
            if complete:
                return candidates
            right = literal(operands[1])
            if right is not None:
                return candidates | {PATH if ordinary_suffix(right) else UNRESOLVED_PATH}
            return candidates | {UNKNOWN}
        if isinstance(node, ast.Call):
            return self.call_result(node, seen)
        return {UNKNOWN}

    def ordinary_field(self, writes, seen):
        for writer, receiver, value in writes:
            owners = writer.origins(receiver, seen)
            if owners and all(self.classes.disjoint(owner, self.instance) for owner in owners):
                continue
            if not ordinary_paths(writer.origins(value, seen)):
                return False
        return True

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
        instances = {self.classes.instance_for(name) for name in names}
        if instances and None not in instances:
            return instances
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
            return self.path_value(call.args, seen)
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
            if target is not None and not fd:
                return set()
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

    def path_value(self, args, seen):
        alternatives = self.path_variants(args, seen, {})
        return set().union(*(joined_paths(parts) for parts in alternatives))

    def path_variants(self, args, seen, cache):
        alternatives = {()}
        for arg in args:
            if isinstance(arg, ast.Starred):
                choices = self.unpacked_variants(arg.value, seen, cache)
            else:
                choices = {(frozenset(self.origins(arg, seen)),)}
            if (len(alternatives) * len(choices) > MAX_ALTERNATIVES
                    or max(map(len, alternatives)) + max(map(len, choices)) > MAX_PATH_COMPONENTS):
                alternatives = {(frozenset({UNRESOLVED_PATH}),)}
                continue
            alternatives = {prefix + tail for prefix in alternatives for tail in choices}
        return alternatives

    def unpacked_variants(self, value, seen, cache):
        # Each alternative is one ordered tuple. Defer the join until the outer
        # call knows its prefix and suffix, so components from two tuples never mix.
        key = (self, value)
        if key in cache:
            return cache[key]
        unknown = {(frozenset({UNKNOWN}),)}
        cache[key] = {(frozenset({UNRESOLVED_PATH}),)}  # cyclic or modified sequence
        if isinstance(value, (ast.Tuple, ast.List)):
            options = self.path_variants(value.elts, seen, cache)
        elif isinstance(value, ast.Name) and value not in seen:
            options = set().union(*(owner.unpacked_variants(v, seen | {value}, cache)
                                    for owner, v in self.binding_sources(value)))
        elif isinstance(value, ast.IfExp):
            options = self.unpacked_variants(value.body, seen, cache)
            options = options | self.unpacked_variants(value.orelse, seen, cache)
        elif (isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute) and value.func.attr == "split"
              and len(value.args) == 1 and not value.keywords):
            texts = self.origins(value.func.value, seen)
            separators = self.origins(value.args[0], seen) - {LITERAL}
            options = set()
            if len(texts) * len(separators) > MAX_ALTERNATIVES:
                return cache[key]
            for text, separator in product(texts, separators):
                if text.startswith(LITERAL) and separator.startswith(LITERAL):
                    parts = text[len(LITERAL):].split(separator[len(LITERAL):])
                    options.add(tuple(frozenset({LITERAL + part}) for part in parts))
                else:
                    options.update(unknown)
        elif value == MUTATED:
            return cache[key]
        else:
            options = unknown
        cache[key] = options or unknown
        return cache[key]

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
                descriptors = self.origins(call.args[0]) if call.args else set()
                if descriptors and descriptors != {"other fd"}:
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
        destination = self.origins(options.get("file"))
        if not destination or destination == {FILE}:
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
    if (len(bindings) != 1 or bindings[0][1] != CHECK_TARGET or "check_target" in module.external_writes
            or module.shared_bindings.get("check_target")):
        return False
    for field in ("check_target", None):
        for writer, receiver, _ in module.field_writes.get(field, []):
            if "govlib.storedform" in writer.origins(receiver):
                return False
    helper = next(s for s in module.children if s.node is bindings[0][0])
    return (not helper.node.decorator_list and bool(helper.returns)
            and all(ordinary_paths(helper.origins(value)) for value in helper.returns))


def program_writes(sources):
    path_functions = set()
    trees = {path: ast.parse(source, filename=path) for path, source in sources.items()}
    field_writes = defaultdict(list)
    classes = ClassHierarchy()
    modules = {path: Scope(tree, path, path_functions=path_functions, field_writes=field_writes, classes=classes)
               for path, tree in trees.items()}
    classes.resolve(field_writes)
    if STORED_FORM in modules and verified_path_helper(modules[STORED_FORM]):
        path_functions.add(CHECK_TARGET)
    return [(path, line) for path, scope in modules.items() for line in sorted(scope.problems())]
