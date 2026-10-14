"""Case-matched DriveMate versus genuinely executed reference routing engines.

Consumer navigator products remain distinct. A backend response must never be
misrepresented as actual Google Maps/Waze/Organic Maps navigation output.
"""
import json
from pathlib import Path

CONSUMER_NAVIGATORS = (
    "Google Maps", "Waze", "Apple Maps", "HERE WeGo", "TomTom",
    "Sygic", "OsmAnd", "Organic Maps", "Magic Earth", "MapFactor Navigator",
)
BACKENDS = ("DriveMate", "GraphHopper", "OSRM MLD", "OSRM CH", "Valhalla", "RoutingKit CH", "pgRouting")
STATUSES = {"pass", "fail", "unknown"}


def _cases(items, label, status_key, expected_key):
    if not isinstance(items, list):
        raise ValueError(f"{label} has no scenario cases")
    rows = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("case"), str):
            raise ValueError(f"{label}: invalid scenario")
        ident = item["case"]
        if ident in rows:
            raise ValueError(f"{label}: duplicate case {ident}")
        if item.get(status_key) not in STATUSES:
            raise ValueError(f"{label}: invalid result for {ident}")
        if expected_key not in item:
            raise ValueError(f"{label}: expected route missing for {ident}")
        rows[ident] = item
    return rows


def build(source_documents):
    """Create verifiable pairings; never infer unexecuted navigator results."""
    gh = next((doc for doc in source_documents
               if doc.get("reference") == "GraphHopper 11.1"), None)
    if gh is None:
        return {"status": "no_candidate_reference_artifact",
                "cases": [], "consumer_navigators": list(CONSUMER_NAVIGATORS),
                "consumer_results": "not tested", "ranking": None}
    if gh.get("fresh_execution") is not True:
        raise ValueError("GraphHopper route execution was not verified fresh")
    digest = gh.get("dataset_sha256")
    if not isinstance(digest, str) or len(digest) != 64:
        raise ValueError("Missing candidate/reference dataset SHA-256")
    primary = _cases(gh.get("routes"), "DriveMate/GraphHopper",
                     "drivemate_status", "expected_ways")
    _cases(gh.get("routes"), "GraphHopper", "graphhopper_status", "expected_ways")
    references = {}
    for engine, name in (("osrm", "OSRM MLD"), ("osrm-ch", "OSRM CH"), ("valhalla", "Valhalla"), ("routingkit", "RoutingKit CH"), ("pgrouting", "pgRouting")):
        doc = next((d for d in source_documents if d.get("engine") == engine), None)
        if doc is not None:
            if doc.get("fresh_execution") is not True:
                raise ValueError(f"{name}: reference execution is not verified")
            if doc.get("dataset_sha256") != digest:
                raise ValueError(f"{name}: non-equivalent dataset")
            rows = _cases(doc.get("cases"), name, "status", "expected_ways")
            for ident, row in rows.items():
                if ident not in primary or row["expected_ways"] != primary[ident]["expected_ways"]:
                    raise ValueError(f"{name}: scenario/route mismatch {ident}")
            references[name] = rows
    pairings = []
    for ident, row in primary.items():
        outcomes = {"DriveMate": row.get("drivemate_route_status",row["drivemate_status"]),
                    "GraphHopper": row.get("graphhopper_route_status",row["graphhopper_status"])}
        for name in ("OSRM MLD", "OSRM CH", "Valhalla", "RoutingKit CH", "pgRouting"):
            refrow=references.get(name, {}).get(ident, {})
            outcomes[name] = refrow.get("route_status",refrow.get("status","not tested"))
        pairings.append({"case": ident, "expected_ways": row["expected_ways"],
                         "results": outcomes})
    summaries = {}
    for name in BACKENDS:
        values = [item["results"][name] for item in pairings]
        summaries[name] = {"passed": values.count("pass"), "failed": values.count("fail"),
                           "unknown": values.count("unknown"),
                           "not_tested": values.count("not tested"),
                           "test_cases": len(values)}
    return {
        "status": "executed_synthetic_route_pairings", "dataset_sha256": digest,
        "test_scope": "Same original tiny synthetic network; static routes, restrictions, simple roundabout ordinals",
        "cases": pairings, "summaries": summaries,
        "consumer_navigators": list(CONSUMER_NAVIGATORS),
        "consumer_results": "not tested; no direct product navigation evidence",
        "ranking": None,
        "rules": [
            "Only real executed per-engine responses paired by case and map are scored",
            "Routing engines are not the same as complete consumer navigator products",
            "No GPS live-controller, occupied-lane, voice or real UK route ranking",
            "A tied synthetic fixture cannot establish a better real navigation system",
        ],
    }


def generate(artifact_root, output):
    documents = []
    for path in sorted(Path(artifact_root).rglob("comparison.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        if doc.get("reference") == "GraphHopper 11.1" or doc.get("engine") in ("osrm", "osrm-ch", "valhalla", "routingkit", "pgrouting"):
            documents.append(doc)
    report = build(documents)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "head_to_head.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Actual head-to-head: DriveMate vs routing-engine references",
        "",
        "These are actual executed same-synthetic-map route outcomes, NOT results from ten consumer navigation apps.",
        "A pass means agreement with a separately authored expected route for this fixture; it is not a real-road safety certification.",
        "",
    ]
    if report["cases"]:
        active=tuple(name for name in BACKENDS
                     if report["summaries"][name]["not_tested"]==0)
        lines += [
            "| Same route case | " + " | ".join(active) + " |",
            "|" + "---|" * (len(active)+1),
        ]
        for row in report["cases"]:
            lines.append("| " + row["case"] + " | " +
                         " | ".join(row["results"][name] for name in active) + " |")
        lines += ["", "All other navigator/product results: **not tested**.",
                  "No overall winner or full-navigation ranking is supported."]
    else:
        lines.append("No fresh candidate/reference paired result was available.")
    (output / "HEAD_TO_HEAD.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
