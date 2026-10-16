"""Safety controls for research-only progress; original/default kept intact."""
import unittest
from engine import RoadEdge,RoadGraph
from gps.fix_quality import GPSFix
from gps.matcher import DirectedRoadMatcher
from gps.temporal_matcher import TemporalRoadMatcher

class ResearchForwardProgressTests(unittest.TestCase):
    def setUp(self):
        self.coords={"a":(53,-2),"b":(53,-1.9998),
                     "c":(53.00001,-1.9995),"d":(53.0002,-1.9998)}
        self.edges=[RoadEdge("w:55:0:f","a","b",13,30,"allowed"),
                    RoadEdge("w:55:1:f","b","c",21,30,"allowed")]
        self.old=GPSFix(1000,53,-1.99986,3,10,90)
        self.new=GPSFix(9000,53.000003,-1.99974,3,10,88)
    def execute(self,roads=None,turns=(),fix=None,enabled=True):
        graph=RoadGraph(self.coords,roads or self.edges,turns)
        t=TemporalRoadMatcher(DirectedRoadMatcher(graph,self.coords,
                experimental_adjacent_fragment_equivalence=enabled))
        a=t.update(self.old)
        b=t.update(fix or self.new)
        return a,b
    def test_default_research_rule_not_enabled(self):
        graph=RoadGraph(self.coords,self.edges)
        default=TemporalRoadMatcher(DirectedRoadMatcher(graph,self.coords))
        self.assertFalse(default.matcher.experimental_adjacent_fragment_equivalence)
    def test_rejected_prohibited_turn_not_promoted(self):
        _,result=self.execute(turns=[("w:55:0:f","w:55:1:f")])
        self.assertNotEqual(result.reason,"research_confirmed_directed_progress")
    def test_unrelated_way_never_promoted(self):
        edges=[self.edges[0],RoadEdge("w:56:1:f","b","c",21,30,"allowed")]
        _,result=self.execute(roads=edges)
        self.assertNotEqual(result.reason,"research_confirmed_directed_progress")
    def test_missing_heading_or_weak_fix_not_promoted(self):
        for fix in (GPSFix(9000,self.new.latitude,self.new.longitude,3,0,None),
                    GPSFix(9000,self.new.latitude,self.new.longitude,40,10,88)):
            _,result=self.execute(fix=fix)
            self.assertNotEqual(result.reason,"research_confirmed_directed_progress")
    def test_sharp_bend_not_promoted(self):
        edges=[self.edges[0],RoadEdge("w:55:1:f","b","d",23,30,"allowed")]
        _,result=self.execute(roads=edges)
        self.assertNotEqual(result.reason,"research_confirmed_directed_progress")
