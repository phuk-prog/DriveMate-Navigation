"""Original whole-drive synthetic fixtures and targeted reference requests.

No real city, proprietary maps or personal driving data. Expected road sequences
are authored independently of the candidate router. External references execute
separately; this module never fabricates their output or scores internal oracles
as competitors. All state/advice checks use the actual local navigation modules.
"""
from dataclasses import dataclass
from datetime import datetime,timezone
from math import hypot
from pathlib import Path
import json,hashlib,xml.etree.ElementTree as ET
from engine.reconciled import prepare_navigation
from engine.routing import RouteNotFound
from gps.matching import Fix
from gps.recovery import RecoveringGpsJourney
from guidance.timing import InstructionScheduler
from map_data.osm_xml import import_osm_xml,Provenance
from benchmarks.roundabout_reference import fixture as ring_fixture

@dataclass(frozen=True)
class DriveCase:
    ident: str
    roads: tuple
    target: str
    fault: str = 'clean'
    expected_exit: int | None = None
    expect_reroute: bool = False

def fixture():
    root=ET.Element('osm',version='0.6',generator='original-synthetic-whole-drive')
    points={1:(0,-.005),2:(0,0),3:(.00045,0),4:(.00045,.003),5:(0,.001),6:(.00135,0),
            8:(.00018,-.005),9:(.00018,.001),20:(.02,0),21:(.02,.001),22:(.02,.002),
            23:(.02,.003),24:(.02,.004),25:(.021,.001)}
    for n,(lat,lon) in points.items():ET.SubElement(root,'node',id=str(n),lat=str(lat),lon=str(lon),version='1')
    def way(n,refs,tags=()):
        w=ET.SubElement(root,'way',id=str(n),version='1')
        for ref in refs:ET.SubElement(w,'nd',ref=str(ref))
        for k,v in [('highway','residential'),('oneway','yes'),('maxspeed','36'),('name','synthetic-'+str(n))]+list(tags):ET.SubElement(w,'tag',k=k,v=v)
    way(10,(1,2),(('lanes','3'),('turn:lanes','left|through|right')))
    for n,refs in [(11,(2,3)),(12,(3,4)),(13,(2,5)),(14,(3,6)),(15,(5,3)),(16,(8,9)),
                   (30,(20,21)),(31,(21,22,23)),(32,(23,24)),(33,(21,25,23))]:way(n,refs)
    relation=ET.SubElement(root,'relation',id='1',version='1')
    for kind,ref,role in [('way',11,'from'),('node',3,'via'),('way',14,'to')]:ET.SubElement(relation,'member',type=kind,ref=str(ref),role=role)
    ET.SubElement(relation,'tag',k='type',v='restriction');ET.SubElement(relation,'tag',k='restriction',v='no_straight_on')
    relation=ET.SubElement(root,'relation',id='2',version='1')
    for ref,role in [(30,'from'),(31,'via'),(32,'to')]:ET.SubElement(relation,'member',type='way',ref=str(ref),role=role)
    ET.SubElement(relation,'tag',k='type',v='restriction');ET.SubElement(relation,'tag',k='restriction',v='no_straight_on')
    raw,_=ring_fixture();ring=ET.fromstring(raw)
    for element in ring:
        element.set('id',str(int(element.get('id'))+1000))
        if element.tag=='node':
            element.set('lat',str(float(element.get('lat'))+.01));element.set('lon',str(float(element.get('lon'))+.01))
        for nd in element.findall('nd'):nd.set('ref',str(int(nd.get('ref'))+1000))
        root.append(element)
    root[:]=sorted(root,key=lambda e:({'node':0,'way':1,'relation':2}[e.tag],int(e.get('id'))))
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)

def prepared(raw=None):
    raw=raw or fixture()
    m=import_osm_xml(raw,provenance=Provenance('synthetic full-drive dataset','v1','independently authored fixtures','OpenStreetMap contributors'))
    return prepare_navigation(m.graph,m.coordinates)

