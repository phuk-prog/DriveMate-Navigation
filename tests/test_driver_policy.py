"""Unit-level preference and reroute policy contracts; not field-road evidence."""
import json
from pathlib import Path
import unittest

from engine.driver_policy import (
    DriverNavigationSettings, RouteOption, choose_preferred_route,
    consider_reroute, decide_reroute_switch,
)


def option(ident, secs, metres, maneuvers=0, confidence=0.95, *,
           verified=True, current=True):
    return RouteOption(ident, secs, metres, confidence, maneuvers, verified, current)


class DriverPolicyTests(unittest.TestCase):
    def setUp(self):
        self.default = DriverNavigationSettings()
        self.current = option("current", 1500, 14000, 3)
        self.better = option("better", 1280, 14500, 2)

    def test_safe_adaptive_defaults(self):
        p = self.default
        self.assertEqual((p.route_mode, p.reroute_mode, p.threshold_mode),
                         ("balanced", "intelligent", "adaptive"))
        self.assertEqual((p.countdown_mode, p.countdown_seconds,
                          p.auto_switch_if_unanswered), ("adaptive", 5, True))

    def test_preferences_round_trip_and_reject_unknown_options(self):
        customized = DriverNavigationSettings(route_mode="fastest",
                        reroute_mode="always_faster", threshold_mode="fixed",
                        countdown_mode="fixed", countdown_seconds=3,
                        fixed_benefit_seconds=180, auto_switch_if_unanswered=False)
        self.assertEqual(DriverNavigationSettings.from_mapping(customized.to_mapping()),
                         customized)
        for bad in ({"route_mode":"unsafe"}, {"countdown_seconds":8},
                    {"auto_switch_if_unanswered":"yes"},
                    {"new_future_field":123}, {"fixed_benefit_seconds":float("nan")}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                DriverNavigationSettings.from_mapping(bad)

    def test_manifest_agrees_with_actual_policy_defaults_and_options(self):
        manifest = json.loads((Path(__file__).resolve().parents[1] /
                              "config/driver-navigation-settings.json").read_text())
        self.assertEqual(manifest["schema_version"], 1)
        self.assertEqual(manifest["defaults"], self.default.to_mapping())
        fields = {entry["id"]:entry for entry in manifest["controls"]}
        self.assertEqual(set(fields), set(self.default.to_mapping()))
        self.assertEqual(fields["route_mode"]["values"],
                         ["fastest","shortest","balanced"])
        self.assertEqual(fields["reroute_mode"]["values"],
                         ["always_faster","blocked_only","intelligent"])
        self.assertEqual(fields["threshold_mode"]["values"],
                         ["any_saving","fixed","adaptive"])
        self.assertEqual(fields["countdown_mode"]["values"],["fixed","adaptive"])
        self.assertFalse(manifest["safety_rules_user_configurable"])

    def test_select_fastest_shortest_and_balanced_independently(self):
        a = option("quick", 800, 18000, 9)
        b = option("short", 1050, 12000, 6)
        c = option("calm", 890, 15500, 0)
        self.assertEqual(choose_preferred_route([a,b,c],
                         DriverNavigationSettings(route_mode="fastest")).route_id,"quick")
        self.assertEqual(choose_preferred_route([a,b,c],
                         DriverNavigationSettings(route_mode="shortest")).route_id,"short")
        self.assertEqual(choose_preferred_route([a,b,c], self.default).route_id,"calm")

    def test_illegal_stale_and_unverified_route_cannot_win_any_mode(self):
        bad = option("too-fast-unsafe", 20, 100, verified=False)
        stale = option("stale", 30, 120, current=False)
        good = option("good", 1000, 20000)
        for mode in ("fastest","shortest","balanced"):
            with self.subTest(mode=mode):
                s=DriverNavigationSettings(route_mode=mode)
                self.assertEqual(choose_preferred_route([bad,stale,good],s),good)
        self.assertIsNone(choose_preferred_route([bad,stale],self.default))

    def test_unverified_candidate_never_offered_even_with_verified_closure(self):
        unsafe=option("unknown", 300, 8000, verified=False)
        d=consider_reroute(self.current,unsafe,self.default,
                           verified_current_route_blocked=True)
        self.assertEqual((d.offered,d.reason),(False,"unverified_or_stale_alternative"))

    def test_adaptive_offers_meaningful_saving_not_tiny_gain(self):
        yes=consider_reroute(self.current,self.better,self.default,
                             maneuver_lead_seconds=40)
        self.assertTrue(yes.offered)
        self.assertEqual(yes.countdown_seconds,5)
        tiny=option("tiny",1498,14000,3)
        no=consider_reroute(self.current,tiny,self.default)
        self.assertEqual((no.offered,no.reason),(False,"improvement_below_threshold"))

    def test_any_saving_and_fixed_threshold_are_selectable(self):
        tiny=option("few",1498,14000,3)
        s=DriverNavigationSettings(route_mode="fastest",threshold_mode="any_saving")
        self.assertTrue(consider_reroute(self.current,tiny,s).offered)
        fixed=DriverNavigationSettings(route_mode="fastest",threshold_mode="fixed",
                                       fixed_benefit_seconds=180)
        self.assertFalse(consider_reroute(self.current,tiny,fixed).offered)
        self.assertTrue(consider_reroute(self.current,self.better,fixed).offered)

    def test_shortest_preference_can_favor_shorter_distance_not_time(self):
        s=DriverNavigationSettings(route_mode="shortest",threshold_mode="any_saving")
        candidate=option("shorter",1600,12000,2)
        decision=consider_reroute(self.current,candidate,s)
        self.assertTrue(decision.offered)
        self.assertLess(decision.estimated_time_saving_seconds,0)  # longer ETA

    def test_blocked_only_never_offers_nonclosure(self):
        s=DriverNavigationSettings(reroute_mode="blocked_only")
        self.assertEqual(consider_reroute(self.current,self.better,s).reason,
                         "rerouting_disabled_until_blocked")
        detour=option("detour",2000,21000,5,confidence=0.2)
        d=consider_reroute(self.current,detour,s,verified_current_route_blocked=True)
        self.assertTrue(d.offered)
        self.assertLess(d.estimated_time_saving_seconds,0)

    def test_prediction_confidence_and_safe_lead_required(self):
        doubtful=option("uncertain",900,14000,3,confidence=0.2)
        self.assertEqual(consider_reroute(self.current,doubtful,self.default).reason,
                         "unreliable_predicted_improvement")
        self.assertEqual(consider_reroute(self.current,self.better,self.default,
                                          maneuver_lead_seconds=7).reason,
                         "insufficient_safe_lead_time")

    def test_adaptive_countdown_and_fixed_countdown(self):
        for lead,seconds in ((12,3),(30,5),(60,7)):
            with self.subTest(lead=lead):
                d=consider_reroute(self.current,self.better,self.default,
                                   maneuver_lead_seconds=lead)
                self.assertEqual(d.countdown_seconds,seconds)
        fixed=DriverNavigationSettings(countdown_mode="fixed",countdown_seconds=6)
        self.assertEqual(consider_reroute(self.current,self.better,fixed,
                                          maneuver_lead_seconds=30).countdown_seconds,6)

    def test_decline_cooldown_and_safe_switch_revalidation(self):
        offer=consider_reroute(self.current,self.better,self.default)
        switch=lambda **kwargs: decide_reroute_switch(
            offer,self.default,elapsed_seconds=5,proposed_route_id="better",**kwargs)
        self.assertEqual(switch(driver_response="reject",safe_to_switch=True,
                                 evidence_still_current=True).action,"KEEP")
        self.assertEqual(switch(safe_to_switch=False,
                                 evidence_still_current=True).action,"DEFER")
        self.assertEqual(switch(safe_to_switch=True,
                                 evidence_still_current=False).action,"DEFER")
        self.assertEqual(switch(safe_to_switch=True,
                                 evidence_still_current=True).action,"SWITCH")
        self.assertEqual(consider_reroute(self.current,self.better,self.default,
                                          rejected_route_id="better").reason,
                         "driver_previously_rejected")
        self.assertEqual(consider_reroute(self.current,self.better,self.default,
                                          cooldown_remaining_seconds=60).reason,
                         "stability_cooldown")

    def test_automatic_switch_after_countdown_not_before(self):
        offer=consider_reroute(self.current,self.better,self.default,
                               maneuver_lead_seconds=30)
        kwargs={"safe_to_switch":True,"evidence_still_current":True,
                "proposed_route_id":"better"}
        self.assertEqual(decide_reroute_switch(offer,self.default,elapsed_seconds=4,
                                              **kwargs).action,"WAIT")
        decision=decide_reroute_switch(offer,self.default,elapsed_seconds=5,**kwargs)
        self.assertEqual((decision.action,decision.reason),
                         ("SWITCH","unanswered_countdown_elapsed"))
        self.assertEqual(decide_reroute_switch(offer,self.default,elapsed_seconds=0,
                       driver_response="accept",**kwargs).action,"SWITCH")
        self.assertEqual(decide_reroute_switch(offer,self.default,elapsed_seconds=20,
                       proposed_route_id="different",safe_to_switch=True,
                       evidence_still_current=True).action,"DEFER")

    def test_automatic_switch_can_be_disabled_without_disabling_manual_accept(self):
        s=DriverNavigationSettings(auto_switch_if_unanswered=False)
        offer=consider_reroute(self.current,self.better,s)
        opts={"elapsed_seconds":100,"safe_to_switch":True,
              "evidence_still_current":True,"proposed_route_id":"better"}
        self.assertEqual(decide_reroute_switch(offer,s,**opts).action,"WAIT")
        self.assertEqual(decide_reroute_switch(offer,s,driver_response="accept",
                                               **opts).action,"SWITCH")

    def test_bad_external_arguments_rejected(self):
        with self.assertRaises(ValueError):
            consider_reroute(self.current,self.better,self.default,
                             cooldown_remaining_seconds=-1)
        with self.assertRaises(ValueError):
            consider_reroute(self.current,self.better,self.default,
                             maneuver_lead_seconds=float("inf"))
        offer=consider_reroute(self.current,self.better,self.default)
        with self.assertRaises(ValueError):
            decide_reroute_switch(offer,self.default,elapsed_seconds=-1)
        with self.assertRaises(ValueError):
            decide_reroute_switch(offer,self.default,elapsed_seconds=6,
                                  driver_response="unsafe")

    def test_verified_closure_cannot_override_unsafe_maneuver(self):
        detour=option("detour",2000,21000,6)
        offer=consider_reroute(self.current,detour,self.default,
                               verified_current_route_blocked=True,
                               maneuver_lead_seconds=30)
        self.assertTrue(offer.offered)
        self.assertEqual(decide_reroute_switch(offer,self.default,
                         elapsed_seconds=100,proposed_route_id="detour",
                         safe_to_switch=False,evidence_still_current=True).action,"DEFER")


if __name__ == "__main__":
    unittest.main()
