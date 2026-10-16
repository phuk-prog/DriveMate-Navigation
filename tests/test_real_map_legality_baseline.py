import unittest
from benchmarks.real_map_legality_baseline import forbidden_direct_traversal, judge


class LegalityBaselineTests(unittest.TestCase):
    def setUp(self):
        self.case={"id":"X","allowed_start":[53.0,-2.0],"allowed_end":[53.001,-2.0]}

    def test_detects_direct_reverse_use(self):
        self.assertTrue(forbidden_direct_traversal([self.case["allowed_end"],self.case["allowed_start"]],
                                                   self.case["allowed_start"],self.case["allowed_end"]))

    def test_detour_does_not_count_as_direct_reverse(self):
        points=[self.case["allowed_end"],[53.001,-1.999],[53.0,-1.999],self.case["allowed_start"]]
        self.assertFalse(forbidden_direct_traversal(points,self.case["allowed_start"],self.case["allowed_end"]))

    def test_reverse_no_route_is_safe_pass(self):
        self.assertEqual("PASS",judge(self.case,"reverse",{"status":"NO_ROUTE"},1)["outcome"])

    def test_allowed_no_route_fails(self):
        self.assertEqual("FAIL",judge(self.case,"allowed",{"status":"NO_ROUTE"},1)["outcome"])

if __name__=="__main__":unittest.main()
