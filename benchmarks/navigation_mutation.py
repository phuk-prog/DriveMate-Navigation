"""Adversarial routing correctness and defect-detection validation.

Every fault is an intentionally corrupt *separate* graph or request, never
a change to DriveMate code. Independent Bellman-Ford oracle from the
navigation-core validation package supplies the original correct answer.
The measured ratio of mutants detected is NOT navigation accuracy.
"""
import json, math
from dataclasses import replace
from pathlib import Path
from navigation_core.core import Edge, Rule, Vehicle, Graph, Router
from navigation_core.holdout import fixture, cases
from navigation_core.validation.oracle import oracle, validate_route

SEEDS=(117031,118719,120041,121217,122689,124093,125533,127019)
MODES=("dijkstra","astar","alt")

def base_graph(*,rule=None,height=None,weight=None,turn_penalty=False):
    links=(Edge(1,0,1,1), Edge(2,1,2,1,max_height=height,max_weight=weight),
           Edge(3,2,3,1),Edge(4,1,4,10),Edge(5,4,3,10),Edge(6,0,3,50))
    restrictions=() if rule is None else (Rule(*rule),)
    penalties=((1,2,30),) if turn_penalty else ()
    return Graph(tuple((i,float(i),float(i%2)) for i in range(5)),
                 links,restrictions,penalties)

def mutations():
    """Seven distinct independently specified safety/optimality faults."""
    cases=[]
    a=base_graph(rule=("no",(1,2,3)))
    cases.append(("ignored_via_way_no_turn",a,base_graph(),0,3,Vehicle(height=1.8,weight=2.0),(),()))
    b=base_graph(rule=("only",(1,4,5)))
    cases.append(("ignored_only_turn",b,base_graph(),0,3,Vehicle(height=1.8,weight=2.0),(),()))
    h=base_graph(height=2.0)
    cases.append(("ignored_bridge_height_limit",h,base_graph(),0,3,Vehicle(height=2.5,weight=2.0),(),()))
    w=base_graph(weight=3.0)
    cases.append(("ignored_vehicle_weight_limit",w,base_graph(),0,3,Vehicle(height=1.8,weight=3.5),(),()))
    t=base_graph(turn_penalty=True)
    cases.append(("lost_turn_cost",t,base_graph(),0,3,Vehicle(height=1.8,weight=2.0),(),()))
    normal=base_graph()
    altered=Graph(normal.nodes, normal.edges+(Edge(7,3,0,2),))
    cases.append(("fabricated_wrong_way_link",normal,altered,3,0,Vehicle(height=1.8,weight=2.0),(),()))
    cases.append(("lost_inbound_turn_history",a,a,1,3,Vehicle(height=1.8,weight=2.0),(1,),()))
    return cases

def mutation_gate():
    records=[]
    for name,correct,corrupt,start,target,vehicle,inbound,corrupt_inbound in mutations():
        cost=oracle(correct,start,target,vehicle,inbound)
        clean=Router(correct,(0,3)).route(start,target,vehicle,"dijkstra",inbound)
        baseline_ok=(clean is None and math.isinf(cost)) or (
            clean is not None and clean.cost==cost)
        if clean is not None:
            try:validate_route(correct,start,target,vehicle,inbound,clean)
            except (KeyError,AssertionError):baseline_ok=False
        bad=Router(corrupt,(0,3)).route(start,target,vehicle,"dijkstra",corrupt_inbound)
        same_cost=(math.isinf(cost) if bad is None else bad.cost==cost)
        valid=True
        if bad is not None:
            try:validate_route(correct,start,target,vehicle,inbound,bad)
            except (KeyError,AssertionError):valid=False
        detected=not same_cost or not valid
        records.append({"case":name,"baseline_correct":baseline_ok,
                        "injected_fault_detected":detected,
                        "original_oracle_cost":"unreachable" if math.isinf(cost) else cost,
                        "corrupted_return_cost":None if bad is None else bad.cost,
                        "corrupted_edges":None if bad is None else bad.edges,
                        "kind":"deliberately injected defect; not a DriveMate production failure"})
    return records

def hard_holdout():
    """Eight precommitted large, asymmetric road graphs with compound rules."""
    rows=[]
    for n,seed in enumerate(SEEDS):
        graph=fixture(8,seed,split=n%4==0)
        routing=Router(graph,(0,7,56,63),cache_capacity=64)
        for k,(source,destination,history,vehicle) in enumerate(cases(graph,seed+19,10)):
            truth=oracle(graph,source,destination,vehicle,history)
            for mode in MODES:
                try:
                    got=routing.route(source,destination,vehicle,mode,history)
                    passed=(got is None and math.isinf(truth)) or (
                        got is not None and got.cost==truth)
                    if got is not None:
                        try:validate_route(graph,source,destination,vehicle,history,got)
                        except (AssertionError,KeyError):passed=False
                    issue=None if passed else "Wrong minimum cost, illegal path or wrong destination"
                except Exception as exc:
                    got=None;passed=False;issue=type(exc).__name__+": "+str(exc)[:150]
                rows.append({"case":f"seed{seed}/query{k}/{mode}","seed":seed,
                             "search":mode,"status":"pass" if passed else "fail",
                             "issue":issue,"expected_cost":"unreachable" if math.isinf(truth) else truth,
                             "actual_cost":None if got is None else got.cost})
    return rows

def run(*,persist=True):
    mutants=mutation_gate()
    holdout=hard_holdout()
    failures=[r for r in holdout if r["status"]!="pass"]
    gate_failures=[r for r in mutants if not r["baseline_correct"] or not r["injected_fault_detected"]]
    result={"classification":"Independent synthetic tests and deliberate fault-detection controls; not external engine comparisons",
            "hard_holdout":{"executed":len(holdout),"passed":len(holdout)-len(failures),
                            "failed":len(failures),"results":holdout},
            "mutations":{"injected":len(mutants),
                         "detected":sum(x["injected_fault_detected"] for x in mutants),
                         "baseline_failures":sum(not x["baseline_correct"] for x in mutants),
                         "cases":mutants},
            "failure_count":len(failures)+len(gate_failures),
            "issues":[{"case":r.get("case"),"issue":r.get("issue","Mutation escaped detection")} for r in (failures+gate_failures)]}
    if persist:
        folder=Path("results/navigation_mutation")
        folder.mkdir(parents=True,exist_ok=True)
        (folder/"report.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"holdout_passed":result["hard_holdout"]["passed"],
                      "holdout_total":len(holdout),
                      "mutants_detected":result["mutations"]["detected"],
                      "mutants_injected":len(mutants),"failures":result["failure_count"]}))
    return result

if __name__=="__main__":
    raise SystemExit(1 if run()["failure_count"] else 0)
