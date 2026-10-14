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

    def test_restriction_enforced_and_unknown_service_not_banned(self):
        m = imported()
        r = shortest_route(m.graph, "osm:1", "osm:5")
        self.assertEqual(r.edge_ids, ("w:100:0:f", "w:102:0:f", "w:103:0:f", "w:104:0:f"))
        self.assertNotIn(("w:100:0:f", "w:102:0:f"), m.graph.prohibited_turns)
        self.assertIn(("w:100:0:f", "w:101:0:f"), m.graph.prohibited_turns)
        # This service road is slower, but its unknown access is not a closure.
        via_service=shortest_route(m.graph,'osm:2','osm:3',incoming_edge_id='w:100:0:f',
                                  blocked_edges=('w:102:0:f',))
        self.assertEqual(via_service.edge_ids,('w:105:0:f','w:106:0:f'))
        self.assertEqual(via_service.unverified_access_edges,('w:105:0:f',))

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
