"""DMN C++ search-mode and compiler A/B on the SAME dated UK road geometry.

This is NOT a competitor whole-navigation ranking: one graph, one independent
C++ source, two compiler flags, 3 existing algorithms, same deterministic 100
route endpoints, same legal route validator, and 10 repeats each variant.
Internal C++-timed queries exclude subprocess startup, map load, Python/HTTP,
JNI, phone battery/memory and full-navigation GPS/guidance behaviour.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import median

from benchmarks.real_english_journey import select_case_cohorts
from benchmarks.real_english_speed import percentile
from engine.reconciled import prepare_navigation
from map_data import Provenance, import_osm_xml
from navigation_core.core import Vehicle
from navigation_core.native_adapter import run
from navigation_core.validation.oracle import validate_route

MODES = ("dijkstra", "astar", "alt")
BUILDS = ("o2", "o3")


def stats(values):
    if not values or any(type(x) not in (int,float) or x < 0 or not math.isfinite(x)
                         for x in values):
        raise ValueError("Missing or invalid measured native samples")
    return {"median_ms": round(median(values)/1e6,6),
            "p95_ms":round(percentile(values,.95)/1e6,6),
            "p99_ms":round(percentile(values,.99)/1e6,6)}


def summarise_records(records, cases, repeats, preparation):
    """Rank ONLY variants whose every query has a validated, same-cost result."""
    if not (type(cases) is int and cases>=1 and type(repeats) is int and repeats>=1):
        raise ValueError("Invalid A/B comparison cohort")
    expected=cases*repeats
    groups={}
    for row in records:
        build,mode=row["build"],row["mode"]
        if build not in BUILDS or mode not in MODES:
            raise ValueError("Unknown compiler/mode label")
        group=groups.setdefault((build,mode),[])
        group.append(row)
    if set(groups)!={(b,m) for b in BUILDS for m in MODES}:
        raise ValueError("Missing compiler/mode evidence")
    scores=[]
    for (build,mode),rows in sorted(groups.items()):
        if len(rows)!=expected:
            raise ValueError("Incomplete mode evidence: "+build+"/"+mode)
        values=[r["nanoseconds"] for r in rows]
        if any(r["status"]!="pass" for r in rows):
            raise ValueError("Wrong-cost or invalid-path mode result: "+build+"/"+mode)
        if len({(r["case"],r["repeat"]) for r in rows})!=expected:
            raise ValueError("Duplicate or absent A/B query")
        timings=stats(values)
        scores.append({"compiler":build,"mode":mode,"pass":len(rows),
                       "total":expected,**timings,
                       "mean_expanded_states":round(sum(r["expanded"] for r in rows)/expected,1),
                       "preparation_ms":preparation[build]})
    ranks=sorted(scores,key=lambda r:(r["p95_ms"],r["median_ms"],r["compiler"],r["mode"]))
    for index,row in enumerate(ranks,1):
        row["native_core_speed_rank"]=index
    return {"scope":"real_UK_OSM_native_C++_algorithm_only",
            "real_road_cases":cases,"repeats_per_case":repeats,
            "verified_native_queries":sum(r["pass"] for r in scores),
            "expected_native_queries":6*expected,
            "algorithms_compared":list(MODES),"compiler_builds":list(BUILDS),
            "ranking":ranks,
            "best_host_core_variant":ranks[0]["compiler"]+"/"+ranks[0]["mode"],
            "requires_new_android_legality_memory_battery_validation":True}


def execute(raw, snapshot, executable_o2, executable_o3, repeats=10, cases=100):
    if not 8<=cases<=100 or not 3<=repeats<=30:
        raise ValueError("Bounded comparison requires 8-100 real cases and 3-30 repeats")
    graph=import_osm_xml(raw,provenance=Provenance(
        "Greater Manchester, England",snapshot,
        "Geofabrik historic public OSM PBF","© OpenStreetMap contributors (ODbL 1.0)"))
    prepared=prepare_navigation(graph.graph,graph.coordinates)
    endpoints=select_case_cohorts(prepared,graph.graph,cases)
    if len(endpoints)!=cases:
        raise ValueError("Missing real UK route cases")
    lands=tuple(list(prepared.node_ids.values())[:1]+list(prepared.node_ids.values())[-1:])
    vehicle=Vehicle("car")
    # Mode order rotates to spread thermal/branch prediction effects across runs.
    queries=[]
    metadata=[]
    for repeat in range(repeats):
        for case in endpoints:
            for offset in range(len(MODES)):
                mode=MODES[(offset+repeat)%len(MODES)]
                queries.append((mode,prepared.node_ids[case["source"]],
                                prepared.node_ids[case["target"]],vehicle,()))
                metadata.append((case["id"],repeat,mode))
    baseline={}
    records=[]
    preparation={}
    for build,binary in (("o2",executable_o2),("o3",executable_o3)):
        if not binary.is_file():
            raise ValueError("Missing actual native compiled build: "+build)
        prep_ns,responses=run(prepared.graph,queries,lands,executable=binary)
        preparation[build]=round(prep_ns/1e6,3)
        if len(responses)!=len(queries):
            raise ValueError("Missing measured native results")
        checked=set()
        for ((mode,start,target,v,h),answer,(case_id,repeat,expected_mode)) in zip(queries,responses,metadata):
            native,elapsed_ns=answer
            if mode!=expected_mode or native is None or native.nanoseconds!=elapsed_ns:
                raise ValueError("Native response missing, altered or mismatch")
            key=(case_id,repeat)
            if key not in baseline:
                baseline[key]=native.cost
            if native.cost!=baseline[key]:
                raise ValueError("Different shortest path cost across algorithms/compilers: "+case_id)
            if (case_id,mode) not in checked:
                validate_route(prepared.graph,start,target,v,h,native)
                checked.add((case_id,mode))
            records.append({"build":build,"mode":mode,"case":case_id,
                            "repeat":repeat,"nanoseconds":elapsed_ns,
                            "expanded":native.expanded,"status":"pass"})
    report=summarise_records(records,len(endpoints),repeats,preparation)
    report.update({"snapshot":snapshot,"source_xml_sha256":hashlib.sha256(raw).hexdigest(),
                   "candidate":"DMN original C++ router, unchanged source for both compiler builds",
                   "landmarks_count":len(lands),
                   "verification":"Every path cost agrees across modes/builds; all first-per-mode paths checked for continuity, car restrictions and returned cost",
                   "limits":["Host compiled C++ algorithm-only measurements, not warm HTTP or Android application latency",
                             "Same-map profile/restrictions may still lack verified current UK legal data",
                             "Two compiler builds share one source implementation; not independent routing products",
                             "Short Wigan endpoints do not establish country-wide routing speed",
                             "Preprocessing time reported separately; additional RAM and device energy not measured"]})
    return report


def markdown(report):
    lines=["# DMN native algorithm and compiler A/B — real UK roads","",
           "The identical 100 real road cases run Dijkstra, A* and ALT using -O2 and -O3.",
           "**This is not a complete-navigation comparison or Android result.**","",
           "| Rank | Build | Algorithm | Valid queries | p50 core ms | p95 core ms | p99 core ms | Avg states expanded |",
           "|---:|---|---|---:|---:|---:|---:|---:|"]
    for x in report["ranking"]:
        lines.append("| %d | %s | %s | %d/%d | %.6f | %.6f | %.6f | %.1f |"%
                     (x["native_core_speed_rank"],x["compiler"],x["mode"],
                      x["pass"],x["total"],x["median_ms"],x["p95_ms"],
                      x["p99_ms"],x["mean_expanded_states"]))
    lines.extend(["","Fastest *measured core* variant: **"+report["best_host_core_variant"]+"**.",
                  "A faster mode is not selected for the DriveMate phone without legality, resource and device replay.",
                  "The original real-map HTTP cross-engine ranking remains unchanged.",
                  "Compilation/preprocessing and map memory have separate trade-offs.","",
                  "### Remaining workstreams","",
                  "11 of 12 workstreams remain open in the most recent verified 100-route benchmark.",
                  "These six compiler/algorithm variants are one optimisation experiment, not six closed product issues.",""])
    return "\n".join(lines)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",type=Path,required=True)
    parser.add_argument("--snapshot",required=True)
    parser.add_argument("--o2",type=Path,required=True)
    parser.add_argument("--o3",type=Path,required=True)
    parser.add_argument("--cases",type=int,default=100)
    parser.add_argument("--repeats",type=int,default=10)
    parser.add_argument("--output-dir",type=Path,default=Path("results/real-england"))
    args=parser.parse_args()
    if not (args.input.resolve().is_relative_to(Path("results").resolve())
            and args.output_dir.resolve().is_relative_to(Path("results").resolve())):
        parser.error("Public map and benchmarks must stay in ignored results/")
    report=execute(args.input.read_bytes(),args.snapshot,args.o2,args.o3,args.repeats,args.cases)
    args.output_dir.mkdir(exist_ok=True,parents=True)
    (args.output_dir/"dmn-native-search-ab.json").write_text(json.dumps(report,indent=2)+"\n")
    (args.output_dir/"DMN_NATIVE_SEARCH_AB.md").write_text(markdown(report))
    print(json.dumps({"best_variant":report["best_host_core_variant"],
          "queries_verified":report["verified_native_queries"],
          "variants":[{k:r[k] for k in ("compiler","mode","p95_ms","pass","total")}
                      for r in report["ranking"]]}))


if __name__=="__main__":
    main()
