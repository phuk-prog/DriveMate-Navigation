"""Stable, bounded, non-personal public UK preference-case register tests."""
import json
import unittest
from hashlib import sha256

from benchmarks.public_route_preferences import probe_preference_diversity
from benchmarks.uk_preference_case_register import (
    summarise_discriminating_case, validate_case_register)
from engine import RoadEdge, RoadGraph
from engine.route_alternatives import generate_route_candidates


class PreferenceCaseRegisterTests(unittest.TestCase):
    def setUp(self):
        self.graph = RoadGraph(["A","B","C","D","E"], [
            RoadEdge("AB","A","B",50,10,"allowed"),
            RoadEdge("BD","B","D",50,10,"allowed"),
            RoadEdge("AC","A","C",150,80,"allowed"),
            RoadEdge("CE","C","E",150,80,"allowed"),
            RoadEdge("ED","E","D",150,80,"allowed"),
        ])
        self.sha=sha256(b"synthetic map only").hexdigest()

    def _cases(self):
        out=[]
        def collect(i, source, target, fastest, shortest, balanced, options):
            out.append(summarise_discriminating_case(
                "synthetic-source",self.sha,i,source,target,
                fastest,shortest,balanced,options))
        # The route generator expects the source SHA as its candidate snapshot.
        report=probe_preference_diversity(self.graph,snapshot_id=self.sha,
                    maximum_pairs=8,on_discriminating_case=collect)
        return out,report

    def test_replayable_and_restricted_to_discriminating_cases(self):
        first,summary=self._cases()
        second,again=self._cases()
        self.assertEqual(first,second)
        self.assertEqual(summary,again)
        self.assertGreater(len(first),0)
        self.assertEqual(len(first),summary["fastest_and_shortest_different_path_pairs"])
        register=validate_case_register(first,expected_count=len(first))
        self.assertTrue(register["case_register_valid"])
        self.assertEqual(register["case_count"],len(first))
        self.assertFalse(register["independent_legality_established"])

    def test_no_route_identifiers_or_coordinates_leaked(self):
        cases,_=self._cases()
        record=json.dumps(cases)
        self.assertNotIn('"source"',record)
        self.assertNotIn('"destination"',record)
        self.assertNotIn('"A"',record)
        self.assertNotIn('"B"',record)
        for case in cases:
            self.assertEqual(case["independent_current_uk_road_legality"],"UNKNOWN")
            self.assertEqual(case["competitor_outcomes"],"NOT_RUN")
            self.assertFalse(case["traffic_observed"])
            self.assertFalse(case["same_fastest_shortest"])

    def test_changed_source_or_pair_changes_identity(self):
        candidate_set=generate_route_candidates(
            self.graph,"A","D",snapshot_id=self.sha)
        f=next(x for x in candidate_set if "fastest" in x.generated_by)
        s=next(x for x in candidate_set if "shortest" in x.generated_by)
        b=next(x for x in candidate_set if "balanced" in x.generated_by)
        x=summarise_discriminating_case(
            "test",self.sha,0,"A","D",f,s,b,candidate_set)
        y=summarise_discriminating_case(
            "test",self.sha,1,"A","D",f,s,b,candidate_set)
        self.assertNotEqual(x["case_id"],y["case_id"])
        self.assertNotEqual(x["fastest_route_digest"],x["shortest_route_digest"])

    def test_false_legality_and_duplicate_cases_rejected(self):
        cases,_=self._cases()
        with self.assertRaises(AssertionError):
            validate_case_register(cases + cases,expected_count=2*len(cases))
        broken=[dict(cases[0],independent_current_uk_road_legality="VERIFIED")]
        with self.assertRaises(AssertionError):
            validate_case_register(broken)
        with self.assertRaises(AssertionError):
            validate_case_register(cases,expected_count=len(cases)+1)

    def test_single_mode_optimum_refused(self):
        candidates=generate_route_candidates(
            self.graph,"A","D",snapshot_id=self.sha)
        f=next(x for x in candidates if "fastest" in x.generated_by)
        s=next(x for x in candidates if "shortest" in x.generated_by)
        b=next(x for x in candidates if "balanced" in x.generated_by)
        with self.assertRaises(ValueError):
            summarise_discriminating_case(
                "test",self.sha,0,"A","D",f,f,b,candidates)
        with self.assertRaises(ValueError):
            summarise_discriminating_case(
                "test","not a sha",0,"A","D",f,s,b,candidates)


if __name__ == "__main__":
    unittest.main()
