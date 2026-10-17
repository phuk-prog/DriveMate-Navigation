import unittest
from benchmarks.map001_valhalla_locate import extract_way_ids, interpret

class ValhallaMap001v3(unittest.TestCase):
    def test_locate_way_ids(self):
        self.assertEqual(extract_way_ids({"edges": [
            {"way_id": 42}, {"edge_info": {"way_id": 45}}
        ]}), {"42", "45"})
    def test_no_claim_on_unknown_schema(self):
        self.assertEqual(interpret("42", {"nodes": []}), "SCHEMA_UNAVAILABLE")
    def test_wrong_candidate_not_graph_fidelity_failure(self):
        self.assertEqual(interpret("42", {"edges": [{"way_id": 43}]}),
                         "UNRESOLVED_CORRELATION")
    def test_visible(self):
        self.assertEqual(interpret("42", {"edges": [{"way_id": 42}]}),
                         "WAY_VISIBLE")

if __name__ == "__main__":
    unittest.main()
