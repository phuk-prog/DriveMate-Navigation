"""Synthetic resource measurement controls, not engine performance verdicts."""
import importlib.util
import unittest

class ResourceTests(unittest.TestCase):
    def test_real_worker_correctness(self):
        self.assertIsNotNone(importlib.util.find_spec('benchmarks.resource_trial'),
                             'Separate setup/request/memory resource harness required')
        from benchmarks.resource_trial import worker
        r=worker(8,'Dijkstra','timing')
        self.assertTrue(all(c['outcome']=='PASS' for c in r['cases']))
        self.assertTrue(all(len(c['samples_ns'])==10 for c in r['cases']))

    def test_prepared_search_bounds_repeated_distance_work(self):
        # Spy delegates every call to real geodesic math; no fabricated route.
        from unittest.mock import patch
        from benchmarks.synthetic_grid import grid
        from engine.astar import astar_route,prepare_astar,metres
        g,p,s,t=grid(8);prepared=prepare_astar(g,p)
        with patch('engine.astar.metres',wraps=metres) as distance:
            r=astar_route(g,s,t,prepared=prepared)
        self.assertEqual(len(r.route.edge_ids),14)
        self.assertLessEqual(distance.call_count,len(g.vertices),
                             'Per-query distance heuristic must not repeat across incoming states')

    def test_changed_destination_does_not_reuse_prior_heuristic(self):
        from benchmarks.synthetic_grid import grid
        from engine.astar import astar_route,prepare_astar
        g,p,s,t=grid(8);prepared=prepare_astar(g,p)
        for source,dest,edges in ((s,t,14),(t,s,14),('v-4-0','v-4-7',7)):
            r=astar_route(g,source,dest,prepared=prepared).route
            self.assertEqual(len(r.edge_ids),edges)
            self.assertAlmostEqual(r.length_m,edges*112)

    def test_nearest_rank_percentile(self):
        from benchmarks.resource_trial import percentile95
        self.assertEqual(percentile95(list(range(1,21))),19)
        self.assertEqual(percentile95(list(range(1,11))),10)
        with self.assertRaises(ValueError):percentile95([])
