"""Conservative raw-OSM path judge, independent of DMN's importer and search.

This checks a dated map's supported rules, NOT independently observed UK law.
Unattributable geometry and unsupported semantics remain unresolved. No legal
path is selected to repair or explain a provider's returned geometry.
"""
import argparse
from contextlib import ExitStack
from hashlib import sha256
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

CATEGORIES = ('route_response','connectivity','one_way','access','turn_restrictions',
              'roundabout_direction','independent_uk_legality')


def judge(raw, points):
    root = ET.fromstring(raw)
    nodes = {n.attrib['id']:(float(n.attrib['lon']),float(n.attrib['lat'])) for n in root.findall('node')}
    tags = lambda item: {t.attrib['k']:t.attrib['v'] for t in item.findall('tag')}
    node_tags = {n.attrib['id']:tags(n) for n in root.findall('node')}
    ways, segments = {}, {}
    for w in root.findall('way'):
        t = tags(w)
        if 'highway' not in t:
            continue
        wid = w.attrib['id']
        ways[wid] = t
        ids = [n.attrib['ref'] for n in w.findall('nd')]
        for a,b in zip(ids,ids[1:]):
            if a not in nodes or b not in nodes or a == b:
                continue
            segments.setdefault((a,b),[]).append((wid,True))
            segments.setdefault((b,a),[]).append((wid,False))
    checks = {c:'unresolved' for c in CATEGORIES}
    if not isinstance(points,list) or len(points)<2:
        checks['route_response']='fail'
        return checks
    if any(not isinstance(p,(list,tuple)) or len(p)!=2 or
           any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) for v in p) for p in points):
        checks['route_response']='fail'
        return checks
    checks['route_response']='pass'
    path=[]
    for lon,lat in points:
        matches=[n for n,(x,y) in nodes.items() if math.hypot((lon-x)*111195*math.cos(math.radians(lat)),(lat-y)*111195)<=1.5]
        if len(matches)!=1:
            return checks
        if not path or path[-1]!=matches[0]:
            path.append(matches[0])
    if len(path)<2:
        return checks
    attributed=[]
    for a,b in zip(path,path[1:]):
        choices=segments.get((a,b),[])
        if len(choices)!=1:
            return checks
        attributed.append((a,b,*choices[0]))
    checks['connectivity']='pass'
    direction=[]; access=[]; roundabout=[]
    def access_status(t):
        if t.get('locked') not in (None,'no'):
            return 'unresolved'
        if any(k.startswith(('maxheight','maxweight','maxwidth','maxlength','maxaxleload','maxweightrating')) for k in t):
            return 'unresolved'
        if any(':conditional' in k for k in t) or any(k.startswith(('motorcar:','motor_vehicle:','vehicle:','access:')) for k in t):
            return 'unresolved'
        value=next((t[k] for k in ('motorcar','motor_vehicle','vehicle','access') if k in t),None)
        if value == 'no': return 'fail'
        if value in ('yes','permissive','designated'): return 'pass'
        if 'barrier' in t: return 'unresolved'
        if value is not None: return 'unresolved'  # destination/customer/emergency purpose unknown
        if t.get('highway') in ('motorway','motorway_link','trunk','trunk_link','primary','primary_link',
                              'secondary','secondary_link','tertiary','tertiary_link','unclassified','residential','living_street','service'):
            return 'pass'
        return 'unresolved'
    for a,b,wid,forward in attributed:
        t=ways[wid]
        value=t.get('oneway:motorcar',t.get('oneway:motor_vehicle',t.get('oneway',
            'yes' if t.get('junction')=='roundabout' or t.get('highway')=='motorway' else 'no')))
        if any(k.startswith('oneway:') and k not in ('oneway:motorcar','oneway:motor_vehicle') for k in t):
            state='unresolved'
        elif value in ('yes','1','true'): state='pass' if forward else 'fail'
        elif value=='-1': state='fail' if forward else 'pass'
        elif value in ('no','0','false'): state='pass'
        else: state='unresolved'
        direction.append(state)
        if t.get('junction')=='roundabout': roundabout.append(state)
        access.append(access_status(t))
        for n in (a,b):
            nt=node_tags[n]
            if 'barrier' in nt or any(k.startswith(('access','motorcar','motor_vehicle','vehicle','maxheight','maxweight','maxwidth','maxlength','maxaxleload','maxweightrating','locked')) for k in nt):
                node_state=access_status({k:v for k,v in nt.items() if k!='highway'})
                # A gate/bollard without explicit motor permission is unknown.
                access.append(node_state)
    combine=lambda values: 'fail' if 'fail' in values else 'unresolved' if not values or 'unresolved' in values else 'pass'
    checks['one_way']=combine(direction)
    checks['access']=combine(access)
    checks['roundabout_direction']=combine(roundabout)
    restrictions=[]
    for relation in root.findall('relation'):
        t=tags(relation)
        if t.get('type')!='restriction': continue
        members=relation.findall('member')
        frm=[m.attrib['ref'] for m in members if m.get('role')=='from' and m.get('type')=='way']
        to=[m.attrib['ref'] for m in members if m.get('role')=='to' and m.get('type')=='way']
        via=[m.attrib['ref'] for m in members if m.get('role')=='via' and m.get('type')=='node']
        member_ways=[m.attrib['ref'] for m in members if m.get('type')=='way']
        touched=any(wid in member_ways for _,_,wid,_ in attributed)
        if not touched: continue
        if set(t.get('except','').replace(' ','').split(';')) & {'motorcar','motor_vehicle','vehicle'}: continue
        kind=t.get('restriction:motorcar',t.get('restriction:motor_vehicle',t.get('restriction','')))
        supported=kind in ('no_left_turn','no_right_turn','no_straight_on','no_u_turn',
                          'only_left_turn','only_right_turn','only_straight_on','only_u_turn')
        if len(frm)!=1 or len(to)!=1 or len(via)!=1 or len(members)!=3 or not supported or any(':conditional' in k for k in t) or t.get('except'):
            restrictions.append('unresolved');continue
        for before,after in zip(attributed,attributed[1:]):
            if before[2]!=frm[0] or before[1]!=via[0]: continue
            matches=after[2]==to[0]
            if frm==to:
                if kind.endswith('u_turn'): matches=matches and after[1]==before[0]
                else: restrictions.append('unresolved');continue
            violated=matches if kind.startswith('no_') else not matches
            restrictions.append('fail' if violated else 'pass')
    checks['turn_restrictions']=combine(restrictions)
    return checks


