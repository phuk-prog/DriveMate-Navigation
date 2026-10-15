"""A first executable contract for the native+GPS real-road journey scorecard."""
import unittest
from pathlib import Path
from benchmarks.real_english_journey import replay_case, sample_fractions, short_destination_ambiguity, select_case_cohorts
from benchmarks.whole_drive import prepared


class RealEnglishJourneyContractTests(unittest.TestCase):
    def test_simulated_journey_is_separate_from_live_device_claims(self):
        p = prepared()
        r = replay_case(p, "synthetic-contract", "osm:1", "osm:4")
        self.assertEqual(r["routing_backend"], "compiled_cpp_via_native_adapter")
        self.assertEqual(r["fix_source"], "simulated_from_public_OSM_geometry")
        self.assertIn(r["status"], ("pass", "fail", "unresolved"))
        self.assertIn("arrival", r["components"])
        self.assertIn("native_routing", r["components"])

    def test_simulated_positions_are_continuous_on_real_length_scale(self):
        for length in (2.5, 17.0, 140.0, 500.0):
            fs = sample_fractions(length)
            self.assertGreaterEqual(len(fs), 11)
            self.assertEqual(tuple(sorted(fs)), fs)
            self.assertLessEqual(max((v-u)*length for u, v in
                   zip((0.0,)+fs, fs+(1.0,))), 6.001)

    def test_short_ambiguous_destination_is_unresolved_not_false_navigation_failure(self):
        evidence = [{"match_status": "ambiguous"} for _ in range(3)]
        self.assertTrue(short_destination_ambiguity(5.4, evidence, False))
        self.assertFalse(short_destination_ambiguity(5.4, evidence, True))
        self.assertFalse(short_destination_ambiguity(30.0, evidence, False))
        self.assertFalse(short_destination_ambiguity(5.4, evidence[:1], False))

    def test_original_eight_remain_pinned_while_holdout_expands(self):
        original = [{"id": "england-%03d" % i, "source": i,
                     "target": i+1} for i in range(8)]
        extended = original + [{"id": "england-%03d" % i,
                                "source": i+10, "target": i+11}
                               for i in range(8, 40)]
        def discover(_p, _g, *, maximum):
            return original if maximum == 8 else extended[:maximum]
        initial = select_case_cohorts(None, None, 8, discover)
        expanded = select_case_cohorts(None, None, 16, discover)
        self.assertEqual(expanded[:8], initial)
        self.assertEqual(len(expanded), 16)
        self.assertEqual([x["cohort"] for x in expanded].count("heldout"), 8)
        self.assertEqual(len({(x["source"], x["target"]) for x in expanded}), 16)

    def test_holdout_shortfall_is_exposed_as_incomplete(self):
        original = [{"id": "england-%03d" % i, "source": i, "target": i+1}
                    for i in range(8)]
        def discover(_p, _g, *, maximum):
            return original
        with self.assertRaisesRegex(ValueError, "distinct held-out"):
            select_case_cohorts(None, None, 16, discover)

    def test_real_road_workflow_writes_inspectable_journey_result(self):
        wf = (Path(__file__).resolve().parents[1] /
              ".github/workflows/real-england-journey.yml").read_text()
        self.assertIn("python -m benchmarks.real_english_journey", wf)
        self.assertIn("results/real-england/journeys.json", wf)


if __name__ == "__main__":
    unittest.main()
