"""Resolve original bounded OSM turn relations to directed road sequences."""
from dataclasses import dataclass
from .conditions import RULES
@dataclass(frozen=True)
class ImportedRestriction:
    kind: str
    roads: tuple[str,...]

def resolve(members,rule,ways,edges,incoming,leaving):
    if rule not in RULES:raise ValueError('Unsupported turn restriction')
    frm=[m.get('ref') for m in members if m.get('role')=='from' and m.get('type')=='way']
    to=[m.get('ref') for m in members if m.get('role')=='to' and m.get('type')=='way']
    via=[m for m in members if m.get('role')=='via']
    if len(frm)!=1 or len(to)!=1 or not via or len(members)!=len(via)+2:
        raise ValueError('Unsupported restriction members')
    if any(x not in ways for x in frm+to):raise ValueError('Missing restriction way')
    if len(via)==1 and via[0].get('type')=='node':
        node='osm:'+str(via[0].get('ref'))
        middle=()
        entry=exit=node
    else:
        if any(m.get('type')!='way' for m in via):raise ValueError('Mixed via types')
        chain=frm+[m.get('ref') for m in via]+to
        if len(set(chain))!=len(chain):raise ValueError('Repeated via/from/to ways need review')
        if any(w not in ways for w in chain):raise ValueError('Missing via way')
        joins=[]
        for a,b in zip(chain,chain[1:]):
            shared=set(ways[a][0]) & set(ways[b][0])
            if len(shared)!=1:raise ValueError('Disconnected or ambiguous via-way chain')
            joins.append(next(iter(shared)))
        middle=[]
        for i,w in enumerate(chain[1:-1]):
            refs=ways[w][0]
            if len(set(refs))!=len(refs):raise ValueError('Looped via-way needs review')
            a,b=refs.index(joins[i]),refs.index(joins[i+1])
            if a==b:raise ValueError('Empty via traversal')
            ids=([f'w:{w}:{j}:f' for j in range(a,b)] if a<b else [f'w:{w}:{j}:r' for j in range(a-1,b-1,-1)])
            if any(e not in edges for e in ids):raise ValueError('Via traversal contradicts driving direction')
            middle.extend(ids)
        if len(middle)>256:raise ValueError('Via traversal exceeds prototype bound')
        middle=tuple(middle);entry,exit=joins[0],joins[-1]
    arrivals=incoming.get((frm[0],entry),[]);departures=leaving.get((to[0],exit),[])
    sequences=[]
    for a in arrivals:
        for b in departures:
            if frm==to:
                if rule in ('no_u_turn','only_u_turn'):
                    if a.source!=b.target:continue
                elif rule in ('no_straight_on','only_straight_on'):
                    if a.source==b.target:continue
                else:raise ValueError('Ambiguous same-way turn type')
            sequences.append((a.edge_id,)+middle+(b.edge_id,))
    if not sequences:raise ValueError('Restriction has no directed manoeuvre')
    # Multiple forced successors cannot be represented by this core's only rule.
    if rule.startswith('only_'):
        nexts={}
        for seq in sequences:
            for i in range(1,len(seq)):nexts.setdefault(seq[:i],set()).add(seq[i])
        if any(len(v)>1 for v in nexts.values()):raise ValueError('Ambiguous mandatory successors need review')
    return tuple(ImportedRestriction('no' if rule.startswith('no_') else 'only',s) for s in sequences)
