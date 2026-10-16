import unittest
from benchmarks.latency_comparability import compare_timing

def sample(name,ms):
    return {"engine":name,"worker":"runner-1","interface":"local-http",
            "boundary":"warm-request","temperature":"warm",
            "map_sha":"same-map","profile_sha":"same-profile","cases":["caseA","caseB"],
            "milliseconds":[ms]*6,"valid_routes":6}

class TimingComparabilityTests(unittest.TestCase):
    def test_equal_host_scope_can_rank_real_observations(self):
        rows=compare_timing([sample("DMN",2),sample("OSRM",3)])
        self.assertEqual(rows["status"],"TIMING_ONLY")
        self.assertEqual([x["engine"] for x in rows["ranking"]],["DMN","OSRM"])
    def test_different_interface_cannot_rank(self):
        d=sample("DMN",.01);d["interface"]="in-process"
        self.assertEqual(compare_timing([d,sample("OSRM",2)])["status"],"NOT_COMPARABLE")
    def test_different_worker_cannot_rank(self):
        d=sample("DMN",.01);d["worker"]="runner-2"
        self.assertEqual(compare_timing([d,sample("OSRM",2)])["status"],"NOT_COMPARABLE")
    def test_failed_routes_not_fast_winners(self):
        d=sample("DMN",.01);d["valid_routes"]=4
        self.assertEqual(compare_timing([d,sample("OSRM",2)])["status"],"NOT_COMPARABLE")
    def test_identical_median_tied(self):
        self.assertEqual([x["rank"] for x in compare_timing(
            [sample("DMN",2),sample("OSRM",2)])["ranking"]],[1,1])
