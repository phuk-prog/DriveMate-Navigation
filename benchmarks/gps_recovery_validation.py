"""Original hard synthetic recovery cases, with constructed outcome oracles.

Names such as tunnel/urban/trees describe injected signal faults, not a tested
real place, physical sensor model, actual drive or fresh external engine run.
"""
import json
from pathlib import Path
from dataclasses import replace
from math import cos,sin,radians,degrees,hypot
from gps.matching import EARTH,Fix,Match,Matcher
from gps.recovery import RecoveringGpsJourney,possible_histories
from engine.routing import RoadGraph,RoadEdge
from engine.reconciled import prepare_navigation,Restriction
from map_data.osm_xml import import_osm_xml,Provenance
from benchmarks.roundabout_reference import fixture

LATEST_RESULTS={}

def judge_history_case(row):
    expected=row['expected_status']
    recovered=expected in ('recovered','history_uncertain')
    return (row['status']==expected and row['guidance_available']==(expected=='recovered')
            and row['rejected_snapshot_advances']==0
            and (not recovered or (row['history_count']==row['expected_histories']
                                  and sorted(row['histories'])==sorted(row['expected_suffixes'])
                                  and row['history_inferred'] is True)))


def history_controls():
    baseline={'expected_status':'history_uncertain','expected_histories':2,
              'status':'history_uncertain','history_count':2,'guidance_available':False,
              'rejected_snapshot_advances':0,'history_inferred':True,
              'histories':[['up','uk'],['down','dk']],
              'expected_suffixes':[['up','uk'],['down','dk']]}
    return [{'fault':key,'baseline_passed':judge_history_case(baseline),
             'detected':not judge_history_case(baseline|{key:value}),
             'scope':'Corrupt-result judge control, not a mutated engine'}
            for key,value in (('guidance_available',True),('history_count',1),
                              ('rejected_snapshot_advances',1),('history_inferred',False),
                              ('histories',[['up','uk'],['invented','dk']]))]


def history_matrix():
    """Candidate-only fork recovery, with acyclic author truth for two paths.

    Both branches physically exist even if a past turn was banned. Therefore
    neither assumed legality nor a partial search may remove a future obligation.
    Held-out coordinates vary geometry, not the topological reasoning oracle.
    """
    rows=[]
    for layout,(latitude,angle) in enumerate(((0,0),(51.5,45),(-20,135),(40,270))):
        def coord(x,y):
            u=x*cos(radians(angle))-y*sin(radians(angle))
            v=x*sin(radians(angle))+y*cos(radians(angle))
            return latitude+degrees(v/EARTH),10+degrees(u/(EARTH*cos(radians(latitude))))
        pts={n:coord(x,y) for n,x,y in [('a',0,0),('j',100,0),('u',150,30),
              ('d',150,-30),('k',200,0),('l',300,0),('z',400,0)]}
        edges=[RoadEdge(n,a,b,length,36,'allowed')
               for n,a,b,length in [('a','a','j',100),('up','j','u',hypot(50,30)),
                   ('down','j','d',hypot(50,30)),('uk','u','k',hypot(50,30)),
                   ('dk','d','k',hypot(50,30)),('merge','k','l',100),('goal','l','z',100)]]
        for mode in ('consensus','future_ban','past_and_future_ban','history_budget'):
            rules=() if mode in ('consensus','history_budget') else (Restriction('no',('uk','merge','goal')),)
            if mode=='past_and_future_ban': rules+=(Restriction('no',('a','up')),)
            p=prepare_navigation(RoadGraph(pts,edges,multi_restrictions=rules),pts)
            for gap in (4,30,298,299):
                journey=RecoveringGpsJourney(p,'goal',800000,max_histories=1 if mode=='history_budget' else 16)
                def fix(x,t):
                    lat,lon=coord(x,0)
                    return Fix(lat,lon,t,2,10,(90-angle)%360,5)
                for t in (1,2,3): journey.observe(fix(50+t,t),t)
                frames=[];advances=0;previous=journey.snapshot
                update=journey.poll(3+gap)
                if journey.snapshot!=previous: advances+=1
                frames.append({'phase':'silence','status':update.status,'guidance_available':update.guidance_available})
                if update.guidance_available: advances+=1
                for i in range(3):
                    t=3+gap+i;previous=journey.snapshot
                    update=journey.observe(fix(240+i,t),t)
                    if (not update.match or update.match.status!='matched') and journey.snapshot!=previous: advances+=1
                    if i<2 and update.guidance_available: advances+=1
                    frames.append({'phase':'reacquisition','status':update.status,
                                   'match_status':None if update.match is None else update.match.status,
                                   'guidance_available':update.guidance_available})
                expected=('recovery_gap_outside_bounds' if gap+2>300 else
                          'recovery_history_incomplete' if mode=='history_budget' else
                          'recovered' if mode=='consensus' else 'history_uncertain')
                row={'case':f'fork{layout}/{mode}/elapsed{gap+2}',
                     'split':'discovery' if layout<2 else 'holdout','mode':mode,
                     'elapsed_since_trusted_fix':gap+2,'expected_status':expected,'expected_histories':2,
                     'expected_suffixes':([['uk'],['dk']] if mode in ('consensus','history_budget')
                                          else [['up','uk'],['down','dk']]),
                     'status':update.status,'history_count':len(journey.sessions),
                     'histories':[list(h) for h in journey.histories],
                     'history_inferred':update.history_inferred,'guidance_available':update.guidance_available,
                     'rejected_snapshot_advances':advances,'frames':frames}
                row['passed']=judge_history_case(row);rows.append(row)
    result={'classification':'Candidate-only synthetic acyclic forks; unknown physical past is not assumed legal',
            'cases':len(rows),'results':rows,'failures':[r for r in rows if not r['passed']],
            'judge_controls':history_controls(),
            'limits':['No external controller comparison','Held-out geometry shares fork topology',
                      'No recorded sensor or road-device evidence']}
    LATEST_RESULTS['history_matrix']=result
    return result


