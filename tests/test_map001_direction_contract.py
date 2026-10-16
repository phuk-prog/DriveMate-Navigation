"""Synthetic oracle/mutation controls; not real UK road evidence."""
import unittest
from copy import deepcopy
import xml.etree.ElementTree as ET
from benchmarks.map001_direction_contract import (direction_access, edge_differences,
    relation_contract, audit_way, edge_expectation)
from benchmarks.map001_v3 import turn_differences
from test_map001_v3_fact_extensions import fixture

class DirectionContract(unittest.TestCase):
    def test_all_vehicle_directional_keys_and_orientations(self):
        for mode in ('motorcar','motor_vehicle','vehicle','access'):
            for forward in (True,False):
                with self.subTest(mode=mode,forward=forward):
                    t={'highway':'residential', mode+(':forward' if forward else ':backward'):'no'}
                    self.assertEqual(direction_access(t,forward),'prohibited')
                    self.assertEqual(direction_access(t,not forward),'allowed')

    def test_specific_car_override(self):
        self.assertEqual(direction_access({'motorcar':'yes','vehicle:backward':'no'},False),'allowed')
        self.assertEqual(direction_access({'motorcar:backward':'no','motorcar':'yes'},False),'prohibited')

    def test_bus_taxi_cycle_permissions_do_not_allow_ordinary_cars(self):
        t={'vehicle:backward':'no', 'bus:backward':'designated','taxi:backward':'designated','bicycle:backward':'designated'}
        self.assertEqual(direction_access(t,False),'prohibited')

    def test_context_is_not_hard_denial(self):
        for value in ('private','destination','delivery','customers','permit','agricultural','forestry'):
            with self.subTest(value=value):
                self.assertEqual(direction_access({'motor_vehicle:forward':value},True),'contextual')

    def test_conditional_precedes_direction(self):
        self.assertEqual(direction_access({'oneway':'yes','vehicle:conditional':'no @ (Mo)'},False),'unknown')

    def test_unknown_oneway(self):
        self.assertEqual(direction_access({'oneway':'alternating'},True),'unknown')

    def test_mode_specific_oneway_is_explicitly_unsupported(self):
        self.assertEqual(direction_access({'oneway':'yes','oneway:motorcar':'no'},False),'unknown')

    def test_bicycle_oneway_exception_does_not_change_car_direction(self):
        self.assertEqual(direction_access({'oneway':'yes','oneway:bicycle':'no'},False),'prohibited')

    def test_oneway_reverse_and_roundabout(self):
        for t,f in (({'oneway':'yes'},False),({'oneway':'-1'},True),({'junction':'roundabout'},False)):
            with self.subTest(tags=t):self.assertEqual(direction_access(t,f),'prohibited')

    def test_edge_mutations_missing_extra_and_access(self):
        expected={'a':('1','2','allowed'),'b':('2','1','prohibited')}
        actual={'a':('2','1','allowed'),'c':('3','4','allowed')}
        d=edge_differences(expected,actual)
        self.assertEqual(d['missing_edges'],['b'])
        self.assertEqual(d['extra_edges'],['c'])
        self.assertEqual(d['wrong_edges'][0]['edge'],'a')

    def test_both_turn_prohibition_errors(self):
        self.assertEqual(turn_differences({('a','b')},{('a','c')}),([('a','b')],[('a','c')]))

    def test_runtime_directional_fix_agrees_with_frozen_oracle(self):
        n,w,r=fixture()
        x=audit_way(w['11'],n)
        self.assertEqual(x['verdict'],'PASS')
        self.assertEqual(x['differences']['wrong_edges'],[])

    def test_reversing_node_order_preserves_source_direction_meaning(self):
        n,w,r=fixture()
        way=deepcopy(w['11'])
        nd=way.findall('nd')
        for x in nd:way.remove(x)
        for x in reversed(nd):way.insert(len(way.findall('nd')),x)
        edges,issue=edge_expectation(way,n)
        self.assertIsNone(issue)
        self.assertEqual(edges['w:11:0:r'],('osm:1','osm:2','prohibited'))

    def test_missing_nodes_not_judged(self):
        n,w,r=fixture();del n['2']
        self.assertEqual(edge_expectation(w['11'],n)[1],'INCOMPLETE_SOURCE')

    def test_relation_inapplicable_not_invalid_proof(self):
        n,w,r=fixture();x=relation_contract(r[0],w,n)
        self.assertEqual(x['verdict'],'NO_AVAILABLE_MOTORCAR_MOVEMENT')
        self.assertFalse(x['stale_or_legally_invalid_proven'])

    def test_relation_conditional_never_passes(self):
        n,w,r=fixture();ET.SubElement(r[0],'tag',k='restriction:conditional',v='no_left_turn @ (Mo)')
        self.assertEqual(relation_contract(r[0],w,n)['verdict'],'UNKNOWN_CONDITIONAL')

    def test_relation_car_exception_and_bus_exception_differ(self):
        for mode,expected in (('motorcar','EXEMPT_ORDINARY_MOTORCAR'),('bus','NO_AVAILABLE_MOTORCAR_MOVEMENT')):
            n,w,r=fixture();ET.SubElement(r[0],'tag',k='except',v=mode)
            self.assertEqual(relation_contract(r[0],w,n)['verdict'],expected)

    def test_relation_extra_member_is_unsupported(self):
        n,w,r=fixture();ET.SubElement(r[0],'member',type='way',ref='99',role='via')
        self.assertEqual(relation_contract(r[0],w,n)['verdict'],'UNSUPPORTED_RELATION')

    def test_relation_missing_way_is_incomplete(self):
        n,w,r=fixture();del w['12']
        self.assertEqual(relation_contract(r[0],w,n)['verdict'],'INCOMPLETE_SOURCE')

    def test_importer_honours_all_eight_directional_denial_controls(self):
        for mode in ('motorcar','motor_vehicle','vehicle','access'):
            for orient in ('forward','backward'):
                with self.subTest(mode=mode,orient=orient):
                    n,w,r=fixture()
                    way=w['11']
                    for tag in list(way.findall('tag')):
                        if tag.get('k')!='highway':way.remove(tag)
                    ET.SubElement(way,'tag',k=mode+':'+orient,v='no')
                    x=audit_way(way,n)
                    self.assertEqual(x['verdict'],'PASS')
                    self.assertEqual(x['differences']['wrong_edges'],[])

    def test_conditional_import_is_safely_withheld(self):
        n,w,r=fixture();ET.SubElement(w['11'],'tag',k='vehicle:conditional',v='no @ (Mo)')
        self.assertEqual(audit_way(w['11'],n)['verdict'],'SAFE_WITHHELD')

    def test_explicit_way_denial_is_a_source_agreement_control(self):
        n,w,r=fixture();ET.SubElement(w['11'],'tag',k='motorcar',v='no')
        self.assertEqual(audit_way(w['11'],n)['verdict'],'PASS')

    def test_barrier_uncertainty_is_unjudged(self):
        n,w,r=fixture();ET.SubElement(n['1'],'tag',k='barrier',v='gate')
        self.assertEqual(audit_way(w['11'],n)['verdict'],'NOT_JUDGED')

    def test_old_directional_bug_mutation_is_still_detected(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        n,w,r=fixture()
        graph=SimpleNamespace(edges={
            'w:11:0:f':SimpleNamespace(source='osm:1',target='osm:2',access='allowed'),
            'w:11:0:r':SimpleNamespace(source='osm:2',target='osm:1',access='allowed')})
        with patch('benchmarks.map001_direction_contract.import_osm_xml',
                   return_value=SimpleNamespace(graph=graph)):
            x=audit_way(w['11'],n)
        self.assertEqual(x['verdict'],'FAIL')
        self.assertEqual(x['differences']['wrong_edges'][0]['edge'],'w:11:0:r')

class AccessApplicabilityReview(unittest.TestCase):
    def test_private_and_destination_require_different_evidence(self):
        from benchmarks.map001_access_review import access_basis
        self.assertEqual(access_basis({'access':'private'})[0],'AUTHORIZATION_REQUIRED')
        self.assertEqual(access_basis({'motor_vehicle':'destination'})[0],'JOURNEY_PURPOSE_REQUIRED')

    def test_explicit_car_permission_precedes_private_general_access(self):
        from benchmarks.map001_access_review import access_basis
        self.assertEqual(access_basis({'motorcar':'yes','access':'private'})[0],'EXPLICIT_MODE_PERMISSION')

    def test_service_default_does_not_invent_legal_denial(self):
        from benchmarks.map001_access_review import access_basis
        self.assertEqual(access_basis({'highway':'service','bus':'yes'})[0],'UNSPECIFIED_SERVICE_PERMISSION')

    def test_context_withholding_is_not_a_road_legality_pass(self):
        from benchmarks.map001_access_review import review_way
        n,w,r=fixture()
        ET.SubElement(w['11'],'tag',k='access',v='private')
        x=review_way(w['11'],n)
        self.assertEqual(x['road_legality_verdict'],'NOT_JUDGED')
        self.assertEqual(x['dmn_no_permission_safety_policy'],'SAFE_WITHHELD')
        self.assertNotIn('PASS',x.values())

    def test_previously_judged_way_is_not_added_to_unjudged_cohort(self):
        from benchmarks.map001_access_review import review_way
        n,w,r=fixture()
        self.assertIsNone(review_way(w['11'],n))

    def test_decode_polyline6_and_reject_malformed(self):
        from benchmarks.map001_access_review import decode_shape
        self.assertEqual(decode_shape('??AC'),[(0,0),(0.000001,0.000002)])
        for s in ('','?','~~~~~~~','!','??'):
            with self.subTest(shape=s),self.assertRaises(ValueError):decode_shape(s)

    def test_stored_shape_direction_is_verified_against_osm_order(self):
        from unittest.mock import patch
        from benchmarks.map001_access_review import osm_orientation
        n,w,r=fixture()
        c={'edge':{'forward':True},'edge_info':{'shape':'unused'}}
        with patch('benchmarks.map001_access_review.decode_shape',return_value=[(53,-2),(53.001,-2)]):
            self.assertTrue(osm_orientation(c,w['11'],n))
        with patch('benchmarks.map001_access_review.decode_shape',return_value=[(53.001,-2),(53,-2)]):
            self.assertFalse(osm_orientation(c,w['11'],n))
        with patch('benchmarks.map001_access_review.decode_shape',return_value=[(54,-2),(54.001,-2)]):
            self.assertIsNone(osm_orientation(c,w['11'],n))

    def test_filtered_candidates_are_preserved_without_inventing_turn_proof(self):
        from benchmarks.map001_access_review import candidate_review
        n,w,r=fixture()
        x=candidate_review('11',{'edges':[],'filtered_edges':[{
            'edge_info':{'way_id':11},'edge_id':{'value':42},
            'edge':{'access':{'car':False},'forward':True,'end_node':{'value':9}}}]},w['11'],n)
        self.assertEqual(x['candidates'][0]['graph_id'],42)
        self.assertEqual(x['candidates'][0]['bucket'],'filtered_edges')
        self.assertIsNone(x['candidates'][0]['osm_forward_verified'])
        self.assertTrue(x['turn_pairs_verdict'].startswith('UNSUPPORTED'))
