"""#87's source-to-output inventory for Seam A (synthetic values only).

Each row below names an input and an output selector. Exact expected fields prove echo
reachability, not merely scanner reachability. All shapes cross npm values/keys and GitHub
strings; shell commands omit private keys because inspection deliberately discards their
lines (the existing private-key-edge-cases fixture covers that behavior). Make/just extract
only target identifiers, so their plants use the identifier-compatible GitHub shape.
Unsupported manifests echo paths/tool names, not contents; the manifest registry check
keeps that distinction explicit. The document inventory covers every name family, suffix,
nested location and the special build-guide path. New source classes require inventory
review; this is not a claim to discover arbitrary future echo paths automatically.
"""

import ast
import json

import generator_support as gs


MANIFEST_NAMES = ("package.json", "Makefile", "makefile", "GNUmakefile", "justfile", "Justfile")
DOCUMENTS = tuple("coverage/%s%s" % (name, suffix)
                  for name in ("README", "CONTRIBUTING", "development", "hacking", "building", "testing")
                  for suffix in (".md", "-extra.rst", ".txt")) + ("docs/agents/build.md",)
# (source in stand-in GitHub, selector in inspect facts)
GITHUB_STRINGS = (
    ("owner login", ("github", "owner", "login")),
    ("default branch", ("github", "default_branch")),
    ("label name", ("github", "labels", 0, "name")),
    ("label description", ("github", "labels", 0, "description")),
    ("ruleset name", ("github", "rulesets", 0, "name")),
    ("ruleset ref", ("github", "rulesets", 0, "conditions", "ref_name", "include", 0)),
    ("PR title", ("github", "open_pull_requests", 0, "title")),
    ("PR author", ("github", "open_pull_requests", 0, "author")),
    ("setting dictionary key", ("github", "settings", "allow_auto_merge", "<bundle>")),
)


def bundle(private=True, redacted=False):
    names = sorted(gs.SHAPE_PLANTS)
    # A truncated private key consumes the rest of its string, so it goes last.
    names.remove("private key")
    if private:
        names.append("private key")
    return "source-marker " + " | ".join(
        "<redacted %s>" % kind if redacted else gs.PLANTED[gs.SHAPE_PLANTS[kind]] for kind in names)


def case():
    text = bundle()
    token = gs.PLANTED["github-token"]
    files = {"package.json": json.dumps({"scripts": {text: text}})}
    for index, name in enumerate(MANIFEST_NAMES[1:]):
        files["coverage/%d/%s" % (index, name)] = token + ":\n\techo safe\n"
    for path in DOCUMENTS:
        files[path] = "```sh\necho " + bundle(private=False) + "\n```\n"
    return {"run": ["inspect"], "repository": {"files": files}, "github": {
        "owner": [text, "User"], "default_branch": text,
        "labels": [{"name": text, "color": "abcdef", "description": text}],
        "rulesets": [{"id": 7004, "name": text, "target": "branch", "enforcement": "active",
                      "conditions": {"ref_name": {"include": [text], "exclude": []}}, "rules": []}],
        "pulls": [{"number": 1, "title": text, "user": {"login": text}, "draft": False}],
        "settings": {"allow_auto_merge": {text: text}},
    }}


def assert_no_values(test, out, err):
    # Never put a plant or captured output in a failure diagnostic.
    for name, value in gs.PLANTED.items():
        test.assertFalse(value in out or value in err, "plant disclosed: " + name)


def assert_output(test, run):
    code, facts, out, err = run["results"]["inspect"]
    assert_no_values(test, out, err)
    test.assertEqual(code, 0, "inspection refused")
    test.assertEqual(err, "", "inspection wrote stderr")
    expected = bundle(redacted=True)
    for source, selector in GITHUB_STRINGS:
        actual = facts
        for key in selector:
            actual = actual[expected if key == "<bundle>" else key]
        test.assertTrue(actual == expected, "source did not reach expected field: " + source)
    manifests = {entry["path"]: entry for entry in facts["commands"]["manifests"]}
    npm = manifests["package.json"]["commands"]
    test.assertTrue(npm == [{"command": "npm run " + expected, "runs": expected}], "npm keys/values not echoed")
    for index, name in enumerate(MANIFEST_NAMES[1:]):
        tool = "make" if "make" in name.lower() else "just"
        test.assertTrue(manifests["coverage/%d/%s" % (index, name)]["commands"] == [
            {"command": tool + " <redacted GitHub token>"}], "target not echoed: " + name)
    documents = {entry["path"]: entry for entry in facts["commands"]["documents"]}
    for path in DOCUMENTS:
        test.assertTrue(documents[path]["command"] == "echo " + bundle(private=False, redacted=True),
                        "document not echoed: " + path)
    found = {(entry["type"], entry["path"], entry["line"]) for entry in facts["credentials"]}
    for kind in gs.SHAPE_PLANTS:
        test.assertIn((kind, "package.json", 1), found, "type/location not retained: " + kind)
    test.assertEqual(run["before"], run["after"], "inspection changed local state")
    test.assertEqual(gs.writes(run["log"]), [], "inspection wrote to GitHub")
    test.assertFalse(any(not row["recorded"] for row in run["log"]), "unrecorded GitHub read")


def output_writers(text, entry=False):
    """Report direct streams/print/fd writers, including aliases acquired from sys.

    Referencing a process stream is refused outside emit, so assigning it to an alias is
    caught too. This deliberately does not ban subprocess capture or other tools' output.
    Dynamic imports/reflection/native extensions are outside this structural guard.
    """
    tree = ast.parse(text)
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    problems, allowed = [], 0
    sys_names, print_names, os_names, fd_names = {"sys"}, {"print"}, {"os"}, set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "sys":
                    sys_names.add(alias.asname or alias.name)
                if alias.name == "os":
                    os_names.add(alias.asname or alias.name)
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if node.module == "sys" and alias.name in ("stdout", "stderr", "__stdout__", "__stderr__", "*"):
                    problems.append(node.lineno)
                if node.module == "builtins" and alias.name == "print":
                    print_names.add(alias.asname or alias.name)
                if node.module == "os" and alias.name in ("write", "fdopen"):
                    fd_names.add(alias.asname or alias.name)
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id in print_names:
            problems.append(node.lineno)
        if isinstance(node, ast.Attribute) and node.attr == "print" and isinstance(node.value, ast.Name) and node.value.id == "builtins":
            problems.append(node.lineno)
        if isinstance(node, ast.Call):
            fn = node.func
            if ((isinstance(fn, ast.Name) and fn.id in fd_names) or
                    (isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name) and
                     fn.value.id in os_names and fn.attr in ("write", "fdopen"))):
                # Conservatively flag computed descriptors too; ordinary file .write is fine.
                if not node.args or not isinstance(node.args[0], ast.Constant) or node.args[0].value in (1, 2):
                    problems.append(node.lineno)
        if not (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and
                node.value.id in sys_names and node.attr in ("stdout", "stderr", "__stdout__", "__stderr__")):
            continue
        parent = parents.get(node)
        call = parents.get(parent)
        scope = parent
        while scope is not None and not isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef)):
            scope = parents.get(scope)
        if (entry and node.attr == "stdout" and isinstance(parent, ast.Attribute) and parent.attr == "write"
                and isinstance(call, ast.Call) and call.func is parent and
                isinstance(scope, ast.FunctionDef) and scope.name == "emit"):
            allowed += 1
        else:
            problems.append(node.lineno)
    if entry and allowed != 1:
        problems.append("emit must own exactly one stdout writer")
    return problems
