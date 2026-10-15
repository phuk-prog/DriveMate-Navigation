"""Authored fault controls only; these are never counted as real-road results."""
import importlib
import unittest

XML = b'''<osm><node id="1" lat="53.5" lon="-2.6"/><node id="2" lat="53.5" lon="-2.599"/><node id="3" lat="53.501" lon="-2.599"/><node id="4" lat="53.5" lon="-2.598"/>
<way id="10"><nd ref="1"/><nd ref="2"/><tag k="highway" v="residential"/><tag k="oneway" v="yes"/></way>
<way id="20"><nd ref="2"/><nd ref="3"/><tag k="highway" v="residential"/></way>
<way id="30"><nd ref="2"/><nd ref="4"/><tag k="highway" v="residential"/><tag k="motorcar" v="no"/></way>
<relation id="100"><member type="way" ref="10" role="from"/><member type="node" ref="2" role="via"/><member type="way" ref="20" role="to"/><tag k="type" v="restriction"/><tag k="restriction" v="no_right_turn"/></relation></osm>'''
POINTS = {1: [-2.6,53.5], 2: [-2.599,53.5], 3: [-2.599,53.501],4:[-2.598,53.5]}

class LegalityTest(unittest.TestCase):
    def judge(self, ids, xml=XML):
        mod=importlib.import_module('benchmarks.real_road_legality')
        return mod.judge(xml,[POINTS[i] for i in ids])

    def test_judge_is_implemented(self):
        from pathlib import Path
        self.assertTrue(Path('benchmarks/real_road_legality.py').is_file(), 'Shared raw-OSM legality judge missing')

    def test_reverse_oneway_detected(self):
        self.assertEqual(self.judge([2,1])['one_way'],'fail')

    def test_forbidden_turn_detected(self):
        self.assertEqual(self.judge([1,2,3])['turn_restrictions'],'fail')

    def test_access_ban_detected(self):
        self.assertEqual(self.judge([2,4])['access'],'fail')

    def test_not_exercised_is_unresolved(self):
        result=self.judge([2,3])
        self.assertEqual(result['turn_restrictions'],'unresolved')
        self.assertEqual(result['independent_uk_legality'],'unresolved')

    def test_disconnected_geometry_is_unresolved_not_illegal(self):
        self.assertEqual(self.judge([1,3])['connectivity'],'unresolved')

    def test_ambiguous_parallel_ways_never_choose_legal_option(self):
        xml=XML.replace(b'</osm>',b'<way id="40"><nd ref="1"/><nd ref="2"/><tag k="highway" v="residential"/></way></osm>')
        self.assertEqual(self.judge([2,1],xml)['one_way'],'unresolved')

    def test_only_turn_violation(self):
        xml=XML.replace(b'no_right_turn',b'only_right_turn')
        self.assertEqual(self.judge([1,2,4],xml)['turn_restrictions'],'fail')

    def test_roundabout_wrong_direction_detected(self):
        xml=XML.replace(b'<tag k="oneway" v="yes"/>',b'<tag k="junction" v="roundabout"/>')
        self.assertEqual(self.judge([2,1],xml)['roundabout_direction'],'fail')

    def test_conditional_access_is_unresolved(self):
        xml=XML.replace(b'<tag k="oneway" v="yes"/>',b'<tag k="access:conditional" v="no @ (Mo-Fr)"/>')
        self.assertEqual(self.judge([1,2],xml)['access'],'unresolved')

    def test_access_specific_override(self):
        xml=XML.replace(b'<tag k="motorcar" v="no"/>',b'<tag k="access" v="no"/><tag k="motorcar" v="yes"/>')
        self.assertEqual(self.judge([2,4],xml)['access'],'pass')

    def test_conditional_node_access_unresolved(self):
        xml=XML.replace(b'<node id="2" lat="53.5" lon="-2.599"/>',b'<node id="2" lat="53.5" lon="-2.599"><tag k="access:conditional" v="no @ (Mo-Fr)"/></node>')
        self.assertEqual(self.judge([1,2],xml)['access'],'unresolved')

    def test_vehicle_dimensions_unknown(self):
        xml=XML.replace(b'<tag k="oneway" v="yes"/>',b'<tag k="maxheight" v="1.2"/>')
        self.assertEqual(self.judge([1,2],xml)['access'],'unresolved')

    def test_private_permission_unknown(self):
        xml=XML.replace(b'<tag k="motorcar" v="no"/>',b'<tag k="access" v="private"/>')
        self.assertEqual(self.judge([2,4],xml)['access'],'unresolved')

    def test_via_way_unsupported_is_not_hidden_by_supported_pass(self):
        xml=XML.replace(b'no_right_turn',b'only_right_turn').replace(b'</osm>',b'<relation id="200"><member type="way" ref="90" role="from"/><member type="way" ref="20" role="via"/><member type="way" ref="91" role="to"/><tag k="type" v="restriction"/><tag k="restriction" v="no_left_turn"/></relation></osm>')
        self.assertEqual(self.judge([1,2,3],xml)['turn_restrictions'],'unresolved')

    def test_locked_gate_never_passes_without_opening_evidence(self):
        xml=XML.replace(b'<node id="2" lat="53.5" lon="-2.599"/>',b'<node id="2" lat="53.5" lon="-2.599"><tag k="barrier" v="gate"/><tag k="motorcar" v="yes"/><tag k="locked" v="yes"/></node>')
        self.assertEqual(self.judge([1,2],xml)['access'],'unresolved')

    def test_bollard_with_highway_tag_never_uses_way_fallback(self):
        xml=XML.replace(b'<node id="2" lat="53.5" lon="-2.599"/>',b'<node id="2" lat="53.5" lon="-2.599"><tag k="highway" v="residential"/><tag k="barrier" v="bollard"/></node>')
        self.assertEqual(self.judge([1,2],xml)['access'],'unresolved')

    def test_node_axle_limit_is_unresolved(self):
        xml=XML.replace(b'<node id="2" lat="53.5" lon="-2.599"/>',b'<node id="2" lat="53.5" lon="-2.599"><tag k="maxaxleload" v="1.2"/></node>')
        self.assertEqual(self.judge([1,2],xml)['access'],'unresolved')

