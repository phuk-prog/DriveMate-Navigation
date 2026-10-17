"""Synthetic progress checks, not surveyed roads or real GNSS observations."""
from math import cos, radians, sin
import unittest

from engine import RoadEdge, RoadGraph
from gps.fix_quality import GPSFix
from gps.matcher import DirectedRoadMatcher
from gps.temporal_matcher import TemporalRoadMatcher


class DirectedProgressTests(unittest.TestCase):
    def coordinate(self, along, across=0, heading=90):
        # Fabricated straight 200m road near latitude 53; rotate its direction.
        angle = radians(heading)
        east = along * sin(angle) + across * cos(angle)
        north = along * cos(angle) - across * sin(angle)
        return (53 + north / 111195, east / (111195 * cos(radians(53))))

    def matcher(self, heading=90):
        points = {"a": self.coordinate(0, heading=heading),
                  "b": self.coordinate(200, heading=heading)}
        graph = RoadGraph(points, [RoadEdge("forward", "a", "b", 200, 40, "allowed")])
        return TemporalRoadMatcher(DirectedRoadMatcher(graph, points))

    def fix(self, timestamp, along, *, across=0, heading=90, speed=10, accuracy=3):
        lat, lon = self.coordinate(along, across, heading)
        return GPSFix(timestamp, lat, lon, accuracy, speed, heading)

    def test_backward_position_with_forward_bearing_is_withheld(self):
        matcher = self.matcher()
        self.assertEqual(matcher.update(self.fix(1000, 100)).edge_id, "forward")
        result = matcher.update(self.fix(5000, 60))
        self.assertEqual((result.status, result.edge_id), ("AMBIGUOUS", None))
        self.assertEqual(result.reason, "backward_directed_progress")
        self.assertEqual(matcher.anchor_fix.timestamp_ms, 1000)

    def test_forward_position_still_matches(self):
        matcher = self.matcher()
        matcher.update(self.fix(1000, 60))
        self.assertEqual(matcher.update(self.fix(5000, 100)).edge_id, "forward")

    def test_backward_jitter_within_combined_uncertainty_is_retained(self):
        matcher = self.matcher()
        matcher.update(self.fix(1000, 100))
        self.assertEqual(matcher.update(self.fix(2000, 96)).edge_id, "forward")

    def test_lateral_jitter_does_not_count_as_backward_progress(self):
        matcher = self.matcher()
        matcher.update(self.fix(1000, 100, across=-4))
        self.assertEqual(matcher.update(self.fix(2000, 100, across=4)).edge_id,
                         "forward")

    def test_forward_recovery_uses_unmodified_anchor(self):
        matcher = self.matcher()
        matcher.update(self.fix(1000, 100))
        self.assertIsNone(matcher.update(self.fix(5000, 60)).edge_id)
        self.assertEqual(matcher.update(self.fix(9000, 110)).edge_id, "forward")

    def test_backward_progress_is_not_trusted_when_speed_is_missing(self):
        matcher = self.matcher()
        matcher.update(self.fix(1000, 100, speed=None))
        result = matcher.update(self.fix(5000, 60, speed=None))
        self.assertIsNone(result.edge_id)

    def test_held_out_compass_directions_preserve_sign(self):
        for heading in (0, 45, 180, 225, 270, 315):
            with self.subTest(heading=heading):
                matcher = self.matcher(heading)
                self.assertEqual(matcher.update(
                    self.fix(1000, 100, heading=heading)).edge_id, "forward")
                self.assertIsNone(matcher.update(
                    self.fix(5000, 60, heading=heading)).edge_id)

    def test_combined_uncertainty_controls_when_reverse_motion_is_resolvable(self):
        for accuracy, expected_status in ((3, "AMBIGUOUS"), (15, "MATCHED")):
            with self.subTest(accuracy=accuracy):
                matcher = self.matcher()
                matcher.update(self.fix(1000, 100, accuracy=accuracy))
                result = matcher.update(self.fix(5000, 80, accuracy=accuracy))
                self.assertEqual(result.status, expected_status)

    def test_just_inside_and_outside_uncertainty_budget(self):
        for backward, expected_status in ((5.9, "MATCHED"), (6.1, "AMBIGUOUS")):
            with self.subTest(backward=backward):
                matcher = self.matcher()
                matcher.update(self.fix(1000, 100))
                result = matcher.update(self.fix(5000, 100 - backward))
                self.assertEqual(result.status, expected_status)

    def test_unresolved_fix_does_not_replace_progress_anchor(self):
        matcher = self.matcher()
        matcher.update(self.fix(1000, 100))
        self.assertEqual(matcher.update(
            self.fix(3000, 60, accuracy=90)).status, "UNKNOWN")
        result = matcher.update(self.fix(5000, 60))
        self.assertEqual((result.status, result.reason),
                         ("AMBIGUOUS", "backward_directed_progress"))

    def test_stationary_report_cannot_justify_large_reverse_position(self):
        matcher = self.matcher()
        matcher.update(self.fix(1000, 100, speed=0))
        self.assertIsNone(matcher.update(self.fix(5000, 60, speed=0)).edge_id)


if __name__ == "__main__":
    unittest.main()
