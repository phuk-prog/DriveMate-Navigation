import unittest
from benchmarks.navigation_mutation import run,SEEDS,mutations
class MutationGateTests(unittest.TestCase):
    def test_independent_holdout_and_detectable_injected_failures(self):
        report=run(persist=False)
        self.assertEqual(report["hard_holdout"]["executed"],len(SEEDS)*10*3)
        self.assertEqual(report["hard_holdout"]["failed"],0,
                         report["issues"][:10])
        self.assertEqual(report["mutations"]["injected"],7)
        self.assertEqual(report["mutations"]["detected"],7,report["mutations"]["cases"])
        self.assertEqual(report["mutations"]["baseline_failures"],0)
    def test_mutants_cover_distinct_failure_modes(self):
        names=[row[0] for row in mutations()]
        self.assertEqual(len(names),len(set(names)))
        self.assertIn("fabricated_wrong_way_link",names)
        self.assertIn("lost_inbound_turn_history",names)
        self.assertIn("ignored_bridge_height_limit",names)
if __name__=="__main__":unittest.main()
