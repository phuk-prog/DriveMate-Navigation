"""Negative controls for programme evidence claims; not mocked engine passes."""
import copy
import json
import unittest
from tools.validation_readiness import audit,CONFIG

class ReadinessTests(unittest.TestCase):
    def test_real_execution_evidence_is_under_ten(self):
        r=audit();self.assertEqual(r['actual_static_families'],5)
        self.assertFalse(r['ten_engine_requirement_met']);self.assertEqual(r['new_generated_variants_executed'],0)
        self.assertEqual(len(r['candidate_target_families']),10)
    def test_variants_cannot_inflate_family_count(self):
        c=json.loads(CONFIG.read_text());c['references'][0]['family']='OSRM CH'
        with self.assertRaises(ValueError):audit(c)
    def test_duplicate_family_rejected(self):
        c=json.loads(CONFIG.read_text());c['references'].append(copy.deepcopy(c['references'][0]))
        with self.assertRaises(ValueError):audit(c)
    def test_new_unexecuted_engine_cannot_be_claimed_as_run(self):
        c=json.loads(CONFIG.read_text());r=next(r for r in c['references'] if r['family']=='Itinero');r.update(execution_status='EXECUTED_STATIC_ROUTING',evidence='references/junction001-executed-20261016.json')
        with self.assertRaises(ValueError):audit(c)
    def test_million_case_claim_needs_evidence(self):
        c=json.loads(CONFIG.read_text());c['scale_policy']['executed_generated_variants_under_this_revision']=1000000
        with self.assertRaises(ValueError):audit(c)
