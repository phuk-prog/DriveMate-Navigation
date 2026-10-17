"""TURN-001 importer/routing regressions. Invented fixtures, not real UK roads."""
import unittest

from engine import RouteNotFound, shortest_route
from engine.astar import astar_route
from map_data import OSMImportError, Provenance, import_osm_xml

PROV = Provenance("unit", "synthetic", "unit", "© OpenStreetMap contributors")
#   1 --101-- 2 --102-- 3 --107-- 7
#             |         |
#            104       103
#             |         |
#             4 --105-- 5
NODES = {1: (53.0, -2.003), 2: (53.0, -2.002), 3: (53.0, -2.001), 7: (53.0, -2.0),
         4: (52.999, -2.002), 5: (52.999, -2.001)}
WAYS = {101: (1, 2), 102: (2, 3), 107: (3, 7), 104: (2, 4), 105: (4, 5), 103: (3, 5)}


def osm(relations="", way_tags=None, node_tags=None):
    parts = ['<osm version="0.6">']
    for n, (lat, lon) in NODES.items():
        extra = (node_tags or {}).get(n, "")
        parts.append(f'<node id="{n}" lat="{lat}" lon="{lon}">{extra}</node>')
    for w, refs in WAYS.items():
        extra = (way_tags or {}).get(w, "")
        nds = "".join(f'<nd ref="{r}"/>' for r in refs)
        parts.append(f'<way id="{w}">{nds}<tag k="highway" v="residential"/>{extra}</way>')
    parts.append(relations + "</osm>")
    return "".join(parts).encode()


def rel(rid, rule, frm, to, via, via_type="node", extra=""):
    members = "".join(f'<member type="way" ref="{f}" role="from"/>' for f in (frm if isinstance(frm, list) else [frm]))
    members += f'<member type="{via_type}" ref="{via}" role="via"/>'
    members += "".join(f'<member type="way" ref="{t}" role="to"/>' for t in (to if isinstance(to, list) else [to]))
    return f'<relation id="{rid}">{members}<tag k="type" v="restriction"/>{rule}{extra}</relation>'


def contains(path, seq):
    return any(path[i:i + len(seq)] == seq for i in range(len(path) - len(seq) + 1))


def route_nodes(imported, start_edge, finish_edge):
    g = imported.graph
    r = shortest_route(g, g.edges[start_edge].target, g.edges[finish_edge].target,
                       incoming_edge_id=start_edge, destination_edge_id=finish_edge)
    start = g.edges[start_edge]
    return [start.source.removeprefix("osm:"), start.target.removeprefix("osm:")] + \
        [g.edges[e].target.removeprefix("osm:") for e in r.edge_ids]


