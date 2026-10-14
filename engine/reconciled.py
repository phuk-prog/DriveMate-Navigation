"""Bridge bounded importer graphs to the independently authored navigation core.

Original algorithms remain available as references. No inferred road permissions.
Time is explicitly quantized to integer microseconds, rounding each edge upward.
Imported graphs currently describe motorcar access only; no bus rights are inferred.
"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING
from types import MappingProxyType
from math import isfinite
from datetime import datetime, timezone, timedelta
from .routing import Route, RouteNotFound
from .restrictions import time_route
from navigation_core.core import Graph, Edge, Rule, Router, Vehicle
from navigation_core.endpoints import Position
from navigation_core.journey import Journey
from navigation_core.native_adapter import run

@dataclass(frozen=True)
class Restriction:
    kind: str
    roads: tuple

@dataclass(frozen=True)
class PreparedNavigation:
    graph: Graph
    node_ids: object
    edge_ids: object
    edge_names: object
    source_edges: object
    prepared_router: object
    validity_window: object = None
    timed_restrictions: tuple = ()
    roundabout_catalog: object = None
    coordinates: object = None
    lane_connections: object = None
    cost_unit: str = 'microseconds, per-road ceiling'

    def position(self,road,fraction):
        if road not in self.edge_ids:raise ValueError('Unknown road')
        return Position(self.edge_ids[road],fraction)

    def road_names(self,ids):
        return tuple(self.edge_names[i] for i in ids)

    def route(self,source,destination,*,inbound=(),backend='research',mode='alt',departure=None,timezone_name=None,max_states=100000):
        if mode not in ('dijkstra','astar','alt'):raise ValueError('Unknown search mode')
        if self.validity_window:
            if not isinstance(departure,datetime) or departure.utcoffset() is None:
                raise ValueError('Conditional routing requires an aware departure time')
            departure=departure.astimezone(timezone.utc)
            if not self.validity_window[0]<=departure<self.validity_window[1]:
                raise ValueError('Departure outside compiled restriction window')
        if source not in self.node_ids or destination not in self.node_ids:
            raise ValueError('Unknown routing node')
        history=tuple(inbound)
        if any(e not in self.edge_ids for e in history):raise ValueError('Unknown inbound road')
        if any(self.source_edges[a].target!=self.source_edges[b].source for a,b in zip(history,history[1:])):
            raise ValueError('Disconnected inbound history')
        if history and self.source_edges[history[-1]].target!=source:
            raise ValueError('Inbound history must end at origin')
        a,b=self.node_ids[source],self.node_ids[destination]
        h=tuple(self.edge_ids[e] for e in history)
        v=Vehicle('car')
        landmarks=tuple(list(self.node_ids.values())[:1]+list(self.node_ids.values())[-1:])
        if self.timed_restrictions:
            if backend!='research':raise ValueError('Portable time-expanded search is not implemented; use a compiled window')
            result=time_route(self,a,b,h,departure,timezone_name,max_states)
        elif backend=='research':result=self.prepared_router.route(a,b,v,mode,h)
        elif backend=='portable':
            _,results=run(self.graph,[(mode,a,b,v,h)],landmarks)
            result=results[0][0]
        else:raise ValueError('Unknown backend')
        if result is None:raise RouteNotFound('No legal route in reconciled graph')
        if self.validity_window and departure+timedelta(microseconds=result.cost)>=self.validity_window[1]:
            raise ValueError('Route outlasts compiled restriction window; reimport a larger interval')
        names=self.road_names(result.edges)
        return Route(names,sum(self.source_edges[n].length_m for n in names),result.cost/1000000,
                    tuple(n for n in names if self.source_edges[n].access=='unknown'))

    def roundabouts(self,route,*,inbound=(),departure=None,timezone_name=None):
        from .roundabouts import identify
        return identify(self,route,inbound,departure,timezone_name)

    def junctions(self,route,*,inbound=(),departure=None,timezone_name=None):
        from .junctions import identify_junctions
        return identify_junctions(self,route,inbound,departure,timezone_name)

    def journey(self,destination_road,fraction,vehicle=None,*,timezone_name=None,max_states=100000):
        v=vehicle or Vehicle('car')
        if v.kind!='car':raise ValueError('Imported graph supplies motorcar access only')
        if self.validity_window or self.timed_restrictions:
            from .timed_journey import ClockJourney
            session=ClockJourney(self,v,self.position(destination_road,fraction),timezone_name,max_states)
        else:session=Journey(self.graph,v,self.position(destination_road,fraction))
        return AccessAwareJourney(session,self)

@dataclass(frozen=True)
class AccessSnapshot:
    position: Position
    timestamp: float
    status: str
    roads: tuple
    cost: int | None
    wrong_turn: bool
    unverified_access_edges: tuple

class AccessAwareJourney:
    """Preserve uncertainty in journey outputs without altering road permissions."""
    def __init__(self,session,prepared):
        self._session=session;self._prepared=prepared;self._junction_cache=None
        from .live_roundabouts import RoundaboutProgress
        self._roundabout_progress=RoundaboutProgress(prepared,session)

    def _annotate(self,s):
        if s is None:return None
        names=self._prepared.road_names(s.roads)
        return AccessSnapshot(s.position,s.timestamp,s.status,s.roads,s.cost,s.wrong_turn,
            tuple(n for n in names if self._prepared.source_edges[n].access=='unknown'))

    @property
    def snapshot(self):return self._annotate(self._session.snapshot)

    def roundabouts(self):
        return self._roundabout_progress.instructions(self._session.snapshot)

    def junctions(self):
        snapshot=self._session.snapshot
        if snapshot is None or snapshot.status!='navigating':return ()
        if self._junction_cache is not None and self._junction_cache[0] is snapshot:return self._junction_cache[1]
        from .junctions import identify_junctions
        names,hist,clock,zone,q0,q1=self._roundabout_progress.remaining_path(snapshot)
        result=identify_junctions(self._prepared,Route(names,0,0),hist,clock,zone,origin_fraction=q0,destination_fraction=q1,actual_origin=True)
        self._junction_cache=(snapshot,result)
        return result

    def start(self,position,timestamp,inbound=()):
        history=tuple(inbound)
        result=self._session.start(position,timestamp,history)
        self._roundabout_progress.start(result,history)
        return self._annotate(result)

    def observe(self,position,timestamp):
        previous=self._session.snapshot;history=self._session._history
        result=self._session.observe(position,timestamp)
        if previous is not None and result.timestamp>previous.timestamp:
            self._roundabout_progress.observe(previous,result,history)
        return self._annotate(result)

def prepare_navigation(source,coordinates=None,*,restrictions=()):
    node_ids={n:i for i,n in enumerate(sorted(source.vertices))}
    edge_ids={n:i for i,n in enumerate(sorted(source.edges))}
    points=dict(coordinates or {})
    if any(n not in node_ids for n in points):raise ValueError('Unknown coordinate node')
    nodes=[]
    for n,i in node_ids.items():
        lat,lon=points.get(n,(0.,0.))
        if not isfinite(lat) or not isfinite(lon) or abs(lat)>90 or abs(lon)>180:
            raise ValueError('Invalid geographic coordinates')
        nodes.append((i,lon,lat))
    edges=[]
    for name,i in edge_ids.items():
        e=source.edges[name]
        seconds=e.estimated_seconds
        if not isfinite(seconds) or seconds<=0:raise ValueError('Invalid road cost')
        cost=int((Decimal(str(seconds))*1000000).to_integral_value(rounding=ROUND_CEILING))
        edges.append(Edge(i,node_ids[e.source],node_ids[e.target],cost,
                    frozenset({'car'}) if e.access!='prohibited' else frozenset()))
    rules=[Rule('no',(edge_ids[a],edge_ids[b]),frozenset({'car'})) for a,b in sorted(source.prohibited_turns)]
    for r in tuple(source.multi_restrictions)+tuple(restrictions):
        if any(name not in edge_ids for name in r.roads):raise ValueError('Unknown restriction road')
        rules.append(Rule(r.kind,tuple(edge_ids[n] for n in r.roads),frozenset({'car'})))
    timed=tuple(r for r in source.extended_restrictions if getattr(r,'condition',None))
    # Validate timed sequences through the same graph connectivity contract.
    for r in timed:
        if any(name not in edge_ids for name in r.roads):raise ValueError('Unknown timed restriction road')
        Graph(tuple(nodes),tuple(edges),(Rule(r.kind,tuple(edge_ids[n] for n in r.roads),frozenset({'car'})),))
    graph=Graph(tuple(nodes),tuple(edges),tuple(rules))
    landmarks=tuple(list(node_ids.values())[:1]+list(node_ids.values())[-1:])
    connections={}
    for c in source.lane_connections:connections.setdefault((c.from_road,c.to_road),[]).append(c)
    from .roundabouts import RoundaboutCatalog
    return PreparedNavigation(graph,
          MappingProxyType(node_ids),MappingProxyType(edge_ids),MappingProxyType({i:n for n,i in edge_ids.items()}),
          MappingProxyType(dict(source.edges)),Router(graph,landmarks),source.validity_window,timed,RoundaboutCatalog(source,graph,{i:n for n,i in edge_ids.items()}),MappingProxyType(points),MappingProxyType({k:tuple(v) for k,v in connections.items()}))