class ScorecardTest(unittest.TestCase):
    def test_missing_rows_remain_unresolved(self):
        from benchmarks.real_road_legality import summarise,CATEGORIES
        r=summarise([],['a'],['dmn','reference'])
        self.assertEqual(r['counts']['dmn']['one_way']['unresolved'],1)
        self.assertEqual(r['shared_category_comparison']['one_way']['ranks'],[])

    def test_only_common_judged_cases_are_ranked(self):
        from benchmarks.real_road_legality import summarise,CATEGORIES
        rows=[{'engine':e,'case':'a','checks':{c:('pass' if e=='dmn' else 'unresolved') for c in CATEGORIES}} for e in ('dmn','reference')]
        r=summarise(rows,['a'],['dmn','reference'])
        self.assertEqual(r['shared_category_comparison']['one_way']['tested_each'],0)
        self.assertIsNone(r['overall_navigation_ranking'])

    def test_duplicate_rows_rejected(self):
        from benchmarks.real_road_legality import summarise,CATEGORIES
        row={'engine':'dmn','case':'a','checks':{c:'pass' for c in CATEGORIES}}
        with self.assertRaises(ValueError): summarise([row,row],['a'],['dmn'])

    def test_duplicate_cohort_rejected(self):
        from benchmarks.real_road_legality import summarise
        with self.assertRaises(ValueError): summarise([],['a','a'],['dmn'])

    def test_geometry_adapter_preserves_existing_response_validation(self):
        import io,json
        from unittest.mock import patch
        from benchmarks.real_english_speed import query
        points=[[-2.64,53.53],[-2.64,53.531]]
        with patch('benchmarks.real_english_speed.urlopen',return_value=io.BytesIO(json.dumps({'paths':[{'points':{'coordinates':points}}]}).encode())):
            self.assertEqual(query('graphhopper',{'source':'a','target':'b'},{'a':(53.53,-2.64),'b':(53.531,-2.64)},1234,1235,return_geometry=True)['coordinates'],points)

    def test_geometry_mode_requires_actual_native_implementation(self):
        import io,json
        from unittest.mock import patch
        from benchmarks.real_english_speed import query
        raw={'ok':True,'implementation':'python','coordinates':[[-2.64,53.53],[-2.64,53.531]]}
        with patch('benchmarks.real_english_speed.urlopen',return_value=io.BytesIO(json.dumps(raw).encode())):
            with self.assertRaises(ValueError): query('drivemate-native-cpp',{'source':'a','target':'b'},{'a':(53.53,-2.64),'b':(53.531,-2.64)},1234,None,return_geometry=True)

    def test_malformed_provider_shape_is_a_value_error(self):
        import io,json
        from unittest.mock import patch
        from benchmarks.real_english_speed import query
        with patch('benchmarks.real_english_speed.urlopen',return_value=io.BytesIO(b'{"paths":[null]}')):
            with self.assertRaises(ValueError): query('graphhopper',{'source':'a','target':'b'},{'a':(53.53,-2.64),'b':(53.531,-2.64)},1234,1235,return_geometry=True)

    def test_geometry_mode_disables_graphhopper_response_simplification(self):
        import io,json
        from unittest.mock import patch
        from urllib.parse import parse_qs,urlparse
        from benchmarks.real_english_speed import query
        points=[[-2.64,53.53],[-2.64,53.531]]
        with patch('benchmarks.real_english_speed.urlopen',return_value=io.BytesIO(json.dumps({'paths':[{'points':{'coordinates':points}}]}).encode())) as opened:
            query('graphhopper',{'source':'a','target':'b'},{'a':(53.53,-2.64),'b':(53.531,-2.64)},1234,1235,return_geometry=True)
            self.assertEqual(parse_qs(urlparse(opened.call_args.args[0]).query).get('way_point_max_distance'),['0'])

    def test_geometry_mode_preserves_graphhopper_import_nodes(self):
        import hashlib,tempfile
        from pathlib import Path
        from unittest.mock import patch,MagicMock
        from benchmarks.expanded_comparison import graphhopper
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);jar=folder/'control.jar';jar.write_bytes(b'authored test control')
            proc=MagicMock();proc.poll.return_value=None
            with patch('benchmarks.expanded_comparison.PIN',hashlib.sha512(jar.read_bytes()).hexdigest()), patch('benchmarks.expanded_comparison.subprocess.Popen',return_value=proc), patch('benchmarks.expanded_comparison.request',return_value={'version':'11.1'}):
                with graphhopper(jar,{'osm':b'<osm/>'},folder,preserve_geometry=True):
                    self.assertIn('routing.way_point_max_distance: 0',(folder/'config.yml').read_text())

if __name__=='__main__': unittest.main()
