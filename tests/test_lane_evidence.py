import unittest
from map_data.lane_evidence import parse_turn_lanes,mapped_lanes_for
class LaneEvidenceTests(unittest.TestCase):
    def test_turn_through_lane_preserved(self):
        e=parse_turn_lanes({"oneway":"yes","lanes":"2","turn:lanes":"left|through;right"})
        self.assertEqual(e.status,"MAPPED")
        self.assertEqual(mapped_lanes_for(e,"through"),(2,))
        self.assertEqual(mapped_lanes_for(e,"right"),(2,))
    def test_direction_specific_and_no_unspecified_inference(self):
        self.assertEqual(parse_turn_lanes({"turn:lanes":"left|through"}).status,"UNKNOWN")
        e=parse_turn_lanes({"turn:lanes:backward":"right|through"},direction="backward")
        self.assertEqual(mapped_lanes_for(e,"through"),(2,))
    def test_incomplete_or_conflicting_source_withheld(self):
        for tags in ({"oneway":"yes","lanes":"3","turn:lanes":"left|right"},
                     {"oneway":"yes","turn:lanes":"fly|right"},
                     {"oneway":"yes","turn:lanes":"none;right|through"},
                     {"turn:lanes:forward":"right","turn:lanes:conditional":"left @ (Mo-Fr)"}):
            self.assertEqual(parse_turn_lanes(tags).status,"UNKNOWN")
    def test_unknown_lane_does_not_offer_best(self):
        self.assertEqual(mapped_lanes_for(parse_turn_lanes({}),"right"),())
