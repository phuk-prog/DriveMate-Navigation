"""Bounded UK local-time semantics for the frozen MAP-001 conditional source tags.

Research evidence only. This parser NEVER modifies DMN routing permissions:
source syntax and applicability time are not independent legal/order truth,
vehicle entitlement, permitted delivery purpose or a current road sign.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

from benchmarks.map001_graph_fact_audit import ROOT, AREAS, source, tags, digest
from benchmarks.map001_v3 import FROZEN_V2_IDS

UK = ZoneInfo("Europe/London")
CONDITION = re.compile(r"^([a-z][a-z0-9_]*)\s*@\s*(?:\(\s*)?([0-2]\d:[0-5]\d)\s*-\s*([0-2]\d:[0-5]\d)(?:\s*\))?$")
VALUES = {"no", "delivery", "no_right_turn", "no_left_turn", "no_straight_on"}
TARGETS = {"glasgow": ("4627827", "143769308"),
           "belfast": ("8301321", "144822061", "148210368",
                       "148210371", "148651263")}


@dataclass(frozen=True)
class TimeSource:
    value: str
    start: int
    end: int

    def active(self, moment: datetime):
        if moment.tzinfo != UK:
            raise ValueError("Require aware Europe/London instant for UK source time")
        minute = moment.hour * 60 + moment.minute
        return ((self.start <= minute < self.end) if self.start < self.end else
                (minute >= self.start or minute < self.end))


def parse_source(raw: str):
    if type(raw) is not str or len(raw) > 120 or ";" in raw:
        raise ValueError("Unsupported or ambiguous conditional expression")
    match = CONDITION.fullmatch(raw.strip())
    if not match or match[1] not in VALUES:
        raise ValueError("Unsupported OSM conditional syntax or rule")
    def minute(s):
        hour, mm = [int(x) for x in s.split(":")]
        if hour > 24 or (hour == 24 and mm > 0):
            raise ValueError("Invalid time boundary")
        return hour * 60 + mm
    start, end = minute(match[2]), minute(match[3])
    if start == end or start == 1440:
        raise ValueError("Empty or ambiguous time interval")
    return TimeSource(match[1], start, end)


def source_evidence(area, identity, kind, key, value):
    record = {"area":area, "source_id":identity, "object_kind":kind, "tag":key,
              "raw_value":value, "legal_road_truth":"NOT_INDEPENDENTLY_VERIFIED",
              "engine_behavior_changed":False, "route_permission":"NOT_GRANTED"}
    try:
        parsed = parse_source(value)
    except ValueError as exc:
        return {**record,"status":"UNSUPPORTED","reason":str(exc)}
    october_day=datetime(2026,10,14,12,0,tzinfo=UK)
    october_evening=datetime(2026,10,14,20,0,tzinfo=UK)
    return {**record, "status":"PARSED_TIME_ONLY_NOT_ROAD_LAW",
            "conditional_value":parsed.value,"start_minute":parsed.start,
            "end_minute":parsed.end,
            "12_00_local_active":parsed.active(october_day),
            "20_00_local_active":parsed.active(october_evening),
            "actual_permission_and_current_order_verified":False}


def run():
    manifest=json.loads((ROOT/"map001-v3-manifest.json").read_text())
    if [p["area"] for p in manifest["areas"]] != list(AREAS):
        raise ValueError("Frozen area cohort changed")
    rows=[]
    for spec in manifest["areas"]:
        area=spec["area"]
        if area not in TARGETS:
            continue
        raw, _, ways, _ = source(ROOT/("map001-"+area+".osm"))
        if digest(raw)!=spec["source_sha256"]:
            raise ValueError("Source changed for "+area)
        if [c["way"] for c in spec["cases"]] != FROZEN_V2_IDS[area]:
            raise ValueError("Selected way IDs changed for "+area)
        for way in TARGETS[area]:
            if way not in ways:
                raise ValueError("Expected conditional source way missing: "+way)
            conditional={k:v for k,v in tags(ways[way]).items() if k.endswith(":conditional")}
            if not conditional:
                raise ValueError("Original conditional case changed: "+way)
            rows.extend(source_evidence(area,way,"way",k,v) for k,v in conditional.items())
        if area=="glasgow":
            root=ET.fromstring(raw)
            for rel in root.findall("relation"):
                if rel.get("id") in {"20429946","20429947","20429948","20429949"}:
                    entries={k:v for k,v in tags(rel).items() if k.endswith(":conditional")}
                    rows.extend(source_evidence(area,rel.get("id"),"relation",k,v)
                                for k,v in entries.items())
    if len(rows)!=11 or len({(x["area"],x["source_id"],x["tag"]) for x in rows})!=11:
        raise ValueError("Seven ways and four restriction-source cases required")
    report={"trial":"MAP-001-UK-TIME-WINDOW-SOURCE-1",
            "frozen_original_source_cohort":True,
            "treat_as_drivable_approval":False,
            "timezone":"Europe/London",
            "evidence":"PARSED_OSM_SYNTAX_ONLY_NOT_LEGAL_PROOF",
            "cases":rows,
            "parsed":sum(x["status"]=="PARSED_TIME_ONLY_NOT_ROAD_LAW" for x in rows),
            "unsupported":sum(x["status"]=="UNSUPPORTED" for x in rows),
            "road_law_verified":0,
            "engine_behavior_changed":False,
            "known_scope_limits":(
                "No local order-date activation, permits, delivery entitlement, "
                "temporary works, bank holidays, daylight-saving historical signs, "
                "or native competitor conditional-access parity")}
    (ROOT/"map001-conditional-syntax.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"trial":report["trial"],"source_cases":len(rows),
                      "parsed":report["parsed"],"unsupported":report["unsupported"],
                      "road_law_verified":0},indent=2))
    if report["unsupported"]:
        raise SystemExit("Unrecognised conditional source syntax; do not guess legality")


if __name__=="__main__":
    run()
