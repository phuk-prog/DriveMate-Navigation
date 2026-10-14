"""Original adversarial instruction streams; no actual speaker/provider/road run."""
import json
from pathlib import Path
from benchmarks.instruction_fixtures import crossroads,observe,start
from guidance.timing import InstructionScheduler,PHASES
from gps.matching import Fix
from gps.recovery import RecoveringGpsJourney
from map_data.osm_xml import import_osm_xml,Provenance
from engine.reconciled import prepare_navigation
from benchmarks.roundabout_reference import fixture

LATEST_RESULTS={}

def adversarial_sweep():
    failures=[];cases=0;frames=0;deliveries=0;blocked=0;rows=[]
    for latitude in (0,51.5):
        for speed in (0,1,2,5,10,15,25,35):
            for gap in (15,40,120):
                for fault in ('clean','gps_loss','bad_burst','late_jump'):
                    for delivery in ('immediate','delayed','restart'):
                        for lanes in (False,True):
                            for access in ('allowed','unknown'):
                                cases+=1;casefails=[];g=crossroads(gap,latitude,access,lanes=lanes)
                                start(g,150,speed);s=InstructionScheduler(g,'synthetic_'+str(cases))
                                accepted=set();rank={};events=[]
                                def process(t):
                                    nonlocal frames,deliveries,blocked,s
                                    frame=s.poll(t);frames+=1
                                    if frame.pending is None:blocked+=1;return
                                    e=frame.pending
                                    if frame.instruction is None or e.text!=frame.instruction.text:casefails.append('speech_display_mismatch')
                                    if not g.guidance_available(t):casefails.append('speech_without_consensus')
                                    if e.expires_at<t or t-g.matcher.last.timestamp>3:casefails.append('expired_event')
                                    if frame.instruction.target.departure not in ('b','c'):casefails.append('unexpected_route_turn')
                                    if 'lane' in e.text.lower():casefails.append('invented_lane_command')
                                    if access=='unknown' and frame.instruction.target.indicated_lanes:casefails.append('unverified_lane_advice')
                                    if delivery=='restart':
                                        old=e.event_id;s=InstructionScheduler(g,s.session_key,checkpoint=s.checkpoint())
                                        if s.acknowledge(old,t):casefails.append('restored_pending_event')
                                        frame=s.poll(t);e=frame.pending
                                        if e is None:return
                                    when=t+.5 if delivery=='delayed' else t
                                    ok=s.acknowledge(e.event_id,when)
                                    if ok:
                                        if e.event_id in accepted:casefails.append('duplicate_event_id')
                                        accepted.add(e.event_id);deliveries+=1
                                        value=PHASES.index(e.phase)
                                        if value<=rank.get(e.target_signature,-1):casefails.append('repeated_or_backwards_phase')
                                        rank[e.target_signature]=value
                                        events.append({'target':frame.instruction.target.departure,'phase':e.phase,'text':e.text})
                                        if s.acknowledge(e.event_id,when):casefails.append('double_ack')
                                process(3)
                                observe(g,-100,0,4,speed);process(4)
                                if fault=='gps_loss':
                                    g.poll(8);frame=s.poll(8);frames+=1
                                    if frame.pending is not None:casefails.append('speech_during_loss')
                                    for t in (12,13,14):observe(g,-90+t-12,0,t,speed);process(t)
                                    t=15
                                elif fault=='bad_burst':
                                    for t in (5,6,7):
                                        observe(g,-90,0,t,speed,accuracy=150);frame=s.poll(t);frames+=1
                                        if frame.pending is not None:casefails.append('speech_during_bad_burst')
                                    for t in (8,9,10):observe(g,-90+t-8,0,t,speed);process(t)
                                    t=11
                                elif fault=='late_jump':
                                    observe(g,-20,0,5,speed);process(5);t=6
                                else:t=5
                                for d in ((16,8) if fault=='late_jump' else (60,28)):
                                    observe(g,-d,0,t,speed);process(t);t+=1
                                # The first turn has been passed: queued left
                                # instructions must be cancelled, even if missed.
                                observe(g,0,min(5,gap/3),t,speed,heading=0)
                                f=s.poll(t);frames+=1
                                if f.instruction and f.instruction.target.departure=='b':casefails.append('passed_turn_still_current')
                                if fault!='late_jump' and speed>=10 and not any(e['target']=='b' for e in events):casefails.append('no_timely_first_turn_event')
                                if casefails:failures.append({'case':cases,'latitude':latitude,'speed':speed,'gap':gap,'fault':fault,'delivery':delivery,'lanes':lanes,'access':access,'issues':sorted(set(casefails))})
                                rows.append({'case':cases,'status':'pass' if not casefails else 'fail','latitude':latitude,'speed':speed,'gap':gap,'fault':fault,'delivery':delivery,'lanes':lanes,'access':access,'delivered_events':events})
    result={'classification':'Original synthetic GPS/recovery/queued-delivery streams; invariant and authored-manoeuvre oracle',
            'cases':cases,'frames':frames,'accepted_events':deliveries,'frames_without_event':blocked,'failures':failures,'register':rows}
    LATEST_RESULTS['adversarial_sweep']=result
    return result

