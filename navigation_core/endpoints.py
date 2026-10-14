"""Directed-road endpoint overlay; prototype, not GPS snapping or address selection.

Fractions are millionths. Uniform edge costs are partitioned by cumulative integer
floor, conserving full-road cost. Start road is the observed current directed road.
Supplied inbound history precedes that road and is actual history, not a proposed turn.
"""
from dataclasses import dataclass
from .core import Graph,Edge,Rule

SCALE=1000000


@dataclass(frozen=True)
class Position:
    edge: int
    fraction: int

    def __post_init__(self):
        if not isinstance(self.edge,int) or isinstance(self.edge,bool):
            raise ValueError("edge ID must be integer")
        if not isinstance(self.fraction,int) or isinstance(self.fraction,bool) or not 0<=self.fraction<=SCALE:
            raise ValueError("fraction must be integer millionths in [0,1000000]")


def permitted(edge,vehicle):
    return vehicle.kind in edge.vehicles and all(
        limit is None or actual is not None and actual<=limit
        for limit,actual in ((edge.max_height,vehicle.height),(edge.max_weight,vehicle.weight)))


def prepare(g,origin,target,inbound,vehicle):
    byid={e.id:e for e in g.edges}
    if origin.edge not in byid or target.edge not in byid:
        raise ValueError("unknown endpoint edge")
    history=tuple(inbound)
    if any(e not in byid for e in history) or any(byid[a].v!=byid[b].u for a,b in zip(history,history[1:])):
        raise ValueError("invalid inbound history")
    if history and byid[history[-1]].v!=byid[origin.edge].u:
        raise ValueError("history must precede current origin road")
    if not permitted(byid[origin.edge],vehicle) or not permitted(byid[target.edge],vehicle):
        return None
    nodes=list(g.nodes);points={n:(x,y) for n,x,y in g.nodes}
    nextnode=min(points,default=0)-1
    nextedge=min(byid,default=0)-1
    selected={}
    selected.setdefault(origin.edge,set()).add(origin.fraction)
    selected.setdefault(target.edge,set()).add(target.fraction)
    lookup={};replacement={};edges=[];aliases={}
    before_origin=[]
    for edge in g.edges:
        if edge.id not in selected:
            replacement[edge.id]=(edge.id,)
            edges.append(edge);aliases[edge.id]=(edge.id,0,SCALE)
            continue
        cuts=[(0,edge.u)]
        for q in sorted(selected[edge.id]):
            n=nextnode;nextnode-=1
            x0,y0=points[edge.u];x1,y1=points[edge.v];f=q/SCALE
            nodes.append((n,x0*(1-f)+x1*f,y0*(1-f)+y1*f))
            cuts.append((q,n));lookup[(edge.id,q)]=n
        cuts.append((SCALE,edge.v))
        ids=[]
        for (q0,n0),(q1,n1) in zip(cuts,cuts[1:]):
            eid=nextedge;nextedge-=1
            cost=edge.cost*q1//SCALE-edge.cost*q0//SCALE
            edges.append(Edge(eid,n0,n1,cost,edge.vehicles,edge.max_height,edge.max_weight))
            aliases[eid]=(edge.id,q0,q1);ids.append(eid)
            if edge.id==origin.edge and n1 in {lookup[(origin.edge,origin.fraction)]}:
                before_origin=list(ids)
        replacement[edge.id]=tuple(ids)
    rules=[]
    for rule in g.rules:
        # Restrictions trigger on ENTRY to final road, not completion. Mapping
        # to its last piece would permit stopping inside a prohibited road.
        seq=[replacement[rule.edges[0]][-1]]
        for eid in rule.edges[1:-1]:
            seq.extend(replacement[eid])
        seq.append(replacement[rule.edges[-1]][0])
        rules.append(Rule(rule.kind,tuple(seq),rule.vehicles))
    turns=tuple((replacement[a][-1],replacement[b][0],cost) for a,b,cost in g.turn_costs)
    expanded=tuple(piece for eid in history for piece in replacement[eid])+tuple(before_origin)
    return (Graph(tuple(nodes),tuple(edges),tuple(rules),turns),
            lookup[(origin.edge,origin.fraction)],lookup[(target.edge,target.fraction)],expanded,aliases)
