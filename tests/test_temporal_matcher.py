"""Temporal matcher candidate tests: graph fixtures, not live GPS evidence."""
import unittest
from engine import RoadEdge, RoadGraph
from gps.fix_quality import GPSFix
from gps.matcher import DirectedRoadMatcher
from gps.temporal_matcher import TemporalRoadMatcher


class TemporalRoadMatcherTests(unittest.TestCase):
    def setUp(self):
        # Parallel eastbound roads separated 5m, with a distinct feeder
        # joining only the northern road. Fixed fabricated geometry for unit
        # tests, never presented as real UK OSM.
        self.pts = {
            "p":(53.000045,-2.0015), "a":(53.000045,-2.0000),
            "b":(53.000045,-1.9990),
            "c":(53.0,-2.0000), "d":(53.0,-1.9990)
        }
        self.g=RoadGraph(self.pts,[
            RoadEdge("feeder","p","a",95,40,"allowed"),
            RoadEdge("north","a","b",65,40,"allowed"),
            RoadEdge("south","c","d",65,40,"allowed")])
        self.m=TemporalRoadMatcher(DirectedRoadMatcher(self.g,self.pts))
    def fix(self,t=1000,lat=53.000045,lon=-2.0009,bearing=90,
            speed=10,accuracy=3):
        return GPSFix(t,lat,lon,accuracy,speed,bearing)
    def anchor(self):
        self.assertEqual(self.m.update(self.fix(t=1000,lon=-2.0013)).edge_id,"feeder")

    def test_standalone_parallel_remains_ambiguous(self):
        r=self.m.update(self.fix(t=1000))
        self.assertEqual(r.status,"AMBIGUOUS")
    def test_connected_road_can_be_selected_after_anchor(self):
        self.anchor()
        r=self.m.update(self.fix(t=7000,lon=-1.9998))
        self.assertEqual((r.status,r.edge_id,r.reason),
                         ("MATCHED","north","unique_legal_temporal_connection"))
    def test_legal_incoming_restriction_prevents_supposed_continuity(self):
        points=self.pts
        g=RoadGraph(points,list(self.g.edges.values()),
                    prohibited_turns=[("feeder","north")])
        temporal=TemporalRoadMatcher(DirectedRoadMatcher(g,points))
        self.assertEqual(temporal.update(self.fix(t=1000,lon=-2.0013)).edge_id,"feeder")
        r=temporal.update(self.fix(t=7000,lon=-1.9998))
        self.assertNotEqual(r.status,"MATCHED")
    def test_disconnected_road_jump_is_withheld(self):
        self.anchor()
        r=self.m.update(self.fix(t=5000,lat=53.0,lon=-1.9995))
        self.assertNotEqual(r.status,"MATCHED")
    def test_without_movement_heading_no_temporal_overconfidence(self):
        self.anchor()
        r=self.m.update(self.fix(t=7000,lon=-1.9998,bearing=None,speed=0))
        self.assertEqual(r.status,"AMBIGUOUS")
    def test_long_gap_expires_anchor(self):
        self.anchor()
        r=self.m.update(self.fix(t=90000,lon=-1.9998))
        self.assertEqual(r.status,"AMBIGUOUS")
    def test_rejected_bad_speed_keeps_anchor_then_recovers(self):
        self.anchor()
        r=self.m.update(self.fix(t=2000,lon=-2.0009,speed=150))
        self.assertEqual(r.status,"REJECTED")
        r=self.m.update(self.fix(t=7000,lon=-1.9998))
        self.assertEqual(r.edge_id,"north")
    def test_two_bad_fixes_expire_anchor(self):
        self.anchor()
        for timestamp in (2000,3000,4000):
            self.assertEqual(self.m.update(self.fix(t=timestamp,speed=120)).status,"REJECTED")
        self.assertEqual(self.m.update(self.fix(t=7000,lon=-1.9998)).status,"AMBIGUOUS")
    def test_reset_does_not_leak_prior_anchor(self):
        self.anchor()
        self.m.reset()
        r=self.m.update(self.fix(t=7000,lon=-1.9998))
        self.assertEqual(r.status,"AMBIGUOUS")
    def test_invalid_new_config_is_rejected(self):
        with self.assertRaises(ValueError):
            TemporalRoadMatcher(DirectedRoadMatcher(self.g,self.pts),
                                max_anchor_age_ms=-5)
    def test_conflicting_reachable_roads_stay_ambiguous(self):
        # Two geometrically coincident ways from the same prior road.
        points={**self.pts,"z":self.pts["b"]}
        edges=list(self.g.edges.values())+[RoadEdge("parallel-branch","a","z",65,40,"allowed")]
        g=RoadGraph(points,edges)
        m=TemporalRoadMatcher(DirectedRoadMatcher(g,points))
        self.assertEqual(m.update(self.fix(t=1000,lon=-2.0013)).edge_id,"feeder")
        r=m.update(self.fix(t=7000,lon=-1.9998))
        self.assertEqual(r.status,"AMBIGUOUS")


if __name__=="__main__":
    unittest.main()
