"""Independent larger authored DAGs and distance oracle, without engine imports."""
from collections import defaultdict
from heapq import heappop,heappush
import math

PROTOCOL='larger-distance-replan-instructions-v1'


def extend(data):
    data['quality_cases']=[]
    for layout in range(4):
        base=100000+layout*10000;serial=0
        def node(i,x,y):
            data['nodes'][base+i]=(round(-.02+.02*layout+y*.001,7),
                                    round(.09+.025*layout+x*.001*(1+.04*layout),7))
        def way(a,b):
            nonlocal serial
            serial+=1;wid=base+2000+serial
            data['ways'][wid]={'nodes':[base+a,base+b],'tags':{
                'highway':'residential','oneway':'yes','maxspeed':'36',
                'driving_side':'right','name':'quality-'+str(wid)}}
            return wid
        def case(name,a,b,category,turns=None):
            data['quality_cases'].append({'id':f'grid{layout}/{name}',
                'split':'discovery' if layout<2 else 'holdout','start':base+a,'end':base+b,
                'category':category,'expected_turns':turns})
        for y in range(16):
            for x in range(16):node(y*16+x,x,y)
        for y in range(16):
            for x in range(16):
                n=y*16+x
                if x<15:way(n,n+1)
                if y<15:way(n,n+16)
                if x<15 and y<15 and (x+2*y+layout)%3==0:way(n,n+17)
        for i,(a,b) in enumerate(((0,255),(1,254),(16,239),(34,221),(50,207),(68,187))):
            case('alternatives'+str(i),a,b,'distance_quality')
        # Fresh route computation after independently authored missed-turn points;
        # no prior restriction history or live off-route detection is implied.
        for i,a in enumerate((18,49,82,115)):case('replan'+str(i),a,255,'stateless_reroute')
        case('reverse0',255,0,'reverse_no_route');case('reverse1',187,68,'reverse_no_route')
        patterns=[[(0,0),(1,0),(1,1),(2,1),(2,2)],
                  [(0,0),(1,0),(1,-1),(2,-1),(2,-2)],
                  [(0,0),(0,1),(1,1),(1,2),(2,2)],
                  [(0,0),(0,-1),(1,-1),(1,-2),(2,-2)]]
        for i,points in enumerate(patterns):
            first=500+i*10
            for j,(x,y) in enumerate(points):node(first+j,20+x,4+i*5+y)
            for j in range(4):way(first+j,first+j+1)
            # Physical alternatives make every 90-degree change a real choice,
            # rather than a silent bend along the only available continuation.
            for j in range(1,4):
                x,y=points[j];px,py=points[j-1]
                node(first+5+j,20+x+(x-px),4+i*5+y+(y-py))
                way(first+j,first+5+j)
            case('turns'+str(i),first,first+4,'junction_instructions',
                 ['left','right','left'] if i in (0,3) else ['right','left','right'])


def length(data,wid):
    refs=data['ways'][wid]['nodes'];total=0
    for a,b in zip(refs,refs[1:]):
        p,q=data['nodes'][a],data['nodes'][b]
        total+=math.hypot((q[0]-p[0])*111195.0802,
                          (q[1]-p[1])*111195.0802*math.cos(math.radians((p[0]+q[0])/2)))
    return total


def optimum(data,case):
    # Quality components contain no turn restrictions and are acyclic. This
    # oracle consumes author ways directly, never a candidate-imported graph.
    outgoing=defaultdict(list)
    for wid,w in data['ways'].items():
        if w['tags'].get('access')!='no':outgoing[w['nodes'][0]].append((w['nodes'][-1],wid,length(data,wid)))
    queue=[(0,case['start'],())];best={case['start']:0}
    while queue:
        cost,node,path=heappop(queue)
        if cost!=best[node]:continue
        if node==case['end']:return cost,list(path)
        for target,wid,d in outgoing[node]:
            candidate=cost+d
            if candidate<best.get(target,float('inf')):
                best[target]=candidate;heappush(queue,(candidate,target,path+(wid,)))
    return None


def judge_route(data,case,path,no_route):
    gold=optimum(data,case)
    if path is None:
        status='pass' if no_route and gold is None else 'fail' if no_route else 'unresolved'
        return {'status':status,'distance_m':None,'minimum_m':None if gold is None else gold[0],
                'distance_ratio':None,'issue':None if status=='pass' else 'Reachable route rejected or path unavailable'}
    node=case['start'];distance=0
    for wid in path:
        w=data['ways'].get(wid)
        if w is None or w['nodes'][0]!=node or w['tags'].get('access')=='no':
            return {'status':'fail','distance_m':None,'minimum_m':None if gold is None else gold[0],
                    'distance_ratio':None,'issue':'Wrong direction, connectivity or access'}
        node=w['nodes'][-1];distance+=length(data,wid)
    passed=gold is not None and node==case['end']
    return {'status':'pass' if passed else 'fail','distance_m':distance,
            'minimum_m':None if gold is None else gold[0],
            'distance_ratio':distance/gold[0] if passed else None,
            'issue':None if passed else 'Wrong destination or false reachable route'}


def controls(data):
    c=data['quality_cases'][0];path=optimum(data,c)[1]
    return [{'fault':name,'baseline_passed':judge_route(data,c,path,False)['status']=='pass',
             'detected':judge_route(data,c,bad,nr)['status']=='fail'}
            for name,bad,nr in (('missing_final_road',path[:-1],False),
                               ('reversed_sequence',list(reversed(path)),False),
                               ('false_no_route',None,True))]
