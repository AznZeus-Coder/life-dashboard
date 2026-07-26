"""
Tests for the Hermes job scanner (job_scanner.py).

The scanner is the data-acquisition half of the auto-scan pipeline:
  - queries SimplyHired + Workopolis for BC/Canada controller roles
  - parses salary out of search-result + detail-page HTML
  - scores each result with the dashboard's locked weights
  - writes hermes-jobs.json to the life-dashboard repo

Run:
    cd ~/projects/life-dashboard && python -m pytest test_scanner.py -q
"""

import importlib.util
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parent
# The scanner lives outside the repo (it's a Hermes script), so import it by path.
SCANNER_PATH = Path.home() / "AppData" / "Local" / "hermes" / "scripts" / "job_scanner.py"


def _load_scanner():
    """Dynamically import job_scanner.py by absolute path so the test works from any cwd."""
    spec = importlib.util.spec_from_file_location("job_scanner", SCANNER_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load scanner from {SCANNER_PATH}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class SalaryParserTests(unittest.TestCase):
    """parse_salary() must extract real numeric ranges from common formats."""

    def setUp(self):
        self.mod = _load_scanner()

    def test_parses_dollar_dash_thousands(self):
        mn, mx = self.mod.parse_salary("$170,000–$200,000")
        self.assertEqual(mn, 170000)
        self.assertEqual(mx, 200000)

    def test_parses_k_suffix_with_dash(self):
        mn, mx = self.mod.parse_salary("$175k-$200k")
        self.assertEqual(mn, 175000)
        self.assertEqual(mx, 200000)

    def test_parses_word_dash_with_space(self):
        mn, mx = self.mod.parse_salary("$130k - $150k a year")
        self.assertEqual(mn, 130000)
        self.assertEqual(mx, 150000)

    def test_handles_em_and_en_dash(self):
        for sep in ("-", "–", "—"):
            mn, mx = self.mod.parse_salary(f"$120k{sep}$130k")
            self.assertEqual((mn, mx), (120000, 130000))

    def test_single_value_returns_pair(self):
        mn, mx = self.mod.parse_salary("$150k+")
        self.assertEqual(mn, 150000)
        self.assertEqual(mx, 150000)

    def test_empty_returns_none(self):
        self.assertEqual(self.mod.parse_salary(""), (None, None))
        self.assertEqual(self.mod.parse_salary(None), (None, None))

    def test_unparseable_returns_none(self):
        self.assertEqual(self.mod.parse_salary("Competitive"), (None, None))


class CompScoreTests(unittest.TestCase):
    """score_job() output's comp dimension must reflect the salary, not default 7."""

    def setUp(self):
        self.mod = _load_scanner()

    def test_undisclosed_returns_seven_with_explicit_label(self):
        s = self.mod.score_job({"title": "Controller", "company": "Acme", "salary": "", "location": "Vancouver, BC"})
        self.assertEqual(s["comp_score"], 7)
        # Contract: undisclosed comps show "no comp listed", not the old "?" placeholder.
        self.assertEqual(s["salary_label"], "no comp listed")

    def test_high_salary_yields_ten(self):
        s = self.mod.score_job({"title": "Controller", "company": "Acme", "salary": "$175k-$200k", "location": "Vancouver, BC"})
        self.assertEqual(s["comp_score"], 10)
        self.assertEqual(s["salary_label"], "$175k-$200k")

    def test_floor_band_yields_seven(self):
        s = self.mod.score_job({"title": "Controller", "company": "Acme", "salary": "$130k-$150k", "location": "Vancouver, BC"})
        self.assertEqual(s["comp_score"], 7)

    def test_below_floor_drops_to_five(self):
        s = self.mod.score_job({"title": "Controller", "company": "Acme", "salary": "$120k-$130k", "location": "Vancouver, BC"})
        self.assertEqual(s["comp_score"], 5)

    def test_adzuna_structured_salary_wins_over_string(self):
        """When salary_min/salary_max are present (Adzuna), use them — no string parse."""
        s = self.mod.score_job({
            "title": "Controller", "company": "Acme",
            "salary": "garbage",  # would fail the regex
            "salary_min": 175000, "salary_max": 200000,
            "location": "Vancouver, BC",
        })
        self.assertEqual(s["comp_score"], 10)
        self.assertEqual(s["salary_label"], "$175k-$200k")


class OutputShapeTests(unittest.TestCase):
    """The final hermes-jobs.json must include direct salary fields per job."""

    @classmethod
    def setUpClass(cls):
        cls.path = ROOT / "hermes-jobs.json"
        cls.data = json.loads(cls.path.read_text(encoding="utf-8")) if cls.path.exists() else None

    def test_output_exists(self):
        self.assertIsNotNone(self.data, "hermes-jobs.json missing — run the scanner first")

    def test_each_job_has_comp_min_and_comp_target(self):
        self.assertIsNotNone(self.data)
        for j in self.data["jobs"]:
            self.assertIn("compMin", j, f"{j['company']} missing compMin")
            self.assertIn("compTarget", j, f"{j['company']} missing compTarget")
            self.assertIn("compStretch", j, f"{j['company']} missing compStretch")

    def test_each_job_has_salary_label_string(self):
        self.assertIsNotNone(self.data)
        for j in self.data["jobs"]:
            self.assertIn("_hermes", j)
            self.assertIn("salaryLabel", j["_hermes"])
            label = j["_hermes"]["salaryLabel"]
            # Real range like "$170k-$200k" / "$150k+", OR the explicit "no comp listed" marker
            self.assertTrue(
                re.match(r"^\$\d+k(-\$\d+k)?(\+)?$", label) or label == "no comp listed",
                f"Unexpected salaryLabel on {j['company']}: {label!r}",
            )

    def test_salary_label_no_longer_question_mark(self):
        """Regression: the ? placeholder is replaced with 'no comp listed' when there is no data."""
        self.assertIsNotNone(self.data)
        bad = [j for j in self.data["jobs"] if j["_hermes"]["salaryLabel"] == "?"]
        self.assertEqual(bad, [], f"{len(bad)} jobs still show '?' for salary: {[j['company'] for j in bad]}")


class ScannerCoversAdzunaTests(unittest.TestCase):
    """The scanner must query Adzuna when ADZUNA_APP_ID+ADZUNA_APP_KEY are present."""

    def test_adzuna_env_keys_referenced_in_source(self):
        src = SCANNER_PATH.read_text(encoding="utf-8")
        self.assertIn("ADZUNA_APP_ID", src)
        self.assertIn("ADZUNA_APP_KEY", src)
        self.assertIn("fetch_adzuna_jobs", src)

    def test_adzuna_only_runs_when_keys_set(self):
        """Without env keys the scanner must not blow up and must not call Adzuna."""
        import os
        if "ADZUNA_APP_ID" in os.environ:
            self.skipTest("Adzuna creds set in this shell; skipping negative test")
        # The check is structural: scanner reads os.environ and gates the call.
        src = SCANNER_PATH.read_text(encoding="utf-8")
        self.assertRegex(src, r"os\.environ.*ADZUNA_APP_ID")

    def test_fetch_adzuna_jobs_returns_empty_without_keys(self):
        """No creds → empty list (not an exception)."""
        import os
        if "ADZUNA_APP_ID" in os.environ:
            self.skipTest("Adzuna creds set in this shell; skipping negative test")
        mod = _load_scanner()
        out = mod.fetch_adzuna_jobs("controller", "Vancouver BC")
        self.assertEqual(out, [])


if __name__ == "__main__":
    unittest.main()