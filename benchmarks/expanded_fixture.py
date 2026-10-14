"""Independently authored road truth for matched engine research tests.

This module imports no candidate graph, router, geometry decoder or competitor.
The OSM export and exhaustive simple-path truth share an explicit author model.
No path is claimed to be real-world legal; all permissions are synthetic facts.
"""
import hashlib
import json
import math
import xml.etree.ElementTree as ET
from collections import defaultdict

PROTOCOL = 'authored-road-legality-v1'
LAYOUTS = (173, 419, 887, 1213)


def suite():
    data = {'nodes': {}, 'ways': {}, 'rules': [], 'cases': []}
    for layout, seed in enumerate(LAYOUTS):
        base = (layout + 1) * 10000
        split = 'discovery' if layout < 2 else 'holdout'
        # Affine skew/scale changes geometry, branch spacing and approach angles.
        scale = 1 + layout * .17
        def node(i, x, y):
            data['nodes'][base+i] = (.025*layout + y*.001*scale,
                                     .025*layout + x*.001*scale + y*.00011*(layout+1))
        def way(i, ns, **tags):
            data['ways'][base+i] = {'nodes': [base+n for n in ns],
                'tags': {'highway': 'residential', 'oneway': 'yes', 'maxspeed': '36',
                         'name': 'authored-'+str(base+i), **tags}}
        def rule(kind, roads, via=None):
            data['rules'].append({'kind': kind, 'ways': [base+w for w in roads],
                                 'via_node': base+via if via is not None else None})
        def case(name, start, end, category, reachable=True, exit_number=None):
            data['cases'].append({'id': f'layout{seed}/{name}', 'layout': seed,
                'split': split, 'start': base+start, 'end': base+end,
                'category': category, 'reachable': reachable, 'exit_number': exit_number})
        # Two multi-segment via-way restrictions. Detours geometrically cross
        # a road without sharing a node: a crossing is not a junction.
        for offset, kind in ((0, 'no'), (100, 'only')):
            for i, x, y in ((1,0,0),(2,1,0),(3,2,0),(4,3,0),(5,4,0),
                            (6,1,2),(7,3,2),(8,2,-1)):
                node(offset+i, x, y+offset*.1)
            for i, ns in ((10,(1,2)),(20,(2,3,4)),(30,(4,5)),
                          (40,(2,6,7,4)),(50,(3,8))):
                way(offset+i, tuple(offset+n for n in ns))
            rule(kind, (offset+10,offset+20,offset+30))
            case(kind+'_chained_turn',offset+1,offset+5,'chained_restrictions')
            case(kind+'_inside_via_reset',offset+3,offset+5,'stateless_replan')
            case(kind+'_early_exit',offset+1,offset+8,'chained_restrictions',kind=='no')
            case(kind+'_reverse',offset+5,offset+1,'oneway_no_route',False)
        # Multi-arm junction combines no-turn, private access and one-way.
        node(201,-2,25); node(202,0,25)
        way(210,(201,202),lanes='3', **{'turn:lanes':'left|through|right'})
        for arm in range(5):
            angle = (-80+arm*40+layout*3)*math.pi/180
            node(203+arm,2*math.cos(angle),25+2*math.sin(angle))
            way(211+arm,(202,203+arm), **({'access':'no'} if arm==4 else {}))
            case('junction_arm_'+str(arm),201,203+arm,'combined_junction_faults',arm not in (2,4))
        rule('no',(210,213),202)
        # One route must satisfy BOTH a via-way ban and a later only-way
        # obligation, while inaccessible/early exits and reverse travel fail.
        for i,x,y in ((600,0,31),(601,1,31),(602,2,31),(603,3,31),
                      (604,4,31),(605,1,33),(606,3,33),(607,5,31),
                      (608,6,31),(609,4.5,29),(610,4,30),(611,5,32)):
            node(i,x,y)
        for i,refs,tags in ((610,(600,601),{}),(620,(601,602,603),{}),
                            (630,(603,604),{}),(640,(601,605,606,603),{}),
                            (650,(604,607),{}),(660,(607,608),{}),
                            (670,(604,609,607),{}),(680,(607,611),{}),
                            (690,(604,610),{'access':'no'})):
            way(i,refs,**tags)
        rule('no',(610,620,630));rule('only',(630,650,660))
        case('compound_no_only_detour',600,608,'compound_corridor')
        case('compound_origin_reset',602,608,'compound_corridor')
        case('compound_only_early_exit',600,611,'compound_corridor',False)
        case('compound_inaccessible_destination',600,610,'compound_corridor',False)
        case('compound_reverse_no_route',608,600,'compound_corridor',False)
        # Asymmetric simple ring: several intermediate geometry nodes, five
        # independent exits, multilane metadata only (no occupied-lane truth).
        count = 12 + layout*2
        cx,cy = 0,40
        for i in range(count):
            angle=2*math.pi*i/count
            radius=1+.15*math.sin(3*angle+layout)
            node(300+i,cx+radius*math.cos(angle),cy+.7*radius*math.sin(angle))
        node(350,3,40); way(360,(350,300))
        way(370,tuple(300+i for i in range(count))+(300,),junction='roundabout',lanes='2')
        exit_nodes = sorted({int(count*q/6) for q in range(1,6)})
        for ordinal, index in enumerate(exit_nodes,1):
            angle=2*math.pi*index/count
            node(380+ordinal,3*math.cos(angle),cy+2.3*math.sin(angle))
            way(390+ordinal,(300+index,380+ordinal))
            case('asymmetric_ring_exit_'+str(ordinal),350,380+ordinal,
                 'asymmetric_roundabout_paths',exit_number=ordinal)
    raw = export_osm(data)
    data['dataset_sha256'] = hashlib.sha256(raw).hexdigest()
    data['protocol'] = PROTOCOL
    data['osm'] = raw
    return data


