"""Original bounded non-waiting, time-expanded search for weekly turn bans.

Every elapsed-time label is retained: earlier arrival does not dominate later
arrival when turns may open later. Search budget exhaustion is never no-route.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from heapq import heappop, heappush
from itertools import count
from zoneinfo import ZoneInfo
from map_data.conditions import parse_schedule, active, RULES
from navigation_core.core import Result, Vehicle

class IncompleteTimeSearch(RuntimeError):pass
@dataclass(frozen=True)
class WeeklyBan:
    value: str
    schedule: tuple
    def active(self,local):
        if not isinstance(local,datetime) or local.utcoffset() is None:raise ValueError('Aware datetime required')
        return active(self.schedule,local)
@dataclass(frozen=True)
class Restriction:
    kind: str
    roads: tuple
    condition: WeeklyBan | None = None
    def __post_init__(self):
        object.__setattr__(self,'roads',tuple(self.roads))
        if self.kind not in ('no','only') or len(self.roads)<2:raise ValueError('Invalid restriction')
        if self.condition and self.kind!='no':raise ValueError('Timed only rules not supported by time-expanded search')

def parse_conditional(text):
    import re
    m=re.fullmatch(r'\s*([a-z_]+)\s*@\s*(?:\(([^()]*)\)|([^()]*))\s*',text)
    if not m or m[1] not in RULES or not m[1].startswith('no_'):raise ValueError('Time-expanded search supports one weekly turn ban')
    return WeeklyBan(m[1],parse_schedule(m[2] if m[2] is not None else m[3]))

def time_route(prepared,start,target,inbound,departure,timezone_name,max_states):
    timed=tuple((tuple(prepared.edge_ids[n] for n in rule.roads),rule.condition)
                for rule in prepared.timed_restrictions)
    return timed_core_route(prepared.prepared_router,timed,start,target,inbound,
                            departure,timezone_name,max_states,Vehicle('car'))

def timed_core_route(router,timed,start,target,inbound,departure,timezone_name,max_states,vehicle):
    if not isinstance(departure,datetime) or departure.utcoffset() is None:raise ValueError('Aware departure required')
    if not isinstance(max_states,int) or isinstance(max_states,bool) or max_states<1:raise ValueError('Positive search budget required')
    zone_name=timezone_name or getattr(departure.tzinfo,'key',None)
    if not zone_name:raise ValueError('An explicit IANA road timezone is required')
    zone=ZoneInfo(zone_name)
    clock=departure.astimezone(timezone.utc)
    # Static reachability proof avoids searching cycles when no route can exist.
    if router.route(start,target,vehicle,'dijkstra',inbound) is None:return None
    timed_actions={}
    for seq,cond in timed:timed_actions.setdefault(seq[-1],[]).append((seq,cond))
    max_history=max([len(seq)-1 for seq,_ in timed]+[router._max_prefix,1])
    serial=count();begin=(start,tuple(inbound[-max_history:]),0)
    pending=[(0,next(serial),begin)];seen={begin};parent={};expanded=0
    while pending:
        cost,_,state=heappop(pending);node,history,_=state
        expanded+=1
        if expanded>max_states:raise IncompleteTimeSearch('Time-label search budget exhausted; no conclusion')
        if node==target:
            path=[];at=state
            while at!=begin:
                at,e=parent[at];path.append(e)
            return Result(tuple(reversed(path)),cost,expanded)
        local=(clock+timedelta(microseconds=cost)).astimezone(zone)
        prefix=router._prefix(history)
        for edge in router._out[node]:
            if vehicle.kind not in edge.vehicles or router._advance(prefix,edge.id,vehicle.kind) is None:continue
            if any(limit is not None and (actual is None or actual>limit) for limit,actual in ((edge.max_height,vehicle.height),(edge.max_weight,vehicle.weight))):continue
            if any(len(history)>=len(seq)-1 and history[-(len(seq)-1):]==seq[:-1] and edge.id==seq[-1] and cond.active(local) for seq,cond in timed_actions.get(edge.id,())):continue
            turn=router._turns.get((history[-1],edge.id),0) if history else 0
            later_cost=cost+edge.cost+turn
            later=(edge.v,(history+(edge.id,))[-max_history:],later_cost)
            if later not in seen:
                if len(seen)>=max_states:raise IncompleteTimeSearch('Time-label storage budget exhausted; no conclusion')
                seen.add(later);parent[later]=(state,edge.id)
                heappush(pending,(later_cost,next(serial),later))
    return None
