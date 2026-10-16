"""Synthetic analytical judge controls; not real-road executions.

A reversed imported edge or a wrong-way route must fail this map-contract judge.
"""
import unittest
from benchmarks.real_map_oneway import judge

class OneWayJudgeTests(unittest.TestCase):
    def test_reverse_import_is_failure_even_if_route_avoids_it(self):
        self.assertEqual(judge(positive=False, allowed_present=True, forbidden_present=True, route_ids=[], forbidden_ids={'bad'}, no_route=True)['outcome'], 'FAIL')

    def test_wrong_way_route_fails(self):
        self.assertEqual(judge(positive=False, allowed_present=True, forbidden_present=False, route_ids=['bad'], forbidden_ids={'bad'}, no_route=False)['outcome'], 'FAIL')

    def test_positive_no_route_is_not_a_pass(self):
        self.assertEqual(judge(positive=True, allowed_present=True, forbidden_present=False, route_ids=[], forbidden_ids={'bad'}, no_route=True)['outcome'], 'FAIL')

    def test_reverse_no_route_only_passes_direction_contract(self):
        r=judge(positive=False, allowed_present=True, forbidden_present=False, route_ids=[], forbidden_ids={'bad'}, no_route=True)
        self.assertEqual(r['outcome'], 'PASS')
        self.assertEqual(r['real_world_legality'], 'UNRESOLVED')
