"""Original DriveMate research routing core, schema 1. Integer nonnegative cost units.

No third-party code/map data. Static snapshot only; conditional restrictions are not
supported. Coordinates are Cartesian fixture units, not latitude/longitude.
"""
from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import count
from math import dist, isfinite, floor
from types import MappingProxyType
from collections import OrderedDict, defaultdict


def nonnegative(value, name, integer=False):
    if integer and (not isinstance(value,int) or isinstance(value,bool) or value > 2**53-1):
        raise ValueError(name + " must be an integer <= 2^53-1")
    if isinstance(value, bool) or not isinstance(value, (int,float)) or not isfinite(value) or value < 0:
        raise ValueError(name + " must be finite and nonnegative")
    if integer and (not isinstance(value,int) or value > 2**53-1):
        raise ValueError(name + " must be an integer <= 2^53-1")


@dataclass(frozen=True)
class Vehicle:
    kind: str = "car"
    height: float | None = None
    weight: float | None = None

    def __post_init__(self):
        if not isinstance(self.kind,str) or not self.kind:
            raise ValueError("vehicle kind required")
        for name in ("height","weight"):
            if getattr(self,name) is not None:
                nonnegative(getattr(self,name),name)


@dataclass(frozen=True)
class Edge:
    id: int
    u: int
    v: int
    cost: int
    vehicles: frozenset = frozenset({"car","bus"})
    max_height: float | None = None
    max_weight: float | None = None

    def __post_init__(self):
        object.__setattr__(self,"vehicles",frozenset(self.vehicles))
        if any(not isinstance(n,int) or isinstance(n,bool) for n in (self.id,self.u,self.v)):
            raise ValueError("edge and node IDs must be integers")
        nonnegative(self.cost,"cost",True)
        for n in ("max_height","max_weight"):
            if getattr(self,n) is not None:
                nonnegative(getattr(self,n),n)


@dataclass(frozen=True)
class Rule:
    kind: str
    edges: tuple
    vehicles: frozenset = frozenset({"car","bus"})

    def __post_init__(self):
        object.__setattr__(self,"edges",tuple(self.edges))
        object.__setattr__(self,"vehicles",frozenset(self.vehicles))
        if self.kind not in ("no","only") or len(self.edges)<2:
            raise ValueError("rule requires no/only and >=2 edges")


@dataclass(frozen=True)
class Graph:
    nodes: tuple
    edges: tuple
    rules: tuple = ()
    turn_costs: tuple = ()

    def __post_init__(self):
        for name in ("nodes","turn_costs"):
            object.__setattr__(self,name,tuple(tuple(x) for x in getattr(self,name)))
        for name in ("edges","rules"):
            object.__setattr__(self,name,tuple(getattr(self,name)))
        ids=set()
        for n,x,y in self.nodes:
            if not isinstance(n,int) or isinstance(n,bool) or n in ids or not all(isfinite(c) for c in (x,y)):
                raise ValueError("invalid or duplicate node")
            ids.add(n)
        by_id={}
        for e in self.edges:
            if e.id in by_id or e.u not in ids or e.v not in ids:
                raise ValueError("duplicate edge or missing endpoint")
            by_id[e.id]=e
        for r in self.rules:
            if any(e not in by_id for e in r.edges):
                raise ValueError("missing restriction edge")
            if any(by_id[a].v!=by_id[b].u for a,b in zip(r.edges,r.edges[1:])):
                raise ValueError("disconnected restriction")
        seen=set()
        for a,b,c in self.turn_costs:
            nonnegative(c,"turn cost",True)
            if (a,b) in seen or a not in by_id or b not in by_id or by_id[a].v!=by_id[b].u:
                raise ValueError("invalid turn cost pair")
            seen.add((a,b))


@dataclass(frozen=True)
class Result:
    edges: tuple
    cost: int
    expanded: int


