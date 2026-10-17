"""Small synthetic oracle checks; real-road exploration runs separately in CI."""
import unittest

from engine import RoadEdge, RoadGraph
from benchmarks.public_route_preferences import (
    _road_pairs, probe_preference_diversity)


class PreferenceCaseDiscoveryTests(unittest.TestCase):
    def test_divergent_road_paths_are_discovered_with_real_search(self):
        pts=["A","B","C","D","E","F","G","H"]
        roads=[
            RoadEdge("AB","A","B",50,10,"allowed"),
            RoadEdge("BD","B","D",50,10,"allowed"),
            RoadEdge("AC","A","C",160,80,"allowed"),
            RoadEdge("CE","C","E",80,80,"allowed"),
            RoadEdge("EF","E","F",70,80,"allowed"),
            RoadEdge("FD","F","D",60,80,"allowed"),
            RoadEdge("DG","D","G",80,50,"allowed"),
            RoadEdge("GH","G","H",80,50,"allowed"),
        ]
        graph=RoadGraph(pts,roads)
        r=probe_preference_diversity(graph,snapshot_id="synthetic-fixture",maximum_pairs=40)
        self.assertGreater(r["map_derived_preference_pairs_checked"],0)
        self.assertGreater(r["fastest_and_shortest_different_path_pairs"],0)
        self.assertGreaterEqual(r["map_derived_pairs_with_multiple_routes"],
                                r["fastest_and_shortest_different_path_pairs"])
        self.assertEqual(r["route_preference_discriminating_coverage"],
                         "MAP_DIVERGENCE_OBSERVED")
        self.assertFalse(r["independently_verified_traffic_legality_or_lane_truth"])

    def test_one_path_does_not_masquerade_as_comparison(self):
        p=RoadGraph(["A","B","C","D","E","F"],[
            RoadEdge("AB","A","B",10,20,"allowed"),
            RoadEdge("BC","B","C",10,20,"allowed"),
            RoadEdge("CD","C","D",10,20,"allowed"),
            RoadEdge("DE","D","E",10,20,"allowed"),
            RoadEdge("EF","E","F",10,20,"allowed")])
        r=probe_preference_diversity(p,snapshot_id="synthetic",maximum_pairs=20)
        self.assertGreater(r["map_derived_preference_pairs_checked"],0)
        self.assertEqual(r["fastest_and_shortest_different_path_pairs"],0)
        self.assertEqual(r["route_preference_discriminating_coverage"],
                         "INSUFFICIENT")

    def test_no_personal_origin_destination_in_aggregate(self):
        p=RoadGraph(["A","B"],[RoadEdge("AB","A","B",10,20,"allowed")])
        result=probe_preference_diversity(p,snapshot_id="fixture")
        self.assertEqual(result["map_derived_preference_pairs_checked"],0)
        self.assertEqual(result["route_preference_discriminating_coverage"],
                         "INSUFFICIENT")
        self.assertNotIn("A",result)
        self.assertNotIn("B",result)

    def test_unavailable_and_invalid_counts(self):
        g=RoadGraph(["A"],[])
        with self.assertRaises(ValueError):
            list(_road_pairs(g,maximum_pairs=0))
        with self.assertRaises(ValueError):
            probe_preference_diversity(g,snapshot_id="fixture",maximum_pairs=241)


if __name__=="__main__":
    unittest.main()
