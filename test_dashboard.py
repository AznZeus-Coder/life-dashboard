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
        self.assertIn('id="habit-list"', html)
        self.assertIn('id="habit-form"', html)
        self.assertIn('id="habit-minutes"', html)
        self.assertIn('id="habit-calendar"', html)
        self.assertNotIn('id="calendar-month"', html)
        self.assertIn('class="tracker-days"', html)
        self.assertIn('"display": "standalone"', manifest)

    def test_app_persists_data_and_supports_recurring_chores(self):
        js = (ROOT / "app.js").read_text(encoding="utf-8")
        self.assertIn("localStorage", js)
        self.assertRegex(js, r"function\s+addTask")
        self.assertRegex(js, r"function\s+completeChore")
        self.assertIn("nextDue", js)
        self.assertRegex(js, r"function\s+completeHabit")
        self.assertIn("Cleaning room", js)
        self.assertIn("minutes:15", js)
        self.assertIn("lastCompleted", js)
        self.assertIn("completionDates", js)
        self.assertRegex(js, r"function\s+renderCalendar")
        self.assertNotRegex(js, r"function\s+changeMonth")
        self.assertIn("tracker-cell", js)

    def test_cloud_sync_uses_supabase_auth_and_user_scoped_data(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "app.js").read_text(encoding="utf-8")
        self.assertIn("@supabase/supabase-js", html)
        self.assertIn('id="auth-panel"', html)
        self.assertIn("signInWithOtp", js)
        self.assertIn("daybook_data", js)
        self.assertIn("user_id", js)
        self.assertNotIn("[truncated]", js)
        self.assertRegex(js, r"document\.querySelector\('#quick-add'\)\.onsubmit")
        self.assertRegex(js, r"document\.querySelector\('#auth-form'\)\.onsubmit")

    def test_service_worker_caches_app_shell(self):
        js = (ROOT / "sw.js").read_text(encoding="utf-8")
        for asset in ["./", "./index.html", "./styles.css", "./app.js"]:
            self.assertIn(asset, js)

    def test_service_worker_updates_installed_app_instead_of_serving_stale_shell(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "sw.js").read_text(encoding="utf-8")
        self.assertIn("skipWaiting", js)
        self.assertIn("clients.claim", js)
        self.assertIn("caches.keys", js)
        self.assertIn('styles.css?v=8', html)
        self.assertIn('app.js?v=8', html)
        self.assertIn("styles.css?v=8", js)
        css = (ROOT / "styles.css").read_text(encoding="utf-8")
        self.assertTrue(css.startswith("@import"))
        self.assertEqual(css.count("{"), css.count("}"))
        self.assertNotIn("[truncated]", css)
        self.assertIn(".auth{", css)
        self.assertIn("@media(max-width:700px)", css)

if __name__ == "__main__":
    unittest.main()
