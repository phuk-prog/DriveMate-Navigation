import unittest
from benchmarks.expanded_fixture import suite
from benchmarks.route_quality_fixture import optimum, judge_route, controls


class RouteQualityTests(unittest.TestCase):
    def test_larger_fixture_has_discovery_holdout_and_fixed_turn_truth(self):
        data=suite();rows=data['quality_cases']
        self.assertEqual(len(rows),64)
        self.assertEqual(sum(r['split']=='holdout' for r in rows),32)
        self.assertGreater(len(data['nodes']),1000)
        for row in rows:
            expected=optimum(data,row)
            self.assertEqual(expected is not None,row['category']!='reverse_no_route')

    def test_independent_oracle_detects_wrong_destination_and_false_no_route(self):
        data=suite();case=data['quality_cases'][0];gold=optimum(data,case)
        self.assertEqual(judge_route(data,case,gold[1],False)['status'],'pass')
        self.assertEqual(judge_route(data,case,gold[1][:-1],False)['status'],'fail')
        self.assertEqual(judge_route(data,case,None,True)['status'],'fail')
        self.assertTrue(all(r['detected'] for r in controls(data)))
