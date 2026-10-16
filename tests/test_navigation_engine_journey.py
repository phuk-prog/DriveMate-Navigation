"""Analytical navigation-core journey using real DMN objects, NOT an app.

The test's roads, clocks and GPS are invented. No real UK driving result.
"""
import unittest
from engine import RoadEdge,RoadGraph,shortest_route
from engine.rerouting_controller import ReroutingController
from engine.arrival_controller import ArrivalController
from gps.matcher import DirectedRoadMatcher
from gps.fix_quality import GPSFix
from benchmarks.route_adherence import check_route_line
from engine.instruction_cues import instruction_phase

class NavigationEngineJourneyTests(unittest.TestCase):
    def setUp(self):
        self.coords={"a":(53,-2),"b":(53,-1.9998),"c":(53,-1.9996),
                     "d":(53,-1.9994),"e":(53.0002,-1.9998),
                     "f":(53.0002,-1.9996)}
        self.edges=[
            RoadEdge("w:1:0:f","a","b",14,30,"allowed"),
            RoadEdge("w:1:1:f","b","c",14,30,"allowed"),
            RoadEdge("w:1:2:f","c","d",14,30,"allowed"),
            RoadEdge("w:2:0:f","b","e",23,25,"allowed"),
            RoadEdge("w:2:1:f","e","f",14,25,"allowed"),
            RoadEdge("w:2:2:f","f","d",27,25,"allowed")]
        self.graph=RoadGraph(self.coords,self.edges)

    def test_navigate_route_position_guidance_and_arrival(self):
        route=shortest_route(self.graph,"a","d")
        self.assertEqual(route.edge_ids,("w:1:0:f","w:1:1:f","w:1:2:f"))
        path=[self.coords[x] for x in ("a","b","c","d")]
        self.assertEqual(check_route_line(self.graph,self.coords,route.edge_ids,path)["status"],"PASS")
        matcher=DirectedRoadMatcher(self.graph,self.coords)
        gps=GPSFix(1000,53,-1.9999,2,9,90)
        self.assertEqual(matcher.match(gps).status,"MATCHED")
        self.assertEqual(instruction_phase(distance_m=60,speed_mps=14,
            reliable_fix=True,on_correct_route=True,maneuver_verified=True,
            observation_age_ms=150),"APPROACH")
        arrival=ArrivalController()
        token=arrival.begin(self.coords["d"],route_length_m=route.length_m,now_ms=0)
        first=arrival.observe(context_revision=token,timestamp_ms=10000,now_ms=10000,
            position=self.coords["d"],accuracy_m=3,reliable=True,
            on_route=True,remaining_m=0)
        second=arrival.observe(context_revision=token,timestamp_ms=12000,now_ms=12000,
            position=self.coords["d"],accuracy_m=3,reliable=True,
            on_route=True,remaining_m=0)
        self.assertEqual((first,second),("CANDIDATE","ARRIVED"))

    def test_offroute_requires_evidence_then_installs_replan(self):
        controller=ReroutingController()
        controller.begin(shortest_route(self.graph,"a","d"),now_ms=0)
        self.assertIsNone(controller.observe(timestamp_ms=1000,now_ms=1000,
            reliable=True,on_route=False))
        request=controller.observe(timestamp_ms=3000,now_ms=3000,
            reliable=True,on_route=False)
        self.assertIsNotNone(request)
        replacement=shortest_route(self.graph,"e","d")
        self.assertEqual(replacement.edge_ids,("w:2:1:f","w:2:2:f"))
        self.assertTrue(controller.complete(request,replacement,now_ms=4000))
        self.assertEqual(controller.installed_route.edge_ids,replacement.edge_ids)

    def test_turn_restriction_alters_full_route(self):
        graph=RoadGraph(self.coords,self.edges,
            [("w:1:0:f","w:1:1:f")])
        route=shortest_route(graph,"a","d")
        self.assertEqual(route.edge_ids,
            ("w:1:0:f","w:2:0:f","w:2:1:f","w:2:2:f"))
