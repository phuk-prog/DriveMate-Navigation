"""GraphHopper MATCH endpoint contracts; fixture is SYNTHETIC, not a UK field trace."""
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.error import HTTPError
from unittest.mock import patch

from benchmarks.graphhopper_match_reference import (
    research_gpx,_check_synthetic_gpx,flattened_matched_points,
    request_local_graphhopper_match,evaluate,MATCH_URL
)
from benchmarks.osrm_match_reference import generate_cases
from gps.fix_quality import GPSFix
from map_data import Provenance,import_osm_xml

RAW=(Path(__file__).resolve().parents[1]/
    "benchmarks/fixtures/synthetic-osm-junction.xml").read_bytes()


class GraphHopperMapMatchingContractTests(unittest.TestCase):
    def points(self):
        return [GPSFix(i*8000+1000,53.0,-2.0+i*.0001,3,10,90)
                for i in range(4)]

    def test_gpx_has_four_timestamped_synthetic_trackpoints(self):
        raw=research_gpx(self.points())
        root=ET.fromstring(raw)
        self.assertEqual(root.get("creator"),"DMN-public-synthetic")
        self.assertEqual(len(root.findall(".//{http://www.topografix.com/GPX/1/1}trkpt")),4)
        _check_synthetic_gpx(raw)
        self.assertIn(b"1970-01-01",raw)

    def test_non_synthetic_or_entity_is_rejected(self):
        raw=research_gpx(self.points())
        with self.assertRaises(ValueError):
            _check_synthetic_gpx(raw.replace(b"DMN-public-synthetic",b"private-source"))
        with self.assertRaises(ValueError):
            _check_synthetic_gpx(b'<!DOCTYPE t [<!ENTITY x "x">]>'+raw)

    def test_identical_time_is_rejected(self):
        points=self.points()
        points[2]=GPSFix(points[1].timestamp_ms,53,-2,3,10,90)
        with self.assertRaises(ValueError):research_gpx(points)

    def test_extended_json_wpts_across_multiple_links(self):
        data={"diary":{"entries":[{"links":[
            {"wpts":[{"x":-2.0,"y":53.0},{"x":-1.9,"y":53.0}]},
            {"wpts":[{"x":-1.8,"y":53.1},{"x":-1.7,"y":53.2}]}
        ]}]}}
        self.assertEqual(len(flattened_matched_points(data)),4)
        self.assertEqual(flattened_matched_points(data)[0],(53,-2))

    def test_bad_response_does_not_invent_snaps(self):
        for bad in ({},{"diary":{"entries":[]}},
                    {"diary":{"entries":[{"links":[{"wpts":[{"x":400,"y":53}]}]}]}}):
            with self.assertRaises(ValueError):
                flattened_matched_points(bad)

    def test_original_same_public_source_research_cases(self):
        imported=import_osm_xml(RAW,provenance=Provenance(
            "synthetic unit topology","synthetic-fixture","in-memory",
            "© OpenStreetMap contributors"))
        sample=generate_cases(imported,2)
        self.assertGreater(len(sample),0)
        for _,__,fixes in sample:
            _check_synthetic_gpx(research_gpx(fixes))

    def test_injected_matching_results_cannot_claim_live_execution(self):
        with self.assertRaises(ValueError):
            evaluate(RAW,snapshot="unit synthetic",limit=1,
                     request=lambda data:{"no_match":True},live_graphhopper=True)

    def test_full_aligned_mock_is_only_proximity_evidence(self):
        import xml.etree.ElementTree as xml
        def replay(gpx):
            root=xml.fromstring(gpx)
            pts=root.findall(".//{http://www.topografix.com/GPX/1/1}trkpt")
            return {"diary":{"entries":[{"links":[
                {"wpts":[{"y":float(point.get("lat")),"x":float(point.get("lon"))}
                          for point in pts]}
            ]}]}}
        result=evaluate(RAW,snapshot="synthetic fixture",limit=2,request=replay)
        self.assertGreater(result["public_road_cases_submitted"],0)
        self.assertEqual(result["graphhopper_snapped_farther_than_20m_from_generated_input"],0)
        self.assertEqual(result["graphhopper_snapped_within_20m_of_generated_input"],
                         result["graphhopper_matched_fixes"])
        self.assertEqual(result["reference_families_actually_executed"],0)
        self.assertIsNone(result["navigation_score"])

    def test_mismatched_trace_length_is_unknown_not_pass(self):
        def replay(_):
            return {"diary":{"entries":[{"links":[{"wpts":[{"x":-2.0,"y":53.0}]}]}]}}
        report=evaluate(RAW,snapshot="synthetic fixture",limit=2,request=replay)
        self.assertEqual(report["graphhopper_matched_fixes"],0)
        self.assertEqual(report["graphhopper_unmatched_or_unaligned_fixes"],
                         4*report["public_road_cases_submitted"])

    def test_local_request_is_strictly_bound_to_gpx(self):
        with self.assertRaises(ValueError):
            request_local_graphhopper_match(b"this is not a generated public fixture")

    def test_404_means_endpoint_not_available_not_a_routing_success(self):
        bad=HTTPError(MATCH_URL,404,"not found",{},None)
        with patch("benchmarks.graphhopper_match_reference._OPENER") as stub:
            stub.open.side_effect=bad
            with self.assertRaisesRegex(RuntimeError,"endpoint is unavailable"):
                request_local_graphhopper_match(research_gpx(self.points()))

    def test_400_is_a_no_match_not_a_confident_match(self):
        bad=HTTPError(MATCH_URL,400,"bad trace",{},None)
        with patch("benchmarks.graphhopper_match_reference._OPENER") as stub:
            stub.open.side_effect=bad
            self.assertEqual(request_local_graphhopper_match(research_gpx(self.points())),
                             {"no_match":True})


if __name__=="__main__":
    unittest.main()
