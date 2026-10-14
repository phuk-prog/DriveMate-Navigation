"""Independent finite-history state enumeration + Bellman-Ford; no core helpers."""
from collections import deque
from math import inf


def allowed(g, history, edge, vehicle):
    if vehicle.kind not in edge.vehicles:
        return False
    if edge.max_height is not None and (vehicle.height is None or vehicle.height > edge.max_height):
        return False
    if edge.max_weight is not None and (vehicle.weight is None or vehicle.weight > edge.max_weight):
        return False
    for r in g.rules:
        if vehicle.kind not in r.vehicles:
            continue
        seq = r.edges
        if r.kind == "no":
            trial = history + (edge.id,)
            if len(trial) >= len(seq) and trial[-len(seq):] == seq:
                return False
        else:
            for n in range(1, len(seq)):
                if len(history) >= n and history[-n:] == seq[:n] and edge.id != seq[n]:
                    return False
    return True


def oracle(g, start, target, vehicle, inbound=()):
    memory = max([1] + [len(r.edges) - 1 for r in g.rules])
    initial = (start, tuple(inbound[-memory:]))
    pending, states, arcs = deque([initial]), {initial}, []
    by_id = {e.id: e for e in g.edges}
    penalties = {(a, b): cost for a, b, cost in g.turn_costs}
    while pending:
        state = pending.popleft()
        node, history = state
        for edge in g.edges:
            if edge.u != node or not allowed(g, history, edge, vehicle):
                continue
            nxt = (edge.v, (history + (edge.id,))[-memory:])
            cost = edge.cost + penalties.get((history[-1], edge.id), 0) if history else edge.cost
            arcs.append((state, nxt, cost))
            if nxt not in states:
                states.add(nxt)
                pending.append(nxt)
    dist = {s: inf for s in states}
    dist[initial] = 0
    for _ in range(len(states) - 1):
        changed = False
        for a, b, cost in arcs:
            if dist[a] + cost < dist[b]:
                dist[b] = dist[a] + cost
                changed = True
        if not changed:
            break
    return min((d for (node, _), d in dist.items() if node == target), default=inf)


def validate_route(g, start, target, vehicle, inbound, result):
    history, node, cost = tuple(inbound), start, 0
    by_id = {e.id: e for e in g.edges}
    penalties = {(a, b): c for a, b, c in g.turn_costs}
    for eid in result.edges:
        e = by_id[eid]
        assert e.u == node and allowed(g, history, e, vehicle)
        cost += e.cost + (penalties.get((history[-1], eid), 0) if history else 0)
        history += (eid,)
        node = e.v
    assert node == target
    assert cost == result.cost