def hard_sweep():
    """1536 cases: independent outcome oracle from linear fixture connectivity."""
    failures=[];cases=0;recovered=0;withheld=0;observations=0
    for latitude in (0,51.5):
        for angle in (0,45,90,135,180,225,270,315):
            east,north=cos(radians(angle)),sin(radians(angle))
            def coord(x,y):
                u,v=x*east-y*north,x*north+y*east
                return latitude+degrees(v/EARTH),10+degrees(u/(EARTH*cos(radians(latitude))))
            pts={n:coord(x,y) for n,x,y in [('a',0,0),('b',100,0),('c',200,0),('d',300,0),('s',0,12),('t',100,12)]}
            p=prepare_navigation(RoadGraph(pts,[RoadEdge('ab','a','b',100,36,'unknown'),RoadEdge('bc','b','c',100,36,'allowed'),RoadEdge('cd','c','d',100,36,'allowed'),RoadEdge('parallel','s','t',100,36,'allowed')]),pts)
            heading=(90-angle)%360
            def fix(x,y,t,accuracy=2,bearing=None):
                a,b=coord(x,y)
                return Fix(a,b,t,accuracy,10,heading if bearing is None else bearing,5)
            for gap in (4,12,60,240):
                for fault in ('tunnel','urban_bounce','tree_cover'):
                    for target in ('same','skipped','parallel','wrong_way'):
                        for repeats in (1,4):
                            cases+=1
                            g=RecoveringGpsJourney(p,'cd',800000)
                            for t in (1,2,3):g.observe(fix(20+t,0,t),t);observations+=1
                            baseline=g.snapshot
                            start=3+gap
                            g.poll(start)
                            for i in range(repeats):
                                t=start+i
                                f=fix(50,0,t,accuracy=150) if fault!='urban_bounce' else fix(50,80,t)
                                bad=g.observe(f,t);observations+=1
                                if bad.guidance_available or g.snapshot!=baseline:failures.append({'case':cases,'phase':'bad_fix_advanced'})
                            begin=start+repeats
                            for i in range(3):
                                x=(220 if target=='skipped' else 50)+i
                                y=12 if target=='parallel' else 0
                                f=fix(x,y,begin+i,bearing=(heading+180)%360 if target=='wrong_way' else heading)
                                result=g.observe(f,begin+i);observations+=1
                            expected=target in ('same','skipped')
                            passed=(result.status=='recovered' and result.guidance_available) if expected else (not result.guidance_available and g.snapshot==baseline)
                            if not passed:failures.append({'case':cases,'latitude':latitude,'angle':angle,'gap':gap,'fault':fault,'target':target,'repeats':repeats,'status':result.status})
                            if result.status=='recovered':recovered+=1
                            else:withheld+=1
    result={'classification':'Original synthetic faults and authored linear-connectivity outcome oracle',
            'cases':cases,'observations':observations,'recovered':recovered,'withheld':withheld,'failures':failures}
    LATEST_RESULTS['hard_sweep']=result
    return result

