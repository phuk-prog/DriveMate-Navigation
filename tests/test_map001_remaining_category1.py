"""Category 1 withheld-access, conditional and native source-mask mutation tests.

Synthetic fixture controls never count toward independently verified UK road law.
"""
from __future__ import annotations
from datetime import datetime,timezone
import unittest
import xml.etree.ElementTree as ET

from benchmarks.map001_remaining_access import source_family,scenario,conditioned_way
from benchmarks.map001_native_turn_barrier import (
    native_mask_verdict,candidate_pairs,assess_relation,barrier_case,only_native_junction_verdict)


def fixture(road='residential',other='',barrier=''):
    root=ET.fromstring('<osm>'
        '<node id="1" lat="53" lon="-2">'+barrier+'</node>'
        '<node id="2" lat="53.0001" lon="-2.0001"/>'
        '<way id="42"><nd ref="1"/><nd ref="2"/>'
        '<tag k="highway" v="'+road+'"/>'+other+'</way></osm>')
    nodes={n.get("id"):n for n in root.findall("node")}
    return root.find("way"),nodes


def rel(rule='no_u_turn'):
    return ET.fromstring('<relation id="777">'
       '<member type="way" ref="42" role="from"/>'
       '<member type="node" ref="1" role="via"/>'
       '<member type="way" ref="42" role="to"/>'
       '<tag k="type" v="restriction"/>'
       '<tag k="restriction" v="'+rule+'"/></relation>')


