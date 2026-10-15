"""Synthetic straight-link segmentation counterexamples and branch controls."""
import unittest
from engine import RoadEdge, RoadGraph
from gps.fix_quality import GPSFix
from gps.matcher import DirectedRoadMatcher
from gps.temporal_matcher import TemporalRoadMatcher
from benchmarks.navigation_trial import run_dmn


class LinkContinuityTests(unittest.TestCase):
    def test_straight_same_way_segmentation_does_not_create_competing_roads(self):
        report = run_dmn()
        for case in report['cases'][:4]:
            with self.subTest(case=case['case_id']):
                self.assertEqual(case['outcome'], 'PASS')

    def test_distinct_way_branch_near_node_remains_ambiguous(self):
        coords = {'a': (0, 0), 'b': (0, .0002),
                  'c': (0, .0004), 'd': (.00001, .0004)}
        graph = RoadGraph(coords, [
            RoadEdge('w:1:0:f', 'a', 'b', 23, 30, 'allowed'),
            RoadEdge('w:1:1:f', 'b', 'c', 23, 30, 'allowed'),
            RoadEdge('w:2:0:f', 'b', 'd', 23, 30, 'allowed')])
        result = DirectedRoadMatcher(graph, coords).match(GPSFix(1000, 0, .00022, 3, 6, 90))
        self.assertEqual(result.status, 'AMBIGUOUS')

    def test_multilink_motion_within_time_budget_is_followed(self):
        report = run_dmn()
        self.assertEqual(report['cases'][4]['outcome'], 'PASS')

    def test_multilink_forbidden_turn_cannot_be_bypassed(self):
        coords = {str(i): (0, i * .0002) for i in range(6)}
        edges = [RoadEdge(f'w:1:{i}:f', str(i), str(i+1), 23, 30, 'allowed')
                 for i in range(5)]
        graph = RoadGraph(coords, edges, [('w:1:1:f', 'w:1:2:f')])
        matcher = TemporalRoadMatcher(DirectedRoadMatcher(graph, coords))
        self.assertEqual(matcher.update(GPSFix(1000, 0, .0001, 1, 10, 90)).status, 'MATCHED')
        result = matcher.update(GPSFix(5000, 0, .0007, 1, 10, 90))
        self.assertNotEqual(result.status, 'MATCHED')

    def test_disconnected_parallel_segments_with_same_way_label_stay_ambiguous(self):
        coords = {'a': (0, 0), 'b': (0, .001),
                  'c': (.00004, 0), 'd': (.00004, .001)}
        graph = RoadGraph(coords, [
            RoadEdge('w:1:0:f', 'a', 'b', 112, 30, 'allowed'),
            RoadEdge('w:1:1:f', 'c', 'd', 112, 30, 'allowed')])
        result = DirectedRoadMatcher(graph, coords).match(GPSFix(1000, .00002, .0005, 3, 6, 90))
        self.assertEqual(result.status, 'AMBIGUOUS')

    def test_connector_search_bound_withholds_overlong_history(self):
        coords = {str(i): (0, i * .0002) for i in range(14)}
        edges = [RoadEdge(f'w:1:{i}:f', str(i), str(i+1), 23, 30, 'allowed')
                 for i in range(13)]
        graph = RoadGraph(coords, edges)
        matcher = TemporalRoadMatcher(DirectedRoadMatcher(graph, coords),
                                      max_anchor_displacement_m=500)
        self.assertEqual(matcher.update(GPSFix(1000, 0, .0001, 1, 30, 90)).status, 'MATCHED')
        result = matcher.update(GPSFix(9000, 0, .0023, 1, 30, 90))
        self.assertNotEqual(result.status, 'MATCHED')

    def test_temporal_candidates_do_not_double_count_same_straight_road(self):
        coords = {'p': (0, -.0005), 'a': (0, 0), 'b': (0, .0002),
                  'c': (0, .0004), 'd': (-.00004, .0002), 'e': (-.00004, .0004)}
        graph = RoadGraph(coords, [
            RoadEdge('feeder', 'p', 'a', 56, 40, 'allowed'),
            RoadEdge('w:1:0:f', 'a', 'b', 23, 40, 'allowed'),
            RoadEdge('w:1:1:f', 'b', 'c', 23, 40, 'allowed'),
            RoadEdge('w:2:0:f', 'd', 'e', 23, 40, 'allowed')])
        matcher = TemporalRoadMatcher(DirectedRoadMatcher(graph, coords))
        self.assertEqual(matcher.update(GPSFix(1000, 0, -.0004, 3, 10, 90)).edge_id, 'feeder')
        result = matcher.update(GPSFix(5000, 0, .00022, 3, 10, 90))
        self.assertEqual((result.status, result.edge_id), ('MATCHED', 'w:1:1:f'))


if __name__ == '__main__':
    unittest.main()
