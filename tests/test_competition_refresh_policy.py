"""Pure, bounded game-day polling rules for all followed competitions."""
import importlib.util
from datetime import datetime, timezone, timedelta
from pathlib import Path
import unittest

p = Path(__file__).resolve().parents[1] / "custom_components/fbm/competition_refresh_policy.py"
spec = importlib.util.spec_from_file_location("fbm_refresh_policy", p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

UTC = timezone.utc
NOW = datetime(2026, 11, 11, 18, 0, tzinfo=UTC)


class PollPolicyTests(unittest.TestCase):
    def setUp(self):
        self.schedule = {"partidos": [
            {"fecha": "14/11/2026", "estado": "scheduled"},
            {"fecha": "10/11/2026", "estado": "finished"}
        ]}

    def test_initial_check_is_immediate(self):
        self.assertTrue(m.should_poll_group(self.schedule, None, NOW))

    def test_no_repeat_within_four_hours(self):
        last = (NOW - timedelta(hours=2)).isoformat()
        self.assertFalse(m.should_poll_group(self.schedule, last, NOW))

    def test_recent_match_is_rechecked(self):
        last = (NOW - timedelta(hours=5)).isoformat()
        self.assertTrue(m.should_poll_group(self.schedule, last, NOW))

    def test_quiet_week_skips_and_weekly_rechecks(self):
        quiet = {"partidos": [{"fecha": "28/11/2026"}]}
        last = (NOW - timedelta(days=2)).isoformat()
        self.assertFalse(m.should_poll_group(quiet, last, NOW))
        last = (NOW - timedelta(days=8)).isoformat()
        self.assertTrue(m.should_poll_group(quiet, last, NOW))

    def test_invalid_metadata_never_suppresses_poll(self):
        self.assertTrue(m.should_poll_group(self.schedule, "invalid", NOW))
        self.assertTrue(m.should_poll_group(None, (NOW-timedelta(days=2)).isoformat(), NOW))


if __name__ == "__main__":
    unittest.main()
