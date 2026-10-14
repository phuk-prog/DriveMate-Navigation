import unittest
from benchmarks.head_to_head import BACKENDS, CONSUMER_NAVIGATORS, build


class HeadToHeadTests(unittest.TestCase):
    def sources(self):
        sha = "a" * 64
        g = {"reference": "GraphHopper 11.1", "fresh_execution": True,
             "dataset_sha256": sha, "routes": [
                {"case": "synthetic_legal", "expected_ways": [1, 2],
                 "drivemate_status": "pass", "graphhopper_status": "pass"},
                {"case": "synthetic_ban", "expected_ways": None,
                 "drivemate_status": "pass", "graphhopper_status": "fail"}]}
        o = {"engine": "osrm", "fresh_execution": True, "dataset_sha256": sha,
             "cases": [{"case": "synthetic_legal", "expected_ways": [1, 2], "status": "pass"},
                       {"case": "synthetic_ban", "expected_ways": None, "status": "unknown"}]}
        return g, o

    def test_actual_cases_paired_with_unknown_not_promoted(self):
        report = build(self.sources())
        self.assertEqual(report["summaries"]["DriveMate"]["passed"], 2)
        self.assertEqual(report["summaries"]["GraphHopper"]["failed"], 1)
        self.assertEqual(report["summaries"]["OSRM MLD"]["unknown"], 1)
        self.assertEqual(report["summaries"]["Valhalla"]["not_tested"], 2)
        self.assertIsNone(report["ranking"])
        self.assertEqual(len(CONSUMER_NAVIGATORS), 10)
        self.assertEqual(report["consumer_results"], "not tested; no direct product navigation evidence")

    def test_osrm_ch_is_only_present_with_independent_fresh_execution(self):
        g, o = self.sources()
        ch = dict(o, engine="osrm-ch")
        report = build((g, o, ch))
        self.assertEqual(report["summaries"]["OSRM CH"]["passed"], 1)
        self.assertEqual(report["summaries"]["OSRM CH"]["unknown"], 1)
        self.assertEqual(len(report["cases"]), 2)
        ch["fresh_execution"] = False
        with self.assertRaisesRegex(ValueError, "not verified"):
            build((g, o, ch))

    def test_additional_real_routing_algorithms_pair_only_when_executed(self):
        g, o = self.sources()
        r=build((g,{**o,"engine":"routingkit"},{**o,"engine":"pgrouting"}))
        self.assertEqual(r["summaries"]["RoutingKit CH"]["passed"],1)
        self.assertEqual(r["summaries"]["pgRouting"]["unknown"],1)
        self.assertEqual(r["summaries"]["RoutingKit CH"]["not_tested"],0)
        self.assertEqual(r["summaries"]["Valhalla"]["not_tested"],2)

    def test_different_dataset_disallowed(self):
        g, o = self.sources()
        o["dataset_sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "non-equivalent dataset"):
            build((g, o))

    def test_different_expected_route_disallowed(self):
        g, o = self.sources()
        o["cases"][0]["expected_ways"] = [5]
        with self.assertRaisesRegex(ValueError, "scenario/route mismatch"):
            build((g, o))

    def test_nonfresh_reference_disallowed(self):
        g, o = self.sources()
        o["fresh_execution"] = False
        with self.assertRaisesRegex(ValueError, "not verified"):
            build((g, o))

    def test_missing_engine_does_not_fabricate_a_pass(self):
        g, o = self.sources()
        r = build((g,))
        self.assertEqual(r["summaries"]["OSRM MLD"]["not_tested"], 2)
        self.assertIsNone(r["ranking"])


if __name__ == "__main__":
    unittest.main()
