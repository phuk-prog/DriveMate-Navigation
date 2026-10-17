"""Both GPS matchers stay available; shadow cannot change baseline output."""
import unittest
from unittest.mock import patch

from engine import RoadGraph, RoadEdge
from gps.fix_quality import GPSFix
from gps.matcher import LEGACY_MATCHER, DirectedRoadMatcher
from gps.temporal_matcher import TemporalRoadMatcher
from gps.shadow_comparison import GPSShadowComparison


class GPSShadowComparisonTests(unittest.TestCase):
    def setUp(self):
        self.coords = {
            "a": (0, 0), "b": (0, .0002),
            "c": (.000015, .00047)}
        self.graph = RoadGraph(
            self.coords, [
                RoadEdge("w:1:0:f", "a", "b", 23, 30, "allowed"),
                RoadEdge("w:1:1:f", "b", "c", 30, 30, "allowed")])
        self.first_fix = GPSFix(1000, .000004, .000270, 3, 10, 87)

    def test_shadow_never_replaces_conservative_first_fix(self):
        paired = GPSShadowComparison(self.graph, self.coords).update(
            self.first_fix, now_ms=1000)
        self.assertTrue(paired.baseline_authoritative)
        self.assertEqual(paired.baseline.status, "AMBIGUOUS")
        self.assertEqual(paired.experimental.status, "MATCHED")
        self.assertTrue(paired.disagrees)
        self.assertIsNone(paired.experiment_error)

    def test_baseline_matches_independent_default_matcher(self):
        paired = GPSShadowComparison(self.graph, self.coords)
        solo = TemporalRoadMatcher(DirectedRoadMatcher(self.graph, self.coords, **LEGACY_MATCHER))
        for fix in (self.first_fix, GPSFix(3000, .000006, .00035, 3, 10, 85)):
            with self.subTest(time=fix.timestamp_ms):
                dual = paired.update(fix, now_ms=fix.timestamp_ms)
                main = solo.update(fix, now_ms=fix.timestamp_ms)
                self.assertEqual(dual.baseline, main)

    def test_experimental_crash_preserves_original_result(self):
        comparator = GPSShadowComparison(self.graph, self.coords)
        with patch.object(comparator._experimental, "update",
                          side_effect=RuntimeError("shadow-only failure")):
            actual = comparator.update(self.first_fix, now_ms=1000)
        self.assertEqual(actual.baseline.status, "AMBIGUOUS")
        self.assertIsNone(actual.experimental)
        self.assertIn("shadow-only failure", actual.experiment_error)

    def test_reset_keeps_both_matchers_available(self):
        comparator = GPSShadowComparison(self.graph, self.coords)
        first = comparator.update(self.first_fix, now_ms=1000)
        comparator.reset()
        after = comparator.update(self.first_fix, now_ms=1000)
        self.assertEqual(first, after)

    def test_rejected_input_is_never_upgraded_by_shadow(self):
        comparator = GPSShadowComparison(self.graph, self.coords)
        impossible = GPSFix(1000, .000004, .000270, 3, 100, 87)
        actual = comparator.update(impossible, now_ms=1000)
        self.assertEqual(actual.baseline.status, "REJECTED")
        self.assertEqual(actual.experimental.status, "REJECTED")
        self.assertFalse(actual.disagrees)
