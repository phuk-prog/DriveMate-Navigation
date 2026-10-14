"""Original synthetic loss/recovery scenarios; no actual place or sensor claims."""
import unittest
from dataclasses import replace
from datetime import datetime,timezone
from unittest.mock import patch
from engine.routing import RoadEdge,RoadGraph
from engine.reconciled import prepare_navigation,Restriction
from engine.restrictions import Restriction as TimedRestriction,parse_conditional
from gps.matching import Matcher,Fix
from gps.recovery import RecoveringGpsJourney,possible_histories
from tests.test_gps_matching import fix,network,UNIT

def start(g,x=20,y=0,t=1,heading=90):
    for d in (0,1,2):result=g.observe(fix(x+d,y,t+d,heading=heading),t+d)
    return result
def recover(g,x=50,y=0,t=30,heading=90,accuracy=2):
    for d in (0,1,2):result=g.observe(fix(x+d,y,t+d,heading=heading,accuracy=accuracy),t+d)
    return result
def diamond(rules=()):
    pts={'a':(0,0),'j':(0,100*UNIT),'u':(30*UNIT,150*UNIT),'d':(-30*UNIT,150*UNIT),
         'k':(0,200*UNIT),'l':(0,300*UNIT),'z':(0,400*UNIT),'q':(100*UNIT,300*UNIT)}
    edges=[RoadEdge(n,a,b,100,36,'allowed') for n,a,b in
           [('a','a','j'),('up','j','u'),('down','j','d'),('uk','u','k'),('dk','d','k'),('merge','k','l'),('goal','l','z'),('side','l','q')]]
    return prepare_navigation(RoadGraph(pts,edges,multi_restrictions=rules),pts)

