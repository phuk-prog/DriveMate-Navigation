import hashlib
from pathlib import Path
import unittest

from engine import RouteNotFound, shortest_route
from map_data import OSMImportError, Provenance, import_osm_xml


FIXTURE = Path(__file__).resolve().parents[1] / "benchmarks/fixtures/synthetic-osm-junction.xml"
PROV = Provenance("synthetic test area", "fabricated-v1", "hand-authored-fixture", "© OpenStreetMap contributors")


def imported(xml=None):
    return import_osm_xml(xml if xml is not None else FIXTURE.read_bytes(), provenance=PROV)


class OSMImporterTests(unittest.TestCase):
    def test_provenance_hash_and_directed_access(self):
        raw = FIXTURE.read_bytes()
        m = imported(raw)
        self.assertEqual(m.metadata["source_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertTrue(m.metadata["directed_edges"] > 10)
        self.assertEqual(m.graph.edges["w:100:0:f"].access, "allowed")
        self.assertNotIn("w:100:0:r", m.graph.edges)
        self.assertIn("w:108:0:r", m.graph.edges)
        self.assertNotIn("w:108:0:f", m.graph.edges)
        self.assertAlmostEqual(m.graph.edges["w:100:0:f"].estimated_kph, 30 * 1.609344)
        self.assertEqual(m.graph.edges["w:105:0:f"].access, "unknown")
        self.assertNotIn("w:109:0:f", m.graph.edges)
        self.assertEqual(m.graph.edges["w:110:0:f"].access, "prohibited")

    def test_restriction_enforced_and_no_unknown_service_shortcut(self):
        m = imported()
        r = shortest_route(m.graph, "osm:1", "osm:5")
        self.assertEqual(r.edge_ids, ("w:100:0:f", "w:102:0:f", "w:103:0:f", "w:104:0:f"))
        self.assertNotIn(("w:100:0:f", "w:102:0:f"), m.graph.prohibited_turns)
        self.assertIn(("w:100:0:f", "w:101:0:f"), m.graph.prohibited_turns)
        self.assertNotIn("w:105:0:f", r.edge_ids)

    def test_oncoming_wrong_way_is_not_allowed(self):
        m = imported()
        # A different road gives a legal route back to A, but not the wrong
        # way down the one-way edge from A to B.
        result = shortest_route(m.graph, "osm:2", "osm:1", incoming_edge_id="w:100:0:f")
        self.assertNotIn("w:100:0:r", m.graph.edges)
        self.assertNotIn("w:100:0:r", result.edge_ids)
        self.assertFalse(any(e.target == "osm:1" and e.edge_id.startswith("w:100:")
                             for e in m.graph.adjacency["osm:2"]))

    def test_only_restriction_blocks_all_other_exits(self):
        raw = FIXTURE.read_text()
        raw = raw.replace("no_right_turn", "only_straight_on").replace('ref="101" role="to"', 'ref="102" role="to"')
        m = imported(raw.encode())
        self.assertIn(("w:100:0:f", "w:101:0:f"), m.graph.prohibited_turns)
        self.assertIn(("w:100:0:f", "w:105:0:f"), m.graph.prohibited_turns)
        self.assertNotIn(("w:100:0:f", "w:102:0:f"), m.graph.prohibited_turns)

    def test_except_motorcar_allows_the_turn(self):
        raw = FIXTURE.read_text().replace('<tag k="restriction" v="no_right_turn"/>',
            '<tag k="restriction" v="no_right_turn"/><tag k="except" v="bus;motorcar"/>')
        m = imported(raw.encode())
        self.assertNotIn(("w:100:0:f", "w:101:0:f"), m.graph.prohibited_turns)

    def test_explicit_vehicle_permission_opens_service_road(self):
        raw = FIXTURE.read_text().replace('<tag k="highway" v="service"/>',
            '<tag k="highway" v="service"/><tag k="motorcar" v="yes"/>')
        m = imported(raw.encode())
        self.assertEqual(m.graph.edges["w:105:0:f"].access, "allowed")

    def test_motorcar_prohibition_overrides_general_access(self):
        raw = FIXTURE.read_text().replace('<tag k="highway" v="tertiary"/></way>',
            '<tag k="highway" v="tertiary"/><tag k="access" v="yes"/><tag k="motorcar" v="no"/></way>', 1)
        m = imported(raw.encode())
        self.assertEqual(m.graph.edges["w:102:0:f"].access, "prohibited")

    def test_conditional_restrictions_fail_closed(self):
        raw = FIXTURE.read_text().replace('<tag k="restriction" v="no_right_turn"/>',
            '<tag k="restriction" v="no_right_turn"/><tag k="restriction:conditional" v="no_right_turn @ (Mo-Fr 07:00-10:00)"/>')
        with self.assertRaises(OSMImportError):
            imported(raw.encode())
        way = FIXTURE.read_text().replace('<tag k="oneway" v="yes"/>',
            '<tag k="oneway" v="yes"/><tag k="oneway:conditional" v="no @ (Su)"/>')
        with self.assertRaises(OSMImportError):
            imported(way.encode())

    def test_via_way_restrictions_fail_closed(self):
        raw = FIXTURE.read_text().replace('<member type="node" ref="2" role="via"/>',
            '<member type="way" ref="102" role="via"/>')
        with self.assertRaises(OSMImportError):
            imported(raw.encode())

    def test_missing_nodes_duplicate_ids_and_entity_input_rejected(self):
        raw = FIXTURE.read_text()
        with self.assertRaises(OSMImportError):
            imported(raw.replace('<nd ref="1"/>', '<nd ref="98765"/>').encode())
        with self.assertRaises(OSMImportError):
            imported(raw.replace('<node id="1"', '<node id="2"', 1).encode())
        with self.assertRaises(OSMImportError):
            imported(raw.replace('<osm version', '<!DOCTYPE osm [<!ENTITY x "bad">]><osm version').encode())

    def test_no_real_data_claim_and_bad_provenance(self):
        with self.assertRaises(OSMImportError):
            Provenance("x", "y", "z", "no attribution")
        with self.assertRaises(OSMImportError):
            imported(b"")
        self.assertIn("prototype", imported().metadata["limitations"])


if __name__ == "__main__":
    unittest.main()

class DirectionalAccessRegression(unittest.TestCase):
    """Approved per-direction semantics; fabricated fixtures, not road-law proof."""
    def graph(self, extra='', node_tags=''):
        raw = ('<osm><node id="1" lat="53" lon="-2">' + node_tags +
               '</node><node id="2" lat="53.001" lon="-2"/>'
               '<way id="11"><nd ref="1"/><nd ref="2"/>'
               '<tag k="highway" v="residential"/>' + extra + '</way></osm>')
        return imported(raw.encode()).graph

    def tag(self, key, value):
        return f'<tag k="{key}" v="{value}"/>'

    def test_all_directional_modes_block_only_requested_orientation(self):
        for mode in ('motorcar', 'motor_vehicle', 'vehicle', 'access'):
            for direction, blocked, allowed in (('forward','f','r'),('backward','r','f')):
                with self.subTest(mode=mode,direction=direction):
                    g=self.graph(self.tag(mode+':'+direction,'no'))
                    self.assertEqual(g.edges['w:11:0:'+blocked].access,'prohibited')
                    self.assertEqual(g.edges['w:11:0:'+allowed].access,'allowed')
                    a,b=('osm:1','osm:2') if blocked=='f' else ('osm:2','osm:1')
                    with self.assertRaises(RouteNotFound): shortest_route(g,a,b)
                    self.assertEqual(shortest_route(g,b,a).edge_ids,('w:11:0:'+allowed,))

    def test_specific_mode_precedence_and_directional_refinement(self):
        cases=[({'vehicle:backward':'no','motorcar':'yes'},'allowed'),
               ({'motorcar':'yes','motorcar:backward':'no'},'prohibited'),
               ({'motor_vehicle':'no','motorcar:backward':'yes'},'allowed'),
               ({'motorcar':'no','vehicle:backward':'yes'},'prohibited'),
               ({'access':'no','access:backward':'yes'},'allowed')]
        for t, expected in cases:
            with self.subTest(tags=t):
                g=self.graph(''.join(self.tag(k,v) for k,v in t.items()))
                self.assertEqual(g.edges['w:11:0:r'].access,expected)

    def test_other_modes_do_not_override_ordinary_car_denial(self):
        t=self.tag('vehicle:backward','no')+''.join(self.tag(k+':backward','designated')
                     for k in ('bus','taxi','bicycle'))
        self.assertEqual(self.graph(t).edges['w:11:0:r'].access,'prohibited')

    def test_unknown_and_contextual_direction_fail_closed(self):
        for value, expected in [('mystery','unknown'),('private','prohibited'),
                                ('destination','prohibited'),('customers','prohibited')]:
            with self.subTest(value=value):
                g=self.graph(self.tag('vehicle:backward',value))
                self.assertEqual(g.edges['w:11:0:r'].access,expected)
                with self.assertRaises(RouteNotFound): shortest_route(g,'osm:2','osm:1')

    def test_directional_permission_never_opens_physical_barrier(self):
        g=self.graph(self.tag('vehicle:backward','yes'),self.tag('barrier','bollard'))
        self.assertTrue(all(e.access=='prohibited' for e in g.edges.values()))

    def test_oneway_geometry_remains_authoritative(self):
        for oneway, permission, absent in [('yes','vehicle:backward','r'),('-1','vehicle:forward','f')]:
            with self.subTest(oneway=oneway):
                g=self.graph(self.tag('oneway',oneway)+self.tag(permission,'yes'))
                self.assertNotIn('w:11:0:'+absent,g.edges)

    def test_directional_condition_still_rejects_import(self):
        with self.assertRaises(OSMImportError):
            self.graph(self.tag('vehicle:backward:conditional','yes @ (Mo)'))
