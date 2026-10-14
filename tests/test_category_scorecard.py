import unittest
from benchmarks.category_scorecard import correctness_score,speed_scores,overall,CATEGORIES
from benchmarks.cloud_reference import polyline6,geometry_ways
from benchmarks.whole_drive import prepared

class CategoryScoringTests(unittest.TestCase):
    def test_missing_category_never_turns_into_zero_or_overall_rank(self):
        self.assertIsNone(overall({'routing_legality':10}))
        self.assertIsNone(overall({k:None for k,_ in CATEGORIES}))
    def test_invalid_evidence_counts_cannot_earn_a_score(self):
        for counts in ((1,0),(2,1),(True,1),(-1,10)):
            with self.assertRaises(ValueError):correctness_score(*counts)
        self.assertEqual(correctness_score(9,9),10);self.assertEqual(correctness_score(8,10),8)
    def test_latency_score_is_relative_and_rejects_invalid_values(self):
        self.assertEqual(speed_scores({'a':2,'b':4}),{'a':10,'b':5})
        with self.assertRaises(ValueError):speed_scores({'a':0})
    def test_unknown_geometry_never_becomes_expected_path(self):
        p=prepared();self.assertIsNone(geometry_ways(p,[(80,80),(81,81)]))
        self.assertEqual(geometry_ways(p,[p.coordinates['osm:1'],p.coordinates['osm:2'],p.coordinates['osm:3'],p.coordinates['osm:4']]),[10,11,12])
    def test_malformed_polyline_is_rejected(self):
        for value in ('~',' ',123):
            with self.assertRaises(ValueError):polyline6(value)

if __name__=='__main__':unittest.main()
