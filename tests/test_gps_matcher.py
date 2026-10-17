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


    def test_same_heading_close_parallel_roads_are_ambiguous(self):
        # Distinct, nearly parallel same-direction roads 5 m apart.
        points={"a":(53.0,-2.0000),"b":(53.0,-1.9990),
                "c":(53.000045,-2.0000),"d":(53.000045,-1.9990)}
        roads=RoadGraph(points,[RoadEdge("south","a","b",65,35,"allowed"),
                                RoadEdge("north","c","d",65,35,"allowed")])
        matcher=DirectedRoadMatcher(roads,points)
        observed=GPSFix(1000,53.000045,-1.9995,3,10,90)
        value=matcher.match(observed)
        self.assertEqual(value.status,"AMBIGUOUS")
        self.assertIsNone(value.edge_id)
    def test_same_heading_parallel_priors_do_not_force_a_wrong_match(self):
        points={"a":(53.0,-2.0000),"b":(53.0,-1.9990),
                "c":(53.000045,-2.0000),"d":(53.000045,-1.9990)}
        roads=RoadGraph(points,[RoadEdge("south","a","b",65,35,"allowed"),
                                RoadEdge("north","c","d",65,35,"allowed")])
        matcher=DirectedRoadMatcher(roads,points)
        observed=GPSFix(1000,53.000045,-1.9995,3,10,90)
        value=matcher.match(observed,prior_edge_id="south")
        self.assertEqual(value.status,"AMBIGUOUS")
    def test_recover_only_after_a_valid_fix(self):
        good=self.fix(t=1000)
        bad=self.fix(t=2000,speed=120)
        good_again=self.fix(t=3000)
        self.assertEqual(self.matcher.match(bad,previous_fix=good).status,"REJECTED")
        result=self.matcher.match(good_again,previous_fix=good)
        self.assertEqual((result.status,result.edge_id),("MATCHED","east"))
    def _bend(self):
        # one OSM way bending at b by 30 degrees, plus a different way's piece alongside
        points={"a":(53.0,-2.0010),"b":(53.0,-2.0),"c":(53.00045,-1.99915),
                "p":(53.00006,-2.0010),"q":(53.00006,-2.0)}
        roads=RoadGraph(points,[RoadEdge("w:7:0:f","a","b",67,35,"allowed"),
                                RoadEdge("w:7:1:f","b","c",58,35,"allowed"),
                                RoadEdge("w:9:0:f","p","q",67,35,"allowed"),
                                RoadEdge("w:7:2:f","c","a",120,35,"unknown")])
        return roads,points
    def test_same_road_pieces_resolves_a_bend_of_one_way_only(self):
        roads,points=self._bend()
        near_bend=GPSFix(1000,53.0000,-2.00005,3,10,90)
        self.assertEqual(DirectedRoadMatcher(roads,points).match(near_bend).status,"AMBIGUOUS")
        improved=DirectedRoadMatcher(roads,points,same_road_pieces=True)
        # the other way's piece 6.7 m away still keeps it ambiguous: different roads stay apart
        self.assertEqual(improved.match(near_bend).status,"AMBIGUOUS")
        far_from_other=GPSFix(1000,53.0000,-2.00005,3,10,60)
        roads2=RoadGraph({k:v for k,v in points.items() if k not in "pq"},
                         [e for e in roads.edges.values() if not e.edge_id.startswith("w:9")])
        value=DirectedRoadMatcher(roads2,points,same_road_pieces=True).match(far_from_other)
        self.assertEqual(value.status,"MATCHED")
        stopped=GPSFix(1000,53.0000,-2.00005,3,0,None)
        self.assertNotEqual(DirectedRoadMatcher(roads2,points,same_road_pieces=True).match(stopped).status,
                            "MATCHED")
    def test_route_aware_access_only_adds_planned_uncertain_roads(self):
        roads,points=self._bend()
        on_unknown=GPSFix(1000,53.000225,-2.000075,3,10,248)  # middle of c->a, heading along it
        plain=DirectedRoadMatcher(roads,points,route_aware_access=True)
        self.assertEqual(plain.match(on_unknown).status,"UNKNOWN")
        plain.set_route(["w:7:0:f","w:7:2:f"])
        self.assertEqual(plain.match(on_unknown).edge_id,"w:7:2:f")
        off=DirectedRoadMatcher(roads,points)
        off.set_route(["w:7:2:f"])  # without the mode it does nothing
        self.assertEqual(off.match(on_unknown).status,"UNKNOWN")

if __name__=="__main__":
    unittest.main()
