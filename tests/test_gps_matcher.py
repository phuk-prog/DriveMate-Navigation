"""Component-level road matcher checks, not measured UK driving evidence."""
import unittest
from engine import RoadEdge, RoadGraph
from gps.fix_quality import GPSFix
from gps.matcher import DirectedRoadMatcher, angular_difference

class DirectedRoadMatcherTests(unittest.TestCase):
    def setUp(self):
        # Artificial parallel carriageways 6-7m apart with opposing direction.
        self.coords={"w":(53.0,-2.0000),"e":(53.0,-1.9990),
                     "wn":(53.00006,-2.0000),"en":(53.00006,-1.9990),
                     "sp":(53.0000,-1.9985)}
        self.graph=RoadGraph(self.coords,[
            RoadEdge("east","w","e",75,40,"allowed"),
            RoadEdge("west","en","wn",75,40,"allowed"),
            RoadEdge("forbidden","wn","w",10,20,"prohibited"),
            RoadEdge("slip","e","sp",35,25,"allowed")])
        self.matcher=DirectedRoadMatcher(self.graph,self.coords)
    def fix(self,lat=53.0,lon=-1.9995,bearing=90,speed=10,acc=3,t=1000):
        return GPSFix(t,lat,lon,acc,speed,bearing)
    def test_choose_direction_by_heading(self):
        r=self.matcher.match(self.fix())
        self.assertEqual((r.status,r.edge_id),("MATCHED","east"))
        r=self.matcher.match(self.fix(lat=53.00006,bearing=270))
        self.assertEqual((r.status,r.edge_id),("MATCHED","west"))
    def test_stationary_parallel_is_ambiguous(self):
        r=self.matcher.match(self.fix(bearing=None,speed=0))
        self.assertEqual((r.status,r.edge_id),("AMBIGUOUS",None))
    def test_prior_road_cannot_override_opposite_heading(self):
        r=self.matcher.match(self.fix(bearing=270,lat=53.00006),
                             prior_edge_id="east")
        self.assertEqual((r.status,r.edge_id),("MATCHED","west"))
    def test_no_unknown_or_prohibited_edges_selected(self):
        self.assertNotEqual(self.matcher.match(self.fix()).edge_id,"forbidden")
    def test_stale_and_duplicate_fix_rejected(self):
        r=self.matcher.match(self.fix(t=1000),previous_fix=self.fix(t=1000))
        self.assertEqual((r.status,r.reason),("REJECTED","duplicate_or_out_of_order"))
        self.assertEqual(self.matcher.match(self.fix(),now_ms=12000).status,"REJECTED")
    def test_spike_and_weak_accuracy_never_confident(self):
        self.assertEqual(self.matcher.match(self.fix(speed=100)).status,"REJECTED")
        self.assertEqual(self.matcher.match(self.fix(acc=80)).status,"UNKNOWN")
    def test_off_road_returns_unknown(self):
        self.assertEqual(self.matcher.match(self.fix(lat=53.1,lon=-1.9)).status,"UNKNOWN")
    def test_invalid_graph_coordinate_fails(self):
        with self.assertRaises(ValueError):
            DirectedRoadMatcher(self.graph,{"w":(91,0)})
    def test_future_fix_rejected(self):
        self.assertEqual(self.matcher.match(self.fix(t=3000),now_ms=1000).status,"REJECTED")
    def test_no_eligible_road_returns_unknown(self):
        g=RoadGraph({"a","b"},[RoadEdge("x","a","b",50,30,"unknown")])
        m=DirectedRoadMatcher(g,{"a":(53,1),"b":(53,1.001)})
        self.assertEqual(m.match(self.fix()).status,"UNKNOWN")
    def test_angular_wrapping_and_heading(self):
        self.assertAlmostEqual(angular_difference(355,5),10)
        self.assertAlmostEqual(angular_difference(180,0),180)

if __name__=="__main__":
    unittest.main()
