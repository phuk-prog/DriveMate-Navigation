"""Synthetic oracle and ranking contract; injected replies are never live runs."""
import unittest

from benchmarks.navigation_trial import judge, scoreboard, load_cases, run_dmn


class NavigationTrialTests(unittest.TestCase):
    def test_exact_independently_declared_positions_pass(self):
        case = load_cases()[0]
        result = judge(case, case['truth'])
        self.assertEqual(result['outcome'], 'PASS')
        self.assertTrue(all(result['checks'].values()))

    def test_reversed_sequence_fails_position_and_direction(self):
        case = load_cases()[0]
        result = judge(case, list(reversed(case['truth'])))
        self.assertEqual(result['outcome'], 'FAIL')
        self.assertFalse(result['checks']['forward_direction'])
        self.assertFalse(result['checks']['positions_within_5m'])

    def test_partial_response_is_missing_required_output_not_pass(self):
        case = load_cases()[0]
        result = judge(case, [None] + case['truth'][1:])
        self.assertEqual(result['outcome'], 'FAIL')
        self.assertFalse(result['checks']['complete_four_observations'])
        self.assertIn('missing_required_match', result['failures'])

    def test_unavailable_engine_is_not_zero_score_or_failed_case(self):
        rows = scoreboard([])
        self.assertEqual(len(rows), 13)
        self.assertTrue(all(r['score_out_of_ten'] is None for r in rows))
        self.assertTrue(all(r['failed'] == 0 for r in rows))
        self.assertTrue(all(r['not_run'] == 6 for r in rows))

    def test_duplicate_engine_results_are_rejected(self):
        report = run_dmn()
        with self.assertRaises(ValueError):
            scoreboard([report, report])

    def test_injected_results_cannot_receive_a_live_engine_rank(self):
        report = run_dmn()
        report['system'] = 'OSRM'
        report['execution'] = 'injected_test_double'
        rows = scoreboard([report])
        self.assertIsNone(next(r for r in rows if r['system'] == 'OSRM')['rank'])


if __name__ == '__main__':
    unittest.main()