def roundabout_instruction_replay():
    raw,_=fixture();m=import_osm_xml(raw,provenance=Provenance('synthetic','v1','original','OpenStreetMap contributors'))
    p=prepare_navigation(m.graph,m.coordinates);g=RecoveringGpsJourney(p,'w:207:0:f',800000)
    s=InstructionScheduler(g,'synthetic_ring');t=100;checks=[]
    def f(name,q,t):
        e=p.source_edges[name];a,b=p.coordinates[e.source],p.coordinates[e.target]
        return Fix(a[0]+q*(b[0]-a[0]),a[1]+q*(b[1]-a[1]),t,1,10,g.matcher.segments[name].bearing,5)
    for q in (.3,.4,.5):t+=2;g.observe(f('w:10:0:f',q,t),t)
    before=s.poll(t);verified=before.instruction is not None and before.instruction.target.exit_number==4
    if before.pending:s.acknowledge(before.pending.event_id,t)
    g.poll(t+20);loss=s.poll(t+20);t+=30
    for q in (.3,.4,.5):t+=2;g.observe(f('w:100:2:f',q,t),t)
    after=s.poll(t)
    unknown=(after.instruction is not None and after.instruction.target.kind=='roundabout_exit' and
             after.instruction.target.exit_number is None and 'exit 4' not in after.instruction.text)
    for i in range(3,7):
        t+=2;g.observe(f(f'w:100:{i}:f',.5,t),t);frame=s.poll(t)
        checks.append({'road':f'w:100:{i}:f','status':frame.status,'text':frame.instruction.text if frame.instruction else None})
        if frame.pending:s.acknowledge(frame.pending.event_id,t)
    for q in (.2,.6,.9):
        t+=2;g.observe(f('w:207:0:f',q,t),t);frame=s.poll(t)
    arrival=frame.pending is not None and frame.pending.phase=='arrival'
    if frame.pending:s.acknowledge(frame.pending.event_id,t)
    result={'classification':'One original full GPS-loss ring replay through scheduler events; no actual audio run',
            'verified_entry_number':verified,'loss_cancelled':loss.pending is None,'unknown_entry_number_withheld':unknown,
            'checks':checks,'arrival_event':arrival,'no_duplicate_arrival':s.poll(t).pending is None,
            'passed':verified and loss.pending is None and unknown and arrival and s.poll(t).pending is None}
    LATEST_RESULTS['roundabout_replay']=result
    return result

def write_latest_results():
    Path('results/instruction_expanded_validation.json').write_text(json.dumps(LATEST_RESULTS,indent=2))
    a=LATEST_RESULTS['adversarial_sweep'];r=LATEST_RESULTS['roundabout_replay']
    print(json.dumps({'instruction_cases':a['cases'],'failures':len(a['failures']),'frames':a['frames'],
                      'accepted_events':a['accepted_events'],'roundabout_passed':r['passed']}))
    if a['failures'] or not r['passed']:raise SystemExit(1)
def main():
    adversarial_sweep();roundabout_instruction_replay();write_latest_results()
if __name__=='__main__':main()