def cases():
    urban=('w:10:0:f','w:11:0:f','w:12:0:f');rows=[]
    for fault in ('clean','tunnel','bad_burst','stopped_lights','jump','parallel','late_delivery','restart'):
        rows.append(DriveCase('urban_'+fault,urban,urban[-1],fault))
    rows.append(DriveCase('urban_skipped_recovery',urban,urban[-1],'skipped'))
    rows.append(DriveCase('legal_wrong_turn_reroute',('w:10:0:f','w:13:0:f','w:15:0:f','w:12:0:f'),'w:12:0:f',expect_reroute=True))
    rows.append(DriveCase('via_way_ban_detour',('w:30:0:f','w:33:0:f','w:33:1:f','w:32:0:f'),'w:32:0:f'))
    for ordinal,end in enumerate((2,4,6,7),1):
        roads=('w:1010:0:f',)+tuple(f'w:1100:{i}:f' for i in range(end))+(f'w:{1200+end}:0:f',)
        rows.append(DriveCase('ring_exit_'+str(ordinal),roads,roads[-1],expected_exit=ordinal))
    roads=('w:1010:0:f',)+tuple(f'w:1100:{i}:f' for i in range(7))+('w:1207:0:f',)
    rows.append(DriveCase('ring_lost_entry',roads,roads[-1],'ring_gap',4))
    return tuple(rows)

def simulate(case,p):
    g=RecoveringGpsJourney(p,case.target,800000);scheduler=InstructionScheduler(g,'synthetic_'+case.ident)
    t=100.;logs=[];events=[];issues=[];samples=[];rerouted=False;fault_done=False;numbered=[]
    def observe(name,q,speed=10,accuracy=1,offset=0):
        nonlocal t,scheduler,rerouted
        e=p.source_edges[name];a,b=p.coordinates[e.source],p.coordinates[e.target]
        lat=a[0]+q*(b[0]-a[0]);lon=a[1]+q*(b[1]-a[1])
        f=Fix(lat+offset,lon,t,accuracy,speed,g.matcher.segments[name].bearing,5)
        previous=g.snapshot;update=g.observe(f,t);frame=scheduler.poll(t)
        if g.snapshot and g.snapshot.wrong_turn:rerouted=True
        samples.append({'lat':f.latitude,'lon':f.longitude,'t':t,'road':name,'fraction':q,
                        'accuracy_m':accuracy,'speed_mps':speed,'injected_fault':accuracy>15 or offset!=0})
        if update.match and update.match.status=='matched' and offset==0 and accuracy<=15 and update.match.road!=name:
            issues.append('wrong_matched_road')
        if update.status not in ('tracking','recovered','history_uncertain','confirming','journey_complete'):
            if g.snapshot!=previous:issues.append('rejection_advanced_snapshot')
            if frame.pending:issues.append('rejection_emitted_speech')
        if frame.pending:
            if case.fault=='restart':scheduler=InstructionScheduler(g,scheduler.session_key,checkpoint=scheduler.checkpoint());frame=scheduler.poll(t)
            event=frame.pending
            if event and case.fault!='late_delivery' and scheduler.acknowledge(event.event_id,t):
                if event.event_id in {x['id'] for x in events}:issues.append('duplicate_event')
                if event.phase!='arrival' and not g.guidance_available(t):issues.append('speech_without_trusted_guidance')
                events.append({'id':event.event_id,'phase':event.phase,'text':event.text,'target':event.target_signature})
        if case.fault=='late_delivery' and frame.pending:
            old=frame.pending;scheduler.poll(t+4)
            if scheduler.acknowledge(old.event_id,t+4):issues.append('expired_speech_delivered')
            # Advance the driving clock too: no receipt time is rewound.
            t+=4
        if case.expected_exit and case.fault!='ring_gap':
            info=g.roundabouts(t)
            if info and name!=case.target:
                numbered.append(info[0].exit_number)
                if info[0].exit_number!=case.expected_exit:issues.append('wrong_ring_ordinal')
        logs.append({'road':name,'fraction':q,'timestamp':t,'gps_status':update.status,'navigation_status':g.snapshot.status if g.snapshot else None,'instruction_status':frame.status,'remaining_roads':p.road_names(g.snapshot.roads) if g.snapshot else (), 'possible_histories':len(g.sessions)})
        return update
    for q in (.1,.12,.14):t+=1;observe(case.roads[0],q)
    index=0
    while index<len(case.roads):
        name=case.roads[index]
        for q in (.25,.5,.75,.9):
            if not fault_done and index==0 and q==.5 and case.fault in ('tunnel','bad_burst','jump','parallel','stopped_lights'):
                fault_done=True
                if case.fault=='tunnel':
                    t+=20;g.poll(t)
                    if scheduler.poll(t).pending:issues.append('speech_during_tunnel')
                elif case.fault in ('bad_burst','jump','parallel'):
                    for _ in range(3):
                        t+=1
                        observe(name,.25,accuracy=150 if case.fault=='bad_burst' else 1,
                                offset=.005 if case.fault=='jump' else .00018 if case.fault=='parallel' else 0)
                elif case.fault=='stopped_lights':
                    t+=1;observe(name,.25,speed=0);t+=1;observe(name,.25,speed=0)
                for r in (.5,.51,.52):t+=1;observe(name,r)
                continue
            if not fault_done and index==0 and q==.9 and case.fault=='skipped':
                fault_done=True;t+=20;g.poll(t);scheduler.poll(t)
                for r in (.25,.26,.27):t+=1;observe(case.roads[2],r)
                index=2;name=case.roads[2]
                for r in (.5,.75,.9):t+=2;observe(name,r,speed=30)
                break
            if not fault_done and case.fault=='ring_gap' and index==1 and q==.5:
                fault_done=True;t+=20;g.poll(t);scheduler.poll(t)
                index=3;name=case.roads[index]
                for r in (.3,.4,.5):t+=1;observe(name,r)
                info=g.roundabouts(t)
                if not info or any(x.exit_number is not None for x in info):issues.append('unknown_entry_ordinal_invented')
                continue
            t+=2;observe(name,q,speed=35 if index==0 else 20)
        index+=1
    if g.snapshot is None or g.snapshot.status!='arrived':issues.append('did_not_arrive')
    if case.expect_reroute and not rerouted:issues.append('expected_reroute_not_detected')
    if case.expected_exit and case.fault!='ring_gap' and not numbered:issues.append('no_ring_number_checks')
    if g.roundabouts(t):issues.append('ring_guidance_not_cleared')
    return {'case':case.ident,'status':'pass' if not issues else 'fail','issues':sorted(set(issues)),
            'arrival':g.snapshot.status if g.snapshot else None,'observations':len(logs),'delivered_events':events,
            'reroute_observed':rerouted,'ring_number_checks':len(numbered),'log':logs,'synthetic_samples':samples}

