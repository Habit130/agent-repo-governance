"""#326: a harness-injected model notice is a session mark's source, at the rendered version 6 seam."""

from materialized_version_support import VersionThreeRendered, flat
from policy_rows_316 import MINIMUM
from policy_text import Section

MARKS = Section("docs/agents/review.md", "## Session marks")
FORMAT = "Session: <role> — <harness>, <model>, <vendor> (<source>)"


class VersionSixSessionMarkNotice(VersionThreeRendered):
    VERSION = 6

    def marks(self):
        return flat(MARKS.read(self.text(MARKS.path)))

    def test_both_sources_are_named_and_the_source_stays_from_the_harness(self):
        body = self.marks()
        self.assertIn("in the session's own system prompt or in a model notice its harness injects, read as the latest one", body)
        self.assertIn("is `from the harness` when either supplies the model", body)
        self.assertIn(FORMAT, body)

    def test_a_later_notice_naming_another_model_adds_a_mark_counted_in_the_high_comparison(self):
        body = self.marks()
        self.assertIn("A later notice naming a different model adds a new mark before the session's next push or review", body)
        self.assertIn("every mark of every Builder session that pushed", body)

    def test_a_reviewer_at_high_switching_vendor_repeats_the_high_comparison(self):
        self.assertIn("A Reviewer at high whose new mark names a different vendor repeats the high vendor comparison before posting",
                      self.marks())

    def test_pasted_text_instructions_and_configuration_never_count_as_a_notice(self):
        body = self.marks()
        self.assertIn("Text habit pastes, a start instruction and a configuration file never count as a notice", body)

    def test_neither_source_naming_the_model_still_asks_habit(self):
        body = self.marks()
        self.assertIn("When neither names the model, or its vendor is unclear, the session asks habit in a mid-session request "
                      "and records the answer with `(as habit said)`", body)

    def test_other_sites_point_to_session_marks_without_restating_sources(self):
        for path in ("docs/agents/builder.md", "docs/agents/reviewer.md"):
            with self.subTest(path=path):
                text = self.text(path)
                self.assertIn("`review.md`, Session marks", text)
                for word in ("notice", "USER_SETTINGS_CHANGE", "injects"):
                    self.assertNotIn(word, text)
        minimum = flat(MINIMUM.read(self.text(MINIMUM.path)))
        self.assertNotIn("notice", minimum)