class GpsRecoveryTests(unittest.TestCase):
    def test_outlier_then_second_gap_requires_a_new_three_fix_streak(self):
        g=RecoveringGpsJourney(network(),'bc',800000);first=start(g)
        bad=g.observe(fix(40,40,4,accuracy=2),4)
        self.assertFalse(bad.guidance_available)
        for x,t in ((40,5),(41,6),(45,10),(46,11)):
            update=g.observe(fix(x,0,t),t)
            self.assertEqual(update.status,'confirming')
            self.assertFalse(update.guidance_available)
            self.assertEqual(g.snapshot,first.trusted_snapshot)
        update=g.observe(fix(47,0,12),12)
        self.assertEqual(update.status,'recovered')
        self.assertTrue(update.guidance_available)

    def test_startup_requires_three_fresh_fixes(self):
        g=RecoveringGpsJourney(network(),'bc',800000)
        for t in (1,2):
            s=g.observe(fix(20+t,0,t),t)
            self.assertEqual(s.status,'confirming');self.assertIsNone(s.trusted_snapshot)
            self.assertFalse(g.guidance_available(t))
        s=g.observe(fix(23,0,3),3)
        self.assertEqual(s.status,'tracking');self.assertTrue(s.guidance_available)
    def test_fast_burst_requires_two_second_span(self):
        g=RecoveringGpsJourney(network(),'bc',800000)
        for t in (1,1.1,1.2):self.assertEqual(g.observe(fix(20,0,t),t).status,'confirming')
        self.assertEqual(g.observe(fix(22,0,3),3).status,'tracking')
    def test_sensor_silence_never_advances_snapshot(self):
        g=RecoveringGpsJourney(network(),'bc',800000);first=start(g)
        s=g.poll(7);self.assertEqual(s.status,'gps_lost');self.assertEqual(s.trusted_snapshot,first.trusted_snapshot)
        self.assertFalse(s.guidance_available);self.assertEqual(g.junctions(7),());self.assertEqual(g.roundabouts(7),())
    def test_guidance_lookup_alone_has_watchdog(self):
        g=RecoveringGpsJourney(network(),'bc',800000);start(g)
        self.assertFalse(g.guidance_available(7));self.assertEqual(g.junctions(7),())
    def test_same_road_tunnel_recovery(self):
        g=RecoveringGpsJourney(network(),'bc',800000);start(g);g.poll(20)
        s=recover(g)
        self.assertEqual(s.status,'recovered');self.assertTrue(s.guidance_available)
        self.assertEqual(s.trusted_snapshot.position.edge,g.p.edge_ids['ab']);self.assertTrue(s.history_inferred)
    def test_skipped_road_recovery_retains_possible_history(self):
        g=RecoveringGpsJourney(network(),'ne',800000);start(g,x=90);g.poll(20)
        s=recover(g,x=130,y=100)
        self.assertEqual(s.status,'recovered');self.assertEqual(g.histories,(('bn',),))
        self.assertTrue(s.guidance_available);self.assertTrue(s.history_inferred)
    def test_parallel_road_without_directed_connection_cannot_recover(self):
        p=network(extra=(RoadEdge('service','s','t',100,36,'allowed'),),coords_extra={'s':(12*UNIT,0),'t':(12*UNIT,100*UNIT)})
        g=RecoveringGpsJourney(p,'bc',800000);first=start(g);g.poll(20)
        s=recover(g,x=50,y=12)
        self.assertEqual(s.status,'recovery_unreachable');self.assertEqual(g.snapshot,first.trusted_snapshot)
    def test_opposing_carriageway_cannot_be_reached_by_teleport(self):
        p=network(extra=(RoadEdge('opp','t','s',100,36,'allowed'),),coords_extra={'s':(12*UNIT,0),'t':(12*UNIT,100*UNIT)})
        g=RecoveringGpsJourney(p,'bc',800000);start(g);g.poll(20)
        s=recover(g,x=60,y=12,heading=270)
        self.assertNotIn(s.status,('recovered','tracking'));self.assertFalse(s.guidance_available)
    def test_one_way_wrong_heading_cannot_recover(self):
        g=RecoveringGpsJourney(network(),'bc',800000);first=start(g);g.poll(20)
        s=recover(g,heading=270)
        self.assertEqual(s.status,'direction_mismatch');self.assertEqual(g.snapshot,first.trusted_snapshot)
    def test_one_way_backwards_position_without_loop_unreachable(self):
        g=RecoveringGpsJourney(network(),'bc',800000);start(g,x=60);g.poll(20)
        s=recover(g,x=20)
        self.assertEqual(s.status,'recovery_unreachable')
    def test_unknown_access_and_missing_lane_data_still_recover(self):
        g=RecoveringGpsJourney(network(access='unknown'),'bc',800000);start(g);g.poll(20)
        s=recover(g);self.assertEqual(s.status,'recovered');self.assertTrue(s.match.unverified_access)
        self.assertIn('ab',s.trusted_snapshot.unverified_access_edges)
    def test_closed_road_recovery_is_rejected(self):
        g=RecoveringGpsJourney(network(access='prohibited'),'bc',800000)
        self.assertEqual(recover(g).status,'prohibited_road');self.assertIsNone(g.snapshot)
    def test_confirmed_future_turn_ban_remains_after_gap(self):
        g=RecoveringGpsJourney(network(turns=(('ab','bn'),)),'bn',800000);start(g);g.poll(20)
        s=recover(g)
        self.assertEqual(s.trusted_snapshot.status,'no_route');self.assertFalse(s.guidance_available)
        self.assertEqual(g.p.route('a','c').edge_ids,('ab','bc'))
    def test_bad_fix_resets_confirmation_streak(self):
        g=RecoveringGpsJourney(network(),'bc',800000);start(g);g.poll(20)
        self.assertEqual(g.observe(fix(40,0,30),30).confirmations,1)
        s=g.observe(fix(41,0,31,accuracy=100),31);self.assertEqual(s.confirmations,0)
        self.assertEqual(g.observe(fix(42,0,32),32).confirmations,1)
    def test_pending_fix_gap_resets_confirmation(self):
        g=RecoveringGpsJourney(network(),'bc',800000);start(g);g.poll(20)
        g.observe(fix(40,0,30),30)
        self.assertEqual(g.observe(fix(45,0,35),35).confirmations,1)
    def test_recovery_uses_stricter_accuracy_than_tracking(self):
        g=RecoveringGpsJourney(network(),'bc',800000);start(g);g.poll(20)
        self.assertEqual(recover(g,accuracy=20).status,'recovery_accuracy_insufficient')
    def test_starting_indoors_and_repeated_bad_fixes_do_not_start_route(self):
        g=RecoveringGpsJourney(network(),'bc',800000)
        for t in range(1,21):
            s=g.observe(fix(20,0,t,accuracy=150),t);self.assertIsNone(s.trusted_snapshot)
        self.assertEqual(start(g,t=21).status,'tracking')
    def test_stale_last_known_fix_never_confirms_recovery(self):
        g=RecoveringGpsJourney(network(),'bc',800000);start(g);g.poll(20)
        self.assertEqual(g.observe(fix(40,0,4),30).status,'stale_fix');self.assertEqual(g.confirmations,0)
    def test_out_of_order_pending_fix_resets(self):
        g=RecoveringGpsJourney(network(),'bc',800000);start(g);g.poll(20)
        g.observe(fix(40,0,30),30)
        s=g.observe(fix(41,0,29),30);self.assertEqual(s.status,'out_of_order');self.assertEqual(s.confirmations,0)
    def test_out_of_order_receipt_does_not_advance(self):
        g=RecoveringGpsJourney(network(),'bc',800000);first=start(g)
        s=g.observe(fix(24,0,4),2);self.assertEqual(s.status,'receipt_out_of_order')
        self.assertEqual(g.snapshot,first.trusted_snapshot)
        self.assertFalse(s.guidance_available);self.assertFalse(g.guidance_available(3))
    def test_recovery_motion_jump_cannot_move_snapshot(self):
        p=network(extra=(RoadEdge('far','s','t',100,36,'allowed'),),coords_extra={'s':(0,5000*UNIT),'t':(0,5100*UNIT)})
        g=RecoveringGpsJourney(p,'bc',800000);first=start(g)
        for t in (4,5,6,7):s=g.observe(fix(5006+t,0,t),t)
        self.assertEqual(s.status,'recovery_impossible_jump');self.assertEqual(g.snapshot,first.trusted_snapshot)
    def test_recovery_search_budget_is_incomplete_not_no_route(self):
        g=RecoveringGpsJourney(network(),'ne',800000,max_states=1);first=start(g);g.poll(20)
        s=recover(g,x=130,y=100)
        self.assertEqual(s.status,'recovery_search_incomplete');self.assertEqual(g.snapshot,first.trusted_snapshot)
    def test_very_long_gap_is_explicitly_bounded(self):
        g=RecoveringGpsJourney(network(),'bc',800000);start(g);g.poll(400)
        self.assertEqual(recover(g,t=401).status,'recovery_gap_outside_bounds')
    def test_multiple_histories_retained_without_declaring_actual_path(self):
        g=RecoveringGpsJourney(diamond(),'goal',800000);start(g,x=50);g.poll(20)
        s=recover(g,x=240)
        self.assertEqual(s.possible_history_count,2);self.assertTrue(s.guidance_available)
        self.assertEqual(set(g.histories),{('uk',),('dk',)})
    def test_history_budget_refuses_partial_result(self):
        g=RecoveringGpsJourney(diamond(),'goal',800000,max_histories=1);first=start(g,x=50);g.poll(20)
        s=recover(g,x=240)
        self.assertEqual(s.status,'recovery_history_incomplete');self.assertEqual(g.snapshot,first.trusted_snapshot)
    def test_history_disagreement_withholds_route(self):
        p=diamond((Restriction('no',('uk','merge','goal')),))
        g=RecoveringGpsJourney(p,'goal',800000);start(g,x=50);g.poll(20)
        s=recover(g,x=240)
        self.assertEqual(s.status,'history_uncertain');self.assertFalse(s.guidance_available)
        self.assertEqual(s.trusted_snapshot.roads,());self.assertEqual(g.junctions(32),())
        self.assertEqual(set(g.histories),{('up','uk'),('down','dk')})
    def test_assuming_legal_past_cannot_erase_future_restriction(self):
        p=diamond((Restriction('no',('a','up')),Restriction('no',('uk','merge','goal'))))
        g=RecoveringGpsJourney(p,'goal',800000);start(g,x=50);g.poll(20)
        s=recover(g,x=240)
        # The banned branch still physically exists. Unknown actual traversal
        # must not be eliminated as an assumed legal trip to clear the next ban.
        self.assertEqual(s.status,'history_uncertain');self.assertFalse(s.guidance_available)
    def test_actual_observed_suffix_merges_equivalent_histories(self):
        g=RecoveringGpsJourney(diamond(),'goal',800000);start(g,x=50);g.poll(20);recover(g,x=240)
        s=g.observe(fix(320,0,34),34)
        self.assertEqual(s.possible_history_count,1);self.assertTrue(s.guidance_available)
        self.assertEqual(g.histories,(('merge',),))
    def test_unknown_history_cannot_authorise_a_turn_legal_for_only_one_variant(self):
        g=RecoveringGpsJourney(diamond((Restriction('no',('uk','merge','goal')),)),'goal',800000)
        start(g,x=50);g.poll(20);recover(g,x=240);previous=g.snapshot
        s=g.observe(fix(320,0,34),34)
        self.assertEqual(s.status,'prohibited_turn');self.assertEqual(g.snapshot,previous)
    def test_tracking_backend_error_preserves_all_trusted_state(self):
        g=RecoveringGpsJourney(network(),'bc',800000);first=start(g);last=g.matcher.last
        with patch('navigation_core.journey.run',side_effect=RuntimeError('Synthetic backend failure')):
            with self.assertRaises(RuntimeError):g.observe(fix(120,0,5),5)
        self.assertEqual(g.snapshot,first.trusted_snapshot);self.assertIs(g.matcher.last,last)
    def test_recovery_backend_error_preserves_old_state_and_streak(self):
        g=RecoveringGpsJourney(network(),'bc',800000);first=start(g);g.poll(20)
        g.observe(fix(50,0,30),30);g.observe(fix(51,0,31),31);last=g.matcher.last
        with patch('navigation_core.journey.run',side_effect=RuntimeError('Synthetic backend failure')):
            with self.assertRaises(RuntimeError):g.observe(fix(52,0,32),32)
        self.assertEqual(g.snapshot,first.trusted_snapshot);self.assertIs(g.matcher.last,last);self.assertEqual(g.confirmations,2)
    def test_fresh_observed_arrival_after_recovery(self):
        g=RecoveringGpsJourney(network(),'bc',800000);start(g);g.poll(20);recover(g,x=120)
        s=g.observe(fix(185,0,34),34);self.assertEqual(s.trusted_snapshot.status,'arrived')
        self.assertFalse(s.guidance_available);self.assertEqual(g.poll(100).status,'journey_complete')
    def test_recovery_past_destination_does_not_invent_arrival(self):
        g=RecoveringGpsJourney(network(),'bc',800000);start(g);g.poll(20)
        s=recover(g,x=190);self.assertNotEqual(s.trusted_snapshot.status,'arrived');self.assertFalse(s.guidance_available)
    def test_uncertain_destination_fixes_cannot_confirm_arrival(self):
        g=RecoveringGpsJourney(network(),'bc',800000);start(g);g.poll(20)
        s=recover(g,x=179);self.assertEqual(s.status,'destination_uncertain');self.assertFalse(s.guidance_available)
    def test_uncertain_destination_fix_preserves_plan_until_confirmed_crossing(self):
        # Independent synthetic fixture proves the formerly broken transition.
        # Never declare arrival merely from the fix at the target itself.
        g=RecoveringGpsJourney(network(),'bc',500000)
        start(g,x=20)
        for x,t in ((85,4),(105,5),(135,6),(145,7)):
            observation=g.observe(fix(x,0,t),t)
            self.assertEqual(observation.status,'tracking')
        previous=g.snapshot
        uncertain=g.observe(fix(150,0,8),8)
        self.assertEqual(uncertain.status,'destination_uncertain')
        self.assertFalse(uncertain.guidance_available)
        self.assertEqual(g.snapshot,previous)
        self.assertEqual(g.mode,'tracking')
        self.assertEqual(g.matcher.last.timestamp,7)
        # A later reliable directed position beyond the target may confirm
        # arrival without searching for an impossible route back in time.
        crossed=g.observe(fix(154,0,9),9)
        self.assertEqual(crossed.trusted_snapshot.status,'arrived')
        self.assertFalse(crossed.guidance_available)
        self.assertEqual(g.poll(12).status,'journey_complete')

    def test_uncertain_destination_does_not_override_gps_timeout(self):
        g=RecoveringGpsJourney(network(),'bc',500000)
        start(g,x=20)
        for x,t in ((85,4),(105,5),(135,6),(145,7)):
            g.observe(fix(x,0,t),t)
        previous=g.snapshot
        self.assertEqual(g.observe(fix(150,0,8),8).status,'destination_uncertain')
        self.assertEqual(g.poll(12).status,'gps_lost')
        self.assertEqual(g.snapshot,previous)
        self.assertFalse(g.guidance_available(12))

    def test_timed_recovery_preserves_future_ban_and_clock(self):
        r=TimedRestriction('no',('ab','bn'),parse_conditional('no_left_turn @ (Mo-Fr 07:00-10:00)'))
        g=RecoveringGpsJourney(network(timed=(r,)),'bn',800000,timezone_name='UTC')
        t=datetime(2026,10,14,7,30,tzinfo=timezone.utc).timestamp()
        start(g,t=t);g.poll(t+20);s=recover(g,t=t+30)
        self.assertEqual(s.trusted_snapshot.status,'no_route');self.assertFalse(s.guidance_available)
    def test_compiled_window_expiration_stops_recovery(self):
        window=(datetime.fromtimestamp(1,timezone.utc),datetime.fromtimestamp(20,timezone.utc))
        g=RecoveringGpsJourney(network(window=window),'bc',800000,timezone_name='UTC')
        start(g);g.poll(25)
        self.assertEqual(recover(g).status,'restriction_window_expired')
    def test_invalid_budgets_and_clocks_rejected(self):
        for kwargs in ({'max_states':0},{'max_states':True},{'max_histories':17},{'max_histories':0}):
            with self.assertRaises(ValueError):RecoveringGpsJourney(network(),'bc',800000,**kwargs)
        g=RecoveringGpsJourney(network(),'bc',800000)
        for action in (g.poll,g.guidance_available):
            with self.assertRaises(ValueError):action(float('nan'))
    def test_pending_recovery_does_not_call_router(self):
        g=RecoveringGpsJourney(network(),'bc',800000);start(g);g.poll(20)
        with patch('navigation_core.journey.run',side_effect=AssertionError('Unexpected route job')):
            g.observe(fix(50,0,30),30);g.observe(fix(51,0,31),31)
    def test_multiple_bad_fix_burst_never_mutates_snapshot(self):
        g=RecoveringGpsJourney(network(),'bc',800000);first=start(g)
        for t in range(4,24):
            s=g.observe(fix(20,0,t,accuracy=100),t)
            self.assertEqual(s.trusted_snapshot,first.trusted_snapshot);self.assertFalse(s.guidance_available)
    def test_ring_recovery_drops_unknown_entry_number(self):
        from benchmarks.gps_recovery_validation import ring_recovery
        row=ring_recovery()
        self.assertTrue(row['passed'],row)
    def test_expanded_hard_recovery_sweep(self):
        from benchmarks.gps_recovery_validation import hard_sweep
        summary=hard_sweep()
        self.assertEqual(summary['failures'],[]);self.assertEqual(summary['cases'],1536)
    def test_independent_exhaustive_recovery_history_oracle(self):
        from benchmarks.gps_recovery_validation import reachability_oracle_sweep
        summary=reachability_oracle_sweep()
        self.assertEqual(summary['failures'],[]);self.assertEqual(summary['cases'],216)
    def test_stationary_at_lights_recovers_without_lane_or_heading_guess(self):
        g=RecoveringGpsJourney(network(),'bc',800000);start(g,x=50);g.poll(20)
        for t,x in ((30,52),(31,51),(32,53)):
            s=g.observe(fix(x,1,t,speed=0,heading=None),t)
        self.assertEqual(s.status,'recovered');self.assertTrue(s.guidance_available)
    def test_alternating_parallel_fixes_never_form_recovery_streak(self):
        p=network(extra=(RoadEdge('service','s','t',100,36,'allowed'),),coords_extra={'s':(12*UNIT,0),'t':(12*UNIT,100*UNIT)})
        g=RecoveringGpsJourney(p,'bc',800000);first=start(g);g.poll(20)
        for t in range(30,46):
            s=g.observe(fix(50,12 if t%2 else 0,t),t)
            self.assertFalse(s.guidance_available);self.assertEqual(g.snapshot,first.trusted_snapshot)
    def test_tracking_failure_on_later_variant_is_atomic(self):
        g=RecoveringGpsJourney(diamond(),'goal',800000);start(g,x=50);g.poll(20);recover(g,x=240)
        previous=g.snapshot;matcher=g.matcher.last;histories=g.histories
        with patch('engine.reconciled.AccessAwareJourney.observe',side_effect=[g.sessions[0].snapshot,RuntimeError('Synthetic second variant failure')]):
            with self.assertRaises(RuntimeError):g.observe(fix(250,0,34),34)
        self.assertEqual(g.snapshot,previous);self.assertIs(g.matcher.last,matcher);self.assertEqual(g.histories,histories)
    def test_converged_road_histories_do_not_erase_disputed_roundabout_ledger(self):
        base=diamond();pts=dict(base.coordinates)
        pts.update({'r1':(100*UNIT,300*UNIT),'r2':(100*UNIT,400*UNIT),
                    'x1':(200*UNIT,300*UNIT),'x2':(100*UNIT,500*UNIT)})
        edges=[e for e in base.source_edges.values() if e.edge_id!='side']
        edges.extend([RoadEdge('r1','l','r1',100,36,'allowed','roundabout'),
                      RoadEdge('r2','r1','r2',100,36,'allowed','roundabout'),
                      RoadEdge('r3','r2','l',141.5,36,'allowed','roundabout'),
                      RoadEdge('x1','r1','x1',100,36,'allowed'),RoadEdge('x2','r2','x2',100,36,'allowed')])
        rules=(Restriction('only',('merge','r1')),Restriction('no',('uk','merge','r1','x1')))
        p=prepare_navigation(RoadGraph(pts,edges,multi_restrictions=rules),pts)
        g=RecoveringGpsJourney(p,'goal',800000);start(g,x=50);g.poll(20);recover(g,x=240)
        g.observe(fix(300,50,34,heading=0),34)
        g.observe(fix(350,100,36),36)
        s=g.observe(fix(350,50,38,heading=225),38)
        self.assertTrue(s.guidance_available);self.assertEqual(len(g.sessions),2)
        self.assertEqual(g.histories[0],g.histories[1])
        self.assertNotEqual(g.sessions[0].roundabouts()[0].exit_number,g.sessions[1].roundabouts()[0].exit_number)
        self.assertEqual(g.roundabouts(38),())
        s=g.observe(fix(320,0,40),40)
        self.assertEqual(len(g.sessions),1);self.assertEqual(g.roundabouts(40),())
    def test_recovery_confirmation_can_cross_contiguous_short_segments(self):
        g=RecoveringGpsJourney(network(),'ne',800000);start(g);g.poll(20)
        self.assertEqual(g.observe(fix(90,0,30),30).status,'confirming')
        self.assertEqual(g.observe(fix(100,70,31,heading=0),31).status,'confirming')
        s=g.observe(fix(120,100,32),32)
        self.assertEqual(s.status,'recovered');self.assertTrue(s.guidance_available)
    def test_startup_crossed_segments_preserve_fresh_restriction_suffix(self):
        extra=(RoadEdge('next','e','t',100,36,'allowed'),)
        p=network(extra=extra,coords_extra={'t':(100*UNIT,300*UNIT)},
                  rules=(Restriction('no',('ab','bn','ne','next')),))
        g=RecoveringGpsJourney(p,'next',800000)
        g.observe(fix(90,0,1),1);g.observe(fix(100,70,2,heading=0),2)
        s=g.observe(fix(120,100,3),3)
        self.assertEqual(g.histories,(('ab','bn'),));self.assertEqual(s.trusted_snapshot.status,'no_route')
    def test_high_fanout_is_bounded_before_expansion(self):
        p=network(extra=tuple(RoadEdge('fan'+str(i),'b','c',100,36,'allowed') for i in range(50)))
        matcher=Matcher(p);origin=matcher.observe(fix(20,0),1)
        target=replace(origin,position=p.position('ne',500000),road='ne')
        result=possible_histories(matcher,origin,target,((),),30,max_states=8)
        self.assertEqual(result.status,'recovery_search_incomplete');self.assertEqual(result.expanded,0)

if __name__=='__main__':unittest.main()
