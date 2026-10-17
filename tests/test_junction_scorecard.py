"""Synthetic scorer controls, not reference executions."""
import copy
import unittest
from benchmarks.junction_trial import run_dmn, normalize
from benchmarks.junction_scorecard import scoreboard

class JunctionScorerTests(unittest.TestCase):
    def test_complete_cohort_and_roster(self):
        rows=scoreboard([run_dmn()])['rows']
        self.assertEqual(len(rows),13)
        self.assertEqual((rows[0]['rank'],rows[0]['score_out_of_ten']),(1,10))
        self.assertTrue(all(r['rank'] is None for r in rows[1:]))

    def test_incomplete_unranked(self):
        r=run_dmn();r['cases'][0]['outcome']='UNRESOLVED'
        row=next(x for x in scoreboard([r])['rows'] if x['system']=='DMN')
        self.assertIsNone(row['rank']);self.assertIsNone(row['score_out_of_ten'])

    def test_duplicate_and_changed_oracle_rejected(self):
        r=run_dmn()
        with self.assertRaises(ValueError):scoreboard([r,r])
        r['oracle_sha256']='changed'
        with self.assertRaises(ValueError):scoreboard([r])

    def test_partial_cohort_rejected(self):
        r=run_dmn();r['cases'].pop()
        with self.assertRaises(ValueError):scoreboard([r])

    def test_unknown_instruction_never_ignored(self):
        d={'paths':[{'instructions':[{'sign':-99}]}]}
        self.assertEqual(normalize('GraphHopper',d)[0],[{'kind':'unknown:-99'}])

    def test_brouter_signed_roundabout(self):
        d={'features':[{'properties':{'voicehints':[[3,14,-2,10,90]]}}]}
        self.assertEqual(normalize('BRouter',d)[0],[{'kind':'roundabout','exit':2}])
