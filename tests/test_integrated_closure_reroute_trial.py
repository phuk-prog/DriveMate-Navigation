"""Synthetic closure/routing integration; not live traffic evidence."""
import unittest

from benchmarks.integrated_closure_reroute_trial import run_dmn
from benchmarks.integrated_journey_trial import scorecard


class IntegratedClosureRerouteTests(unittest.TestCase):
    def test_frozen_four_case_baseline(self):
        report=run_dmn()
        self.assertEqual((report["passed"],report["failed"],report["total"]),(4,0,4))

    def test_only_current_verified_legal_closure_proposes(self):
        rows={row["case_id"]:row["actual"] for row in run_dmn()["cases"]}
        proposed=[case_id for case_id,actual in rows.items()
                  if actual["traffic_decision"]["propose_reroute"]]
        self.assertEqual(proposed,["INTEGRATED-005-current-verified-closure"])
        self.assertEqual(rows[proposed[0]]["route_edges"],["w:95:0:f","w:100:0:f","w:50:0:f"])
        self.assertEqual(rows["INTEGRATED-005-no-legal-detour"]["route_status"],"NO_ROUTE")

    def test_external_families_are_unranked(self):
        rows=scorecard(run_dmn())["rows"]
        self.assertEqual(len(rows),13)
        self.assertTrue(all(row["rank"] is None for row in rows[1:]))


if __name__=="__main__":unittest.main()
