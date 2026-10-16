"""Independent source-oracle mutation controls (synthetic, not UK legal facts)."""
import unittest
from benchmarks.map001_native_six_region import rank_rows
import xml.etree.ElementTree as ET
from benchmarks.map001_category1_closure import (
    expected_way, compare_rows, relation_facts, mode_access, barrier_access,
    conditional, combined)


def case(waytags="", left="", right=""):
    root = ET.fromstring('<osm>'
        '<node id="1" lat="53" lon="-2">' + left + '</node>'
        '<node id="2" lat="53.001" lon="-2.001">' + right + '</node>'
        '<way id="42"><nd ref="1"/><nd ref="2"/><tag k="highway" v="residential"/>'
        + waytags + '</way></osm>')
    nodes = {x.get("id"): x for x in root.findall("node")}
    return root.find("way"), nodes


class FrozenCategoryClosureTests(unittest.TestCase):
    def test_restriction_in_reverse_source_direction(self):
        way, nodes = case('<tag k="vehicle:backward" v="no"/>')
        edges, why = expected_way(way, nodes)
        self.assertIsNone(why)
        self.assertEqual(edges["w:42:0:f"], ("osm:1", "osm:2", "allowed"))
        self.assertEqual(edges["w:42:0:r"], ("osm:2", "osm:1", "prohibited"))

    def test_oneway_remove_wrong_way_edges_not_just_deny(self):
        way, nodes = case('<tag k="oneway" v="yes"/>')
        edges, why = expected_way(way, nodes)
        self.assertEqual(set(edges), {"w:42:0:f"})
        self.assertIsNone(why)
        way, nodes = case('<tag k="oneway" v="-1"/>')
        edges, _ = expected_way(way, nodes)
        self.assertEqual(set(edges), {"w:42:0:r"})

    def test_mode_precedence_vs_general_road_access(self):
        self.assertEqual(mode_access({"motorcar": "yes", "vehicle:backward": "no"}, "r"), "allowed")
        self.assertEqual(mode_access({"vehicle": "yes", "vehicle:backward": "no"}, "r"), "prohibited")
        self.assertEqual(mode_access({"motor_vehicle": "destination"}, "f"), "unknown")
        self.assertEqual(mode_access({"access": "private"}, "r"), "unknown")

    def test_barriers_and_uncertain_sources(self):
        self.assertEqual(barrier_access({"barrier": "bollard"}), "prohibited")
        self.assertEqual(barrier_access({"barrier": "gate"}), "unknown")
        self.assertEqual(barrier_access({"barrier": "gate", "motorcar": "yes"}), "allowed")
        self.assertEqual(combined("allowed", "unknown", "prohibited"), "prohibited")
        way, nodes = case('<tag k="access" v="private"/>')
        expected, _ = expected_way(way, nodes)
        self.assertEqual({x[2] for x in expected.values()}, {"unknown"})

    def test_conditionals_are_not_accepted_as_binary_access(self):
        way, nodes = case('<tag k="vehicle:conditional" v="no @ (Mo-Fr 07:00-09:00)"/>')
        self.assertEqual(expected_way(way, nodes)[1],
                         "conditional_source_requires_vehicle_time_policy")
        self.assertTrue(conditional({"restriction:motorcar:conditional": "no @ (Mo-Fr)"}))

    def test_mutation_detects_missing_extra_and_wrong_edges(self):
        way, nodes = case('<tag k="vehicle:backward" v="no"/>')
        expected, _ = expected_way(way, nodes)
        self.assertEqual(compare_rows(expected, expected)["verdict"], "MATCH")
        changed = dict(expected)
        changed["w:42:0:r"] = ("osm:2", "osm:1", "allowed")
        self.assertIn("w:42:0:r", compare_rows(expected, changed)["wrong"])
        changed.pop("w:42:0:r")
        changed["w:42:9:f"] = ("osm:1", "osm:2", "allowed")
        self.assertEqual(compare_rows(expected, changed)["verdict"], "FAIL")
        self.assertIn("w:42:9:f", compare_rows(expected, changed)["extra"])

    def test_inapplicable_direction_is_not_road_legality_proof(self):
        way, nodes = case('<tag k="oneway" v="yes"/>')
        rel = ET.fromstring('''<relation id="6">
          <member type="way" ref="42" role="from"/>
          <member type="node" ref="1" role="via"/>
          <member type="way" ref="42" role="to"/>
          <tag k="type" v="restriction"/><tag k="restriction" v="no_u_turn"/>
          </relation>''')
        check = relation_facts(rel, {"42": way}, nodes)
        self.assertEqual(check["verdict"], "NO_MOTORCAR_SOURCE_MOVEMENT")
        self.assertFalse(check["motorcar_road_law_verified"])

    def test_relations_with_contextual_access_withheld(self):
        way, nodes = case('<tag k="access" v="private"/>')
        rel = ET.fromstring('''<relation id="7">
          <member type="way" ref="42" role="from"/>
          <member type="node" ref="1" role="via"/>
          <member type="way" ref="42" role="to"/>
          <tag k="type" v="restriction"/><tag k="restriction" v="no_u_turn"/>
          </relation>''')
        r = relation_facts(rel, {"42": way}, nodes)
        self.assertEqual(r["verdict"], "WITHHELD_UNQUALIFIED_MOTORCAR_ACCESS")

    def test_native_rank_only_shared_binary_complete_cases(self):
        rows = [
            {"source_way": "1", "equivalent_scored_cohort": True,
             "dmn_verdict": "PASS", "valhalla_verdict": "PASS"},
            {"source_way": "2", "equivalent_scored_cohort": False,
             "dmn_verdict": "PASS", "valhalla_verdict": "UNSUPPORTED"},
            {"source_way": "3", "equivalent_scored_cohort": True,
             "dmn_verdict": "PASS", "valhalla_verdict": "FAIL"}]
        common, ranks = rank_rows(rows)
        self.assertEqual(len(common), 2)
        self.assertEqual(ranks[0]["engine"], "DMN ★")
        self.assertEqual(ranks[0]["pass"], 2)
        self.assertEqual(ranks[1]["fail"], 1)
        self.assertTrue(all(r["total"] == 2 for r in ranks))


if __name__ == "__main__":
    unittest.main()
