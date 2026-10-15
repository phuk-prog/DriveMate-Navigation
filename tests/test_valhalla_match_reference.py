"""Unit contracts for Valhalla local trace_attributes; fake != live reference."""
import json
import unittest
from pathlib import Path
from benchmarks.valhalla_match_reference import evaluate,trace_body
from gps.fix_quality import GPSFix

RAW=(Path(__file__).resolve().parents[1]/"benchmarks/fixtures/synthetic-osm-junction.xml").read_bytes()

class ValhallaTraceMatchingTests(unittest.TestCase):
    def test_post_payload_uses_trace_attributes_map_snap(self):
        fixes=[GPSFix(t,53.4,-2.1,3,10,90) for t in (1000,9000,17000,25000)]
        x=json.loads(trace_body(fixes))
        self.assertEqual(x["costing"],"auto")
        self.assertEqual(x["shape_match"],"map_snap")
        self.assertEqual(len(x["shape"]),4)
    def test_mocked_response_reports_no_external_run(self):
        def mocked(payload):
            x=json.loads(payload)
            points=[{"lat":p["lat"],"lon":p["lon"],"type":"matched"}
                    for p in x["shape"]]
            return {"matched_points":points,"edges":[]}
        report=evaluate(RAW,snapshot="synthetic-test-fixture",limit=3,request=mocked)
        self.assertEqual(report["external_reference_families_executed"],0)
        self.assertEqual(report["valhalla_trace_ok_cases"],report["public_road_cases_sent_to_both"])
        self.assertEqual(report["valhalla_snapped_farther_than_20m_from_input"],0)
        self.assertIsNone(report["navigation_score"])
    def test_unroutable_stays_nonexistent_evidence(self):
        report=evaluate(RAW,snapshot="synthetic",limit=2,
                        request=lambda _:{"unroutable":True})
        self.assertEqual(report["valhalla_no_trace_cases"],report["public_road_cases_sent_to_both"])
        self.assertEqual(report["valhalla_tracepoints_total"],0)
    def test_invalid_points_cannot_be_counted(self):
        with self.assertRaises(ValueError):
            evaluate(RAW,snapshot="synthetic",limit=2,
                     request=lambda _:{"matched_points":[{"type":"matched","lat":float("nan"),"lon":0}]*4})
    def test_count_bounds(self):
        with self.assertRaises(ValueError):evaluate(RAW,snapshot="x",limit=0)

if __name__=="__main__":
    unittest.main()
