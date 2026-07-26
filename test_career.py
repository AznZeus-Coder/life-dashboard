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

    def test_job_description_popup_exists(self):
        for el in [
            "job-description-dialog",
            "job-description-title",
            "job-description-meta",
            "job-description-content",
            "job-source-link",
            "job-open-workspace",
            "job-description-close",
        ]:
            self.assertIn(f'id="{el}"', HTML)
        self.assertIn("showJobDescription", JS)
        self.assertIn("job-description-content", JS)
        self.assertIn("job-source-link", JS)
        self.assertIn('target="_blank"', HTML)
        self.assertIn('rel="noopener noreferrer"', HTML)
        for sel in [".job-description-dialog", ".job-description-content", ".job-description-actions"]:
            self.assertIn(sel, CSS)

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

    def test_career_card_company_is_most_prominent(self):
        """Company name must be visually larger than the title on each job card."""
        # Company uses Press Start 2P display font at 22px; title uses 17px.
        m_company = re.search(r"\.career-card-company\{([^}]+)\}", CSS)
        m_title = re.search(r"\.career-card strong\{([^}]+)\}", CSS)
        self.assertIsNotNone(m_company, "missing .career-card-company rule")
        self.assertIsNotNone(m_title, "missing .career-card strong rule")
        company_decl = m_company.group(1)
        title_decl = m_title.group(1)
        # Company should declare the bigger display font and a larger size.
        self.assertIn("Press Start 2P", company_decl,
                      "company must use the prominent Press Start 2P display font")
        self.assertIn("22px", company_decl, "company font-size must be 22px")
        self.assertIn("17px", title_decl, "title font-size must be 17px (smaller than company)")
        # Numeric guard: company px size > title px size.
        comp_px = int(re.search(r"(\d+)px", company_decl).group(1))
        title_px = int(re.search(r"(\d+)px", title_decl).group(1))
        self.assertGreater(comp_px, title_px,
                           f"company ({comp_px}px) must be larger than title ({title_px}px)")

    def test_career_card_renders_company_above_title(self):
        """Cards must show Company above Title (LinkedIn / Indeed layout)."""
        # The renderCareer template must place .career-card-company BEFORE <strong>{title}.
        company_idx = JS.find("career-card-company")
        title_idx = JS.find("data-show-job")
        self.assertNotEqual(company_idx, -1)
        self.assertNotEqual(title_idx, -1)
        # Company should appear in the card's innerHTML before the title text. The simplest
        # way to assert this: extract the data-show-job card template and confirm company
        # string precedes title string within it.
        i = JS.find('data-show-job="')
        j = JS.find('</article>', i)
        card_template = JS[i:j]
        company_pos = card_template.find("career-card-company")
        title_pos = card_template.find("<strong>")
        self.assertNotEqual(company_pos, -1)
        self.assertNotEqual(title_pos, -1)
        self.assertLess(company_pos, title_pos,
                        "Company must render above the title inside the card template")

    def test_career_card_includes_company_tag_one_liner(self):
        """When a job has a `companyTag`, the card must render it under the company name."""
        # The renderCareer template must include a .career-card-company-tag paragraph
        # placed after .career-card-company and before the title header.
        i = JS.find('data-show-job="')
        j = JS.find('</article>', i)
        card_template = JS[i:j]
        self.assertIn("career-card-company-tag", card_template,
                      "card template missing .career-card-company-tag element")
        # Order: company name -> company tag -> header (title+pill)
        c = card_template.find("career-card-company\"")
        t = card_template.find("career-card-company-tag")
        h = card_template.find("<header>")
        self.assertNotEqual(c, -1); self.assertNotEqual(t, -1); self.assertNotEqual(h, -1)
        self.assertLess(c, t, "company tag must appear after company name")
        self.assertLess(t, h, "company tag must appear before the title header")
        # CSS must define the tag style
        self.assertIn(".career-card-company-tag", CSS)

    def test_career_block_exists_in_sw(self):
        self.assertIn("app.js?v=17", HTML)
        self.assertIn("styles.css?v=17", HTML)
        self.assertIn("daybook-v17", SW)
        self.assertIn("styles.css?v=17", SW)
        self.assertIn("app.js?v=17", SW)
        self.assertIn("hermes-jobs.json", SW)

    def test_hermes_auto_pull_present(self):
        self.assertIn('id="hermes-scanned-at"', HTML)
        self.assertIn('id="hermes-count"', HTML)
        self.assertIn('id="hermes-refresh"', HTML)
        self.assertIn('id="hermes-add-all"', HTML)
        self.assertIn("HERMES_URL", JS)
        self.assertIn("fetchHermesJobs", JS)
        self.assertIn("aznzeus-coder.github.io/life-dashboard/hermes-jobs.json", JS)

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
