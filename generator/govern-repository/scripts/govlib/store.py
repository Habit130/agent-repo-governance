"""The template store (#44 §4): one directory per governance model version.

Each version directory holds `manifest.json`, the templates in stored form under
`templates/` at the paths they take in a governed repository, and, once the version is
released, `change-note.md`. A version is released when its change note is present, and the
installed version is the highest released version in a store.
"""

import json
import os
import re

from govlib import GovernError, storedform

MANIFEST = "manifest.json"
CHANGE_NOTE = "change-note.md"
TEMPLATES = "templates"

CLASSES = ("fixed", "fixed part", "record", "skeleton")
MODES = ("100644", "100755")
URGENCIES = ("urgent", "when convenient")
MUST_ACT = ("yes", "no")

_VERSION_NAME = re.compile(r"^[1-9][0-9]*$")
_SKILL_NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_COLOR = re.compile(r"^[0-9A-Fa-f]{6}$")
_MANIFEST_KEYS = {"version", "templates", "relied_on_skills", "labels"}
_TEMPLATE_KEYS = {"path", "class", "mode"}
_LABEL_KEYS = {"name", "color", "description"}


class StoreError(GovernError):
    pass


class ChangeNoteError(GovernError):
    pass


def version_name(name):
    """The version a store entry names, or None when the name isn't a version's integer."""
    return int(name) if _VERSION_NAME.match(name) else None


def parse_change_note(data):
    """Read a change note's two fixed fields from its bytes.

    The note opens with `urgency: urgent` or `urgency: when convenient`, then
    `must-act: yes` or `must-act: no`, then a blank line, then its plain-Chinese body.
    """
    if data.startswith(b"\xef\xbb\xbf"):
        raise ChangeNoteError("the change note starts with a byte order mark")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise ChangeNoteError("the change note is not UTF-8")
    if "\r" in text:
        raise ChangeNoteError("the change note has a carriage return; use LF line endings")
    lines = text.split("\n")
    fields = {}
    for index, key, values in ((0, "urgency", URGENCIES), (1, "must-act", MUST_ACT)):
        line = lines[index] if index < len(lines) else ""
        prefix = key + ": "
        if not line.startswith(prefix):
            raise ChangeNoteError(
                "line %d must be `%s<%s>`, and it is %r" % (index + 1, prefix, " | ".join(values), line)
            )
        value = line[len(prefix):]
        if value not in values:
            raise ChangeNoteError("%s must be one of %s, and it is %r" % (key, ", ".join(values), value))
        fields[key.replace("-", "_")] = value
    if len(lines) < 3 or lines[2] != "":
        raise ChangeNoteError("line 3 must be a blank line between the fields and the body")
    if not "\n".join(lines[3:]).strip():
        raise ChangeNoteError("the change note has no body")
    return fields


def validate_manifest(manifest, version):
    """Check a parsed manifest's shape; return it."""
    if not isinstance(manifest, dict) or set(manifest) != _MANIFEST_KEYS:
        raise StoreError("version %d's manifest must hold exactly %s" % (version, ", ".join(sorted(_MANIFEST_KEYS))))
    if manifest["version"] != version:
        raise StoreError("version %d's manifest names version %r" % (version, manifest["version"]))

    templates = manifest["templates"]
    if not isinstance(templates, list):
        raise StoreError("version %d's templates must be a list" % version)
    paths = set()
    records = 0
    for entry in templates:
        if not isinstance(entry, dict) or set(entry) != _TEMPLATE_KEYS:
            raise StoreError("version %d has a template entry without exactly path, class and mode: %r" % (version, entry))
        path = entry["path"]
        if not isinstance(path, str) or path in paths:
            raise StoreError("version %d lists template path %r twice or not as text" % (version, path))
        storedform.encode(path)
        paths.add(path)
        if entry["class"] not in CLASSES:
            raise StoreError("version %d gives %s the unknown class %r" % (version, path, entry["class"]))
        if entry["mode"] not in MODES:
            raise StoreError("version %d gives %s the unknown mode %r" % (version, path, entry["mode"]))
        records += entry["class"] == "record"
    if records > 1:
        raise StoreError("version %d has %d record templates; a version has at most one" % (version, records))

    skills = manifest["relied_on_skills"]
    if not isinstance(skills, list) or len(set(skills)) != len(skills):
        raise StoreError("version %d's relied-on skills must be a list without repeats" % version)
    for skill in skills:
        if not isinstance(skill, str) or not _SKILL_NAME.match(skill):
            raise StoreError("version %d's relied-on skill %r isn't a lowercase-hyphenated name" % (version, skill))

    labels = manifest["labels"]
    if not isinstance(labels, list):
        raise StoreError("version %d's labels must be a list" % version)
    names = set()
    for label in labels:
        if not isinstance(label, dict) or set(label) != _LABEL_KEYS:
            raise StoreError("version %d has a label without exactly name, color and description: %r" % (version, label))
        name = label["name"]
        if not isinstance(name, str) or not name or len(name) > 50 or name in names:
            raise StoreError("version %d's label name %r is empty, too long or repeated" % (version, name))
        names.add(name)
        if not isinstance(label["color"], str) or not _COLOR.match(label["color"]):
            raise StoreError("label %s's color %r isn't six hex digits" % (name, label["color"]))
        description = label["description"]
        if not isinstance(description, str) or len(description) > 100:
            raise StoreError("label %s's description must be text of at most 100 characters" % name)
    return manifest


