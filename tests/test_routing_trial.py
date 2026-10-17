import unittest
from benchmarks.routing_trial import load_cases, judge, run_dmn

class RoutingTrialTests(unittest.TestCase):
    def test_declared_paths_pass(self):
        for case in load_cases():
            self.assertEqual(judge(case,case['path'])['outcome'],'PASS')

    def test_wrong_way_shortcut_fails(self):
        for case in load_cases()[2:]:
            row=judge(case,[case['path'][0],case['path'][-1]])
            self.assertEqual(row['outcome'],'FAIL')
            self.assertFalse(row['checks']['declared_path_length'])

    def test_reversed_direct_path_fails_endpoints(self):
        case=load_cases()[0]
        self.assertEqual(judge(case,list(reversed(case['path'])))['outcome'],'FAIL')

    def test_dmn_executes_four_cases(self):
        self.assertTrue(all(c['outcome']=='PASS' for c in run_dmn()['cases']))