class ViaWayRestrictions(unittest.TestCase):
    def test_no_via_way_sequence_is_avoided_but_parts_stay_legal(self):
        m = import_osm_xml(osm(rel(9, '<tag k="restriction" v="no_right_turn"/>', 101, 103, 102, "way")), provenance=PROV)
        self.assertEqual(m.metadata["prohibited_turn_sequences"], 1)
        path = route_nodes(m, "w:101:0:f", "w:103:0:f")
        self.assertFalse(contains(path, ["1", "2", "3", "5"]))
        self.assertEqual(path[-2:], ["3", "5"])
        # Arriving on the via way from elsewhere (4 -> 2 -> 3 -> 5) is not restricted.
        self.assertEqual(route_nodes(m, "w:104:0:r", "w:103:0:f"), ["4", "2", "3", "5"])

    def test_only_via_way_bans_other_exits(self):
        m = import_osm_xml(osm(rel(9, '<tag k="restriction" v="only_straight_on"/>', 101, 103, 102, "way")), provenance=PROV)
        path = route_nodes(m, "w:101:0:f", "w:107:0:f")
        self.assertFalse(contains(path, ["1", "2", "3", "7"]))
        self.assertEqual(path[-2:], ["3", "7"])

    def test_astar_respects_sequences(self):
        m = import_osm_xml(osm(rel(9, '<tag k="restriction" v="no_right_turn"/>', 101, 103, 102, "way")), provenance=PROV)
        g = m.graph
        result = astar_route(g, "osm:2", "osm:5", incoming_edge_id="w:101:0:f", coordinates=m.coordinates)
        nodes = ["2"] + [g.edges[e].target.removeprefix("osm:") for e in result.route.edge_ids]
        self.assertNotEqual(nodes, ["2", "3", "5"])

    def test_unconnected_via_way_still_rejects(self):
        with self.assertRaises(OSMImportError):
            import_osm_xml(osm(rel(9, '<tag k="restriction" v="no_left_turn"/>', 101, 105, 103, "way")), provenance=PROV)


    def test_two_via_ways_in_a_chain(self):
        # from 104 (4->2) via 102 (2->3) and 107 (3->7)? no: via 102 then 103 (3->5), to 105 (5->4)
        rel_xml = ('<relation id="9"><member type="way" ref="104" role="from"/>'
                   '<member type="way" ref="102" role="via"/><member type="way" ref="103" role="via"/>'
                   '<member type="way" ref="105" role="to"/><tag k="type" v="restriction"/>'
                   '<tag k="restriction" v="no_u_turn"/></relation>')
        m = import_osm_xml(osm(rel_xml), provenance=PROV)
        self.assertEqual(m.graph.prohibited_sequences,
                         {("w:104:0:r", "w:102:0:f", "w:103:0:f", "w:105:0:r")})

    def test_truncated_only_restriction_bans_every_exit(self):
        # The permitted exit (way 999) is outside the extract: no exit remains (fail safe).
        rel_xml = rel(9, '<tag k="restriction" v="only_left_turn"/>', 101, 999, 2)
        m = import_osm_xml(osm(rel_xml), provenance=PROV)
        banned = {b for a, b in m.graph.prohibited_turns if a == "w:101:0:f"}
        self.assertEqual(banned, {e.edge_id for e in m.graph.adjacency["osm:2"]})

    def test_uninterpretable_structure_blocks_entry_not_the_map(self):
        rel_xml = ('<relation id="9"><member type="way" ref="101" role="from"/>'
                   '<member type="node" ref="2" role="via"/><member type="way" ref="102" role="via"/>'
                   '<member type="way" ref="103" role="to"/><tag k="type" v="restriction"/>'
                   '<tag k="restriction" v="no_u_turn"/></relation>')
        m = import_osm_xml(osm(rel_xml), provenance=PROV)
        self.assertEqual(m.metadata["restrictions_not_applied"], {"uninterpretable_structure_blocked": 1})
        self.assertIn(("w:101:0:f", "w:102:0:f"), m.graph.prohibited_turns)


class OnewayValues(unittest.TestCase):
    def test_alternating_is_two_way_and_reversible_is_withheld(self):
        alt = import_osm_xml(osm(way_tags={104: '<tag k="oneway" v="alternating"/>'}), provenance=PROV)
        self.assertEqual({alt.graph.edges["w:104:0:f"].access, alt.graph.edges["w:104:0:r"].access}, {"allowed"})
        rev = import_osm_xml(osm(way_tags={104: '<tag k="oneway" v="reversible"/>'}), provenance=PROV)
        self.assertEqual({rev.graph.edges["w:104:0:f"].access, rev.graph.edges["w:104:0:r"].access}, {"unknown"})


class DestinationEdge(unittest.TestCase):
    def test_final_turn_onto_destination_road_is_checked(self):
        m = import_osm_xml(osm(rel(9, '<tag k="restriction" v="no_straight_on"/>', 101, 102, 2)), provenance=PROV)
        g = m.graph
        # Without a destination edge the router may stop at node 2 then "drive" 102 unchecked.
        with self.assertRaises(ValueError):
            shortest_route(g, "osm:2", "osm:2", incoming_edge_id="w:101:0:f", destination_edge_id="w:102:0:f")
        path = route_nodes(m, "w:101:0:f", "w:102:0:f")
        self.assertFalse(contains(path, ["1", "2", "3"]))
        self.assertEqual(path[-2:], ["2", "3"])

    def test_no_route_when_only_illegal_arrival_exists(self):
        ways = {104: '<tag k="access" v="no"/>'}
        m = import_osm_xml(osm(rel(9, '<tag k="restriction" v="no_straight_on"/>', 101, 102, 2), way_tags=ways), provenance=PROV)
        # 1->2->3 banned and 2->4 closed: no legal way onto 2->3 from 101 (U-turn back to 1 is a dead end).
        g = m.graph
        with self.assertRaises(RouteNotFound):
            shortest_route(g, "osm:2", "osm:3", incoming_edge_id="w:101:0:f", destination_edge_id="w:102:0:f")


