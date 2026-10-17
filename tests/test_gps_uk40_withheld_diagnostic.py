"""Check diagnosis categories only; do not invent real-road tests."""
import unittest
from benchmarks.gps_uk40_withheld_diagnostic import classify

class DiagnosticReasons(unittest.TestCase):
    def test_missing_anchor(self):
        self.assertEqual(classify(None,"a",{"a"},{"a"}),"NO_TRUSTED_INITIAL_ANCHOR")
    def test_expected_fragment_missing(self):
        self.assertEqual(classify("old","a",{"b"},{"b"}),
                         "GENERATING_FRAGMENT_NOT_IN_CANDIDATES")
    def test_none_time_reachable(self):
        self.assertEqual(classify("old","a",{"a"},set()),
                         "NO_TIME_REACHABLE_CANDIDATE")
    def test_generating_fragment_not_reachable(self):
        self.assertEqual(classify("old","a",{"a","b"},{"b"}),
                         "GENERATING_FRAGMENT_NOT_TIME_REACHABLE")
    def test_multiple_reachable(self):
        self.assertEqual(classify("old","a",{"a","b"},{"a","b"}),
                         "MULTIPLE_TIME_REACHABLE_CANDIDATES")
    def test_unique_but_uncertain(self):
        self.assertEqual(classify("old","a",{"a"},{"a"}),
                         "UNRESOLVED_DESPITE_UNIQUE_REACHABLE_CANDIDATE")
