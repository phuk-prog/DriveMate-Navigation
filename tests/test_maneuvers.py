"""Synthetic maneuver contracts; no physical-road validation."""
import unittest
from engine.maneuvers import principal_maneuvers
from benchmarks.junction_trial import load_map, cases, run_dmn
from engine import shortest_route

class ManeuverTests(unittest.TestCase):
    def test_frozen_cases(self):
        self.assertEqual([r['outcome'] for r in run_dmn()['cases']], ['PASS']*5)

    def test_partial_ring_withholds_number(self):
        data, ring=load_map()
        r=shortest_route(data.graph,'osm:12','osm:18')
        with self.assertRaisesRegex(ValueError,'partial roundabout'):
            principal_maneuvers(data.graph,data.coordinates,r.edge_ids,ring)

    def test_destination_on_ring_withholds_number(self):
        data, ring=load_map()
        r=shortest_route(data.graph,'osm:10','osm:14')
        with self.assertRaisesRegex(ValueError,'partial roundabout'):
            principal_maneuvers(data.graph,data.coordinates,r.edge_ids,ring)

    def test_disconnected_route_rejected(self):
        data, ring=load_map()
        with self.assertRaises(ValueError):
            principal_maneuvers(data.graph,data.coordinates,('w:101:0:f','w:112:0:f'),ring)

    def test_prohibited_spur_rejected(self):
        data, ring=load_map()
        r=shortest_route(data.graph,'osm:10','osm:13')
        with self.assertRaises(ValueError):
            principal_maneuvers(data.graph,data.coordinates,r.edge_ids+('w:116:0:f',),ring)

    def test_turn_restriction_excludes_first_spoke(self):
        # Additional analytical control: removing first legal departure makes
        # the geometrically second exit the first accessible exit. No road claim.
        from engine.routing import RoadGraph
        data, ring=load_map()
        graph=RoadGraph(data.graph.vertices,data.graph.edges.values(), [('w:111:0:f','w:112:0:f')])
        r=shortest_route(graph,'osm:10','osm:17')
        self.assertEqual(principal_maneuvers(graph,data.coordinates,r.edge_ids,ring),[{'kind':'roundabout','exit':1}])

    def test_unknown_spoke_does_not_count(self):
        from engine.routing import RoadGraph
        from dataclasses import replace
        data,ring=load_map()
        graph=RoadGraph(data.graph.vertices,[replace(e,access='unknown') if e.edge_id=='w:112:0:f' else e for e in data.graph.edges.values()])
        r=shortest_route(graph,'osm:10','osm:18')
        self.assertEqual(principal_maneuvers(graph,data.coordinates,r.edge_ids,ring),[{'kind':'roundabout','exit':2}])

    def test_unknown_metadata_rejected(self):
        data,ring=load_map()
        with self.assertRaises(ValueError):
            principal_maneuvers(data.graph,data.coordinates,(),ring|{'missing'})

    def test_reversed_ring_first_exit(self):
        # Analytical control for opposite circulation, not UK map evidence.
        from engine.routing import RoadGraph
        from dataclasses import replace
        data,ring=load_map()
        graph=RoadGraph(data.graph.vertices,[replace(e,source=e.target,target=e.source) if e.edge_id in ring else e for e in data.graph.edges.values()])
        r=shortest_route(graph,'osm:10','osm:18')
        self.assertEqual(principal_maneuvers(graph,data.coordinates,r.edge_ids,ring),[{'kind':'roundabout','exit':1}])

    def test_repeated_ring_junction_withholds(self):
        data,ring=load_map()
        ids=('w:110:0:f',)+tuple(f'w:111:{i}:f' for i in range(5))+('w:111:0:f','w:112:0:f')
        with self.assertRaisesRegex(ValueError,'Repeated roundabout'):
            principal_maneuvers(data.graph,data.coordinates,ids,ring)
