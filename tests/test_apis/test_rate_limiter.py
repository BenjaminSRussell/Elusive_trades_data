"""RateLimiter RPM delay + 429 backoff (offline, fake clock)."""
import time
import unittest
from unittest import mock

from phase1_acquisition.apis.base_api import RateLimiter


class TestRateLimiter(unittest.TestCase):
    def test_rpm_delays_second_call(self):
        clock = {"t": 1000.0}
        sleeps = []

        def fake_monotonic():
            return clock["t"]

        def fake_sleep(dt):
            sleeps.append(dt)
            clock["t"] += dt

        lim = RateLimiter(requests_per_minute=60)  # 1 req/sec
        with mock.patch.object(lim, "_clock", fake_monotonic), mock.patch(
            "phase1_acquisition.apis.base_api.time.sleep", fake_sleep
        ):
            lim.wait_turn()
            lim.wait_turn()
        self.assertTrue(sleeps)
        self.assertGreaterEqual(sleeps[0], 0.9)

    def test_429_triggers_backoff_then_success(self):
        lim = RateLimiter(requests_per_minute=1000, max_retries=3)
        calls = {"n": 0}
        sleeps = []

        def do_request():
            calls["n"] += 1
            if calls["n"] < 3:
                return mock.Mock(status_code=429)
            return mock.Mock(status_code=200)

        with mock.patch("phase1_acquisition.apis.base_api.time.sleep", side_effect=lambda d: sleeps.append(d)):
            # also stub wait_turn to avoid RPM sleeps
            with mock.patch.object(lim, "wait_turn", return_value=0.0):
                resp = lim.request_with_retry(do_request)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(calls["n"], 3)
        self.assertTrue(sleeps)  # backoff sleeps


if __name__ == "__main__":
    unittest.main()
