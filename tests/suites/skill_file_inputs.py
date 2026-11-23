"""Source evidence for the machine's ordinary skill-file destination in #254.

The installer stages two kinds of maps: git-tracked relative names, and copies whose
stored names pass the decoder's component checks. The fresh-directory writer relies
on those input contracts. Another caller or a changed derivation loses that proof.
"""

import ast
import hashlib


INSTALL = "machine/scripts/machinelib/install.py"
SKILLS = "machine/scripts/machinelib/skills.py"
STORED = "generator/govern-repository/scripts/govlib/storedform.py"

# Follow the map and its keys. Unrelated statements, docstrings, formatting and the
# wording of refusals do not participate. The producers establish the relative-name
# contract, and the installer forwards those maps into the newly created staging tree.
FLOWS = {
    (SKILLS, "_git"): {"args", "result"},
    (SKILLS, "tracked"): {"out", "path", "prefix", "found"},
    (SKILLS, "machine_skill_set"): {"skill_set", "copies", "tracked", "rel", "inner", "name"},
    (SKILLS, "content_hash"): {"files"},
    (SKILLS, "write_dir"): {"path", "files", "rel", "full"},
    (STORED, "_segments"): {"path", "segments", "segment"},
    (STORED, "decode"): {"stored_path", "segments", "segment", "real", "base"},
    (INSTALL, "run"): {"skill_set", "tools", "_machine_skills", "_replace_dir"},
    (INSTALL, "_machine_skills"): {"files", "skill_set", "_replace_dir"},
    (INSTALL, "_replace_dir"): {"files", "write_dir"},
}
FORWARDERS = {"write_dir", "_replace_dir", "_machine_skills"}
REVIEWED_KEY_FLOW = "0bc8265682dd9747bce269d5fd8c91738d4eb1aaa849fe5b2042d0ec3ca5623a"
PRODUCERS = {"_git", "tracked", "machine_skill_set", "_segments", "decode"}


def name_of(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.alias):
        return node.name.rsplit(".", 1)[-1]
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def syntax(node):
    if (isinstance(node, ast.keyword) and node.arg == "stderr" and isinstance(node.value, ast.Attribute)
            and isinstance(node.value.value, ast.Name) and node.value.value.id == "subprocess"
            and node.value.attr in ("PIPE", "DEVNULL")):
        return ("stderr separate from stdout",)
    if isinstance(node, ast.Raise):
        return ("Raise",)
    if isinstance(node, ast.If) and node.body and isinstance(node.body[-1], ast.Raise):
        return ("IfRaises", syntax(node.test), syntax(node.orelse))
    if isinstance(node, ast.ExceptHandler) and node.body and isinstance(node.body[-1], ast.Raise):
        return ("ExceptRaises", syntax(node.type))
    if isinstance(node, ast.AST):
        return (type(node).__name__, tuple((name, syntax(value)) for name, value in ast.iter_fields(node)
                if value is not None and value != [] and name != "type_comment"))
    if isinstance(node, list):
        return tuple(syntax(item) for item in node)
    return node


def key_flow(function, names):
    rows = [syntax(function.args), syntax(function.decorator_list)]
    if function.name in PRODUCERS:
        return tuple(rows + [syntax(stmt) for stmt in function.body if not (
            isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str)
        )])
    for stmt in ast.walk(function):
        if not isinstance(stmt, ast.stmt) or stmt is function or isinstance(stmt, ast.Raise):
            continue
        inputs = [(field, value) for field, value in ast.iter_fields(stmt)
                  if field not in ("body", "orelse", "handlers", "finalbody")]
        for _, value in inputs:
            roots = value if isinstance(value, list) else [value]
            if any((isinstance(n, ast.Name) and n.id in names) or name_of(n) in FORWARDERS
                   for root in roots if isinstance(root, ast.AST) for n in ast.walk(root)):
                # Changing an assignment target must invalidate the originating expression too.
                rows.append((type(stmt).__name__, tuple((key, syntax(part)) for key, part in inputs
                            if part is not None and key != "type_comment")))
                break
    return tuple(rows)


def input_signature(modules):
    facts = []
    authorized = set()
    for (path, name), keys in FLOWS.items():
        tree = modules.get(path)
        if tree is None:
            return None
        matches = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name]
        if len(matches) != 1:
            return None
        function = matches[0]
        facts.append((path, name, key_flow(function, keys | FORWARDERS)))
        if path == INSTALL:
            authorized.update(n for n in ast.walk(function) if name_of(n) in FORWARDERS)
    for tree in modules.values():
        for node in ast.walk(tree):
            if name_of(node) in FORWARDERS and node not in authorized:
                return None
    return hashlib.sha256(repr(facts).encode("utf-8")).hexdigest()


def relative_skill_inputs(modules):
    return input_signature(modules) == REVIEWED_KEY_FLOW
