"""First fix after a GPS gap is not trusted alone (owner-approved, 17 Oct 2026). Synthetic road."""
import unittest

from engine import RoadEdge, RoadGraph
from gps.fix_quality import GPSFix
from gps.matcher import DirectedRoadMatcher
from gps.temporal_matcher import TemporalRoadMatcher

POINTS = {"a": (53.0, -2.002), "b": (53.0, -2.0), "c": (53.0, -1.998)}
GRAPH = RoadGraph(POINTS, [RoadEdge("w:1:0:f", "a", "b", 134, 30, "allowed"),
                           RoadEdge("w:1:1:f", "b", "c", 134, 30, "allowed")])


class ConfirmAfterGapTests(unittest.TestCase):
    def matcher(self, **kw):
        return TemporalRoadMatcher(DirectedRoadMatcher(GRAPH, POINTS), **kw)

    def test_first_fix_after_a_gap_only_seeds(self):
        m = self.matcher(confirm_after_gap_ms=10000)
        self.assertEqual(m.update(GPSFix(1000, 53.0, -2.0015, 3, 10, 90), now_ms=1000).status, "MATCHED")
        seed = m.update(GPSFix(30000, 53.0, -1.9990, 3, 10, 90), now_ms=30000)
        self.assertEqual((seed.status, seed.reason), ("AMBIGUOUS", "first_fix_after_gap"))
        self.assertEqual(m.update(GPSFix(31000, 53.0, -1.99885, 3, 10, 90), now_ms=31000).status, "MATCHED")

    def test_original_behaviour_without_the_option(self):
        m = self.matcher()
        m.update(GPSFix(1000, 53.0, -2.0015, 3, 10, 90), now_ms=1000)
        self.assertNotEqual(m.update(GPSFix(30000, 53.0, -1.9990, 3, 10, 90), now_ms=30000).reason,
                            "first_fix_after_gap")


if __name__ == "__main__":
    unittest.main()
