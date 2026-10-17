"""Routing candidate research contract; ALL road fixtures here are synthetic.

A generated option is not legal evidence. No claims of field-ready shortest,
fastest, traffic quality, correct lanes, or verified UK maneuver counts.
"""
import unittest

from engine import RoadEdge, RoadGraph, RouteNotFound, shortest_route
from engine.driver_policy import DriverNavigationSettings, RouteOption, choose_preferred_route
from engine.route_alternatives import generate_route_candidates


class RouteAlternativesTests(unittest.TestCase):
    def setUp(self):
        self.edges=[
            RoadEdge("AB","A","B",50,10,"allowed"),
            RoadEdge("BD","B","D",50,10,"allowed"),
            RoadEdge("AC","A","C",150,90,"allowed"),
            RoadEdge("CD","C","D",150,90,"allowed"),
            RoadEdge("AE","A","E",80,30,"allowed"),
            RoadEdge("ED","E","D",80,30,"allowed"),
        ]
        self.graph=RoadGraph(["A","B","C","D","E"],self.edges)
        self.complex={("AC","CD")}

    def generate(self, **kwargs):
        return generate_route_candidates(
            self.graph,"A","D",snapshot_id="synthetic-fixture-v1",
            verified_complex_turns=self.complex,**kwargs)

    def by_mode(self, candidates, mode):
        return next(c for c in candidates if mode in c.generated_by)

    def test_fastest_shortest_and_balanced_generate_distinct_real_paths(self):
        found=self.generate(max_detour_searches=0)
        self.assertEqual(len(found),3)
        self.assertEqual(self.by_mode(found,"fastest").route.edge_ids,("AC","CD"))
        self.assertEqual(self.by_mode(found,"shortest").route.edge_ids,("AB","BD"))
        self.assertEqual(self.by_mode(found,"balanced").route.edge_ids,("AE","ED"))

    def test_preference_objective_agrees_with_path_generation_when_evidence_is_supplied(self):
        generated=self.generate(max_detour_searches=0)
        # Synthetic verified=True models an independent verifier's contract
        # only; this does not establish real UK legal permissions.
        opts=[RouteOption(c.route_id,c.route.estimated_seconds,c.route.length_m,
                          0.95,c.complex_maneuvers,True,True) for c in generated]
        for mode in ("fastest","shortest","balanced"):
            with self.subTest(mode=mode):
                policy=DriverNavigationSettings(route_mode=mode)
                chosen=choose_preferred_route(opts,policy)
                self.assertEqual(chosen.route_id,self.by_mode(generated,mode).route_id)

    def test_never_mark_generated_map_edges_independently_verified(self):
        found=self.generate(max_detour_searches=0)
        opts=[route.as_unverified_option(eta_confidence=0.99) for route in found]
        self.assertTrue(all(not x.independently_verified_legal
                            and not x.evidence_current for x in opts))
        self.assertIsNone(choose_preferred_route(opts,DriverNavigationSettings()))

    def test_disabling_complexity_penalty_changes_balanced_route(self):
        policy=DriverNavigationSettings(avoid_complex_maneuvers=False)
        c=self.generate(settings=policy,max_detour_searches=0)
        self.assertEqual(self.by_mode(c,"balanced").route.edge_ids,("AC","CD"))

    def test_traffic_delay_changes_fastest_not_shortest(self):
        c=self.generate(time_penalties_s={"AC":40.0},max_detour_searches=0)
        self.assertEqual(self.by_mode(c,"fastest").route.edge_ids,("AE","ED"))
        self.assertEqual(self.by_mode(c,"shortest").route.edge_ids,("AB","BD"))
        self.assertAlmostEqual(self.by_mode(c,"fastest").route.estimated_seconds,19.2)

    def test_prohibited_turns_cannot_be_overridden_by_any_mode(self):
        g=RoadGraph(["A","B","C","D","E"],self.edges,
                    prohibited_turns={("AC","CD"),("AB","BD")})
        for mode in ("fastest","shortest","balanced"):
            routes=generate_route_candidates(
                g,"A","D",snapshot_id="synthetic",
                settings=DriverNavigationSettings(route_mode=mode))
            self.assertTrue(routes)
            for candidate in routes:
                self.assertEqual(candidate.route.edge_ids,("AE","ED"))
                self.assertNotIn(("AC","CD"),list(zip(candidate.route.edge_ids,
                                                     candidate.route.edge_ids[1:])))

    def test_blocked_edges_never_selected(self):
        routes=self.generate(blocked_edges=("AC","AE"))
        self.assertTrue(routes)
        for candidate in routes:
            self.assertEqual(candidate.route.edge_ids,("AB","BD"))
            self.assertFalse({"AC","AE"} & set(candidate.route.edge_ids))

    def test_unknown_and_prohibited_access_not_used_even_if_shorter(self):
        edges=self.edges+[RoadEdge("AD-direct","A","D",1,90,"unknown")]
        g=RoadGraph(["A","B","C","D","E"],edges)
        options=generate_route_candidates(g,"A","D",snapshot_id="test")
        self.assertTrue(all("AD-direct" not in o.route.edge_ids for o in options))

    def test_reroute_preserves_incoming_turn_context(self):
        # B->D is prohibited when arriving from A, but the genuine mapped
        # detour B->E->D remains allowed. Never claim a detour if none exists.
        g=RoadGraph(["A","B","C","D","E"],
                    self.edges+[RoadEdge("BE","B","E",45,30,"allowed")],
                    prohibited_turns={("AB","BD")})
        options=generate_route_candidates(g,"B","D",snapshot_id="test",
                                          incoming_edge_id="AB")
        self.assertTrue(options)
        self.assertTrue(all(o.route.edge_ids==("BE","ED") for o in options))
        with self.assertRaises(RouteNotFound):
            generate_route_candidates(g,"B","D",snapshot_id="test",
                                      incoming_edge_id="AB",blocked_edges=("BE",))

    def test_unreachable_keeps_actual_no_route_error(self):
        with self.assertRaises(RouteNotFound):
            self.generate(blocked_edges=("AB","AC","AE"))

    def test_candidate_ids_deterministic_and_scoped_to_snapshot(self):
        first=self.generate()
        again=self.generate()
        self.assertEqual(first,again)
        next_snapshot=generate_route_candidates(self.graph,"A","D",
            snapshot_id="synthetic-fixture-v2",verified_complex_turns=self.complex)
        self.assertEqual([v.route.edge_ids for v in first],
                         [v.route.edge_ids for v in next_snapshot])
        self.assertNotEqual([v.route_id for v in first],
                            [v.route_id for v in next_snapshot])

    def test_no_double_counting_same_route_and_bounded_detour_search(self):
        only=RoadGraph(["A","B","D"],[
            RoadEdge("AB","A","B",10,20,"allowed"),
            RoadEdge("BD","B","D",10,20,"allowed")])
        result=generate_route_candidates(only,"A","D",snapshot_id="test",
                                         max_detour_searches=32)
        self.assertEqual(len(result),1)
        self.assertEqual(set(result[0].generated_by),
                         {"fastest","shortest","balanced"})
        found=self.generate(max_candidates=3,max_detour_searches=20)
        self.assertEqual(len(found),3)

    def test_zero_distance_returns_stay_put(self):
        routes=generate_route_candidates(self.graph,"A","A",snapshot_id="test")
        self.assertEqual(len(routes),1)
        self.assertEqual(routes[0].route.edge_ids,())
        self.assertEqual(routes[0].route.estimated_seconds,0)

    def test_reject_invalid_profiles_and_unsafe_inputs(self):
        cases=[
            {"snapshot_id":""},
            {"blocked_edges":["nonexistent"]},
            {"time_penalties_s":{"bad":1}},
            {"time_penalties_s":{"AC":-1}},
            {"time_penalties_s":{"AC":float("nan")}},
            {"time_penalties_s":{"AC":True}},
            {"verified_complex_turns":[("AB","missing")]},
            {"verified_complex_turns":[("BD","AC")]},
            {"incoming_edge_id":"AC"},
            {"max_candidates":2},
            {"max_detour_searches":100},
        ]
        for changes in cases:
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                args={"snapshot_id":"fixture"}
                args.update(changes)
                generate_route_candidates(self.graph,"A","D",**args)

    def test_fastest_cost_matches_existing_time_dijkstra(self):
        fast=shortest_route(self.graph,"A","D")
        selected=self.by_mode(self.generate(),"fastest")
        self.assertEqual(selected.route.edge_ids,fast.edge_ids)
        self.assertAlmostEqual(selected.route.estimated_seconds,fast.estimated_seconds)

    def test_detour_candidates_have_unique_paths_and_protect_turn_rules(self):
        edges=self.edges+[
            RoadEdge("AF","A","F",100,25,"allowed"),
            RoadEdge("FD","F","D",100,25,"allowed")]
        graph=RoadGraph(["A","B","C","D","E","F"],edges)
        candidates=generate_route_candidates(graph,"A","D",snapshot_id="test",
                                             verified_complex_turns=self.complex,
                                             max_candidates=6)
        self.assertEqual(len(candidates),4)
        paths=[c.route.edge_ids for c in candidates]
        self.assertEqual(len(paths),len(set(paths)))
        self.assertIn(("AF","FD"),paths)


if __name__ == "__main__":
    unittest.main()