def export_osm(data):
    root=ET.Element('osm',version='0.6',generator='independent-authored-heldout-v1')
    for ident,(lat,lon) in sorted(data['nodes'].items()):
        ET.SubElement(root,'node',id=str(ident),lat=str(lat),lon=str(lon),version='1')
    for ident,way in sorted(data['ways'].items()):
        item=ET.SubElement(root,'way',id=str(ident),version='1')
        for n in way['nodes']: ET.SubElement(item,'nd',ref=str(n))
        for k,v in sorted(way['tags'].items()): ET.SubElement(item,'tag',k=k,v=v)
    for i,rule in enumerate(data['rules'],1):
        item=ET.SubElement(root,'relation',id=str(i),version='1')
        ET.SubElement(item,'member',type='way',ref=str(rule['ways'][0]),role='from')
        if rule['via_node'] is not None:
            ET.SubElement(item,'member',type='node',ref=str(rule['via_node']),role='via')
        else:
            for w in rule['ways'][1:-1]: ET.SubElement(item,'member',type='way',ref=str(w),role='via')
        ET.SubElement(item,'member',type='way',ref=str(rule['ways'][-1]),role='to')
        ET.SubElement(item,'tag',k='type',v='restriction')
        ET.SubElement(item,'tag',k='restriction',v=rule['kind']+'_straight_on')
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)


def legal_paths(data, case):
    """Exhaust all simple directed physical-edge paths, independently of costs.

    Small authored components make enumeration bounded. Only-way obligations
    apply at each exit from the via road, not just at its last junction. Node
    restrictions require their authored junction. Replan has no prior history.
    """
    outgoing=defaultdict(list)
    for wid,way in data['ways'].items():
        if way['tags'].get('access')=='no': continue
        for segment,(a,b) in enumerate(zip(way['nodes'],way['nodes'][1:])):
            outgoing[a].append((b,wid,segment))
    paths=set()
    def visit(node, history, used):
        if node==case['end']:
            paths.add(history);return
        for dest,way,segment in outgoing[node]:
            edge=(way,segment)
            if edge in used: continue
            # Continuing one physical way is not another turn.
            new = history if history and history[-1]==way else history+(way,)
            permitted=True
            if new!=history:
                for rule in data['rules']:
                    roads=tuple(rule['ways'])
                    if rule['via_node'] is not None and node!=rule['via_node']: continue
                    if rule['kind']=='no' and new[-len(roads):]==roads:
                        permitted=False
                    if rule['kind']=='only' and history:
                        for prefix in range(1,len(roads)):
                            if history[-prefix:]==roads[:prefix] and way!=roads[prefix]:
                                permitted=False
            if permitted: visit(dest,new,used|{edge})
    visit(case['start'],(),frozenset())
    return sorted(paths)


def judge(data, case, observed, no_route):
    allowed=legal_paths(data,case)
    if observed is None:
        if not no_route: status,issue='unresolved','No unambiguous decoded path or semantic no-route response'
        elif allowed: status,issue='fail','Engine rejected independently reachable legal destination'
        else: status,issue='pass',None
    elif tuple(observed) in allowed:
        status,issue='pass',None
    else:
        status,issue='fail','Path violates authored access/turn/direction/connectivity/destination truth'
    return {'status':status,'issue':issue,'allowed_ways':[list(x) for x in allowed],
            'actual_ways':observed, 'semantic_no_route':bool(no_route)}


def mutation_controls(data):
    rows=[]
    for seed in LAYOUTS[:2]:
        for suffix,bad in [('no_chained_turn',(10,20,30)),
                           ('only_chained_turn',(110,140,130)),
                           ('no_reverse',(30,20,10)),
                           ('junction_arm_2',(210,213)),
                           ('junction_arm_4',(210,215)),
                           ('compound_no_only_detour',(610,620,630,650,660)),
                           ('compound_only_early_exit',(610,640,630,650,680))]:
            c=next(c for c in data['cases'] if c['id']==f'layout{seed}/{suffix}')
            base=(LAYOUTS.index(seed)+1)*10000
            allowed=legal_paths(data,c)
            baseline=judge(data,c,list(allowed[0]) if allowed else None,not allowed)
            corrupt=judge(data,c,[base+w for w in bad],False)
            rows.append({'case':c['id'],'fault':suffix,'baseline_passed':baseline['status']=='pass',
                         'detected':corrupt['status']=='fail',
                         'scope':'Judge control using intentionally corrupt output; not a competitor failure'})
    return rows


if __name__=='__main__':
    from pathlib import Path
    data=suite();out=Path('results/expanded/map');out.mkdir(parents=True,exist_ok=True)
    (out/'expanded.osm').write_bytes(data['osm'])
    manifest={k:v for k,v in data.items() if k!='osm'}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'cases':len(data['cases']),'map_sha256':data['dataset_sha256']}))
