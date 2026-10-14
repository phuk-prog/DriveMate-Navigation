import math
import random
import unittest
from navigation_core.core import Edge, Rule, Vehicle, Graph, Router
from navigation_core.endpoints import Position,prepare
from navigation_core.native_adapter import run
from navigation_core.validation.oracle import oracle,validate_route
from navigation_core.validation.endpoint_oracle import endpoint_cost

V=Vehicle(height=1.8,weight=2)


class EndpointTests(unittest.TestCase):
    def check(self,g,origin,target,expected,inbound=(),vehicle=V):
        self.assertEqual(endpoint_cost(g,origin,target,vehicle,inbound),expected)
        prepared=prepare(g,origin,target,inbound,vehicle)
        if prepared is None:
            self.assertTrue(math.isinf(expected))
            return
        overlay,a,b,h,aliases=prepared
        self.assertEqual(oracle(overlay,a,b,vehicle,h),expected)
        r=Router(overlay)
        queries=[]
        for mode in ("dijkstra","astar","alt"):
            got=r.route(a,b,vehicle,mode,h)
            self.assertEqual(math.inf if got is None else got.cost,expected)
            if got:
                validate_route(overlay,a,b,vehicle,h,got)
            queries.append((mode,a,b,vehicle,h))
        _,native=run(overlay,queries)
        for got,_ in native:
            self.assertEqual(math.inf if got is None else got.cost,expected)
            if got:
                validate_route(overlay,a,b,vehicle,h,got)

    def test_same_road_forward_zero_and_no_reverse(self):
        g=Graph(((0,0.,0.),(1,10.,0.)),(Edge(1,0,1,100),))
        self.check(g,Position(1,200000),Position(1,800000),60)
        self.check(g,Position(1,500000),Position(1,500000),0)
        self.check(g,Position(1,800000),Position(1,200000),math.inf)
        self.check(g,Position(1,0),Position(1,1000000),100)

    def test_backward_destination_requires_legal_loop(self):
        g=Graph(((0,0.,0.),(1,10.,0.),(2,10.,10.)),
                (Edge(1,0,1,100),Edge(2,1,2,20),Edge(3,2,0,30)))
        self.check(g,Position(1,800000),Position(1,200000),90)

    def test_turn_cost_and_access_apply_at_entry(self):
        g=Graph(((0,0.,0.),(1,10.,0.),(2,20.,0.)),
                (Edge(1,0,1,100),Edge(2,1,2,200,max_height=2)),(),((1,2,7),))
        self.check(g,Position(1,500000),Position(2,250000),107)
        self.check(g,Position(1,500000),Position(2,0),57)
        self.check(g,Position(1,500000),Position(2,250000),math.inf,vehicle=Vehicle())

    def test_restriction_blocks_partial_target_at_all_offsets(self):
        g=Graph(((0,0.,0.),(1,10.,0.),(2,20.,0.)),
                (Edge(1,0,1,100),Edge(2,1,2,100)),(Rule("no",(1,2)),))
        for q in (0,1,500000,1000000):
            self.check(g,Position(1,500000),Position(2,q),math.inf)

    def test_multi_road_restriction_survives_partial_inbound(self):
        g=Graph(tuple((n,float(n),0.) for n in range(4)),
                (Edge(1,0,1,100),Edge(2,1,2,100),Edge(3,2,3,100)),
                (Rule("no",(1,2,3)),))
        self.check(g,Position(2,500000),Position(3,500000),math.inf,inbound=(1,))
        self.check(g,Position(2,500000),Position(3,500000),100)

    def test_only_rule_blocks_wrong_exit_after_partial_origin(self):
        g=Graph(tuple((n,float(n),0.) for n in range(4)),
                (Edge(1,0,1,100),Edge(2,1,2,100),Edge(3,1,3,100)),
                (Rule("only",(1,2)),))
        self.check(g,Position(1,500000),Position(3,500000),math.inf)
        self.check(g,Position(1,500000),Position(2,500000),100)

    def test_integer_partition_conserves_cost(self):
        g=Graph(((0,0.,0.),(1,1.,0.)),(Edge(1,0,1,7),))
        self.check(g,Position(1,100000),Position(1,900000),6)
        overlay,*_=prepare(g,Position(1,100000),Position(1,900000),(),V)
        self.assertEqual(sum(e.cost for e in overlay.edges),7)

    def test_invalid_positions_and_history(self):
        for q in (-1,1000001,0.5,True):
            with self.assertRaises(ValueError):
                Position(1,q)
        g=Graph(((0,0.,0.),(1,1.,0.)),(Edge(1,0,1,7),))
        with self.assertRaises(ValueError):
            prepare(g,Position(99,1),Position(1,2),(),V)
        with self.assertRaises(ValueError):
            prepare(g,Position(1,1),Position(1,2),(1,),V)

    def test_generated_endpoints_against_original_road_oracle(self):
        rng=random.Random(142026)
        count=0
        for _ in range(24):
            nodes=tuple((n,float(n),float(n%2)) for n in range(5))
            edges=tuple(Edge(i,a,b,rng.randrange(20)) for i,(a,b) in
                enumerate(((a,b) for a in range(5) for b in range(5) if a!=b and rng.random()<.45),1))
            if not edges: continue
            rules=[]
            for _ in range(3):
                first=rng.choice(edges); seq=[first.id]; node=first.v
                for _ in range(rng.randrange(1,4)):
                    outgoing=[e for e in edges if e.u==node]
                    if not outgoing: break
                    edge=rng.choice(outgoing); seq.append(edge.id); node=edge.v
                if len(seq)>1: rules.append(Rule(rng.choice(('no','only')),tuple(seq)))
            turns=tuple((a.id,b.id,rng.randrange(5)) for a in edges for b in edges if a.v==b.u and rng.random()<.1)
            g=Graph(nodes,edges,tuple(rules),turns)
            for _ in range(8):
                origin=Position(rng.choice(edges).id,rng.choice((0,1,333333,500000,999999,1000000)))
                target=Position(rng.choice(edges).id,rng.choice((0,1,333333,500000,999999,1000000)))
                self.check(g,origin,target,endpoint_cost(g,origin,target,V))
                count+=1
        self.assertEqual(count,192)


if __name__=="__main__":
    unittest.main()
