"""Unseen synthetic fixture family. Fixed seeds; no real road data."""
import random
from collections import defaultdict
from .core import Edge, Rule, Graph, Vehicle


def fixture(size, seed, split=False):
    rng=random.Random(seed)
    nodes=tuple((y*size+x,float(x),float(y)) for y in range(size) for x in range(size))
    edges=[]
    outgoing=defaultdict(list)
    for n,x,y in nodes:
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            xx,yy=int(x)+dx,int(y)+dy
            if not(0<=xx<size and 0<=yy<size):
                continue
            if split and dy==0 and min(int(x),xx)==size//2-1:
                continue
            # Guaranteed directed outer boundary; asymmetric interior road costs.
            if dx==-1 and int(y)%4==1 and 0<int(x)<size-1:
                continue
            e=Edge(len(edges),n,yy*size+xx,10+rng.randrange(21),
                   max_height=2.1 if len(edges)%67==0 else None)
            edges.append(e)
            outgoing[n].append(e)
    rules=[]
    for e in edges[::31]:
        seq=[e]
        for _ in range(rng.choice((1,2,3))):
            nxt=[f for f in outgoing[seq[-1].v] if f.v!=seq[-1].u]
            if not nxt:
                break
            seq.append(rng.choice(nxt))
        if len(seq)>1:
            rules.append(Rule("only" if e.id%5==0 else "no",tuple(f.id for f in seq)))
    turns=tuple((e.id,f.id,7) for e in edges[::59] for f in outgoing[e.v] if f.v!=e.u)
    return Graph(nodes,tuple(edges),tuple(rules),turns)


def cases(g, seed, count=8):
    rng=random.Random(seed)
    ids=[n for n,*_ in g.nodes]
    # Interior endpoints chosen without consulting algorithm outputs or landmarks.
    result=[]
    incoming=defaultdict(list)
    for e in g.edges:
        incoming[e.v].append(e.id)
    for i in range(count):
        a,b=rng.sample(ids,2)
        hist=tuple(g.rules[i%len(g.rules)].edges[:-1]) if i%3==0 and g.rules else ()
        if hist:
            a={e.id:e.v for e in g.edges}[hist[-1]]
        result.append((a,b,hist,Vehicle(height=1.8,weight=2)))
    return result
