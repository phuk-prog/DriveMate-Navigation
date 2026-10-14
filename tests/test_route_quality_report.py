import json
from pathlib import Path
import tempfile
import unittest
from benchmarks.expanded_fixture import suite
from benchmarks.route_quality_fixture import PROTOCOL,controls,optimum,judge_route
from benchmarks.route_quality_report import build
from benchmarks.route_quality import turns


def record(data):
    rows=[]
    for c in data['quality_cases']:
        gold=optimum(data,c);path=gold[1] if gold else None
        rows.append(c|judge_route(data,c,path,gold is None)|{'actual_ways':path,
                    'actual_turns':c['expected_turns'],
                    'instruction_status':'pass' if c['expected_turns'] is not None else None})
    return {'engine':'graphhopper','fresh_execution':True,'commit_sha':'test',
            'protocol':PROTOCOL,'dataset_sha256':data['dataset_sha256'],'cases':rows,
            'judge_controls':controls(data)}


class QualityReportTests(unittest.TestCase):
    def test_partial_timed_geometry_cannot_earn_a_sample(self):
        from benchmarks.route_quality_speed import validated_geometry
        data=suite();c=data['quality_cases'][0];path=optimum(data,c)[1]
        nodes=[c['start']]+[data['ways'][wid]['nodes'][-1] for wid in path]
        points=[[data['nodes'][n][1],data['nodes'][n][0]] for n in nodes]
        raw={'paths':[{'points':{'coordinates':points}}]}
        self.assertEqual(validated_geometry(data,c,raw)[0],path)
        raw['paths'][0]['points']['coordinates'].pop()
        with self.assertRaises(ValueError):validated_geometry(data,c,raw)

    def test_malformed_case_is_unresolved_without_aborting_engine(self):
        from unittest.mock import patch
        from benchmarks.route_quality import run
        data=suite()
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp,patch('benchmarks.route_quality.query',side_effect=AttributeError('Malformed synthetic response')):
            r=run('osrm',data,temp,None)
            self.assertEqual(len(r['cases']),64)
            self.assertTrue(all(c['status']=='unresolved' for c in r['cases']))

    def test_missing_engines_are_unresolved_not_passes_or_ranked(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp:
            Path(temp,'quality.json').write_text(json.dumps(record(suite())))
            r=build(temp,'test');c=r['categories'][0]
            self.assertEqual(c['counts']['graphhopper']['pass'],64)
            self.assertEqual(c['counts']['drivemate']['unresolved'],64)
            self.assertEqual(c['ranks']['native-road-import'],[])

    def test_false_distance_and_instruction_pass_stale_revision_missing_case_rejected(self):
        data=suite()
        for mutation in ('distance','instruction','revision','coverage'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory(dir=Path.cwd()) as temp:
                r=record(data)
                if mutation=='distance':r['cases'][0]['distance_ratio']=0
                elif mutation=='instruction':next(c for c in r['cases'] if c['expected_turns'])['actual_turns']=[]
                elif mutation=='revision':r['commit_sha']='old'
                else:r['cases'].pop()
                Path(temp,'quality.json').write_text(json.dumps(r))
                with self.assertRaises(ValueError):build(temp,'test')

    def test_pinned_turn_family_decoders_exclude_start_and_arrival(self):
        self.assertEqual(turns('graphhopper',{'paths':[{'instructions':[{'sign':s} for s in (0,-2,2,-2,4)]}]}),['left','right','left'])
        self.assertEqual(turns('osrm',{'routes':[{'legs':[{'steps':[{'maneuver':m} for m in
            ({'type':'depart','modifier':'left'},{'type':'turn','modifier':'left'},
             {'type':'turn','modifier':'right'},{'type':'arrive','modifier':'left'})]}]}]}),['left','right'])
        self.assertEqual(turns('valhalla',{'trip':{'legs':[{'maneuvers':[{'type':t} for t in (1,15,10,15,4)]}]}}),['left','right','left'])