class Store(object):
    """A template store on disk: the installed one, the source one, or a fixture."""

    def __init__(self, root):
        self.root = os.path.realpath(root)

    def version_dir(self, version):
        return os.path.join(self.root, str(version))

    def versions(self):
        if not os.path.isdir(self.root):
            raise StoreError("the template store %r is not a directory" % self.root)
        found = []
        for name in sorted(os.listdir(self.root)):
            if name in storedform.IGNORED_NAMES:
                continue
            number = version_name(name)
            if number is None or not os.path.isdir(os.path.join(self.root, name)):
                raise StoreError("the template store holds %r, which is not a version directory" % name)
            found.append(number)
        return sorted(found)

    def is_released(self, version):
        return os.path.isfile(os.path.join(self.version_dir(version), CHANGE_NOTE))

    def released(self):
        return [version for version in self.versions() if self.is_released(version)]

    def installed_version(self):
        released = self.released()
        return released[-1] if released else None

    def change_note(self, version):
        path = os.path.join(self.version_dir(version), CHANGE_NOTE)
        with open(path, "rb") as handle:
            data = handle.read()
        try:
            return parse_change_note(data)
        except ChangeNoteError as error:
            raise StoreError("version %d's %s: %s" % (version, CHANGE_NOTE, error))

    def manifest(self, version):
        """Version's manifest, checked against the templates the version directory holds."""
        if version not in self.versions():
            raise StoreError("the template store has no version %d" % version)
        path = os.path.join(self.version_dir(version), MANIFEST)
        try:
            with open(path) as handle:
                manifest = json.load(handle)
        except (OSError, ValueError) as error:
            raise StoreError("version %d's manifest can't be read: %s" % (version, error))
        validate_manifest(manifest, version)

        templates_dir = os.path.join(self.version_dir(version), TEMPLATES)
        stored = {}
        if os.path.isdir(templates_dir):
            stored = dict(storedform.stored_files(templates_dir))
        listed = set()
        for entry in manifest["templates"]:
            stored_path = storedform.encode(entry["path"])
            listed.add(stored_path)
            if stored_path not in stored:
                raise StoreError("version %d lists %s, but %s/%s is missing" % (version, entry["path"], TEMPLATES, stored_path))
            actual = storedform.mode_of(stored[stored_path])
            if actual != entry["mode"]:
                raise StoreError(
                    "version %d lists %s with mode %s, but its stored file has mode %s"
                    % (version, entry["path"], entry["mode"], actual)
                )
        unlisted = sorted(set(stored) - listed)
        if unlisted:
            raise StoreError("version %d holds templates its manifest doesn't list: %s" % (version, ", ".join(unlisted)))
        return manifest

    def template_path(self, version, real_path):
        return os.path.join(self.version_dir(version), TEMPLATES, *storedform.encode(real_path).split("/"))

    def facts(self):
        versions = self.versions()
        for version in versions:
            self.manifest(version)
        released = [version for version in versions if self.is_released(version)]
        return {
            "store": self.root,
            "versions": versions,
            "released": released,
            "installed_version": released[-1] if released else None,
            "change_notes": {str(version): self.change_note(version) for version in released},
        }
