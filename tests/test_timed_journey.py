from datetime import datetime,timezone,timedelta
import unittest
from engine.routing import RoadGraph,RoadEdge
from engine.reconciled import prepare_navigation
from engine.restrictions import Restriction,parse_conditional

def clock(s):return datetime.fromisoformat('2026-10-14T'+s).replace(tzinfo=timezone.utc)
def prepared(multi=False,unknown=False):
    edges=[RoadEdge('a','a','b',120,3.6,'unknown' if unknown else 'allowed'),
           RoadEdge('b','b','c',10,3.6,'allowed'),RoadEdge('d','b','d',20,3.6,'allowed'),
           RoadEdge('e','d','c',20,3.6,'allowed'),RoadEdge('f','c','t',10,3.6,'allowed')]
    seq=('a','b','f') if multi else ('a','b')
    g=RoadGraph('abcdt',edges,extended_restrictions=(Restriction('no',seq,parse_conditional('no_straight_on @ (Mo-Fr 07:00-10:00)')),))
    return prepare_navigation(g)

class TimedJourneyTests(unittest.TestCase):
    def test_partial_origin_estimated_arrival_selects_detour(self):
        p=prepared();j=p.journey('f',800000,timezone_name='UTC')
        s=j.start(p.position('a',500000),clock('06:59:30'))
        self.assertEqual(p.road_names(s.roads),('a','d','e','f'))
        self.assertEqual(s.cost,108000000)
    def test_same_road_delay_rechecks_new_arrival_time(self):
        p=prepared();j=p.journey('f',800000,timezone_name='UTC')
        before=j.start(p.position('a',500000),clock('06:58:00'))
        self.assertEqual(p.road_names(before.roads),('a','b','f'))
        later=j.observe(p.position('a',500000),clock('06:59:30'))
        self.assertEqual(p.road_names(later.roads),('a','d','e','f'))
        self.assertFalse(later.wrong_turn)
    def test_rule_ending_while_on_same_road_restores_short_route(self):
        p=prepared();j=p.journey('f',800000,timezone_name='UTC')
        before=j.start(p.position('a',500000),clock('09:58:00'))
        self.assertEqual(p.road_names(before.roads),('a','d','e','f'))
        after=j.observe(p.position('a',600000),clock('09:59:30'))
        self.assertEqual(p.road_names(after.roads),('a','b','f'))
    def test_wrong_turn_actual_history_retains_multi_road_ban(self):
        p=prepared(multi=True);j=p.journey('f',800000,timezone_name='UTC')
        before=j.start(p.position('a',500000),clock('07:30:00'))
        self.assertEqual(p.road_names(before.roads),('a','d','e','f'))
        wrong=j.observe(p.position('b',500000),clock('07:31:00'))
        self.assertTrue(wrong.wrong_turn)
        self.assertEqual(wrong.status,'no_route')
        self.assertEqual(wrong.roads,())
    def test_journey_from_partial_final_road_does_not_reject_actual_past_turn(self):
        p=prepared();j=p.journey('f',800000,timezone_name='UTC')
        s=j.start(p.position('b',500000),clock('07:30:00'),inbound=(p.edge_ids['a'],))
        self.assertEqual(p.road_names(s.roads),('b','f'))
    def test_restricted_destination_partway_along_road_is_not_a_bypass(self):
        p=prepared();j=p.journey('b',500000,timezone_name='UTC')
        s=j.start(p.position('a',500000),clock('07:30:00'))
        self.assertEqual(s.status,'no_route')
    def test_unknown_access_flag_and_arrival(self):
        p=prepared(unknown=True);j=p.journey('f',800000,timezone_name='UTC')
        s=j.start(p.position('a',500000),clock('07:30:00'))
        self.assertEqual(s.unverified_access_edges,('a',))
        j.observe(p.position('d',500000),clock('07:31:00'))
        j.observe(p.position('e',500000),clock('07:32:00'))
        j.observe(p.position('f',500000),clock('07:33:00'))
        arrived=j.observe(p.position('f',900000),clock('07:34:00'))
        self.assertEqual(arrived.status,'arrived');self.assertEqual(arrived.cost,0)
    def test_invalid_stale_discontinuous_observations_do_not_mutate_state(self):
        p=prepared();j=p.journey('f',800000,timezone_name='UTC')
        s=j.start(p.position('a',500000),clock('07:30:00'))
        for pos,t in [(p.position('a',500000),clock('07:30:00')),(p.position('a',400000),clock('07:31:00')),(p.position('f',400000),clock('07:31:00'))]:
            with self.assertRaises(ValueError):j.observe(pos,t)
            self.assertEqual(j.snapshot,s)
        with self.assertRaises(ValueError):j.observe(p.position('a',500000),datetime(2026,10,14,8))
        self.assertEqual(j.snapshot,s)
    def test_search_budget_failure_is_incomplete_not_no_route(self):
        p=prepared();j=p.journey('f',800000,timezone_name='UTC',max_states=1)
        s=j.start(p.position('a',500000),clock('07:30:00'))
        self.assertEqual(s.status,'incomplete');self.assertEqual(s.roads,());self.assertIsNone(s.cost)
    def test_timezone_is_required_and_static_journeys_still_use_numeric_clock(self):
        p=prepared()
        with self.assertRaises(ValueError):p.journey('f',800000)
        j=p.journey('f',800000,timezone_name='UTC')
        with self.assertRaises(ValueError):j.start(p.position('a',500000),1)
    def test_stationary_overlay_is_reused_but_clock_plan_is_not(self):
        p=prepared();j=p.journey('f',800000,timezone_name='UTC')
        first=j.start(p.position('a',500000),clock('06:58:00'))
        self.assertEqual(j._session._overlay_builds,1)
        later=j.observe(p.position('a',500000),clock('06:59:30'))
        self.assertEqual(j._session._overlay_builds,1)
        self.assertNotEqual(first.roads,later.roads)
    def test_no_route_recovers_when_clock_ban_ends(self):
        p=prepared();j=p.journey('b',500000,timezone_name='UTC')
        first=j.start(p.position('a',500000),clock('09:58:00'))
        self.assertEqual(first.status,'no_route')
        later=j.observe(p.position('a',500000),clock('09:59:30'))
        self.assertEqual(later.status,'navigating')
        self.assertEqual(p.road_names(later.roads),('a','b'))
    def test_compiled_window_expiry_clears_the_previous_plan(self):
        from dataclasses import replace
        p=replace(prepared(),timed_restrictions=(),validity_window=(clock('07:00:00'),clock('08:00:00')))
        j=p.journey('f',800000,timezone_name='UTC')
        first=j.start(p.position('a',500000),clock('07:30:00'))
        self.assertEqual(first.status,'navigating')
        later=j.observe(p.position('a',500000),clock('08:00:00'))
        self.assertEqual(later.status,'restriction_window_expired')
        self.assertEqual(later.roads,());self.assertIsNone(later.cost)
    def test_observation_during_incomplete_plan_does_not_invent_wrong_turn(self):
        p=prepared();j=p.journey('f',800000,timezone_name='UTC',max_states=1)
        first=j.start(p.position('a',500000),clock('07:30:00'))
        self.assertEqual(first.status,'incomplete')
        next_=j.observe(p.position('d',500000),clock('07:31:00'))
        self.assertFalse(next_.wrong_turn)
    def test_partial_positions_and_delays_match_independent_oracle(self):
        # Acyclic fixture has exactly two destination paths. Calculate their
        # costs and junction clocks directly, without endpoint/router helpers.
        cases=0
        for fraction in (0,250000,500000,750000,1000000):
            remaining=120*(1000000-fraction)/1000000
            for start in ('06:57:30','06:59:00','07:00:00','09:58:30','09:59:50','10:00:00'):
                p=prepared();j=p.journey('f',800000,timezone_name='UTC')
                t=clock(start)
                for iteration in range(2):
                    now=t+timedelta(seconds=30*iteration)
                    s=j.start(p.position('a',fraction),now) if iteration==0 else j.observe(p.position('a',fraction),now)
                    arrival=now+timedelta(seconds=remaining)
                    restricted=clock('07:00:00')<=arrival<clock('10:00:00')
                    expected=(('a',) if remaining else ())+(('d','e','f') if restricted else ('b','f'))
                    self.assertEqual(p.road_names(s.roads),expected)
                    self.assertEqual(s.cost,round((remaining+(40 if restricted else 10)+8)*1000000))
                    cases+=1
        self.assertEqual(cases,60)
    def test_imported_conditional_clock_and_compiled_window_journey(self):
        from map_data.osm_xml import import_osm_xml,Provenance
        raw=b'''<osm><node id="1" lat="0" lon="0"/><node id="2" lat="0" lon=".001"/>
        <node id="3" lat="0" lon=".002"/><node id="4" lat=".001" lon=".001"/>
        <way id="10"><nd ref="1"/><nd ref="2"/><tag k="highway" v="residential"/><tag k="oneway" v="yes"/></way>
        <way id="20"><nd ref="2"/><nd ref="3"/><tag k="highway" v="residential"/><tag k="oneway" v="yes"/></way>
        <way id="30"><nd ref="2"/><nd ref="4"/><nd ref="3"/><tag k="highway" v="residential"/><tag k="oneway" v="yes"/></way>
        <relation id="100"><member type="way" ref="10" role="from"/><member type="node" ref="2" role="via"/><member type="way" ref="20" role="to"/><tag k="type" v="restriction"/><tag k="restriction:conditional" v="no_straight_on @ (Mo-Fr 07:00-10:00)"/></relation></osm>'''
        prov=Provenance('synthetic','v2','authored','OpenStreetMap contributors')
        for kw in ({},{'window':(clock('07:00:00'),clock('08:00:00')),'timezone_name':'UTC'}):
            m=import_osm_xml(raw,provenance=prov,**kw);p=prepare_navigation(m.graph,m.coordinates)
            j=p.journey('w:20:0:f',500000,timezone_name='UTC')
            s=j.start(p.position('w:10:0:f',500000),clock('07:30:00'))
            self.assertEqual(s.status,'no_route')
    def test_datetime_offset_order_uses_utc_not_local_wall_clock(self):
        from zoneinfo import ZoneInfo
        p=prepared();j=p.journey('f',800000,timezone_name='Europe/London')
        a=datetime(2026,10,25,1,30,tzinfo=ZoneInfo('Europe/London'),fold=0)
        b=datetime(2026,10,25,1,15,tzinfo=ZoneInfo('Europe/London'),fold=1)
        first=j.start(p.position('a',500000),a)
        later=j.observe(p.position('a',500000),b)
        self.assertGreater(later.timestamp,first.timestamp)
    def test_already_on_destination_road_can_complete_without_a_future_turn(self):
        p=prepared();j=p.journey('b',500000,timezone_name='UTC')
        s=j.start(p.position('b',500000),clock('07:30:00'),inbound=(p.edge_ids['a'],))
        self.assertEqual(s.status,'arrived');self.assertEqual(s.cost,0)
