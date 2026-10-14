"""Publish measurement-only category tables from fresh, same-map references.

Unexecuted systems do not appear as scored competitors. Unknown is a recorded
measurement outcome, never a zero, pass or silently excluded failed case.
"""
import argparse
import json
from pathlib import Path
from benchmarks.head_to_head import generate as generate_head_to_head, BACKENDS
from benchmarks.benchmark_ranking import judge as judge_ranking, markdown as ranking_markdown, save as save_ranking

MEASURED_CATEGORIES = (
    ("Routing/legality", "routing_legality"),
    ("Roundabout exit counting", "junction_roundabout"),
    ("Clean path observations", "gps_matching"),
    ("Warm HTTP latency", "speed_rerouting"),
)
EXCLUDED_SCOPE = (
    "Unrun navigator apps, SDKs and backends are excluded from scored tables rather "
    "than displayed as untested placeholder rows or assigned fabricated results. Google Maps, Waze, "
    "Apple Maps, HERE WeGo, TomTom, Sygic, OsmAnd, Organic Maps, Magic Earth, "
    "MapFactor Navigator, BRouter, Mapbox and openrouteservice have no equivalent "
    "fresh whole-product comparison in this workflow."
)

def load_records(root):
    """Only source-backed, fresh records may populate the measured cohort."""
    records={}
    for path in Path(root).rglob("scorecard.json"):
        scorecard=json.loads(path.read_text())
        for row in scorecard["systems"]:
            if row["system"] in ("DriveMate","GraphHopper"):
                records[row["system"]]=row
    for path in Path(root).rglob("comparison.json"):
        entry=json.loads(path.read_text())
        engine=entry.get("engine")
        if engine not in ("osrm","osrm-ch","valhalla","routingkit","pgrouting"):
            continue
        if entry.get("fresh_execution") is not True:
            raise ValueError("Cannot score an unverified reference: "+engine)
        label={"osrm":"OSRM MLD","osrm-ch":"OSRM CH","valhalla":"Valhalla",
               "routingkit":"RoutingKit CH","pgrouting":"pgRouting"}[engine]
        row=records.setdefault(label,{"system":label,"scores":{},"overall":None})
        row["status"]="executed verified reference"
        cases=entry["cases"]
        row["scores"]["routing_legality"]=(round(10*sum(c["status"]=="pass" for c in cases)/len(cases),2)
            if cases and all(c["status"]!="unknown" for c in cases) else None)
        ring=[case for case in entry["cases"] if case["case"].startswith("ring_exit_")]
        row["scores"]["junction_roundabout"]=(round(10*sum(c["status"]=="pass" for c in ring)/4,2)
            if engine in ("osrm","osrm-ch","valhalla") and len(ring)==4
            and all(c["status"]!="unknown" for c in ring) else None)
    return records

