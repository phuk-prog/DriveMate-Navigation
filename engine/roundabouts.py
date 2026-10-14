"""Original evidence-led roundabout exit counting; no inferred lane instructions.

Numbers describe legal motorcar exit opportunities in the supplied graph snapshot.
Ambiguous grouping/topology and unknown access never produce a verified ordinal.
"""
from dataclasses import dataclass
from datetime import datetime,timedelta,timezone
from types import MappingProxyType
from zoneinfo import ZoneInfo

@dataclass(frozen=True)
class Ring:
    roads: frozenset
    nodes: frozenset
    simple: bool

@dataclass(frozen=True)
class RoundaboutInstruction:
    entry_road: str | None
    ring_roads: tuple
    exit_road: str | None
    exit_number: int | None
    candidate_exit_number: int | None
    status: str
    counted_exits: tuple
    unverified_edges: tuple
    remaining_exit_number: int | None = None
    numbering_supported: bool = True

class RoundaboutCatalog:
    def __init__(self,source,graph,edge_names):
        roads={n:e for n,e in source.edges.items() if e.junction=='roundabout'}
        touching={}
        for name,e in roads.items():
            touching.setdefault(e.source,set()).add(name)
            touching.setdefault(e.target,set()).add(name)
        by_road={};todo=set(roads)
        for first in sorted(roads):
            if first not in todo:continue
            pending=[first];component=set()
            while pending:
                n=pending.pop()
                if n in component:continue
                component.add(n);todo.discard(n)
                e=roads[n]
                pending.extend(touching[e.source]-component);pending.extend(touching[e.target]-component)
            nodes={v for n in component for v in (roads[n].source,roads[n].target)}
            ins={v:0 for v in nodes};outs={v:0 for v in nodes}
            for n in component:ins[roads[n].target]+=1;outs[roads[n].source]+=1
            simple=len(nodes)>=3 and all(ins[v]==outs[v]==1 for v in nodes)
            ring=Ring(frozenset(component),frozenset(nodes),simple)
            for n in component:by_road[n]=ring
        self.by_road=MappingProxyType(by_road)
        self.outgoing=source.adjacency
        self.costs=MappingProxyType({edge_names[e.id]:e.cost for e in graph.edges})


@dataclass(frozen=True)
class Opportunity:
    group: str | None
    ambiguous: bool
    unverified: tuple

class GuidanceRules:
    def __init__(self,p,zone_name=None):
        self.p=p;self.zone=ZoneInfo(zone_name) if zone_name else None
        self.memory=max([1,p.prepared_router._max_prefix]+[len(r.roads)-1 for r in p.timed_restrictions])
        self.timed_actions={}
        for r in p.timed_restrictions:self.timed_actions.setdefault(r.roads[-1],[]).append(r)

    def legal(self,hist,name,at):
        p=self.p
        if p.source_edges[name].access=='prohibited':return False
        prefix=p.prepared_router._prefix(tuple(p.edge_ids[n] for n in hist[-self.memory:]))
        if p.prepared_router._advance(prefix,p.edge_ids[name],'car') is None:return False
        if p.timed_restrictions:
            if at is None or self.zone is None:raise ValueError('Clock and road timezone required')
            local=at.astimezone(self.zone)
            for r in self.timed_actions.get(name,()):
                if len(hist)>=len(r.roads)-1 and hist[-(len(r.roads)-1):]==r.roads[:-1] and r.condition.active(local):return False
        return True

    def opportunity(self,hist,node,at):
        p=self.p;catalog=p.roundabout_catalog
        exits=[e for e in catalog.outgoing[node] if e.edge_id not in catalog.by_road and self.legal(hist,e.edge_id,at)]
        unknown=tuple(sorted(e.edge_id for e in exits if e.access=='unknown'))
        if not exits:return Opportunity(None,False,unknown)
        groups={e.exit_group for e in exits}
        if len(exits)>1 and (None in groups or len(groups)!=1):return Opportunity(None,True,unknown)
        return Opportunity(next(iter(groups)) or 'node:'+node,False,unknown)


