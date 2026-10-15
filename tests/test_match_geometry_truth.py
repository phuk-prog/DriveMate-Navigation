"""Synthetic unit-contract checks of a COMMON geometric proxy, not GPS truth."""
import unittest
from collections import Counter
from engine import RoadEdge,RoadGraph
from gps.fix_quality import GPSFix
from gps.matcher import MatchResult
from benchmarks.match_geometry_truth import (
    closest_point_on_road, expected_road_geometry_probe,
    report_geometry_last_fix,ensure_geometry_denominators,geometry_summary,
    projected_dmn_result)

class CommonGeometryOracleTests(unittest.TestCase):
    def setUp(self):
        self.coords={"a":(53.0,-2.001),"b":(53.0,-2.0),
                     "c":(53.000040,-2.001),"d":(53.000040,-2.0)}
        self.graph=RoadGraph(self.coords,[
            RoadEdge("target","a","b",65,35,"allowed"),
            RoadEdge("parallel","c","d",65,35,"allowed"),
            RoadEdge("reverse","b","a",65,35,"allowed")])
    def test_same_segment_point_is_near_but_does_not_prove_direction(self):
        p=expected_road_geometry_probe(self.graph,self.coords,"target",(53.0,-2.0005))
        self.assertEqual(p["state"],"near_generated_geometry")
        self.assertGreaterEqual(p["nearby_other_directed_edges"],2)
        self.assertEqual(p["reverse_same_segment_directed_edges"],1)
        self.assertEqual(p["nearby_disjoint_graph_segments"],1)
        self.assertEqual(p["nearby_adjacent_graph_segments"],0)
        self.assertFalse(p["direction_verified"])
    def test_wrong_parallel_link_can_still_be_geometrically_near(self):
        p=expected_road_geometry_probe(self.graph,self.coords,"target",(53.000040,-2.0005))
        self.assertTrue(p["near_expected_geometry"])
        self.assertGreater(p["nearby_other_directed_edges"],0)
    def test_reverse_direction_is_not_a_distinct_physical_segment(self):
        coords={"a":(53.,-2.001),"b":(53.,-2.),
                "c":(53.00004,-2.001),"d":(53.00004,-2.)}
        graph=RoadGraph(coords,[
            RoadEdge("w:100:0:f","a","b",70,30,"allowed"),
            RoadEdge("w:100:0:r","b","a",70,30,"allowed")])
        observation=expected_road_geometry_probe(graph,coords,"w:100:0:f",(53.,-2.0005))
        self.assertEqual(observation["nearby_other_directed_edges"],1)
        self.assertEqual(observation["nearby_reversed_same_segment_edges"],1)
        self.assertEqual(observation["nearby_distinct_osm_way_edges"],0)
        self.assertFalse(observation["direction_verified"])
        counts=Counter()
        report_geometry_last_fix(counts,"provider",graph,coords,"w:100:0:f",(53.,-2.0005))
        summary=geometry_summary(counts,"provider")
        self.assertEqual(summary["near_and_reverse_same_segment_only"],1)
        self.assertEqual(summary["near_and_distinct_osm_way_present"],0)

    def test_separate_osm_way_close_to_target_is_still_a_risk(self):
        coords={"a":(53.,-2.001),"b":(53.,-2.),
                "c":(53.00004,-2.001),"d":(53.00004,-2.)}
        graph=RoadGraph(coords,[
            RoadEdge("w:100:0:f","a","b",70,30,"allowed"),
            RoadEdge("w:100:0:r","b","a",70,30,"allowed"),
            RoadEdge("w:200:0:f","c","d",70,30,"allowed")])
        observation=expected_road_geometry_probe(graph,coords,"w:100:0:f",(53.,-2.0005))
        self.assertEqual(observation["nearby_reversed_same_segment_edges"],1)
        self.assertEqual(observation["nearby_distinct_osm_way_edges"],1)
        counts=Counter()
        report_geometry_last_fix(counts,"test",graph,coords,"w:100:0:f",(53.,-2.0005))
        summary=geometry_summary(counts,"test")
        self.assertEqual(summary["near_and_reverse_same_segment_only"],0)
        self.assertEqual(summary["near_and_distinct_osm_way_present"],1)

    def test_same_way_adjacent_segment_is_not_a_distinct_way(self):
        coords={"a":(53.,-2.001),"b":(53.,-2.),"c":(53.,-1.999)}
        graph=RoadGraph(coords,[
            RoadEdge("w:100:0:f","a","b",70,30,"allowed"),
            RoadEdge("w:100:1:f","b","c",70,30,"allowed")])
        p=expected_road_geometry_probe(graph,coords,"w:100:0:f",(53.,-2.00001))
        self.assertEqual(p["nearby_other_segments_same_osm_way"],1)
        self.assertEqual(p["nearby_distinct_osm_way_edges"],0)

    def test_far_point_is_not_source_geometry_match(self):
        p=expected_road_geometry_probe(self.graph,self.coords,"target",(53.0005,-2.0005))
        self.assertEqual(p["state"],"off_generated_geometry")
    def test_unavailable_is_not_success(self):
        p=expected_road_geometry_probe(self.graph,self.coords,"target",None)
        self.assertEqual(p["state"],"withheld")
    def test_invalid_point_fails_closed(self):
        with self.assertRaises(ValueError):
            expected_road_geometry_probe(self.graph,self.coords,"target",(float("nan"),-2))
        with self.assertRaises(ValueError):
            expected_road_geometry_probe(self.graph,self.coords,"unknown",(53,-2))
    def test_projection_clamps_to_road_endpoints(self):
        snap=closest_point_on_road((53.0,-2.003),self.coords["a"],self.coords["b"])
        self.assertAlmostEqual(snap[0][1],-2.001,places=6)
    def test_dmn_same_geometry_uses_same_oracle(self):
        fix=GPSFix(1000,53,-2.0005,3,10,90)
        p=projected_dmn_result(MatchResult("MATCHED","target","ok",0,1),
                               fix,self.graph,self.coords)
        self.assertTrue(expected_road_geometry_probe(self.graph,self.coords,"target",p)["near_expected_geometry"])
        self.assertIsNone(projected_dmn_result(MatchResult("AMBIGUOUS",None,"x",0,2),
                               fix,self.graph,self.coords))

    def test_reverse_only_is_not_a_second_physical_road(self):
        pts={"a":(53.0,-2.001),"b":(53.0,-2.0)}
        g=RoadGraph(pts,[RoadEdge("f","a","b",65,35,"allowed"),
                         RoadEdge("r","b","a",65,35,"allowed")])
        result=expected_road_geometry_probe(g,pts,"f",(53.0,-2.0005))
        self.assertEqual(result["nearby_other_directed_edges"],1)
        self.assertEqual(result["reverse_same_segment_directed_edges"],1)
        self.assertEqual(result["nearby_disjoint_graph_segments"],0)
        self.assertEqual(result["nearby_adjacent_graph_segments"],0)
    def test_junction_continuation_not_classed_as_parallel_road(self):
        pts={"a":(53.0,-2.001),"b":(53.0,-2.0),"c":(53.0,-1.999)}
        g=RoadGraph(pts,[RoadEdge("a","a","b",65,35,"allowed"),
                         RoadEdge("b","b","c",65,35,"allowed")])
        result=expected_road_geometry_probe(g,pts,"a",(53.0,-2.00001))
        self.assertEqual(result["nearby_adjacent_graph_segments"],1)
        self.assertEqual(result["nearby_disjoint_graph_segments"],0)
    def test_overlapping_disconnected_road_is_flagged_not_verified_wrong(self):
        pts={"a":(53.0,-2.001),"b":(53.0,-2.0),
             "c":(53.0,-2.001),"d":(53.0,-2.0)}
        g=RoadGraph(pts,[RoadEdge("a","a","b",65,35,"allowed"),
                         RoadEdge("other","c","d",65,35,"allowed")])
        result=expected_road_geometry_probe(g,pts,"a",(53.0,-2.0005))
        self.assertEqual(result["nearby_disjoint_graph_segments"],1)
        self.assertFalse(result["direction_verified"])
    def test_denominator_and_risky_road_alternatives(self):
        totals=Counter()
        report_geometry_last_fix(totals,"provider",self.graph,self.coords,"target",(53,-2.0005))
        report_geometry_last_fix(totals,"provider",self.graph,self.coords,"target",None)
        report_geometry_last_fix(totals,"provider",self.graph,self.coords,"target",(53.001,-2.0005))
        ensure_geometry_denominators(totals,("provider",),3)
        result=geometry_summary(totals,"provider")
        self.assertEqual((result["near_generating_road_within_5m"],
                          result["not_alignable_or_withheld"],
                          result["farther_than_5m_from_generating_road"]),(1,1,1))
        self.assertEqual(result["near_but_alternative_directed_roads_within_10m"],1)
        self.assertEqual(result["near_with_opposite_direction_of_same_segment"],1)
        self.assertEqual(result["near_with_disjoint_graph_segments"],1)
        self.assertEqual(result["near_with_connected_junction_segments"],0)
        with self.assertRaises(AssertionError):
            ensure_geometry_denominators(totals,("provider",),4)

if __name__=="__main__":
    unittest.main()
