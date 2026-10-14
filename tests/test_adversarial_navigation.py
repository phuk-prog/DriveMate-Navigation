"""Hard navigation tests: execution and independently verifiable failure evidence."""
import unittest
from benchmarks.navigation_adversarial import run

class NavigationStressTests(unittest.TestCase):
    def test_generated_roundabouts_junctions_routing_gps_and_recovery(self):
        report=run()
        checks={r['category']:r for r in report['checks']}
        self.assertEqual(report['categories_executed'],5)
        self.assertGreaterEqual(checks['roundabout_geometry']['exit_cases'],200)
        self.assertGreaterEqual(checks['roundabout_geometry']['unsupported_topologies'],50)
        self.assertGreaterEqual(checks['multi_arm_junctions']['legal_turn_cases'],195)
        self.assertGreaterEqual(checks['multi_arm_junctions']['banned_turn_cases'],30)
        self.assertEqual(checks['gps_corruption']['fault_cases'],1008)
        self.assertEqual(checks['gps_corruption']['valid_fix_controls'],1008)
        self.assertEqual(checks['independent_routing_oracle']['route_executions'],300)
        self.assertEqual(checks['compound_gps_recovery']['journey_cases'],72)
        self.assertEqual(report['failure_count'],0,report['checks'])

if __name__=='__main__':
    unittest.main()
