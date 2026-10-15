"""OSRM Match external adapter contracts; no mocked value counts as an engine run."""
import unittest
from pathlib import Path
from benchmarks.osrm_match_reference import evaluate, local_match_url, request_local_osrm_match
from gps.fix_quality import GPSFix

RAW=(Path(__file__).resolve().parents[1]/"benchmarks/fixtures/synthetic-osm-junction.xml").read_bytes()

class OSRMMatchAdapterTests(unittest.TestCase):
    def test_loopback_url_and_observation_order(self):
        fixes=[GPSFix(t,53.45,-2.15,3.0,10,90) for t in (1000,9000,17000)]
        url=local_match_url(fixes)
        self.assertIn("/match/v1/driving/",url)
        self.assertIn("timestamps=1;9;17",url)
        self.assertIn("radiuses=6;6;6",url)
    def test_duplicate_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            local_match_url([GPSFix(1000,53,-2,3)]*3)
    def test_bad_external_url_rejected_before_http(self):
        with self.assertRaises(ValueError):
            request_local_osrm_match("https://example.com/match/v1/driving/coords")
    def test_mocked_provider_is_not_treated_as_actual_execution(self):
        # This verifies diagnostic labeling and response schema only.
        responses=[]
        def fake(url):
            pts=url.split("/match/v1/driving/")[1].split("?")[0].split(";")
            trace=[{"location":list(map(float,p.split(",")))} for p in pts]
            responses.append(url)
            return {"code":"Ok","tracepoints":trace,"matchings":[{"confidence":0.9}]}
        report=evaluate(RAW,snapshot="synthetic-fixture-only",limit=3,request=fake)
        self.assertGreater(report["public_road_cases_sent_to_both"],0)
        self.assertEqual(report["osrm_match_ok_cases"],len(responses))
        self.assertEqual(report["osrm_snapped_farther_than_20m_from_generated_input"],0)
        self.assertEqual(report["external_reference_families_executed"],0)
        self.assertFalse(report["independent_position_ground_truth"])
        self.assertTrue(report["do_not_rank"])
        self.assertIsNone(report["navigation_score"])
    def test_no_match_has_explicit_denominator(self):
        report=evaluate(RAW,snapshot="synthetic-fixture-only",limit=3,
                        request=lambda _:{"code":"NoMatch"})
        self.assertEqual(report["osrm_no_match_cases"],report["public_road_cases_sent_to_both"])
        self.assertEqual(report["osrm_tracepoints_total"],0)
    def test_malformed_ok_must_fail_instead_of_counting_success(self):
        with self.assertRaises(ValueError):
            evaluate(RAW,snapshot="synthetic-fixture-only",limit=3,
                     request=lambda _:{"code":"Ok","tracepoints":[],"matchings":[]})
    def test_sample_bounds(self):
        with self.assertRaises(ValueError):evaluate(RAW,snapshot="synthetic-fixture-only",limit=0)
        with self.assertRaises(ValueError):evaluate(RAW,snapshot="synthetic-fixture-only",limit=30)

if __name__=="__main__":
    unittest.main()
