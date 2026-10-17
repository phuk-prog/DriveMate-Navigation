import unittest
from engine import RoadEdge,RoadGraph
from benchmarks.route_adherence import check_route_line
class RouteLineTests(unittest.TestCase):
    def setUp(self):
        self.coords={"a":(53,-2),"b":(53,-1.9998),
                     "c":(53.0002,-1.9998),"d":(53.0002,-1.9996)}
        edges=[RoadEdge("ab","a","b",15,30,"allowed"),
               RoadEdge("bc","b","c",23,30,"allowed"),
               RoadEdge("cd","c","d",15,30,"allowed")]
        self.graph=RoadGraph(self.coords,edges)
        self.ids=("ab","bc","cd")
    def test_vertex_by_vertex_route_adheres(self):
        self.assertEqual(check_route_line(self.graph,self.coords,self.ids,
                [self.coords[x] for x in ("a","b","c","d")])["status"],"PASS")
    def test_corner_cutting_detected(self):
        result=check_route_line(self.graph,self.coords,self.ids,
                [self.coords[x] for x in ("a","b","d")])
        self.assertEqual(result["status"],"FAIL")
        self.assertIn("c",result["missing_road_nodes"])
    def test_offroad_geometry_fails(self):
        pts=[self.coords["a"],(53.01,-1.99),self.coords["d"]]
        self.assertEqual(check_route_line(self.graph,self.coords,self.ids,pts)["status"],"FAIL")
    def test_illegal_transition_rejected(self):
        with self.assertRaises(ValueError):
            check_route_line(self.graph,self.coords,("ab","cd"),
                             [self.coords["a"],self.coords["d"]])
