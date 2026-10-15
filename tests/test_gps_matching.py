"""Original synthetic coordinates; no user/device driving data."""
import unittest
from dataclasses import replace
from datetime import datetime,timezone
from math import degrees
from unittest.mock import patch
from engine.routing import RoadEdge,RoadGraph
from engine.reconciled import prepare_navigation,Restriction
from engine.restrictions import Restriction as TimedRestriction,parse_conditional
from gps.matching import EARTH,Fix,Matcher,GpsJourney

UNIT=degrees(1/EARTH)
def fix(x,y,t=1,accuracy=2,heading=90,speed=10,heading_accuracy=5):
    return Fix(y*UNIT,x*UNIT,t,accuracy,speed,heading,heading_accuracy if heading is not None else None)
def network(extra=(),turns=(),rules=(),access='allowed',coords_extra=None,timed=(),window=None):
    coords={'a':(0,0),'b':(0,100*UNIT),'c':(0,200*UNIT),'n':(100*UNIT,100*UNIT),'e':(100*UNIT,200*UNIT)}
    coords.update(coords_extra or {})
    roads=[RoadEdge('ab','a','b',100,36,access),RoadEdge('bc','b','c',100,36,'allowed'),
           RoadEdge('bn','b','n',100,36,'allowed'),RoadEdge('ne','n','e',100,36,'allowed')]+list(extra)
    return prepare_navigation(RoadGraph(coords,roads,turns,multi_restrictions=rules,extended_restrictions=timed,validity_window=window),coords)