def ring_recovery():
    raw,_=fixture();m=import_osm_xml(raw,provenance=Provenance('synthetic','v1','original','OpenStreetMap contributors'))
    p=prepare_navigation(m.graph,m.coordinates);g=RecoveringGpsJourney(p,'w:207:0:f',800000);t=100;checks=[]
    def observation(name,q,t):
        e=p.source_edges[name];a,b=p.coordinates[e.source],p.coordinates[e.target]
        return Fix(a[0]+q*(b[0]-a[0]),a[1]+q*(b[1]-a[1]),t,1,10,g.matcher.segments[name].bearing,5)
    for q in (.3,.4,.5):
        t+=2;g.observe(observation('w:10:0:f',q,t),t)
    before=g.roundabouts(t)
    initial=before[0].exit_number if before else None
    g.poll(t+20)
    t+=30
    for q in (.3,.4,.5):
        t+=2;s=g.observe(observation('w:100:2:f',q,t),t)
    after=g.roundabouts(t)
    withheld=bool(after) and all(r.exit_number is None for r in after)
    cleared=False
    for i in range(3,7):
        t+=2;s=g.observe(observation(f'w:100:{i}:f',.5,t),t)
        info=g.roundabouts(t)
        checks.append({'road':f'w:100:{i}:f','status':s.status,'exit_number':info[0].exit_number if info else None})
    t+=2;s=g.observe(observation('w:207:0:f',.2,t),t);cleared=g.roundabouts(t)==()
    for q in (.6,.9):
        t+=2;s=g.observe(observation('w:207:0:f',q,t),t)
    result={'classification':'Original synthetic ring GPS loss, multi-road recovery and observed completion',
            'initial_exit_number':initial,'withheld_unknown_entry_after_recovery':withheld,
            'possible_histories':len(g.sessions),'checks':checks,'cleared_after_exit':cleared,
            'arrival':g.snapshot.status,'passed':initial==4 and withheld and all(c['exit_number'] is None for c in checks)
                                               and cleared and g.snapshot.status=='arrived'}
    LATEST_RESULTS['ring_recovery']=result
    return result

def reachability_oracle_sweep():
    """Exhaustive path enumeration independent of the state's Dijkstra search."""
    cases=0;failures=[]
    for loop in (False,True):
        for memory in (1,2,3):
            xy={'0':(0,0),'1':(50,0),'2':(100,25),'3':(100,-25),'4':(150,0),'5':(200,0)}
            endpoints=[('a','0','1'),('b','1','2'),('c','1','3'),('d','2','4'),('e','3','4'),('f','4','5')]
            if loop:endpoints.append(('loop','5','1'))
            lengths={n:hypot(xy[v][0]-xy[u][0],xy[v][1]-xy[u][1]) for n,u,v in endpoints}
            sequence=('a','b','d','f')[:memory+1]
            pts={n:(degrees(y/EARTH),degrees(x/EARTH)) for n,(x,y) in xy.items()}
            p=prepare_navigation(RoadGraph(pts,[RoadEdge(n,u,v,lengths[n],36,'allowed') for n,u,v in endpoints],
                                           multi_restrictions=(Restriction('no',sequence),)),pts)
            matcher=Matcher(p);out={v:[] for v in xy};end={}
            for n,u,v in endpoints:out[u].append(n);end[n]=v
            for q0 in (.1,.5,.9):
                for q1 in (.1,.5,.9):
                    for elapsed in (1,2,3,4):
                        cases+=1;limit=80*elapsed+7
                        origin=Match('matched',p.position('a',round(q0*1000000)),'a',1,2,0,10,5)
                        target=replace(origin,road='f',position=p.position('f',round(q1*1000000)))
                        expected=set()
                        def visit(road,path,distance):
                            if distance>limit:return
                            if road=='f' and distance+q1*lengths['f']<=limit:
                                expected.add(tuple(path[-memory:]))
                            for child in out[end[road]]:visit(child,path+[road],distance+lengths[road])
                        for child in out['1']:visit(child,['a'],(1-q0)*lengths['a'])
                        actual=possible_histories(matcher,origin,target,((),),elapsed)
                        if set(actual.histories)!=expected or actual.status!=('reachable' if expected else 'recovery_unreachable'):
                            failures.append({'case':cases,'loop':loop,'memory':memory,'q0':q0,'q1':q1,'elapsed':elapsed,
                                             'status':actual.status,'expected':sorted(expected),'actual':actual.histories})
    result={'classification':'Independent exhaustive directed physical path enumeration; includes cycles and past turn bans',
            'cases':cases,'failures':failures}
    LATEST_RESULTS['reachability_oracle']=result
    return result

def write_latest_results():
    result={'classification':'Synthetic recovery only; no external matcher/device/real-road ranking',**LATEST_RESULTS}
    Path('results/gps_recovery_expanded.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'hard_cases':result['hard_sweep']['cases'],'failures':len(result['hard_sweep']['failures']),
                      'recovered':result['hard_sweep']['recovered'],'withheld':result['hard_sweep']['withheld'],
                      'observations':result['hard_sweep']['observations'],'ring_passed':result['ring_recovery']['passed']}))
    if result['hard_sweep']['failures'] or result['reachability_oracle']['failures'] or not result['ring_recovery']['passed'] or result['history_matrix']['failures']:raise SystemExit(1)
def main():
    hard_sweep();ring_recovery();reachability_oracle_sweep();history_matrix();write_latest_results()
if __name__=='__main__':main()
