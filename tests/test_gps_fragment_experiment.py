"""Opt-in GPS road-fragment experiment; defaults stay conservative."""
import unittest
from engine import RoadGraph, RoadEdge
from gps.fix_quality import GPSFix
from gps.matcher import LEGACY_MATCHER, DirectedRoadMatcher

class FragmentExperimentTests(unittest.TestCase):
    def setUp(self):
        self.coords={"a":(0,0),"b":(0,.0002),"c":(.000015,.00047),
                     "p":(.000045,0),"q":(.000045,.0002)}
        self.edges=[RoadEdge("w:1:0:f","a","b",23,30,"allowed"),
                    RoadEdge("w:1:1:f","b","c",30,30,"allowed")]
        self.fix=GPSFix(1000,.000004,.000270,3,10,87)
    def matcher(self,edges=None,**kwargs):  # the research variant is defined against the pre-Run-C matcher
        return DirectedRoadMatcher(RoadGraph(self.coords,edges or self.edges),self.coords,
                                   **{**LEGACY_MATCHER,**kwargs})
    def test_existing_default_stays_ambiguous(self):
        self.assertEqual(self.matcher().match(self.fix).status,"AMBIGUOUS")
    def test_opt_in_resolves_small_same_way_bend(self):
        r=self.matcher(experimental_adjacent_fragment_equivalence=True).match(self.fix)
        self.assertEqual((r.status,r.edge_id),("MATCHED","w:1:1:f"))
    def test_other_way_branch_stays_ambiguous(self):
        road=[self.edges[0],RoadEdge("w:2:1:f","b","c",30,30,"allowed")]
        self.assertEqual(self.matcher(road,experimental_adjacent_fragment_equivalence=True)
                         .match(self.fix).status,"AMBIGUOUS")
    def test_stationary_fix_stays_ambiguous(self):
        self.assertEqual(self.matcher(experimental_adjacent_fragment_equivalence=True)
             .match(GPSFix(1000,.000004,.000270,3,0,None)).status,"AMBIGUOUS")
    def test_prohibited_mapped_turn_stays_ambiguous(self):
        graph=RoadGraph(self.coords,self.edges,[("w:1:0:f","w:1:1:f")])
        matcher=DirectedRoadMatcher(graph,self.coords,
                 experimental_adjacent_fragment_equivalence=True)
        self.assertEqual(matcher.match(self.fix).status,"AMBIGUOUS")
    def test_opt_in_never_accepts_non_boolean(self):
        with self.assertRaises(ValueError):
            self.matcher(experimental_adjacent_fragment_equivalence=1)
