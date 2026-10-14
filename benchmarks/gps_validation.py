"""Expanded original synthetic GPS tests. No live provider/device comparison.

The fraction oracle comes from fixture construction, not another matcher. The
roundabout expected ordinal is authored fixture exit order; historical external
entry evidence is not scored as a new GPS or competitor-controller comparison.
"""
import json
from math import cos,sin,radians,degrees
from pathlib import Path
from gps.matching import EARTH,Fix,Matcher,GpsJourney
from engine.routing import RoadEdge,RoadGraph
from engine.reconciled import prepare_navigation
from map_data.osm_xml import import_osm_xml,Provenance
from benchmarks.roundabout_reference import fixture
LATEST_RESULTS={}

def projection_sweep():
    failures=[];cases=0;maximum_fraction_error=0;maximum_distance_error=0
    for latitude in (-60,0,51.5,75):
        for angle in range(0,360,30):
            a=radians(angle);east,north=cos(a),sin(a)
            def coordinate(x,y):return latitude+degrees(y/EARTH),10+degrees(x/(EARTH*cos(radians(latitude))))
            pts={'a':coordinate(0,0),'b':coordinate(100*east,100*north)}
            p=prepare_navigation(RoadGraph(pts,[RoadEdge('f','a','b',100,36,'allowed'),RoadEdge('r','b','a',100,36,'unknown')]),pts)
            for fraction in (.1,.25,.5,.75,.9):
                for error in (-6,-2,0,2,6):
                    lat,lon=coordinate(100*fraction*east-error*north,100*fraction*north+error*east)
                    for accuracy in (2,6):
                        for reverse in (False,True):
                            cases+=1
                            heading=(90-angle+(180 if reverse else 0))%360
                            m=Matcher(p).observe(Fix(lat,lon,1,accuracy,10,heading,5),1)
                            expected=round((1-fraction if reverse else fraction)*1000000)
                            fraction_error=abs(m.position.fraction-expected) if m.position else None
                            distance_error=abs(m.distance_m-abs(error)) if m.distance_m is not None else None
                            if m.status!='matched' or m.road!=('r' if reverse else 'f') or fraction_error>2 or distance_error>1e-5:
                                failures.append({'case':cases,'latitude':latitude,'angle':angle,'fraction':fraction,'noise_m':error,
                                    'accuracy_m':accuracy,'reverse':reverse,'status':m.status,'fraction_error':fraction_error,'distance_error':distance_error})
                            else:
                                maximum_fraction_error=max(maximum_fraction_error,fraction_error)
                                maximum_distance_error=max(maximum_distance_error,distance_error)
    result={'classification':'Independent constructed-fraction oracle; synthetic local-plane policy geometry',
            'cases':cases,'failures':failures,'max_fraction_error_millionths':maximum_fraction_error,
            'max_perpendicular_distance_error_m':maximum_distance_error}
    LATEST_RESULTS['projection']=result
    return result

def roundabout_replays():
    raw,_=fixture();m=import_osm_xml(raw,provenance=Provenance('synthetic','v1','original','OpenStreetMap contributors'))
    p=prepare_navigation(m.graph,m.coordinates);rows=[]
    for expected,end in enumerate((2,4,6,7),1):
        target=f'w:{200+end}:0:f';g=GpsJourney(p,target,800000);t=100;checks=[];rejected=0
        roads=['w:10:0:f']+[f'w:100:{i}:f' for i in range(end)]+[target]
        for name in roads:
            edge=p.source_edges[name];a,b=p.coordinates[edge.source],p.coordinates[edge.target]
            heading=g.matcher.segments[name].bearing
            for fraction in (.2,.9 if name==target else .8):
                t+=4
                f=Fix(a[0]+fraction*(b[0]-a[0]),a[1]+fraction*(b[1]-a[1]),t,1,10,heading,5)
                update=g.observe(f,t)
                info=g.roundabouts(t)
                number=info[0].exit_number if info else None
                checks.append({'road':name,'fraction':fraction,'match':update.match.status,'exit_number':number,'status':update.trusted_snapshot.status if update.trusted_snapshot else None})
                if name!=target:
                    previous=g.journey.snapshot
                    poor=Fix(f.latitude,f.longitude,t+1,150,10,heading,5)
                    fault=g.observe(poor,t+1);rejected+=1
                    if fault.guidance_available or g.journey.snapshot!=previous:raise AssertionError('Rejected fix advanced journey')
        ringchecks=[c for c in checks if c['road']!=target]
        passed=all(c['match']=='matched' and c['exit_number']==expected for c in ringchecks)
        passed=passed and all(c['match']=='matched' and c['exit_number'] is None for c in checks if c['road']==target)
        passed=passed and g.journey.snapshot.status=='arrived'
        rows.append({'exit':expected,'passed':passed,'matched_observations':len(checks),'rejected_quality_observations':rejected,'checks':checks})
    LATEST_RESULTS['roundabout_gps_journeys']=rows
    return rows

def write_latest_results():
    projection=LATEST_RESULTS['projection'];replays=LATEST_RESULTS['roundabout_gps_journeys']
    result={'classification':'Original synthetic GPS and integrated guidance validation; no external matcher or device run',
            'projection':projection,'roundabout_gps_journeys':replays,
            'external_gps_comparison':'Pending; no winner or accuracy ranking established'}
    Path('results/gps_expanded_validation.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'projection_cases':projection['cases'],'projection_failures':len(projection['failures']),
                      'gps_journeys':len(replays),'journeys_passed':sum(r['passed'] for r in replays),
                      'matched_observations':sum(r['matched_observations'] for r in replays),
                      'rejected_quality_observations':sum(r['rejected_quality_observations'] for r in replays)}))
    if projection['failures'] or not all(r['passed'] for r in replays):raise SystemExit(1)
def main():
    projection_sweep();roundabout_replays();write_latest_results()
if __name__=='__main__':main()
