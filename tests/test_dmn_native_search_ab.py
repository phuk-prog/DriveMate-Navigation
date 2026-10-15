import unittest
from benchmarks.dmn_native_search_ab import MODES, BUILDS, stats, summarise_records


class DMNNativeSpeedABTests(unittest.TestCase):
    def test_variants_only_rank_after_same_100_route_full_correctness(self):
        rows=[]
        for build in BUILDS:
            for mode in MODES:
                for i in range(4):
                    rows.append({"build":build,"mode":mode,"case":"real-%02d"%i,
                                 "repeat":0,"nanoseconds":50_000 if mode=="alt" else 100_000,
                                 "expanded":3 if mode=="alt" else 6,"status":"pass"})
        result=summarise_records(rows,4,1,{"o2":9,"o3":8})
        self.assertEqual(result["expected_native_queries"],24)
        self.assertEqual(result["verified_native_queries"],24)
        self.assertEqual(result["ranking"][0]["mode"],"alt")
        self.assertTrue(result["requires_new_android_legality_memory_battery_validation"])
        rows[0]["status"]="fail"
        with self.assertRaisesRegex(ValueError,"Wrong-cost"):
            summarise_records(rows,4,1,{"o2":9,"o3":8})

    def test_missing_or_duplicate_results_cannot_be_ranked(self):
        rows=[]
        for build in BUILDS:
            for mode in MODES:
                rows.append({"build":build,"mode":mode,"case":"c",
                             "repeat":0,"nanoseconds":1000,"expanded":1,"status":"pass"})
        rows.append(dict(rows[0]))
        with self.assertRaisesRegex(ValueError,"Incomplete mode evidence"):
            summarise_records(rows,1,1,{"o2":1,"o3":1})
        rows.pop()
        rows[0]["nanoseconds"]=-1
        with self.assertRaisesRegex(ValueError,"invalid measured"):
            summarise_records(rows,1,1,{"o2":1,"o3":1})

    def test_research_build_is_o3_while_ab_uses_separate_o2(self):
        from pathlib import Path
        root=Path(__file__).resolve().parents[1]
        build=(root/"navigation_core/native/build.sh").read_text()
        workflow=(root/".github/workflows/real-england-speed.yml").read_text()
        self.assertIn("-O3",build)
        self.assertIn("-O2",workflow)
        self.assertIn("-o results/real-england/router-o2",workflow)
        self.assertIn("--o2 results/real-england/router-o2",workflow)
        self.assertIn("--o3 navigation_core/native/router",workflow)

    def test_percentile_is_native_only_not_http(self):
        x=stats([1000]*19+[3000])
        self.assertEqual(x["median_ms"],.001)
        self.assertEqual(x["p95_ms"],.001)
        self.assertEqual(x["p99_ms"],.003)


if __name__=="__main__":
    unittest.main()