def path_context(p,route,inbound=(),departure=None,timezone_name=None,*,origin_fraction=0,destination_fraction=1000000,actual_origin=False):
    roads=tuple(route.edge_ids);history=tuple(inbound)
    names=p.source_edges;catalog=p.roundabout_catalog
    if any(n not in names for n in roads+history):raise ValueError('Unknown guidance road')
    if any(names[a].target!=names[b].source for a,b in zip(history+roads,(history+roads)[1:])):
        raise ValueError('Disconnected guidance road sequence')
    for q in (origin_fraction,destination_fraction):
        if not isinstance(q,int) or isinstance(q,bool) or not 0<=q<=1000000:raise ValueError("Invalid partial-road fraction")
    clock=None;zone_name=timezone_name
    if p.timed_restrictions or p.validity_window:
        if not isinstance(departure,datetime) or departure.utcoffset() is None:raise ValueError('Aware guidance departure required')
        clock=departure.astimezone(timezone.utc)
        if p.timed_restrictions:
            zone_name=timezone_name or getattr(departure.tzinfo,'key',None)
            if not zone_name:raise ValueError('Road IANA timezone required')
            ZoneInfo(zone_name)
        if p.validity_window and not p.validity_window[0]<=clock<p.validity_window[1]:
            raise ValueError('Guidance outside compiled restriction window')
    edge_costs=catalog.costs
    rules=GuidanceRules(p,zone_name);memory=rules.memory
    after=[];times=[]
    history=history[-memory:]
    for index,name in enumerate(roads):
        if names[name].access=='prohibited' or not (actual_origin and index==0) and not rules.legal(history,name,clock):raise ValueError('Guidance route contains a prohibited manoeuvre')
        history=(history+(name,))[-memory:];after.append(history)
        q0=origin_fraction if index==0 else 0
        q1=destination_fraction if index==len(roads)-1 else 1000000
        if q1<q0:raise ValueError('Partial route goes backwards without a loop')
        if clock is not None:clock+=timedelta(microseconds=edge_costs[name]*q1//1000000-edge_costs[name]*q0//1000000)
        times.append(clock)
    if p.validity_window and clock>=p.validity_window[1]:raise ValueError('Guidance outlasts compiled restriction window')
    return roads,names,catalog,rules,after,times


def identify(p,route,inbound=(),departure=None,timezone_name=None,*,origin_fraction=0,destination_fraction=1000000,actual_origin=False):
    roads,names,catalog,rules,after,times=path_context(p,route,inbound,departure,timezone_name,
        origin_fraction=origin_fraction,destination_fraction=destination_fraction,actual_origin=actual_origin)
    result=[];i=0
    while i<len(roads):
        if roads[i] not in catalog.by_road:i+=1;continue
        first=i;ring=catalog.by_road[roads[i]]
        while i<len(roads) and roads[i] in ring.roads:i+=1
        circle=roads[first:i];exit_road=roads[i] if i<len(roads) else None
        prior=roads[first-1] if first else (inbound[-1] if inbound else None)
        entry=prior if prior is not None and prior not in ring.roads else None
        status='numbered';counted=[];last_group=None;seen=set();uncertain=set()
        for name in circle:
            if names[name].access=='unknown':uncertain.add(name)
        if entry and names[entry].access=='unknown':uncertain.add(entry)
        if not ring.simple:status='unsupported_roundabout_topology'
        elif len(circle)>len(ring.roads):status='repeated_circulation'
        for offset,name in enumerate(circle,first):
            node=names[name].target
            if offset==len(roads)-1 and destination_fraction<1000000:continue
            opportunity=rules.opportunity(after[offset],node,times[offset])
            uncertain.update(opportunity.unverified)
            if opportunity.ambiguous:
                if status=='numbered':status='ambiguous_exit_grouping'
                continue
            group=opportunity.group
            if group is None:continue
            if group in seen:
                if group!=last_group and status=='numbered':status='ambiguous_exit_grouping'
                continue
            seen.add(group);counted.append(group);last_group=group
        supported=status=="numbered"
        remaining=len(counted) if supported and exit_road is not None and counted else None
        candidate=remaining
        if exit_road is None:status='destination_inside'
        elif entry is None:status='started_inside'
        elif status=='numbered' and uncertain:status='unverified_access'
        number=candidate if status=='numbered' else None
        if status not in ('numbered','unverified_access'):candidate=None
        result.append(RoundaboutInstruction(entry,tuple(circle),exit_road,number,candidate,status,tuple(counted),tuple(sorted(uncertain)),remaining,supported))
    return tuple(result)
