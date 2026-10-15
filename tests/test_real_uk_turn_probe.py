"""Real OSM semantics contract tests. The synthetic fixtures do not prove legal UK turns."""
import unittest
from pathlib import Path
from benchmarks.real_uk_turn_probe import evaluate, _small_subset, _eligible
from map_data import Provenance,import_osm_xml
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
fixture=(ROOT/"benchmarks/fixtures/synthetic-osm-junction.xml").read_bytes()

class PublicTurnProbeTests(unittest.TestCase):
    def test_explicit_fixture_rule_is_exercised_safely(self):
        r=evaluate(fixture,snapshot="fabricated-for-unit-only",limit=2)
        self.assertGreater(r["eligible_node_via_relations"],0)
        self.assertGreater(r["cases_with_judged_map_rule"],0)
        self.assertGreater(r["tested_map_rule_pairs"],0)
        self.assertFalse(r["independent_road_legality_verified"])
        self.assertIsNone(r["navigation_score"])
    def test_no_restriction_is_unknown_not_a_pass(self):
        raw=fixture.decode()
        raw=raw.replace('k="type" v="restriction"','k="type" v="route"')
        r=evaluate(raw.encode(),snapshot="fabricated-for-unit-only")
        self.assertEqual(r["tested_map_rule_pairs"],0)
        self.assertIn("coverage_gap",r)
    def test_bounds_and_bad_root(self):
        with self.assertRaises(ValueError):evaluate(fixture,snapshot="unit",limit=0)
        with self.assertRaises(ValueError):evaluate(b"<test/>",snapshot="unit")
    def test_reject_contributor_metadata(self):
        raw=fixture.replace(b'<node id="1"',b'<node user="private" id="1"')
        with self.assertRaisesRegex(ValueError,"metadata"):evaluate(raw,snapshot="unit")
    def test_reject_entity(self):
        raw=fixture.replace(b"<osm ",b'<!DOCTYPE osm [<!ENTITY bad "value">]><osm ',1)
        with self.assertRaises(ValueError):evaluate(raw,snapshot="unit")
    def test_source_node_via_only(self):
        root=ET.fromstring(fixture)
        rel=root.find("relation")
        self.assertTrue(_eligible(rel))
        rel.find('member[@role="via"]').set("type","way")
        self.assertFalse(_eligible(rel))
    def test_subset_requires_way_references(self):
        root=ET.fromstring(fixture)
        rel=root.find("relation")
        self.assertIsNone(_small_subset(rel,{},{}))

if __name__=="__main__":
    unittest.main()