class RelationApplicability(unittest.TestCase):
    def test_cars_exempt_and_mode_only_restrictions_do_not_apply(self):
        for extra in ('<tag k="restriction" v="no_right_turn"/><tag k="except" v="motor_vehicle"/>',
                      '<tag k="restriction" v="no_right_turn"/><tag k="except" v="vehicle;bicycle"/>',
                      '<tag k="restriction:bus" v="no_right_turn"/>'):
            with self.subTest(extra=extra):
                m = import_osm_xml(osm(rel(9, extra, 101, 104, 2)), provenance=PROV)
                self.assertEqual(len(m.graph.prohibited_turns), 0)

    def test_no_entry_with_several_from_ways(self):
        m = import_osm_xml(osm(rel(9, '<tag k="restriction" v="no_entry"/>', [101, 102], 104, 2)), provenance=PROV)
        self.assertEqual(m.graph.prohibited_turns, {("w:101:0:f", "w:104:0:f"), ("w:102:0:r", "w:104:0:f")})

    def test_member_outside_extract_is_skipped_not_fatal(self):
        m = import_osm_xml(osm(rel(9, '<tag k="restriction" v="no_left_turn"/>', 999, 104, 2)), provenance=PROV)
        self.assertEqual(len(m.graph.prohibited_turns), 0)
        self.assertEqual(m.metadata["restrictions_not_applied"], {"member_outside_extract": 1})

    def test_conditional_ban_applies_at_all_times(self):
        m = import_osm_xml(osm(rel(9, '<tag k="restriction:conditional" v="no_right_turn @ (Mo-Fr 07:00-10:00)"/>',
                                   101, 104, 2)), provenance=PROV)
        self.assertEqual(m.graph.prohibited_turns, {("w:101:0:f", "w:104:0:f")})

    def test_only_turn_to_missing_exit_leaves_no_exit(self):
        m = import_osm_xml(osm(rel(9, '<tag k="restriction" v="only_left_turn"/>', 101, 104, 2),
                               way_tags={104: '<tag k="access" v="no"/>'}), provenance=PROV)
        banned = {b for a, b in m.graph.prohibited_turns if a == "w:101:0:f"}
        self.assertTrue({"w:102:0:f", "w:101:0:r"} <= banned)


class ConditionalAccess(unittest.TestCase):
    def test_access_condition_withholds_only_that_way(self):
        m = import_osm_xml(osm(way_tags={104: '<tag k="motor_vehicle:conditional" v="no @ (07:00-19:00)"/>'}),
                           provenance=PROV)
        access = {k: e.access for k, e in m.graph.edges.items()}
        self.assertEqual({access["w:104:0:f"], access["w:104:0:r"]}, {"unknown"})
        self.assertEqual(access["w:105:0:f"], "allowed")
        self.assertEqual(m.metadata["conditional_ways_withheld"], 1)

    def test_directional_condition_withholds_one_direction(self):
        m = import_osm_xml(osm(way_tags={104: '<tag k="oneway:conditional" v="yes @ (Mo-Fr 07:00-10:00)"/>'}),
                           provenance=PROV)
        self.assertEqual(m.graph.edges["w:104:0:f"].access, "allowed")
        self.assertEqual(m.graph.edges["w:104:0:r"].access, "unknown")

    def test_unrelated_conditionals_ignored(self):
        plain = import_osm_xml(osm(), provenance=PROV)
        speed = import_osm_xml(osm(way_tags={104: '<tag k="maxspeed:conditional" v="20 @ (08:00-09:00)"/>'}),
                               provenance=PROV)
        self.assertEqual({k: e.access for k, e in plain.graph.edges.items()},
                         {k: e.access for k, e in speed.graph.edges.items()})

    def test_conditional_barrier_is_uncertain(self):
        m = import_osm_xml(osm(node_tags={4: '<tag k="barrier" v="bollard"/><tag k="motor_vehicle:conditional" v="yes @ (00:00-06:00)"/>'}),
                           provenance=PROV)
        self.assertNotEqual(m.graph.edges["w:104:0:f"].access, "allowed")


if __name__ == "__main__":
    unittest.main()
