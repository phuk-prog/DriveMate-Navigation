import math
import random
import unittest
from navigation_core.core import Edge, Rule, Vehicle, Graph, Router
from navigation_core.validation.oracle import oracle, validate_route


CAR = Vehicle(height=1.8,weight=2.0)
MODES = ("dijkstra", "astar", "alt")


def graph(edges, rules=(), turns=(), nodes=None):
    if nodes is None:
        ids = sorted({n for e in edges for n in (e.u, e.v)})
        nodes = tuple((n, float(n), 0.0) for n in ids)
    return Graph(tuple(nodes), tuple(edges), tuple(rules), tuple(turns))


class RoutingTests(unittest.TestCase):
    def check(self, g, start, end, cost, expected=None, inbound=(), vehicle=CAR):
        router = Router(g, (g.nodes[0][0], g.nodes[-1][0]))
        self.assertEqual(oracle(g, start, end, vehicle, inbound), cost)
        for mode in MODES:
            result = router.route(start, end, vehicle, mode, inbound)
            if math.isinf(cost):
                self.assertIsNone(result)
            else:
                self.assertEqual(result.cost, cost, mode)
                validate_route(g, start, end, vehicle, inbound, result)
                if expected is not None:
                    self.assertEqual(result.edges, expected)

    def test_multi_edge_no_and_inbound_reroute(self):
        g = graph([Edge(1,0,1,1),Edge(2,1,2,1),Edge(3,2,3,1),
                   Edge(4,0,2,5),Edge(5,2,4,2),Edge(6,4,3,2)],
                  [Rule("no",(1,2,3))])
        self.check(g,0,3,6,(1,2,5,6))
        self.check(g,2,3,4,(5,6),inbound=(1,2))
        self.check(g,2,3,1,(3,),inbound=(4,))

    def test_multi_edge_only_requires_each_continuation(self):
        g=graph([Edge(1,0,1,1),Edge(2,1,2,1),Edge(3,2,3,1),
                 Edge(4,1,3,0),Edge(5,2,3,0)],[Rule("only",(1,2,3))])
        self.check(g,0,3,3,(1,2,3))
        self.check(g,1,3,0,(4,))
        self.check(g,1,3,2,(2,3),inbound=(1,))

    def test_overlapping_rules_and_vehicle_specific_exception(self):
        g=graph([Edge(1,0,1,1),Edge(2,1,2,1),Edge(3,2,3,1)],
                [Rule("only",(1,2,3)),Rule("no",(2,3),frozenset({"car"}))])
        self.check(g,0,3,math.inf)
        self.check(g,0,3,3,(1,2,3),vehicle=Vehicle("bus"))

    def test_oneway_parallel_roads_and_access(self):
        g=graph([Edge(1,0,1,1,vehicles=frozenset({"bus"})),
                 Edge(2,0,1,4),Edge(3,1,2,1,max_height=2.0,max_weight=3.0),
                 Edge(4,0,2,8)])
        self.check(g,0,2,5,(2,3))
        self.check(g,0,2,8,(4,),vehicle=Vehicle(height=2.1))
        self.check(g,0,2,8,(4,),vehicle=Vehicle(weight=3.1))
        self.check(g,0,2,8,(4,),vehicle=Vehicle())
        self.check(g,0,2,5,(2,3),vehicle=Vehicle(height=2.0,weight=3.0))
        self.check(g,2,0,math.inf)

    def test_turn_costs_and_zero_cost_cycle(self):
        g=graph([Edge(1,0,1,0),Edge(2,1,0,0),Edge(3,1,2,1),
                 Edge(4,0,2,3)],turns=[(1,3,4)])
        self.check(g,0,2,3,(4,))
        self.check(g,0,0,0,())

    def test_disconnected_directed_landmark(self):
        g=graph([Edge(1,0,1,1),Edge(2,1,2,1)],
                nodes=((0,0.,0.),(1,1.,0.),(2,2.,0.),(3,5.,5.)))
        self.check(g,0,2,2,(1,2))
        self.check(g,3,2,math.inf)

    def test_input_validation(self):
        for bad in (-1,math.inf,math.nan):
            with self.assertRaises(ValueError):
                graph([Edge(1,0,1,bad)])
        for bad in (-1,math.inf,math.nan):
            with self.assertRaises(ValueError):
                Vehicle(height=bad)
        with self.assertRaises(ValueError):
            graph([Edge(1,0,1,1),Edge(1,1,2,1)])
        with self.assertRaises(ValueError):
            graph([Edge(1,0,1,1)],[Rule("no",(1,99))])
        with self.assertRaises(ValueError):
            graph([Edge(1,0,1,1),Edge(2,2,3,1)],[Rule("no",(1,2))])
        with self.assertRaises(ValueError):
            graph([Edge(1,0,1,1)],turns=[(1,1,-1)])
        with self.assertRaises(ValueError):
            graph([Edge(1,0,1,1)],nodes=((0,math.nan,0),(1,0,0)))
        r=Router(graph([Edge(1,0,1,1),Edge(2,0,2,1)]))
        for history in ((99,),(1,2)):
            with self.assertRaises(ValueError):
                r.route(1,0,inbound=history)
        with self.assertRaises(ValueError):
            r.route(0,99)
        with self.assertRaises(ValueError):
            r.route(0,1,mode="unknown")

    def test_snapshot_immutable_and_ties_deterministic(self):
        edges=[Edge(1,0,1,1),Edge(2,0,2,1),Edge(3,1,3,1),Edge(4,2,3,1)]
        g=graph(edges)
        r=Router(g)
        edges.clear()
        with self.assertRaises((AttributeError,TypeError)):
            g.edges += (Edge(5,0,3,0),)
        self.assertEqual(r.route(0,3).edges,r.route(0,3).edges)

    def test_extreme_coordinates_and_invalid_cost_units(self):
        g=graph([Edge(1,0,1,1)],nodes=((0,0.,0.),(1,1e-320,0.)))
        self.check(g,0,1,1,(1,))
        for bad in (0.5,2**1000):
            with self.assertRaises(ValueError):
                graph([Edge(1,0,1,bad)])

    def test_new_snapshot_rebuilds_landmark_costs(self):
        before=graph([Edge(1,0,1,20),Edge(2,1,2,20),Edge(3,0,2,30)])
        after=graph([Edge(1,0,1,1),Edge(2,1,2,1),Edge(3,0,2,30)])
        self.check(before,0,2,30,(3,))
        self.check(after,0,2,2,(1,2))

    def test_generated_graphs_independent_oracle_and_lower_bounds(self):
        rng=random.Random(20261014)
        for case in range(40):
            edges=[]
            for u in range(5):
                for v in range(5):
                    if u!=v and rng.random()<.38:
                        edges.append(Edge(len(edges),u,v,rng.randint(0,9)))
            rules=[]
            for e in edges:
                nxt=[f for f in edges if f.u==e.v]
                if nxt and rng.random()<.35:
                    f=rng.choice(nxt)
                    nxt2=[h for h in edges if h.u==f.v]
                    seq=(e.id,f.id)
                    if nxt2 and rng.random()<.5:
                        seq+=(rng.choice(nxt2).id,)
                    rules.append(Rule(rng.choice(["no","only"]),seq))
            g=graph(edges,rules,nodes=tuple((n,float(n),float(n%2)) for n in range(5)))
            r=Router(g,(0,4))
            for a in range(5):
                for b in range(5):
                    for hist in [()]+[(e.id,) for e in edges if e.v==a][:1]:
                        expected=oracle(g,a,b,CAR,hist)
                        for mode in MODES:
                            got=r.route(a,b,CAR,mode,hist)
                            self.assertEqual(math.inf if got is None else got.cost,expected,(case,a,b,hist,mode))
                            if got is not None:
                                validate_route(g,a,b,CAR,hist,got)
                        for mode in ("astar","alt"):
                            self.assertLessEqual(r.lower_bound(a,b,mode),expected)


if __name__=="__main__":
    unittest.main()
