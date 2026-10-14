"""Original line-protocol adapter. Native schema supports car/bus static graphs."""
from pathlib import Path
from dataclasses import dataclass
import subprocess

ROOT=Path(__file__).parent
KINDS={"car":0,"bus":1}


def mask(kinds):
    if any(k not in KINDS for k in kinds):
        raise ValueError("native schema currently supports car/bus only")
    return sum(1<<KINDS[k] for k in kinds)


def dim(value):
    return -1 if value is None else value


def encode(graph, queries, landmarks=()):
    text=[f"DMNAV1 {len(graph.nodes)} {len(graph.edges)} {len(graph.rules)} {len(graph.turn_costs)}"]
    text.extend(f"{n} {x:.17g} {y:.17g}" for n,x,y in graph.nodes)
    text.extend(f"{e.id} {e.u} {e.v} {e.cost} {mask(e.vehicles)} {dim(e.max_height)} {dim(e.max_weight)}" for e in graph.edges)
    text.extend(f"{r.kind} {mask(r.vehicles)} {len(r.edges)} "+" ".join(map(str,r.edges)) for r in graph.rules)
    text.extend(f"{a} {b} {c}" for a,b,c in graph.turn_costs)
    text.append(str(len(landmarks))+" "+" ".join(map(str,landmarks)))
    text.append(str(len(queries)))
    for mode,a,b,v,history in queries:
        if v.kind not in KINDS:
            raise ValueError("unsupported native vehicle")
        text.append(f"{mode} {a} {b} {KINDS[v.kind]} {dim(v.height)} {dim(v.weight)} {len(history)} "+" ".join(map(str,history)))
    return "\n".join(text)+"\n"


@dataclass
class NativeResult:
    edges: tuple
    cost: int
    expanded: int
    nanoseconds: int


def run(graph, queries, landmarks=(), executable=None):
    binary=Path(executable or ROOT/"native"/"router")
    proc=subprocess.run([str(binary)],input=encode(graph,queries,landmarks),text=True,
                        capture_output=True,timeout=60)
    if proc.returncode:
        raise ValueError(proc.stderr.strip())
    lines=proc.stdout.splitlines()
    if len(lines)!=len(queries)+1 or not lines[0].startswith("READY "):
        raise ValueError("native protocol response mismatch")
    result=[]
    for line in lines[1:]:
        fields=line.split()
        if fields[0]=="NONE":
            result.append((None,int(fields[1])))
        elif fields[0]=="FOUND":
            cost,expanded,ns,count=map(int,fields[1:5])
            ids=tuple(map(int,fields[5:]))
            if len(ids)!=count:
                raise ValueError("native path length mismatch")
            result.append((NativeResult(ids,cost,expanded,ns),ns))
        else:
            raise ValueError("unknown native result")
    return int(lines[0].split()[1]),result