class OutstandingAccessControls(unittest.TestCase):
    def test_private_permission_cannot_leak_from_unrelated_way(self):
        way,nodes=fixture('service','<tag k="access" v="private"/>')
        self.assertEqual(source_family(way,nodes),'OWNER_AUTHORIZATION')
        out=scenario(way,nodes,"fixture",'OWNER_AUTHORIZATION')
        self.assertEqual(out["baseline_policy"],"SAFE_WITHHELD")
        self.assertTrue(out["route_safety_gate_pass"])
        self.assertFalse(out["actual_route_search_observation"]["default_can_route"])
        self.assertFalse(out["actual_route_search_observation"]["unrelated_context_can_route"])
        self.assertTrue(out["actual_route_search_observation"]["hypothetical_matched_can_route"])
        self.assertFalse(out["legal_permission_proven"])

    def test_private_authorization_cannot_pass_a_gated_midway_node(self):
        root=ET.fromstring('''<osm>
          <node id="1" lat="53" lon="-2"/>
          <node id="2" lat="53.0001" lon="-2.0001"><tag k="barrier" v="gate"/></node>
          <node id="3" lat="53.0002" lon="-2.0002"/>
          <way id="42"><nd ref="1"/><nd ref="2"/><nd ref="3"/>
            <tag k="highway" v="service"/><tag k="access" v="private"/></way>
        </osm>''')
        way=root.find('way')
        nodes={n.get('id'):n for n in root.findall('node')}
        out=scenario(way,nodes,"fixture","OWNER_AUTHORIZATION")
        self.assertTrue(out["route_safety_gate_pass"])
        self.assertFalse(out["actual_route_search_observation"]["hypothetical_matched_can_route"])
        self.assertEqual(out["remaining_unverified_physical_barrier_nodes"],{"2":"gate"})
        self.assertEqual(out["matched_scenario_states"],{"unknown":4})
        self.assertFalse(out["legal_permission_proven"])

    def test_destination_requires_matching_way_and_actual_destination(self):
        way,nodes=fixture('residential','<tag k="motor_vehicle" v="destination"/>')
        self.assertEqual(source_family(way,nodes),'QUALIFYING_JOURNEY_DESTINATION')
        out=scenario(way,nodes,"fixture",'QUALIFYING_JOURNEY_DESTINATION')
        self.assertTrue(out["route_safety_gate_pass"])
        self.assertTrue(out["actual_route_search_observation"]["hypothetical_matched_can_route"])
        self.assertEqual(out["current_road_legality"],"NOT_JUDGED")

    def test_permit_not_autogranted_by_generic_authorization(self):
        way,nodes=fixture('residential','<tag k="motor_vehicle" v="permit"/>')
        self.assertEqual(source_family(way,nodes),'AUTHORITY_ISSUED_WAY_PERMISSION')
        out=scenario(way,nodes,"fixture",'AUTHORITY_ISSUED_WAY_PERMISSION')
        self.assertTrue(out["route_safety_gate_pass"])
        self.assertEqual(out["matched_scenario_states"],{"unknown":2})
        self.assertFalse(out["actual_route_search_observation"]["hypothetical_matched_can_route"])

    def test_unmarked_service_does_not_become_public_by_assertion(self):
        way,nodes=fixture("service")
        self.assertEqual(source_family(way,nodes),"UNSPECIFIED_SERVICE")
        out=scenario(way,nodes,"fixture","UNSPECIFIED_SERVICE")
        self.assertTrue(out["route_safety_gate_pass"])
        self.assertFalse(out["actual_route_search_observation"]["hypothetical_matched_can_route"])

    def test_unknown_physical_gate_cannot_be_unlocked(self):
        way,nodes=fixture("unclassified",barrier='<tag k="barrier" v="gate"/>')
        self.assertEqual(source_family(way,nodes),"UNKNOWN_PHYSICAL_GATE")
        out=scenario(way,nodes,"fixture","UNKNOWN_PHYSICAL_GATE")
        self.assertTrue(out["route_safety_gate_pass"])
        self.assertEqual(out["baseline_states"],{"unknown":2})

    def test_explicit_vehicle_mode_beats_general_denial(self):
        way,nodes=fixture("living_street",'<tag k="access" v="no"/><tag k="motor_vehicle" v="permit"/>')
        self.assertEqual(source_family(way,nodes),"AUTHORITY_ISSUED_WAY_PERMISSION")

    def test_conditional_daylight_and_overnight_imports_remain_blocked(self):
        for expr in ('no @ 07:00-19:00','delivery @ (18:00-11:00)'):
            with self.subTest(expr=expr):
                way,nodes=fixture("primary",
                    '<tag k="motor_vehicle:conditional" v="'+expr+'"/>')
                out=conditioned_way(way,nodes,"fixture")
                self.assertTrue(out["always_safe_import_rejection"])
                self.assertFalse(out["expressions"][0]["legal_date_or_signed_order_verified"])
                self.assertEqual(out["current_road_legality"],"NOT_JUDGED")
                times=out["expressions"][0]["instants_utc"]
                self.assertEqual(len(times),4)
                self.assertNotEqual(times[0]["local"][-6:],times[1]["local"][-6:])

    def test_qualifying_time_does_not_prove_vehicle_entitlement(self):
        way,nodes=fixture("primary",'<tag k="motor_vehicle:conditional" v="delivery @ (18:00-11:00)"/>')
        out=conditioned_way(way,nodes,"fixture")
        self.assertTrue(any(c["source_expression_active"]
                            for c in out["expressions"][0]["instants_utc"]))
        self.assertTrue(all(e["ordinary_motorcar_legal_permission"]=="NOT_ESTABLISHED"
                            for e in out["expressions"]))


