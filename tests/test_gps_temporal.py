"""Synthetic parallel-road temporal safety regressions; no field accuracy."""
import unittest
from engine import RoadEdge,RoadGraph
from gps.fix_quality import GPSFix
from gps.matcher import DirectedRoadMatcher
from gps.temporal import TemporalState,advance

class TemporalGPSMatcherTests(unittest.TestCase):
    def setUp(self):
        p={"a":(53.0,-2.0),"b":(53.0,-1.999),"c":(53.000045,-2.0),
           "d":(53.000045,-1.999),"e":(53.0,-1.998)}
        g=RoadGraph(p,[RoadEdge("south","a","b",65,35,"allowed"),
                       RoadEdge("north","c","d",65,35,"allowed"),
                       RoadEdge("next","b","e",65,35,"allowed")])
        self.m=DirectedRoadMatcher(g,p)
    def fix(self,t,lat=53.0,lon=-1.9995,speed=10,bearing=90,acc=3):
        return GPSFix(t,lat,lon,acc,speed,bearing)
    def test_first_parallel_fix_withheld(self):
        r=advance(self.m,TemporalState(),self.fix(1000))
        self.assertEqual(r.match.status,"AMBIGUOUS")
    def test_two_parallel_fixes_still_withheld(self):
        a=advance(self.m,TemporalState(),self.fix(1000))
        b=advance(self.m,a.state,self.fix(2000,lon=-1.9994))
        self.assertEqual(b.match.status,"AMBIGUOUS")
    def test_topology_resolves_after_entering_unique_continuation(self):
        a=advance(self.m,TemporalState(),self.fix(1000))
        b=advance(self.m,a.state,self.fix(11000,lon=-1.9985))
        self.assertEqual((b.match.status,b.match.edge_id),("MATCHED","next"))
    def test_rejected_speed_spike_does_not_update_history(self):
        a=advance(self.m,TemporalState(),self.fix(1000))
        b=advance(self.m,a.state,self.fix(2000,speed=130))
        self.assertEqual(b.match.status,"REJECTED")
        self.assertEqual(b.state,a.state)
    def test_weak_accuracy_resets_road_confidence(self):
        a=advance(self.m,TemporalState(),self.fix(1000))
        b=advance(self.m,a.state,self.fix(2000,acc=100))
        self.assertEqual(b.match.status,"UNKNOWN")
        self.assertFalse(b.state.possible_edges)
    def test_no_disconnected_jump_confidently_matched(self):
        a=advance(self.m,TemporalState(),self.fix(1000,lat=53.000045))
        b=advance(self.m,a.state,self.fix(2000,lat=53.0,lon=-1.9985))
        self.assertNotEqual(b.match.status,"MATCHED")
    def test_fast_graph_connected_jump_rejected_by_speed_consistency(self):
        a=advance(self.m,TemporalState(),self.fix(1000))
        b=advance(self.m,a.state,self.fix(2000,lon=-1.9985))
        self.assertEqual((b.match.status,b.match.reason),
                         ("REJECTED","distance_speed_disagreement"))
        self.assertEqual(b.state,a.state)
    def test_stale_fix_rejected_without_state_advance(self):
        a=advance(self.m,TemporalState(),self.fix(1000))
        b=advance(self.m,a.state,self.fix(2000),now_ms=15000)
        self.assertEqual(b.match.status,"REJECTED")
        self.assertEqual(b.state,a.state)

if __name__=="__main__":
    unittest.main()
