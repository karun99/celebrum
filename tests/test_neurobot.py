"""Tests for the Celebrum cognitive-robotics validation (neurobot module).

Covers organoid/MEA spike simulation, closed-loop robotic control, adversarial
neural-security stress testing, and the integrated validation harness.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from celebrum.neurobot import (
    SpikeTensor,
    make_spike_tensor,
    ControlLoop,
    DEFAULT_MAZE,
    adversarial_stress_test,
    validate_cognitive_robotics,
    ATTACK_SUITE,
)


class TestSpikeTensor(unittest.TestCase):
    def test_stats_bounds(self):
        t = make_spike_tensor(electrodes=8, time_bins=64, baseline_rate=0.3)
        s = t.stats()
        self.assertEqual(s["electrodes"], 8)
        self.assertEqual(s["time_bins"], 64)
        self.assertLessEqual(s["spike_count"], 8 * 64)
        self.assertGreaterEqual(s["mean_rate"], 0.0)
        self.assertLessEqual(s["mean_rate"], 1.0)

    def test_refractory_enforced(self):
        t = SpikeTensor(2, 10, baseline_rate=1.0, refractory_bins=3)
        before = t.stats()["spike_count"]
        t.apply_refractory()
        after = t.stats()["spike_count"]
        self.assertLessEqual(after, before)
        for e in range(2):
            last = -99
            for b in range(10):
                if t.data[e * 10 + b] == 1:
                    self.assertGreaterEqual(b - last, 3)
                    last = b

    def test_slice(self):
        t = make_spike_tensor(4, 32)
        s = t.slice_window(4, 12)
        self.assertEqual(s.time_bins, 8)
        self.assertEqual(s.electrodes, 4)


class TestControlLoop(unittest.TestCase):
    def test_default_maze_runs(self):
        loop = ControlLoop(input_electrodes=6, motor_electrodes=6, time_bins=32)
        result = loop.run(max_steps=40)
        self.assertGreaterEqual(result["steps_used"], 1)
        self.assertTrue(all(a in ("wait", "step_x+", "step_x-", "step_y+", "step_y-")
                            for a in result["route"]))

    def test_step_has_coherence(self):
        loop = ControlLoop(input_electrodes=4, motor_electrodes=4, time_bins=16)
        r = loop.step((0, 0), (4, 4), DEFAULT_MAZE)
        self.assertEqual(len(r["sensor"]), 4)
        self.assertGreaterEqual(r["coherence"], 0.0)
        self.assertLessEqual(r["coherence"], 1.0)


class TestAdversarial(unittest.TestCase):
    def test_full_suite_report(self):
        report = adversarial_stress_test(electrodes=8, time_bins=48)
        self.assertEqual(len(report["attacks"]), len(ATTACK_SUITE))
        self.assertIn("coherence", report["baseline"])
        for a in report["attacks"]:
            self.assertIn(a["name"], {x[0] for x in ATTACK_SUITE})
            self.assertIn("detected", a)
            self.assertLessEqual(a["security_score"], 1.0)

    def test_catastrophic_flagged(self):
        report = adversarial_stress_test(electrodes=8, time_bins=32)
        cat = next(a for a in report["attacks"] if a["name"] == "impulse-catastrophic")
        self.assertTrue(cat["detected"])


class TestIntegration(unittest.TestCase):
    def test_harness_shape(self):
        result = validate_cognitive_robotics(electrodes=8, time_bins=32)
        self.assertIn("spike", result)
        self.assertIn("robotics", result)
        self.assertIn("adversarial", result)
        self.assertIn("passed", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)