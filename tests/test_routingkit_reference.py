"""RoutingKit adapter restrictions and evidence contract independent of executable."""
import unittest
from benchmarks.routingkit_reference import compile_query,legal,weighted_cost
from benchmarks.whole_drive import prepared

class RoutingKitAdapterTests(unittest.TestCase):
    def test_restrictions_and_only_turns(self):
        self.assertFalse(legal(('a','b'),'c',(('no',('a','b','c')),)))
        self.assertTrue(legal(('a','b'),'d',(('no',('a','b','c')),)))
        self.assertFalse(legal(('a','b'),'d',(('only',('a','b','c')),)))
        self.assertTrue(legal(('a','b'),'c',(('only',('a','b','c')),)))

    def test_graph_generated_with_explicit_banned_via_way(self):
        p=prepared()
        n,source,sink,arcs,labels=compile_query(p,'osm:20','osm:24')
        self.assertGreater(n,2)
        self.assertGreater(len(arcs),3)
        self.assertEqual(len(labels),len(arcs))
        self.assertNotIn(('w:30:0:f','w:31:0:f','w:31:1:f','w:32:0:f'),[
            tuple(x for x in labels if x is not None)])

    def test_positive_weights_and_invalid_access_absent(self):
        p=prepared()
        for road in p.source_edges.values():
            self.assertGreater(weighted_cost(road),0)
        n,s,t,arcs,labels=compile_query(p,'osm:4','osm:1')
        self.assertFalse(any(i==t for _,i,_ in arcs))
if __name__=='__main__':unittest.main()
