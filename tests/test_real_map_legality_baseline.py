import unittest
from benchmarks.real_map_legality_baseline import forbidden_direct_traversal, judge, sanitize_supported_map


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

    def test_sanitizer_removes_conditional_node_and_dependent_way(self):
        raw=b'''<osm version="0.6"><node id="1" lat="53" lon="-2"><tag k="access:conditional" v="no @ (Mo)"/></node><node id="2" lat="53.001" lon="-2"/><way id="3"><nd ref="1"/><nd ref="2"/><tag k="highway" v="residential"/></way></osm>'''
        clean,summary=sanitize_supported_map(raw)
        self.assertNotIn(b'<way',clean)
        self.assertNotIn(b'id="1"',clean)
        self.assertEqual(1,summary["removed_conditional_or_dependent_ways"])

if __name__=="__main__":unittest.main()
