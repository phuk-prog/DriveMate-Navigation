"""Roundabout entry and historical-exit context for trusted-road journeys.

Past opportunities are evaluated at observed crossings, not at the current clock.
Ambiguous crossing times remove the ordinal, never road/turn availability.
"""
from dataclasses import dataclass,replace
from datetime import datetime,timedelta,timezone
from .routing import Route
from .roundabouts import identify,GuidanceRules

@dataclass
class Context:
    ring: object
    entry: str | None
    opportunities: list
    traversed: int = 0
    uncertain_time: bool = False
    repeated: bool = False
    unknown: tuple = ()

class RoundaboutProgress:
    def __init__(self,prepared,session):
        self.p=prepared;self.session=session;self.context=None;self._guidance_cache=None
        self.rules=GuidanceRules(prepared,getattr(session,'_zone',None))

    def _name(self,eid):return self.p.edge_names[eid]
    def _clock(self,timestamp):
        return datetime.fromtimestamp(timestamp,timezone.utc) if self.p.timed_restrictions or self.p.validity_window else None

    def start(self,s,inbound):
        name=self._name(s.position.edge);ring=self.p.roundabout_catalog.by_road.get(name)
        if ring is None:return
        history=tuple(self._name(e) for e in inbound)
        entry=history[-1] if history and history[-1] not in ring.roads else None
        self.context=Context(ring,entry,[],unknown=(entry,) if entry and self.p.source_edges[entry].access=='unknown' else ())
        # Reconstruct only static history when a complete explicit entry is given.
        tail=len(history)
        while tail and history[tail-1] in ring.roads:tail-=1
        if tail<len(history) and tail:
            self.context.entry=history[tail-1]
            self.context.unknown=(self.context.entry,) if self.p.source_edges[self.context.entry].access=='unknown' else ()
            if self.p.timed_restrictions:self.context.uncertain_time=True
            for i in range(tail,len(history)):
                if self.p.source_edges[history[i]].access=="unknown":
                    self.context.unknown=tuple(sorted(set(self.context.unknown)|{history[i]}))
                h=history[:i+1][-self.rules.memory:]
                at=self._clock(s.timestamp)
                op=self.rules.opportunity(h,self.p.source_edges[history[i]].target,at)
                self._record(op)

    def _record(self,op):
        c=self.context
        if c.traversed<len(c.ring.roads):c.opportunities.append(op)
        else:c.repeated=True
        c.traversed=min(c.traversed+1,len(c.ring.roads)+1)

    def observe(self,previous,current,old_history):
        a=self._name(previous.position.edge);b=self._name(current.position.edge)
        if a==b:return
        catalog=self.p.roundabout_catalog;old_ring=catalog.by_road.get(a);new_ring=catalog.by_road.get(b)
        if new_ring is None:self.context=None;return
        if old_ring!=new_ring:
            entry=a if a not in new_ring.roads else None
            self.context=Context(new_ring,entry,[],unknown=(entry,) if entry and self.p.source_edges[entry].access=='unknown' else ())
            return
        if self.context is None:self.context=Context(new_ring,None,[])
        hist=(tuple(self._name(e) for e in old_history)+(a,))[-self.rules.memory:]
        now=self._clock(current.timestamp);node=self.p.source_edges[a].target
        op=self.rules.opportunity(hist,node,now)
        if self.p.timed_restrictions and current.position.fraction>0:
            earlier=self._clock(previous.timestamp)
            if now-earlier>timedelta(days=7):self.context.uncertain_time=True
            else:
                sample=earlier
                while sample<now:
                    if self.rules.opportunity(hist,node,sample)!=op:
                        self.context.uncertain_time=True;break
                    sample=sample.replace(second=0,microsecond=0)+timedelta(minutes=1)
        if self.p.source_edges[a].access=="unknown":
            self.context.unknown=tuple(sorted(set(self.context.unknown)|{a}))
        self._record(op)

    def instructions(self,s):
        if self._guidance_cache is not None and self._guidance_cache[0] is s:
            return self._guidance_cache[1]
        result=self._instructions(s)
        self._guidance_cache=(s,result)
        return result

    def remaining_path(self,s):
        current=self._name(s.position.edge)
        names=tuple(self._name(e) for e in s.roads)
        if not names or names[0]!=current:names=(current,)+names
        destination=self._name(self.session._destination.edge)
        if self.session._destination.fraction==0 and names[-1]!=destination:names+=(destination,)
        hist=tuple(self._name(e) for e in self.session._history)
        return names,hist,self._clock(s.timestamp),getattr(self.session,'_zone',None),s.position.fraction,self.session._destination.fraction if names[-1]==destination else 1000000

    def _instructions(self,s):
        if s is None or s.status!='navigating':return ()
        current=self._name(s.position.edge)
        names,hist,clock,zone,q0,q1=self.remaining_path(s)
        guidance=identify(self.p,Route(names,0,0),hist,clock,zone,origin_fraction=q0,destination_fraction=q1,actual_origin=True)
        c=self.context
        if c is None or not guidance or current not in c.ring.roads:return guidance
        g=guidance[0];groups=[];seen=set();last=None;ambiguous=not g.numbering_supported;unknown=set(c.unknown)|set(g.unverified_edges)
        for op in c.opportunities:
            unknown.update(op.unverified)
            ambiguous|=op.ambiguous
            if op.group is None:continue
            if op.group in seen:
                if op.group!=last:ambiguous=True
            else:groups.append(op.group);seen.add(op.group);last=op.group
        for group in g.counted_exits:
            if group in seen:
                if group!=last:ambiguous=True
            else:groups.append(group);seen.add(group);last=group
        future_arcs=sum(self.p.source_edges[n].junction=='roundabout' for n in g.ring_roads)
        repeated=c.repeated or c.traversed+future_arcs>len(c.ring.roads)
        status='numbered'
        if g.exit_road is None:status='destination_inside'
        elif c.entry is None:status='started_inside'
        elif repeated:status='repeated_circulation'
        elif c.uncertain_time:status='uncertain_crossing_time'
        elif ambiguous:status='ambiguous_exit_grouping' if c.ring.simple else 'unsupported_roundabout_topology'
        elif unknown:status='unverified_access'
        candidate=len(groups) if status in ('numbered','unverified_access') else None
        updated=replace(g,entry_road=c.entry,exit_number=candidate if status=='numbered' else None,
                        candidate_exit_number=candidate,status=status,counted_exits=tuple(groups),
                        unverified_edges=tuple(sorted(unknown)))
        return (updated,)+guidance[1:]
