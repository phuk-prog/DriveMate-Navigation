"""The matcher's area index finds exactly the roads a full search finds (stage 1, 17 Oct 2026)."""
import random
import unittest

from engine import RoadEdge, RoadGraph
from gps.fix_quality import GPSFix
from gps.matcher import DirectedRoadMatcher


class AreaIndexTests(unittest.TestCase):
    def test_same_candidates_as_a_full_search(self):
        rnd = random.Random(7)
        points, edges = {}, []
        for i in range(40):  # a 40 x 40 street grid, about 60 m blocks, around Manchester
            for j in range(40):
                points[f"{i}:{j}"] = (53.48 + i * 0.00055, -2.24 + j * 0.0009)
        for i in range(40):
            for j in range(40):
                for di, dj in ((0, 1), (1, 0)):
                    if i + di < 40 and j + dj < 40:
                        a, b = f"{i}:{j}", f"{i + di}:{j + dj}"
                        edges += [RoadEdge(f"w:{i * 1000 + j * 10 + di}:0:f", a, b, 60, 30, "allowed"),
                                  RoadEdge(f"w:{i * 1000 + j * 10 + di}:0:r", b, a, 60, 30, "allowed")]
        m = DirectedRoadMatcher(RoadGraph(points, edges), points)
        for k in range(400):
            fix = GPSFix(k * 1000, 53.48 + rnd.uniform(0, 0.0215), -2.24 + rnd.uniform(0, 0.035),
                         rnd.choice([3, 5, 10, 20]), rnd.choice([None, 0.0, 9.0]), rnd.choice([None, 0.0, 90.0, 180.0]))
            fast = m._candidates(fix)
            saved = m._near
            m._near = lambda f: m._allowed
            try:
                full = m._candidates(fix)
            finally:
                m._near = saved
            self.assertEqual([c.edge_id for c in fast], [c.edge_id for c in full])


if __name__ == "__main__":
    unittest.main()
