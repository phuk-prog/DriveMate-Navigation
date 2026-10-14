import unittest
from unittest.mock import patch
from pathlib import Path
from engine.routing import RoadGraph, RoadEdge, shortest_route, RouteNotFound
from engine.reconciled import prepare_navigation, Restriction
from map_data.osm_xml import import_osm_xml, Provenance
from navigation_core.core import Vehicle
from navigation_core.core import Router

class ReconciliationTests(unittest.TestCase):
    def graph(self):
        return RoadGraph(['a','b','c','d','e'],[
            RoadEdge('ab','a','b',10,36,'allowed'),RoadEdge('bc','b','c',10,36,'allowed'),
            RoadEdge('cd','c','d',10,36,'allowed'),RoadEdge('be','b','e',20,36,'allowed'),
            RoadEdge('ec','e','c',20,36,'allowed')])

    def test_importer_routes_connect_to_both_cores(self):
        raw=Path('benchmarks/fixtures/synthetic-osm-junction.xml').read_bytes()
        imported=import_osm_xml(raw,provenance=Provenance('synthetic','fabricated-v1','synthetic','OpenStreetMap contributors'))
        prepared=prepare_navigation(imported.graph,imported.coordinates)
        checked=0
        for a in sorted(imported.graph.vertices):
            for b in sorted(imported.graph.vertices):
                try:old=shortest_route(imported.graph,a,b)
                except RouteNotFound:
                    for backend in ('research','portable'):
                        with self.assertRaises(RouteNotFound):prepared.route(a,b,backend=backend)
                    continue
                for backend in ('research','portable'):
                    route=prepared.route(a,b,backend=backend)
                    self.assertAlmostEqual(route.estimated_seconds,old.estimated_seconds,delta=max(1,len(old.edge_ids))*1e-6)
                checked+=1
        self.assertGreater(checked,0)

    def test_multi_road_restriction_and_reroute_history(self):
        p=prepare_navigation(self.graph(),restrictions=(Restriction('no',('ab','bc','cd')),))
        for backend in ('research','portable'):
            self.assertEqual(p.route('a','d',backend=backend).edge_ids,('ab','be','ec','cd'))
            with self.assertRaises(RouteNotFound):p.route('c','d',inbound=('ab','bc'),backend=backend)
            self.assertEqual(p.route('c','d',inbound=('be','ec'),backend=backend).edge_ids,('cd',))

    def test_unknown_access_is_routable_and_marked_unverified(self):
        g=RoadGraph(['a','b'],[RoadEdge('ab','a','b',10,36,'unknown')]);p=prepare_navigation(g)
        for backend in ('research','portable'):
            r=p.route('a','b',backend=backend)
            self.assertEqual(r.edge_ids,('ab',));self.assertEqual(r.unverified_access_edges,('ab',))
        self.assertEqual(shortest_route(g,'a','b').unverified_access_edges,('ab',))
        from engine.astar import astar_route
        self.assertEqual(astar_route(g,'a','b').route.unverified_access_edges,('ab',))
        j=p.journey('ab',800000)
        s=j.start(p.position('ab',200000),1)
        self.assertEqual(s.status,'navigating');self.assertEqual(s.unverified_access_edges,('ab',))
        self.assertEqual(j.observe(p.position('ab',400000),2).unverified_access_edges,('ab',))

    def test_known_access_ban_is_still_enforced(self):
        g=RoadGraph(['a','b'],[RoadEdge('ab','a','b',10,36,'prohibited')]);p=prepare_navigation(g)
        for backend in ('research','portable'):
            with self.assertRaises(RouteNotFound):p.route('a','b',backend=backend)
        with self.assertRaises(RouteNotFound):shortest_route(g,'a','b')

    def test_journey_uses_imported_edge_names_and_wrong_turn(self):
        p=prepare_navigation(self.graph());j=p.journey('cd',800000,Vehicle())
        initial=j.start(p.position('ab',200000),1)
        self.assertEqual(p.road_names(initial.roads),('ab','bc','cd'))
        wrong=j.observe(p.position('be',200000),2)
        self.assertTrue(wrong.wrong_turn);self.assertEqual(p.road_names(wrong.roads),('be','ec','cd'))

    def test_cost_units_and_immutable_mapping(self):
        p=prepare_navigation(self.graph())
        self.assertEqual(p.route('a','d').estimated_seconds,3)
        self.assertEqual(p.cost_unit,'microseconds, per-road ceiling')
        with self.assertRaises(TypeError):p.edge_ids['ab']=99

    def test_invalid_mapping_history_and_dimensions_rejected(self):
        p=prepare_navigation(self.graph())
        with self.assertRaises(ValueError):p.route('a','d',inbound=('bc',))
        with self.assertRaises(ValueError):p.position('missing',1)
        with self.assertRaises(ValueError):prepare_navigation(self.graph(),restrictions=(Restriction('no',('missing','cd')),))

    def test_preparation_reused_across_research_routes(self):
        with patch('engine.reconciled.Router',wraps=Router) as factory:
            p=prepare_navigation(self.graph())
            for _ in range(3):p.route('a','d')
            self.assertEqual(factory.call_count,1)

if __name__=='__main__':unittest.main()
