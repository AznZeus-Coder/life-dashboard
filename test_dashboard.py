import re
import unittest
from pathlib import Path

ROOT = Path(__file__).parent

class DashboardTests(unittest.TestCase):
    def test_installable_app_files_and_core_controls_exist(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        manifest = (ROOT / "manifest.webmanifest").read_text(encoding="utf-8")
        self.assertIn('manifest.webmanifest', html)
        self.assertIn('id="quick-add"', html)
        self.assertIn('id="task-list"', html)
        self.assertIn('id="chore-list"', html)
        self.assertIn('"display": "standalone"', manifest)

    def test_app_persists_data_and_supports_recurring_chores(self):
        js = (ROOT / "app.js").read_text(encoding="utf-8")
        self.assertIn("localStorage", js)
        self.assertRegex(js, r"function\s+addTask")
        self.assertRegex(js, r"function\s+completeChore")
        self.assertIn("nextDue", js)

    def test_service_worker_caches_app_shell(self):
        js = (ROOT / "sw.js").read_text(encoding="utf-8")
        for asset in ["./", "./index.html", "./styles.css", "./app.js"]:
            self.assertIn(asset, js)

if __name__ == "__main__":
    unittest.main()
