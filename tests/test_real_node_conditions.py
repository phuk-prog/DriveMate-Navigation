"""Real-road scoped conditional metadata must not bypass car access safety."""
import unittest
from map_data.osm_xml import import_osm_xml, Provenance, OSMImportError

P = Provenance("English road fixture", "unit", "independent unit test", "© OpenStreetMap contributors")


def node(key, value="yes @ (Mo-Fr 07:00-09:00)"):
    xml = ('<osm><node id="1" lat="53.480" lon="-2.240">'
           '<tag k="%s" v="%s"/></node>'
           '<node id="2" lat="53.481" lon="-2.240"/>'
           '<way id="7"><nd ref="1"/><nd ref="2"/>'
           '<tag k="highway" v="residential"/></way></osm>')
    return (xml % (key, value)).encode()


class MotorcarNodeConditionSafetyTests(unittest.TestCase):
    def test_bicycle_only_conditional_does_not_block_motorcar_graph(self):
        m = import_osm_xml(node("bicycle:conditional"), provenance=P)
        self.assertEqual(m.metadata["non_car_node_conditional_tags_not_modelled"], 1)
        self.assertIn("w:7:0:f", m.graph.edges)

    def test_conditional_vehicle_access_or_speed_cannot_silently_pass(self):
        for key in ("access:conditional", "motorcar:conditional",
                    "vehicle:conditional", "maxspeed:conditional", "barrier:conditional"):
            with self.subTest(key=key), self.assertRaises(OSMImportError):
                import_osm_xml(node(key), provenance=P)

    def test_conditional_barrier_even_with_unrelated_key_is_not_ignored(self):
        raw = node("bicycle:conditional").replace(
            b'<tag k="bicycle:conditional"',
            b'<tag k="barrier" v="gate"/><tag k="bicycle:conditional"')
        with self.assertRaises(OSMImportError):
            import_osm_xml(raw, provenance=P)


if __name__ == "__main__":
    unittest.main()
