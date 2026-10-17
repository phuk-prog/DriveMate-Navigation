"""Analytical selector checks only; GitHub runs real UK OSM-region probes."""
import unittest
from engine import RoadGraph,RoadEdge
from benchmarks.gps_uk_region_progress import sample_pairs
class MultipleUKRoadSelectorTests(unittest.TestCase):
    def test_distinct_incoming_osm_way_ids(self):
        graph=RoadGraph("abcde",[
            RoadEdge("w:1:0:f","a","b",25,30,"allowed"),
            RoadEdge("w:1:1:f","b","c",25,30,"allowed"),
            RoadEdge("w:2:0:f","c","d",25,30,"allowed"),
            RoadEdge("w:3:0:f","d","e",25,30,"allowed")])
        r=sample_pairs(graph)
        self.assertEqual(len(r),2)
        self.assertEqual(len({a.edge_id.split(":")[1] for a,b in r}),2)
    def test_restricted_movements_excluded(self):
        graph=RoadGraph("abc",[
            RoadEdge("w:1:0:f","a","b",25,30,"allowed"),
            RoadEdge("w:2:0:f","b","c",25,30,"allowed")],
            [("w:1:0:f","w:2:0:f")])
        self.assertEqual(sample_pairs(graph),[])
