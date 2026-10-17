"""Output-judge negative controls only; never counted as engine executions."""
import unittest
from benchmarks.itinero_public_probe import judge

class ItineroProbeTests(unittest.TestCase):
    def case(self):return dict(id='control',start=[53.355,-2.265],end=[53.356,-2.265])
    def test_provider_error_is_unresolved_not_no_route_pass(self):
        r=judge(self.case(),dict(id='control',status='UNRESOLVED',reason='search error'))
        self.assertEqual(r['outcome'],'UNRESOLVED')
    def test_wrong_endpoint_is_failed_output_contract(self):
        r=judge(self.case(),dict(id='control',status='OUTPUT',points=[[53.355,-2.265],[53.3551,-2.265]]))
        self.assertEqual(r['outcome'],'FAIL');self.assertFalse(r['checks']['end_within_5m'])
    def test_nonfinite_geometry_never_passes(self):
        r=judge(self.case(),dict(id='control',status='OUTPUT',points=[[53.355,-2.265],[float('nan'),-2.265]]))
        self.assertEqual(r['outcome'],'UNRESOLVED')

    def test_expected_map_hash_is_prior_xml_fingerprint(self):
        import json
        from benchmarks.itinero_public_probe import ROOT,EXPECTED_XML_HASH
        prior=json.loads((ROOT/'references/gps001-uk-topology-20261015.json').read_text())['report']
        self.assertEqual(EXPECTED_XML_HASH,prior['source_sha256'])
