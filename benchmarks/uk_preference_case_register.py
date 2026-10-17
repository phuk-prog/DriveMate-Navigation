"""Reproducible *public-map derived* preference case IDs, not user journeys.

No precise source/destination positions or node/road IDs appear in persisted
records. Exact comparison journeys regenerate from the same pinned public
map snapshot, complete imported restriction set, and deterministic pair index.

Cryptographic digests are identifiers, NOT official UK traffic-law evidence.
"""
from __future__ import annotations

from hashlib import sha256
from math import isfinite
from typing import Sequence

from engine.route_alternatives import GeneratedRoute

MAX_CASES = 240


def _hex_digest(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def summarise_discriminating_case(
    snapshot: str, map_sha256: str, pair_index: int,
    source: str, destination: str,
    fastest: GeneratedRoute, shortest: GeneratedRoute,
    balanced: GeneratedRoute, candidates: Sequence[GeneratedRoute]
) -> dict[str, object]:
    """Report only independently-reproducible, unverified map-path decisions."""
    if not isinstance(snapshot, str) or not snapshot.strip() or len(snapshot) > 128:
        raise ValueError("Missing pinned public map snapshot")
    if (not isinstance(map_sha256, str) or len(map_sha256) != 64 or
            any(c not in "0123456789abcdef" for c in map_sha256)):
        raise ValueError("Expected canonical SHA256 of public map import source")
    if type(pair_index) is not int or not 0 <= pair_index < MAX_CASES:
        raise ValueError("Invalid deterministic sampled-pair index")
    if (not isinstance(source, str) or not source.strip() or
            not isinstance(destination, str) or not destination.strip() or
            source == destination):
        raise ValueError("Public map endpoints must be distinct")
    if not 2 <= len(candidates) <= 12:
        raise ValueError("Discriminating case must contain two or more candidates")
    if len({c.route_id for c in candidates}) != len(candidates):
        raise ValueError("Candidate paths must have unique identities")
    for c in candidates:
        if not isinstance(c, GeneratedRoute) or c.snapshot_id != map_sha256:
            raise ValueError("Candidate source map mismatch")
        option = c.as_unverified_option()
        if option.independently_verified_legal or option.evidence_current:
            raise AssertionError("Unverified source map cannot certify road law")
    if fastest.route_id == shortest.route_id:
        raise ValueError("Only divergent map-derived fastest/shortest cases belong here")
    if any(c not in candidates for c in (fastest, shortest, balanced)):
        raise ValueError("Every mode's route must come from this candidate set")
    case_digest = _hex_digest(repr((
        "dmn-preference-case-v1", snapshot, map_sha256, pair_index,
        source, destination)))
    for r in (fastest, shortest, balanced):
        if not all(isfinite(x) and x >= 0 for x in (
                r.route.length_m, r.route.estimated_seconds)):
            raise ValueError("Invalid graph-derived distance or time")
    return {
        "case_id": "dmn-mapcase-" + case_digest[:24],
        "case_schema_version": 1,
        "sample_pair_index": pair_index,
        "map_sha256": map_sha256,
        "map_snapshot": snapshot,
        "fastest_route_digest": fastest.route_id,
        "shortest_route_digest": shortest.route_id,
        "balanced_route_digest": balanced.route_id,
        "candidate_paths": len(candidates),
        "fastest_estimated_seconds": round(fastest.route.estimated_seconds, 3),
        "shortest_estimated_seconds": round(shortest.route.estimated_seconds, 3),
        "fastest_length_m": round(fastest.route.length_m, 3),
        "shortest_length_m": round(shortest.route.length_m, 3),
        "same_fastest_shortest": False,
        "independent_current_uk_road_legality": "UNKNOWN",
        "traffic_observed": False,
        "map_only_test_case": True,
        "competitor_outcomes": "NOT_RUN",
    }


def validate_case_register(cases: Sequence[dict[str, object]], *,
                           expected_count: int | None = None) -> dict[str, object]:
    """Catch lost, duplicated or falsely 'validated' research cases."""
    if not isinstance(cases, (list, tuple)) or len(cases) > MAX_CASES:
        raise ValueError("Case register exceeds bounded research scope")
    if expected_count is not None and len(cases) != expected_count:
        raise AssertionError("Discriminating source cases missing from register")
    ids = [c.get("case_id") for c in cases]
    if any(not isinstance(x, str) or not x.startswith("dmn-mapcase-") for x in ids):
        raise ValueError("Invalid map-only case identity")
    if len(ids) != len(set(ids)):
        raise AssertionError("Duplicate case ID in register")
    for c in cases:
        if (c.get("independent_current_uk_road_legality") != "UNKNOWN" or
                c.get("competitor_outcomes") != "NOT_RUN" or
                c.get("traffic_observed") is not False or
                c.get("map_only_test_case") is not True or
                c.get("same_fastest_shortest") is not False):
            raise AssertionError("Case report asserts evidence it does not possess")
    digest = _hex_digest("|".join(ids))
    return {
        "case_count": len(cases),
        "case_register_sha256": digest,
        "case_register_valid": True,
        "independent_legality_established": False,
        "comparator_execution_complete": False,
    }



def validate_neighborhood_case_registers(records: Sequence[dict[str, object]]
                                         ) -> dict[str, object]:
    """Fail closed if a multi-area test loses, duplicates or overstates cases.

    Unsupported areas must not emit fake route victories. Every supported
    neighborhood's claimed divergent count must equal its stable case records.
    The aggregate checksum is order-sensitive so a future run can detect drift.
    """
    if not isinstance(records, (list, tuple)) or len(records) > 12:
        raise ValueError("Expected up to twelve bounded public neighborhoods")
    combined = []
    count_by_area = []
    expected = 0
    for item in records:
        if not isinstance(item, dict):
            raise ValueError("Invalid neighborhood record")
        status = item.get("status")
        cases = item.get("discriminating_case_register", [])
        if not isinstance(cases, list):
            raise ValueError("Expected a list of map-only research cases")
        claimed = item.get("case_register_count", 0)
        divergences = item.get("neighborhood_fastest_shortest_divergences", 0)
        if type(claimed) is not int or type(divergences) is not int:
            raise ValueError("Invalid neighborhood case counters")
        if status == "map_rule_checked":
            verified = validate_case_register(cases, expected_count=divergences)
            if claimed != divergences:
                raise AssertionError("Neighborhood case count does not match actual divergence")
            if item.get("case_register_sha256") != verified["case_register_sha256"]:
                raise AssertionError("Neighborhood case checksum mismatch")
        elif status == "unsupported":
            if cases or claimed != 0 or divergences != 0:
                raise AssertionError("Unsupported neighborhood cannot assert route cases")
        else:
            raise ValueError("Unknown map neighborhood evidence classification")
        count_by_area.append(len(cases))
        expected += divergences
        combined.extend(cases)
    summary = validate_case_register(combined, expected_count=expected)
    return {
        **summary,
        "case_register_counts_by_neighborhood": count_by_area,
        "discriminating_case_register": combined,
    }
