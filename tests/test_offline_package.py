"""Synthetic offline package contract; not a native/device offline test."""
import importlib.util
import unittest

class OfflinePackageTests(unittest.TestCase):
    def require_capability(self):
        self.assertIsNotNone(importlib.util.find_spec('map_data.offline'),
                             'Verified offline package activation must exist')

    def test_frozen_eighteen_cases(self):
        self.require_capability()
        from benchmarks.offline_integrity_trial import run_dmn
        r=run_dmn()
        self.assertEqual(len(r['cases']),18)
        self.assertEqual([(c['case_id'],c['outcome']) for c in r['cases']],
                         [(c['case_id'],'PASS') for c in r['cases']])

    def test_unisolated_execution_cannot_receive_offline_score(self):
        self.require_capability()
        from benchmarks.offline_integrity_trial import run_dmn,coverage
        r=run_dmn();r['network']={'isolated':False,'reason':'explicit negative scoring control'}
        row=coverage(r)['rows'][0]
        self.assertIsNone(row['rank'])
        self.assertIsNone(row['score_out_of_ten'])

    def test_manifest_mutation_does_not_mutate_active_snapshot(self):
        self.require_capability()
        from benchmarks.offline_integrity_trial import inputs
        from map_data.offline import OfflineMapStore
        _,_,variants=inputs();payload,manifest=variants['A']
        s=OfflineMapStore();info=s.activate(payload,manifest)
        manifest['required_nodes'].clear();manifest['provenance']['snapshot']='changed';manifest['sha256']='0'*64
        self.assertEqual(s.info,info)
        self.assertEqual(s.info.snapshot,'synthetic-v1')
        self.assertEqual(s.info.required_nodes,('osm:1','osm:3'))
        self.assertEqual(s.route('osm:1','osm:3').package_sha256,info.sha256)

    def test_active_info_is_immutable(self):
        from dataclasses import FrozenInstanceError
        from benchmarks.offline_integrity_trial import inputs
        from map_data.offline import OfflineMapStore
        _,_,variants=inputs();s=OfflineMapStore();info=s.activate(*variants['A'])
        with self.assertRaises(FrozenInstanceError):info.sha256='changed'

    def test_payload_limit_boundaries(self):
        from benchmarks.offline_integrity_trial import inputs
        from map_data.offline import OfflineMapStore,PackageValidationError
        _,_,variants=inputs();raw,m=variants['A']
        self.assertEqual(OfflineMapStore(max_payload_bytes=len(raw)).activate(raw,m).sha256,m['sha256'])
        with self.assertRaises(PackageValidationError):OfflineMapStore(max_payload_bytes=len(raw)-1).activate(raw,m)
        for limit in (0,-1,True,6000001,float('nan')):
            with self.subTest(limit=limit),self.assertRaises(ValueError):OfflineMapStore(max_payload_bytes=limit)

    def test_strict_manifest_and_mutable_payload_rejected(self):
        from copy import deepcopy
        from benchmarks.offline_integrity_trial import inputs
        from map_data.offline import OfflineMapStore,PackageValidationError
        _,_,variants=inputs();raw,m=variants['A'];s=OfflineMapStore();old=s.activate(raw,m)
        for change in ({'schema_version':True},{'byte_length':True},{'sha256':m['sha256'].upper()},{'required_nodes':[]},{'required_nodes':['osm:1','osm:1']},{'unexpected':1},{'provenance':{'region':'bad'}}):
            with self.subTest(change=change),self.assertRaises(PackageValidationError):s.activate(raw,deepcopy(m)|change)
            self.assertEqual(s.info,old)
        with self.assertRaises(PackageValidationError):s.activate(bytearray(raw),m)
        self.assertEqual(s.info,old)

    def test_old_routes_retain_original_package_identity(self):
        from benchmarks.offline_integrity_trial import inputs
        from map_data.offline import OfflineMapStore
        _,_,v=inputs();s=OfflineMapStore();a=s.activate(*v['A']);old=s.route('osm:1','osm:3')
        b=s.activate(*v['B']);new=s.route('osm:1','osm:3')
        self.assertEqual(old.package_sha256,a.sha256)
        self.assertEqual(new.package_sha256,b.sha256)
        self.assertNotEqual(old.package_sha256,new.package_sha256)
        self.assertEqual(old.route.edge_ids,('w:10:0:f','w:30:0:f','w:40:0:f','w:50:0:f'))

    def test_incomplete_scorecard_rejected(self):
        from benchmarks.offline_integrity_trial import coverage,run_dmn
        r=run_dmn();r['cases'].pop()
        with self.assertRaises(ValueError):coverage(r)