class GpsMatchingTests(unittest.TestCase):
    def test_projects_directed_fraction_and_preserves_quality(self):
        m=Matcher(network()).observe(fix(25,2),1.5)
        self.assertEqual(m.status,'matched');self.assertEqual(m.road,'ab')
        self.assertAlmostEqual(m.position.fraction,250000,delta=1)
        self.assertAlmostEqual(m.distance_m,2,places=5)
        self.assertEqual((m.accuracy_m,m.age_s,m.speed_mps,m.bearing_accuracy_degrees),(2,.5,10,5))
    def test_projection_clips_at_endpoint(self):
        m=Matcher(network()).observe(fix(-2,0),1)
        self.assertEqual(m.position.fraction,0)
    def test_missing_geometry_is_explicit_not_fake_zero_coordinates(self):
        p=prepare_navigation(RoadGraph('ab',[RoadEdge('ab','a','b',10,36)]))
        with self.assertRaisesRegex(ValueError,'geometry'):Matcher(p)
    def test_degenerate_and_long_geometry_rejected(self):
        for end in ((0,0),(0,3000*UNIT)):
            p=prepare_navigation(RoadGraph('ab',[RoadEdge('ab','a','b',10,36)]),{'a':(0,0),'b':end})
            with self.assertRaises(ValueError):Matcher(p)
    def test_polar_and_large_region_rejected(self):
        for a,b in [((81,0),(81,.001)),((0,0),(0,30000*UNIT))]:
            p=prepare_navigation(RoadGraph('ab',[RoadEdge('ab','a','b',10,36)]),{'a':a,'b':b})
            with self.assertRaises(ValueError):Matcher(p)
    def test_wrapped_longitude_short_segment(self):
        p=prepare_navigation(RoadGraph('ab',[RoadEdge('ab','a','b',100,36,'allowed')]),{'a':(0,179.999),'b':(0,-179.999)})
        m=Matcher(p).observe(Fix(0,180,1,2,10,90,5),1)
        self.assertEqual(m.status,'matched');self.assertAlmostEqual(m.position.fraction,500000,delta=2)
    def test_stale_future_poor_and_impossible_speed_do_not_change_match(self):
        m=Matcher(network());first=m.observe(fix(20,0),1)
        for f,now,status in [(fix(30,0,2),6,'stale_fix'),(fix(30,0,2),1,'future_fix'),
                             (fix(30,0,2,accuracy=100),2,'poor_accuracy'),(fix(30,0,2,speed=81),2,'impossible_speed')]:
            self.assertEqual(m.observe(f,now).status,status);self.assertIs(m.last,first)
    def test_out_of_order_and_duplicate_do_not_mutate(self):
        m=Matcher(network());first=m.observe(fix(20,0,5),5)
        for t in (4,5):
            self.assertEqual(m.observe(fix(25,0,t),5).status,'out_of_order');self.assertIs(m.last,first)
    def test_invalid_fix_values_and_receipt_time(self):
        for changes in [{'latitude':float('nan')},{'longitude':181},{'accuracy_m':0},{'timestamp':True},
                        {'speed_mps':-1},{'bearing_degrees':360},{'bearing_accuracy_degrees':181},
                        {'bearing_degrees':None,'bearing_accuracy_degrees':5}]:
            with self.assertRaises(ValueError):replace(fix(0,0),**changes)
        with self.assertRaises(ValueError):Matcher(network()).observe(fix(0,0),float('inf'))
    def test_off_map_does_not_advance_progress(self):
        m=Matcher(network());first=m.observe(fix(20,0),1)
        self.assertEqual(m.observe(fix(20,-100,3),3).status,'off_map');self.assertIs(m.last,first)
    def test_outside_region_fix_is_explicit(self):
        self.assertEqual(Matcher(network()).observe(fix(40000,0),1).status,'outside_supported_region')
    def test_one_way_heading_against_travel_rejected(self):
        self.assertEqual(Matcher(network()).observe(fix(20,0,heading=270),1).status,'direction_mismatch')
    def test_bidirectional_heading_selects_correct_directed_road(self):
        p=network(extra=(RoadEdge('ba','b','a',100,36,'allowed'),))
        for heading,road in [(90,'ab'),(270,'ba')]:
            self.assertEqual(Matcher(p).observe(fix(25,0,heading=heading),1).road,road)
    def test_unreliable_low_speed_bearing_cannot_break_initial_ambiguity(self):
        p=network(extra=(RoadEdge('ba','b','a',100,36,'allowed'),))
        for speed,uncertainty in [(0,5),(10,60)]:
            self.assertEqual(Matcher(p).observe(fix(25,0,speed=speed,heading_accuracy=uncertainty),1).status,'ambiguous')
    def test_unknown_access_and_missing_lanes_do_not_block(self):
        p=network(access='unknown');m=Matcher(p).observe(fix(20,0),1)
        self.assertEqual(m.status,'matched');self.assertTrue(m.unverified_access)
        self.assertEqual(p.route('a','c').edge_ids,('ab','bc'))
    def test_prohibited_road_not_snapped_to_an_alternative(self):
        m=Matcher(network(access='prohibited')).observe(fix(20,0),1)
        self.assertEqual(m.status,'prohibited_road');self.assertIsNone(m.position)
    def test_turn_ban_preserved_and_rejection_keeps_history(self):
        m=Matcher(network(turns=(('ab','bn'),)));first=m.observe(fix(90,0),1)
        self.assertEqual(m.observe(fix(100,10,2,heading=0),2).status,'prohibited_turn')
        self.assertIs(m.last,first);self.assertEqual(m.history,())
    def test_only_turn_rule_preserved(self):
        m=Matcher(network(rules=(Restriction('only',('ab','bn')),)))
        m.observe(fix(90,0),1)
        self.assertEqual(m.observe(fix(110,0,2),2).status,'prohibited_turn')
    def test_multi_road_restriction_history_retained(self):
        m=Matcher(network(rules=(Restriction('no',('ab','bn','ne')),)))
        m.observe(fix(90,0),1);self.assertEqual(m.observe(fix(100,90,3,heading=0),3).status,'matched')
        self.assertEqual(m.observe(fix(110,100,5),5).status,'prohibited_turn')
    def test_legal_adjacent_turn(self):
        m=Matcher(network());m.observe(fix(90,0),1)
        s=m.observe(fix(100,20,3,heading=0),3)
        self.assertEqual((s.status,s.road,m.history),('matched','bn',('ab',)))
    def test_collinear_endpoint_hysteresis_then_transition(self):
        m=Matcher(network());m.observe(fix(90,0),1)
        self.assertEqual(m.observe(fix(100,0,2),2).road,'ab')
        self.assertEqual(m.observe(fix(106,0,3),3).road,'bc')
    def test_small_backward_jitter_clamps_and_large_backwards_rejected(self):
        m=Matcher(network());first=m.observe(fix(50,0),1)
        s=m.observe(fix(48,0,2),2)
        self.assertEqual(s.position,first.position)
        self.assertEqual(m.observe(fix(40,0,3),3).status,'backwards_progress')
    def test_movement_heading_detects_wrong_way_without_bearing(self):
        m=Matcher(network());m.observe(fix(50,0,heading=None),1)
        self.assertEqual(m.observe(fix(30,0,3,heading=None),3).status,'direction_mismatch')
    def test_100_and_500_m_jumps_are_rejected(self):
        m=Matcher(network());first=m.observe(fix(10,0),1)
        for x in (110,510):
            self.assertEqual(m.observe(fix(x,0,1.1),1.1).status,'impossible_jump');self.assertIs(m.last,first)
    def test_skipped_roads_are_not_invented(self):
        m=Matcher(network());m.observe(fix(90,0),1)
        self.assertEqual(m.observe(fix(150,100,3),3).status,'discontinuous')
    def test_parallel_service_road_cannot_steal_progress(self):
        p=network(extra=(RoadEdge('service','s','t',100,36,'allowed'),),
                  coords_extra={'s':(10*UNIT,0),'t':(10*UNIT,100*UNIT)})
        m=Matcher(p);first=m.observe(fix(30,0),1)
        self.assertEqual(m.observe(fix(40,5,2,accuracy=10),2).status,'ambiguous')
        self.assertEqual(m.observe(fix(50,10,3),3).status,'discontinuous');self.assertIs(m.last,first)
    def test_crossing_or_bridge_geometry_is_not_assumed_connected(self):
        p=network(extra=(RoadEdge('bridge','s','t',100,36,'allowed'),),
                  coords_extra={'s':(-50*UNIT,50*UNIT),'t':(50*UNIT,50*UNIT)})
        m=Matcher(p);m.observe(fix(30,0),1)
        self.assertEqual(m.observe(fix(50,20,2,heading=0),2).status,'discontinuous')
    def test_no_route_bias_resolves_parallel_ambiguity(self):
        p=network(extra=(RoadEdge('service','s','t',100,36,'allowed'),),
                  coords_extra={'s':(4*UNIT,0),'t':(4*UNIT,100*UNIT)})
        self.assertEqual(Matcher(p).observe(fix(30,2),1).status,'ambiguous')
    def test_junction_hold_is_uncertain_not_spoken_or_assumed_turn(self):
        p=network()
        m=Matcher(p)
        self.assertEqual(m.observe(fix(90,0,1),1).status,'matched')
        held=m.observe(fix(100,0,2),2)
        self.assertEqual(held.status,'matched')
        self.assertEqual(held.road,'ab')
        self.assertTrue(held.junction_held)
        self.assertEqual(m.last.road,'ab')
        crossed=m.observe(fix(106,0,3),3)
        self.assertEqual((crossed.status,crossed.road,crossed.junction_held),
                         ('matched','bc',False))

    def test_junction_hold_does_not_authorise_forbidden_successor(self):
        p=network(turns=(('ab','bc'),))
        m=Matcher(p)
        m.observe(fix(90,0,1),1)
        held=m.observe(fix(100,0,2),2)
        self.assertTrue(held.junction_held)
        prohibited=m.observe(fix(106,0,3),3)
        self.assertEqual(prohibited.status,'prohibited_turn')
        self.assertIs(m.last,held)

    def test_parallel_road_ambiguity_is_not_treated_as_safe_junction_hold(self):
        p=network(extra=(RoadEdge('service','s','t',100,36,'allowed'),),
                  coords_extra={'s':(4*UNIT,0),'t':(4*UNIT,100*UNIT)})
        m=Matcher(p)
        # No physical connection between the parallel service road and ab.
        self.assertEqual(m.observe(fix(20,2),1).status,'ambiguous')

    def test_normal_adapter_withholds_guidance_during_junction_hold(self):
        g=GpsJourney(network(),'bc',800000)
        g.observe(fix(90,0,1),1)
        s=g.observe(fix(100,0,2),2)
        self.assertTrue(s.match.junction_held)
        self.assertFalse(s.guidance_available)
        self.assertFalse(g.guidance_available(2))
        self.assertEqual(g.junctions(2),())
        self.assertEqual(g.roundabouts(2),())
        advanced=g.observe(fix(106,0,3),3)
        self.assertFalse(advanced.match.junction_held)
        self.assertTrue(advanced.guidance_available)

    def test_gap_requires_explicit_later_reacquisition_component(self):
        m=Matcher(network());first=m.observe(fix(20,0),1)
        self.assertEqual(m.observe(fix(30,0,12),12).status,'reacquisition_required');self.assertIs(m.last,first)
    def test_timed_turn_does_not_use_clock_at_wrong_endpoint(self):
        r=TimedRestriction('no',('ab','bn'),parse_conditional('no_left_turn @ (Mo-Fr 07:00-10:00)'))
        m=Matcher(network(timed=(r,)),timezone_name='UTC')
        t=datetime(2026,10,14,6,59,58,tzinfo=timezone.utc).timestamp()
        m.observe(fix(95,0,t),t)
        self.assertEqual(m.observe(fix(100,10,t+4,heading=0),t+4).status,'prohibited_turn')
    def test_timed_history_timezone_required(self):
        r=TimedRestriction('no',('ab','bn'),parse_conditional('no_left_turn @ (Mo-Fr 07:00-10:00)'))
        with self.assertRaises(ValueError):Matcher(network(timed=(r,)))
    def test_compiled_window_expiry_withholds_position(self):
        p=network(window=(datetime.fromtimestamp(1,timezone.utc),datetime.fromtimestamp(5,timezone.utc)))
        self.assertEqual(Matcher(p).observe(fix(30,0,5),5).status,'restriction_window_expired')
    def test_candidate_budget_reports_incomplete_not_no_road(self):
        roads=[RoadEdge('p'+str(i),'s','t',100,36,'allowed') for i in range(513)]
        p=network(extra=roads,coords_extra={'s':(UNIT,0),'t':(UNIT,100*UNIT)})
        self.assertEqual(Matcher(p).observe(fix(30,0),1).status,'candidate_budget_exceeded')
    def test_preview_does_not_mutate(self):
        m=Matcher(network());s=m.propose(fix(20,0),1)
        self.assertEqual(s.status,'matched');self.assertIsNone(m.last)
    def test_adapter_rejections_do_not_route_or_emit_guidance(self):
        g=GpsJourney(network(),'bc',800000);s=g.observe(fix(20,0),1)
        with patch('navigation_core.journey.run',side_effect=AssertionError('Unexpected routing')):
            rejected=g.observe(fix(30,0,2,accuracy=100),2)
        self.assertEqual(rejected.trusted_snapshot,s.trusted_snapshot)
        self.assertFalse(rejected.guidance_available);self.assertEqual(g.junctions(2),());self.assertEqual(g.roundabouts(2),())
    def test_adapter_same_road_progress_reuses_route_then_arrives(self):
        g=GpsJourney(network(),'bc',800000);g.observe(fix(20,0),1)
        with patch('navigation_core.journey.run',side_effect=AssertionError('Unexpected routing')):
            s=g.observe(fix(60,0,2),2)
        self.assertTrue(s.guidance_available)
        g.observe(fix(120,0,3),3)
        s=g.observe(fix(185,0,4),4)
        self.assertEqual(s.trusted_snapshot.status,'arrived');self.assertFalse(s.guidance_available)
    def test_adapter_error_is_atomic(self):
        g=GpsJourney(network(),'bc',800000)
        with patch.object(g.journey,'start',side_effect=RuntimeError('Synthetic backend failure')):
            with self.assertRaises(RuntimeError):g.observe(fix(20,0),1)
        self.assertIsNone(g.matcher.last);self.assertIsNone(g.journey.snapshot)
    def test_correct_unplanned_legal_turn_triggers_reroute_flag(self):
        g=GpsJourney(network(),'bc',800000);g.observe(fix(90,0),1)
        s=g.observe(fix(100,20,3,heading=0),3)
        self.assertTrue(s.trusted_snapshot.wrong_turn)
    def test_stationary_drift_on_bidirectional_road_keeps_direction(self):
        m=Matcher(network(extra=(RoadEdge('ba','b','a',100,36,'allowed'),)))
        first=m.observe(fix(50,0),1)
        for i,x in enumerate((51,49,50),2):
            s=m.observe(fix(x,1,i,speed=0),i)
            self.assertEqual(s.status,'matched');self.assertEqual(s.road,first.road)
    def test_no_fix_watchdog_withholds_guidance_without_advancing(self):
        g=GpsJourney(network(),'bc',800000);s=g.observe(fix(20,0),1)
        self.assertTrue(g.guidance_available(3));self.assertFalse(g.guidance_available(5))
        self.assertEqual(g.junctions(5),());self.assertEqual(g.roundabouts(5),())
        self.assertEqual(g.journey.snapshot,s.trusted_snapshot)
    def test_terminal_arrival_does_not_move_matcher_beyond_snapshot(self):
        g=GpsJourney(network(),'ab',500000);g.observe(fix(20,0),1);g.observe(fix(60,0,2),2)
        previous=g.matcher.last;s=g.observe(fix(70,0,3),3)
        self.assertEqual(s.match.status,'journey_complete');self.assertIs(g.matcher.last,previous)
    def test_extreme_epoch_is_rejected_without_crash(self):
        self.assertEqual(Matcher(network()).observe(fix(20,0,1e100),1e100).status,'unsupported_clock')
    def test_uncertain_destination_does_not_prematurely_arrive(self):
        g=GpsJourney(network(),'ab',500000);g.observe(fix(40,0),1)
        previous=g.journey.snapshot
        s=g.observe(fix(51,0,2),2)
        self.assertEqual(s.match.status,'destination_uncertain');self.assertEqual(g.journey.snapshot,previous)
        self.assertFalse(s.guidance_available)
        self.assertEqual(g.observe(fix(55,0,3),3).trusted_snapshot.status,'arrived')
    def test_rejected_fix_does_not_consume_accepted_clock(self):
        m=Matcher(network());m.observe(fix(20,0),1)
        self.assertEqual(m.observe(fix(30,0,2,accuracy=100),2).status,'poor_accuracy')
        self.assertEqual(m.observe(fix(30,0,2),2).status,'matched')
    def test_timed_adapter_uses_aware_clock_and_enforces_ban(self):
        r=TimedRestriction('no',('ab','bn'),parse_conditional('no_left_turn @ (Mo-Fr 07:00-10:00)'))
        g=GpsJourney(network(timed=(r,)),'bc',800000,timezone_name='UTC')
        t=datetime(2026,10,14,7,30,tzinfo=timezone.utc).timestamp()
        s=g.observe(fix(90,0,t),t);self.assertTrue(s.guidance_available)
        rejected=g.observe(fix(100,10,t+2,heading=0),t+2)
        self.assertEqual(rejected.match.status,'prohibited_turn');self.assertEqual(rejected.trusted_snapshot,s.trusted_snapshot)

    def test_deterministic_expanded_projection_sweep(self):
        from benchmarks.gps_validation import projection_sweep
        summary=projection_sweep()
        self.assertEqual(summary['failures'],[]);self.assertEqual(summary['cases'],4800)
    def test_four_complete_roundabout_gps_replays(self):
        from benchmarks.gps_validation import roundabout_replays
        rows=roundabout_replays()
        self.assertEqual(len(rows),4)
        self.assertTrue(all(r['passed'] for r in rows),rows)

if __name__=='__main__':unittest.main()
