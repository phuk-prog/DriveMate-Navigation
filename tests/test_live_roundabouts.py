import unittest
from datetime import datetime,timezone
from engine.routing import RoadGraph,RoadEdge
from engine.reconciled import prepare_navigation
from engine.restrictions import Restriction,parse_conditional

def network(unknown=False,timed=False,blocked=False):
    edges=[RoadEdge('entry','s','0',100,36,'unknown' if unknown else 'allowed')]
    for i in range(4):
        edges.append(RoadEdge('r'+str(i),str(i),str((i+1)%4),100,36,'allowed',junction='roundabout'))
        edges.append(RoadEdge('x'+str(i),str(i),'t'+str(i),100,36,'prohibited' if blocked and i==1 else 'allowed'))
    rules=(Restriction('no',('r0','x1'),parse_conditional('no_right_turn @ (Mo-Fr 07:00-10:00)')),) if timed else ()
    return prepare_navigation(RoadGraph(['s']+[str(i) for i in range(4)]+['t'+str(i) for i in range(4)],edges,extended_restrictions=rules))
def clock(h,m,s=0):return datetime(2026,10,14,h,m,s,tzinfo=timezone.utc)

class LiveRoundaboutTests(unittest.TestCase):
    def test_original_third_exit_remains_third_during_partial_progress(self):
        p=network();j=p.journey('x3',800000)
        j.start(p.position('entry',500000),1)
        self.assertEqual(j.roundabouts()[0].exit_number,3)
        j.observe(p.position('r0',250000),2)
        self.assertEqual(j.roundabouts()[0].exit_number,3)
        j.observe(p.position('r1',250000),3)
        self.assertEqual(j.roundabouts()[0].exit_number,3)
        j.observe(p.position('r2',250000),4)
        self.assertEqual(j.roundabouts()[0].exit_number,3)
        j.observe(p.position('x3',250000),5)
        self.assertEqual(j.roundabouts(),())
    def test_missed_exit_reroutes_with_original_entry_and_counts_extra_lap(self):
        p=network();j=p.journey('x2',800000)
        j.start(p.position('entry',500000),1)
        j.observe(p.position('r0',500000),2)
        j.observe(p.position('r1',500000),3)
        self.assertEqual(j.roundabouts()[0].exit_number,2)
        wrong=j.observe(p.position('r2',500000),4)
        self.assertTrue(wrong.wrong_turn)
        self.assertEqual(j.roundabouts()[0].status,'repeated_circulation')
        self.assertIsNone(j.roundabouts()[0].exit_number)
    def test_start_inside_does_not_invent_an_entry(self):
        p=network();j=p.journey('x3',800000)
        j.start(p.position('r1',500000),1)
        self.assertEqual(j.roundabouts()[0].status,'started_inside')
        self.assertIsNone(j.roundabouts()[0].exit_number)
    def test_explicit_inbound_entry_is_retained(self):
        p=network();j=p.journey('x3',800000)
        j.start(p.position('r0',500000),1,inbound=(p.edge_ids['entry'],))
        self.assertEqual(j.roundabouts()[0].exit_number,3)
    def test_unknown_access_does_not_close_road_or_invent_verified_guidance(self):
        p=network(unknown=True);j=p.journey('x3',800000)
        s=j.start(p.position('entry',500000),1)
        self.assertEqual(s.status,'navigating');self.assertIn('entry',s.unverified_access_edges)
        self.assertEqual(j.roundabouts()[0].status,'unverified_access')
        j.observe(p.position('r0',500000),2)
        self.assertEqual(j.snapshot.status,'navigating');self.assertEqual(j.roundabouts()[0].status,'unverified_access')
    def test_partial_cost_does_not_apply_clock_ban_too_early(self):
        p=network(timed=True);j=p.journey('x3',800000,timezone_name='UTC')
        j.start(p.position('r0',900000),clock(6,59,58),inbound=(p.edge_ids['entry'],))
        self.assertEqual(j.roundabouts()[0].exit_number,3)
        # Only one second remains on r0. A full-road timing bug would arrive
        # after the ban starts, wrongly renumbering the planned exit.
    def test_passed_timed_exit_uses_observed_crossing_not_current_clock(self):
        p=network(timed=True);j=p.journey('x3',800000,timezone_name='UTC')
        j.start(p.position('r0',900000),clock(6,59,58),inbound=(p.edge_ids['entry'],))
        j.observe(p.position('r1',0),clock(6,59,59))
        self.assertEqual(j.roundabouts()[0].exit_number,3)
        j.observe(p.position('r1',500000),clock(7,0,10))
        self.assertEqual(j.roundabouts()[0].exit_number,3)
    def test_uncertain_crossing_time_withholds_number_but_keeps_route(self):
        p=network(timed=True);j=p.journey('x3',800000,timezone_name='UTC')
        j.start(p.position('r0',500000),clock(6,59,58),inbound=(p.edge_ids['entry'],))
        s=j.observe(p.position('r1',500000),clock(7,0,5))
        self.assertEqual(s.status,'navigating')
        self.assertEqual(j.roundabouts()[0].status,'uncertain_crossing_time')
        self.assertIsNone(j.roundabouts()[0].exit_number)
    def test_at_road_end_repeated_wait_does_not_double_count(self):
        p=network();j=p.journey('x3',800000)
        j.start(p.position('entry',1000000),1)
        j.observe(p.position('r0',1000000),2)
        self.assertEqual(j.roundabouts()[0].exit_number,3)
        j.observe(p.position('r0',1000000),3)
        self.assertEqual(j.roundabouts()[0].exit_number,3)
        j.observe(p.position('r1',0),4)
        self.assertEqual(j.roundabouts()[0].exit_number,3)
    def test_stale_and_disconnected_observations_leave_context_unchanged(self):
        p=network();j=p.journey('x3',800000)
        j.start(p.position('entry',500000),1);j.observe(p.position('r0',500000),2)
        before=j.roundabouts()
        for pos,t in [(p.position('r0',750000),2),(p.position('r2',500000),3)]:
            with self.assertRaises(ValueError):j.observe(pos,t)
            self.assertEqual(j.roundabouts(),before)
    def test_known_oneway_and_access_bans_stay_enforced(self):
        p=network(blocked=True)
        with self.assertRaises(ValueError):p.position('reverse_r0',500000)
        j=p.journey('x1',800000)
        self.assertEqual(j.start(p.position('entry',500000),1).status,'no_route')
        self.assertEqual(j.roundabouts(),())
        # Ring has no recorded lanes, yet remains routable in its legal direction.
        j=p.journey('x3',800000);s=j.start(p.position('entry',500000),1)
        self.assertEqual(s.status,'navigating');self.assertEqual(j.roundabouts()[0].exit_number,2)
    def test_imported_unverified_lanes_and_access_do_not_relax_oneway(self):
        from map_data.osm_xml import import_osm_xml,Provenance
        from engine.routing import RouteNotFound
        raw=b'''<osm><node id="1" lat="0" lon="0"/><node id="2" lat="0" lon=".001"/>
        <way id="10"><nd ref="1"/><nd ref="2"/><tag k="highway" v="service"/><tag k="oneway" v="yes"/>
        <tag k="turn:lanes:conditional" v="unconfirmed lane hint"/></way></osm>'''
        m=import_osm_xml(raw,provenance=Provenance('synthetic','v1','authored','OpenStreetMap contributors'))
        p=prepare_navigation(m.graph,m.coordinates)
        for backend in ('research','portable'):
            r=p.route('osm:1','osm:2',backend=backend)
            self.assertEqual(r.edge_ids,('w:10:0:f',));self.assertEqual(r.unverified_access_edges,('w:10:0:f',))
            with self.assertRaises(RouteNotFound):p.route('osm:2','osm:1',backend=backend)
        self.assertEqual(m.metadata['unverified_lane_ways'],1)
    def test_lane_hint_is_not_a_bypass_for_confirmed_access_ban(self):
        from map_data.osm_xml import import_osm_xml,Provenance
        from engine.routing import RouteNotFound
        raw=b'''<osm><node id="1" lat="0" lon="0"/><node id="2" lat="0" lon=".001"/>
        <way id="10"><nd ref="1"/><nd ref="2"/><tag k="highway" v="service"/><tag k="motorcar" v="no"/>
        <tag k="turn:lanes:conditional" v="unconfirmed lane hint"/></way></osm>'''
        m=import_osm_xml(raw,provenance=Provenance('synthetic','v1','authored','OpenStreetMap contributors'));p=prepare_navigation(m.graph,m.coordinates)
        for backend in ('research','portable'):
            with self.assertRaises(RouteNotFound):p.route('osm:1','osm:2',backend=backend)
    def test_explicit_static_entry_history_preserves_already_passed_exit(self):
        p=network();j=p.journey('x3',800000)
        j.start(p.position('r1',500000),1,inbound=(p.edge_ids['entry'],p.edge_ids['r0']))
        self.assertEqual(j.roundabouts()[0].exit_number,3)
    def test_unknown_ring_access_remains_visible_after_passing_that_road(self):
        from dataclasses import replace
        p=network();edges=[replace(e,access='unknown') if name=='r0' else e for name,e in p.source_edges.items()]
        p=prepare_navigation(RoadGraph(p.node_ids.keys(),edges));j=p.journey('x3',800000)
        j.start(p.position('entry',500000),1);j.observe(p.position('r0',500000),2);j.observe(p.position('r1',500000),3)
        self.assertEqual(j.snapshot.status,'navigating')
        self.assertEqual(j.roundabouts()[0].status,'unverified_access')
        self.assertIn('r0',j.roundabouts()[0].unverified_edges)
    def test_next_roundabout_gets_its_own_entry_context(self):
        p=network(unknown=True)
        edges=[e for name,e in p.source_edges.items() if name!='x2']
        edges.append(RoadEdge('join','2','b0',100,36,'allowed'))
        vertices=list(p.node_ids)+['b'+str(i) for i in range(4)]+['bt'+str(i) for i in range(4)]
        for i in range(4):
            edges.append(RoadEdge('br'+str(i),'b'+str(i),'b'+str((i+1)%4),100,36,'allowed',junction='roundabout'))
            edges.append(RoadEdge('bx'+str(i),'b'+str(i),'bt'+str(i),100,36,'allowed'))
        p=prepare_navigation(RoadGraph(vertices,edges));j=p.journey('bx2',800000)
        j.start(p.position('entry',500000),1)
        initial=j.roundabouts()
        self.assertEqual(initial[0].status,'unverified_access');self.assertEqual(initial[1].exit_number,2)
        for road,t in [('r0',2),('r1',3),('join',4),('br0',5),('br1',6)]:j.observe(p.position(road,500000),t)
        self.assertEqual(j.roundabouts()[0].entry_road,'join')
        self.assertEqual(j.roundabouts()[0].exit_number,2)
        self.assertEqual(j.roundabouts()[0].unverified_edges,())
    def test_no_guidance_before_start_or_after_arrival(self):
        p=network();j=p.journey('x1',800000)
        self.assertEqual(j.roundabouts(),())
        j.start(p.position('entry',500000),1);j.observe(p.position('r0',500000),2)
        j.observe(p.position('x1',900000),3)
        self.assertEqual(j.snapshot.status,'arrived');self.assertEqual(j.roundabouts(),())
    def test_old_explicit_timed_history_does_not_invent_historical_crossing_times(self):
        p=network(timed=True);j=p.journey('x3',800000,timezone_name='UTC')
        j.start(p.position('r1',500000),clock(7,0,5),inbound=(p.edge_ids['entry'],p.edge_ids['r0']))
        self.assertEqual(j.snapshot.status,'navigating')
        self.assertEqual(j.roundabouts()[0].status,'uncertain_crossing_time')
    def test_optional_lane_hints_do_not_hide_unsupported_oneway_conditions(self):
        from map_data.osm_xml import import_osm_xml,Provenance,OSMImportError
        raw=b'''<osm><node id="1" lat="0" lon="0"/><node id="2" lat="0" lon=".001"/>
        <way id="10"><nd ref="1"/><nd ref="2"/><tag k="highway" v="residential"/>
        <tag k="turn:lanes:conditional" v="unverified"/><tag k="oneway:conditional" v="yes @ (Mo-Fr 07:00-10:00)"/></way></osm>'''
        with self.assertRaises(OSMImportError):import_osm_xml(raw,provenance=Provenance('synthetic','v1','authored','OpenStreetMap contributors'))
    def test_guidance_and_same_road_static_updates_do_not_launch_extra_route_jobs(self):
        from unittest.mock import patch
        from navigation_core.native_adapter import run
        p=network()
        with patch('navigation_core.journey.run',wraps=run) as route_jobs:
            j=p.journey('x3',800000);j.start(p.position('entry',500000),1)
            for _ in range(4):self.assertEqual(j.roundabouts()[0].exit_number,3)
            j.observe(p.position('entry',750000),2)
            for _ in range(4):self.assertEqual(j.roundabouts()[0].exit_number,3)
            self.assertEqual(route_jobs.call_count,1)
