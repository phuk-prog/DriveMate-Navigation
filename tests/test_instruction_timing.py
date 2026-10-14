"""Original synthetic instruction fixtures; every journey uses the real local core."""
import unittest
from dataclasses import replace
from math import cos,radians,degrees
from unittest.mock import patch
from gps.matching import Fix,EARTH
from gps.recovery import RecoveringGpsJourney
from engine.routing import RoadGraph,RoadEdge
from engine.reconciled import prepare_navigation,Restriction
from engine.lanes import parse_lane_evidence
from guidance.timing import InstructionScheduler,Planner,uk_distance,phase_for,MILE,YARD
from benchmarks.instruction_fixtures import crossroads,observe,start

class InstructionTimingTests(unittest.TestCase):
    def test_format_zero_yards_and_exact_mile(self):
        self.assertEqual(uk_distance(0),'0 yards');self.assertEqual(uk_distance(100*YARD),'100 yards')
        self.assertEqual(uk_distance(MILE),'1 mile');self.assertEqual(uk_distance(2*MILE),'2 miles')
    def test_rounding_below_and_above_mile_boundary(self):
        self.assertEqual(uk_distance(MILE-.001),'1750 yards');self.assertEqual(uk_distance(MILE+.001),'1 mile')
        self.assertEqual(uk_distance(1.25*MILE),'1.3 miles')
    def test_invalid_distance_and_speed_rejected(self):
        for value in (-1,True,float('nan'),float('inf'),1000001):
            with self.assertRaises(ValueError):uk_distance(value)
        for speed in (-1,True,float('nan'),81):
            with self.assertRaises(ValueError):phase_for(20,speed)
    def test_speed_adapts_preparation_and_unknown_speed_has_no_now(self):
        self.assertIsNone(phase_for(500,10));self.assertEqual(phase_for(500,30),'prepare')
        self.assertEqual(phase_for(15,None),'prepare');self.assertEqual(phase_for(15,0),'prepare')
    def test_prepare_instruction_distance_and_lane_evidence(self):
        g=crossroads();start(g,150);s=InstructionScheduler(g,'synthetic')
        f=s.poll(3)
        self.assertEqual(f.pending.phase,'prepare');self.assertIn('turn left',f.pending.text)
        self.assertAlmostEqual(f.instruction.target.distance_m,150,places=4)
        self.assertEqual(f.instruction.target.indicated_lanes,(1,))
        self.assertEqual(f.pending.text,f.instruction.text)
    def test_close_turns_are_linked_before_first_turn(self):
        g=crossroads();start(g,150);f=InstructionScheduler(g,'synthetic').poll(3)
        self.assertIn('then turn right',f.pending.text);self.assertEqual(f.instruction.next_target.departure,'c')
    def test_far_successive_turn_not_linked(self):
        g=crossroads(gap=150);start(g,150);f=InstructionScheduler(g,'synthetic').poll(3)
        self.assertNotIn('then',f.pending.text);self.assertIsNone(f.instruction.next_target)
    def test_peek_is_idempotent_and_acknowledge_delivers_once(self):
        g=crossroads();start(g,150);s=InstructionScheduler(g,'synthetic')
        a=s.poll(3).pending;b=s.poll(3).pending
        self.assertEqual(a,b);self.assertTrue(s.acknowledge(a.event_id,3))
        self.assertIsNone(s.poll(3).pending);self.assertFalse(s.acknowledge(a.event_id,3))
    def test_progress_emits_ordered_phases_without_repeating(self):
        g=crossroads(gap=150);start(g,150);s=InstructionScheduler(g,'synthetic');phases=[]
        for t,d in ((3,150),(5,60),(6,28)):
            if t!=3:observe(g,-d,0,t)
            f=s.poll(t);self.assertIsNotNone(f.pending,f)
            phases.append(f.pending.phase);self.assertTrue(s.acknowledge(f.pending.event_id,t))
            self.assertIsNone(s.poll(t).pending)
        self.assertEqual(phases,['prepare','approach','now'])
    def test_stale_gps_cancels_queued_event(self):
        g=crossroads();start(g,150);s=InstructionScheduler(g,'synthetic');e=s.poll(3).pending
        self.assertFalse(s.acknowledge(e.event_id,7));self.assertIsNone(s.poll(7).pending)
    def test_poor_fix_cancels_before_speech(self):
        g=crossroads();start(g,150);s=InstructionScheduler(g,'synthetic');e=s.poll(3).pending
        observe(g,-140,0,4,accuracy=150)
        self.assertFalse(s.acknowledge(e.event_id,4));self.assertIsNone(s.poll(4).instruction)
    def test_recovery_same_turn_does_not_repeat_delivered_prepare(self):
        g=crossroads();start(g,150);s=InstructionScheduler(g,'synthetic');e=s.poll(3).pending;s.acknowledge(e.event_id,3)
        g.poll(20);self.assertIsNone(s.poll(20).pending)
        for t in (30,31,32):observe(g,-140+ t-30,0,t)
        self.assertIsNone(s.poll(32).pending)
    def test_recovery_cannot_replay_expired_unacknowledged_token(self):
        g=crossroads();start(g,150);s=InstructionScheduler(g,'synthetic');e=s.poll(3).pending
        g.poll(20);s.poll(20)
        for t in (30,31,32):observe(g,-140+t-30,0,t)
        new=s.poll(32).pending;self.assertNotEqual(new.event_id,e.event_id)
        self.assertFalse(s.acknowledge(e.event_id,32))
    def test_text_change_invalidates_old_distance_token(self):
        g=crossroads();start(g,150);s=InstructionScheduler(g,'synthetic');e=s.poll(3).pending
        observe(g,-130,0,4);new=s.poll(4).pending
        self.assertNotEqual(e.text,new.text);self.assertFalse(s.acknowledge(e.event_id,4))
    def test_jitter_cannot_replay_less_urgent_stage(self):
        g=crossroads(gap=150);start(g,60);s=InstructionScheduler(g,'synthetic');e=s.poll(3).pending
        self.assertEqual(e.phase,'approach');s.acknowledge(e.event_id,3)
        observe(g,-62,0,4);self.assertIsNone(s.poll(4).pending)
    def test_late_fast_approach_does_not_emit_catch_up_speech(self):
        g=crossroads();start(g,8,speed=30);s=InstructionScheduler(g,'synthetic')
        f=s.poll(3);self.assertEqual(f.status,'too_late_for_speech');self.assertIsNone(f.pending)
    def test_accuracy_interval_at_junction_suppresses_instruction(self):
        g=crossroads();start(g,4);s=InstructionScheduler(g,'synthetic')
        observe(g,-3,0,4,accuracy=6);f=s.poll(4)
        self.assertEqual(f.status,'junction_position_uncertain');self.assertIsNone(f.pending);self.assertIsNone(f.instruction)
    def test_moving_age_allowance_can_suppress_action_before_stale_limit(self):
        g=crossroads();start(g,28);s=InstructionScheduler(g,'synthetic')
        self.assertEqual(s.poll(5.9).status,'junction_position_uncertain')
    def test_stopped_vehicle_gets_preparation_not_immediate_turn(self):
        g=crossroads();start(g,50,speed=0);f=InstructionScheduler(g,'synthetic').poll(3)
        self.assertEqual(f.pending.phase,'prepare');self.assertTrue(f.pending.text.startswith('In '))
    def test_missing_lanes_leave_direction_available(self):
        g=crossroads(lanes=False);start(g,150);f=InstructionScheduler(g,'synthetic').poll(3)
        self.assertIsNotNone(f.pending);self.assertEqual(f.instruction.target.indicated_lanes,())
    def test_unknown_access_does_not_close_or_hide_direction(self):
        g=crossroads(access='unknown');start(g,150);f=InstructionScheduler(g,'synthetic').poll(3)
        self.assertIsNotNone(f.pending);self.assertEqual(f.instruction.target.indicated_lanes,())
    def test_known_turn_ban_never_generates_forbidden_turn(self):
        g=crossroads(turns=(('a','b'),));start(g,150);f=InstructionScheduler(g,'synthetic').poll(3)
        self.assertIsNone(f.pending);self.assertEqual(g.snapshot.status,'no_route')
    def test_first_turn_clears_and_second_turn_becomes_primary(self):
        g=crossroads(gap=100);start(g,30);s=InstructionScheduler(g,'synthetic');e=s.poll(3).pending
        if e:s.acknowledge(e.event_id,3)
        observe(g,0,20,4,heading=0);f=s.poll(4)
        self.assertEqual(f.instruction.target.approach,'b');self.assertEqual(f.instruction.target.departure,'c')
        self.assertIn('right',f.instruction.text);self.assertNotIn('left',f.instruction.text)
    def test_checkpoint_restart_preserves_delivered_stage(self):
        g=crossroads();start(g,150);s=InstructionScheduler(g,'synthetic');e=s.poll(3).pending;s.acknowledge(e.event_id,3)
        new=InstructionScheduler(g,'synthetic',checkpoint=s.checkpoint())
        self.assertIsNone(new.poll(3).pending)
    def test_checkpoint_does_not_restore_pending_speech(self):
        g=crossroads();start(g,150);s=InstructionScheduler(g,'synthetic');e=s.poll(3).pending
        new=InstructionScheduler(g,'synthetic',checkpoint=s.checkpoint());other=new.poll(3).pending
        self.assertNotEqual(e.event_id,other.event_id);self.assertFalse(new.acknowledge(e.event_id,3))
    def test_checkpoint_wrong_trip_invalid_schema_and_values_rejected(self):
        g=crossroads();s=InstructionScheduler(g,'synthetic');state=s.checkpoint()
        for changes in ({'session_key':'other'},{'schema':True},{'seq':True},{'delivered':3},{'arrival_delivered':1},{'observed_road':123}):
            with self.assertRaises(ValueError):InstructionScheduler(g,'synthetic',checkpoint={**state,**changes})
        with self.assertRaises(ValueError):InstructionScheduler(g,'synthetic',checkpoint={})
    def test_clock_regression_cancels_without_speaking(self):
        g=crossroads();start(g,150);s=InstructionScheduler(g,'synthetic');e=s.poll(3).pending
        f=s.poll(2);self.assertEqual(f.status,'clock_out_of_order');self.assertIsNone(f.pending)
        self.assertFalse(s.acknowledge(e.event_id,3))
    def test_invalid_clock_and_session_key_rejected(self):
        g=crossroads();s=InstructionScheduler(g,'synthetic')
        with self.assertRaises(ValueError):s.poll(float('nan'))
        with self.assertRaises(ValueError):InstructionScheduler(g,'bad key')
    def test_repeated_instruction_queries_do_not_run_router(self):
        g=crossroads();start(g,150);s=InstructionScheduler(g,'synthetic')
        with patch('navigation_core.journey.run',side_effect=AssertionError('Unexpected routing')):
            s.poll(3);s.poll(3.1);s.poll(3.2)
    def test_arrival_delivered_once_and_text_shared(self):
        g=crossroads();start(g,30);s=InstructionScheduler(g,'synthetic')
        observe(g,0,30,4,heading=0);observe(g,50,40,5)
        for t,x in ((6,120),(7,190),(8,260)):observe(g,x,40,t)
        f=s.poll(8);self.assertEqual(f.pending.phase,'arrival');self.assertEqual(f.pending.text,f.instruction.text)
        self.assertTrue(s.acknowledge(f.pending.event_id,8));self.assertIsNone(s.poll(8).pending)
        restored=InstructionScheduler(g,'synthetic',checkpoint=s.checkpoint());self.assertIsNone(restored.poll(8).pending)
    def test_delayed_arrival_is_not_spoken_after_gps_freshness_expired(self):
        g=crossroads();start(g,30);s=InstructionScheduler(g,'synthetic')
        observe(g,0,30,4,heading=0);observe(g,50,40,5)
        for t,x in ((6,120),(7,190),(8,260)):observe(g,x,40,t)
        self.assertIsNone(s.poll(12).pending)
    def test_history_route_disagreement_suppresses_all_instruction_events(self):
        from tests.test_gps_recovery import diamond,start as begin,recover
        g=RecoveringGpsJourney(diamond((Restriction('no',('uk','merge','goal')),)),'goal',800000)
        begin(g,x=50);g.poll(20);recover(g,x=240)
        f=InstructionScheduler(g,'synthetic').poll(32)
        self.assertIsNone(f.pending);self.assertIsNone(f.instruction)
    def test_roundabout_instruction_replay_and_unknown_entry(self):
        from benchmarks.instruction_validation import roundabout_instruction_replay
        result=roundabout_instruction_replay()
        self.assertTrue(result['passed'],result)
    def test_even_harder_instruction_stream_sweep(self):
        from benchmarks.instruction_validation import adversarial_sweep
        result=adversarial_sweep()
        self.assertEqual(result['failures'],[]);self.assertEqual(result['cases'],2304)
    def test_actual_wrong_turn_cancels_old_left_token_and_generates_new_plan(self):
        g=crossroads(detour=True);start(g,30);s=InstructionScheduler(g,'synthetic');old=s.poll(3).pending
        observe(g,50,0,4);f=s.poll(4)
        self.assertTrue(g.snapshot.wrong_turn);self.assertEqual(f.instruction.target.approach,'straight')
        self.assertEqual(f.instruction.target.departure,'detour');self.assertFalse(s.acknowledge(old.event_id,4))
        self.assertNotEqual(f.pending.target_signature,old.target_signature)
    def test_wrong_turn_without_route_cancels_queued_instruction(self):
        g=crossroads();start(g,30);s=InstructionScheduler(g,'synthetic');old=s.poll(3).pending
        observe(g,50,0,4);self.assertEqual(g.snapshot.status,'no_route')
        self.assertFalse(s.acknowledge(old.event_id,4));self.assertIsNone(s.poll(4).instruction)
    def test_unverified_lane_evidence_does_not_block_valid_direction(self):
        g=crossroads(lanes='invalid');start(g,150);f=InstructionScheduler(g,'synthetic').poll(3)
        self.assertIsNotNone(f.pending);self.assertEqual(f.instruction.target.indicated_lanes,())
    def test_unknown_speed_never_assumes_a_timely_speech_window(self):
        g=crossroads();start(g,50,speed=None);f=InstructionScheduler(g,'synthetic').poll(3)
        self.assertIsNotNone(f.instruction);self.assertIsNone(f.pending)
    def test_unverified_first_manoeuvre_does_not_skip_to_later_right_turn(self):
        g=crossroads();start(g,150);original=g.sessions[0].junctions()
        changed=(replace(original[0],manoeuvre='unknown'),)+original[1:]
        with patch.object(g.sessions[0],'junctions',return_value=changed):
            f=InstructionScheduler(g,'synthetic').poll(3)
        self.assertEqual(f.status,'manoeuvre_unverified');self.assertIsNone(f.pending)
    def test_checkpoint_malformed_target_is_rejected(self):
        g=crossroads();s=InstructionScheduler(g,'synthetic');state=s.checkpoint()
        for value in ('invalid','[]','{}','["junction","a","b","left",true,[]]'):
            with self.assertRaises(ValueError):InstructionScheduler(g,'synthetic',checkpoint={**state,'active':value})
    def test_legal_u_turn_is_distinct_from_a_confirmed_banned_u_turn(self):
        points={'w':(0,0),'j':(0,degrees(100/EARTH))}
        edges=[RoadEdge('a','w','j',100,36,'allowed'),RoadEdge('r','j','w',100,36,'allowed')]
        for banned in (False,True):
            p=prepare_navigation(RoadGraph(points,edges,(('a','r'),) if banned else ()),points)
            g=RecoveringGpsJourney(p,'r',800000)
            for t in (1,2,3):g.observe(Fix(0,degrees((50+t)/EARTH),t,2,10,90,5),t)
            f=InstructionScheduler(g,'synthetic').poll(3)
            if banned:self.assertIsNone(f.pending)
            else:self.assertIn('U-turn',f.pending.text)
    def test_repeated_junction_visit_has_a_new_occurrence(self):
        points={'s':(0,degrees(-100/EARTH)),'w':(0,0),'j':(0,degrees(100/EARTH)),
                'n':(degrees(100/EARTH),degrees(100/EARTH)),'end':(0,degrees(200/EARTH))}
        edges=[RoadEdge(n,a,b,l,36,'allowed') for n,a,b,l in
               [('start','s','w',100),('a','w','j',100),('b','j','n',100),('c','n','w',141.5),('goal','j','end',100)]]
        rules=(Restriction('no',('start','a','goal')),Restriction('no',('start','a','b','c','a','goal')))
        p=prepare_navigation(RoadGraph(points,edges,multi_restrictions=rules),points)
        g=RecoveringGpsJourney(p,'goal',800000);s=InstructionScheduler(g,'synthetic')
        def location(x,y,t,h):g.observe(Fix(degrees(y/EARTH),degrees(x/EARTH),t,2,10,h,5),t)
        for t,x in ((1,-80),(2,-70),(3,-60)):location(x,0,t,90)
        location(50,0,5,90);first=s.poll(5).pending;self.assertTrue(s.acknowledge(first.event_id,5))
        location(100,50,7,0);s.poll(7)
        location(50,50,9,225);s.poll(9)
        location(50,0,11,90);again=s.poll(11).pending
        self.assertEqual(first.target_signature,again.target_signature)
        self.assertEqual(first.phase,again.phase);self.assertNotEqual(first.event_id,again.event_id)
        self.assertTrue(s.acknowledge(again.event_id,11))

if __name__=='__main__':unittest.main()
