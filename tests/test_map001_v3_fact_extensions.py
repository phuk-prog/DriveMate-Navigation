"""Synthetic evidence-only controls, never independently verified UK road truth."""
import unittest
import xml.etree.ElementTree as ET
from benchmarks.map001_v3_restriction_diagnostics import (directed_legs,
      relation_viability, explicit_direction,isolated_direction_mismatch)
from benchmarks.map001_valhalla_graph_facts import expected_direction,summarize_way

def fixture():
    root=ET.fromstring('''<osm>
     <node id="1" lat="53" lon="-2"/>
     <node id="2" lat="53.001" lon="-2"/>
     <node id="3" lat="53.002" lon="-2"/>
     <way id="11"><nd ref="1"/><nd ref="2"/><tag k="highway" v="residential"/><tag k="vehicle:backward" v="no"/></way>
     <way id="12"><nd ref="3"/><nd ref="1"/><tag k="highway" v="tertiary"/><tag k="oneway" v="yes"/></way>
     <relation id="21"><member type="way" ref="11" role="from"/><member type="node" ref="1" role="via"/><member type="way" ref="12" role="to"/><tag k="type" v="restriction"/><tag k="restriction" v="no_left_turn"/></relation>
    </osm>''')
    return ({n.get("id"):n for n in root.findall("node")},
            {w.get("id"):w for w in root.findall("way")},
            root.findall("relation"))

class V3FactExtensions(unittest.TestCase):
    def test_blocked_backward_direction(self):
        n,w,r=fixture()
        arrived=directed_legs(w["11"],"1",n)["arrivals"]
        self.assertEqual(len(arrived),1)
        self.assertEqual(arrived[0]["access"],"prohibited")

    def test_oneway_ending_cannot_depart_from_via(self):
        n,w,r=fixture()
        self.assertEqual(directed_legs(w["12"],"1",n)["departures"],[])

    def test_relation_reports_inapplicable_movement(self):
        n,w,r=fixture()
        self.assertEqual(relation_viability(r[0],w,n)["verdict"],
                         "NO_AVAILABLE_MOTORCAR_MOVEMENT")

    def test_isolated_way_no_longer_has_source_direction_mismatch(self):
        n,w,r=fixture()
        result=isolated_direction_mismatch(w["11"],n)
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]["verdict"],"NO_MISMATCH_DETECTED")
        self.assertEqual(result[0]["graph_edge_count"],0)

    def test_valhalla_edge_fields_are_not_turn_pair_proof(self):
        n,w,r=fixture()
        fake={"edges":[{"edge_info":{"way_id":11},"edge":{"forward":False,
             "access":{"car":True},"start_restriction":{"car":True},
             "end_restriction":{"car":True}}}]}
        x=summarize_way("11",fake,w["11"])
        self.assertEqual(x["source_contradiction_candidates"],1)
        self.assertFalse(x["turn_pairs_comparable"])

    def test_destination_access_is_not_hard_denial(self):
        n,w,r=fixture()
        t={"highway":"residential","motor_vehicle":"destination"}
        self.assertEqual(expected_direction(t,True),"contextual")
        self.assertEqual(expected_direction({"access":"private"},False),"contextual")
        tagged=ET.fromstring('<way id="15"><tag k="highway" v="residential"/><tag k="motor_vehicle" v="destination"/></way>')
        fake={"edges":[{"way_id":15,"edge":{"forward":True,"access":{"car":True},
                     "destination_only":True}}]}
        observation=summarize_way("15",fake,tagged)
        self.assertEqual(observation["source_contradiction_candidates"],0)
        self.assertEqual(observation["contextual_candidate_count"],1)
        self.assertEqual(observation["candidates"][0]["verdict"],"POLICY_CONTEXT_NOT_BINARY")

    def test_missing_verbose_fields_are_unknown(self):
        n,w,r=fixture()
        x=summarize_way("11",{"edges":[{"way_id":11}]},w["11"])
        self.assertFalse(x["directed_candidate_schema_available"])
        self.assertEqual(x["candidates"][0]["verdict"],"UNKNOWN_EDGE_SCHEMA")

if __name__=="__main__":
    unittest.main()
