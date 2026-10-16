"""Non-OSM unit checks for pinned variant script shape; full real-map runs in CI."""
import unittest
from engine import RoadEdge,RoadGraph
from benchmarks.gps003_research_variant import uk_pairs
class GPSResearchVariantShapeTests(unittest.TestCase):
    def test_uk_pair_selection_is_deterministic(self):
        g=RoadGraph(("a","b","c"),(
            RoadEdge("w:1:0:f","a","b",21,30,"allowed"),
            RoadEdge("w:1:1:f","b","c",21,30,"allowed")))
        self.assertEqual([(a.edge_id,b.edge_id) for a,b in uk_pairs(g)],
            [("w:1:0:f","w:1:1:f")])
    def test_unverified_road_is_never_selected_as_allowed(self):
        g=RoadGraph(("a","b","c"),(
            RoadEdge("w:1:0:f","a","b",21,30,"allowed"),
            RoadEdge("w:1:1:f","b","c",21,30,"unknown")))
        self.assertEqual(uk_pairs(g),[])
