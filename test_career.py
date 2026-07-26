import re
import unittest
from pathlib import Path

ROOT = Path(__file__).parent
HTML = (ROOT / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "app.js").read_text(encoding="utf-8")
CSS = (ROOT / "styles.css").read_text(encoding="utf-8")
SW = (ROOT / "sw.js").read_text(encoding="utf-8")


class CareerTabTests(unittest.TestCase):
    def test_career_nav_and_main_panel_present(self):
        self.assertIn('data-tab="career"', HTML)
        self.assertIn('id="career-panel"', HTML)
        self.assertIn('data-tab="today"', HTML)

    def test_career_pipeline_stages_rendered(self):
        for stage in [
            "Found", "Reviewing", "Shortlisted", "Tailoring",
            "Ready", "Applied", "Interviewing", "Offer", "Archived",
        ]:
            self.assertIn(stage, HTML)

    def test_career_scoring_dimensions_rendered(self):
        for dim in ["qualifications", "comp", "scope", "growth", "company", "location", "industry", "priority"]:
            self.assertIn(dim, HTML)

    def test_career_add_job_form_exists(self):
        self.assertIn('id="job-form"', HTML)
        self.assertIn('id="job-title"', HTML)
        self.assertIn('id="job-company"', HTML)
        self.assertIn('id="job-url"', HTML)
        self.assertIn('id="job-stage"', HTML)
        self.assertIn('id="job-comp-min"', HTML)
        self.assertIn('id="job-comp-target"', HTML)
        self.assertIn('id="job-location"', HTML)
        self.assertIn('id="job-mode"', HTML)
        self.assertIn('id="job-description"', HTML)

    def test_career_job_detail_view_exists(self):
        for el in ["career-detail", "job-tailored-resume", "job-cover-letter", "job-match-analysis", "job-screening-answers", "job-interview-prep", "job-stage-update", "job-score-update", "job-composite", "job-detail-title", "job-detail-meta", "job-tailor-suggestion"]:
            self.assertIn(f'id="{el}"', HTML)

    def test_job_pipeline_state_normalized(self):
        self.assertIn("state.jobs", JS)
        self.assertIn("state.jobs=state.jobs||[]", JS)
        self.assertIn("PLAN_KEY", JS)
        for fn in ["addJob", "renderCareer", "saveJob", "deleteJob", "selectJob", "computeCompositeScore", "computeCompScore", "computeFitScore", "advanceJob", "recommendTailoring"]:
            self.assertRegex(JS, rf"function\s+{fn}", f"missing function {fn}")

    def test_job_scoring_uses_comp_and_fit_dimensions(self):
        for fn in ["computeCompositeScore", "computeCompScore", "computeFitScore"]:
            self.assertRegex(JS, rf"function\s+{fn}")

    def test_composite_score_weights_comp_heavily(self):
        # Weights must reward comp heavily and sum to 1.0:
        # qualifications 0.4, comp 0.2, scope 0.1, growth 0.1, company 0.05,
        # location 0.05, industry 0.05, priority 0.05.
        for w in ["0.4", "0.2", "0.1", "0.05"]:
            self.assertIn(w, JS)
        # Ensure no orphan weight that would break the sum
        self.assertNotIn("0.15", JS)
        self.assertNotIn("0.25", JS)
        self.assertNotIn("0.3", JS)

    def test_telegram_digest_payload(self):
        self.assertIn("data-telegram", HTML)
        self.assertIn("buildDailyDigest", JS)
        self.assertIn("telegram", JS.lower())

    def test_career_views_persist_to_cloud(self):
        self.assertIn("state.jobs", JS)
        self.assertIn("pushCloud", JS)
        self.assertIn("daybook_data", JS)

    def test_career_css_styles_defined(self):
        for sel in [".career-tabs", ".career-board", ".career-card", ".career-detail", ".career-score", ".career-toolbar", ".career-stage", ".career-mode-remote", ".career-mode-hybrid", ".career-mode-onsite"]:
            self.assertIn(sel, CSS)

    def test_career_block_exists_in_sw(self):
        self.assertIn("app.js?v=14", HTML)
        self.assertIn("styles.css?v=14", HTML)
        self.assertIn("daybook-v14", SW)
        self.assertIn("styles.css?v=14", SW)
        self.assertIn("app.js?v=14", SW)

    def test_job_import_widget_present(self):
        for el in ["job-import-json", "job-import-run", "job-import-status"]:
            self.assertIn('id="'+el+'"', HTML)
        self.assertIn('class="career-import"', HTML)
        self.assertIn("import", JS.lower())
        self.assertIn("JSON.parse", JS)

    def test_no_truncation_markers(self):
        for marker in ["[truncated]", "[Truncated]"]:
            self.assertNotIn(marker, JS)
            self.assertNotIn(marker, CSS)
            self.assertNotIn(marker, HTML)

    def test_removed_director_and_senior_manager_tags(self):
        # The pipeline definitions should not pre-create targets that the user excluded
        self.assertNotIn("Director", JS.replace("state.jobs", ""))  # allow only in user data
        self.assertNotIn("SeniorManager", JS)

    def test_today_panel_unchanged(self):
        # The Today panel IDs from V12 must still be present
        for required_id in ["quick-add", "chore-list", "habit-list", "habit-form", "journal-form", "goal-form", "event-form"]:
            self.assertIn(f'id="{required_id}"', HTML)


if __name__ == "__main__":
    unittest.main()
