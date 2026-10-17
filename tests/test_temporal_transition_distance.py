"""Synthetic folded-road counterexamples; no personal or surveyed GPS data."""
import unittest

from engine import RoadEdge, RoadGraph
from gps.fix_quality import GPSFix
from gps.matcher import DirectedRoadMatcher
from gps.temporal_matcher import TemporalRoadMatcher


class TemporalTransitionDistanceTests(unittest.TestCase):
    def matcher(self, length=1000):
        # Two nearly parallel directed links meet only at a distant hairpin.
        # Coordinates are fabricated near the equator for simple metre scales.
        points = {"a": (0.0, 0.0), "b": (0.0, length / 111195),
                  "c": (20 / 111195, 0.0)}
        graph = RoadGraph(points, [
            RoadEdge("outbound", "a", "b", length, 40, "allowed"),
            RoadEdge("return", "b", "c", length + 1, 40, "allowed")])
        return TemporalRoadMatcher(DirectedRoadMatcher(graph, points))

    def fix(self, timestamp, x, y, heading, speed=10, accuracy=3):
        return GPSFix(timestamp, y / 111195, x / 111195,
                      accuracy, speed, heading)

    def test_nearby_return_road_cannot_be_reached_via_distant_junction(self):
        matcher = self.matcher()
        self.assertEqual(matcher.update(self.fix(1000, 100, 0, 90)).edge_id,
                         "outbound")
        # Just 18m apart physically, but ~1800m via the shared vertex in 2s.
        result = matcher.update(self.fix(3000, 100, 18, 270))
        self.assertEqual(result.status, "AMBIGUOUS")
        self.assertEqual(result.reason, "implausible_road_transition")
        self.assertIsNone(result.edge_id)
        self.assertEqual(matcher.anchor_edge_id, "outbound")

    def test_short_plausible_junction_transition_is_retained(self):
        matcher = self.matcher()
        self.assertEqual(matcher.update(self.fix(1000, 990, 0, 90)).edge_id,
                         "outbound")
        result = matcher.update(self.fix(3000, 990, 0.2, 270))
        self.assertEqual((result.status, result.edge_id), ("MATCHED", "return"))

    def test_rejected_transition_can_recover_on_original_road(self):
        matcher = self.matcher()
        matcher.update(self.fix(1000, 100, 0, 90))
        self.assertIsNone(matcher.update(self.fix(3000, 100, 18, 270)).edge_id)
        result = matcher.update(self.fix(5000, 120, 0, 90))
        self.assertEqual((result.status, result.edge_id), ("MATCHED", "outbound"))

    def test_held_out_fold_sizes_and_speeds_withhold_impossible_transitions(self):
        # Different sizes/speeds from the reproducer; every shared-junction
        # trip exceeds 100m while the maximum 2-second budget is only 90m.
        for length in (100, 350, 1700):
            for speed in (0, 5, 15):
                with self.subTest(length=length, speed=speed):
                    matcher = self.matcher(length)
                    self.assertEqual(matcher.update(
                        self.fix(1000, length * 0.1, 0, 90, speed)).edge_id,
                        "outbound")
                    result = matcher.update(
                        self.fix(3000, length * 0.1, 18, 270, speed))
                    self.assertIsNone(result.edge_id)

    def test_missing_speed_still_enforces_generic_physical_limit(self):
        matcher = self.matcher()
        self.assertEqual(matcher.update(
            self.fix(1000, 100, 0, 90, speed=None)).edge_id, "outbound")
        result = matcher.update(self.fix(3000, 100, 18, 270, speed=None))
        self.assertEqual((result.status, result.reason),
                         ("AMBIGUOUS", "implausible_road_transition"))

    def test_time_budget_uses_anchor_before_unresolved_readings(self):
        matcher = self.matcher()
        matcher.update(self.fix(1000, 990, 0, 90))
        self.assertEqual(matcher.update(
            self.fix(2500, 990, 0.1, 90, accuracy=90)).status, "UNKNOWN")
        # 20m over the full 2s is plausible; treating the weak fix as the
        # anchor would falsely reduce the time budget to just half a second.
        result = matcher.update(self.fix(3000, 990, 0.2, 270, speed=2))
        self.assertEqual((result.status, result.edge_id), ("MATCHED", "return"))


if __name__ == "__main__":
    unittest.main()