def summarise(rows, cases, engines):
    if not cases or not engines or len(set(cases))!=len(cases) or len(set(engines))!=len(engines):
        raise ValueError('Nonempty unique cohort and engines required')
    expected={(e,c) for e in engines for c in cases}
    indexed={}
    for row in rows:
        key=row['engine'],row['case']
        if key not in expected or key in indexed: raise ValueError('Unknown/duplicate row')
        if set(row['checks'])!=set(CATEGORIES) or any(s not in ('pass','fail','unresolved') for s in row['checks'].values()):
            raise ValueError('Invalid checks')
        indexed[key]=row
    counts={e:{c:{s:sum(indexed.get((e,k),{}).get('checks',{}).get(c,'unresolved')==s for k in cases)
                       for s in ('pass','fail','unresolved')} for c in CATEGORIES} for e in engines}
    shared={}
    for category in CATEGORIES:
        cohort=[c for c in cases if all(indexed.get((e,c),{}).get('checks',{}).get(category) in ('pass','fail') for e in engines)]
        scores={e:sum(indexed[e,c]['checks'][category]=='pass' for c in cohort) for e in engines}
        shared[category]={'tested_each':len(cohort),'correct':scores,'ranks':[
            {'engine':e,'rank':1+sum(v>scores[e] for v in scores.values())} for e in engines] if cohort else []}
    return {'counts':counts,'shared_category_comparison':shared,'rows_expected':len(expected),'rows_received':len(rows),
            'overall_navigation_ranking':None,'independent_uk_legality_verified':False,'rows':rows}


