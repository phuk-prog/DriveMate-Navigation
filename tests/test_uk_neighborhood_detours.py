"""Buffered map-rule detour checks; synthetic OSM fixture is NOT a real UK road."""
import unittest
from pathlib import Path
from benchmarks.uk_neighborhood_detours import (find_candidates, evaluate_neighborhood,
                                               _parse_public, expanded_bbox)

ROOT=Path(__file__).resolve().parents[1]
RAW=(ROOT/"benchmarks/fixtures/synthetic-osm-junction.xml").read_bytes()

class BufferedDetourTests(unittest.TestCase):
    def test_find_pinned_nonpersonal_restriction(self):
        cases=find_candidates(RAW,limit=2)
        self.assertEqual(len(cases),1)
        self.assertEqual(cases[0]["relation_id"],"200")
        self.assertEqual(cases[0]["via_id"],"2")
        self.assertEqual(len(cases[0]["bbox"].split(",")),4)

    def test_full_synthetic_network_has_mapped_legal_detour(self):
        out=evaluate_neighborhood(RAW,RAW,relation_id="200",snapshot="synthetic-unit")
        self.assertEqual(out["status"],"map_rule_checked")
        self.assertGreaterEqual(out["rule_pairs"],1)
        self.assertGreaterEqual(out["detours_found"],1)
        self.assertEqual(out["no_route_within_buffer"],0)
        self.assertFalse(out["independent_legality"])

    def test_extra_restriction_not_silently_discarded(self):
        s=RAW.decode()
        new_rel='''<relation id="201"><member type="way" ref="102" role="from"/>
        <member type="node" ref="4" role="via"/>
        <member type="way" ref="103" role="to"/>
        <tag k="type" v="restriction"/>
        <tag k="restriction:conditional" v="no_right_turn @ (Mo-Fr 08:00-10:00)"/>
        <tag k="restriction" v="no_right_turn"/></relation>'''
        augmented=s.replace("</osm>",new_rel+"</osm>").encode()
        out=evaluate_neighborhood(RAW,augmented,relation_id="200",snapshot="synthetic-unit")
        self.assertEqual(out["status"],"unsupported")
        self.assertEqual(out["reason"],"unsupported_graph_or_restriction")

    def test_missing_target_road_is_not_declared_no_route(self):
        s=RAW.decode()
        import re
        # Whole from/to ways remain in the *truth source*, but one is absent
        # in the bounding-box input.
        without_101=re.sub(r'<way id="101">.*?</way>', "", s, flags=re.S).encode()
        out=evaluate_neighborhood(without_101,RAW,relation_id="200",snapshot="synthetic-unit")
        self.assertEqual(out["status"],"unsupported")
        self.assertEqual(out["reason"],"missing_target_way_or_via")
        self.assertEqual(out["no_route_within_buffer"],0)

    def test_invalid_xml_and_contributor_metadata_rejected(self):
        with self.assertRaises(ValueError):_parse_public(b'<bad/>')
        with self.assertRaises(ValueError):
            _parse_public(RAW.replace(b'<node id="1"',b'<node uid="123" id="1"'))

    def test_bounds_of_proposed_areas(self):
        with self.assertRaises(ValueError):find_candidates(RAW,limit=100)
        with self.assertRaises(ValueError):find_candidates(RAW,radius_deg=0.2)


    def test_wider_buffer_is_bounded(self):
        wider=expanded_bbox("-2.007000,53.000000,-1.993000,53.014000")
        self.assertEqual(wider,"-2.014000,52.993000,-1.986000,53.021000")
        self.assertIsNone(expanded_bbox("-2.014000,53.000000,-1.986000,53.028000"))

    def test_invalid_bbox_is_rejected(self):
        with self.assertRaises(ValueError):
            expanded_bbox("-2.1,53.1,-2.2,53.2")


    def test_nondrivable_map_features_do_not_exhaust_importer(self):
        original=RAW.decode()
        filler=''.join(
            f'<way id="{4000+i}"><nd ref="1"/><nd ref="2"/>'
            '<tag k="highway" v="footway"/>'
            '<tag k="oneway:conditional" v="no @ (Su)"/></way>'
            for i in range(200))
        larger=original.replace('</osm>',filler+'</osm>').encode()
        out=evaluate_neighborhood(larger,RAW,relation_id="200",snapshot="synthetic-unit")
        self.assertEqual(out["status"],"map_rule_checked")
        self.assertGreaterEqual(out["detours_found"],1)

    def test_conditional_motorcar_way_still_blocks_prototype(self):
        original=RAW.decode()
        updated=original.replace('<tag k="highway" v="tertiary"/></way>',
            '<tag k="highway" v="tertiary"/>'
            '<tag k="maxspeed:conditional" v="30 @ (Mo-Fr 08:00-10:00)"/></way>',1).encode()
        out=evaluate_neighborhood(updated,RAW,relation_id="200",snapshot="synthetic-unit")
        self.assertEqual(out["status"],"unsupported")
        self.assertEqual(out["reason"],"unsupported_graph_or_restriction")

if __name__=="__main__":
    unittest.main()
