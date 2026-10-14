"""Matched synthetic batch trace faults, separate from live GPS controllers.

Four real batch APIs receive the same quantized coordinates and declared 3m
accuracy, without clocks. Author-defined underlying paths supply truth. No
physical sensor calibration, lane identity or real driving data is implied.
"""
import copy
import hashlib
import json
import math
from pathlib import Path
import subprocess
import urllib.error
import urllib.request
from urllib.parse import urlencode
import xml.etree.ElementTree as ET
from benchmarks.expanded_comparison import clean_trace, candidate_trace, shape_roads
from benchmarks.cloud_reference import polyline6

PROTOCOL='coordinate-only-batch-faults-v1'
BATCH=('graphhopper','osrm','osrm-ch','valhalla')
FAULTS=('jitter_2m','spike_40m','gap_3fix','compound')
BASE_NAMES=('no_chained_turn','only_chained_turn','no_inside_via_reset',
            'asymmetric_ring_exit_5','compound_no_only_detour')


def canonical_input(samples):
    return {'coordinates':[[round(s['lat'],7),round(s['lon'],7)] for s in samples],
            'accuracy_m':3,'timing':'not supplied'}


def input_hash(samples):
    return hashlib.sha256(json.dumps(canonical_input(samples),sort_keys=True,separators=(',',':')).encode()).hexdigest()


def clocked_input_hash(samples):
    body=[{'lat':s['lat'],'lon':s['lon'],'t':s['t'],'accuracy_m':3} for s in samples]
    return hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def on_segment(point,a,b):
    east=111195.0802*math.cos(math.radians(a[0]))
    dx,dy=(b[1]-a[1])*east,(b[0]-a[0])*111195.0802
    px,py=(point['lon']-a[1])*east,(point['lat']-a[0])*111195.0802
    sq=dx*dx+dy*dy;q=(px*dx+py*dy)/sq
    return 0<=q<=1 and math.hypot(px-q*dx,py-q*dy)<.05


def gap_window(data,samples,expected):
    """Remove only three interior fixes bounded by observations on ONE segment.

    This deliberately does not erase a complete turn or invent certainty about
    an unobserved junction. No candidate matcher or routing output is consulted.
    """
    choices=[]
    for i in range(1,len(samples)-3):
        anchors=samples[i-1:i+4]
        for wid in expected:
            nodes=data['ways'][wid]['nodes']
            for a,b in zip(nodes,nodes[1:]):
                if all(on_segment(s,data['nodes'][a],data['nodes'][b]) for s in anchors):
                    choices.append((abs(i-len(samples)/2),i,wid,a,b))
    if not choices: raise ValueError('No independently bounded three-fix gap')
    _,i,wid,a,b=min(choices)
    return i,{'way':wid,'segment_nodes':[a,b],'removed_indices':[i,i+1,i+2],
              'bound':'Clean-control anchors and removed underlying points lie on one authored segment'}