def main():
    from benchmarks.real_english_speed import query,start_candidate,graphhopper
    from benchmarks.real_english_journey import select_case_cohorts
    from engine.reconciled import prepare_navigation
    from map_data import Provenance,import_osm_xml
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',type=Path,required=True)
    ap.add_argument('--graphhopper-jar',type=Path,required=True)
    ap.add_argument('--snapshot',required=True)
    ap.add_argument('--cases',type=int,default=100)
    args=ap.parse_args()
    if not args.input.resolve().is_relative_to(Path('results').resolve()) or args.input.stat().st_size>6000000 or not 8<=args.cases<=100:
        ap.error('Bounded public map under results/ and 8..100 cases required')
    raw=args.input.read_bytes()
    imported=import_osm_xml(raw,provenance=Provenance('Greater Manchester, England',args.snapshot,'Geofabrik historic public OSM PBF','© OpenStreetMap contributors (ODbL 1.0)'))
    prepared=prepare_navigation(imported.graph,imported.coordinates)
    cases=select_case_cohorts(prepared,imported.graph,args.cases)
    engines=['drivemate-native-cpp','graphhopper','osrm-mld','osrm-ch','valhalla']
    rows=[];out=Path('results/legality');out.mkdir(parents=True,exist_ok=True)
    with ExitStack() as stack:
        gh=stack.enter_context(graphhopper(args.graphhopper_jar,{'osm':raw},Path('results/real-england/graphhopper'),preserve_geometry=True))
        server,thread,native=start_candidate(prepared,Path('navigation_core/native/router'))
        stack.callback(lambda:(server.shutdown(),server.server_close(),thread.join(timeout=3),native.close()))
        for i,case in enumerate(cases):
            for engine in (engines if i%2 else list(reversed(engines))):
                row={'engine':engine,'case':case['id']}
                try:
                    result=query(engine,case,imported.coordinates,server.server_port,gh,return_geometry=True)
                    row['checks']=judge(raw,result['coordinates'])
                    row['geometry_points']=len(result['coordinates'])
                except (OSError,ValueError,KeyError,TypeError,IndexError) as exc:
                    row['checks']={c:'unresolved' for c in CATEGORIES}
                    row['checks']['route_response']='fail'
                    row['error']=type(exc).__name__+': '+str(exc)[:160]
                rows.append(row)
                (out/'rows.json').write_text(json.dumps(rows,indent=2)+'\n')
    result=summarise(rows,[c['id'] for c in cases],engines)
    result.update({'source_xml_sha256':sha256(raw).hexdigest(),'source_snapshot':args.snapshot,
                   'cohort_sha256':sha256(json.dumps([(c['id'],c['source'],c['target']) for c in cases],separators=(',',':')).encode()).hexdigest(),
                   'attribution':'© OpenStreetMap contributors, ODbL 1.0',
                   'limitations':['Dated OSM rules, not independently observed current UK legal truth.',
                    'Exact unique OSM-node/segment attribution only; simplified, offset, ambiguous or partial geometry is unresolved.',
                    'Via-way, conditional, unusual access and unsupported restriction semantics remain unresolved.',
                    'Different car costing/profiles; no route-cost or speed ranking.',
                    'The original 100 Wigan endpoints are retained; targeted synthetic fault controls are separate.']})
    (out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    lines=['# Real Wigan map-rule comparison','', 'Full navigation and independently verified UK legality: unresolved.','',
           '| Engine | Category | Correct / judged | Failed | Unresolved / planned |','|---|---|---:|---:|---:|']
    for engine,counts in result['counts'].items():
        for category,c in counts.items(): lines.append(f"| {engine} | {category} | {c['pass']}/{c['pass']+c['fail']} | {c['fail']} | {c['unresolved']}/{len(cases)} |")
    lines+=['',*result['limitations']]
    (out/'COMPARISON.md').write_text('\n'.join(lines)+'\n')
    print('LEGALITY_SUMMARY='+json.dumps({k:v for k,v in result.items() if k!='rows'}))
    # Preserve genuine map-rule failures as red, while unresolved stays explicit.
    return int(len(rows)!=len(engines)*len(cases) or any(c['fail'] for e in result['counts'].values() for c in e.values()))

if __name__=='__main__': raise SystemExit(main())