class NativeStructuralControls(unittest.TestCase):
    def candidate(self, mask=2, incoming=True, outgoing=True, contextual=False):
        return {"incoming_car":incoming,"outgoing_car":outgoing,
                "local_index":1,"mask_bit":bool(mask & 2),
                "contextual_native_flags":contextual}

    def test_prohibited_turn_native_mask_bit_compares_both_ways(self):
        self.assertEqual(native_mask_verdict("no_left_turn",
             "REPRESENTABLE_SOURCE_MOVEMENT",[self.candidate(mask=2)]),"PASS")
        self.assertEqual(native_mask_verdict("no_left_turn",
             "REPRESENTABLE_SOURCE_MOVEMENT",[self.candidate(mask=0)]),"FAIL")
        self.assertEqual(native_mask_verdict("no_left_turn",
             "REPRESENTABLE_SOURCE_MOVEMENT",[self.candidate(mask=0,contextual=True)]),
             "NOT_JUDGED_NATIVE_TURN_POLICY_CONTEXT")

    def test_only_turn_not_falsely_scored_against_one_mask_bit(self):
        self.assertEqual(native_mask_verdict("only_right_turn",
             "REPRESENTABLE_SOURCE_MOVEMENT",[self.candidate()]),
             "UNSUPPORTED_ONLY_TURN_COMPLETENESS")

    def test_unusable_source_and_no_native_pair_unjudged(self):
        self.assertEqual(native_mask_verdict("no_u_turn",
             "NO_MOTORCAR_SOURCE_MOVEMENT",[self.candidate()]),
             "NOT_JUDGED_SOURCE_MOVEMENT_OR_ACCESS")
        self.assertEqual(native_mask_verdict("no_u_turn",
             "REPRESENTABLE_SOURCE_MOVEMENT",[]),
             "NOT_JUDGED_ZERO_OR_MULTIPLE_NATIVE_PAIRS")
        self.assertEqual(native_mask_verdict("no_u_turn",
             "REPRESENTABLE_SOURCE_MOVEMENT",[self.candidate(),self.candidate()]),
             "NOT_JUDGED_ZERO_OR_MULTIPLE_NATIVE_PAIRS")

    def test_node_gate_not_equivalent_native_edge_flag(self):
        way,nodes=fixture("unclassified",barrier='<tag k="barrier" v="block"/>')
        native=[{"graph_id":82,"way_id":42,"car_access":True,
                 "start_restriction":0,"end_restriction":0,
                 "access_restriction":0,"restriction_mask":0}]
        out=barrier_case("fixture",way,nodes,native)
        self.assertFalse(out["scored"])
        self.assertEqual(out["verdict"],"NOT_JUDGED_NATIVE_NODE_TRAVERSAL")
        self.assertTrue(out["native_edge_indicators"][0]["car_access"])

    def test_native_node_auto_mask_correlates_block_but_not_full_traversal(self):
        way,nodes=fixture("unclassified",barrier='<tag k="barrier" v="block"/>')
        native=[{"graph_id":82,"way_id":42,"car_access":True,
                 "start_node":901,"end_node":902,
                 "start_node_auto_access":False,"end_node_auto_access":True,
                 "start_node_type":4,"end_node_type":0,
                 "shape":[[53,-2],[53.0001,-2.0001]],
                 "start_restriction":0,"end_restriction":0,
                 "access_restriction":0,"restriction_mask":0}]
        out=barrier_case("fixture",way,nodes,native)
        checks=out["source_vs_native_node_access_checks"]
        self.assertEqual(checks[0]["source_vs_native_node_access"],
                         "MATCHED_CLOSED_NATIVE_AUTO_ACCESS_MASK")
        self.assertFalse(checks[0]["motorcar_traversal_verified"])
        self.assertFalse(out["native_node_policy_equivalent"])
        self.assertEqual(out["verdict"],"NOT_JUDGED_NATIVE_NODE_TRAVERSAL")

    def test_native_gate_auto_access_does_not_prove_permission(self):
        way,nodes=fixture("unclassified",barrier='<tag k="barrier" v="gate"/>')
        native=[{"graph_id":83,"way_id":42,"car_access":True,
                 "start_node":901,"end_node":902,
                 "start_node_auto_access":True,"end_node_auto_access":True,
                 "start_node_type":5,"end_node_type":0,
                 "shape":[[53,-2],[53.0001,-2.0001]],
                 "start_restriction":0,"end_restriction":0,
                 "access_restriction":0,"restriction_mask":0}]
        out=barrier_case("fixture",way,nodes,native)
        self.assertEqual(out["source_vs_native_node_access_checks"][0]
                         ["source_vs_native_node_access"],
                         "NOT_JUDGED_NODE_POLICY_OR_GATE_STATE")
        self.assertFalse(out["scored"])

    def test_relation_context_and_missing_geometry_not_automatic_fail(self):
        way,nodes=fixture("residential")
        row=assess_relation("fixture",rel(),{"42":way},nodes,[])
        self.assertNotEqual(row["verdict"],"FAIL")
        self.assertEqual(row["full_turn_legality"],"NOT_INSPECTED")

    def test_only_turn_checks_all_outgoing_graph_alternatives(self):
        root=ET.fromstring("""<osm>
          <node id="1" lat="53" lon="-2"/>
          <node id="2" lat="53.0001" lon="-2.0001"/>
          <node id="3" lat="53.0002" lon="-2.0002"/>
          <node id="4" lat="53.0003" lon="-2.0003"/>
          <way id="42"><nd ref="1"/><nd ref="2"/>
            <tag k="highway" v="residential"/></way>
          <way id="43"><nd ref="2"/><nd ref="3"/>
            <tag k="highway" v="residential"/></way>
          <way id="44"><nd ref="2"/><nd ref="4"/>
            <tag k="highway" v="residential"/></way>
        </osm>""")
        nodes={n.get("id"):n for n in root.findall("node")}
        ways={w.get("id"):w for w in root.findall("way")}
        relation=ET.fromstring("""<relation id="777">
          <member type="way" ref="42" role="from"/>
          <member type="node" ref="2" role="via"/>
          <member type="way" ref="43" role="to"/>
          <tag k="type" v="restriction"/>
          <tag k="restriction" v="only_right_turn"/>
        </relation>""")
        def edge(wayid,start,end,graphid,index,points,mask=0):
            return {"way_id":int(wayid),"start_node":start,"end_node":end,
                "graph_id":graphid,"car_access":True,"local_index":index,
                "restriction_mask":mask,"complex":False,"start_restriction":0,
                "end_restriction":0,"access_restriction":0,
                "destination_only":False,"shape":points}
        inc=edge("42",800,900,101,0,[[53,-2],[53.0001,-2.0001]],4)
        intended=edge("43",900,901,102,1,[[53.0001,-2.0001],[53.0002,-2.0002]])
        other=edge("44",900,902,103,2,[[53.0001,-2.0001],[53.0003,-2.0003]])
        correct=assess_relation("fixture",relation,ways,nodes,[inc,intended,other])
        self.assertEqual(correct["verdict"],"PASS")
        self.assertEqual(len(correct["native_only_exit_completeness_evidence"]),2)
        broken=dict(inc,restriction_mask=0)
        wrong=assess_relation("fixture",relation,ways,nodes,[broken,intended,other])
        self.assertEqual(wrong["verdict"],"FAIL")
        self.assertTrue(any(not x["agrees"] for x in wrong["native_only_exit_completeness_evidence"]))
        incomplete=assess_relation("fixture",relation,ways,nodes,[inc,intended])
        self.assertEqual(incomplete["verdict"],"NOT_JUDGED_ONLY_MISSING_ALTERNATIVES")
        unknown_way=ET.fromstring("""<way id="44"><nd ref="2"/><nd ref="4"/>
          <tag k="highway" v="service"/></way>""")
        withheld=assess_relation("fixture",relation,{**ways,"44":unknown_way},
                                 nodes,[inc,intended,other])
        self.assertEqual(withheld["verdict"],"NOT_JUDGED_ONLY_OTHER_EXIT_ACCESS")

    def test_candidate_pair_index_bounds_fail_closed(self):
        way,nodes=fixture("residential")
        edges=[{"way_id":42,"shape":[[53,-2],[53.0001,-2.0001]],
                "graph_id":5,"start_node":12,"end_node":13,
                "restriction_mask":0,"local_index":10,"car_access":True}]
        self.assertEqual(candidate_pairs(rel(),edges,nodes),[])


if __name__=="__main__":
    unittest.main()
