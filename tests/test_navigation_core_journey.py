import unittest
from unittest.mock import patch
from navigation_core.core import Edge, Graph, Rule, Vehicle
from navigation_core.endpoints import Position
from navigation_core.journey import Journey
from navigation_core.native_adapter import run

V=Vehicle(height=1.8,weight=2)

def network(rules=()):
    return Graph(tuple((n,float(n),0.) for n in range(6)),
        (Edge(1,0,1,10),Edge(2,1,2,10),Edge(3,2,3,10),
         Edge(4,1,4,20),Edge(5,4,2,20),Edge(6,3,5,10)),rules)

class JourneyTests(unittest.TestCase):
    def test_start_progress_and_arrival(self):
        j=Journey(network(),V,Position(3,800000))
        first=j.start(Position(1,200000),10)
        self.assertEqual(first.roads,(1,2,3));self.assertEqual(first.cost,26)
        moved=j.observe(Position(1,600000),11)
        self.assertEqual(moved.cost,22);self.assertEqual(moved.status,'navigating')
        self.assertEqual(j.observe(Position(2,200000),12).status,'navigating')
        arrived=j.observe(Position(3,800000),13)
        self.assertEqual(arrived.status,'arrived');self.assertEqual(arrived.cost,0)

    def test_wrong_turn_recalculates(self):
        j=Journey(network(),V,Position(3,800000))
        j.start(Position(1,200000),10)
        r=j.observe(Position(4,200000),11)
        self.assertTrue(r.wrong_turn);self.assertEqual(r.roads,(4,5,3))
        self.assertEqual(r.status,'navigating')

    def test_inbound_history_blocks_multi_road_exit(self):
        g=network((Rule('no',(1,2,3)),))
        j=Journey(g,V,Position(3,800000))
        self.assertEqual(j.start(Position(1,200000),10).roads,(1,4,5,3))
        r=j.observe(Position(2,500000),11)
        self.assertTrue(r.wrong_turn);self.assertEqual(r.status,'no_route')
        self.assertEqual(r.roads,());self.assertIsNone(r.cost)

    def test_actual_illegal_turn_history_is_not_invented_permission(self):
        g=network((Rule('no',(1,2)),Rule('no',(1,2,3))))
        j=Journey(g,V,Position(3,800000));j.start(Position(1,200000),1)
        self.assertEqual(j.observe(Position(2,200000),2).status,'no_route')

    def test_stale_backward_disconnected_and_bad_timestamp_are_atomic(self):
        j=Journey(network(),V,Position(3,800000));r=j.start(Position(1,500000),10)
        for p,t in [(Position(1,600000),10),(Position(1,600000),9),
                    (Position(1,200000),11),(Position(3,200000),11),
                    (Position(1,600000),float('nan')),(Position(1,600000),True)]:
            with self.assertRaises(ValueError):j.observe(p,t)
            self.assertEqual(j.snapshot,r)
        self.assertEqual(j.observe(Position(2,200000),11).status,'navigating')

    def test_snapshot_is_immutable_and_arrival_does_not_restart(self):
        j=Journey(network(),V,Position(1,400000));s=j.start(Position(1,200000),1)
        with self.assertRaises(Exception):s.cost=9
        self.assertEqual(j.observe(Position(1,600000),2).status,'arrived')
        self.assertEqual(j.observe(Position(2,200000),3).status,'arrived')

    def test_start_past_destination_requires_loop(self):
        j=Journey(network(),V,Position(1,200000))
        self.assertEqual(j.start(Position(1,800000),1).status,'no_route')

    def test_access_failure_has_no_guidance(self):
        g=Graph(((0,0.,0.),(1,1.,0.)),(Edge(1,0,1,10,max_height=2),))
        j=Journey(g,Vehicle(),Position(1,800000))
        self.assertEqual(j.start(Position(1,200000),1).status,'no_route')

    def test_missing_current_road_and_double_start(self):
        j=Journey(network(),V,Position(3,800000))
        with self.assertRaises(ValueError):j.observe(Position(1,200000),1)
        with self.assertRaises(ValueError):j.start(Position(99,200000),1)
        j.start(Position(1,200000),1)
        with self.assertRaises(ValueError):j.start(Position(1,200000),2)

    def test_same_road_progress_reuses_route_without_backend_calls(self):
        with patch('navigation_core.journey.run',wraps=run) as backend:
            j=Journey(network(),V,Position(3,800000));j.start(Position(1,200000),1)
            for q,t in ((300000,2),(600000,3),(1000000,4)):
                s=j.observe(Position(1,q),t)
                self.assertEqual(s.cost,28-q//100000)
            self.assertEqual(backend.call_count,1)
            self.assertEqual(j.observe(Position(2,200000),5).cost,16)
            self.assertEqual(backend.call_count,2)

    def test_zero_cost_current_road_is_present_in_guidance_sequence(self):
        g=Graph(((0,0.,0.),(1,1.,0.),(2,2.,0.)),(Edge(1,0,1,0),Edge(2,1,2,10)))
        j=Journey(g,V,Position(2,500000));r=j.start(Position(1,200000),1)
        self.assertEqual(r.roads,(1,2))
        self.assertEqual(j.observe(Position(2,200000),2).cost,3)

if __name__=='__main__':unittest.main()
