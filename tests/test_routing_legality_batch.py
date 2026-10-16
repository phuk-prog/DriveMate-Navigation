import unittest
from benchmarks.routing_legality_batch import load_cases, judge_case, run_dmn, scorecard, classify_response

class RoutingLegalityBatchTests(unittest.TestCase):
    def test_declared_controls_pass(self):
        for case in load_cases():
            result={'status':'NO_ROUTE'} if case['expected']=='NO_ROUTE' else {'status':'ROUTE','points':case['path']}
            self.assertEqual(judge_case(case,result)['outcome'],'PASS')

    def test_prohibited_shortcuts_and_fabricated_connection_fail(self):
        cases=load_cases()
        for case in (cases[0],cases[2],cases[3],cases[5]):
            self.assertEqual(judge_case(case,{'status':'ROUTE','points':[case['start'],case['end']]})['outcome'],'FAIL')

    def test_error_is_not_no_route_or_pass(self):
        row=judge_case(load_cases()[3],{'status':'UNRESOLVED','reason':'HTTP500'})
        self.assertEqual(row['outcome'],'UNRESOLVED')

    def test_actual_dmn_and_shared_cohort(self):
        report=run_dmn()
        self.assertEqual(len(report['cases']),8)
        self.assertTrue(all(c['outcome']=='PASS' for c in report['cases']))
        rows=scorecard([report])['rows']
        self.assertEqual(len(rows),13)
        self.assertEqual(rows[0]['score_out_of_ten'],10)
        self.assertEqual(rows[0]['judged_shared_cases'],5)
        self.assertTrue(all(r['rank'] is None for r in rows[1:]))

    def test_provider_error_cannot_be_a_no_route_pass(self):
        for name,raw in [('OSRM',b'{"code":"NoRoute"}'),('Valhalla',b'{"error_code":442}'),('GraphHopper',b'{"hints":[{"details":"ConnectionNotFoundException"}]}'),('openrouteservice',b'{"error":{"code":2009}}')]:
            self.assertEqual(classify_response(name,500,raw)['status'],'UNRESOLVED')

    def test_explicit_search_refusal_is_distinct_from_missing_map(self):
        self.assertEqual(classify_response('OSRM',400,b'{"code":"NoRoute"}')['status'],'NO_ROUTE')
        self.assertEqual(classify_response('OSRM',400,b'{"code":"NoSegment"}')['status'],'UNRESOLVED')
        self.assertEqual(classify_response('BRouter',400,b'no track found at pass=0')['status'],'NO_ROUTE')
        self.assertEqual(classify_response('BRouter',400,b'map file not found')['status'],'UNRESOLVED')

    def test_longer_legal_variant_not_failed_for_profile_costs(self):
        case=load_cases()[0]
        self.assertEqual(judge_case(case,{'status':'ROUTE','points':case['accepted_paths'][1]})['outcome'],'PASS')
