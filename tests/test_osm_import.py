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
        # The unconditional ban applies at all times (conditional never relaxes it).
        restricted = imported(raw.encode())
        self.assertEqual(restricted.graph.prohibited_turns, imported().graph.prohibited_turns)
        way = FIXTURE.read_text().replace('<tag k="oneway" v="yes"/>',
            '<tag k="oneway" v="yes"/><tag k="oneway:conditional" v="no @ (Su)"/>')
        # A conditional lifting of a one-way never opens the reverse direction.
        self.assertEqual(set(imported(way.encode()).graph.edges), set(imported().graph.edges))

    def test_via_way_restrictions_fail_closed(self):
        raw = FIXTURE.read_text().replace('<member type="node" ref="2" role="via"/>',
            '<member type="way" ref="102" role="via"/>')
        # Owner-approved (17 Oct 2026): still fail closed, but per relation, not for the
        # whole map: every move from the from-way into the via way is banned.
        m = imported(raw.encode())
        self.assertEqual(m.metadata["restrictions_not_applied"], {"disconnected_via_way_blocked": 1})
        self.assertIn(("w:100:0:f", "w:102:0:f"), m.graph.prohibited_turns)
        self.assertIn(("w:100:0:f", "w:101:0:f"), m.graph.prohibited_turns)

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
        self.assertIn("no-real-world-legality-claims", imported().metadata["limitations"])


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
        for value, expected in [('mystery','unknown'),('private','unknown'),
                                ('destination','unknown'),('customers','unknown')]:
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

    def test_directional_condition_never_broadens_access(self):
        # A conditional that only grants access is not evaluated: the stricter
        # unconditional value governs, so the conditional changes nothing.
        base=self.graph()
        granted=self.graph(self.tag('vehicle:backward:conditional','yes @ (Mo)'))
        self.assertEqual({k:e.access for k,e in base.edges.items()},{k:e.access for k,e in granted.edges.items()})
        denied=self.graph(self.tag('vehicle:backward:conditional','no @ (Mo)'))
        self.assertTrue(all(e.access!='allowed' for k,e in denied.edges.items() if k.endswith(':r')))

