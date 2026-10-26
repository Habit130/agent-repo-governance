"""The template store (#44 §4): versions, the version manifest, the change note, released and installed."""

import json
import os
import shutil
import unittest

import support
from govlib import store

FOUR_CLASSES = os.path.join(support.FIXTURES, "stores", "four-classes")
NOTES = os.path.join(support.FIXTURES, "change-notes")

# #41 §13: the skills the role files rely on, govern-repository aside.
RELIED_ON = {
    "to-spec", "to-tickets", "triage", "wayfinder", "retro",
    "grilling", "domain-modeling", "research", "prototype", "codebase-design", "writing-for-agents",
    "implement-spec", "tdd", "code-review", "pr", "diagnosing-bugs",
}

# The labels the generator creates (#41 §1), with this repository's live colors and descriptions.
LABELS = [
    ("needs-triage", "D4C5F9", "Maintainer needs to evaluate this issue"),
    ("needs-info", "D876E3", "Waiting on reporter for more information"),
    ("ready-for-agent", "0E8A16", "Fully specified, ready for an AFK agent"),
    ("ready-for-human", "FBCA04", "Requires human implementation"),
    ("wontfix", "FFFFFF", "Will not be actioned"),
    ("wayfinder:map", "5319E7", "Wayfinder map: the index of a planning effort"),
    ("wayfinder:research", "1D76DB", "Wayfinder ticket: surface facts a decision waits on"),
    ("wayfinder:prototype", "FBCA04", "Wayfinder ticket: a rough artifact to react to"),
    ("wayfinder:grilling", "D93F0B", "Wayfinder ticket: a decision reached in conversation with habit"),
    ("wayfinder:task", "0E8A16", "Wayfinder ticket: work that must happen before a decision"),
    ("miss", "B60205", "Miss record: something governance should have stopped got through"),
]


def load_expected():
    with open(os.path.join(NOTES, "expected.json")) as handle:
        return json.load(handle)


class ChangeNoteParser(unittest.TestCase):
    def test_reads_both_fields_of_every_valid_note(self):
        for name, fields in load_expected()["valid"].items():
            with open(os.path.join(NOTES, "valid", name), "rb") as handle:
                self.assertEqual(store.parse_change_note(handle.read()), fields, name)

    def test_rejects_every_malformed_note_naming_what_is_wrong(self):
        for name, mentioned in load_expected()["malformed"].items():
            with open(os.path.join(NOTES, "malformed", name), "rb") as handle:
                data = handle.read()
            with self.assertRaises(store.ChangeNoteError, msg=name) as caught:
                store.parse_change_note(data)
            self.assertIn(mentioned, str(caught.exception), name)

    def test_rejects_variants_git_would_flag_as_whitespace(self):
        with open(os.path.join(NOTES, "valid", "urgent-must-act.md"), "rb") as handle:
            good = handle.read()
        variants = {
            "crlf": good.replace(b"\n", b"\r\n"),
            "trailing space": good.replace(b"urgency: urgent\n", b"urgency: urgent \n"),
            "byte order mark": b"\xef\xbb\xbf" + good,
            "not utf-8": good + b"\xff",
            "empty body": b"urgency: urgent\nmust-act: yes\n\n",
            "blank body": b"urgency: urgent\nmust-act: yes\n\n  \n\n",
        }
        for label, data in variants.items():
            with self.assertRaises(store.ChangeNoteError, msg=label):
                store.parse_change_note(data)

    def test_cli_prints_the_fields_and_refuses_a_malformed_note(self):
        code, facts = support.govern(["change-note", os.path.join(NOTES, "valid", "urgent-must-act.md")])
        self.assertEqual((code, facts["urgency"], facts["must_act"]), (0, "urgent", "yes"))
        code, facts = support.govern(["change-note", os.path.join(NOTES, "malformed", "unknown-urgency.md")])
        self.assertEqual(code, 2)
        self.assertIn("urgency", facts["error"])
        code, facts = support.govern(["change-note", os.path.join(NOTES, "no-such-note.md")])
        self.assertEqual(code, 2)
        self.assertIn("no-such-note.md", facts["error"])


