"""Add an isolated draft v3 to a copy of the real released v1/v2 store."""

import json
import os
import shutil


def add_draft(root):
    target = os.path.join(root, "3")
    shutil.copytree(os.path.join(root, "2"), target)
    os.remove(os.path.join(target, "change-note.md"))
    path = os.path.join(target, "manifest.json")
    with open(path) as handle:
        manifest = json.load(handle)
    manifest["version"] = 3
    with open(path, "w") as handle:
        json.dump(manifest, handle)
