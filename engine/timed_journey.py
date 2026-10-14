"""Clock-aware navigation over trusted contiguous road observations.

UTC wall-clock input is separate from road progress. This is not a raw-GPS matcher.
Reuses only the endpoint graph overlay; temporal plans are never cached.
"""
from datetime import datetime,timezone,timedelta
from zoneinfo import ZoneInfo
from navigation_core.journey import Journey,Snapshot
from navigation_core.endpoints import prepare
from navigation_core.core import Router
from navigation_core.native_adapter import run
from .restrictions import timed_core_route,IncompleteTimeSearch

class ClockJourney(Journey):
    def __init__(self,prepared,vehicle,destination,timezone_name,max_states):
        if not timezone_name:raise ValueError('A road IANA timezone is required for a timed journey')
        ZoneInfo(timezone_name)
        if not isinstance(max_states,int) or isinstance(max_states,bool) or max_states<1:raise ValueError('Positive search budget required')
        super().__init__(prepared.graph,vehicle,destination)
        self._prepared=prepared;self._zone=timezone_name;self._max_states=max_states
        self._memory=max([self._memory]+[len(r.roads)-1 for r in prepared.timed_restrictions])
        self._overlay_cache=None;self._overlay_builds=0

    @staticmethod
    def _epoch(clock):
        if not isinstance(clock,datetime) or clock.utcoffset() is None:raise ValueError('Timed journey observations require aware datetimes')
        return clock.astimezone(timezone.utc).timestamp()

    def start(self,position,timestamp,inbound=()):
        return super().start(position,self._epoch(timestamp),inbound)

    def observe(self,position,timestamp):
        return super().observe(position,self._epoch(timestamp))

    def _same_road(self,position,timestamp,history,previous,wrong):
        # Delays/progress change estimated junction arrival even on the same road.
        return self._calculate(position,timestamp,history,wrong)

    def _overlay(self,position,history):
        key=(position,tuple(history))
        if self._overlay_cache is not None and self._overlay_cache[0]==key:
            return self._overlay_cache[1]
        overlay=prepare(self._graph,position,self._destination,history,self._vehicle)
        self._overlay_builds+=1
        payload=None
        if overlay is not None:
            graph,a,b,inbound,aliases=overlay
            timed=[]
            pieces={}
            for eid,(original,q0,q1) in aliases.items():pieces.setdefault(original,[]).append((q0,q1,eid))
            # Numeric ID ordering is irrelevant; sort by directed fraction.
            replacement={eid:tuple(p[2] for p in sorted(items,key=lambda p:(p[0],p[1]))) for eid,items in pieces.items()}
            for r in self._prepared.timed_restrictions:
                ids=tuple(self._prepared.edge_ids[n] for n in r.roads)
                seq=[replacement[ids[0]][-1]]
                for eid in ids[1:-1]:seq.extend(replacement[eid])
                seq.append(replacement[ids[-1]][0])
                timed.append((tuple(seq),r.condition))
            payload=(graph,a,b,inbound,aliases,Router(graph),tuple(timed))
        self._overlay_cache=(key,payload)
        return payload

    def _calculate(self,position,timestamp,history,wrong_turn=False):
        clock=datetime.fromtimestamp(timestamp,timezone.utc)
        window=self._prepared.validity_window
        if window and not window[0]<=clock<window[1]:
            return Snapshot(position,timestamp,'restriction_window_expired',(),None,wrong_turn)
        overlay=self._overlay(position,history)
        if overlay is None:return Snapshot(position,timestamp,'no_route',(),None,wrong_turn)
        graph,a,b,inbound,aliases,router,timed=overlay
        try:
            if timed:result=timed_core_route(router,timed,a,b,inbound,clock,self._zone,self._max_states,self._vehicle)
            else:
                _,results=run(graph,[('alt',a,b,self._vehicle,inbound)])
                result=results[0][0]
        except IncompleteTimeSearch:
            return Snapshot(position,timestamp,'incomplete',(),None,wrong_turn)
        if result is None:return Snapshot(position,timestamp,'no_route',(),None,wrong_turn)
        if window and clock+timedelta(microseconds=result.cost)>=window[1]:
            return Snapshot(position,timestamp,'restriction_window_expired',(),None,wrong_turn)
        roads=[]
        for eid in result.edges:
            original,q0,q1=aliases[eid]
            if q1>q0 and (not roads or roads[-1]!=original):roads.append(original)
        return Snapshot(position,timestamp,'arrived' if position==self._destination else 'navigating',tuple(roads),result.cost,wrong_turn)
