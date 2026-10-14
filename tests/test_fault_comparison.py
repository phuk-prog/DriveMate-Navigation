import unittest
from benchmarks.expanded_fixture import suite
from benchmarks.fault_comparison import scenarios, canonical_input, judge_sequence, parse_batch, controls


class FaultComparisonTests(unittest.TestCase):
    def test_fixed_fault_coverage_and_preserved_truth(self):
        rows=scenarios(suite())
        self.assertEqual(len(rows),80)
        self.assertEqual({x['split'] for x in rows},{'discovery','holdout'})
        self.assertEqual({x['fault'] for x in rows},{'jitter_2m','spike_40m','gap_3fix','compound'})
        for row in rows:
            self.assertTrue(3<=len(row['samples'])<=100)
            self.assertEqual(row['expected_ways'],row['baseline_expected_ways'])
            self.assertNotEqual(canonical_input(row['samples']),canonical_input(row['baseline_samples']))

    def test_no_clock_or_engine_only_fields_in_common_input(self):
        row=scenarios(suite())[0]
        body=canonical_input(row['samples'])
        self.assertEqual(set(body),{'coordinates','accuracy_m','timing'})
        self.assertEqual(body['timing'],'not supplied')
        self.assertEqual(body['accuracy_m'],3)
        self.assertTrue(all(len(x)==2 for x in body['coordinates']))

    def test_wrong_sequence_and_explicit_no_match_are_failures(self):
        self.assertEqual(judge_sequence([1,2,3],[1,2,3],'pass')['status'],'pass')
        self.assertEqual(judge_sequence([1,2,3],[1,3],'pass')['status'],'fail')
        self.assertEqual(judge_sequence([1,2,3],None,'fail')['status'],'fail')
        self.assertEqual(judge_sequence([1,2,3],None,'unresolved')['status'],'unresolved')

    def test_api_no_match_and_split_paths_do_not_earn_passes(self):
        data=suite()
        self.assertEqual(parse_batch('osrm',data,{'code':'NoMatch'})[1],'fail')
        self.assertEqual(parse_batch('osrm',data,{'code':'Ok','matchings':[{},{}]})[1],'fail')
        self.assertEqual(parse_batch('valhalla',data,{'error_code':442})[1],'fail')
        self.assertEqual(parse_batch('osrm',data,{'code':'UnknownService'})[1],'unresolved')

    def test_fault_judge_controls_detect_every_corrupt_output(self):
        rows=controls()
        self.assertGreaterEqual(len(rows),4)
        self.assertTrue(all(x['baseline_passed'] and x['detected'] for x in rows))

    def test_malformed_api_geometry_is_unresolved_without_crashing(self):
        data=suite()
        for raw in (None,[],{'code':'Ok','matchings':[None]},
                    {'code':'Ok','matchings':[{'geometry':None}]},
                    {'code':'Ok','matchings':[{'geometry':{'coordinates':[1,2]}}]},
                    {'code':'Ok','matchings':[{'geometry':{'coordinates':[[False,0],[0,0]]}}]}):
            self.assertEqual(parse_batch('osrm',data,raw)[1],'unresolved')
        self.assertEqual(parse_batch('valhalla',data,{'trip':None})[1],'unresolved')
        self.assertEqual(parse_batch('graphhopper',data,{'paths':[None]})[1],'unresolved')
