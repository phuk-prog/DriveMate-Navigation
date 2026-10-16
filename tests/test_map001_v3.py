"""MAP-001-v3 test-system contracts: separate synthetic controls from UK road facts."""
import unittest
import xml.etree.ElementTree as ET
from benchmarks.map001_v3 import (FROZEN_V2_IDS, turn_differences,
                                   relation_missing_ways, merge_way_full, close_area)
from test_map001_v2 import setup

class Map001v3(unittest.TestCase):
    def test_original_case_selection_immutable(self):
        self.assertEqual(sum(map(len, FROZEN_V2_IDS.values())), 120)
        self.assertIn("155729945", FROZEN_V2_IDS["manchester"])
        self.assertIn("4627827", FROZEN_V2_IDS["glasgow"])

    def test_detect_missing_and_extra_prohibited_turns(self):
        expected = {("a", "b"), ("c", "d")}
        actual = {("a", "b"), ("x", "y")}
        self.assertEqual(turn_differences(expected, actual),
                         ([("c", "d")], [("x", "y")]))

    def test_extra_turn_detected_even_when_every_expected_turn_present(self):
        self.assertEqual(turn_differences({("a", "b")},
                         {("a", "b"), ("b", "c")}), ([], [("b", "c")]))

    def test_missing_relation_member_identified(self):
        nodes, ways, rels = setup()
        root = ET.Element("osm")
        for n in nodes.values(): root.append(n)
        root.append(ways["11"])
        for r in rels: root.append(r)
        self.assertEqual(relation_missing_ways(root, ["11"]), ["12"])

    def test_full_way_merge_adds_nodes_no_duplicate_existing_objects(self):
        nodes, ways, rels = setup()
        root = ET.Element("osm")
        root.append(nodes["2"])
        root.append(ways["11"])
        full = b'<osm><node id="2" lat="53.001" lon="-2"/><node id="3" lat="53.001" lon="-1.999"/><way id="12"><nd ref="2"/><nd ref="3"/><tag k="highway" v="residential"/></way></osm>'
        merge_way_full(root, "12", full)
        self.assertEqual(len(root.findall("node")), 2)
        self.assertEqual(len(root.findall("way")), 2)

    def test_reject_wrong_full_reply(self):
        with self.assertRaises(ValueError):
            merge_way_full(ET.Element("osm"), "12", b'<osm><way id="42"/></osm>')

if __name__ == "__main__":
    unittest.main()
