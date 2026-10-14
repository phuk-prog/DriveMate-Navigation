import math
import os
import random
import subprocess
import unittest
from pathlib import Path
from navigation_core.core import Edge, Rule, Vehicle, Graph
from navigation_core.holdout import fixture,cases
from navigation_core.native_adapter import run,encode
from navigation_core.validation.oracle import oracle,validate_route

BIN=Path(os.environ.get("DM_NATIVE_BIN",str(Path(__file__).resolve().parents[1]/"navigation_core/native/router")))


class NativeTests(unittest.TestCase):
    def compare(self,g,journeys,landmarks=()):
        queries=[(mode,a,b,v,h) for a,b,h,v in journeys for mode in ("dijkstra","astar","alt")]
        _,results=run(g,queries,landmarks,BIN)
        for (mode,a,b,v,h),(r,_) in zip(queries,results):
            expected=oracle(g,a,b,v,h)
            self.assertEqual(math.inf if r is None else r.cost,expected,(mode,a,b,h))
            if r:
                validate_route(g,a,b,v,h,r)

    def test_holdout_oracle_parity(self):
        for seed in (51211,51317,51421):
            g=fixture(7,seed,split=seed==51421)
            self.compare(g,cases(g,seed+1,18),(0,6,42,48))

    def test_overlaps_access_parallel_edges_and_history(self):
        g=Graph(((0,0.,0.),(1,1.,0.),(2,2.,0.),(3,3.,0.),(4,4.,0.)),
                (Edge(-1,0,1,1),Edge(2,1,2,1),Edge(3,2,3,1,max_height=2),
                 Edge(4,0,2,6),Edge(5,2,4,2),Edge(6,4,3,2),
                 Edge(7,0,1,0,vehicles=frozenset({"bus"}))),
                (Rule("only",(-1,2,3)),Rule("no",(-1,2,3),frozenset({"car"}))),
                ((7,2,3),))
        self.compare(g,[(0,3,(),Vehicle(height=1.8)),
                        (0,3,(),Vehicle("bus",height=1.8)),
                        (2,3,(-1,2),Vehicle(height=1.8)),
                        (2,3,(4,),Vehicle()),
                        (2,3,(4,),Vehicle(height=2)),
                        (3,0,(),Vehicle()),(0,0,(),Vehicle())],(0,3))

    def test_zero_cycle_and_extreme_geometry(self):
        g=Graph(((0,0.,0.),(1,1e-320,0.),(2,2.,0.),(3,5.,0.)),
                (Edge(0,0,1,0),Edge(1,1,0,0),Edge(2,1,2,3),Edge(3,0,2,4)),
                (),((0,2,4),))
        self.compare(g,[(0,2,(),Vehicle()),(0,0,(),Vehicle()),(3,2,(),Vehicle())],(0,3))

    def test_generated_graphs_all_pairs(self):
        rng=random.Random(51913)
        for _ in range(20):
            edges=[]
            for a in range(5):
                for b in range(5):
                    if a!=b and rng.random()<.4:
                        edges.append(Edge(len(edges),a,b,rng.randrange(8)))
            rules=[]
            for e in edges[::3]:
                nxt=[f for f in edges if f.u==e.v]
                if nxt:
                    f=rng.choice(nxt)
                    third=[h for h in edges if h.u==f.v]
                    ids=(e.id,f.id)+( (rng.choice(third).id,) if third else () )
                    rules.append(Rule(rng.choice(("no","only")),ids))
            g=Graph(tuple((n,float(n),0.) for n in range(5)),tuple(edges),tuple(rules))
            journeys=[]
            for a in range(5):
                inbound=[()] + [(e.id,) for e in edges if e.v==a][:1]
                for b in range(5):
                    journeys.extend((a,b,h,Vehicle()) for h in inbound)
            self.compare(g,journeys,(0,4))

    def test_invalid_protocol_fails(self):
        g=fixture(3,111)
        text=encode(g,[("alt",0,8,Vehicle(),())],(0,8))
        malformed=[
            text.replace("DMNAV1","BAD",1),
            text.replace("DMNAV1 9","DMNAV1 -9",1),
            text[:30],
            text.replace("alt 0 8","wrong 0 8",1),
            text.replace("alt 0 8","alt 999 8",1),
            text.replace("alt 0 8 0 -1 -1 0","alt 0 8 0 -2 -1 0",1),
            text+"extra\n"]
        for data in malformed:
            p=subprocess.run([str(BIN)],input=data,text=True,capture_output=True,timeout=5)
            self.assertNotEqual(p.returncode,0)
            self.assertIn("ERROR",p.stderr)

    def test_native_cost_overflow_is_error_not_no_route(self):
        g=Graph(tuple((n,float(n),0.) for n in range(1030)),
                tuple(Edge(n,n,n+1,2**53-1) for n in range(1029)))
        with self.assertRaisesRegex(ValueError,"capacity"):
            run(g,[("dijkstra",0,1029,Vehicle(),())],(),BIN)

    def test_invalid_graph_rejected_at_native_boundary(self):
        valid="DMNAV1 2 1 0 0\n0 0 0\n1 1 0\n1 0 1 2 3 -1 -1\n0\n1\ndijkstra 0 1 0 -1 -1 0\n"
        for data in [
            valid.replace("1 0 1 2 3","1 0 1 -2 3",1),
            valid.replace("1 0 1 2 3","1 0 99 2 3",1),
            valid.replace("1 1 0\n","0 1 0\n",1),
            valid.replace("1 0 1 2 3","1 0 1 2 7",1),
            valid.replace("0 0 0\n","0 nan 0\n",1),
            valid.replace("dijkstra 0 1 0","dijkstra 0 1 2",1)]:
            p=subprocess.run([str(BIN)],input=data,text=True,capture_output=True,timeout=5)
            self.assertNotEqual(p.returncode,0)
            self.assertIn("ERROR",p.stderr)


if __name__=="__main__":
    unittest.main()
