"""Clock check for OSM time conditions (owner-approved, 17 Oct 2026). Synthetic tags only."""
import unittest
from datetime import datetime

from map_data import Provenance, import_osm_xml
from map_data.conditions import condition_applies, parts

PROV = Provenance("synthetic test area", "fabricated-v1", "hand-authored-fixture", "© OpenStreetMap contributors")
MONDAY_8 = datetime(2026, 10, 19, 8, 0)    # a Monday
MONDAY_12 = datetime(2026, 10, 19, 12, 0)
SUNDAY_8 = datetime(2026, 10, 18, 8, 0)


def raw(tag, value):
    return (f'<osm><node id="1" lat="53" lon="-2"/><node id="2" lat="53.001" lon="-2"/>'
            f'<way id="11"><nd ref="1"/><nd ref="2"/><tag k="highway" v="residential"/>'
            f'<tag k="{tag}" v="{value}"/></way></osm>').encode()


class TimeConditionTests(unittest.TestCase):
    def test_weekday_and_time_ranges(self):
        self.assertTrue(condition_applies("(Mo-Fr 07:00-09:30)", MONDAY_8))
        self.assertFalse(condition_applies("(Mo-Fr 07:00-09:30)", MONDAY_12))
        self.assertFalse(condition_applies("(Mo-Fr 07:00-09:30)", SUNDAY_8))
        self.assertTrue(condition_applies("(Mo-Fr 07:00-09:30,16:00-18:30; Sa 08:00-12:00)", MONDAY_8))
        self.assertTrue(condition_applies("(22:00-06:00)", datetime(2026, 10, 19, 23, 0)))
        self.assertTrue(condition_applies("(Su 22:00-06:00)", datetime(2026, 10, 19, 3, 0)))  # Monday 3am
        self.assertTrue(condition_applies("24/7", MONDAY_12))

    def test_unreadable_conditions_are_unknown(self):
        for text in ("(PH)", "(Jan-Mar)", "(weight>7.5)", "(school days)", "(sunrise-sunset)"):
            with self.subTest(text=text):
                self.assertIsNone(condition_applies(text, MONDAY_8))

    def test_parts_split_outside_brackets(self):
        self.assertEqual(parts("no @ (Mo-Fr 07:00-10:00; Sa 08:00-12:00); destination @ (Su)"),
                         [("no", "(Mo-Fr 07:00-10:00; Sa 08:00-12:00)"), ("destination", "(Su)")])

    def test_import_without_a_time_keeps_the_rule_always_on(self):
        m = import_osm_xml(raw("motor_vehicle:conditional", "no @ (Mo-Fr 07:00-09:30)"), provenance=PROV)
        self.assertEqual(m.graph.edges["w:11:0:f"].access, "unknown")

    def test_import_with_the_clock(self):
        tags = raw("motor_vehicle:conditional", "no @ (Mo-Fr 07:00-09:30)")
        self.assertEqual(import_osm_xml(tags, provenance=PROV, when=MONDAY_8).graph.edges["w:11:0:f"].access,
                         "unknown")
        self.assertEqual(import_osm_xml(tags, provenance=PROV, when=MONDAY_12).graph.edges["w:11:0:f"].access,
                         "allowed")
        unreadable = raw("motor_vehicle:conditional", "no @ (PH)")
        self.assertEqual(import_osm_xml(unreadable, provenance=PROV, when=MONDAY_12)
                         .graph.edges["w:11:0:f"].access, "unknown")

    def test_time_limited_one_way(self):
        tags = raw("oneway:conditional", "yes @ (Mo-Fr 07:00-09:30)")
        rush = import_osm_xml(tags, provenance=PROV, when=MONDAY_8).graph.edges
        noon = import_osm_xml(tags, provenance=PROV, when=MONDAY_12).graph.edges
        self.assertEqual(rush["w:11:0:r"].access, "unknown")
        self.assertEqual(noon["w:11:0:r"].access, "allowed")


if __name__ == "__main__":
    unittest.main()
