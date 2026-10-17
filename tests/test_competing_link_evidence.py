"""Synthetic topology facts for diagnostics, not independent surveyed truth."""
import unittest
from engine import RoadEdge, RoadGraph
from gps.fix_quality import GPSFix
from gps.matcher import DirectedRoadMatcher
from gps.temporal_matcher import TemporalRoadMatcher
from benchmarks.public_temporal_gps import competing_link_evidence


class CompetingEvidenceTests(unittest.TestCase):
    def test_forward_fragment_and_heading_are_reported_without_raw_identifiers(self):
        coords = {'a': (0, 0), 'b': (0, .0002), 'c': (.0001, .0004)}
        graph = RoadGraph(coords, [RoadEdge('w:1:0:f', 'a', 'b', 23, 30, 'allowed'),
                                   RoadEdge('w:1:1:f', 'b', 'c', 26, 30, 'allowed')])
        temporal = TemporalRoadMatcher(DirectedRoadMatcher(graph, coords))
        rows = competing_link_evidence(temporal, GPSFix(1000, 0, .00018, 3, 10, 90),
                                      {'w:1:0:f'}, {'w:1:0:f', 'w:1:1:f'})
        self.assertEqual(rows[0]['relationship'], 'forward_adjacent')
        self.assertTrue(rows[0]['same_direction_flag'])
        self.assertTrue(rows[0]['direct_is_best_spatial_candidate'])
        self.assertGreater(rows[0]['heading_difference_deg'], 20)
        self.assertNotIn('w:1:', str(rows))

    def test_predecessor_relationship_is_distinct_from_forward_motion(self):
        coords = {'a': (0, 0), 'b': (0, .0002), 'c': (.0001, .0004)}
        graph = RoadGraph(coords, [RoadEdge('w:1:0:f', 'a', 'b', 23, 30, 'allowed'),
                                   RoadEdge('w:1:1:f', 'b', 'c', 26, 30, 'allowed')])
        temporal = TemporalRoadMatcher(DirectedRoadMatcher(graph, coords))
        rows = competing_link_evidence(temporal, GPSFix(1000, 0, .00018, 3, 10, 90),
                                      {'w:1:1:f'}, {'w:1:0:f', 'w:1:1:f'})
        self.assertEqual(rows[0]['relationship'], 'backward_adjacent')

    def test_no_unique_direct_candidate_is_not_manufactured(self):
        self.assertEqual(competing_link_evidence(None, None, set(), set()), [])


if __name__ == '__main__':
    unittest.main()
