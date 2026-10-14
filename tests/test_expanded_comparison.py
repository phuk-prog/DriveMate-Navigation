import unittest
from benchmarks.expanded_fixture import suite, legal_paths, judge, mutation_controls


class ExpandedComparisonTests(unittest.TestCase):
    def test_independent_golden_paths_and_heldout_coverage(self):
        data = suite()
        self.assertGreaterEqual(len(data['cases']), 60)
        self.assertEqual({c['split'] for c in data['cases']}, {'discovery', 'holdout'})
        for case in data['cases']:
            paths = legal_paths(data, case)
            self.assertEqual(bool(paths), case['reachable'], case['id'])
            for path in paths:
                self.assertEqual(judge(data, case, path, False)['status'], 'pass')
            if not paths:
                self.assertEqual(judge(data, case, None, True)['status'], 'pass')
                self.assertEqual(judge(data, case, None, False)['status'], 'unresolved')

    def test_fault_controls_require_clean_baselines(self):
        rows = mutation_controls(suite())
        self.assertGreaterEqual(len(rows), 6)
        self.assertTrue(all(r['baseline_passed'] and r['detected'] for r in rows), rows)

    def test_missing_route_on_reachable_case_is_failure(self):
        data = suite()
        case = next(c for c in data['cases'] if c['reachable'])
        self.assertEqual(judge(data, case, None, True)['status'], 'fail')
        self.assertEqual(judge(data, case, None, False)['status'], 'unresolved')

    def test_trace_inputs_use_independent_legal_paths(self):
        from benchmarks.expanded_comparison import clean_trace
        data=suite()
        for case in data['cases']:
            if not case['reachable']: continue
            path,samples=clean_trace(data,case)
            self.assertIn(tuple(path),legal_paths(data,case))
            self.assertLessEqual(len(samples),100)
            self.assertTrue(all(not s['injected_fault'] for s in samples))

    def test_endpoint_snapping_cannot_earn_a_pass(self):
        from benchmarks.expanded_comparison import endpoint_check
        data=suite();case=data['cases'][0]
        a,b=[data['nodes'][case[k]] for k in ('start','end')]
        good={'routes':[{'geometry':{'coordinates':[[a[1],a[0]],[b[1],b[0]]]}}]}
        self.assertTrue(endpoint_check('osrm',good,data,case)['within_2m'])
        good['routes'][0]['geometry']['coordinates'][-1][0]+=.001
        self.assertFalse(endpoint_check('osrm',good,data,case)['within_2m'])

    def test_independent_geometry_judge_catches_reversed_ring(self):
        from benchmarks.expanded_comparison import shape_roads
        data=suite();way=next(w for w in data['ways'].values() if w['tags'].get('junction'))
        shape=[data['nodes'][n] for n in way['nodes'][:4]]
        self.assertEqual(shape_roads(data,shape)[1],'pass')
        self.assertEqual(shape_roads(data,list(reversed(shape)))[1],'fail')


if __name__ == '__main__':
    unittest.main()