def reference_requests():
    return [
        {'id':'urban_route','nodes':(1,4),'ways':[10,11,12],'directions':[-2,2]},
        {'id':'urban_wrong_turn_replan','nodes':(5,4),'ways':[15,12]},
        {'id':'via_way_ban_detour','nodes':(20,24),'ways':[30,33,32]},
        {'id':'origin_inside_via_way','nodes':(22,24),'ways':[31,32]},
        {'id':'reverse_one_way_no_route','nodes':(4,1),'ways':None},
        *[{'id':'ring_exit_'+str(i),'nodes':(1010,1020+end),'ways':[1010,1100,1200+end],'exit_number':i}
          for i,end in enumerate((2,4,6,7),1)]
    ]

def run():
    raw=fixture();p=prepared(raw);rows=[simulate(c,p) for c in cases()]
    result={'classification':'Actual local DriveMate full synthetic journey execution; no real city/device/audio run',
            'dataset_sha256':hashlib.sha256(raw).hexdigest(),'cases':rows,'passed':sum(r['status']=='pass' for r in rows),
            'failed':sum(r['status']!='pass' for r in rows)}
    out=Path('results/whole_drive');out.mkdir(parents=True,exist_ok=True)
    (out/'synthetic_map.osm').write_bytes(raw);(out/'drivemate.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'full_drives':len(rows),'passed':result['passed'],'failed':result['failed'],'observations':sum(r['observations'] for r in rows)}))
    return result
if __name__=='__main__':
    result=run()
    if result['failed']:raise SystemExit(1)