def scorecard_markdown(records, comparison, gps_traces=None):
    """One table per category: only competitors actually measured in that category."""
    lines=[
        "# Measured navigation scorecard",
        "",
        "Only executed evidence is displayed. A missing engine/category is **excluded**, not "
        "graded zero. These are synthetic research results, not real-UK-drive or app rankings.",
        "",
        "## Shared nine-case routing and legality comparison",
        "",
        "| Executed engine/configuration | Passed | Failed | Unknown | Evidence coverage |",
        "|---|---:|---:|---:|---|",
    ]
    summary=comparison.get("summaries",{})
    active=[name for name in BACKENDS if name in summary and summary[name]["not_tested"]==0]
    if not active:
        lines.append("| No fully executed paired comparison | — | — | — | Unavailable |")
    for name in active:
        s=summary[name]
        lines.append(f"| {name} | {s['passed']}/{s['test_cases']} | {s['failed']} | {s['unknown']} "
                     f"| Same authored map and scenario IDs |")
    lines.extend(["",
        "An unknown outcome is not a failure or an awarded pass. Exact route choice can "
        "also legitimately differ with an engine's cost and turn models.",
        "",
        "## Roundabout exit numbers (four common synthetic cases)",
        "",
        "| Executed engine/configuration | Passed | Failed | Unknown |",
        "|---|---:|---:|---:|",
    ])
    for name in active:
        subset=[case["results"][name] for case in comparison["cases"] if case["case"].startswith("ring_exit_")]
        if len(subset)!=4:continue
        lines.append(f"| {name} | {subset.count('pass')}/4 | {subset.count('fail')} | {subset.count('unknown')} |")
    lines.extend(["",
        "## Other measured subsets (NOT a full head-to-head GPS/voice ranking)",
        "",
        "| Category | Engine/configuration | Measured subset score | Important limit |",
        "|---|---|---:|---|",
    ])
    subset_categories=[
      ("gps_matching","Four clean synthetic observed path sequences; DriveMate live versus GraphHopper offline batch processing"),
      ("speed_rerouting","Warm local HTTP p95; only comparable as tested configurations, not real-world rerouting"),
    ]
    count=0
    for key,explanation in subset_categories:
        for name in ("DriveMate","GraphHopper"):
            value=records.get(name,{}).get("scores",{}).get(key)
            if value is None:continue
            lines.append(f"| {key.replace('_',' ').title()} | {name} | {value}/10 | {explanation} |")
            count+=1
    if not count:
        lines.append("| No comparable subset available | — | — | Unavailable |")
    if gps_traces:
        lines.extend(["",
            "## Identical four clean synthetic GPS traces",
            "",
            "| Engine/configuration | Correct observed road sequence | Incorrect | Unresolved |",
            "|---|---:|---:|---:|",
        ])
        for name in BACKENDS:
            outcomes=gps_traces.get(name)
            if outcomes is None or len(outcomes)!=4:continue
            lines.append(f"| {name} | {outcomes.count('pass')}/4 | {outcomes.count('fail')} | "
                         f"{outcomes.count('unknown')} |")
        lines.extend(["",
            "These are comparable clean coordinate-input path outcomes, **not** a ranking "
            "of live GPS controllers, recovery delay, accuracy in metres or real sensor quality.",
        ])
    lines.extend(["",
        "## Coverage excluded from overall ranking",
        "",
        EXCLUDED_SCOPE,
        "",
        "GPS signal-loss recovery, occupied-lane identification, spoken-instruction timing, "
        "offline device efficiency and fault combinations remain unranked until equivalent "
        "engine or device output exists. DriveMate-only hard synthetic tests are regression "
        "evidence, not evidence that competitors passed or failed those same tests.",
        "",
        "**Overall/navigation-app winner: not established.**",
    ])
    return "\n".join(lines)+"\n"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path,required=True)
    a=ap.parse_args()
    root=a.input
    records=load_records(root)
    out=Path("results/ci-report")
    out.mkdir(parents=True,exist_ok=True)
    comparisons=generate_head_to_head(root,out)
    matched={}
    for path in root.rglob("comparison.json"):
        data=json.loads(path.read_text())
        if data.get("reference")=="GraphHopper 11.1":
            matched["DriveMate"]=[row["drivemate_online_status"] for row in data.get("batch_matches",())]
            matched["GraphHopper"]=[row["graphhopper_batch_status"] for row in data.get("batch_matches",())]
        elif data.get("engine") in ("osrm","osrm-ch","valhalla") and data.get("fresh_execution") is True:
            label={"osrm":"OSRM MLD","osrm-ch":"OSRM CH","valhalla":"Valhalla"}[data["engine"]]
            matched[label]=[row["status"] for row in data.get("batch_matches",())]
    ranking=judge_ranking(comparisons)
    save_ranking(ranking,out)
    (out/"SCORECARD.md").write_text(ranking_markdown(ranking)+"\n"+scorecard_markdown(records,comparisons,matched))
    (out/"results.json").write_text(json.dumps(records,indent=2))

if __name__=="__main__":
    main()
