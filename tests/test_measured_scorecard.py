"""Scoreboard must contain only genuinely measured and matched category results."""
import unittest
from benchmarks.cloud_report import scorecard_markdown

class MeasuredScorecardTests(unittest.TestCase):
    def test_no_empty_unexecuted_engines_or_n_t_placeholder_rows(self):
        matched={
          "cases":[
            {"case":"ring_exit_1","results":{"DriveMate":"pass","GraphHopper":"pass","OSRM MLD":"unknown"}},
            {"case":"ring_exit_2","results":{"DriveMate":"pass","GraphHopper":"pass","OSRM MLD":"pass"}},
            {"case":"ring_exit_3","results":{"DriveMate":"pass","GraphHopper":"pass","OSRM MLD":"pass"}},
            {"case":"ring_exit_4","results":{"DriveMate":"pass","GraphHopper":"pass","OSRM MLD":"pass"}}
          ],
          "summaries":{
            "DriveMate":{"passed":4,"failed":0,"unknown":0,"not_tested":0,"test_cases":4},
            "GraphHopper":{"passed":4,"failed":0,"unknown":0,"not_tested":0,"test_cases":4},
            "OSRM MLD":{"passed":3,"failed":0,"unknown":1,"not_tested":0,"test_cases":4},
            "OSRM CH":{"passed":0,"failed":0,"unknown":0,"not_tested":4,"test_cases":4}
          }
        }
        text=scorecard_markdown({"DriveMate":{"scores":{"gps_matching":10.0}},
            "GraphHopper":{"scores":{"gps_matching":10.0}}},matched)
        self.assertNotIn("N/T",text)
        self.assertIn("| OSRM MLD | 3/4 | 0 | 1 |",text)
        self.assertNotIn("| OSRM CH |",text)
        self.assertNotIn("| Organic Maps |",text)
        self.assertIn("excluded",text.lower())

    def test_no_reference_scorecard_is_still_explicitly_unavailable(self):
        text=scorecard_markdown({},{"summaries":{},"cases":[]})
        self.assertIn("No fully executed paired comparison",text)
        self.assertNotIn("| TomTom |",text)

if __name__=="__main__":
    unittest.main()
