"""Aggregate actual downloaded workflow artifacts; absent engines remain unscored."""
import argparse,json
from pathlib import Path
from benchmarks.ten_system_matrix import SYSTEMS

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);a=ap.parse_args()
    records={}
    for p in a.input.rglob('scorecard.json'):
        for row in json.loads(p.read_text())['systems']:records[row['system']]=row
    for p in a.input.rglob('comparison.json'):
        r=json.loads(p.read_text());engine=r.get('engine')
        if engine not in ('osrm','valhalla'):continue
        name='OSRM MLD' if engine=='osrm' else 'Valhalla';row=records.setdefault(name,{'system':name,'scores':{},'overall':None})
        row['status']='actual cloud execution';row['scores']['routing_legality']=r.get('score_out_of_10')
        ring=[c for c in r['cases'] if c['case'].startswith('ring_exit')]
        row['scores']['junction_roundabout']=round(10*sum(c['status']=='pass' for c in ring)/len(ring),2) if len(ring)==4 and all(c['status']!='unknown' for c in ring) else None
    out=Path('results/ci-report');out.mkdir(parents=True,exist_ok=True)
    names=('DriveMate',)+tuple(n for n,_,_ in SYSTEMS)
    keys=('routing_legality','speed_rerouting','gps_matching','gps_recovery','junction_roundabout','lane_guidance','instruction_timing','offline_efficiency')
    lines=['# Navigation category results','',
           'Scores describe executed synthetic fixture subsets only. Unexecuted or non-equivalent categories are N/T. No overall/global ranking until category coverage is complete. Speed compares only the two measured local HTTP configurations in the same candidate/GraphHopper job.','',
           '| System | Route legality | Warm HTTP speed | Clean GPS paths | Recovery | Ring exits | Lanes | Timing | Offline/efficiency |','|---|---|---|---|---|---|---|---|---|']
    for name in names:
        r=records.get(name,{});values=r.get('scores',{})
        lines.append('| '+name+' | '+' | '.join('N/T' if values.get(k) is None else str(values[k])+'/10' for k in keys)+' |')
    lines+=['','Unavailable references are not ranked last. Commercial SDK/device access and remaining open-source adapters still need provisioning.']
    (out/'SCORECARD.md').write_text('\n'.join(lines)+'\n');(out/'results.json').write_text(json.dumps(records,indent=2))
if __name__=='__main__':main()