class ContextualAccessRegression(unittest.TestCase):
    def raw(self, value, key='access'):
        return (f'<osm><node id="1" lat="53" lon="-2"/>'
                f'<node id="2" lat="53.001" lon="-2"/>'
                f'<node id="3" lat="53.002" lon="-2"/>'
                f'<way id="11"><nd ref="1"/><nd ref="2"/>'
                f'<tag k="highway" v="residential"/><tag k="{key}" v="{value}"/>'
                f'</way></osm>').encode()

    def context(self, raw, **kw):
        from map_data import JourneyAccessContext
        return JourneyAccessContext(hashlib.sha256(raw).hexdigest(), **kw)

    def test_contextual_without_evidence_is_unknown_not_illegal(self):
        for value in ('private','destination','delivery','customers','permit','agricultural','forestry'):
            with self.subTest(value=value):
                self.assertEqual(imported(self.raw(value)).graph.edges['w:11:0:f'].access,'unknown')

    def test_private_requires_exact_way_authorization_and_keeps_base_unchanged(self):
        raw=self.raw('private');base=imported(raw)
        ctx=self.context(raw,authorized_way_ids=frozenset({'11'}))
        m=import_osm_xml(raw,provenance=PROV,access_context=ctx)
        self.assertEqual(m.graph.edges['w:11:0:f'].access,'allowed')
        self.assertEqual(base.graph.edges['w:11:0:f'].access,'unknown')
        self.assertEqual(shortest_route(m.graph,'osm:1','osm:2').edge_ids,('w:11:0:f',))
        self.assertIn('way:11:private',m.access_requirements['w:11:0:f'])

    def test_destination_access_requires_destination_on_that_way(self):
        raw=self.raw('destination')
        for target, expected in [('osm:2','allowed'),('osm:3','unknown')]:
            with self.subTest(target=target):
                m=import_osm_xml(raw,provenance=PROV,access_context=self.context(raw,destination_node=target,destination_way_ids=frozenset({'11'}) if target=='osm:2' else frozenset()))
                self.assertEqual(m.graph.edges['w:11:0:f'].access,expected)

    def test_destination_context_cannot_be_reused_for_another_target(self):
        raw=self.raw('destination')
        m=import_osm_xml(raw,provenance=PROV,access_context=self.context(raw,destination_node='osm:2',destination_way_ids=frozenset({'11'})))
        with self.assertRaises(ValueError):shortest_route(m.graph,'osm:2','osm:1')

    def test_permission_does_not_override_hard_directional_no(self):
        raw=self.raw('private').replace(b'</way>',b'<tag k="vehicle:backward" v="no"/></way>')
        m=import_osm_xml(raw,provenance=PROV,access_context=self.context(raw,authorized_way_ids=frozenset({'11'})))
        self.assertEqual(m.graph.edges['w:11:0:r'].access,'prohibited')
        self.assertEqual(m.graph.edges['w:11:0:f'].access,'allowed')

    def test_destination_qualification_is_not_private_authorization(self):
        raw=self.raw('private')
        m=import_osm_xml(raw,provenance=PROV,access_context=self.context(raw,destination_node='osm:2',destination_way_ids=frozenset({'11'})))
        self.assertEqual(m.graph.edges['w:11:0:f'].access,'unknown')

    def test_authorization_is_not_a_qualifying_destination(self):
        raw=self.raw('destination')
        m=import_osm_xml(raw,provenance=PROV,access_context=self.context(raw,authorized_way_ids=frozenset({'11'})))
        self.assertEqual(m.graph.edges['w:11:0:f'].access,'unknown')

    def test_context_is_snapshot_bound_and_immutable(self):
        raw=self.raw('private');ctx=self.context(raw,authorized_way_ids=frozenset({'11'}))
        with self.assertRaises(OSMImportError):import_osm_xml(raw+b' ',provenance=PROV,access_context=ctx)
        from dataclasses import FrozenInstanceError
        with self.assertRaises(FrozenInstanceError):ctx.authorized_way_ids=frozenset()

    def test_unknown_service_is_not_opened_by_unrelated_permission(self):
        raw=self.raw('yes','bus').replace(b'v="residential"',b'v="service"')
        m=import_osm_xml(raw,provenance=PROV,access_context=self.context(raw,authorized_way_ids=frozenset({'11'})))
        self.assertEqual(m.graph.edges['w:11:0:f'].access,'unknown')

    def test_other_routers_enforce_destination_binding(self):
        from engine.astar import astar_route
        from engine.route_alternatives import generate_route_candidates
        from engine.driver_policy import DriverNavigationSettings
        raw=self.raw('destination')
        m=import_osm_xml(raw,provenance=PROV,access_context=self.context(raw,destination_node='osm:2',destination_way_ids=frozenset({'11'})))
        with self.assertRaises(ValueError):astar_route(m.graph,'osm:2','osm:1')
        with self.assertRaises(ValueError):generate_route_candidates(m.graph,'osm:2','osm:1',settings=DriverNavigationSettings(),snapshot_id='context-fixture')

    def test_context_does_not_open_physical_barriers_or_other_private_nodes(self):
        raw=self.raw('private').replace(b'<node id="1" lat="53" lon="-2"/>',
            b'<node id="1" lat="53" lon="-2"><tag k="barrier" v="gate"/><tag k="access" v="private"/></node>')
        ctx=self.context(raw,authorized_way_ids=frozenset({'11'}))
        self.assertEqual(import_osm_xml(raw,provenance=PROV,access_context=ctx).graph.edges['w:11:0:f'].access,'unknown')
        ctx=self.context(raw,authorized_way_ids=frozenset({'11'}),authorized_node_ids=frozenset({'1'}))
        self.assertEqual(import_osm_xml(raw,provenance=PROV,access_context=ctx).graph.edges['w:11:0:f'].access,'allowed')
        blocked=raw.replace(b'v="gate"',b'v="bollard"')
        ctx=self.context(blocked,authorized_way_ids=frozenset({'11'}),authorized_node_ids=frozenset({'1'}))
        self.assertNotEqual(import_osm_xml(blocked,provenance=PROV,access_context=ctx).graph.edges['w:11:0:f'].access,'allowed')

    def test_higher_mode_permission_does_not_retain_overridden_requirement(self):
        raw=self.raw('private').replace(b'</way>',b'<tag k="motorcar" v="yes"/></way>')
        m=imported(raw)
        self.assertEqual(m.graph.edges['w:11:0:f'].access,'allowed')
        self.assertNotIn('w:11:0:f',m.access_requirements)

    def test_invalid_context_fields_rejected(self):
        from map_data import JourneyAccessContext
        for args in [{'authorized_way_ids':{'11'}},{'destination_node':'11'},
                     {'authorized_node_ids':frozenset({'abc'})}]:
            with self.subTest(args=args),self.assertRaises(OSMImportError):
                JourneyAccessContext('0'*64,**args)
        raw=self.raw('private')
        with self.assertRaises(OSMImportError):
            import_osm_xml(raw,provenance=PROV,access_context=self.context(raw,authorized_way_ids=frozenset({'99'})))

    def test_offline_journey_permission_does_not_leak_into_active_map(self):
        from map_data.offline import OfflineMapStore
        raw=self.raw('private');h=hashlib.sha256(raw).hexdigest()
        manifest={'schema_version':1,'format':'dmn-osm-xml-v1','byte_length':len(raw),
                  'sha256':h,'provenance':dict(region=PROV.region,snapshot=PROV.snapshot,
                    source=PROV.source,attribution=PROV.attribution),'required_nodes':['osm:1','osm:2']}
        store=OfflineMapStore();store.activate(raw,manifest)
        with self.assertRaises(RouteNotFound):store.route('osm:1','osm:2')
        r=store.route('osm:1','osm:2',access_context=self.context(raw,authorized_way_ids=frozenset({'11'})))
        self.assertEqual(r.package_sha256,h)
        with self.assertRaises(RouteNotFound):store.route('osm:1','osm:2')

    def test_coordinate_membership_does_not_infer_qualifying_purpose(self):
        raw=self.raw('destination')
        m=import_osm_xml(raw,provenance=PROV,access_context=self.context(raw,destination_node='osm:2'))
        self.assertEqual(m.graph.edges['w:11:0:f'].access,'unknown')
        with self.assertRaises(OSMImportError):
            import_osm_xml(raw,provenance=PROV,access_context=self.context(
                raw,destination_node='osm:3',destination_way_ids=frozenset({'11'})))

    def test_private_grant_does_not_bypass_turn_prohibition(self):
        import xml.etree.ElementTree as ET
        root=ET.fromstring(FIXTURE.read_bytes())
        way=next(w for w in root.findall('way') if w.get('id')=='101')
        ET.SubElement(way,'tag',k='access',v='private');raw=ET.tostring(root)
        ctx=self.context(raw,authorized_way_ids=frozenset({'101'}))
        m=import_osm_xml(raw,provenance=PROV,access_context=ctx)
        self.assertEqual(m.graph.edges['w:101:0:f'].access,'allowed')
        self.assertIn(('w:100:0:f','w:101:0:f'),m.graph.prohibited_turns)

    def test_destination_does_not_create_wrong_way_edges(self):
        raw=self.raw('destination').replace(b'</way>',b'<tag k="oneway" v="yes"/></way>')
        m=import_osm_xml(raw,provenance=PROV,access_context=self.context(
            raw,destination_node='osm:2',destination_way_ids=frozenset({'11'})))
        self.assertEqual(m.graph.edges['w:11:0:f'].access,'allowed')
        self.assertNotIn('w:11:0:r',m.graph.edges)

    def test_grant_never_evaluates_unsupported_time_conditions(self):
        # A time-conditional denial is never overridden by a caller permission:
        # the way stays unroutable (withheld), whatever the clock.
        raw=self.raw('private').replace(b'</way>',b'<tag k="access:conditional" v="no @ (Mo)"/></way>')
        graph=import_osm_xml(raw,provenance=PROV,access_context=self.context(raw,authorized_way_ids=frozenset({'11'}))).graph
        way=[e for k,e in graph.edges.items() if k.split(':')[1]=='11']
        self.assertTrue(way)
        self.assertTrue(all(e.access!='allowed' for e in way))

    def test_authorization_for_another_way_is_not_global(self):
        raw=self.raw('private').replace(b'</osm>',b'<way id="12"><nd ref="1"/><nd ref="3"/><tag k="highway" v="residential"/></way></osm>')
        m=import_osm_xml(raw,provenance=PROV,access_context=self.context(raw,authorized_way_ids=frozenset({'12'})))
        self.assertEqual(m.graph.edges['w:11:0:f'].access,'unknown')
