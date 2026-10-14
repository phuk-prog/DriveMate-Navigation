"""Original navigation session over trusted directed-road observations.

Not a GPS matcher: callers must supply actual contiguous road traversal. A new
road observation means the previous road was completed. Skipped roads are rejected.
No public-road or Android readiness claim. Backend is the verified native core.
"""
from dataclasses import dataclass
from math import isfinite
from .endpoints import Position, prepare
from .native_adapter import run

@dataclass(frozen=True)
class Snapshot:
    position: Position
    timestamp: float
    status: str
    roads: tuple
    cost: int | None
    wrong_turn: bool = False

class Journey:
    def __init__(self, graph, vehicle, destination):
        self._graph=graph; self._vehicle=vehicle; self._destination=destination
        self._edges={e.id:e for e in graph.edges}
        if not isinstance(destination,Position) or destination.edge not in self._edges:
            raise ValueError('Unknown destination road')
        self._memory=max([1]+[len(r.edges)-1 for r in graph.rules])
        self._history=(); self._snapshot=None

    @property
    def snapshot(self):
        return self._snapshot

    def _validate(self,position,timestamp):
        if not isinstance(position,Position) or position.edge not in self._edges:
            raise ValueError('Unknown current road')
        if isinstance(timestamp,bool) or not isinstance(timestamp,(int,float)) or not isfinite(timestamp):
            raise ValueError('Timestamp must be finite')

    def _calculate(self,position,timestamp,history,wrong_turn=False):
        overlay=prepare(self._graph,position,self._destination,history,self._vehicle)
        if overlay is None:
            return Snapshot(position,timestamp,'no_route',(),None,wrong_turn)
        graph,a,b,inbound,aliases=overlay
        _,results=run(graph,[('alt',a,b,self._vehicle,inbound)])
        result=results[0][0]
        if result is None:
            return Snapshot(position,timestamp,'no_route',(),None,wrong_turn)
        roads=[]
        for eid in result.edges:
            w,q0,q1=aliases[eid]
            if q1>q0 and (not roads or roads[-1]!=w):roads.append(w)
        arrived=position==self._destination
        return Snapshot(position,timestamp,'arrived' if arrived else 'navigating',tuple(roads),result.cost,wrong_turn)

    def _same_road(self,position,timestamp,history,previous,wrong):
        # Static plans can reuse remaining costs without another search.
        consumed=(self._edges[position.edge].cost*position.fraction//1000000-
                  self._edges[position.edge].cost*previous.position.fraction//1000000)
        roads=previous.roads
        if position.fraction==1000000 and roads and roads[0]==position.edge:roads=roads[1:]
        return Snapshot(position,timestamp,previous.status,roads,
                        None if previous.cost is None else max(0,previous.cost-consumed),wrong)

    def start(self,position,timestamp,inbound=()):
        if self._snapshot is not None: raise ValueError('Journey already started')
        self._validate(position,timestamp)
        history=tuple(inbound)
        result=self._calculate(position,timestamp,history)
        self._history=history[-self._memory:];self._snapshot=result
        return result

    def observe(self,position,timestamp):
        if self._snapshot is None:raise ValueError('Journey not started')
        self._validate(position,timestamp)
        previous=self._snapshot
        if timestamp<=previous.timestamp:raise ValueError('Stale or out-of-order observation')
        if previous.status=='arrived':return previous
        changed=position.edge!=previous.position.edge
        if changed:
            if self._edges[previous.position.edge].v!=self._edges[position.edge].u:
                raise ValueError('Discontinuous road observation: supply intermediate roads')
            history=(self._history+(previous.position.edge,))[-self._memory:]
        else:
            if position.fraction<previous.position.fraction:
                raise ValueError('Backwards progress requires actual intervening roads')
            history=self._history
        expected=list(previous.roads)
        if expected and expected[0]==previous.position.edge:expected.pop(0)
        wrong=changed and previous.status=="navigating" and bool(expected) and position.edge!=expected[0]
        crossed=(position.edge==self._destination.edge and position.fraction>=self._destination.fraction and
                 (changed or previous.position.fraction<=self._destination.fraction))
        # Evaluate access before declaring arrival. A trusted observed illegal turn
        # is actual history, never a permission added to the graph.
        if changed:
            result=self._calculate(position,timestamp,history,wrong)
        else:
            result=self._same_road(position,timestamp,history,previous,wrong)
        if crossed and prepare(self._graph,position,self._destination,history,self._vehicle) is not None:
            result=Snapshot(position,timestamp,'arrived',(),0,wrong)
        self._history=history;self._snapshot=result
        return result
