import unittest
from benchmarks.dmn_real_road_scorecard import analyse


def cases():
    return ["england-%03d"%n for n in range(8)]+["heldout-%03d"%n for n in range(1,9)]


def fixtures():
    c=cases();samples={}
    for engine in ("dmn-native-cpp","osrm-mld"):
        samples[engine]=[{"case":case,"repeat":i,"milliseconds":2.5} for case in c for i in range(3)]
    speed={"category":"real-English-roads-warm-http-speed",
           "source_snapshot":"2026-10-13","source_xml_sha256":"a"*64,
           "cohort_sha256":"b"*64,"cases":c,"repeats":3,"warmups":3,
           "route_cohorts":{"original":8,"heldout":8},
           "samples":samples,"failures":{"dmn-native-cpp":[],"osrm-mld":[]},
           "implementations":{
            "dmn-native-cpp":{"complete":True,"passed_requests":48,"total_requests":48,"p95_ms":1.8},
            "osrm-mld":{"complete":True,"passed_requests":48,"total_requests":48,"p95_ms":1.4}}}
    gps={"category":"DriveMate-native-full-GPS-journey-replay-on-real-English-roads",
         "source_snapshot":"2026-10-13","source_xml_sha256":"a"*64,
         "cohort_sha256":"b"*64,"scenario_count":16,
         "pass":0,"fail":0,"unresolved":16,"arrivals_confirmed":8,
         "uncertain_junction_holds":700,"speech_during_uncertain_junction":0,
         "cases":[{"case":case,"status":"unresolved","cohort":"original" if i<8 else "heldout",
                   "issues":["junction_ambiguous"],"components":{"native_routing":"pass"}}
                   for i,case in enumerate(c)]}
    return speed,gps


class DMNRealRoadScorecardTests(unittest.TestCase):
    def test_same_real_road_latency_rank_is_not_navigation_rank(self):
        result=analyse(*fixtures())
        self.assertEqual([r["engine"] for r in result["routing_latency_ranking_only"]],["osrm-mld","dmn-native-cpp"])
        self.assertIsNone(result["complete_navigation_ranking"])
        self.assertIsNone(result["actual_legal_routing_ranking"])
        self.assertEqual(result["dmn_simulated_gps_on_same_real_roads"]["unresolved"],16)

    def test_no_ranking_different_routes_or_maps(self):
        for k in ("source_snapshot","source_xml_sha256","cohort_sha256"):
            a,b=fixtures();b[k]="different"
            with self.assertRaisesRegex(ValueError,"mismatch"):analyse(a,b)
        a,b=fixtures();b["cases"][1]["case"]="wrong"
        with self.assertRaisesRegex(ValueError,"Case order"):analyse(a,b)

    def test_no_invented_complete_engine(self):
        a,b=fixtures();a["samples"]["osrm-mld"].pop()
        with self.assertRaises(ValueError):analyse(a,b)
        a,b=fixtures();a["implementations"]["osrm-mld"]["complete"]=False
        a["implementations"]["osrm-mld"].update(passed_requests=47,p95_ms=None)
        result=analyse(a,b)
        self.assertEqual(len(result["routing_latency_ranking_only"]),1)

    def test_duplicated_measurements_rejected(self):
        a,b=fixtures();a["samples"]["dmn-native-cpp"][1]["repeat"]=0
        with self.assertRaises(ValueError):analyse(a,b)


if __name__=="__main__":
    unittest.main()
