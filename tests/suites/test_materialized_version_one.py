"""Governance model version one: rendered policy-text checks."""

import os

import materialized
import parsers
import support
from govlib import record, render, store
from test_record import DEFAULT_PATTERNS, RECORD
from materialized_version_support import (
    AGENTS, AGENTS_BUDGET, AGENTS_SECTIONS, BEGIN_MARKER, BUGBOT, BUILD_SKELETON,
    CLAUDE, CODE_REVIEW_RULES, END_MARKER, GATE_FILES, MARKDOWN_NOTICE,
    MERGE_WATCH_FILES, MIXED_FILES, MIXED_NOTICE, NEVER_WRITTEN, NOTICE,
    NOT_RELIED_ON, OWNER_SCRIPT, PR_TEMPLATE, REPOSITORY_SECTIONS,
    ROLE_AND_REVIEW_FILES, ROLE_FILES, ROLE_SKILLS, SKILLS_HEADING, TRACKER_FILES,
    TRIAGE_LABELS, budget_failures, bugbot_failures, comment_line_failures,
    comment_line_numbers, headings, label_mismatches, marker_failures,
    pointer_targets, role_skills, routing_failures, skill_mismatches,
    triage_role_failures,
)


class MaterializedVersionOne(support.TempDirCase):
    def setUp(self):
        super(MaterializedVersionOne, self).setUp()
        self.worktree, self.render_facts = materialized.render_version_one(self.tmp)

    def test_exact_comparison_finds_no_difference(self):
        code, facts = materialized.compare_version_one(self.worktree)
        self.assertEqual(code, 0, facts)
        self.assertEqual(facts["differences"], [])
        self.assertEqual((facts["repository"], facts["default_branch"]), ("Habit130/tally", "main"))
        self.assertIn(RECORD, facts["checked"])

    def test_rendering_writes_only_the_versions_templates(self):
        status = support.git(self.worktree, "status", "--porcelain", "--untracked-files=all")
        changed = sorted(line[3:] for line in status.splitlines())
        self.assertEqual(changed, sorted(self.render_facts["written"]))

    def test_tally_keeps_its_own_files_and_modes(self):
        self.assertEqual(support.file_mode(os.path.join(self.worktree, "scripts", "release.sh")), "100755")
        self.assertTrue(os.path.isfile(os.path.join(self.worktree, ".github", "workflows", "ci.yml")))
        self.assertTrue(os.path.isfile(os.path.join(self.worktree, ".gitignore")))

    # #41's template tickets add their seam-3 checks below, against self.worktree.

    def test_the_gate_workflow_and_script_carry_the_notice_with_their_placeholders_resolved(self):
        for path in GATE_FILES:
            text = support.read_text(os.path.join(self.worktree, *path.split("/")))
            self.assertEqual(text.split("\n")[0], NOTICE, path)
            self.assertNotIn("@@", text, path)
        workflow = support.read_text(os.path.join(self.worktree, ".github", "workflows", "governance-gate.yml"))
        self.assertIn('    branches:\n      - "main"\n', workflow)

    def test_the_gate_files_keep_their_mode_and_pass_exact_comparison(self):
        code, facts = materialized.compare_version_one(self.worktree)
        self.assertEqual(code, 0, facts)
        for path in GATE_FILES:
            self.assertIn(path, facts["checked"])
            self.assertEqual(support.file_mode(os.path.join(self.worktree, *path.split("/"))), "100644", path)

    def test_merge_watchs_workflow_and_script_carry_the_notice_keep_their_mode_and_pass_exact_comparison(self):
        entries = {entry["path"]: entry for entry in store.Store(support.REAL_STORE).manifest(1)["templates"]}
        code, facts = materialized.compare_version_one(self.worktree)
        self.assertEqual(code, 0, facts)
        for path in MERGE_WATCH_FILES:
            text = support.read_text(os.path.join(self.worktree, *path.split("/")))
            self.assertEqual(text.split("\n")[0], NOTICE, path)
            self.assertNotIn("@@", text, path)
            self.assertEqual((entries[path]["class"], entries[path]["mode"]), ("fixed", "100644"), path)
            self.assertEqual(support.file_mode(os.path.join(self.worktree, *path.split("/"))), "100644", path)
            self.assertIn(path, facts["checked"])
        workflow = support.read_text(os.path.join(self.worktree, *MERGE_WATCH_FILES[0].split("/")))
        self.assertEqual(workflow.count('      - "main"\n'), 2)

    def test_the_owner_script_carries_the_notice_after_its_shebang_and_stays_executable(self):
        text = support.read_text(os.path.join(self.worktree, *OWNER_SCRIPT.split("/")))
        self.assertEqual(text.split("\n")[:2], ["#!/bin/bash", NOTICE])
        self.assertNotIn("@@", text)
        self.assertEqual(support.file_mode(os.path.join(self.worktree, *OWNER_SCRIPT.split("/"))), "100755")
        entries = {entry["path"]: entry for entry in store.Store(support.REAL_STORE).manifest(1)["templates"]}
        self.assertEqual((entries[OWNER_SCRIPT]["class"], entries[OWNER_SCRIPT]["mode"]), ("fixed", "100755"))
        code, facts = materialized.compare_version_one(self.worktree)
        self.assertEqual(code, 0, facts)
        self.assertIn(OWNER_SCRIPT, facts["checked"])

    def test_the_role_files_and_review_md_carry_the_notice_and_pass_exact_comparison(self):
        code, facts = materialized.compare_version_one(self.worktree)
        self.assertEqual(code, 0, facts)
        for path in ROLE_AND_REVIEW_FILES:
            text = support.read_text(os.path.join(self.worktree, *path.split("/")))
            self.assertEqual(text.split("\n")[0], MARKDOWN_NOTICE, path)
            self.assertNotIn("@@", text, path)
            self.assertIn(path, facts["checked"])
            self.assertEqual(support.file_mode(os.path.join(self.worktree, *path.split("/"))), "100644", path)

    def test_the_tracker_label_domain_files_and_pr_template_carry_the_notice_and_pass_exact_comparison(self):
        code, facts = materialized.compare_version_one(self.worktree)
        self.assertEqual(code, 0, facts)
        for path in TRACKER_FILES:
            text = support.read_text(os.path.join(self.worktree, *path.split("/")))
            self.assertEqual(text.split("\n")[0], MARKDOWN_NOTICE, path)
            self.assertNotIn("@@", text, path)
            self.assertIn(path, facts["checked"])
            self.assertEqual(support.file_mode(os.path.join(self.worktree, *path.split("/"))), "100644", path)
        tracker = support.read_text(os.path.join(self.worktree, "docs", "agents", "issue-tracker.md"))
        self.assertIn("--repo Habit130/tally", tracker)

    def test_the_build_skeleton_is_written_without_the_notice_and_left_uncompared(self):
        entries = {entry["path"]: entry for entry in store.Store(support.REAL_STORE).manifest(1)["templates"]}
        self.assertEqual(entries[BUILD_SKELETON]["class"], "skeleton")
        self.assertIn(BUILD_SKELETON, self.render_facts["written"])
        text = support.read_text(os.path.join(self.worktree, *BUILD_SKELETON.split("/")))
        self.assertNotIn("Generated by governance model", text)
        self.assertNotIn("@@", text)
        code, facts = materialized.compare_version_one(self.worktree)
        self.assertEqual(code, 0, facts)
        self.assertNotIn(BUILD_SKELETON, facts["checked"])
        self.assertEqual(facts["not_compared"], {BUILD_SKELETON: "skeleton: repository-owned content"})

    def pr_template(self):
        return support.read_text(os.path.join(self.worktree, *PR_TEMPLATE.split("/")))

    def test_no_pr_template_comment_line_starts_with_risk_or_reverts(self):
        self.assertEqual(comment_line_failures(self.pr_template(), PR_TEMPLATE), [])

    def test_a_planted_comment_line_fails_the_comment_check(self):
        self.plant(PR_TEMPLATE, "- The evidence and the Merge summary", "Reverts: <full sha>\n- The evidence and the Merge summary")
        self.plant(PR_TEMPLATE, "<!-- Written with `pr`. -->", "<!-- Written with `pr`.\nRisk: low — planted\n-->")
        lines = self.pr_template().split("\n")
        self.assertEqual(
            comment_line_failures("\n".join(lines), PR_TEMPLATE),
            [
                "%s line %d starts with Reverts: inside an HTML comment" % (PR_TEMPLATE, lines.index("Reverts: <full sha>") + 1),
                "%s line %d starts with Risk: inside an HTML comment" % (PR_TEMPLATE, lines.index("Risk: low — planted") + 1),
            ],
        )

    def test_a_comment_naming_the_fields_mid_sentence_passes_the_comment_check(self):
        self.plant(PR_TEMPLATE, "<!-- Written with `pr`. -->", "<!-- Written with `pr`; no line here\n  starts with Risk: or Reverts: -->")
        self.assertEqual(comment_line_failures(self.pr_template(), PR_TEMPLATE), [])

    def test_the_pr_templates_one_risk_line_sits_outside_its_comments_and_no_line_starts_with_reverts(self):
        text = self.pr_template()
        risk = [number for number, line in enumerate(text.split("\n"), 1) if line.startswith("Risk:")]
        self.assertEqual(len(risk), 1, risk)
        self.assertNotIn(risk[0], comment_line_numbers(text))
        self.assertEqual([line for line in text.split("\n") if line.startswith("Reverts:")], [])

    def test_the_pr_template_with_its_risk_line_filled_passes_both_parsers(self):
        body = self.pr_template().replace("Risk: <low|medium|high> — <reason>", "Risk: medium — edits docs/agents")
        sha = "0123456789abcdef0123456789abcdef01234567"
        reverting = body.replace("Risk: medium — edits docs/agents\n", "Risk: medium — edits docs/agents\nReverts: %s\n" % sha)
        for parser in parsers.PARSERS:
            self.assertEqual(
                parser.pr_body(body), {"risk": {"tier": "medium", "reason": "edits docs/agents"}, "reverts": None}, parser.name
            )
            self.assertEqual(parser.pr_body(reverting)["reverts"], {"sha": sha}, parser.name)

    def test_triage_labels_md_gives_each_label_the_generator_creates_with_its_description(self):
        labels = store.Store(support.REAL_STORE).manifest(1)["labels"]
        text = support.read_text(os.path.join(self.worktree, *TRIAGE_LABELS.split("/")))
        self.assertEqual(label_mismatches(text, labels), [])

    def test_triage_mapping_independently_requires_two_categories_and_five_states(self):
        labels = store.Store(support.REAL_STORE).manifest(1)["labels"]
        self.assertEqual(triage_role_failures(self.text(TRIAGE_LABELS), labels), [])

    def test_each_missing_or_wrong_category_mapping_fails_even_with_joint_omissions(self):
        labels = store.Store(support.REAL_STORE).manifest(1)["labels"]
        text = self.text(TRIAGE_LABELS)
        for category in ("bug", "enhancement"):
            row = next(line for line in text.splitlines() if line.startswith("| `%s` |" % category))
            missing_mapping = text.replace(row + "\n", "")
            missing_label = [label for label in labels if label["name"] != category]
            mapping_failure = "Category role %s must map to its own label once" % category
            provision_failure = "manifest must provision %s once" % category
            cells = row.split("|")
            cells[2] = " `needs-triage` "
            wrong_mapping = text.replace(row, "|".join(cells))
            for mutation, mapped, provisioned, expected in (
                ("manifest only", text, missing_label, [provision_failure]),
                ("mapping only", missing_mapping, labels, [mapping_failure]),
                ("both missing", missing_mapping, missing_label, [provision_failure, mapping_failure]),
                ("wrong mapping", wrong_mapping, labels, [mapping_failure]),
            ):
                with self.subTest(category=category, mutation=mutation):
                    self.assertEqual(triage_role_failures(mapped, provisioned), expected)

    def test_a_planted_label_description_fails_the_label_check(self):
        labels = store.Store(support.REAL_STORE).manifest(1)["labels"]
        self.plant(TRIAGE_LABELS, "| Will not be actioned |", "| Won't be done |")
        self.plant(TRIAGE_LABELS, "| `miss` |", "| `misses` |")
        text = support.read_text(os.path.join(self.worktree, *TRIAGE_LABELS.split("/")))
        self.assertEqual(
            label_mismatches(text, labels),
            [
                "%s has no table row for wontfix with the description %r" % (TRIAGE_LABELS, "Will not be actioned"),
                "%s has no table row for miss with the description %r"
                % (TRIAGE_LABELS, "Miss record: something governance should have stopped got through"),
            ],
        )

    def test_each_role_file_lists_its_roles_skills(self):
        for role, path in ROLE_FILES.items():
            listed = role_skills(support.read_text(os.path.join(self.worktree, *path.split("/"))), path)
            self.assertEqual(listed, ROLE_SKILLS[role], path)
            self.assertEqual(listed & set(NOT_RELIED_ON), set(), path)

    def test_the_role_files_skills_equal_the_relied_on_list(self):
        relied_on = store.Store(support.REAL_STORE).manifest(1)["relied_on_skills"]
        self.assertEqual(skill_mismatches(self.worktree, relied_on), [])

    def plant(self, path, old, new):
        target = os.path.join(self.worktree, *path.split("/"))
        text = support.read_text(target)
        self.assertEqual(text.count(old), 1, (path, old))
        with open(target, "wb") as handle:
            handle.write(text.replace(old, new).encode("utf-8"))

    def test_a_planted_skill_mismatch_fails_the_skills_check(self):
        relied_on = store.Store(support.REAL_STORE).manifest(1)["relied_on_skills"]
        self.plant(ROLE_FILES["builder"], "- The session calls: `tdd`,", "- The session calls: `implement`, `tdd`,")
        self.plant(ROLE_FILES["planner"], ", `retro`", "")
        self.assertEqual(
            skill_mismatches(self.worktree, relied_on),
            [
                "no role file lists the relied-on skill retro",
                "a role file lists implement, which the relied-on list lacks",
            ],
        )

    def test_a_skill_dropped_from_the_relied_on_list_fails_the_skills_check(self):
        relied_on = [name for name in store.Store(support.REAL_STORE).manifest(1)["relied_on_skills"] if name != "pr"]
        self.assertEqual(skill_mismatches(self.worktree, relied_on), ["a role file lists pr, which the relied-on list lacks"])

    def test_a_skill_named_outside_the_skill_lines_is_not_listed(self):
        relied_on = store.Store(support.REAL_STORE).manifest(1)["relied_on_skills"]
        self.plant(ROLE_FILES["builder"], SKILLS_HEADING + "\n", SKILLS_HEADING + "\n\nhabit may still use `implement`.\n")
        self.assertEqual(skill_mismatches(self.worktree, relied_on), [])

    def test_the_record_parses(self):
        with open(os.path.join(self.worktree, *RECORD.split("/")), "rb") as handle:
            parsed = record.parse(handle.read())
        self.assertEqual(
            parsed,
            {
                "version": 1,
                "agent_account": "Habit098",
                "sensitive_paths": [{"pattern": pattern, "floor": "medium"} for pattern in DEFAULT_PATTERNS],
                "confirmed": materialized.tally_fixture()["confirmed"],
            },
        )

    def text(self, path):
        return support.read_text(os.path.join(self.worktree, *path.split("/")))

    def test_agents_md_claude_md_and_bugbot_md_carry_the_notice_and_pass_exact_comparison(self):
        code, facts = materialized.compare_version_one(self.worktree)
        self.assertEqual(code, 0, facts)
        for path in MIXED_FILES:
            self.assertEqual(marker_failures(self.text(path), path), [])
        self.assertEqual(self.text(BUGBOT).split("\n")[0], MARKDOWN_NOTICE)
        for path in MIXED_FILES + (BUGBOT,):
            self.assertIn(path, self.render_facts["written"])
            self.assertNotIn("@@", self.text(path), path)
            self.assertIn(path, facts["checked"])
            self.assertEqual(support.file_mode(os.path.join(self.worktree, *path.split("/"))), "100644", path)

    def test_planted_missing_duplicated_or_out_of_order_markers_fail_the_marker_check(self):
        text = self.text(AGENTS)
        self.assertEqual(
            marker_failures(text.replace(END_MARKER + "\n", ""), AGENTS),
            ["AGENTS.md has 1 begin and 0 end markers; a fixed part needs exactly one of each"],
        )
        self.assertEqual(
            marker_failures(text.replace(BEGIN_MARKER + "\n", BEGIN_MARKER + "\n" + BEGIN_MARKER + "\n"), AGENTS),
            ["AGENTS.md has 2 begin and 1 end markers; a fixed part needs exactly one of each"],
        )
        swapped = text.replace(BEGIN_MARKER, "<swap>").replace(END_MARKER, BEGIN_MARKER).replace("<swap>", END_MARKER)
        self.assertEqual(marker_failures(swapped, AGENTS), ["AGENTS.md has its end marker before its begin marker"])
        self.assertEqual(
            marker_failures(text.replace(BEGIN_MARKER, "<!-- governance:begin v2 -->"), AGENTS),
            ["AGENTS.md's begin marker is '<!-- governance:begin v2 -->', not version 1's"],
        )
        self.assertEqual(
            marker_failures(self.text(CLAUDE).replace(MIXED_NOTICE + "\n", ""), CLAUDE),
            [".claude/CLAUDE.md's first line inside the markers is '@../AGENTS.md', not the notice"],
        )

    def test_agents_md_holds_its_sections_in_order_with_this_repository_after_the_markers(self):
        text = self.text(AGENTS)
        start, end = render.find_block(text, AGENTS)
        self.assertEqual(headings(text[start:end]), list(AGENTS_SECTIONS))
        self.assertEqual(headings(text[end:]), list(REPOSITORY_SECTIONS))
        self.assertEqual(headings(text[:start]), [])

    def test_claude_md_imports_agents_md_from_inside_its_markers(self):
        text = self.text(CLAUDE)
        start, end = render.find_block(text, CLAUDE)
        self.assertEqual(text[start:end].split("\n")[2], "@../AGENTS.md")
        self.assertEqual(pointer_targets(CLAUDE, "../AGENTS.md"), [AGENTS])

    def test_text_after_the_end_markers_is_repository_owned_and_inside_them_is_compared(self):
        self.plant(AGENTS, "## This repository\n", "## This repository\n\nA carried rule.\n")
        self.plant(CLAUDE, END_MARKER + "\n", END_MARKER + "\n\nA Claude Code note.\n")
        code, facts = materialized.compare_version_one(self.worktree)
        self.assertEqual((code, facts["differences"]), (0, []))
        self.plant(AGENTS, "## Hard limits\n", "## Hard limits\n\nA planted rule.\n")
        code, facts = materialized.compare_version_one(self.worktree)
        self.assertEqual(code, 1)
        self.assertEqual([(d["path"], d["kind"]) for d in facts["differences"]], [(AGENTS, "content")])

    def test_agents_md_is_within_its_budget(self):
        with open(os.path.join(self.worktree, AGENTS), "rb") as handle:
            self.assertEqual(budget_failures(handle.read()), [])

    def test_a_planted_agents_md_over_its_budget_fails_the_budget_check(self):
        with open(os.path.join(self.worktree, AGENTS), "rb") as handle:
            data = handle.read()
        padded = data + b"x" * (AGENTS_BUDGET + 1 - len(data))
        self.assertEqual(budget_failures(padded), ["AGENTS.md is 11265 bytes, over its 11264-byte budget"])
        self.assertEqual(budget_failures(padded[:-1]), [])

    def test_bugbot_md_equals_agents_mds_code_review_rules(self):
        self.assertEqual(bugbot_failures(self.text(AGENTS), self.text(BUGBOT)), [])
        self.assertEqual(self.text(BUGBOT).split("\n")[2], CODE_REVIEW_RULES)

    def test_a_planted_one_character_difference_fails_the_bugbot_check(self):
        agents, bugbot = self.text(AGENTS), self.text(BUGBOT)
        line = next(line for line in bugbot.split("\n") if "Important" in line)
        planted = bugbot.replace(line, line.replace("Important", "Importent", 1), 1)
        number = bugbot.split("\n").index(line) + 1
        self.assertEqual(bugbot_failures(agents, planted), ["%s departs from %s's Code Review Rules at its line %d" % (BUGBOT, AGENTS, number)])
        self.assertEqual(
            bugbot_failures(agents.replace(line, line.replace("Important", "Importent", 1), 1), bugbot),
            ["%s departs from %s's Code Review Rules at its line %d" % (BUGBOT, AGENTS, number)],
        )
        self.assertEqual(
            bugbot_failures(agents, bugbot + "A rule only Bugbot reads.\n"),
            ["%s departs from %s's Code Review Rules at its line %d" % (BUGBOT, AGENTS, len(bugbot.split("\n")))],
        )

    def manifest_paths(self):
        return [entry["path"] for entry in store.Store(support.REAL_STORE).manifest(1)["templates"]]

    def test_every_path_pointer_names_a_file_version_one_writes(self):
        self.assertEqual(routing_failures(self.worktree, self.manifest_paths()), [])

    def line_number(self, path, text):
        """The 1-based number of the one line of a worktree file holding text."""
        numbers = [number for number, line in enumerate(self.text(path).split("\n"), 1) if text in line]
        self.assertEqual(len(numbers), 1, (path, text))
        return numbers[0]

    def test_planted_broken_pointers_fail_the_routing_check(self):
        self.plant(PR_TEMPLATE, "as builder.md, step 7", "as build-steps.md, step 7")
        self.plant(AGENTS, "`docs/agents/triage-labels.md`", "`docs/agents/labels.md`")
        self.plant(CLAUDE, "@../AGENTS.md", "@../AGENT.md")
        self.plant(CLAUDE, "## Claude Code notes\n", "## Claude Code notes\n\nSee ./local-notes.md.\n")
        self.assertEqual(
            routing_failures(self.worktree, self.manifest_paths()),
            [
                "%s line %d points at ../AGENT.md, which version 1 doesn't write" % (CLAUDE, self.line_number(CLAUDE, "@../AGENT.md")),
                "%s line %d points at ./local-notes.md, which version 1 doesn't write" % (CLAUDE, self.line_number(CLAUDE, "./local-notes.md")),
                "%s line %d points at build-steps.md, which version 1 doesn't write" % (PR_TEMPLATE, self.line_number(PR_TEMPLATE, "build-steps.md")),
                "%s line %d points at docs/agents/labels.md, which version 1 doesn't write" % (AGENTS, self.line_number(AGENTS, "docs/agents/labels.md")),
            ],
        )

    def test_unrouted_names_stay_outside_the_routing_check_and_fail_without_it(self):
        paths = self.manifest_paths()
        before = len(routing_failures(self.worktree, paths, unrouted=()))
        planted = ("`GLOSSARY.md`", "`docs/adr/`", "`.github/workflows/ci.yml`", "no root `CLAUDE.md`", "`.codex/`")
        for pointer in planted:
            self.plant(AGENTS, "## This repository\n", "## This repository\n\n%s\n" % pointer)
        self.assertEqual(routing_failures(self.worktree, paths), [])
        self.assertEqual(len(routing_failures(self.worktree, paths, unrouted=())), before + len(planted))

    def test_version_one_writes_no_root_claude_md_override_or_codex_directory(self):
        self.assertEqual([path for path in self.manifest_paths() if NEVER_WRITTEN.match(path)], [])
        self.assertEqual([path for path in self.render_facts["written"] if NEVER_WRITTEN.match(path)], [])
        planted = ["CLAUDE.md", "claude.md", "docs/AGENTS.override.md", ".codex/config.toml", ".claude/CLAUDE.md", "AGENTS.md"]
        self.assertEqual([path for path in planted if NEVER_WRITTEN.match(path)], planted[:4])