class Router:
    def __init__(self, graph, landmarks=(), cache_capacity=8192):
        if not isinstance(cache_capacity,int) or isinstance(cache_capacity,bool) or cache_capacity<0:
            raise ValueError("cache capacity must be a nonnegative integer")
        self._graph=graph
        self._nodes=MappingProxyType({n:(x,y) for n,x,y in graph.nodes})
        self._edges=MappingProxyType({e.id:e for e in graph.edges})
        outgoing={n:[] for n in self._nodes}
        reverse={n:[] for n in self._nodes}
        for e in graph.edges:
            outgoing[e.u].append(e)
            reverse[e.v].append((e.u,e.cost))
        self._out=MappingProxyType({n:tuple(es) for n,es in outgoing.items()})
        self._reverse=MappingProxyType({n:tuple(es) for n,es in reverse.items()})
        self._turns=MappingProxyType({(a,b):c for a,b,c in graph.turn_costs})
        self._prefixes={r.edges[:i] for r in graph.rules for i in range(1,len(r.edges))}
        self._max_prefix=max(map(len,self._prefixes),default=0)
        self._cache_capacity=cache_capacity
        self._transitions=OrderedDict()
        # Index only actions triggered by a restriction prefix; every suffix can
        # trigger a distinct overlapping rule. No scan of unrelated rules at query time.
        direct=defaultdict(lambda: defaultdict(lambda: (set(),set())))
        for r in graph.rules:
            for kind in r.vehicles:
                if r.kind=="no":
                    direct[r.edges[:-1]][kind][0].add(r.edges[-1])
                else:
                    for i in range(1,len(r.edges)):
                        direct[r.edges[:i]][kind][1].add(r.edges[i])
        actions={}
        for prefix in self._prefixes:
            joined=defaultdict(lambda: (set(),set()))
            for i in range(len(prefix)):
                for kind,(forbid,require) in direct.get(prefix[i:],{}).items():
                    joined[kind][0].update(forbid)
                    joined[kind][1].update(require)
            actions[prefix]={kind:(frozenset(a),frozenset(b)) for kind,(a,b) in joined.items()}
        self._actions=actions
        ratios=[]
        for e in graph.edges:
            distance=dist(self._nodes[e.u],self._nodes[e.v])
            if not isfinite(distance):
                raise ValueError("coordinate distance overflow")
            if distance:
                ratios.append(e.cost/distance)
        self._scale=min(ratios,default=0)*(1-1e-12)
        if not isfinite(self._scale):
            self._scale=0
        self.landmarks=tuple(dict.fromkeys(landmarks))
        if any(n not in self._nodes for n in self.landmarks):
            raise ValueError("unknown landmark")
        self._landmarks=tuple((self._distances(n,False),self._distances(n,True)) for n in self.landmarks)

    @property
    def graph(self):
        return self._graph

    @property
    def cache_entries(self):
        return len(self._transitions)

    def _distances(self, source, reverse):
        adj=self._reverse if reverse else {n:tuple((e.v,e.cost) for e in es) for n,es in self._out.items()}
        distances={source:0}
        queue=[(0,source)]
        while queue:
            cost,n=heappop(queue)
            if cost!=distances[n]:
                continue
            for other,w in adj[n]:
                new=cost+w
                if new<distances.get(other,float("inf")):
                    distances[other]=new
                    heappush(queue,(new,other))
        return MappingProxyType(distances)

    def _prefix(self, history):
        for size in range(min(len(history),self._max_prefix),0,-1):
            suffix=history[-size:]
            if suffix in self._prefixes:
                return suffix
        return ()

    def _advance(self, prefix, eid, kind):
        key=(prefix,eid,kind)
        if key in self._transitions:
            self._transitions.move_to_end(key)
            return self._transitions[key]
        forbidden,required=self._actions.get(prefix,{}).get(kind,((),()))
        invalid=eid in forbidden or (required and (len(required)!=1 or eid not in required))
        nxt=None if invalid else self._prefix(prefix+(eid,))
        if self._cache_capacity:
            self._transitions[key]=nxt
            if len(self._transitions)>self._cache_capacity:
                self._transitions.popitem(last=False)
        return nxt

    def lower_bound(self, node, target, mode):
        if mode=="dijkstra":
            return 0
        raw=dist(self._nodes[node],self._nodes[target])*self._scale
        # Under/overflow must weaken a heuristic, never break route correctness.
        geometric=floor(raw) if isfinite(raw) else 0
        if mode=="astar":
            return geometric
        if mode!="alt":
            raise ValueError("unknown search mode")
        bound=geometric
        for forward,backward in self._landmarks:
            # Both operands must be finite; never compute infinity-infinity.
            if target in forward and node in forward:
                bound=max(bound,forward[target]-forward[node])
            if node in backward and target in backward:
                bound=max(bound,backward[node]-backward[target])
        return bound

    def route(self, start, target, vehicle=Vehicle(), mode="astar", inbound=()):
        if start not in self._nodes or target not in self._nodes or mode not in ("dijkstra","astar","alt"):
            raise ValueError("unknown node or search mode")
        inbound=tuple(inbound)
        if any(e not in self._edges for e in inbound):
            raise ValueError("unknown inbound edge")
        if inbound and (self._edges[inbound[-1]].v!=start or
                        any(self._edges[a].v!=self._edges[b].u for a,b in zip(inbound,inbound[1:]))):
            raise ValueError("inbound history must be continuous and end at start")
        initial=(start,inbound[-1] if inbound else None,self._prefix(inbound))
        best={initial:0}
        parent={}
        serial=count()
        queue=[(self.lower_bound(start,target,mode),0,next(serial),initial)]
        expanded=0
        while queue:
            _,cost,_,state=heappop(queue)
            if cost!=best[state]:
                continue
            node,incoming,prefix=state
            expanded+=1
            if node==target:
                path=[]
                cursor=state
                while cursor!=initial:
                    cursor,eid=parent[cursor]
                    path.append(eid)
                return Result(tuple(reversed(path)),cost,expanded)
            for e in self._out[node]:
                if vehicle.kind not in e.vehicles or (e.max_height is not None and (vehicle.height is None or vehicle.height>e.max_height)) or (e.max_weight is not None and (vehicle.weight is None or vehicle.weight>e.max_weight)):
                    continue
                nxt_prefix=self._advance(prefix,e.id,vehicle.kind)
                if nxt_prefix is None:
                    continue
                nxt=(e.v,e.id,nxt_prefix)
                total=cost+e.cost+self._turns.get((incoming,e.id),0)
                if total<best.get(nxt,float("inf")):
                    best[nxt]=total
                    parent[nxt]=(state,e.id)
                    heappush(queue,(total+self.lower_bound(e.v,target,mode),total,next(serial),nxt))
        return None