def scenarios(data):
    result=[]
    for c in data['cases']:
        if c['id'].split('/')[-1] not in BASE_NAMES: continue
        expected,base=clean_trace(data,c)
        gap,gap_proof=gap_window(data,base,expected)
        for fault in FAULTS:
            samples=copy.deepcopy(base);operations=[]
            if fault in ('jitter_2m','compound'):
                for i,s in enumerate(samples):
                    # Alternating east/north error of magnitude exactly 2m.
                    phase=(i%4)*math.pi/2
                    s['lat']+=2*math.sin(phase)/111195.0802
                    s['lon']+=2*math.cos(phase)/(111195.0802*math.cos(math.radians(s['lat'])))
                operations.append('Deterministic alternating 2m spatial error')
            if fault in ('spike_40m','compound'):
                spike=max(1,len(samples)//3)
                if gap<=spike<gap+3: spike=max(1,gap-1)
                samples[spike]['lat']+=40/111195.0802
                operations.append(f'One northward 40m outlier at original index {spike}')
            if fault in ('gap_3fix','compound'):
                del samples[gap:gap+3]
                operations.append('Three interior fixes removed on one independently verified segment')
            for s in samples:
                s['lat']=round(s['lat'],7);s['lon']=round(s['lon'],7)
            result.append({'id':c['id']+'/'+fault,'base_case':c['id'],'split':c['split'],
                'fault':fault,'expected_ways':expected,'samples':samples,'baseline_samples':base,
                'baseline_expected_ways':expected,'operations':operations,
                'gap_proof':gap_proof if fault in ('gap_3fix','compound') else None,
                'input_sha256':input_hash(samples),'baseline_input_sha256':input_hash(base)})
    return result


def judge_sequence(expected,actual,decode_status):
    if decode_status=='unresolved': return {'status':'unresolved','issue':'Adapter/runtime output cannot establish one matched path'}
    if decode_status=='fail': return {'status':'fail','issue':'Engine rejected or split the trace; no complete reconstruction'}
    if actual!=expected: return {'status':'fail','issue':'Matched road sequence differs from independent underlying path'}
    return {'status':'pass','issue':None}


def controls():
    clean=[11,22,33,44]
    bad=[('omitted_road',[11,33,44],'pass'),('extra_road',[11,22,77,33,44],'pass'),
         ('reverse_order',[44,33,22,11],'pass'),('false_no_match',None,'fail')]
    return [{'case':name,'baseline_passed':judge_sequence(clean,clean,'pass')['status']=='pass',
             'detected':judge_sequence(clean,path,status)['status']=='fail',
             'scope':'Deliberate judge-output control, not a competitor mutation'} for name,path,status in bad]


def call_batch(engine,samples,http=None):
    common=canonical_input(samples);coords=common['coordinates']
    if engine=='graphhopper':
        root=ET.Element('gpx',version='1.1',creator='original-synthetic-faults',xmlns='http://www.topografix.com/GPX/1/1')
        segment=ET.SubElement(ET.SubElement(root,'trk'),'trkseg')
        for lat,lon in coords: ET.SubElement(segment,'trkpt',lat=str(lat),lon=str(lon))
        params={'profile':'car','details':'osm_way_id','instructions':'false','points_encoded':'false','gps_accuracy':'3'}
        url=urllib.request.Request(f'http://127.0.0.1:{http}/match?'+urlencode(params),
            data=ET.tostring(root,encoding='utf-8',xml_declaration=True),headers={'Content-Type':'application/gpx+xml'})
    elif engine in ('osrm','osrm-ch'):
        points=';'.join(f'{lon:.7f},{lat:.7f}' for lat,lon in coords)
        params={'geometries':'geojson','overview':'full','steps':'false','tidy':'false',
                'radiuses':';'.join('3' for _ in coords)}
        url='http://127.0.0.1:'+('5001' if engine=='osrm-ch' else '5000')+'/match/v1/driving/'+points+'?'+urlencode(params)
    else:
        payload={'shape':[{'lat':lat,'lon':lon} for lat,lon in coords],
                 'costing':'auto','shape_match':'map_snap','shape_format':'polyline6',
                 'use_timestamps':False,'trace_options':{'gps_accuracy':3}}
        url=urllib.request.Request('http://127.0.0.1:8002/trace_route',data=json.dumps(payload).encode(),
                                  headers={'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(url,timeout=20) as response: return json.load(response)
    except urllib.error.HTTPError as error: return json.loads(error.read())


def parse_batch(engine,data,raw):
    if not isinstance(raw,dict): return None,'unresolved'
    if engine in ('osrm','osrm-ch'):
        if raw.get('code') in ('NoMatch','NoSegment'): return None,'fail'
        if raw.get('code')!='Ok': return None,'unresolved'
        matches=raw.get('matchings')
        if not isinstance(matches,list): return None,'unresolved'
        if len(matches)!=1: return None,'fail'
        if not isinstance(matches[0],dict) or not isinstance(matches[0].get('geometry'),dict): return None,'unresolved'
        coords=matches[0]['geometry'].get('coordinates')
        if not isinstance(coords,list) or any(not isinstance(v,(list,tuple)) or len(v)!=2 for v in coords): return None,'unresolved'
        points=[(v[1],v[0]) for v in coords]
    elif engine=='graphhopper':
        paths=raw.get('paths')
        if not paths:
            # The local matcher uses this class when it cannot connect the
            # finite submitted observations. Other errors remain unavailable.
            hints=raw.get('hints',())
            rejected=isinstance(hints,list) and any(isinstance(h,dict) and 'IllegalArgumentException' in str(h.get('details','')) for h in hints)
            return None,'fail' if rejected else 'unresolved'
        if not isinstance(paths,list): return None,'unresolved'
        if len(paths)!=1: return None,'fail'
        if not isinstance(paths[0],dict) or not isinstance(paths[0].get('points'),dict): return None,'unresolved'
        coords=paths[0]['points'].get('coordinates')
        if not isinstance(coords,list) or any(not isinstance(v,(list,tuple)) or len(v)!=2 for v in coords): return None,'unresolved'
        points=[(v[1],v[0]) for v in coords]
    else:
        if raw.get('error_code') in (171,172,442,443,444): return None,'fail'
        if not isinstance(raw.get('trip'),dict): return None,'unresolved'
        legs=raw['trip'].get('legs')
        if not isinstance(legs,list) or not legs: return None,'unresolved'
        if any(not isinstance(leg,dict) or not isinstance(leg.get('shape'),str) for leg in legs): return None,'unresolved'
        try: points=[p for leg in legs for p in polyline6(leg['shape'])]
        except ValueError: return None,'unresolved'
    if any(not isinstance(v,(tuple,list)) or len(v)!=2 or
           any(not isinstance(n,(int,float)) or isinstance(n,bool) or not math.isfinite(n) for n in v) for v in points):
        return None,'unresolved'
    if any(abs(v[0])>90 or abs(v[1])>180 for v in points): return None,'unresolved'
    return shape_roads(data,points)


def recovery_diagnostics(data,p):
    """Paired candidate-only controller probe; never mixed with batch ranks."""
    from gps.recovery import RecoveringGpsJourney
    from gps.matching import Fix
    from benchmarks.whole_drive_reference import ways
    records=[]
    for row in scenarios(data):
        if row['fault']!='compound' or not row['base_case'].endswith('asymmetric_ring_exit_5'): continue
        for variant,samples in (('clean_control',row['baseline_samples']),('compound',row['samples'])):
            seen=[];frames=[];advanced=0
            try:
                target='w:'+str(row['expected_ways'][-1])+':0:f'
                journey=RecoveringGpsJourney(p,target,990000)
                for i,s in enumerate(samples):
                    previous=journey.snapshot
                    u=journey.observe(Fix(s['lat'],s['lon'],s['t'],3),s['t'])
                    m=u.match
                    if m and m.status=='matched' and u.status in ('tracking','recovered','history_uncertain'):
                        seen.append(m.road)
                    if m and m.status!='matched' and journey.snapshot!=previous: advanced+=1
                    frames.append({'sample':i,'status':u.status,'match_status':None if m is None else m.status,
                                   'guidance_available':u.guidance_available})
                path=ways(seen);status='pass' if path==row['expected_ways'] and advanced==0 else 'fail'
                issue=None if status=='pass' else 'Missing expected accepted-road sequence or snapshot advanced on rejected fix'
            except (OSError,ValueError,KeyError) as exc:
                path=None;status='unresolved';issue=f'{type(exc).__name__}: {str(exc)[:160]}'
            records.append({'case':row['base_case']+'/'+variant,'status':status,'issue':issue,
                'input_sha256':clocked_input_hash(samples),'sample_count':len(samples),
                'expected_ways':row['expected_ways'],'actual_ways':path,'snapshot_advances_on_rejection':advanced,
                'frames':frames,'scope':'Candidate-only recovery controller; no competitor equivalent'})
    return records


def run(engine,data,out,p,*,http=None):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    rows=scenarios(data);baselines=[];baseline_status={};results=[];streaming=[]
    bases={r['base_case']:r for r in rows}
    if engine in BATCH:
        for case,row in bases.items():
            try:
                raw=call_batch(engine,row['baseline_samples'],http)
                (out/(case.replace('/','_')+'_fault_control.json')).write_text(json.dumps(raw,indent=2))
                actual,status=parse_batch(engine,data,raw)
                outcome=judge_sequence(row['expected_ways'],actual,status)
            except (OSError,ValueError,KeyError,IndexError,TypeError,AttributeError) as exc:
                actual=None;outcome={'status':'unresolved','issue':f'{type(exc).__name__}: {str(exc)[:160]}'}
            baseline_status[case]=outcome['status']
            baselines.append({'case':case,**outcome,'input_sha256':row['baseline_input_sha256'],
                              'expected_ways':row['expected_ways'],'actual_ways':actual})
    for row in rows:
        actual=None
        if engine not in BATCH:
            outcome={'status':'not_supported','issue':'No equivalent batch reconstruction interface'}
            if engine=='drivemate':
                path,rejected=candidate_trace(p,row['samples'])
                streaming.append({'case':row['id'],'fault':row['fault'],'expected_ways':row['expected_ways'],
                    'input_sha256':clocked_input_hash(row['samples']),
                    'actual_ways':path,'sequence_equal':path==row['expected_ways'],
                    'rejected_samples':rejected,'sample_count':len(row['samples']),
                    'scope':'Streaming matcher diagnostics, not a batch or live recovery-controller rank'})
        else:
            try:
                raw=call_batch(engine,row['samples'],http)
                (out/(row['id'].replace('/','_')+'_fault_match.json')).write_text(json.dumps(raw,indent=2))
                actual,status=parse_batch(engine,data,raw)
                outcome=judge_sequence(row['expected_ways'],actual,status)
                if baseline_status[row['base_case']]!='pass':
                    outcome={'status':'unresolved','issue':'Same-protocol clean baseline did not pass; fault effect cannot be isolated'}
            except (OSError,ValueError,KeyError,IndexError,TypeError,AttributeError) as exc:
                outcome={'status':'unresolved','issue':f'{type(exc).__name__}: {str(exc)[:160]}'}
        results.append({k:row[k] for k in ('id','base_case','split','fault','expected_ways','operations','gap_proof','input_sha256')}|
                       outcome|{'actual_ways':actual,'sample_count':len(row['samples'])})
    record={'engine':engine,'protocol':PROTOCOL,'fresh_execution':True,'dataset_sha256':data['dataset_sha256'],
        'commit_sha':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'driving_side':data['driving_side'],'batch_interface':engine in BATCH,
        'cases':results,'clean_controls':baselines,'judge_controls':controls(),'streaming_diagnostics':streaming,
        'recovery_diagnostics':recovery_diagnostics(data,p) if engine=='drivemate' else [],
        'limits':['Synthetic spatial errors, not measured sensor calibration',
                  'No clocks in batch inputs; no live controller/recovery delay rank',
                  'Gap removes only interior points on one author segment; unseen turns remain untested']}
    (out/'faults.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({'fault_engine':engine,'passed':sum(r['status']=='pass' for r in results),
        'failed':sum(r['status']=='fail' for r in results),'unresolved':sum(r['status']=='unresolved' for r in results),
        'not_supported':sum(r['status']=='not_supported' for r in results),'cases':len(results)}))
    return record
