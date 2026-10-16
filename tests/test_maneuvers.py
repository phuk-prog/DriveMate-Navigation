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
