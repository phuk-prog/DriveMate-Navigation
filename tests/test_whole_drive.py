"""Whole candidate drives and immutable captured reference evidence checks."""
import unittest,json,hashlib,xml.etree.ElementTree as ET
from pathlib import Path
from benchmarks.whole_drive import fixture,prepared,cases,simulate,reference_requests
from benchmarks.whole_drive_reference import ways,gpx
from benchmarks.import_restriction_compare import PIN,decode_response

class WholeDriveTests(unittest.TestCase):
    def test_all_authored_complete_drives(self):
        p=prepared();rows=[]
        for case in cases():
            with self.subTest(case=case.ident):
                result=simulate(case,p);rows.append(result)
                self.assertEqual(result['status'],'pass',result['issues'])
                self.assertEqual(result['arrival'],'arrived')
        self.assertEqual(len(rows),16)
        out=Path('results/whole_drive');out.mkdir(exist_ok=True,parents=True)
        raw=fixture();(out/'drivemate.json').write_text(json.dumps({'classification':'Actual synthetic candidate simulation from full regression run',
                    'dataset_sha256':hashlib.sha256(raw).hexdigest(),'cases':rows,'passed':sum(r['status']=='pass' for r in rows),'failed':sum(r['status']!='pass' for r in rows)},indent=2))
    def test_exact_authored_node_routes_and_known_prohibitions(self):
        from engine.routing import RouteNotFound
        p=prepared()
        for c in reference_requests():
            with self.subTest(case=c['id']):
                if c['ways'] is None:
                    with self.assertRaises(RouteNotFound):p.route('osm:'+str(c['nodes'][0]),'osm:'+str(c['nodes'][1]))
                else:self.assertEqual(ways(p.route('osm:'+str(c['nodes'][0]),'osm:'+str(c['nodes'][1])).edge_ids),c['ways'])
    def test_fixture_order_valid_for_both_importers(self):
        root=ET.fromstring(fixture());ranks={'node':0,'way':1,'relation':2}
        types=[ranks[e.tag] for e in root]
        self.assertEqual(types,sorted(types))
    def test_preserved_actual_reference_is_same_map_and_raw_outputs_agree(self):
        path=Path('results/whole_drive/reference/comparison.json')
        if not path.exists():self.skipTest('Actual external run has not been provisioned; no fabricated substitute')
        s=json.loads(path.read_text())
        self.assertEqual(s['runtime_sha512'],PIN);self.assertTrue(s['fresh_execution'])
        self.assertEqual(s['dataset_sha256'],hashlib.sha256(fixture()).hexdigest())
        self.assertEqual(len(s['routes']),9);self.assertEqual(len(s['batch_matches']),4)
        for row in s['routes']:
            raw=json.loads((path.parent/(row['case']+'.json')).read_text())
            actual,rejected=decode_response(raw)
            self.assertEqual(actual,row['graphhopper_ways'])
            self.assertEqual(row['graphhopper_status'],'pass')
            if row['expected_ways'] is None:self.assertTrue(rejected)
            else:self.assertEqual(actual,row['expected_ways'])
        for row in s['batch_matches']:
            body=(path.parent/(row['case']+'_track.xml')).read_bytes()
            self.assertEqual(hashlib.sha256(body).hexdigest(),row['track_sha256'])
            raw=json.loads((path.parent/(row['case']+'_match.json')).read_text())
            actual,_=decode_response(raw)
            self.assertEqual(actual,row['expected_observed_ways'])
            self.assertEqual(row['graphhopper_batch_status'],'pass')
    def test_ten_external_targets_never_score_missing_systems(self):
        from benchmarks.ten_system_matrix import SYSTEMS,TARGETS
        self.assertEqual(len(SYSTEMS),10);self.assertEqual(len({s[0] for s in SYSTEMS}),10)
        self.assertIn('instruction_timing',TARGETS);self.assertIn('gps_loss_recovery',TARGETS)
        self.assertTrue(all(blocker for name,_,blocker in SYSTEMS if name!='GraphHopper'))

if __name__=='__main__':unittest.main()
