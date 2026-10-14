"""Endpoint cost oracle on ORIGINAL roads; does not use the split-road overlay."""
from collections import deque
from math import inf
from .oracle import allowed

def endpoint_cost(g, origin, target, vehicle, inbound=()):
    edges={e.id:e for e in g.edges}
    current=edges[origin.edge]; final=edges[target.edge]
    def accessible(e):
        return vehicle.kind in e.vehicles and all(limit is None or actual is not None and actual<=limit
            for limit,actual in ((e.max_height,vehicle.height),(e.max_weight,vehicle.weight)))
    if not accessible(current) or not accessible(final): return inf
    scale=1000000
    best=inf
    if current.id==final.id and origin.fraction<=target.fraction:
        best=current.cost*target.fraction//scale-current.cost*origin.fraction//scale
    memory=max([1]+[len(r.edges)-1 for r in g.rules])
    initial=(current.v,(tuple(inbound)+(current.id,))[-memory:])
    initial_cost=current.cost-current.cost*origin.fraction//scale
    penalties={(a,b):c for a,b,c in g.turn_costs}
    todo=deque([initial]); states={initial}; arcs=[]; finishes=[]
    while todo:
        state=todo.popleft(); node,history=state
        for e in g.edges:
            if e.u!=node or not allowed(g,history,e,vehicle): continue
            penalty=penalties.get((history[-1],e.id),0)
            if e.id==final.id:
                finishes.append((state,penalty+e.cost*target.fraction//scale))
            nxt=(e.v,(history+(e.id,))[-memory:])
            arcs.append((state,nxt,penalty+e.cost))
            if nxt not in states: states.add(nxt); todo.append(nxt)
    distance={s:inf for s in states}; distance[initial]=initial_cost
    for _ in range(len(states)-1):
        changed=False
        for a,b,c in arcs:
            if distance[a]+c<distance[b]: distance[b]=distance[a]+c; changed=True
        if not changed: break
    return min([best]+[distance[s]+c for s,c in finishes])