class Versions(support.TempDirCase):
    def store_copy(self):
        root = self.path("store")
        shutil.copytree(FOUR_CLASSES, root)
        return root

    def add_version(self, root, number, note=True):
        target = os.path.join(root, str(number))
        shutil.copytree(os.path.join(root, "1"), target)
        manifest_path = os.path.join(target, "manifest.json")
        with open(manifest_path) as handle:
            manifest = json.load(handle)
        manifest["version"] = number
        with open(manifest_path, "w") as handle:
            json.dump(manifest, handle)
        if not note:
            os.remove(os.path.join(target, "change-note.md"))

    def test_a_version_is_released_when_its_change_note_is_present(self):
        root = self.store_copy()
        self.add_version(root, 2, note=True)
        self.add_version(root, 3, note=False)
        templates = store.Store(root)
        self.assertEqual(templates.versions(), [1, 2, 3])
        self.assertEqual(templates.released(), [1, 2])
        self.assertEqual(templates.installed_version(), 2)

    def test_a_store_with_no_released_version_has_no_installed_version(self):
        root = self.store_copy()
        os.remove(os.path.join(root, "1", "change-note.md"))
        self.assertIsNone(store.Store(root).installed_version())

    def test_cli_reports_versions_released_and_installed(self):
        root = self.store_copy()
        self.add_version(root, 2, note=False)
        code, facts = support.govern(["store", "--store", root])
        self.assertEqual(code, 0, facts)
        self.assertEqual(facts["versions"], [1, 2])
        self.assertEqual(facts["released"], [1])
        self.assertEqual(facts["installed_version"], 1)
        self.assertEqual(facts["change_notes"]["1"], {"urgency": "when convenient", "must_act": "yes"})

    def test_refuses_an_entry_that_is_not_a_version_directory(self):
        for stray in ["01", "v2", "draft"]:
            root = self.path("store-" + stray)
            shutil.copytree(FOUR_CLASSES, root)
            os.makedirs(os.path.join(root, stray))
            with self.assertRaises(store.StoreError, msg=stray):
                store.Store(root).versions()

    def test_refuses_a_released_note_that_does_not_parse(self):
        root = self.store_copy()
        shutil.copy(os.path.join(NOTES, "malformed", "unknown-urgency.md"), os.path.join(root, "1", "change-note.md"))
        code, facts = support.govern(["store", "--store", root])
        self.assertEqual(code, 2)
        self.assertIn("change-note.md", facts["error"])


class VersionManifest(support.TempDirCase):
    def test_version_one_lists_the_relied_on_skills_and_the_labels(self):
        manifest = store.Store(support.REAL_STORE).manifest(1)
        self.assertEqual(set(manifest["relied_on_skills"]), RELIED_ON)
        self.assertEqual(len(manifest["relied_on_skills"]), 16)
        self.assertEqual(
            [(label["name"], label["color"], label["description"]) for label in manifest["labels"]], LABELS
        )
        for label in manifest["labels"]:
            self.assertLessEqual(len(label["description"]), 100, label["name"])

    def test_the_real_store_is_valid_and_version_one_is_not_yet_released(self):
        code, facts = support.govern(["store", "--store", support.REAL_STORE])
        self.assertEqual(code, 0, facts)
        self.assertEqual(facts["versions"][0], 1)
        self.assertNotIn(1, facts["released"])

    def test_lists_each_template_with_target_path_class_and_mode(self):
        manifest = store.Store(FOUR_CLASSES).manifest(1)
        self.assertEqual(
            {(t["path"], t["class"], t["mode"]) for t in manifest["templates"]},
            {
                ("AGENTS.md", "fixed part", "100644"),
                (".claude/CLAUDE.md", "fixed part", "100644"),
                ("docs/agents/review.md", "fixed", "100644"),
                ("docs/agents/build.md", "skeleton", "100644"),
                (".github/governance/owner.sh", "fixed", "100755"),
                (".github/governance/record.yml", "record", "100644"),
            },
        )

    def edited(self, change):
        root = self.path("store")
        if os.path.exists(root):
            shutil.rmtree(root)
        shutil.copytree(FOUR_CLASSES, root)
        path = os.path.join(root, "1", "manifest.json")
        with open(path) as handle:
            manifest = json.load(handle)
        change(manifest, root)
        with open(path, "w") as handle:
            json.dump(manifest, handle)
        return store.Store(root)

    def test_refuses_a_manifest_that_disagrees_with_its_templates(self):
        def unknown_class(manifest, root):
            manifest["templates"][0]["class"] = "generated"

        def mode_mismatch(manifest, root):
            for entry in manifest["templates"]:
                if entry["path"] == ".github/governance/owner.sh":
                    entry["mode"] = "100644"

        def missing_template(manifest, root):
            manifest["templates"].append({"path": "docs/agents/planner.md", "class": "fixed", "mode": "100644"})

        def unlisted_template(manifest, root):
            support.write_tree(os.path.join(root, "1", "templates"), {"docs/agents/extra.md": "x\n"})

        def wrong_version(manifest, root):
            manifest["version"] = 2

        def two_records(manifest, root):
            support.write_tree(os.path.join(root, "1", "templates"), {"docs/agents/second.yml": "confirmed:\n"})
            manifest["templates"].append({"path": "docs/agents/second.yml", "class": "record", "mode": "100644"})

        def long_description(manifest, root):
            manifest["labels"][0]["description"] = "x" * 101

        def bad_color(manifest, root):
            manifest["labels"][0]["color"] = "#D4C5F9"

        def skill_named_badly(manifest, root):
            manifest["relied_on_skills"].append("Code Review")

        for change in [
            unknown_class, mode_mismatch, missing_template, unlisted_template, wrong_version,
            two_records, long_description, bad_color, skill_named_badly,
        ]:
            with self.assertRaises(store.StoreError, msg=change.__name__):
                self.edited(change).manifest(1)


if __name__ == "__main__":
    unittest.main()
