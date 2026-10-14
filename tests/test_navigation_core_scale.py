import unittest
import math
from navigation_core.core import Router
from navigation_core.holdout import fixture, cases
from navigation_core.validation.oracle import oracle, validate_route


class HoldoutTests(unittest.TestCase):
    def test_unseen_restrictions_against_independent_oracle(self):
        for seed in (7101,8129,9103):
            g=fixture(7,seed,split=seed==9103)
            router=Router(g,(0,6,42,48))
            for a,b,h,v in cases(g,seed+1,18):
                expected=oracle(g,a,b,v,h)
                for mode in ("dijkstra","astar","alt"):
                    got=router.route(a,b,v,mode,h)
                    self.assertEqual(math.inf if got is None else got.cost,expected)
                    if got:
                        validate_route(g,a,b,v,h,got)

    def test_cached_and_uncached_routes_identical(self):
        g=fixture(7,4123)
        for cap in (0,1,8,64):
            router=Router(g,(0,48),cache_capacity=cap)
            for a,b,h,v in cases(g,4124,16):
                expected=oracle(g,a,b,v,h)
                for mode in ("dijkstra","astar","alt"):
                    got=router.route(a,b,v,mode,h)
                    self.assertEqual(math.inf if got is None else got.cost,expected)
                    if got:
                        validate_route(g,a,b,v,h,got)
                self.assertLessEqual(router.cache_entries,cap)


if __name__=="__main__":
    unittest.main()
